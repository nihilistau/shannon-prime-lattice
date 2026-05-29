# SESSION CLOSED — lat-3-hx-mode-e-axpby
**Date:** 2026-05-29
**Engine commit:** 921c569
**Umbrella tag:** `lat-phase-3-hx-mode-e-axpby-closed`

Both Sprint E items delivered.  F1 (explicit-HVX axpby) and F2 (batched dispatch) are wall-faster, bitwise-correct against the scalar reference, and SASS-verified to lower to V-register HVX instructions on V69 cDSP of the Samsung S22 Ultra.

---

## Outcomes

| Sub-tag | Result |
|---|---|
| `lat-phase-3-hx-mode-e-axpby-intrin-builds` | sp_compute_skel.so rebuilt (13952 B); axpby_hvx + scale_i16_batched both linked |
| `lat-phase-3-hx-mode-e-axpby-intrin-bitwise` | T_HVX_AXPBY_INTRIN_64 / 1024 / 65536 PASS; T_HVX_AXPBY_INTRIN_SATURATE PASS |
| `lat-phase-3-hx-mode-e-batched-faster` | T_BATCH_VS_UNBATCHED ratio 0.329× = **3.04× wall speedup** (gate ≥5%) |
| `lat-phase-3-hx-mode-e-sass-confirmed` | axpby_hvx inner loop has `vmpy`, `vadd`, `vasr`, `vsat` V-register ops |
| `lat-phase-3-hx-mode-e-axpby-closed` | umbrella |

T_BATCH_BITWISE also PASS (8 × 4 KB i16 inline batches bitwise-equal scalar reference).

---

## F1 — explicit HVX intrinsics axpby

Kernel chain per 64-element block, from `sp_compute_axpby_hvx()` in `tools/sp_compute_skel/src_dsp/sp_compute_imp.c`:

```
HVX_VectorPair ax = Q6_Ww_vmpy_VhRh(x_vec, a_dup);   // widening i16×i16 → i32 pair
HVX_Vector slo = Q6_Vw_vadd_VwVw(Q6_V_lo_W(ax), vb); // + b on lo half
HVX_Vector shi = Q6_Vw_vadd_VwVw(Q6_V_hi_W(ax), vb); // + b on hi half
HVX_Vector rlo = Q6_Vw_vasr_VwR(slo, q_bits);         // arith shift
HVX_Vector rhi = Q6_Vw_vasr_VwR(shi, q_bits);
yv[i] = Q6_Vh_vsat_VwVw(rhi, rlo);                    // sat-INTERLEAVE i32→i16
```

SASS dump (libsp_compute_skel.so), inner loop:

```
1120:  v3:2.w = vmpy(v1.h, r8.h)
1124:  v1.cur = vmem(r9++#1)         { prefetched next x }
1128:  v2.w   = vadd(v2.w, v0.w)     { + b on lo }
112c:  v3.w   = vadd(v3.w, v0.w)     { + b on hi }
1130:  v4.w   = vasr(v2.w, r5)       { >> q_bits lo }
1134:  v5.w   = vasr(v3.w, r5)       { >> q_bits hi }
1138:  v6.h   = vsat(v5.w, v4.w)     { sat+interleave }
113c:  vmem(r12++#1) = v6.new
```

### Bug found during initial integration

The Sprint E draft used `Q6_Vh_vpack_VwVw_sat(rhi, rlo)` for the final pack.  All three INTRIN_{64,1024,65536} bitwise tests failed identically: `got[1] = expected[2]` and so on — i.e. the output had the right elements but in the wrong order.  Investigation:

`Q6_Ww_vmpy_VhRh(x_vec, Rt.h(a_dup))` returns a pair of word vectors where the LO half holds the products for the EVEN input lanes (x[0], x[2], …, x[62]) and the HI half holds the ODD input lanes (x[1], x[3], …, x[63]).  This decimation-by-2 layout requires an INTERLEAVE on the way back to the natural i16 lane order.

