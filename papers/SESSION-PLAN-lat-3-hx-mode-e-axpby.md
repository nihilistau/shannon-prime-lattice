# SESSION PLAN — lat-3-hx-mode-e-axpby (Sprint E)
**Date:** 2026-05-29  
**Goal:** Close the two highest-priority Sprint E items from the Sprint D closure: F1 (explicit HVX intrinsics for fixed-point axpby) and F2 (batched FastRPC call surface). Halide AOT generator pipeline + VTCM + DMA prefetch + full FFN remain Sprint F.

---

## 1. Scope

| Item | Sprint E? |
|---|---|
| F1: Explicit HVX intrinsics for axpby (i16 × i16 → i32 acc + variable shift + saturating pack to i16) | **YES** |
| F2: Batched call surface (N kernel invocations per FastRPC round-trip) | **YES** |
| F4: Halide AOT generator pipeline (Windows host) | NO — Sprint F |
| VTCM staging | NO — Sprint F |
| DMA prefetch (non-temporal HVX loads) | NO — Sprint F |
| Full FFN with HardSwish-SwiGLU | NO — post-Sprint F (gated on §16.5 KSTE) |

Rationale: F1 + F2 are the load-bearing kernel + dispatch upgrades that compound — getting axpby to land on HVX and amortizing the FastRPC round-trip across many ops both improve the eventual FFN's wall regardless of whether it ships via Halide or hand-written intrinsics. Sprint F can then focus the Halide chain or VTCM tuning with a clear baseline to compare against.

---

## 2. F1 design — explicit HVX intrinsics axpby

### Kernel

```c
int sp_compute_axpby_hvx(int n, int a, int b, int q_bits,
                        const int16_t *x, int16_t *y)
{
    // Constraints (return -1 if violated):
    //   |a| ≤ 32767     (a must fit in i16 for HVX vmpy)
    //   0 ≤ q_bits ≤ 30
    //   n divisible by 64 (one HVX vector); scalar tail handles remainder
}
```

### HVX intrinsic chain per 64-element block

Per `<hexagon_types.h>` + `<hexagon_protos.h>` (V69):

1. **Load** — `HVX_Vector x_vec = *(const HVX_Vector*)(x + 64*i)`
2. **Widening multiply** — `Q6_Ww_vmpy_VhRh(x_vec, combine(a_h, a_h))` → HVX_VectorPair of i32 (low + high halves)
3. **Add b** — splat `b` to a word vector via `Q6_V_vsplat_R(b)`, then `Q6_Vw_vadd_VwVw` on both halves of the pair
4. **Variable shift right** — `Q6_Vw_vasr_VwR(vec, q_bits)` on both halves
5. **Saturating pack i32×2 → i16** — `Q6_Vh_vpack_VwVw_sat(hi, lo)` produces one HVX_Vector of i16
6. **Store** — `*(HVX_Vector*)(y + 64*i) = y_vec`

Verification:
- T_HVX_AXPBY_INTRIN_BITWISE — vs scalar Rust reference for n ∈ {64, 1024, 65536}
- T_HVX_AXPBY_INTRIN_SATURATE — overflow/underflow cases
- SASS dump shows `Vw = vmpy`, `Vw = vasr`, `Vh = vpack` instructions — gate for the "vectorized" sub-tag

### Fallback plan

If a specific intrinsic name doesn't exist in the SDK's `hexagon_protos.h` (the naming differs slightly across SDK versions), pivot to the closest valid intrinsic and document. The chain may compress (e.g., `vmpyhsrs` does mul + shift + round + sat in one) at the cost of losing the `b` addend; in that case fall back to a 2-pass kernel (mul-shift first, scalar add of b in a second pass) and surface as F2 in Sprint F.

---

## 3. F2 design — batched call surface

### IDL extension

```c
// Run sp_compute_scale_i16 N_BATCHES times in sequence inside one FastRPC call.
// Each batch's x_i / y_i / a_h_i parameters are packed into the input/output
// buffers.  Reduces FastRPC per-call overhead from ~400 µs/call to once per
// batch group.
long scale_i16_batched(in long n_per_batch,
                       in long n_batches,
                       in  sequence<octet> a_h_buf,   // n_batches × i16 LE
                       in  sequence<octet> x_buf,     // n_batches × n_per_batch × i16 LE
                       rout sequence<octet> y_buf);   // same shape as x_buf
```

### Kernel layout

```c
for (int b = 0; b < n_batches; b++) {
    int16_t a_h = a_h_arr[b];
    sp_compute_scale_i16_hvx_inner(n_per_batch,
                                   a_h,
                                   x + b * n_per_batch,
                                   y + b * n_per_batch);
}
```

`sp_compute_scale_i16_hvx_inner` is the HVX intrinsic body from Sprint D (Q6_Vh_vadd_VhVh_sat).

### Verification

- T_BATCH_BITWISE: 8 batches × 4 KB elements; bitwise == scalar reference
- T_BATCH_VS_UNBATCHED: same total work, batched (1 call) vs unbatched (8 calls); the batched path should be wall-faster by a margin matching the per-call FastRPC overhead × (N-1)/N.

---

## 4. Sub-tag taxonomy

- `lat-phase-3-hx-mode-e-axpby-intrin-builds` — sp_compute_skel rebuilds with new axpby_hvx + scale_i16_batched methods
- `lat-phase-3-hx-mode-e-axpby-intrin-bitwise` — T_HVX_AXPBY_INTRIN_* PASS
- `lat-phase-3-hx-mode-e-batched-faster` — T_BATCH_VS_UNBATCHED shows batched wall < unbatched wall
- `lat-phase-3-hx-mode-e-sass-confirmed` — hexagon-llvm-objdump shows `vmpy`, `vasr`, `vpack` in axpby_hvx SASS
- Umbrella: `lat-phase-3-hx-mode-e-axpby-closed`

---

## 5. Commit plan

| # | Content |
|---|---|
| 1 | Plan (this file) — lattice |
| 2 | sp_compute_skel: axpby_hvx + scale_i16_batched in imp.c, IDL update — engine |
| 3 | test_hvx: extend with T_HVX_AXPBY_INTRIN_* + T_BATCH_* — engine |
| 4 | Run on device, iterate — engine |
| 5 | Closure + tags — lattice |

---

## 6. Risk + fallback

**Intrinsic-name mismatch** — most likely failure mode. SDK versions name intrinsics slightly differently; my draft uses canonical Q6 names. If hexagon-clang errors on a specific name, the build log surfaces the exact missing symbol → look up the SDK's `hexagon_protos.h` for the closest, swap, document.

**Auto-vec re-fires accidentally** — if hexagon-clang's auto-vectorizer decides to fold the HVX_Vector kernel back to scalar, the SASS won't have V instructions. Mitigate by inspecting SASS after each build.

**Batched call hits AEE_EUNSUPPORTED** — per `reference-hexagon-working-setup`, exact-size match between rpcmem and IDL Len is mandatory. For batched, ensure `n_batches × n_per_batch × 2` bytes EXACTLY matches the IDL Len. Use the DmaBuffer API for safety (Sprint B's exact-size discipline).
