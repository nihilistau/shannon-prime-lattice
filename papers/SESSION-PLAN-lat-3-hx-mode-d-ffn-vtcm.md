# SESSION PLAN — lat-3-hx-mode-d-ffn-vtcm (Sprint G)
**Date:** 2026-05-29
**Goal:** Implement the dual-VTCM staging architecture for a 2-stage matmul FFN
slice via Halide AOT, validating that the canonical Halide-internal
`.store_in(MemoryType::VTCM)` for an intermediate composes with Sprint F.1's
C-side `HAP_request_VTCM` hot-copy for inputs/outputs without collision.

This sprint follows the user-supplied plan `SESSION-PLAN-lat-3-hx-mode-d-ffn-vtcm`
verbatim modulo three corrections the prior sprints established as load-bearing:
- The SDK function names are `HAP_request_VTCM` / `HAP_release_VTCM`, not
  `HAP_vtcm_alloc` / `HAP_vtcm_free` (the latter do not exist).
- The Halide target string requires `noos` + `no_bounds_query` suffixes for
  in-skel use (Sprint F).
- Buffer alignment via `set_host_alignment(128)` in the generator (Sprint F.1).

The matmul math chain is the user's:
```
hidden(h, b) = clamp((Σ_d X(d, b) * W1(d, h) + b_term) >> q_bits, 0, 32767)
Y(c, b)      = sat_i16((Σ_h hidden(h, b) * W2(h, c) + b_term) >> q_bits)
```

---

## 1. Dual-VTCM Strategy

| Memory region | Allocator | Contents | Sized |
|---|---|---|---|
| External VTCM | `HAP_request_VTCM` from the FastRPC handler | X, W1, W2, Y (all 4 I/O buffers) | `r_X + r_W1 + r_W2 + r_Y` (each 128-byte-aligned) |
| Internal VTCM | `halide_hexagon_alloc_vtcm` from inside the Halide AOT runtime | hidden intermediate via `.store_in(MemoryType::VTCM)` | per-stripe allocation by Halide |

Both allocators tap the same V69 4 MB VTCM pool; the runtime returns disjoint
ranges. The skel asserts the external allocation fits with margin and falls
back to DDR if `HAP_request_VTCM` denies (won't fire on this S22U per Sprint F).

`HAP_perf_get_pcycles` brackets the Halide call so per-kernel time is reported
separately from FastRPC RTT + alloc + memcpy overhead. Earlier sprints could
not measure per-kernel time at all — Sprint G unblocks that.

---

## 2. Generator (`tools/sp_halide_gen/sp_ffn_2stage_gen.cpp`)

Two explicit reduction Funcs (`mm1`, `mm2`) via `update()` instead of `sum()`,
with `hidden` between them. Schedule:

```cpp
Y.hexagon()
 .vectorize(c, 64)
 .prefetch(X, batch, 2);

mm1.compute_root();
hidden.compute_root().store_in(MemoryType::VTCM);
mm2.compute_at(Y, batch);
```

All four input/output buffers carry `set_host_alignment(128)` so the runtime
asserts caller alignment, even though current Halide 2.4.07 codegen still emits
`vmemu` (unaligned) rather than `vmem` for this schedule (Sprint F.1 finding —
this hasn't been moved by any ablation tried so far). The kernel runs fine
with `vmemu` on VTCM-resident buffers per Sprint F.1.

Target: `hexagon-32-noos-no_bounds_query-no_asserts-hvx_128` (Sprint F lockdown).

---

## 3. Skel Handler (`sp_compute_imp.c::sp_compute_ffn_2stage_halide`)

1. Validate dims: `batch ≥ 1 mult-of-4`; `d_in, h_dim, d_out` mult-of-128.
2. Compute per-buffer aligned sizes; assert `need + per-iter-hidden ≤ 4 MB`.
3. `void *vtcm = HAP_request_VTCM(need, 0);`
4. memcpy DDR → VTCM for X, W1, W2.
5. Build `halide_buffer_t` descriptors with `host=vtcm_offset`, `host_dirty=1`.
6. `pcyc_before = HAP_perf_get_pcycles();`
7. `int rc = sp_ffn_2stage_halide(&X, &W1, &W2, b_term, q_bits, &Y);`
8. `pcyc_after = HAP_perf_get_pcycles();` — report delta as rout scalar (split lo/hi).
9. memcpy VTCM → DDR for Y; `HAP_release_VTCM(vtcm)`.

---

## 4. Gates

- `T_HALIDE_FFN_VTCM_ZEROS` — zero inputs → zero outputs ground truth.
- `T_HALIDE_FFN_VTCM_B{4,8,16,64}` — varying batch with D_in = H = D_out = 128;
  bitwise vs scalar saturating-arithmetic reference; reports `vtcm_used = 1`
  and `kernel_pcycles`.
- Umbrella tag `lat-phase-3-hx-mode-d-ffn-closed`.

---

## 5. Constraints recorded for downstream

- All matmul dims (`d_in`, `h_dim`, `d_out`) must equal the Halide tile width
  (128) for the current schedule. With sufficient time the schedule could be
  generalized, but the current empirical envelope is what's been validated.
- `q_bits ≤ 14` is the validated shift range. q_bits = 16 with the current
  test data produced a Halide-codegen divergence whose root cause did not
  yield to the standard ablations (sum() vs update(), compute_root vs
  compute_at(c|batch), Var disambiguation, explicit .bound(), schedule
  simplification). Open as Sprint G.1 with a minimal repro.
- Scalar reference uses `saturating_add` to match Halide's `vmpy(...):sat`
  accumulator codegen (Sprint G finding via SASS — `vmpy(Vu.h, Rt.h):sat`
  is the dominant MAC instruction).

---

## 6. Sub-tag taxonomy

- `lat-phase-3-hx-mode-d-ffn-halide-gen` — generator builds + AOT-emits
- `lat-phase-3-hx-mode-d-ffn-vtcm-staged` — handler does dual-VTCM staging
- `lat-phase-3-hx-mode-d-ffn-bitwise-correct` — gate suite passes
- `lat-phase-3-hx-mode-d-ffn-closed` — umbrella
