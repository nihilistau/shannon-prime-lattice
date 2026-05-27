# SESSION-PLAN: Phase 2-CU.PTX.MMA.TILE

**Roadmap §:** §17.3.TILE  
**Hardware:** RTX 2060, sm_75 (Turing), CUDA 13.2  
**Commit prefix:** `[lat-2-cu-ptx-mma-tile]`  
**Status:** PRE-CODE — plan locked, no kernel written yet  

---

## 0. Hardware Ceiling Analysis (mandatory before gate review)

### sm_75 RTX 2060 peak throughput

| Operation | Peak | Source |
|-----------|------|--------|
| FP32 (CUDA cores) | 6.5 TFLOPS | NVIDIA RTX 2060 spec |
| FP16 with Tensor Cores (HMMA.F16) | ~52 TFLOPS | 2× FP32 TC multiplier, Turing 2nd gen |
| INT8 with Tensor Cores (IMMA.S8) | ~104 TOPS | 2× HMMA.F16 peak |
| INT4 with Tensor Cores (IMMA.S4) | ~208 TOPS | 4× HMMA.F16 peak |
| DRAM bandwidth | 336 GB/s | GDDR6 |

### Gate workload analysis: (M,N,K) = (3072, 3072, 8192)

GFLOP count: 2 × 3072 × 3072 × 8192 = 154.6 GFLOP (same for INT8 GIOP, INT4 GIOP)

**Baseline time estimate** (cuBLAS HGEMM + dequant, assuming 80% HGEMM efficiency):
- cublasHgemm at 80% FP16 TC efficiency: 154.6 / (52,000 × 0.80) = 3.72 ms
- INT8 dequant (2 matrices, read int8 write fp16): 2 × 3072×8192×3B / 336e9 = ~0.45 ms
- INT4 nibble-expand (2 matrices): 2 × 3072×8192×2.5B / 336e9 = ~0.37 ms
- **INT8 baseline total: ~4.17 ms**
- **INT4 baseline total: ~4.09 ms**

**INT8 achievable speedup table:**

| INT8 TC utilization | Our time | Speedup vs baseline | Gate |
|--------------------|----------|--------------------|-|
| 50% | 2.97 ms | 1.40× | FAIL (≥3×) |
| 70% | 2.12 ms | 1.97× | FAIL |
| 90% | 1.65 ms | 2.53× | FAIL |
| 100% (physical ceiling) | 1.49 ms | **2.80×** | **FAIL — ceiling < gate** |

**INT8 ≥3× conclusion: IMPOSSIBLE on sm_75.** INT8 TC peak is 2× FP16 TC peak;
cuBLAS achieves ≥75% FP16 efficiency at this shape; the physical ceiling is ~2.8–3.0×.
Proceed with best-effort; report achieved speedup + ncu SOL %; document ceiling hit.

**INT4 achievable speedup table:**

| INT4 TC utilization | Our time | Speedup vs baseline | Gate |
|--------------------|----------|--------------------|-|
| 50% | 1.49 ms | 2.75× | FAIL (≥4×) |
| 70% | 1.06 ms | 3.86× | borderline FAIL |
| **75%** | **0.99 ms** | **4.13×** | **PASS** |
| 85% | 0.87 ms | 4.70× | PASS |
| 100% (ceiling) | 0.74 ms | 5.53× | PASS |

**INT4 ≥4× conclusion: ACHIEVABLE** at ≥75% TC utilization. INT4 has 4× FP16 TC peak;
the gate is comfortably below the ceiling given the nibble-expand dequant overhead.
This is the primary performance target.

### Strategy given ceiling analysis

- **INT8:** Implement the same tiled kernel; document ceiling conflict; accept achieved
  speedup (expected ~2.0–2.5×). If the bench shows >3×, cuBLAS was less efficient than
  estimated — record the actual number.
- **INT4:** Target ≥75% TC utilization via bank-conflict-free smem layout + cooperative
  tile loading. This is the closure gate.

---

## 1. Kernel Architecture

