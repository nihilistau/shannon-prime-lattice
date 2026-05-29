# SESSION CLOSED — lat-3-hx-mode-k-beta (PARTIAL via 2.5b-C deferral)
**Date:** 2026-05-30
**Status:** **PARTIAL** — Stage 2.5a (scalar Barrett foundation) PASS; Stages 2.5b through 7 deferred to a focused HVX-engineering sprint per operator-authorized 2.5b-C path.
**Engine commits:**
- `39e286c` (Stage 2 probe — Halide Int(64) panics)
- `5b446e9` (SpErr::Other(String) for diagnostic loader errors)
- `41963ac` (Stage 2.5a scalar Barrett + T_BARRETT_SCALAR_ORACLE_C_SCALAR PASS)
- `cdaaf15` (K v0.alpha verbatim output — context reference)
**Lattice commits:**
- `2da3eed` (Sprint K v0.beta plan)
- `faf13dd` (Stage 2.5 plan amendment with PTX→HVX intrinsic mapping)
- this closure

---

## Status summary

K v0.beta scope as planned: emit two Halide skels (`libsp_compute_skel_q{1,2}.so`) with Barrett-reduction modular matmul, dispatch via the K v0.alpha `DualDispatch` substrate, Garner-recombine on ARM, 4 gates including math identity vs Sprint J and dual-dispatch speedup ≥ 1.5×.

What landed:
- ✅ **Stage 1** — plan committed at lattice `2da3eed`.
- ✅ **Stage 2** — Halide Int(64) probe SASS check. Halide rejects `int64x32` for hvx_v65/v68/v69 with HexagonOptimize.cpp:163 internal panic. F-B (hand-rolled HVX intrinsics) authorized.
- ✅ **Stage 2.5 plan amendment** — PTX→HVX intrinsic mapping documented at lattice `faf13dd`; scalar (2.5a) / HVX-vector (2.5b) split with diagnostic-isolation discipline.
- ✅ **Stage 2.5a** — scalar Barrett primitives in `sp_compute_crt_imp.c`; `barrett_oracle` IDL method (method 10); Rust scalar reference + harness; **T_BARRETT_SCALAR_ORACLE_C_SCALAR PASS** for both primes (1024 vectors each, per-element bitwise).

What deferred:
- ⏸️ **Stage 2.5b** — HVX vector Barrett intrinsic chain. Empirical scope inflation discovered during the PTX→HVX mapping work: HVX lacks single-instruction i32×i32→i64 widening, requiring u15-half-decomposition + 4× `Q6_Wuw_vmpy_VuhVuh` sub-products + multi-precision combine per Barrett step. Honest re-estimate: 250-350 LOC + 3-5 hours of SASS-debug cycles, well above the original Stage 2.5 envelope. Filed as a focused follow-on sprint below.
- ⏸️ **Stages 3-7** — two-skel build, CrtDispatcher with dual sessions, Garner recombine, math identity gate, dual-dispatch speedup gate, leak gate, closure. All gated on Stage 2.5b's HVX vector Barrett.

The closure is PARTIAL because the 4 substantive K v0.beta gates (`M_K_beta_MATH_IDENTITY`, `M_K_beta_BARRETT_CORRECTNESS`, `M_K_beta_DUAL_DISPATCH_SPEEDUP`, `M_K_beta_LEAK_FREE`) are not run. Per `feedback-no-silent-gate-revisions`, the deferral is explicit, not silent.

---

## Findings

### 1. Halide HVX i64 limitation (verified empirically, Stage 2)

```
Unhandled exception: Internal Error at
  C:\bots\prod-worker\halide-24-win\src\halide\src\HexagonOptimize.cpp:163
  triggered by user code at : Unsupported HVX type: int64x32 for target hvx_v65
```

Halide's HVX backend has no vector i64 type for v65/v68/v69. The `Halide::Int(64)` intermediate path closes; explicit decomposition is the only Halide-resident path forward. F-A (Halide Int(32) decomposition) was NOT attempted in this sprint because (1) no precedent in codebase, (2) high risk of secondary lowering panics on intermediate Int(32) ops, (3) F-B (hand-rolled HVX intrinsics) has Sprint E precedent as proven counter-example.

Future investigation worth filing (operator-flagged): whether newer Halide versions (post our pinned 24.x) added Int(64) HVX lowering. If yes, a future sprint could replace the hand-rolled C kernel with Halide for maintainability — but only after a T_BARRETT_SCALAR_ORACLE_HVX-equivalent verification gates the Halide path identically.

### 2. PTX→HVX intrinsic mapping table (documented in plan amendment)

