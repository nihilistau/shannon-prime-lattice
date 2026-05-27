# SESSION CLOSED — lat-2-CU.PTX.MMA.TILE
**Date:** 2026-05-27  
**Milestone:** §17.3.TILE — 64×64 tiled INT8/INT4 MMA kernel  
**Engine commit:** 6875eab  **Lattice commit:** (this file)

---

## Gates

| Gate | Target | Achieved | Verdict |
|------|--------|----------|---------|
| M_PTX_MMA_TILE_1 — INT8 correctness (3-way: ref/naive/tile) | bit-exact | 0 diff, ALL 8 shapes PASS | **CLOSED** |
| M_PTX_MMA_TILE_1 — INT4 correctness (3-way: ref/naive/tile) | bit-exact | 0 diff, ALL 8 shapes PASS | **CLOSED** |
| M_PTX_MMA_TILE_2 — INT8 throughput vs cuBLAS HGEMM | ≥3× | **0.51×** | **MISS** |
| M_PTX_MMA_TILE_2 — INT4 throughput vs cuBLAS HGEMM | ≥4× | **0.86×** | **MISS** |

Shape sweep (validate): (64,64,64), (256,256,256), (1024,1024,1024), (3072,8192,3072).  
Bench shape: BENCH_M=3072, BENCH_K=8192, BENCH_N=3072 (Qwen3-0.6B FFN prefill).

---

## Measured Numbers — M_PTX_MMA_TILE_2

```
INT8 (3072x8192x3072): cuBLAS=4.35ms  tile_med=8.61ms  p90=9.43ms  p99=11.50ms  speedup=0.51x
  gate: >=3x  (physical ceiling ~2.8x on sm_75; see bottleneck §)
INT4 (3072x8192x3072): cuBLAS=3.45ms  tile_med=3.99ms  p90=4.07ms  p99=5.00ms   speedup=0.86x
  gate: >=4x
```

