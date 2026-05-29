# SESSION PLAN — lat-3-hx-mode-d-h (Sprint H — diagnostic)
**Date:** 2026-05-30
**Goal:** Empirically characterize the two G.1 boundaries that Sprint G left open. Do not patch the kernel; bisect the boundaries with data, then file Sprint H.PATCH as a follow-on grounded in that data.

Sprint G's closure recorded two constraints whose root cause did not yield to schedule ablations:

1. All matmul dims must equal the Halide tile width (128). H ∈ {256, 512} and D_out ∈ {256} all failed with identical-magnitude diverging values across ~8 ablations.
2. `q_bits ≤ 14` with the current test data. q_bits = 16 hit a similar deterministic divergence even though the scalar reference already uses `saturating_add` matching Halide's `vmpy.h:sat` (Sprint G commit 903cddc; lattice retraction 433f465 acknowledges this).

Sprint H runs three bisection experiments to pin down the actual boundary surfaces.

---

## 1. Scope (engine-only, ~150-200 LOC)

| Item | Sprint H? |
|---|---|
| `T_HALIDE_FFN_DIAG_INSTRUMENT` — IDL method returning `hidden[0..16]` alongside `y` | **YES** |
| `T_HALIDE_FFN_BISECT_QBITS` — sweep q_bits ∈ {12, 13, 14, 15, 16} at fixed shape | **YES** |
| `T_HALIDE_FFN_BISECT_DIM` — sweep H ∈ {128, 160, 192, 224, 256} at fixed q_bits=14 | **YES** |
| `Sprint H.PATCH` — kernel patch | NO — filed as follow-on after Sprint H closes with the data |
| `shannon-prime-system` changes | NO |
| New memory entries | NO |
| Touching bridge / FastRpcSession / DmaBuffer / Axum code | NO |

---

## 2. T_HALIDE_FFN_DIAG_INSTRUMENT design

A second Halide generator `sp_ffn_2stage_diag_gen.cpp` clones the Sprint G generator (`sp_ffn_2stage_gen.cpp`) but adds a second `Output<Buffer<int16_t>> hidden_out{"hidden_out", 2}` alongside `Y`. The schedule is identical; `hidden_out(hc, batch) = hidden(hc, batch)` simply teesthe internal intermediate to a caller-provided buffer.

Skel handler `sp_compute_ffn_2stage_diag`:
- Same VTCM staging as Sprint G's `ffn_2stage_halide` for X / W1 / W2 / Y.
- Additional VTCM region for `hidden_out` (sized `batch * h_dim * 2`, 128-aligned).
- `HAP_perf_get_pcycles` brackets the call.
- IDL has two `rout sequence<octet>` buffers: `y_buf` and `hidden_buf`.

Rust harness invokes the diag method on the simplest Sprint G failing shape — B=8 D_in=128 H=256 D_out=128 q=16 b=16 — and compares both `hidden[0..16]` and `y[0..16]` against the existing scalar reference's intermediates.

**Discriminator:**
- If `hidden` matches reference but `y` diverges → matmul-2 is the bug site.
- If `hidden` already diverges → matmul-1 is the bug site, or hidden's storage/cast layer.
- The first diverging element index is the smallest-failing-tile coordinate, which pinpoints the bad axis (c, batch, or rh reduction).

No PASS/FAIL gate on this test by itself — it's a data-collection method whose output the next two bisections cite.

---

## 3. T_HALIDE_FFN_BISECT_QBITS design

Fix shape to **B=8 D_in=128 H=128 D_out=128** (TINY shape known to pass at q=14; smallest possible repro).

Run the diag-instrumented kernel at q_bits ∈ {12, 13, 14, 15, 16}. For each q:
- Record `y[0]` from Halide.
- Record `hidden[0..4]` from Halide.
- Compute the scalar reference's y[0] and hidden[0..4] (both already saturating-arithmetic, mirroring Halide's `vmpy.h:sat`).
- Verdict: `PASS` if got==exp, `FAIL @ y[i]=got vs exp` otherwise.

