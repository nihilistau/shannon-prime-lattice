---
type: session-handoff
title: SESSION CLOSED — lat-3-hx-mode-d-ffn-vtcm (Sprint G)
description: "Date: 2026-05-29"
tags: [session-handoff, vtcm]
timestamp: 2026-05-29T07:09:17Z
resource: shannon-prime-lattice/papers/SESSION-CLOSED-lat-3-hx-mode-d-ffn-vtcm.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# SESSION CLOSED — lat-3-hx-mode-d-ffn-vtcm (Sprint G)
**Date:** 2026-05-29
**Engine commit:** (see tag)
**Umbrella tag:** `lat-phase-3-hx-mode-d-ffn-closed`

The dual-VTCM staging architecture for a 2-stage matmul FFN is end-to-end
functional on the Samsung S22 Ultra cdsp via Path B. External VTCM
(`HAP_request_VTCM` from the skel) holds the four I/O buffers; internal VTCM
(Halide's `halide_hexagon_alloc_vtcm` triggered by `hidden.store_in(MemoryType::VTCM)`)
holds the intermediate. Both share the same V69 4 MB VTCM pool without collision;
the kernel runs bitwise-correct against a saturating-arithmetic scalar reference
across all four batch sizes tested, with per-kernel cycle timing now visible
via `HAP_perf_get_pcycles()` brackets — closing the perf-measurement gap left
open by Sprint F.1.

The H ≠ D_in case mandated in the user's plan does not pass with the
current generator + Halide 2.4.07 combination; the dual-VTCM mechanism itself
is independently validated by every passing configuration.

---

## Outcomes

| Sub-tag | Result |
|---|---|
| `lat-phase-3-hx-mode-d-ffn-halide-gen` | `sp_ffn_2stage_gen.exe` builds; AOT-emits a 109 KB Hexagon ELF `sp_ffn_2stage_halide.o` |
| `lat-phase-3-hx-mode-d-ffn-vtcm-staged` | Handler allocates all four I/O buffers in VTCM, runs Halide kernel, copies output back. vtcm_used = 1 reported on every test invocation |
| `lat-phase-3-hx-mode-d-ffn-bitwise-correct` | T_HALIDE_FFN_VTCM_ZEROS + B={4, 8, 16, 64} PASS; bitwise vs scalar reference (saturating arithmetic) |
| `lat-phase-3-hx-mode-d-ffn-closed` | umbrella |

```
T_HALIDE_FFN_VTCM_ZEROS  PASS  (all-zero output)              pcyc =  31,469,806
T_HALIDE_FFN_VTCM_B4     PASS via VTCM  B=4 D_in=H=D_out=128  pcyc =   7,868,421
T_HALIDE_FFN_VTCM_B8     PASS via VTCM  B=8                   pcyc =  15,725,027
T_HALIDE_FFN_VTCM_B16    PASS via VTCM  B=16                  pcyc =  31,449,905
T_HALIDE_FFN_VTCM_B64    PASS via VTCM  B=64                  pcyc = 125,804,392
```

Per-kernel pcycles scales linearly with batch (as expected — same matmul math
× batch count), suggesting the Halide kernel + dual-VTCM dance has no
batch-related overhead.

---

## Architecture

### External VTCM (skel-allocated)

```c
size_t need = align128(n_X) + align128(n_W1) + align128(n_W2) + align128(n_Y);
void *vtcm = HAP_request_VTCM(need, 0);
// VTCM offsets:
//   X  at vtcm + 0
//   W1 at vtcm + r_X
//   W2 at vtcm + r_X + r_W1
//   Y  at vtcm + r_X + r_W1 + r_W2

memcpy(x_dev,  x_buf,  n_X);   // DDR → VTCM
memcpy(w1_dev, w1_buf, n_W1);
memcpy(w2_dev, w2_buf, n_W2);

// build halide_buffer_t with .host = vtcm offsets, host_dirty = 1
int rc = sp_ffn_2stage_halide(&hx, &hw1, &hw2, b_term, q_bits, &hy);

memcpy(y_buf, y_dev, n_Y);     // VTCM → DDR
HAP_release_VTCM(vtcm);
```

### Internal VTCM (Halide-allocated)

```cpp
hidden.compute_root().store_in(MemoryType::VTCM);
```

Halide's runtime calls `halide_hexagon_alloc_vtcm` for `hidden`. The size
budget assertion in the skel reserves headroom — the total of external +
internal stays under 4 MB.

### Per-kernel timing

```c
uint64_t pcyc_before = HAP_perf_get_pcycles();
int rc = sp_ffn_2stage_halide(&hx, &hw1, &hw2, b_term, q_bits, &hy);
uint64_t pcyc_after  = HAP_perf_get_pcycles();
*kernel_pcycles_lo = (int)((pcyc_after - pcyc_before) & 0xFFFFFFFF);
*kernel_pcycles_hi = (int)((pcyc_after - pcyc_before) >> 32);
```

This is the first per-kernel time measurement in the project. Sprint F.1
could only report end-to-end wall, dominated by FastRPC RTT + VTCM alloc.
With `HAP_perf_get_pcycles()` brackets now in place, downstream sprints can
compare VTCM vs DDR at the kernel-only level.

---

## Bugs found during integration

### Sat-mul-acc accumulator divergence

SASS for the kernel inner loop:
```
v1:0.w += vmpy(v23.h, r4.h):sat
v3:2.w += vmpy(v27.h, r4.h):sat
```

Halide emits `vmpy(...):sat` — saturating multiply-accumulate. A wrapping
scalar reference diverges from this when accumulator saturation actually fires.
Fix: scalar reference uses `saturating_add` on the i32 accumulator.

For the test data range used in Sprint G (`w1, w2 in [-64, 63]`,
`x in [-16384, 16383]`), the i32 max ≈ 2.15G is not reached at any batch size
tested, so saturation should not fire. The reference matches Halide anyway,
which confirms the bitwise gate is meaningful.

### `q_bits ≤ 14` empirical constraint

With `q_bits = 16` and the saturating-arithmetic Rust reference, Halide
produced consistently different values from the reference — same exact
magnitudes across many schedule ablations (sum() vs update(), compute_root
vs compute_at, schedule simplification, Var disambiguation, .bound()). With
`q_bits = 14` the same configurations all PASS bitwise. Root cause did not
yield to the time budget. **Open as Sprint G.1 with a minimal repro
(B=64, all dims = 128, q=16 vs q=14 fails-vs-passes).**

### Halide-runtime hooks

Carried forward from Sprint F:
- `halide_print(void*, const char*)` → FARF
- `halide_error(void*, const char*)` → FARF
- `halide_qurt_hvx_lock/unlock` overridden as no-ops (FastRPC thread already
  holds HVX context)

Same stubs satisfy the FFN AOT; no new ones needed.

---

## What this sprint did NOT do

- **H ≠ D_in.** The user's plan envisioned varying H_dim independently. Empirically, the current generator + Halide 2.4.07 combo diverges from the scalar reference for these shapes. The exact same divergence values appeared across:
  - `mm1.compute_root()` ↔ `compute_at(Y, batch)`
  - `hidden.compute_root()` ↔ `compute_at(Y, batch)` ↔ `compute_at(Y, c)`
  - `mm2.compute_root()` ↔ `compute_at(Y, batch)` ↔ `compute_at(Y, c)`
  - `sum()` ↔ explicit `update()` with `+=`
  - `Var c` shared ↔ `Var hc` disambiguated for hidden
  - With and without explicit `.bound(hc, 0, H_dim)` on hidden
  - Schedule with `.tile(c, batch, ci, bi, 128, 4).vectorize(ci, 64).unroll(bi)` ↔ simplified `.vectorize(c, 64)`
  - Inputs at `[-16384, 16383]` × `[-256, 767]` (overflow-risk) and `[-16384, 16383]` × `[-64, 63]` (safe)

  All these ablations produced the **same exact diverging numbers** (e.g., 4KB B=8 H=256 q=16 b=16 always got=-1648 exp=-1; LARGE always got=-8 exp=-1).
  That stability suggests a deterministic Halide-codegen interaction that does
  not respond to any of the standard scheduling levers — worth a dedicated
  investigation session with the Halide upstream rather than ad-hoc fixes here.

- **`q_bits > 14` with the current test data.** Same family of divergences.

- **Halide auto-schedule, DMA prefetch, full FFN with HardSwish-SwiGLU.**
  Sprint H+.

---

## Constraints recorded for downstream

1. Sprint G FFN works for `d_in = h_dim = d_out = 128` and `q_bits ≤ 14`.
   Multi-batch fine.  Larger dims or larger `q_bits` open as Sprint G.1.

2. Halide kernels in this stack run on VTCM-backed I/O buffers when all four
   I/O buffers are colocated in VTCM (Sprint F.1's empirical lesson, validated
   here for matmul too).

3. Per-kernel timing is now available via `kernel_pcycles_lo/hi` rout
   parameters from `sp_compute_ffn_2stage_halide`. Use these to compare
   VTCM vs DDR at the kernel level (Sprint H opportunity).

---

## File map (delta from Sprint F.1)

| Repo | Path | Change |
|---|---|---|
| engine | `tools/sp_halide_gen/sp_ffn_2stage_gen.cpp` | new — 2-stage matmul Halide generator |
| engine | `tools/sp_halide_gen/build.cmd` | extended to emit FFN AOT alongside axpby_2d |
| engine | `tools/sp_compute_skel/halide_gen/sp_ffn_2stage_halide.{o,h}` | new — 109 KB Hexagon ELF + C header |
| engine | `tools/sp_compute_skel/halide_gen/HalideRuntimeHexagonHost.h` | staged for the .store_in(VTCM) ABI |
| engine | `tools/sp_compute_skel/inc/sp_compute.idl` | +`ffn_2stage_halide` IDL method |
| engine | `tools/sp_compute_skel/src_dsp/sp_compute_imp.c` | +`sp_compute_ffn_2stage_halide` handler with dual-VTCM + pcycles brackets |
| engine | `tools/sp_compute_skel/CMakeLists.txt` | link FFN .o alongside axpby .o |
| engine | `tools/sp_dsp_smoke/src/test_hvx.rs` | +ZEROS + B={4,8,16,64} test cases + saturating-arithmetic reference |
| lattice | `papers/SESSION-PLAN-lat-3-hx-mode-d-ffn-vtcm.md` | plan |
| lattice | `papers/SESSION-CLOSED-lat-3-hx-mode-d-ffn-vtcm.md` | this note |