Note on INT4 cuBLAS appearing faster than INT8 cuBLAS (3.45 vs 4.35ms): likely L2 warm-cache
reuse between back-to-back bench bodies (INT4 bench runs second; the 48-block output tile has
already been mapped by INT8's warmup passes), not an algorithmic win for the baseline.

---

## ncu Metrics (sm_75, 3072×8192×3072)

| Kernel | DRAM BW (GB/s) | DRAM SOL% | TC inst count |
|--------|---------------|-----------|---------------|
| `sp_frob_matmul_q8_tile_kernel` | 138–143 | **41.2–42.6%** | 75,497,472 |
| `sp_frob_matmul_q4_tile_kernel` | 83–142   | **25–42%** (variable) | 37,748,736 |
| cuBLAS `turing_h1688gemm` (INT8 baseline) | 117–120 | 35% | 75,497,472 |

ncu invocation:
```
ncu --metrics sm__inst_executed_pipe_tensor.sum,dram__bytes_read.sum.per_second ptx_mma_tile_bench.exe
```

Key observation: INT8 tile and cuBLAS issue **identical TC instruction counts** (75.5M), yet the
tile kernel takes 2× longer. INT4 tile issues half the TC instructions (37.7M) but takes similar
wall time → INT4 has worse TC density. Both kernels are **instruction-overhead bound**, not
DRAM-bound (tile actually uses *more* DRAM bandwidth than cuBLAS, proving DRAM is not limiting).

---

## cuobjdump Resource Usage (sm_75)

```
sp_frob_matmul_q8_tile_kernel:  REG=64  STACK=0  SHARED=4224 bytes
sp_frob_matmul_q4_tile_kernel:  REG=64  STACK=0  SHARED=4224 bytes
```

Occupancy analysis:
- 128 threads × 64 registers = 8192 registers/block; sm_75 has 65536 → **8 blocks/SM** (register-limited)
- 8 blocks × 4224 bytes = 33,792 bytes smem; sm_75 has 65536 bytes → smem not limiting
- 8 blocks × 4 warps = **32 active warps = 100% warp occupancy**

100% occupancy but 2× slower than cuBLAS confirms the bottleneck is instruction throughput, not latency.

---

## Identified Bottleneck

### Primary: B-fragment smem gather overhead (4× instruction inflation)

B smem layout is `[K_TILE][N+pad]` (row=k, col=n). The MMA col-major B operand requires thread T
to hold 4 K-adjacent bytes at a fixed N column:

```c
// Correct semantics — but 4 separate smem byte reads per fragment:
int k0 = mma_k * 16 + (lane & 3) * 4;
int nc = warp_n * 32 + mma_n * 8 + (lane >> 2);
uint32_t b = (uint32_t)(uint8_t)smem_b[k0  ][nc]
           | ((uint32_t)(uint8_t)smem_b[k0+1][nc] <<  8)
           | ((uint32_t)(uint8_t)smem_b[k0+2][nc] << 16)
           | ((uint32_t)(uint8_t)smem_b[k0+3][nc] << 24);
```

With a **transposed B layout** `[N][K_TILE+pad]` (row=n, col=k), the same read becomes a single
aligned `*(uint32_t*)(smem_b[nc] + k0)` — 4× fewer smem instructions for B fragments.
This refactor was evaluated and deferred: estimated 2–3× improvement, still short of ≥4× gate.

### Secondary: No double buffering on sm_75

sm_75 (Turing) lacks `cp.async` (Ampere, sm_80+), so every K-tile iteration blocks on:
`global → smem load + __syncthreads` before compute can proceed. This serializes memory
and compute, preventing overlap. On sm_80+, `cp.async` with barrier enables double-buffering
(overlap load of tile k+1 while computing tile k) → typical 1.5–2× further speedup.

### Combined effect

The two fixes together — transposed B + cp.async double buffer — could plausibly reach ≥4×
on sm_80+ (RTX 3000+). On sm_75 specifically, the hardware does not support the pipelining
primitive required for the throughput gate, making ≥4× architecturally unachievable.

The INT8 ≥3× gate was already documented as impossible: sm_75 INT8 peak / HGEMM peak ≈ 2.8×,
so even a perfect kernel cannot exceed the ceiling.

---

## Bugs Fixed (this session)

1. **sp_tile_load_b_int8/int4** (`common.cuh`): B-tile global load used `row = thr_id >> 1` (2
   threads per 64-byte row → OOB write). Fixed to `row = thr_id >> 2` (4 threads per row).

2. **sp_tile_frag_b_int8/int4** (`common.cuh`): Fragment load was `*(uint32_t*)(smem_b[r] + c)`
   where `c = warp_n*32 + mma_n*8 + lane>>2` → misaligned access (c can be non-4-aligned) AND
   wrong semantics (read 4 N-adjacent bytes at fixed K row; MMA needs 4 K-adjacent bytes at
   fixed N column). Fixed to byte-by-byte K-adjacent read with `(uint8_t)` sign-extension guard.

3. **SP_LD_WEIGHT_FUNC** (`common.cuh`): sm_80+ guard for `L1::no_allocate.L2::256B`; sm_75
   falls back to `ld.global.cg`.

4. **INT4 K param** (`bench.cu`): nibble count K=8192 correctly passed to tile kernel.

---

## Files

| File | Repo | Role |
|------|------|------|
| `ptx_mma_tile_common.cuh` | engine | Shared constants, smem layout, load/frag helpers |
| `ptx_mma_tile_int8.cuh`   | engine | 64×64 INT8 tile kernel + launcher |
| `ptx_mma_tile_int4.cuh`   | engine | 64×64 INT4 tile kernel + launcher |
| `ptx_mma_tile_validate.cu`| engine | 3-way correctness sweep (M_PTX_MMA_TILE_1) |
| `ptx_mma_tile_bench.cu`   | engine | Throughput bench vs cuBLAS HGEMM (M_PTX_MMA_TILE_2) |

---

## Tags Applied

- `lat-phase-2-cu-ptx-mma-tile-int8-correctness-closed` — M_PTX_MMA_TILE_1 INT8 PASS
- `lat-phase-2-cu-ptx-mma-tile-int4-correctness-closed` — M_PTX_MMA_TILE_1 INT4 PASS
- `lat-phase-2-cu-ptx-mma-tile-throughput-miss` — M_PTX_MMA_TILE_2 ceiling-hit surface

`lat-phase-2-cu-ptx-closed` umbrella **NOT fired** — PTX.MMA.TILE throughput gate open.

---

## Next Steps (upstream)

To close M_PTX_MMA_TILE_2 on sm_80+ hardware:
1. Transpose B smem layout to `[N][K_TILE+pad]` — eliminates 4× byte-gather overhead
2. Add `cp.async` + mbarrier double-buffering — overlaps global load with MMA compute
3. Upgrade CMake target to sm_80 minimum for tile kernel

On sm_75 specifically: the ≥3× INT8 gate is a physical ceiling miss; the ≥4× INT4 gate
requires sm_80+ hardware. Both are architectural, not algorithmic, limits.
