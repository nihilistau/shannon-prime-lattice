# SESSION PLAN — lat-3-hx-mode-k-beta (K v0.beta — Barrett-reduction CRT kernel)
**Date:** 2026-05-30
**Goal:** Implement the manifesto Trick #1 CRT-split matmul: two Halide AOT skels emitting `mod-q_1` and `mod-q_2` residue computations, dispatched concurrently via the K v0.alpha `DualDispatch` substrate, recombined via ARM-side Garner into the full unbounded integer matmul. Math identity to Sprint J's saturating kernel in the no-saturation regime; per-prime Barrett correctness verified against arbitrary-precision (i128) reference; dual-dispatch speedup ≥ 1.5× per K v0.alpha's measured baseline.

---

## 1. Reference summary

| Source | Citation | Relevance |
|---|---|---|
| K v0.alpha closure `lat-phase-13-6-k-alpha-closed` | overlap_fraction=0.9699, speedup=1.935× | The dispatch substrate. K v0.beta's two threads each invoke its prime's skel concurrently. |
| Phase 2-CU.PTX closure (engine `63d7e2d`) | `MU_Q1=1073744895`, `MU_Q2=1073751039`, k=60 (Barrett with floor(2^60/q) precomputed constants); q_1=1073738753, q_2=1073732609 | Same primes + Barrett constants reused from the CUDA NTT lineage. |
| `reference-nvcc-paired-register-bug` (operator memory) | HVX word-pair codegen unreliable on the same paired-register allocator surface that bit nvcc | Drives the explicit `mul_hi + mul_lo` decomposition fallback if Halide's `Int(64)` lowering doesn't produce clean SASS. |
| Sprint J closure | Sprint J kernel produces saturating-i32 matmul output | Math identity comparison target (conditional on no-saturation regime). |
| Sprint H method 9 IDL marshalling | `sp_compute_ffn_2stage_diag_halide` ABI | NOT reused — Sprint K beta has its own kernel/IDL method. |

---

## 2. Architectural decisions

### 2.1 Two compile-time-parameterized skels

One Halide generator (`sp_mod_q_matmul_gen.cpp`) takes the prime + Barrett μ as `Generator<>` parameters. Build script invokes the AOT step **twice**, emitting:

- `tools/sp_compute_skel_q1/halide_gen/sp_mod_q_matmul_q1_halide.{o,h}` (q=1073738753, μ=1073744895)
- `tools/sp_compute_skel_q2/halide_gen/sp_mod_q_matmul_q2_halide.{o,h}` (q=1073732609, μ=1073751039)

Two new skel directories `tools/sp_compute_skel_q1/` and `tools/sp_compute_skel_q2/` are clones of `sp_compute_skel/`'s CMake + IDL + handler skeleton, each linking its prime-specific Halide .o. They build into:
- `libsp_compute_skel_q1.so`
- `libsp_compute_skel_q2.so`

The existing `libsp_compute_skel.so` (Sprint G/H/I/J saturating kernel) is **untouched**.

### 2.2 IDL method shape (shared between both skels)

```
long mod_q_matmul(in long batch, in long d_in, in long h_dim,
                  in  sequence<octet> x_buf,   // batch × d_in × i16
                  in  sequence<octet> w_buf,   // h_dim × d_in × i16
                  rout sequence<octet> r_buf,  // batch × h_dim × i32 (residues in [0, q))
                  rout long vtcm_used,
                  rout long kernel_pcycles_lo,
                  rout long kernel_pcycles_hi);
```

No `d_out` (this is the single-matmul kernel: X @ W^T). No `b_term` or `q_bits` (those apply ARM-side after Garner). Output is i32 residue in [0, q), one per (batch, h_dim) output cell.

### 2.3 Halide kernel — Barrett-reduction matmul

Math per output cell (c, b):
```
acc_i64 = Σ_{rd=0..D_in} signed_to_mod_q(X(rd, b)) × signed_to_mod_q(W(c, rd))
r = barrett_reduce(acc_i64, q, μ)   // r in [0, q)
output(c, b) = cast<i32>(r)
```

where:
- `signed_to_mod_q(v)`: i16 → i32 in [0, q). For v ≥ 0: v. For v < 0: v + q.
- `barrett_reduce(x, q, μ)` (Phase 2-CU.PTX pattern at k=60):
  ```
  q_est = (x × μ) >> 60   // i64 → i64
  r = x - q_est × q       // in [0, 2q)
  r = select(r ≥ q, r - q, r)
  ```

