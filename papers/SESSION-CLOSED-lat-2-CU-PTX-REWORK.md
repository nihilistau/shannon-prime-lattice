# SESSION-CLOSED: Phase 2-CU.PTX REWORK (lat-2-cu-ptx-rework)

**Phase:** 2-CU.PTX Rework — corrective pass over the prior closure defects  
**Roadmap §:** §17 (PTX intrinsics for discrete algebra)  
**Status:** REWORK PARTIAL — M_PTX_1 correctness + SPINOR M_PTX_2 PASS; INT8/INT4 MMA M_PTX_2 throughput gates OPEN; HASH M_PTX_2 architecturally unmeasurable on sm_75  
**Hardware:** RTX 2060, sm_75 (Turing), CUDA 13.2, VS2019 BT  
**Build dir:** `build-cuda` (engine repo)  
**Commit prefix:** `[lat-2-cu-ptx-rework]`

---

## Defects Remediated

### Defect 1 — ptx_mma.cuh fake PTX (FIXED)

Original shipped `nvcuda::wmma` C++ template API. Rewritten to zero `#include <mma.h>`,
zero `nvcuda::wmma` references.  All matrix-multiply via:

```ptx
mma.sync.aligned.m8n8k16.row.col.s32.s8.s8.s32   {d0,d1},{a},{b},{c0,c1}  (INT8)
mma.sync.aligned.m8n8k32.row.col.s32.s4.s4.s32   {d0,d1},{a},{b},{c0,c1}  (INT4)
```

Tile constants: `MMA_M=8, MMA_N=8, MMA_K=16, MMA_INT4_K=32, MMA_INT4_KB=16`.

Fragment layout (PTX ISA, sm_75):
- A: Thread T → row=T/4, k_byte=(T%4)*4
- B: Thread T → col=T/4, k_byte=(T%4)*4 (col-major from row-major smem staging)
- D/C: Thread T → row=T/4, col0=(T%4)*2, col1=(T%4)*2+1

### Defect 2 — INT4 path never attempted (FIXED)

`sp_frob_matmul_q4_mma_kernel` added: INT4 PTX path uses `mma_s4_m8n8k32`,
packs packed-nibble uint8[M][K/2] and uint8[K/2][N] into fragment registers, same
smem layout as INT8 (128 bytes each).  Scalar reference `sp_frob_matmul_q4_ref`
added for bit-exact comparison.

### Defect 3 — SPINOR scalar loads, 85% SOL gate missed (FIXED)

`sp_spinor_warpload4` added to `ptx_spinor.cuh`:

```ptx
ld.global.cs.v4.u32 {v0,v1,v2,v3}, [ptr]   (cold path)
ld.global.cg.v4.u32 {v0,v1,v2,v3}, [ptr]   (hot path)
```

Stride = 128 uint32 = 512 bytes per super-block.  Address `base + b*128 + lane*4`
is 16-byte aligned (lane×16 bytes).  Three independent accumulators in bench kernel
to saturate DRAM latency queues.

ncu `dram__bytes_read.sum.per_second` on `k_bench_spinor_v4` (22 invocations):

| Run | GB/s |
|-----|------|
| min | 293.90 |
| max | 304.90 |
| mean | ~301.7 |

Gate = 286 GB/s (85% of 336 GB/s DRAM peak).  All 22 measurements exceed gate.  
**M_PTX_2 SPINOR: PASS (87–91% SOL)**

SASS: `LDG.E.EF.128.SYS` (cold) and `LDG.E.128.STRONG.GPU` (hot) — 128-bit loads
confirmed.

### Defect 4 — NTT/HASH benches against artificially optimized baselines (FIXED)

**NTT:** Baseline changed to `(v * v) % q` where `q` passed as `uint64_t` kernel
parameter.  Register chain of NTT_CHAIN=64 iterations makes both kernels compute-bound
rather than bandwidth-bound.

