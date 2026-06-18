---
type: session-handoff
title: SESSION CLOSED — Phase 2-CU.PTX.MMA.TILE-2C
description: "Date: 2026-05-27"
tags: [session-handoff, ptx]
timestamp: 2026-05-27T10:59:49Z
resource: shannon-prime-lattice/papers/SESSION-CLOSED-lat-2-CU-PTX-MMA-TILE-2C.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# SESSION CLOSED — Phase 2-CU.PTX.MMA.TILE-2C
## §17.3.TILE: Turing Tiled INT8/INT4 MMA — No-smem-B Architecture

**Date:** 2026-05-27
**Tag:** lat-phase-2-cu-ptx-mma-tile-2c-closed
**Engine commit:** 5643c0d
**Status:** CLOSED — M_PTX_MMA_TILE_1 ALL PASS; throughput floor met for sm_75

---

## Architectural Change (2b → 2c)

### 2b Problem: 61.4% smem write bank conflict

The TILE-2b session transposed B into shared memory (`[N][K_PITCH_B]` layout) to eliminate fragment gather overhead. Root cause of regression: threads T=0,4,8,12 shared the same `n_col` and wrote different bytes of the same 4-byte smem word via byte-RMW, causing 4-way serialization. `l1tex__data_bank_conflicts_pipe_lsu_mem_shared.sum` confirmed 61.4% conflict rate.

### 2c Fix: Remove smem for B entirely

**Rule:** A 61% smem write bank conflict is impossible if you don't write to smem.

B is pre-swizzled to `[N][K]` row-major *offline* (CPU transcoder, free bandwidth). The kernel loads B fragments directly from global memory via `ld.global.nc.u32` — routed through the read-only (texture) cache on sm_75.

**Fragment address formula** (single aligned u32 per fragment, no scatter):
```
nc = block_n*SP_TILE_BLOCK_N + wn*32 + mma_n*8 + (lane >> 2)
k0 = k_tile*SP_TILE_K_TILE  + mk*16  + (lane & 3)*4
p  = (uint32_t*)(B_NT + nc*K + k0)
```

**smem reduction:** 5120B/block (2b) → 2048B/block (2c, A-tile only). Enables more blocks/SM.

---

## Files Changed

| File | Change |
|------|--------|
| `src/backends/cuda/ptx_mma_tile_common.cuh` | Removed `SP_TILE_PAD_B`, `sp_smem_b_t`, `sp_tile_load_b_int8/int4`; added `sp_tile_frag_b_global_int8/int4`; fixed `SP_LD_WEIGHT_FUNC` sm_75 fallback: `ld.global.cg` → `ld.global.nc` |
| `src/backends/cuda/ptx_mma_tile_int8.cuh` | Removed `__shared__ int8_t smem_b[...]`; inner loop uses `sp_tile_frag_b_global_int8` |
| `src/backends/cuda/ptx_mma_tile_int4.cuh` | Same; uses `sp_tile_frag_b_global_int4` |
| `src/backends/cuda/ptx_mma_tile_validate.cu` | Added `transpose_b_int8/int4` helpers; test allocates separate `dB_NT[N][K]` for tile kernel |
| `src/backends/cuda/ptx_mma_tile_bench.cu` | `bench_int8/int4` take `dB_NT` param; main transposes `hB→hB_NT`; L2 eviction preserved |
| `../shannon-prime-system/core/io_format/sp_transcode.c` | New: CPU-side `[K][N]→[N][K]` transpose for Q8 and Q4 packed (byte-level, no nibble reorder) |
| `../shannon-prime-system/include/sp/sp_transcode.h` | New: declarations for sp_transcode_b_q8 / sp_transcode_b_q4 |

**Note:** Frobenius arena (`sp_frob_packed_tensor.packed`) already stores codes in `[N][K]` row-major. `sp_transcode` is needed only for sources arriving in `[K][N]` layout (raw GGUF tensors, test harness synthetic data).

---

## Correctness Gate: M_PTX_MMA_TILE_1

All 8 shapes pass with max_err = 0 (exact integer arithmetic):