**Halide expression style (initial — Int(64) native lowering attempted first):**
```cpp
Expr xv = cast<int64_t>(select(X(rd, b) < 0,
                               cast<int32_t>(X(rd, b)) + int32_t(Q),
                               cast<int32_t>(X(rd, b))));
Expr wv = cast<int64_t>(select(W(c, rd) < 0,
                               cast<int32_t>(W(c, rd)) + int32_t(Q),
                               cast<int32_t>(W(c, rd))));
Expr prod = xv * wv;                  // i64
Expr acc = sum(prod);                  // i64 reduction over rd
Expr q_est = (acc * int64_t(MU)) >> 60;
Expr r1 = acc - q_est * int64_t(Q);
Expr r2 = select(r1 >= int64_t(Q), r1 - int64_t(Q), r1);
output(c, b) = cast<int32_t>(r2);
```

**Fallback if Int(64) doesn't lower cleanly to HVX SASS:** explicit `mul_hi + mul_lo` decomposition using `Int(32)` halves (per `reference-nvcc-paired-register-bug`). Decomposition pattern:
- For positive 30-bit values a, b: split each into 15-bit halves `a = a_hi*2^15 + a_lo`, `b = b_hi*2^15 + b_lo`.
- `a*b = a_hi*b_hi*2^30 + (a_hi*b_lo + a_lo*b_hi)*2^15 + a_lo*b_lo` — each sub-product is i15×i15→i32 (safe on `vmpyih`).
- Barrett reduction similarly decomposed.

The fallback adds ~80 LOC to the generator. Anti-pattern lock: **do not commit Int(64) path until SASS verified clean.**

### 2.4 Dispatcher — two-prime concurrent invoke

`CrtDispatcher` opens **two** FastRpcSession instances (one per skel). Per Sprint J / K v0.alpha: each session opens its own `remote_handle64`. Both wrapped in `Arc<FastRpcSession>` (auto-Send+Sync per K v0.alpha empirical check).

```rust
pub struct CrtDispatcher {
    pub sess_q1: Arc<FastRpcSession>,
    pub sess_q2: Arc<FastRpcSession>,
}

pub fn dispatch_crt_matmul(&self, x, w, batch, d_in, h_dim) -> (Vec<i32>, Vec<i32>) {
    // Spawn 2 threads; each calls invoke_mod_q_matmul on its own session.
    // Returns (r_1, r_2) residue vectors of length batch*h_dim each.
}
```

### 2.5 Garner recombine on ARM

For each output element, given residues `r_1 ∈ [0, q_1)` and `r_2 ∈ [0, q_2)`:

```
let q1_inv_q2: i64 = mod_inverse(q_1, q_2);   // precomputed at startup
let diff = (r_2 - r_1).rem_euclid(q_2 as i64);
let t = (diff * q1_inv_q2) % q_2 as i64;
let unbounded = r_1 as i64 + t * q_1 as i64;  // in [0, M) where M = q_1 * q_2
// If unbounded > M/2, interpret as signed negative (CRT covers signed range too)
let signed = if unbounded >= (M / 2) { unbounded - M } else { unbounded };
```

`signed` is the recovered i64 value of the unbounded sum (in [-M/2, M/2)). For Sprint J's saturating-i32 matmul to match, `signed` must fit in i32 — that's the no-saturation regime gate.

### 2.6 Arbitrary-precision Rust reference

For `M_K_beta_BARRETT_CORRECTNESS`, the scalar reference uses Rust's native `i128` (covers 2^60 with ample margin):
```rust
fn mod_q_matmul_ref(x: &[i16], w: &[i16], q: i64,
                    batch: usize, d_in: usize, h_dim: usize) -> Vec<i32> {
    let mut out = vec![0i32; batch * h_dim];
    for b in 0..batch {
        for c in 0..h_dim {
            let mut acc: i128 = 0;
            for d in 0..d_in {
                let xv = (x[b*d_in + d] as i128).rem_euclid(q as i128);
                let wv = (w[c*d_in + d] as i128).rem_euclid(q as i128);
                acc = (acc + xv * wv).rem_euclid(q as i128);
            }
            out[b * h_dim + c] = acc as i32;
        }
    }
    out
}
```

---

## 3. Gates