Output: a 5-row table that pinpoints the exact q_bits boundary at which divergence first appears. The Sprint G observation was "q=14 PASS, q=16 FAIL"; this bisection determines whether q=15 also fails (smooth boundary) or if 15 passes and 16 fails (single-point step).

---

## 4. T_HALIDE_FFN_BISECT_DIM design

Fix q_bits = 14 (known to pass at H=128). Sweep H ∈ {128, 160, 192, 224, 256} at fixed B=8 D_in=128 D_out=128.

- H=128: tile width, single tile, known PASS baseline.
- H=160 = 128 + 32: non-multiple of 128, partial tile in second iteration → tests "tail-loop predication" hypothesis directly.
- H=192 = 128 + 64: non-multiple, larger partial tile.
- H=224 = 128 + 96: non-multiple, near-full second tile.
- H=256 = 2 × 128: multiple-but-not-128, exact two tiles → tests "multi-tile state leakage" hypothesis.

Decision tree per the user mandate:

| H=160 (non-multiple) | H=256 (multiple, not 128) | Implication |
|---|---|---|
| FAIL | FAIL | NOT just predication — the constraint is broader |
| FAIL | PASS | Tail-loop predication problem; pad-to-tile fixes |
| PASS | FAIL | "Equals tile width" constraint; multi-tile codegen bug |
| PASS | PASS | Sprint G's empirical record was wrong or input-dependent — re-investigate |

The 192 and 224 rows add resolution to whichever hypothesis the 160/256 results favor.

---

## 5. Commit discipline

Per the user's mandate: one commit per bisection test, isolating attribution.

| # | Content | Repo |
|---|---|---|
| 1 | This plan | lattice |
| 2 | Diag generator + IDL method + skel handler + `T_HALIDE_FFN_DIAG_INSTRUMENT` test (the infrastructure all three sub-tests depend on) | engine |
| 3 | `T_HALIDE_FFN_BISECT_QBITS` test, building on commit 2's infrastructure | engine |
| 4 | `T_HALIDE_FFN_BISECT_DIM` test, building on commit 2's infrastructure | engine |
| 5 | Closure with bisection result tables + best-fit hypothesis + Sprint H.PATCH spec proposal | lattice |

Per the user: do NOT propose Sprint H.PATCH within Sprint H itself. The closure files it as a follow-on with the bisection evidence cited.

---

## 6. Sub-tags

- `lat-phase-3-hx-mode-d-h-diag-instrument`
- `lat-phase-3-hx-mode-d-h-bisect-qbits`
- `lat-phase-3-hx-mode-d-h-bisect-dim`
- `lat-phase-3-hx-mode-d-h-closed` — umbrella

---

## 7. What this sprint does NOT do

- Fix the bug. That's Sprint H.PATCH, gated on this sprint's data.
- Modify Sprint G's existing `ffn_2stage_halide` kernel or any of its callers. The diag generator is additive; Sprint G's FFN gate continues to gate on the existing kernel.
- Add `shannon-prime-system` code or memory entries. The diagnostic harness is engine-only.
- Touch the bridge.

---

## 8. Risks

**R1: Diag kernel's added hidden_out exposure changes Halide's schedule decisions.** If exposing `hidden` as Output forces different storage/codegen than the inlined-intermediate `hidden` in the Sprint G kernel, the bisection results may not be a faithful reproduction of Sprint G's bug. Mitigation: re-run T_HALIDE_FFN_VTCM_B8 against the diag kernel (just discard `hidden_out`) to confirm Y output is identical to Sprint G's kernel on a known-passing config. If diag kernel doesn't reproduce Sprint G's q=16 failure for the same shape, that's data too — it would say the bug is sensitive to whether the intermediate is inlined.

**R2: VTCM budget overflows with the extra hidden_out region.** For B=8 H=256: extra hidden_out region = 8 × 256 × 2 = 4 KB. Negligible against the 4 MB cap. Not a real risk.

**R3: Bisection results disagree across runs.** All Sprint G failure values were stable across runs. If diag bisection gives different y[0]/hidden values run-to-run, that itself is a finding (non-determinism in Halide codegen) and gets reported.
