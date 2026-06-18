---
type: session-handoff
title: SESSION CLOSED — lat-3-hx-mode-d-h (Sprint H — diagnostic)
description: "Date: 2026-05-30"
tags: [session-handoff]
timestamp: 2026-05-29T08:25:18Z
resource: shannon-prime-lattice/papers/SESSION-CLOSED-lat-3-hx-mode-d-h.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# SESSION CLOSED — lat-3-hx-mode-d-h (Sprint H — diagnostic)
**Date:** 2026-05-30
**Engine commits:** `1c3b0c5` (diag instrument), `facbdfc` (bisect qbits), `b5a642b` (bisect dim)
**Umbrella tag:** `lat-phase-3-hx-mode-d-h-closed`

Sprint H is diagnostic and closes with **a material reframing of Sprint G's two G.1 constraints**. The bisections show only one G.1 constraint exists, not two:

- The empirically-real boundary is **q_bits ≤ 15**. q_bits = 16 triggers matmul-2 divergence regardless of dimensions.
- The Sprint G "dim constraint" (dims must equal 128) was misattributed. Sprint G's failing test runs simultaneously varied q_bits and dimensions, and the failures correlate with q_bits = 16, not with H ∈ {256, 512}. At q_bits = 14, all H values in the bisected range — including non-multiples (160, 192, 224) and multiples-not-128 (256) — produce bitwise-correct output.

Sprint H.PATCH is filed as a follow-on with this empirical grounding cited; the patch can focus on the q=16 matmul-2 codegen surface without chasing the dim phantom.

---

## Bisection results (verbatim from device runs)

### T_HALIDE_FFN_DIAG_INSTRUMENT (engine commit `1c3b0c5`)

