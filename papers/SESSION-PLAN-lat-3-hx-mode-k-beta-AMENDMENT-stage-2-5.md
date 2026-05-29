# SESSION PLAN AMENDMENT — lat-3-hx-mode-k-beta Stage 2.5
**Date:** 2026-05-30
**Trigger:** Stage 2 SASS check (engine `39e286c`) — Halide rejects Int(64) on HVX with internal panic. Operator authorized F-B (hand-rolled HVX intrinsic chain) and added T_BARRETT_SCALAR_ORACLE as the diagnostic-isolation gate prerequisite. This amendment specifies the Stage 2.5 design before code.

---

## 1. PTX → HVX intrinsic mapping table (operator canary requirement)

Reference: engine `63d7e2d:src/backends/cuda/ptx_ntt.cuh` — `ptx_modmul_q1`/`ptx_modmul_q2` Barrett implementations using PTX inline ASM. Each PTX op maps as follows:

| # | PTX op (CUDA, engine `63d7e2d`) | Function | HVX scalar (per-lane) | HVX vector intrinsic | Notes |
|---|---|---|---|---|---|
| 1 | `mul.lo.u32 lo, a, b` | low 32 of `a*b` | `(uint32_t)(a*b)` | **No single intrinsic.** Decompose: u15-halves + `Q6_Ww_vmpy_VhVh` (i16×i16→i32 pair) sub-products | Phase 2-CU.PTX got `mul.lo` for free; HVX needs ~4 vmpyh + combine. |
| 2 | `mul.hi.u32 hi, a, b` | high 32 of `a*b` | `(uint32_t)((u64)a*b >> 32)` | **No single intrinsic.** Same decomposition supplies `hi` from upper sub-products. | Same caveat. |
| 3 | `shf.r.wrap.b32 dst, lo, hi, 29` | `((hi:lo) >> 29) & 0xFFFFFFFF` | `(uint32_t)((((u64)hi<<32) \| lo) >> 29)` | `Q6_Vw_vor_VwVw(Q6_Vw_vlsr_VwR(lo, 29), Q6_Vw_vasl_VwR(hi, 3))` | bits 29..60 of (hi:lo). 32 - 29 = 3 left-shift on hi. |
| 4 | `mul.lo.u32 mlo, sh, mu` | low 32 of `sh*mu` | `(uint32_t)(sh*mu)` | Decomposition (mu < 2^31, sh < 2^31). | |
| 5 | `mul.hi.u32 mhi, sh, mu` | high 32 of `sh*mu` | `(uint32_t)((u64)sh*mu >> 32)` | Decomposition. | |
| 6 | `shf.r.wrap.b32 qhat, mlo, mhi, 31` | `((mhi:mlo) >> 31) & 0xFFFFFFFF` | scalar | Same vor+vlsr+vasl pattern. | qhat < 2^31. |
| 7 | `mul.lo.u32 qlo, qhat, q` | low 32 of `qhat*q` | scalar | Decomposition. | |
| 8 | `sub.u32 rlo, lo, qlo` | i32 modular subtract | `(uint32_t)(lo - qlo)` | `Q6_Vw_vsub_VwVw(lo, qlo)` | i32 wrap is OK because r_hi=0. |
| 9 | `if (r >= q) r -= q; (×2)` | canonicalize to [0, q) | scalar | `Q6_V_vmux_QVV(Q6_Q_vcmp_gt_VwVw(r, q-1), Q6_Vw_vsub_VwVw(r, q_splat), r)` (×2) | Two conditional subtracts per Barrett bound. |

**Critical observation:** Steps 1, 2, 4, 5, 7 (the four mul.lo + mul.hi pairs) are the load-bearing complexity. PTX has them as single instructions. HVX requires decomposition into u15-half sub-products, each via `Q6_Ww_vmpy_VhVh` (4 × i16 multiplies per i32×i32→i64 widening), plus shift+add combine. **Each i32×i32→i64 widening costs ~6 HVX vector ops** (4 vmpy + 2 combine).

---

## 2. Stage 2.5 split — scalar foundation + HVX layered

Per operator's discipline ("isolate intrinsic-correctness from kernel-integration"):

### Stage 2.5a — Scalar Barrett (foundation)

- **Rust scalar** in test harness: straightforward `u64` Barrett (~10 LOC).
- **C scalar** in `sp_compute_skel`: same algorithm using `uint64_t` (~20 LOC).
- **IDL method** `barrett_oracle_test(in q_idx, in a_buf, in b_buf, rout r_buf)` — drives N test vectors through the C scalar function.
- **Test harness** in `sp_dsp_smoke`: generates test vectors, calls IDL method, computes Rust scalar reference, bitwise-compares.
- **Gate:** `T_BARRETT_SCALAR_ORACLE_C_SCALAR` — Rust scalar ≡ C scalar Barrett, per-element bitwise.

This validates the Barrett MATHEMATICS independently of HVX codegen. If 2.5a fails, the math is wrong; if it passes, the math is right and any HVX failures are in the intrinsic translation.