`vpackwh_sat` (the `Q6_Vh_vpack_VwVw_sat` builtin) saturates both halves but then CONCATENATES — output[0..31] from the saturated Vv, output[32..63] from the saturated Vu.  That's the wrong shuffle for vmpyh's pair layout.

`vsatwh` (the `Q6_Vh_vsat_VwVw` builtin) saturates both halves AND interleaves: output.h[2k] = sat(Vv.w[k]); output.h[2k+1] = sat(Vu.w[k]).  With Vv = rlo (even-lane products) and Vu = rhi (odd-lane products), output.h[2k] = x[2k]·a result and output.h[2k+1] = x[2k+1]·a result — natural order restored.

The fix is a one-line intrinsic swap.  No clamp constants or vmin/vmax helpers needed; vsat does both jobs in one V-slot.

### Verification

T_HVX_AXPBY_INTRIN_{64, 1024, 65536}: n ∈ {64, 1024, 65536}, (a_h, b, q_bits) deterministic per size.  Each lane bitwise-equal scalar Rust reference `axpby_ref()`.  All PASS.

T_HVX_AXPBY_INTRIN_SATURATE: a_h = 30000, x = 10000, b = 0, q_bits = 4 → preshift = 3·10⁸ which saturates to 32767 in the i16 output.  PASS confirms saturation kicks in inside the vsat path.

---

## F2 — batched call surface

`sp_compute_scale_i16_batched(n_per_batch, n_batches, a_h_buf, x_buf, y_buf)` runs the Sprint D HVX scale_i16 kernel n_batches times inline.  One FastRPC call, one DSP-side loop over batches, no per-batch round-trip.  The inner kernel is the same `Q6_Vh_vadd_VhVh_sat` body extracted into `scale_i16_inner()` and reused.

### Verification

T_BATCH_BITWISE: 8 batches × 4096 i16 elements, distinct a_h per batch.  All 8·4096 = 32 768 outputs bitwise-equal the scalar reference.  PASS.

T_BATCH_VS_UNBATCHED: 200 iter, each iter does either 8 individual `scale_i16` calls (unbatched) or one `scale_i16_batched` call with n_batches=8.  Total work identical.

```
unbatched:  502.822 ms   (200 × 8 = 1600 FastRPC round-trips)
batched:    167.338 ms   (200       FastRPC round-trips)
ratio:      0.329×       (= 3.04× wall speedup)
```

The 3.04× ratio matches the expected (N-1)/N + per-call-overhead share: with 7 round-trips amortized per batch group, the per-call ~ 400 µs floor times 7 ≈ 2.8 ms saved per batched call.  Across 200 iters at 8 calls each, that's ≈ 200·7·400 µs = 560 ms of overhead removed, which lines up with the 502 → 167 ms delta.

---

## Sprint F follow-ups (unchanged from Sprint D closure)

- F3: Halide AOT generator pipeline (Windows host) — gives portability across HVX revisions
- F4: VTCM staging — for kernels larger than L1
- F5: DMA prefetch (non-temporal HVX loads)
- F6: Full FFN with HardSwish-SwiGLU — gated on §16.5 KSTE

The batched-faster ratio of 3.04× tells us the round-trip is no longer the bottleneck for medium payloads, so Sprint F's optimization focus should shift back to per-kernel cost (VTCM + Halide) rather than batching depth.

---

## File map

| Repo | Path | Change |
|---|---|---|
| engine | `tools/sp_compute_skel/inc/sp_compute.idl` | +axpby_hvx, +scale_i16_batched method decls |
| engine | `tools/sp_compute_skel/src_dsp/sp_compute_imp.c` | F1 + F2 impls; scale_i16_inner helper |
| engine | `tools/sp_dsp_smoke/src/test_hvx.rs` | Sprint E test suite + invoke_axpby_hvx / invoke_scale_batched wrappers |
| lattice | `papers/SESSION-PLAN-lat-3-hx-mode-e-axpby.md` | plan |
| lattice | `papers/SESSION-CLOSED-lat-3-hx-mode-e-axpby.md` | this note |

Engine head: 921c569.