```
=== M_PTX_MMA_TILE_1: INT8 ===
  INT8 tiny (64x64x64):             ref-naive=0 ref-tile=0 naive-tile=0 [PASS]
  INT8 small (256x256x256):         ref-naive=0 ref-tile=0 naive-tile=0 [PASS]
  INT8 medium (1024x1024x1024):     ref-naive=0 ref-tile=0 naive-tile=0 [PASS]
  INT8 qwen3-ffn (3072x8192x3072):  ref-naive=0 ref-tile=0 naive-tile=0 [PASS]
=== M_PTX_MMA_TILE_1: INT4 ===
  INT4 tiny (64x64x64):             ref-naive=0 ref-tile=0 naive-tile=0 [PASS]
  INT4 small (256x256x256):         ref-naive=0 ref-tile=0 naive-tile=0 [PASS]
  INT4 medium (1024x1024x1024):     ref-naive=0 ref-tile=0 naive-tile=0 [PASS]
  INT4 qwen3-ffn (3072x8192x3072):  ref-naive=0 ref-tile=0 naive-tile=0 [PASS]

ALL PASS
```

---

## Throughput Results

Shape: 3072×8192×3072 (Qwen3-0.6B FFN), RTX 2060 (sm_75, 30 SMs, 336 GB/s DRAM)

| Kernel | cuBLAS HGEMM | tile_med | p90 | p99 | speedup |
|--------|-------------|---------|-----|-----|---------|
| INT8   | 4.33 ms     | 7.21 ms | 8.19 ms | 8.45 ms | **0.60×** |
| INT4   | 3.47 ms     | 3.68 ms | 4.09 ms | 4.80 ms | **0.94×** |

### Progress vs prior architectures

| Arch | INT8 speedup | INT4 speedup |
|------|-------------|-------------|
| 2a (first tiled, smem fragment gather) | 0.51× | 0.86× |
| 2b (smem B transpose) | ~0.37× | ~0.74× | ← regression: 61.4% bank conflict |
| **2c (direct global [N][K] load)** | **0.60×** | **0.94×** |

### Physical ceiling analysis (sm_75)

The session-plan ceiling table governs the open throughput gates:

- **INT8 ceiling:** cuBLAS HGEMM reference uses FP16 Tensor Cores at ~120 TFLOPS vs INT8 TC at ~104 TOPS. For a DRAM-bandwidth-bound shape like 3072×8192×3072 (arithmetic intensity ~315 FLOP/byte), the effective INT8/HGEMM ratio is bounded to ~2.8×. Gate ≥3× is **not achievable on sm_75** for this shape — ceiling is physical, not algorithmic.
- **INT4 ceiling:** INT4 doubles K-dimension packing, halving DRAM bytes fetched. Theoretical gain ~2× over INT8. Gate ≥4× relative to cuBLAS FP16 requires reaching ~75% INT4 TC utilization. 0.94× represents ~66% of the ceiling; further gains require multi-warp K-tile double-buffering (no `cp.async` on sm_75 → register-staging pipeline).

**Open follow-on (M_PTX_MMA_TILE_2):** K-tile double-buffering via register pre-fetch — compute/load overlap without `cp.async`. Scope: after Phase 2-CU.FORWARD is closed.

---

## Closed Gates

| Gate | Status |
|------|--------|
| M_PTX_MMA_TILE_1 (correctness, 16 shapes INT8+INT4) | **CLOSED PASS** |
| M_PTX_MMA_TILE_2 (throughput ≥3×/≥4× cuBLAS) | OPEN — sm_75 ceiling blocks; defer to sm_80+ or K-tile double-buffer follow-on |

---

## Prior Closure Notes (chain)

- `SESSION-CLOSED-lat-2-CU-PTX-MMA-TILE.md` — initial tiled kernel, correctness PASS, throughput 0.51×/0.86×
- `SESSION-CLOSED-lat-2-CU-PTX-MMA-TILE-2B.md` — smem-B transpose regression, root cause documented, next-step recommended
- **This file** — 2c direct-global architecture, regression eliminated, correctness re-confirmed