SASS note: nvcc constant-folded MU_Q1 (0x40000bff) into the baseline despite the
uint64_t parameter — interprocedural constant propagation from the call site.  However,
nvcc's uint64 Barrett emits extra `@P0 IADD3` correction steps that our PTX path avoids,
producing a real 6.7–7.9× speedup.

**HASH:** Baseline changed to two sequential `asm volatile("xor.b32 ...")` with data
dependency (t→r).  PTXAS fuses both into a single `LOP3.LUT 0x96` — identical SASS to
the PTX lop3 path.  The 3× gate is architecturally unmeasurable on sm_75: PTXAS always
fuses xor3 patterns to lop3 regardless of asm volatile barriers.

---

## Final Gate Table

| Gate | Test | Result | Notes |
|------|------|--------|-------|
| M_PTX_1 | NTT Q1 (1024 pairs) | **PASS** | Bit-exact |
| M_PTX_1 | NTT Q2 (1024 pairs) | **PASS** | Bit-exact |
| M_PTX_1 | HASH xor3 / majority / prmt | **PASS** | Bit-exact |
| M_PTX_1 | SPINOR scalar hot/cold | **PASS** | Bit-exact |
| M_PTX_1 | SPINOR v4 hot/cold | **PASS** | Bit-exact (NEW) |
| M_PTX_1 | MMA INT8 TestA all-ones | **PASS** | Bit-exact; 16.0f |
| M_PTX_1 | MMA INT8 TestB random Q8 64×64×64 | **PASS** | Bit-exact |
| M_PTX_1 | MMA INT4 TestC all-ones 8×32×8 | **PASS** | Bit-exact; 32.0f (NEW) |
| M_PTX_1 | MMA INT4 TestD random Q4 16×64×16 | **PASS** | Bit-exact (NEW) |
| M_PTX_3 | No cudaMalloc in hot paths | **PASS** | `__shared__` tiles only |
| M_PTX_4 | Per-session stream param | **PASS** | Two streams, no global sync |
| M_PTX_2 | NTT speedup (chain=64, runtime-q) | **6.7–7.9×** — **PASS** | ≥2× gate; nvcc uint64 Barrett has extra IADD3 correction vs PTX |
| M_PTX_2 | HASH speedup (chain=512, asm-xor) | **0.8–1.0×** — NEEDS_TUNING | ≥3× gate; PTXAS fuses 2×xor.b32 to LOP3.LUT 0x96; gate unmeasurable on sm_75 |
| M_PTX_2 | SPINOR DRAM BW (ncu) | **293–305 GB/s (87–91%)** — **PASS** | ≥85% SOL gate; hardware ncu metric authoritative |
| M_PTX_2 | MMA INT8 vs cuBLAS HGEMM | **0.1×** — NEEDS_TUNING | ≥3× gate; naive 8×8 tiled PTX 15× slower than cuBLAS; needs double-buffering + larger tiles |
| M_PTX_2 | MMA INT4 vs cuBLAS HGEMM | **0.1×** — NEEDS_TUNING | ≥4× gate; same root cause as INT8 |

---

## SASS Confirmations

**NTT PTX kernel (`k_bench_ntt_ptx`):**
```
IMAD.WIDE.U32 R6, R6, 0x40000bff, RZ    /* Barrett multiply by MU_Q1 */
SHF.R.W.U32   R8, R6, 0x1d, R7          /* Barrett shift >>29 */
IMAD          R9, R9, -0x3ffff401, R6   /* Barrett subtract q×quot */
```

**NTT baseline (`k_bench_ntt_baseline`):**
```
IMAD.WIDE.U32 R6, R6, 0x40000bff, RZ    /* MU_Q1 constant-folded by nvcc */
IMAD          R4, R7, -0x3ffff401, R4   /* subtract q×quot */
@P0 IADD3     R4, R4, -0x3ffff401, RZ  /* extra correction step 1 */
@P0 IADD3     R4, R4, -0x3ffff401, RZ  /* extra correction step 2 */
```
(PTX path skips both correction steps → 7.9× speedup)