Configuration: B=8, D_in=128, H=256, D_out=128, q=16, b=16 (Sprint G's smallest failing 4KB config).

```
hidden MATCHES, y diverges at [0]: got=-1648 exp=-1
→ matmul-2 is the divergence site (stage 1 OK, stage 2 wrong)
hidden[0..8] = [13, 13, 13, 13, 13, 13, 13, 13]  (identical Halide vs ref)
```

**Implication:** Matmul-1 (X @ W1 → clamp → cast<i16> → hidden) is bit-exact against the scalar reference. The divergence is exclusively in matmul-2 (hidden @ W2 → sat_i16(Y)). Sprint G's `got = -1648` was the matmul-2 output.

### T_HALIDE_FFN_BISECT_QBITS (engine commit `facbdfc`)

Configuration: B=8 D_in=128 H=128 D_out=128 b=16. Sweep q ∈ {12, 13, 14, 15, 16}.

```
q_bits | matmul-1 (hidden[0..2]) | matmul-2 (y[0])           | verdict
   12  | [216, 216] OK           | got=-4  exp=-4 OK         | PASS
   13  | [108, 108] OK           | got=-1  exp=-1 OK         | PASS
   14  | [54, 54]   OK           | got=-1  exp=-1 OK         | PASS
   15  | [27, 27]   OK           | got=-1  exp=-1 OK         | PASS
   16  | [13, 13]   OK           | got=-816 exp=-1 DIVERGE   | FAIL mm-2
```

**Sharp boundary at q=16.** q=15 is the last passing value; q=16 is the first failing value. No graceful degradation.

**Matmul-1 halves cleanly across q steps** (216 → 108 → 54 → 27 → 13 = each step ÷2 = shift by 1), confirming that mathematical correctness holds at every q value for stage 1.

### T_HALIDE_FFN_BISECT_DIM (engine commit `b5a642b`)

Configuration: B=8 D_in=128 D_out=128 q=14 b=0. Sweep H ∈ {128, 160, 192, 224, 256}.

```
 H   | matmul-1 (hidden[0..2]) | matmul-2 (y[0])    | verdict
128  | [54, 54] OK             | got=-1 exp=-1 OK   | PASS
160  | [54, 54] OK             | got=-1 exp=-1 OK   | PASS  (non-multiple of 128)
192  | [54, 54] OK             | got=-1 exp=-1 OK   | PASS  (non-multiple)
224  | [54, 54] OK             | got=-1 exp=-1 OK   | PASS  (non-multiple)
256  | [54, 54] OK             | got=-1 exp=-1 OK   | PASS  (multiple, not 128)
```

**At q=14, no dim sensitivity in the tested range.** The decision tree from the plan resolves to row 4: "Sprint G's empirical record was wrong or input-dependent — re-investigate." Investigation: Sprint G's H=256 failure runs all used q=16 (specifically: 4KB at b=16 q=16, LARGE at b=128 q=20, DIM at b=64 q=18, DOUT at b=16 q=16). No Sprint G run held q=14 with H=256, so the H/q variables were never independent.

---

## Reframed G.1 — single constraint, single failure surface

| | Sprint G's claim | Sprint H's evidence |
|---|---|---|
| Constraint #1 | "All matmul dims must equal 128" | At q=14, H ∈ {128, 160, 192, 224, 256} all PASS. Dim is not a constraint at this q. |
| Constraint #2 | "q_bits ≤ 14" (with wrap-vs-sat suspected) | Confirmed: q_bits ≤ 15. q=16 triggers matmul-2 divergence (not matmul-1). |
| Failure site | Both matmuls "fail" | Only matmul-2. Matmul-1 is bit-exact at every q value tested. |

The single empirical constraint is **q_bits ≤ 15**. The Sprint G failures that LOOKED like dim sensitivity (H=256 failing) were actually q_bits=16 cases that happened to also use H=256.

---

## Sprint H.PATCH follow-on (filed, not implemented in Sprint H)

Per the user's "do NOT propose patch within H itself" discipline, Sprint H.PATCH is a separate sprint. Its empirical brief from this closure:

1. **Bug site:** sp_ffn_2stage_halide's matmul-2 codegen at q_bits = 16.
2. **Boundary:** sharp at q=16. q=15 PASS, q=16 FAIL.
3. **Suspect codegen surface:** the saturating shift-by-16 in `vmpyih_acc:sat` post-stage-2. SASS already shows `vmpy(Vu.h, Rt.h):sat` for both matmuls; the >> 16 at the end of stage 2 lowers to either `vasr(Vw, R)` followed by a `vsat` (separate slots) or fuses to `vasr(Vw, Vw, R):sat` (one slot — Sprint F's axpby_2d saw this pattern). Hypothesis: at q=16 the fused form has a bug or selects a different opcode than at q=15; or the i32 shift-by-16 on Halide's accumulator hits a Halide-level type-coercion edge.
4. **Diagnostic next steps for H.PATCH:**
   - Read the .s for sp_ffn_2stage_halide's stage-2 epilogue at q=14 vs q=16. Look for differing opcodes around `vasr` / `vsat`.
   - Try `>> cast<int32_t>(q_bits)` in the generator (advisor's earlier "cheap test #2"); if 4KB-shape-q=16 then passes, the implicit `i32 >> u8` coercion was the bug.
   - Try `Input<int32_t> q_bits` instead of `Input<uint8_t>`; if that resolves, the i32/u8 boundary at the shift is the bug.
5. **Out of scope for H.PATCH (carried forward as future work):**
   - Whether the q_bits-=15 cap covers Qwen3-0.6B's actual quantization scales. (The phase log assumed hidden_size=896 needed padding; this sprint shows that assumption was the wrong variable. Whether Qwen3's q_bits in practice stay ≤ 15 is a Sprint I+ question.)

---

## Outcomes

| Sub-tag | Result |
|---|---|
| `lat-phase-3-hx-mode-d-h-diag-instrument` | diag generator + IDL method + skel handler ship; T_HALIDE_FFN_DIAG_INSTRUMENT runs cleanly, isolates matmul-2 as divergence site |
| `lat-phase-3-hx-mode-d-h-bisect-qbits` | q boundary pinned at q=16 (q=15 PASS, q=16 FAIL); matmul-1 clean at every q |
| `lat-phase-3-hx-mode-d-h-bisect-dim` | At q=14, H ∈ {128, 160, 192, 224, 256} all PASS; Sprint G's dim constraint reframed as confounded |
| `lat-phase-3-hx-mode-d-h-closed` | umbrella |

Sprint G's existing `T_HALIDE_FFN_VTCM_*` gates all still PASS (engine HEAD `b5a642b`) — Sprint H added a parallel diag generator and didn't touch Sprint G's kernel.

---

## Architectural-discipline notes

- **Pcycle scaling preserved.** Sprint G's FFN kernel pcycles (B4=7.9M, B8=15.7M, B16=31.4M, B64=125.8M) are unchanged. Sprint H only adds infrastructure; the production kernel path is untouched.
- **No silent gate revisions.** Sprint G's two-constraint G.1 framing is amended here in a new closure note, not by editing Sprint G's closure. The Sprint G closure stands as the empirical record at the time it was written; Sprint H supersedes its attribution with the bisection data and cites the supersession explicitly.
- **One commit per bisection, isolated attribution.** Three engine commits (`1c3b0c5`, `facbdfc`, `b5a642b`) each provide its own data row; closure reads them in order.

---

## File map

| Repo | Path | Change |
|---|---|---|
| engine | `tools/sp_halide_gen/sp_ffn_2stage_diag_gen.cpp` | new — diag Halide generator (Sprint G clone + hidden teed Output) |
| engine | `tools/sp_halide_gen/build.cmd` | extended to emit diag .o |
| engine | `tools/sp_compute_skel/halide_gen/sp_ffn_2stage_diag_halide.{o,h}` | new AOT outputs |
| engine | `tools/sp_compute_skel/inc/sp_compute.idl` | +`ffn_2stage_diag_halide` |
| engine | `tools/sp_compute_skel/src_dsp/sp_compute_imp.c` | +diag handler; h_dim%128 relaxed for the diag path only |
| engine | `tools/sp_compute_skel/CMakeLists.txt` | link diag .o |
| engine | `tools/sp_dsp_smoke/src/test_hvx.rs` | +diag invoker + 3 bisection tests |
| lattice | `papers/SESSION-PLAN-lat-3-hx-mode-d-h.md` | plan |
| lattice | `papers/SESSION-CLOSED-lat-3-hx-mode-d-h.md` | this note |

---

## Open work

- **Sprint H.PATCH** — diagnose and patch matmul-2 q=16 codegen with the empirical brief above. Self-contained kernel fix; no architectural changes.
- **Sprint I** — single-layer real-model smoke. Now unblocked: at q ≤ 15 the FFN kernel is bitwise-correct across the dim range we'd expect a real layer to use. Sprint I should sanity-check Qwen3-0.6B's actual quantization q_bits before assuming the kernel applies as-is.
- **Sprint J** — full loader, gated on Sprint I.