### Stage 2.5b — HVX vector Barrett

- **C HVX vector** implementation: same algorithm using HVX intrinsics from the mapping table above (~100-150 LOC).
- **IDL method**: extend `barrett_oracle_test` with a 4th input parameter `mode: 0=scalar, 1=hvx` so the same test harness exercises both.
- **Gate:** `T_BARRETT_SCALAR_ORACLE_HVX` — Rust scalar ≡ C HVX vector Barrett, per-element bitwise. Same test vectors as 2.5a.
- **SASS verify:** `hexagon-llvm-objdump` confirms `Q6_Ww_vmpy_VhVh`, `Q6_Vw_vlsr_VwR`, `Q6_Vw_vsub_VwVw`, `Q6_V_vmux_QVV` emitted (not scalar fallback).

If 2.5b runs into intrinsic-availability or correctness issues, 2.5a is still shippable as the SCALAR foundation — the K v0.beta closure can document the HVX-vectorization status separately and file remaining work as 2.5c.

### Combined umbrella

Stage 2.5 closes ONLY when BOTH 2.5a and 2.5b PASS. If 2.5b lingers, Stage 2.5 closes as PARTIAL, the scalar foundation stands, and K v0.beta's downstream stages 3–7 are blocked pending vectorized Barrett.

---

## 3. Test vectors for `T_BARRETT_SCALAR_ORACLE_*`

Per operator's spec:

1. **Edge cases** (~12 vectors):
   - `(a=0, b=0)`, `(a=0, b=q-1)`, `(a=q-1, b=0)`, `(a=q-1, b=q-1)` × 2 primes + 1 random q ∈ {q_1, q_2, q_1−1}
2. **Random** (1000 vectors, deterministic seed): `(a = rand & (q-1), b = rand & (q-1))` for each prime
3. **Worst-case** (~10 vectors): `(a, b)` both close to `q-1` (forcing maximum Barrett q_est)

Total test population: ~1024 vectors per prime, 2048 total across both. Bitwise per-element match between Rust reference and skel result.

---

## 4. File deliverables (this amendment)

| File | Purpose | Stage |
|---|---|---|
| `papers/SESSION-PLAN-lat-3-hx-mode-k-beta-AMENDMENT-stage-2-5.md` | this amendment | (committing now) |
| `tools/sp_compute_skel/src_dsp/sp_compute_crt_imp.c` | C Barrett: scalar + (later) HVX intrinsic chain | 2.5a / 2.5b |
| `tools/sp_compute_skel/inc/sp_compute.idl` | +`barrett_oracle_test` method | 2.5a |
| `tools/sp_compute_skel/CMakeLists.txt` | link sp_compute_crt_imp.c | 2.5a |
| `tools/sp_dsp_smoke/src/sp_barrett_oracle.rs` | Rust scalar Barrett + test harness logic | 2.5a |
| `tools/sp_dsp_smoke/src/sp_barrett_oracle_smoke.rs` | bin: drive the oracle gate | 2.5a |
| `tools/sp_dsp_smoke/Cargo.toml` | +bin entry | 2.5a |

---

## 5. Anti-patterns (locked, additions to original plan)

11. **DO NOT skip Stage 2.5a in favor of jumping straight to HVX.** Per operator's discipline requirement: scalar oracle gate is the diagnostic isolator.
12. **DO NOT extend `sp_compute_skel`'s existing Halide-built kernel** with Barrett. Sprint G/H/I/J kernel stays untouched; Barrett primitive is a NEW C source file (`sp_compute_crt_imp.c`) compiled into the SAME skel binary alongside the existing handler.
13. **DO NOT silently widen `T_BARRETT_SCALAR_ORACLE_*` gates.** Bitwise per-element OR surface upstream. If even one of 1024+ vectors diverges, the test fails.
14. **DO NOT defer the PTX→HVX mapping documentation.** The table in §1 is the audit surface; future agents need it for the Halide-upgrade follow-on path.

---

## 6. Sub-tags

- `lat-phase-13-6-k-beta-barrett-scalar-c` — Stage 2.5a closed: scalar Barrett primitive correct
- `lat-phase-13-6-k-beta-barrett-scalar-oracle` — T_BARRETT_SCALAR_ORACLE_C_SCALAR PASS
- `lat-phase-13-6-k-beta-barrett-hvx-vector` — Stage 2.5b closed: HVX intrinsic chain SASS-verified + T_BARRETT_SCALAR_ORACLE_HVX PASS

Each fires independently; 2.5 umbrella waits for all three.

---

## 7. What this amendment does NOT change from the original plan

- 4 gate definitions (M_K_beta_MATH_IDENTITY, M_K_beta_BARRETT_CORRECTNESS, M_K_beta_DUAL_DISPATCH_SPEEDUP, M_K_beta_LEAK_FREE).
- Stage 3+ design (two skel directories, CrtDispatcher, Garner recombine on ARM).
- Out-of-scope list.
- All existing anti-patterns (1–10).