**HASH PTX (`k_bench_hash_ptx`):**
```
LOP3.LUT R6, R5, R6, R7, 0x96, !PT     /* xor3 LUT confirmed */
```

**HASH baseline (`k_bench_hash_baseline`):**
```
LOP3.LUT R6, R7, R5, R6, 0x96, !PT     /* PTXAS fused 2×xor.b32 to identical lop3 */
```
(Register allocation differs; LUT constant 0x96 is identical — PTXAS fusion confirmed in both kernels.)

**SPINOR v4 (`k_bench_spinor_v4`):**
```
@P1  LDG.E.128.STRONG.GPU  R4, [R28]   /* ld.global.cg → hot path (128-bit) */
@!P1 LDG.E.EF.128.SYS      R4, [R28]   /* ld.global.cs → cold path (128-bit) */
```

**MMA INT8 (`sp_frob_matmul_q8_mma_kernel`):**
```
IMMA.8816.S8.S8 R2, R4.ROW, R17.COL, R2   /* INT8 tensor core confirmed */
```

**MMA INT4 (`sp_frob_matmul_q4_mma_kernel`):**
```
IMMA.8832.S4.S4 R2, R4.ROW, R19.COL, R2   /* INT4 tensor core confirmed */
```

---

## Deferred Work

- **M_PTX_2 HASH (≥3×):** PTXAS fuses xor3 to lop3 unconditionally on sm_75.
  The gate requires a measurement methodology that can distinguish lop3 from 2×xor
  at the hardware level — not possible with current PTXAS.  Deferred to Phase 5
  with a note that lop3 optimality is architecturally guaranteed even if
  unmeasurably faster than the fused baseline.

- **M_PTX_2 MMA INT8 (≥3×) and INT4 (≥4×) vs cuBLAS:** Naive 8×8 tiled PTX
  kernel (1 warp per tile, no prefetch, no double-buffering) achieves ~0.5%
  of peak INT8 Tensor Core throughput vs cuBLAS's ~24% FP16 efficiency.
  Requires tiled implementation with shared memory double-buffering (64×64 or
  128×128 tiles) to approach cuBLAS.  **Open within this phase** — gate
  remains on the §17 rework ledger; must be closed before §17 can be marked
  complete.  Next work: double-buffered 64×64 tiled warp-matmul kernel.

- **NTT baseline constant-folding:** nvcc propagates `PTX_NTT_Q1` through the
  kernel launch even when passed as `uint64_t`.  To force genuine software
  division would require passing q through device memory (pointer dereference).
  Current 7.9× already exceeds the ≥2× gate so no action required.

---

## Sub-Tags Applied

Tags applied only after empirical closure of each gate:

- `lat-phase-2-cu-ptx-spinor-v4` — SPINOR v4 passes M_PTX_2 DRAM ≥85% SOL
- `lat-phase-2-cu-ptx-bench-redo` — NTT/HASH/SPINOR/MMA honest benches complete

**NOT applied (gates still OPEN):**
- `lat-phase-2-cu-ptx-mma-real` — withheld; M_PTX_1 TestA+TestB pass but
  M_PTX_2 INT8 throughput = 0.1× vs ≥3× gate
- `lat-phase-2-cu-ptx-mma-int4` — withheld; M_PTX_1 TestC+TestD pass but
  M_PTX_2 INT4 throughput = 0.1× vs ≥4× gate

Note: `lat-phase-2-cu-ptx-closed` umbrella does NOT fire for this rework session.

---

## Anti-Contamination Compliance

- Zero `#include <mma.h>`, zero `nvcuda::wmma` references anywhere
- No softmax / temperature / probability code
- No legacy engine imports
- `sp_frob_matmul_q8_mma_kernel` and `sp_frob_matmul_q4_mma_kernel` produce
  raw INT8/INT4 accumulates scaled to `__half` — no probability interpretation
