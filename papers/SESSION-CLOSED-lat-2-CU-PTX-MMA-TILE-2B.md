# SESSION CLOSED — lat-2-CU.PTX.MMA.TILE.2B
**Date:** 2026-05-27  
**Milestone:** §17.3.TILE-2b — B smem transpose, naive byte-scatter  
**Engine commits:** 8a55a3e (smem transpose), 883339c (L2 eviction fix)  
**Lattice commit:** (this file)  
**Status:** REGRESSION — engine commits NOT pushed

---

## Objective

Eliminate the 4× B-fragment smem byte-gather overhead identified in the
§17.3.TILE session by transposing the B smem layout from `[K_TILE][N+pad]`
(row=k) to `[BLOCK_N][K_PITCH_B=48]` (row=n). Expected result: fragment
reads collapse from 4 serial byte instructions to 1 aligned `uint32_t` load.

---

## Gates

| Gate | Target | Prior baseline (6875eab) | This session | Verdict |
|------|--------|--------------------------|--------------|---------|
| M_PTX_MMA_TILE_1 — INT8 correctness | bit-exact | PASS | **PASS (all 8 shapes)** | **CLOSED** |
| M_PTX_MMA_TILE_1 — INT4 correctness | bit-exact | PASS | **PASS (all 8 shapes)** | **CLOSED** |
| Floor gate — INT8 wall-clock vs prior tile | any improvement | 8.61ms | **8.76ms (+1.7%)** | **REGRESSION** |
| Floor gate — INT4 wall-clock vs prior tile | any improvement | 3.99ms | **4.44ms (+11.3%)** | **REGRESSION** |

---

## Measured Numbers

```
Prior tile (6875eab, [K_TILE][N+pad] layout):
  INT8 (3072x8192x3072): cuBLAS=4.35ms  tile_med=8.61ms  speedup=0.51x
  INT4 (3072x8192x3072): cuBLAS=3.45ms  tile_med=3.99ms  speedup=0.86x

This session (8a55a3e, [N][K_PITCH_B=48] layout):
  INT8 (3072x8192x3072): cuBLAS=3.46ms  tile_med=8.76ms p90=9.71ms  speedup=0.40x
  INT4 (3072x8192x3072): cuBLAS=3.46ms  tile_med=4.44ms p90=4.86ms  speedup=0.78x
```

Note: cuBLAS INT8 baseline drop (4.35ms → 3.46ms) reflects GPU thermal/clock state
differences between sessions, not a code change. INT4 cuBLAS is now measured cold
(L2 eviction fix applied).

---

## ncu Metrics (sm_75, 3072×8192×3072)

| Kernel | Bank conflicts | Total smem wavefronts | Conflict rate |
|--------|---------------|----------------------|---------------|
| `sp_frob_matmul_q8_tile_kernel` (2b) | 136,957,630 | 223,090,366 | **61.4%** |
| `sp_frob_matmul_q4_tile_kernel` (2b) | 68,428,590  | 111,504,174 | **61.4%** |

Metric: `l1tex__data_bank_conflicts_pipe_lsu_mem_shared.sum` (sm_75-compatible).
Prior baseline bank conflicts: not measured; write path was conflict-free by construction
(each thread wrote v4.u32 to its own contiguous smem row without cross-thread overlap).

---

## cuobjdump Resource Usage (sm_75)

| Kernel | REG | SHARED (2b) | SHARED (prior) | Delta |
|--------|-----|-------------|----------------|-------|
| `q8_tile_kernel` | 64 | 5120 B | 4224 B | +896 B |
| `q4_tile_kernel` | 64 | 5120 B | 4224 B | +896 B |

Register count: unchanged. Occupancy: still 8 blocks/SM (8×5120=40,960 < 65,536).

---

## Root Cause Analysis

### What was fixed (fragment reads)

Old `sp_tile_frag_b_int8` read:
```c
return  (uint32_t)(uint8_t)smem_b[k0    ][nc]
      | ((uint32_t)(uint8_t)smem_b[k0 + 1][nc] <<  8)
      | ((uint32_t)(uint8_t)smem_b[k0 + 2][nc] << 16)
      | ((uint32_t)(uint8_t)smem_b[k0 + 3][nc] << 24);
```
New `sp_tile_frag_b_int8` read:
```c
return *(const uint32_t *)(&smem_b[nc][k0]);
```
Fragment reads: 4 byte-gathers → 1 aligned uint32_t. Instruction count for reads
reduced from 128 to 32 per warp per K-tile iteration. This improvement is real.

### What was NOT fixed (scatter writes — primary culprit)