| Gate | Definition (per operator's authorization) |
|---|---|
| **M_K_beta_MATH_IDENTITY** | (a) Sprint J `hidden` output bitwise-equal to CRT-recombined-then-clamp/cast output at layer-14 W_gate / B=8 / q_bits=14 / Sprint I+J activation patterns. (b) Sprint J accumulator stays within ±INT32_MAX across the test data (asserted via instrumented scalar reference; if fires, identity claim is vacuous — surface upstream). Identity is **conditional on the no-saturation regime; document explicitly**. |
| **M_K_beta_BARRETT_CORRECTNESS** | q_1 and q_2 residues each match `mod_q_matmul_ref` (i128 arbitrary precision). Tests: edge cases (a=0, a=q-1, b=0, b=q-1 across input range); worst-case 128-element dot product of near-maximum residues; cross-validate r_1+r_2 Garner → Z_M result matches i128-direct Z_M compute. |
| **M_K_beta_DUAL_DISPATCH_SPEEDUP** | Wall-clock speedup of CRT-split (q_1 thread + q_2 thread) vs sequential single-prime baseline ≥ **1.5×** (operator's stretch is 1.8×; floor per `feedback-lattice-baseline-is-prior-lattice` is any measurable improvement). |
| **M_K_beta_LEAK_FREE** | 100-iter CRT-dispatch + drop cycle; no fd accumulation; no DmaBuffer leaks across the dual-skel handles. |

Umbrella `lat-phase-13-6-k-beta-closed` fires when all 4 gates close.

---

## 4. Stage ordering (with risk-driven sequencing)

Per the operator's "plan-first/multi-file/commit-between-stages discipline" + the operator-added scope direction: "DO NOT use Halide::Int(64) for the Barrett intermediate without first cross-checking the lowered HVX assembly."

| Stage | Content | Repo | Derisks |
|---|---|---|---|
| 1 | This plan | lattice | Architectural scope agreement |
| 2 | **Halide gen probe** — minimal `mod_q_matmul` generator with Int(64) intermediate; AOT-emit; dump SASS and inspect for `vmem` / `vmpy_oeih` / paired-register patterns. **NO skel binding yet.** | engine | Int(64) lowering on HVX — the single biggest unknown |
| 3 | **Skel infra clone** — `tools/sp_compute_skel_q1/` + `tools/sp_compute_skel_q2/` directories (CMake + IDL + handler skeleton). Initially link a TRIVIAL Halide .o that just returns zeros — proves the dual-skel build infrastructure works without committing to the kernel SASS quality. | engine | CMake / build script / IDL pipeline |
| 4 | **Real kernel emission** — wire Stage-2's verified-SASS kernel into the skels. Build both .so files. Push to device + verify loadable. | engine | End-to-end loadability under Path B |
| 5 | **CrtDispatcher + Garner + arbitrary-prec reference + sp_crt_dispatch_smoke bin** | engine | Math identity + Barrett correctness can be exercised against the reference |
| 6 | **On-device verification** — all 4 gates against layer 14 W_gate (load via Sprint J pattern; do NOT recreate the loader) | engine | Real-data correctness |
| 7 | **Closure + tags** | lattice | Audit trail |

If Stage 2 SASS shows Int(64) doesn't lower cleanly (panic, scalar fallback, or paired-register chaos), an interstitial commit converts the generator to explicit `mul_hi + mul_lo` decomposition before proceeding to Stage 3.

---

## 5. Sub-tag taxonomy

- `lat-phase-13-6-k-beta-halide-int64-sass-check` — Stage 2 (derisk).
- `lat-phase-13-6-k-beta-halide-dual-prime` — generator emits both .o files cleanly.
- `lat-phase-13-6-k-beta-skel-build` — Stage 3/4 build infra produces two .so files.
- `lat-phase-13-6-k-beta-dispatcher` — Stage 5 CrtDispatcher.
- `lat-phase-13-6-k-beta-garner-recombine` — Garner ARM-side code + math.
- `lat-phase-13-6-k-beta-math-identity` — gate PASS.
- `lat-phase-13-6-k-beta-barrett-correctness` — gate PASS.
- `lat-phase-13-6-k-beta-parallelism-measured` — speedup gate PASS with verbatim number.
- `lat-phase-13-6-k-beta-leak-free` — 100-iter gate.
- `lat-phase-13-6-k-beta-closed` — umbrella.

---

## 6. Out of scope (explicit)

- ❌ NPU dispatch (K.2; remains the cross-island unlock).
- ❌ Full FFN (gate × up × down → SiLU); K v0.beta is single matmul.
- ❌ Multi-layer composition (post-K integration).
- ❌ KV cache compression (Sprint J.3).
- ❌ Modifying the existing `sp_compute_skel` (Sprint G/H/I/J saturating kernel).
- ❌ Modifying Sprint J's loader (read-only consumer).
- ❌ Modifying K v0.alpha's `sp_dual_dispatch.rs` (CrtDispatcher is a NEW module).
- ❌ Touching `sp_daemon` (Sprint J.5 owns it).
- ❌ q_bits > 15 — Sprint H constraint stands.
- ❌ `Halide::%` operator (per Gemini guidance — explicit Barrett or canonical select).
- ❌ Halide `saturating_cast` in the kernel (per Gemini guidance — modular semantics throughout, saturation only at ARM post-Garner step).

---

## 7. Anti-patterns (hard limits)

1. **DO NOT use `Halide::Int(64)` for Barrett intermediate without Stage-2 SASS verification.** If Int(64) lowers correctly, great; if it panics, falls back to scalar, or produces wrong codegen, **fall back to explicit `mul_hi + mul_lo` decomposition per `reference-nvcc-paired-register-bug`**.
2. **DO NOT use `Halide::%` operator anywhere in the kernel.** Use explicit Barrett.
3. **DO NOT use `Halide::saturating_cast` in the kernel.** Modular semantics throughout the Halide kernel; saturation only on ARM post-Garner if the K-output is post-shifted to match Sprint J's i16 output.
4. **DO NOT bundle Halide generator changes with dispatcher code** (per `feedback-bundled-changeset-root-cause-ambiguity` — three separate commits minimum: gen / skel-infra / dispatcher).
5. **DO NOT silently widen the math identity gate.** Bit-exact in the no-saturation regime or surface upstream. The conditional formulation (Sprint J accumulator within ±INT32_MAX) must be asserted.
6. **DO NOT claim speedup ≥ 1.5× if measured < 1.5×.** Report the actual number; document the gap.
7. **DO NOT skip the Stage 2 SASS check.** The Int(64) lowering is the single biggest risk; deferring the check until the kernel is wired into the skel + bin would surface failure expensively.

---

## 8. Risks + responses

**R1: Halide Int(64) lowering panics or emits non-vectorized SASS.** Stage 2 catches this. Fallback path: explicit `mul_hi + mul_lo` decomposition using i32 halves + `vmpyih`. Adds ~80 LOC. Documented in plan §2.3.

**R2: HVX `vmem` alignment requirements on the 4-byte i32 output buffer.** Sprint F.1's `set_host_alignment(128)` finding stands. Output buffer is `batch × h_dim × 4 bytes` — for B=8 H=128 = 4096 bytes, 128-aligned. Fine for tile sizes; document if non-128-multiple sizes are tested.

**R3: cdsp dual-vector-context dispatch doesn't extend to the heavier Int(64) Barrett kernel.** K v0.alpha showed clean parallelism on the saturating kernel. If the Int(64) kernel has different L1 / VTCM / DDR pressure, the speedup could degrade. **Mitigation:** report measured speedup honestly; if <1.5×, document which resource pressured.

**R4: Sprint J's accumulator saturates on Sprint I+J's activation patterns.** The no-saturation regime is the math identity precondition. If the instrumented scalar reference reports `|acc| > INT32_MAX` at any test cell, identity is vacuous — file as K.3 follow-on (need different activation patterns for the identity gate). Per `feedback-no-silent-gate-revisions`, this surfaces upstream rather than the gate being weakened.

**R5: Garner `q1_inv_mod_q_2` arithmetic.** Single Rust computation at startup; trivial; tested by the i128 reference cross-check.

**R6: 100-iter leak across dual skels.** Drop chain order: CrtDispatcher drops both sessions; each session's `Drop` closes its handle. Sprint A precedent for clean handle teardown.

---

## 9. Effort estimate

| Stage | LOC estimate | Time estimate |
|---|---|---|
| 1 (plan) | 250 (this file) | ~30 min |
| 2 (Halide gen + SASS check) | 100-180 (depending on Int(64) vs decomposition) | 1-2 hours |
| 3 (skel infra) | 200 (CMake + IDL + handler skeletons, mostly copy-paste) | 1 hour |
| 4 (real kernel binding) | 50 (mostly link + push verify) | 30 min |
| 5 (dispatcher + ref + bin) | 250 | 2 hours |
| 6 (on-device verify) | 30 (verbatim output capture) | 30 min |
| 7 (closure) | 100 | 30 min |
| **Total** | **~880-960 LOC** | **6-8 hours** |

Above operator's 500-600 LOC estimate. Drivers:
- Two NEW skel directories (CMake + IDL + handler clones) = ~200 LOC of mostly boilerplate.
- Arbitrary-precision i128 reference + edge-case tests = ~80 LOC.
- The Halide kernel itself may be 100-180 depending on the Int(64) vs decomposition choice.

This is the honest scope; if it exceeds operator's expectation, surface in Stage 1 closure before Stage 2 begins.

---

## 10. What this sprint does NOT prove

- **Full FFN end-to-end correctness.** K v0.beta is single matmul mod-q. Full FFN (matmul-1 → clamp → matmul-2 → sat) under CRT split is K.3+.
- **CRT speedup scales to larger shapes.** K v0.alpha measured at B=8 D=H=128. K v0.beta will measure at the same shape for direct comparability; multi-shape sweep is K.4.
- **CRT split is the optimal architecture vs alternatives.** It validates Trick #1 specifically. Alternatives (Trick #2: NPU offload, Trick #4: spinor-block KV) are separate sprints.
- **Production daemon integration.** Sprint J.5 remains the AppState wiring sprint; K v0.beta produces a smoke binary, not daemon code.