Cited engine `63d7e2d:src/backends/cuda/ptx_ntt.cuh`. Critical observation surfaced: each PTX `mul.{lo,hi}.u32` (5 such pairs in `ptx_modmul_q1`) is a single device instruction; the HVX equivalent requires ~6 vector ops via u15-half decomposition + paired-multiply + combine. **Per-modmul cost moves from ~20 PTX instructions to ~80-100 HVX vector ops.** The Stage 2.5b sprint scope reflects this.

### 3. Stage 2.5a scalar Barrett math is sound

Engine commit `41963ac` ships:
- `sp_barrett_reduce32_scalar(x: u64, q: u32, mu: u32) -> u32` — algorithm byte-for-byte matches engine `63d7e2d:ptx_ntt.cuh::barrett_reduce32_ref` (qhat = ((x>>29)*mu)>>31; r = x - qhat*q; ≤2 conditional subtracts).
- `sp_compute_barrett_oracle` IDL method (method 10) drives N (a, b) u32 pairs through scalar mod-mul.
- 1024 vectors × 2 primes (q_1 = 1073738753, q_2 = 1073732609) verified per-element bitwise vs Rust scalar reference.
- Worst-case `(q-2, q-8)` returns 16 for both primes (since `(-2)*(-8) mod q = 16` independent of q), confirming the algorithm's modular semantics.

This foundation primitive is the basis for any HVX vectorization path — once 2.5b lands, the HVX result vector can be cross-verified against the scalar primitive on identical inputs.

### 4. Operator's `(int32 *acc, int n_elements)` signature interpretation

The original Stage 2.5 spec signature suggested canonicalize-only Barrett (input already in i32 range). For our 30-bit primes with single-multiply use case, the multiply produces i60 products that don't fit in i32, so full Barrett requires i64 widening multiply — the source of the Stage 2.5b scope inflation. The simpler "canonicalize i32 from [0, K*q) to [0, q)" path applies only if the multiply is done elsewhere AND the result fits in i32. This nuance documented for the Stage 2.5b sprint plan.

---

## Architectural-discipline notes

- **No silent gate revisions.** K v0.beta closes as PARTIAL with explicit deferral rather than weakening any gate. Stage 2.5a's gate is the one PASS-ing gate; the other four are explicitly not-run.
- **No production skel changes.** `sp_compute_skel/src_dsp/sp_compute_imp.c` (Sprint G/H/I/J kernel handler) is untouched. The new `sp_compute_crt_imp.c` is an additive compilation unit; Sprint J's `sp_full_load_smoke` and Sprint K v0.alpha's `sp_dual_dispatch_smoke` still pass on the same skel binary.
- **No K v0.alpha changes.** `sp_dual_dispatch.rs` is read-only; Stage 2.5b will consume it once dispatched.
- **No new memory entries inside the sprint.** The `reference-halide-hvx-int64-limitation` memory entry the operator pre-authorized will be written as a separate post-closure commit alongside this closure (per operator instruction).
- **5 isolated engine commits** preserved per `feedback-bundled-changeset-root-cause-ambiguity`:
  - Plan + amendment in lattice
  - Stage 2 probe artifact (`39e286c`)
  - SpErr::Other separate (`5b446e9`)
  - Stage 2.5a deliverable (`41963ac`)

---

## Sub-tags (what closes here vs what waits)

| Sub-tag | Status | Engine commit |
|---|---|---|
| `lat-phase-13-6-k-beta-barrett-scalar-c` | **CLOSED** — C scalar Barrett primitive correct | `41963ac` |
| `lat-phase-13-6-k-beta-barrett-scalar-oracle` | **CLOSED** — T_BARRETT_SCALAR_ORACLE_C_SCALAR PASS | `41963ac` |
| `lat-phase-13-6-k-beta-barrett-hvx-vector` | DEFERRED — Stage 2.5b sprint | (n/a) |
| `lat-phase-13-6-k-beta-halide-dual-prime` | DEFERRED — Stage 3+ | (n/a) |
| `lat-phase-13-6-k-beta-skel-build` | DEFERRED | (n/a) |
| `lat-phase-13-6-k-beta-dispatcher` | DEFERRED | (n/a) |
| `lat-phase-13-6-k-beta-garner-recombine` | DEFERRED | (n/a) |
| `lat-phase-13-6-k-beta-math-identity` | DEFERRED — needs Stages 2.5b through 6 | (n/a) |
| `lat-phase-13-6-k-beta-barrett-correctness` | DEFERRED | (n/a) |
| `lat-phase-13-6-k-beta-parallelism-measured` | DEFERRED | (n/a) |
| `lat-phase-13-6-k-beta-leak-free` | DEFERRED | (n/a) |
| `lat-phase-13-6-k-beta-partial` | **CLOSED** — explicit partial-closure marker | `41963ac` |