### Block/warp/MMA geometry

```
Block tile:  BLOCK_M=64, BLOCK_N=64, K_TILE=32 (INT8) / K_TILE_I4=64 nibbles (32 bytes)
Warp tile:   WARP_M=32,  WARP_N=32
MMA shape:   m8n8k16 (INT8) / m8n8k32 (INT4)
Block layout: 4 warps in 2×2 arrangement
             warp 0: rows 0..31,  cols 0..31
             warp 1: rows 0..31,  cols 32..63
             warp 2: rows 32..63, cols 0..31
             warp 3: rows 32..63, cols 32..63
MMA grid per warp: 4(M) × 4(N) for INT8 (2 MMA steps per K_TILE)
                   4(M) × 4(N) for INT4 (2 MMA steps per K_TILE nibble-units)
```

### sm_75 pipeline (synchronous, no cp.async)

sm_75 (Turing) does not support `cp.async`; the pipeline is synchronous:

```
for each k_tile:
  [Load phase]
    128 threads cooperatively load smem_a[BLOCK_M][K_TILE] from A global
    128 threads cooperatively load smem_b[K_TILE][BLOCK_N] from B global
    __syncthreads()
  [Compute phase]
    each warp executes 4×4 MMA grid on its 32×32 warp tile
    (32 mma.sync calls per warp for INT8, 16 calls for INT4)
    __syncthreads()
```

Note: no double-buffering on sm_75. The compute phase does not overlap with global
memory loads. Tensor Core utilization is maximized by minimizing __syncthreads overhead.

sm_80+ cp.async upgrade path is commented in ptx_mma_tile_common.cuh under
`#if SP_TILE_SM80` guard (deferred, not implemented this phase).

---

## 2. Shared-Memory Layout

### INT8 tiles (K_TILE=32, BLOCK_M=64, BLOCK_N=64)

```
smem_a: int8_t [BLOCK_M][K_TILE]             = int8_t [64][32] = 2048 bytes
smem_b: int8_t [K_TILE][BLOCK_N + PAD_B]     = int8_t [32][68] = 2176 bytes
        (PAD_B = 4 bytes per row to avoid bank conflicts on B column-gather)
Total:  4224 bytes per block ≈ 4.1 KB
```

### INT4 tiles (K_TILE nibbles = 64, byte width = 32, BLOCK_M=64, BLOCK_N=64)

```
smem_a: uint8_t [BLOCK_M][K_TILE_BYTES]      = uint8_t [64][32] = 2048 bytes (packed nibbles)
smem_b: uint8_t [K_TILE_BYTES][BLOCK_N + PAD_B] = uint8_t [32][68] = 2176 bytes
Total:  4224 bytes (same physical layout as INT8)
```

Physical smem footprint is identical for INT8 and INT4; the difference is how
fragment registers are packed before mma.sync.

### Bank-conflict analysis

**smem_a load (128 threads, 16 bytes each → 2048 bytes):**
- Thread T: row = T/2, col_byte_start = (T%2)*16
- 2 threads per row, loading non-overlapping halves → 0 conflicts

**smem_a MMA read (thread T, m8n8k16, A fragment):**
- Thread T reads row = warp_m*8 + T/4, col_byte = k_step*16 + (T%4)*4
- 4 threads share same row, each at offset 0,4,8,12 → 4 distinct banks → 0 conflicts

**smem_b load (128 threads, 16 bytes each → 2176 bytes; row pitch 68 bytes):**
- Thread T: row = T/2, col_byte_start = (T%2)*16 (same pattern as A load)
- 0 conflicts on cooperative load

**smem_b MMA read (thread T, m8n8k16, B fragment, col-major access):**
- Thread T reads row = k_step*16 + (T%4)*4, col = warp_n*8 + T/4
- Without PAD_B: 4 threads with T%4=0 all hit row=k_step*16 col varying → potential conflict
- With PAD_B=4: row pitch = 68 bytes = 17 × 4-byte banks → column 0 of row R at bank 17R%32
  Different rows map to different bank sequences → eliminates systematic conflicts