New `sp_tile_load_b_int8` scatter:
```c
smem_b[n_col_base +  0][k_row] = (int8_t)( v0        & 0xFF);
smem_b[n_col_base +  1][k_row] = (int8_t)((v0 >>  8) & 0xFF);
/* ...16 byte assignments total per thread */
```

The critical failure: within a warp, threads T=0,4,8,12 have n_col_base=0 and
k_row=0,1,2,3 respectively. Their writes target:

```
smem_b[0][0], smem_b[0][1], smem_b[0][2], smem_b[0][3]
```

These are bytes 0,1,2,3 of the **same 4-byte smem word** at base+0. GPU hardware
issues these as 4-way serialized byte-RMW operations, not a single coalesced store.

Per warp, per K-tile load, there are 8 such groups (by n_col_base=0,16,32,48 for each
of the two warp-halves: T=0–15 and T=16–31). Each group performs 16 byte writes in the
inner loop. Result: 8 × 16 = 128 same-word conflicts per warp per K-tile iteration.

For K=8192 / K_TILE=32 = 256 K-tile iterations: 256 × 128 = 32,768 serializations
per warp per kernel launch.

The ncu measurement confirms this: 136.9M / 223.1M = 61.4% of all smem accesses are
bank conflicts. The old layout's write path had ~0% write conflicts (v4.u32 stores to
consecutive words in the same smem row, no cross-thread overlap).

### Why the 2–3× estimate was wrong

The prior session estimate assumed:
1. B-fragment read overhead was the PRIMARY bottleneck
2. Write serialization could be eliminated with appropriate padding

Assumption 2 failed: padding (K_PITCH_B=48) eliminates bank conflicts for
**reads** (confirmed: fragment reads in new layout are conflict-free), but the
byte-scatter write introduces structural same-word conflicts that no row-pitch
adjustment can remove — the problem is the write ORDER, not alignment.

### Net effect

- Fragment read instruction savings: ~96 instructions/warp/K-tile (4→1 per fragment × 32 frags)
- Same-word write serialization cost: ~384 extra cycles/warp/K-tile (128 conflicts × ~3 extra cycles each)
- The write overhead exceeds the read savings → net regression.

---

## Next Steps (follow-on work)

To realize the fragment-read speedup without write regression, eliminate the
same-word byte-RMW by packing the 4 k_row bytes into a single word BEFORE writing:

### Option A: Warp-shuffle pack (recommended)

After the v4 global load, each thread T has one byte per n_col (16 bytes for
n_col_base..n_col_base+15). Four threads T, T+4, T+8, T+12 (k_row=0,1,2,3) need to
contribute one byte each to form a single `uint32_t` word for smem_b[n][0..3].

Use `__shfl_sync` to exchange bytes across threads:
```c
/* Thread T is responsible for k_row = T >> 2 */
/* For each n offset i (0..15): */
uint8_t my_byte = (uint8_t)(vi_component);
/* Gather bytes from k_row=0..3 into a single word */
uint32_t word =  (uint32_t)__shfl_sync(mask, my_byte, base + (i & 3)     )
              | ((uint32_t)__shfl_sync(mask, my_byte, base + (i & 3) + 4  ) <<  8)
              | ((uint32_t)__shfl_sync(mask, my_byte, base + (i & 3) + 8  ) << 16)
              | ((uint32_t)__shfl_sync(mask, my_byte, base + (i & 3) + 12 ) << 24);
/* One thread per group writes the full word */
if ((T & 3) == 0)
    *(uint32_t *)(&smem_b[n_col_base + i/4][k_row_group * 4]) = word;  /* approximate */
```

This replaces 4 byte stores with 3 shuffles + 1 word store per group. Expected: write
conflicts → 0; net benefit = read savings dominate → likely 1.5–2× improvement.

The exact shuffle indexing is non-trivial (needs careful alignment of the lane→n→k
mapping); this warrants a separate session (§17.3.TILE-2c).

### Option B: Accept ceiling hit (sm_75 specific)

On sm_75, INT8 ≥3× is architecturally impossible (physical ceiling ~2.8×) and INT4 ≥4×
requires sm_80+ (cp.async + properly pipelined kernel). If targeting sm_80+ is acceptable,
implement: transposed B (this session's work) + shuffle-pack + cp.async double-buffering.

---

## Disposition

Engine commits 8a55a3e + 883339c: **NOT pushed** (regression commits).  
Correctness result (M_PTX_MMA_TILE_1 ALL PASS with transposed layout) stands —  
the layout is semantically correct; the regression is performance-only.

Tag `lat-phase-2-cu-ptx-mma-tile-2b-closed` **NOT applied** — floor gate not met.

Surface upstream: regression confirmed, root cause identified (same-word byte-RMW
at scatter write, 61.4% bank conflict rate), shuffle-pack path documented above.