No `*-closed` umbrella tag — that fires when 2.5b → 7 also close.

---

## K v0.beta-stage-2-5b — explicit follow-on sprint filing

**Scope:** Implement HVX vector Barrett intrinsic chain in `sp_compute_crt_imp.c` alongside the existing scalar primitive. Use the u15-half decomposition pattern per the plan amendment §1 PTX→HVX intrinsic mapping. SASS-verify each multiplication sub-stage emits clean vector codegen (no scalar fallback). Pass `T_BARRETT_SCALAR_ORACLE_HVX` (mode=1 in `barrett_oracle` IDL method) — same 1024-vector test harness as 2.5a, bitwise per-element vs Rust scalar reference.

**Prerequisites:**
- K v0.beta-2.5a scalar primitive (already shipped at engine `41963ac`).
- PTX→HVX intrinsic mapping table (already shipped at lattice `faf13dd`).
- Engine `63d7e2d:src/backends/cuda/ptx_ntt.cuh` PTX reference (existing).

**Estimated scope:** ~250-350 LOC C HVX intrinsic chain; ~3-5 hours including:
- Per-sub-stage SASS verification cycle (probe → SASS check → adjust → re-probe);
- May surface additional HVX type panics analogous to the Halide Int(64) finding; mitigation = incremental SASS gates per sub-stage.

**Gate set (K v0.beta-2.5b dedicated):**
- `T_BARRETT_HVX_VECTOR_SASS_CLEAN` — SASS grep confirms `Q6_Wuw_vmpy_VuhVuh` (or equivalent u15-half decomposition), `Q6_Vw_vsub_VwVw`, `Q6_V_vmux_QVV` emitted; zero scalar Hexagon fallback in the Barrett path.
- `T_BARRETT_SCALAR_ORACLE_HVX` — vector Barrett ≡ Rust scalar reference per-element across the 1024 vectors per prime test population (same vectors as 2.5a).
- `T_BARRETT_HVX_PCYCLES` — per-vector kernel pcycle count; informational baseline for downstream K v0.beta Stage 3+ kernel performance estimates.

**Anti-pattern callout:** do NOT bundle K v0.beta-2.5b with K v0.beta Stages 3-7 (skel-clone + CrtDispatcher + Garner). If 2.5b's intrinsic chain is buggy, mixing it with downstream code makes attribution impossible. Pattern: 2.5b closes as its own sprint; THEN K v0.beta Stages 3-7 resume on the proven HVX primitive.

**Sub-tags (when 2.5b runs):**
- `lat-phase-13-6-k-beta-2-5b-hvx-sass-clean`
- `lat-phase-13-6-k-beta-2-5b-hvx-oracle-pass`
- `lat-phase-13-6-k-beta-2-5b-closed`

---

## K v0.beta-3-through-7 — gated on 2.5b

After K v0.beta-2.5b closes with HVX vector Barrett primitive proven:
- Stage 3: dual-skel infrastructure (`tools/sp_compute_skel_q1/`, `tools/sp_compute_skel_q2/`).
- Stage 4: wire Barrett-via-HVX into modular-matmul kernels in both skels; emit two `.o` files.
- Stage 5: `CrtDispatcher` (extends K v0.alpha's `DualDispatch`); ARM-side Garner recombine; arbitrary-precision i128 reference.
- Stage 6: on-device run, 4 gates.
- Stage 7: closure + tags.

This work proceeds in a successor sprint (call it K v0.beta-stage-3-onwards) once 2.5b ships.

---

## What this PARTIAL closure does NOT prove

- The manifesto Trick #1 modular-arithmetic CRT split. Math foundation is in place (scalar Barrett); HVX vector implementation pending.
- Dual-dispatch speedup on the modular kernel. K v0.alpha proved the dispatch substrate; the modular kernel hasn't been measured.
- Math identity vs Sprint J's saturating matmul. Needs Stages 3+ to produce CRT-recombined output to compare.

---

## What this PARTIAL closure DOES prove

- **Halide's HVX backend cannot vectorize Int(64) on this Halide version + target combo.** Definitive panic at codegen, not silent fallback. This is the load-bearing finding that re-shaped the K v0.beta path from "Halide-resident kernel" to "hand-rolled HVX intrinsics in C."
- **The PTX→HVX intrinsic mapping is documented** for any future agent who picks up the HVX Barrett work, including the load-bearing scope-inflation note around the missing single-instruction i32×i32→i64 widening.
- **Scalar Barrett math is empirically correct** on the cdsp scalar pipe — both primes, 1024 test vectors each, edge + worst-case + random coverage, per-element bitwise vs Rust reference. The foundation for ANY future modular-arithmetic kernel (Halide-vectorized OR hand-rolled HVX OR scalar-in-loop) on the cdsp.