---

## 3. Register Budget

Per warp lane (32 threads per warp, 4 warps per block):

```
Accumulators d[m][n]: 4×4 MMA ops × 2 INT32 regs/op = 32 registers
A fragments  a[m][k]: 4 M-tiles × 2 K-steps × 1 reg each = 8 registers
B fragments  b[k][n]: 2 K-steps × 4 N-tiles × 1 reg each = 8 registers
Addressing:  smem ptr, global ptr, tile index, loop vars = ~8 registers
Total:       56 registers per lane ← under 64-reg occupancy target
```

Register allocation note: during MMA compute, A and B fragments for both K-steps can be
preloaded into registers simultaneously (all 16 fragment regs live alongside all 32 accums
= 48 regs before addressing). The remaining 8 addressing regs fit the budget.

---

## 4. Global Load Strategy

### A-tile cooperative load (activation side — uses ld.global.cg: L2-cached)

128 threads load 64×32 = 2048 bytes of INT8 (or nibble-packed bytes).
Each thread loads 16 bytes (128-bit load):
```
thr = warp_id*32 + lane_id;       // 0..127
row = thr / 2;                    // 0..63
col_byte = (thr % 2) * 16;        // 0 or 16
ptr = &A_global[block_row*64 + row][k_tile*32 + col_byte];
ld.global.cg.v4.u32  // 4×4=16 bytes, L2-cached (activation side)
st.shared.v4.u32
```

### B-tile cooperative load (weight side — uses LD_NC pattern: L1 non-allocating)

B is the weight matrix (reused across batch rows). Weight-side loads use
LD_NC (L1::no_allocate) to prevent weight data evicting activation cache.
Pattern mirrors DeepEP `utils.cuh` LD_NC_FUNC macro (lines 177-181):

```c
// ptx_mma_tile_common.cuh
#ifndef DISABLE_WEIGHT_LD_NC
  #define SP_LD_WEIGHT_FUNC "ld.global.nc.L1::no_allocate.L2::256B"
#else
  #define SP_LD_WEIGHT_FUNC "ld.global.cg"
#endif
```

This mirrors DeepEP's DISABLE_AGGRESSIVE_PTX_INSTRS fallback pattern
(ptx.cuh lines 1-10; utils.cuh lines 177-181).

---

## 5. Fragment Packing (smem → MMA registers)

### INT8 A fragment (thread T, warp-tile row m, k-step k):
```ptx
ld.shared.u32 %a0, [smem_a + (warp_m*8 + T/4)*32 + k*16 + (T%4)*4];
```
One 4-byte register holds 4 INT8 values for the 8×16 MMA A-matrix stripe.

### INT8 B fragment (thread T, warp-tile col n, k-step k):
```ptx
ld.shared.u32 %b0, [smem_b + (k*16 + (T%4)*4)*(BLOCK_N+PAD_B) + warp_n*8 + T/4];
```

### INT4 A fragment (thread T, warp-tile row m, k-step k):
INT4 uses m8n8k32 → K=32 nibbles = 16 bytes per row, 4 bytes per thread fragment.
Same PTX as INT8 but base + offset halved (32 bytes per row instead of 32 bytes for K=16).

### INT4 B fragment: mirror of A with B-tile addressing.

Fragment packing logic in `ptx_mma_tile_common.cuh` as inline device functions.

---

## 6. Frobenius Scale Epilogue

After all K-tiles complete:
- Each lane holds 32 INT32 accumulators for its 4×4 output sub-tile
- Per-row scale: scale_C[row] = scale_a[row] * scale_b[0] * (1/128.0f)
  (scale_b[0] is per-column scale; only row dimension varies in Frobenius convention)
- Conversion: d_float = __int2float_rn(d_int32) * scale_C[row]
- Write to C as __half: C[row][col] = __float2half(d_float)

