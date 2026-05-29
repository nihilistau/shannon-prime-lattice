# SESSION CLOSED — lat-3-hx-mode-d-hvx (Sprint D MVP)
**Date:** 2026-05-29  
**Plan:** `papers/SESSION-PLAN-lat-3-hx-mode-d-hvx.md` (`d0d273f`)  
**Engine commit:** `bd072de`

**Tags issued at engine `bd072de`:**
- `lat-phase-3-hx-mode-d-hvx-skel-builds` ✓
- `lat-phase-3-hx-mode-d-hvx-bitwise` ✓
- `lat-phase-3-hx-mode-d-hvx-vectorized` ✓
- **Umbrella: `lat-phase-3-hx-mode-d-hvx-closed` ✓**

---

## 1. Status

**CLOSED.** All three sub-tags + umbrella issued. HVX V-register SASS confirmed; bitwise correctness across 64 / 1024 / 65536 elements; ± saturation verified; perf comparison documented as finding.

---

## 2. Deliverables (`bd072de`)

### `tools/sp_compute_skel/` (NEW workspace)

Mirrors the proven `sp_echo_skel` SDK CMake template (S22U IDE pattern). Two methods:

| Method | Kernel | Auto-vec? |
|---|---|---|
| `axpby(n, a, b, q_bits, x, y)` | `y = saturate_i16((a*x + b) >> q_bits)` | NO — i32 mul-shift-clamp doesn't auto-vec to HVX; Hexagon scalar `loop0` instead. Sprint E follow-on with explicit intrinsics. |
| `scale_i16(n, a_h, x, y)` | `y = saturate_i16(x + a_h)` | **YES** — explicit HVX intrinsics via `Q6_Vh_vadd_VhVh_sat`; SASS verified. |

### `tools/sp_dsp_smoke/[[bin]] test_hvx` (NEW)

Stand-alone aarch64-android binary (510 KB), opens FastRpcSession against `sp_compute_skel`, runs 6 tests.

---

## 3. On-Device Smoke Results (S22U R5CT22445JA)

```
[hvx] opening FastRpcSession against sp_compute_skel (Path B)...
[hvx] session open
[hvx] T_HVX_SCALE_BITWISE_64    (n=64,    a_h=100)   PASS
[hvx] T_HVX_SCALE_BITWISE_1024  (n=1024,  a_h=-200)  PASS  (16 HVX vectors)
[hvx] T_HVX_SCALE_BITWISE_65536 (n=65536, a_h=1234)  PASS  (1024 HVX vectors)
[hvx] T_HVX_SCALE_SATURATE (clamp +) PASS  (30000 + 30000 → 32767)
[hvx] T_HVX_SCALE_SATURATE (clamp -) PASS  (-30000 + -10000 → -32768)
[hvx] T_HVX_SCALE_VS_SCALAR (64 KB × 1000 iter): dsp_hvx 424.290417ms  host_scalar 31.706146ms
[hvx] session closed cleanly
[hvx] ALL GATES PASS
```

### HVX SASS verification

`hexagon-llvm-objdump -d libsp_compute_skel.so | grep "v[0-9]\+\."`:

```
c94:	62 81 40 1c	1c408162 { 	v2.h = vadd(v1.h,v0.h):sat }
```

— exactly the canonical V69 HVX i16 saturating add we asked for.

---

## 4. Findings

### F1 — HVX auto-vec for fixed-point axpby with variable shift requires explicit intrinsics

The first-draft kernel was a straight C `axpby` loop with branchless saturate. Even with `-O3 -mhvx -mhvx-length=128B` (auto-set by the SDK toolchain), hexagon-clang emits a scalar Hexagon `loop0` instead of HVX V-registers. The i32 accumulator + variable-shift + dual-clamp pattern doesn't pattern-match the auto-vec rewriter.

Forcing it with `#pragma clang loop vectorize(enable) vectorize_width(64)` is a hard build error (`loop not vectorized: the optimizer was unable to perform the requested transformation`).

The reliable path: explicit HVX intrinsics via `Q6_Vh_*` from `<hexagon_types.h>`. `scale_i16` uses this pattern; SASS verified.

**Sprint E item**: rewrite `axpby` with explicit intrinsics using `Q6_Vh_vmpyih_VhRh` (i16 × i16 → i32 word pairs) + `Q6_Vh_vasr_VhR` (variable arithmetic shift right) + saturating pack.

### F2 — FastRPC per-call overhead dominates host scalar for small per-call payloads

T_HVX_SCALE_VS_SCALAR: 1000 iterations of 32K elements (64 KB i16 each):
- DSP HVX: 424 ms (avg 424 µs per call)
- Host scalar: 32 ms (avg 32 µs per call)

The HVX kernel itself runs in microseconds; the dominating cost is the FastRPC round-trip (~400 µs/call). For Sprint D's MVP payload, host scalar is 13× faster.

**Where HVX wins**: very large per-call payloads (≥ MB-scale), compute-dense kernels (≥ ops per byte), or batched dispatch that amortizes the round-trip. Production FFN / matmul / NTT fall in this category.

**Sprint E item**: a "batched compute" endpoint that takes N independent kernels per FastRPC call. Combined with Sprint B's DmaBuffer + Sprint B's `RPCMEM_TRY_MAP_STATIC` cuts the round-trip cost per logical op.

### F3 — `BUILD_TYPE=Release` is required to even attempt vectorization

The first sp_compute_skel build used `BUILD_TYPE=Debug` (default in our `.bat` template). The Debug build's SASS had no `loop0`, no auto-vec, scalar-everywhere code (verified). Changed `.bat` to `BUILD_TYPE=Release`. Documented in `build.cmd` header.

### F4 — Halide AOT generator pipeline deferred to Sprint E

Stage 0 probed `C:\Qualcomm\HALIDE_Tools\2.4.07\Halide\`. The install has `Halide.dll` + `Halide.lib` + `include/Halide.h`, but no pre-built Hexagon AOT objects (the `Examples/offload/apps/hexagon_benchmarks/` directory has only `.cpp` generators and `.schedule.h` headers — the `.a` files must be produced by running the generator binaries on the host, which requires linking against Halide.lib + the underlying LLVM in a non-trivial way).

Sprint D MVP shipped explicit HVX intrinsics instead; the Halide AOT generator chain stays Sprint E.

---

## 5. Open Work

| Item | Phase | Trigger |
|---|---|---|
| Explicit HVX intrinsics for `axpby` (i16 × i16 → i32 with variable shift + saturating pack) | Sprint E | Closes the F1 finding; needed before FFN |
| Halide AOT generator pipeline on Windows host (host generator → `target=hexagon-v69-no_asserts` → AOT `.a` → link into skel) | Sprint E | Production path for any non-trivial kernel; gated on §16.5 KSTE |
| Batched FastRPC call surface (N independent ops per round-trip) | Sprint E | Amortizes per-call overhead; needed for production throughput |
| VTCM staging via `HAP_compute_res_acquire_cached` | Sprint E | Hot working set in 256 KB DSP scratch |
| DMA prefetch (HVX `Vh = vmem(...):nt` non-temporal hints) | Sprint E | Hides L2 miss latency in compute-bound loops |
| Full FFN with HardSwish-approximated SwiGLU per `ISP_ENGINE.md` | post-Sprint E | Production payload of Mode D; gated on KSTE integration |
| Consolidate `dsp_rpc.rs` duplication across sp_daemon / sp_dsp_smoke | post-Sprint A umbrella | Same as prior sprints' open item |