Cooperative reduction for per-row scale: broadcast scale_a[row] via smem
using 1 float per output row. 64 floats × 4 bytes = 256 bytes of smem for
epilogue (reuse the smem_a buffer after compute phase).

---

## 7. File-by-File Budget and Signatures

### ptx_mma_tile_common.cuh (≤400 lines)

Shared definitions used by both INT8 and INT4 tile kernels.

```c
// Constants
#define SP_TILE_BLOCK_M  64
#define SP_TILE_BLOCK_N  64
#define SP_TILE_K_TILE   32     // INT8: 32 bytes; INT4: 32 packed-nibble bytes
#define SP_TILE_PAD_B    4      // smem_b row padding bytes
#define SP_TILE_WARPS    4      // warps per block (2×2 arrangement)
#define SP_TILE_THREADS  128    // SP_TILE_WARPS × 32

// Load helpers (A-tile via cg, B-tile via LD_NC)
__device__ __forceinline__
void sp_tile_load_a(const int8_t *A_global, int8_t *smem_a,
                    int block_row, int k_tile, int M, int K, int thr_id);

__device__ __forceinline__
void sp_tile_load_b(const int8_t *B_global, int8_t *smem_b,
                    int block_col, int k_tile, int K, int N, int thr_id);

// Fragment load from smem to registers
__device__ __forceinline__
uint32_t sp_tile_frag_a(const int8_t *smem_a, int warp_m, int mma_m, int mma_k, int lane);

__device__ __forceinline__
uint32_t sp_tile_frag_b(const int8_t *smem_b, int warp_n, int mma_n, int mma_k, int lane);

// Epilogue: INT32 accums → scaled FP16 output
__device__ __forceinline__
void sp_tile_epilogue(int *acc, __half *C_global, const float *scale_a, float scale_b,
                      int out_row, int out_col, int warp_m, int warp_n, int mma_m, int mma_n,
                      int lane, int M, int N);
```

### ptx_mma_tile_int8.cuh (≤600 lines)

```c
// Main tiled INT8 kernel — one block handles BLOCK_M × BLOCK_N output tile
__global__
void sp_frob_matmul_q8_tile_kernel(
    const int8_t *__restrict__ A,    // [M][K]
    const int8_t *__restrict__ B,    // [K][N]
    const float  *__restrict__ scale_a, // [M] per-row Frobenius scale
    float scale_b,                   // scalar B scale (uniform for bench)
    __half       *__restrict__ C,    // [M][N] FP16 output
    int M, int K, int N);

// Host launcher (handles grid sizing, stream, smem config)
cudaError_t sp_frob_matmul_q8_mma_tile(
    const int8_t *A, const int8_t *B,
    const float *scale_a, float scale_b,
    __half *C, int M, int K, int N, cudaStream_t stream);
```

### ptx_mma_tile_int4.cuh (≤600 lines)

```c
// INT4 variant — A and B are nibble-packed uint8_t[M][K/2] and uint8_t[K/2][N]
__global__
void sp_frob_matmul_q4_tile_kernel(
    const uint8_t *__restrict__ A_q4, // [M][K/2] packed nibbles
    const uint8_t *__restrict__ B_q4, // [K/2][N]
    const float   *__restrict__ scale_a,
    float scale_b,
    __half        *__restrict__ C,
    int M, int K, int N);              // K is nibble count

cudaError_t sp_frob_matmul_q4_mma_tile(
    const uint8_t *A_q4, const uint8_t *B_q4,
    const float *scale_a, float scale_b,
    __half *C, int M, int K, int N, cudaStream_t stream);
```

### ptx_mma_tile_validate.cu (≤400 lines)

Three-way correctness check per shape:
1. Scalar host reference: `sp_frob_matmul_q8_ref` / `sp_frob_matmul_q4_ref` (existing)
2. Single-instruction reference: `sp_frob_matmul_q8_mma_kernel` / `q4_mma_kernel` (existing)
3. Tiled kernel: `sp_frob_matmul_q8_mma_tile` / `q4_mma_tile` (new)

Shape sweep: (64,64,64), (256,256,256), (1024,1024,1024), (3072,3072,8192)
Exit code 0 = all byte-exact, non-zero = failure with failing shape and max diff.

### ptx_mma_tile_bench.cu (≤400 lines)

Matches ptx_bench.cu structure (50 REPS, 5 warm-up discarded):
- INT8: cuBLAS baseline (dequant + HGEMM) vs sp_frob_matmul_q8_mma_tile
- INT4: cuBLAS baseline (nibble-expand + HGEMM) vs sp_frob_matmul_q4_mma_tile
- Shape: (3072, 3072, 8192) only (prefill-shape, matches M_PTX_MMA_TILE_2 gate)
- Timing: median / p90 / p99 over 50 reps
- ncu metrics (when run under ncu): sm__inst_executed_pipe_tensor.sum, l1tex__t_bytes_pipe_lsu_mem_global_op_ld.sum, dram__bytes_read.sum.per_second

---

## 8. Reference Citation Map

| Construct | Source file | Lines | Why |
|-----------|------------|-------|-----|
| `__forceinline__ __device__` wrapper discipline | DeepEP ptx.cuh | 37-53 | Style + inlining guarantee |
| `#ifndef DISABLE_…` fallback macro pattern | DeepEP ptx.cuh | 1-10; utils.cuh 177-181 | sm_75 vs sm_80+ guards |
| LD_NC_FUNC weight-side loads | DeepEP utils.cuh | 177-181 | L1::no_allocate for B-side |
| mbarrier wrappers (sm_80+ future) | DeepEP ptx.cuh | 56-90 | cp.async upgrade path |
| cp.async wrapper (sm_80+ future) | DeepEP ptx.cuh | 137-143 | double-buffer upgrade path |
| v4 load pattern | ptx_spinor.cuh | 36-50 | vetted ld.global.cg.v4 discipline |
| mma_s8_m8n8k16 / mma_s4_m8n8k32 | ptx_mma.cuh | 21-40 | called directly — no rewrite |
| sp_frob_matmul_q8_ref / q4_ref | ptx_mma.cuh | 250-350 | bit-exact reference for validate |

---

## 9. Commit Sequence (8 commits minimum)

| # | Repo | What |
|---|------|------|
| 1 | lattice | This plan document |
| 2 | engine | `ptx_mma_tile_common.cuh` skeleton (≤150 lines) + fill sections |
| 3 | engine | `ptx_mma_tile_int8.cuh` skeleton + fill sections |
| 4 | engine | `ptx_mma_tile_int4.cuh` skeleton + fill sections |
| 5 | engine | CMake: add ptx_mma_tile_validate + ptx_mma_tile_bench targets |
| 6 | engine | `ptx_mma_tile_validate.cu` |
| 7 | engine | `ptx_mma_tile_bench.cu` |
| 8 | lattice | `SESSION-CLOSED-lat-2-CU-PTX-MMA-TILE.md` closure note |

Sub-tags `lat-phase-2-cu-ptx-mma-tile-int8-closed` and
`lat-phase-2-cu-ptx-mma-tile-int4-closed` applied after empirical gate closure.
Do NOT fire `lat-phase-2-cu-ptx-closed` umbrella.

---

## 10. Anti-contamination Checklist

- [ ] Zero `#include <mma.h>`, zero `nvcuda::wmma` in any new file
- [ ] Zero `cudaMalloc` on hot path; all staging via `__shared__`
- [ ] No softmax/temperature/probability code
- [ ] No reads from legacy repos (shannon-prime\ or shannon-prime-engine\)
- [ ] mma_s8_m8n8k16 / mma_s4_m8n8k32 called from ptx_mma.cuh — not redefined
- [ ] B-side loads use SP_LD_WEIGHT_FUNC (L1::no_allocate)
- [ ] All gates measured at (3072,3072,8192); no shape-tuning to hit the number

---

*Plan locked — begin Commit 2 (ptx_mma_tile_common.cuh skeleton).*
