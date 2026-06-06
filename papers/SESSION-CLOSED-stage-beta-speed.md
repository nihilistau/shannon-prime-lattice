# SESSION-CLOSED — Stage Beta speed: CUDA graphs + the INT8/Q4 dp4a ladder (2026-06-06)

**Scope:** turn the Stage-Beta GPU decode (Beta-S0) into a real speed story —
CUDA graphs, then the discrete-quant memory-bandwidth win — all gated bit-exact /
top-1-lossless on the actual RTX 2060 (12 GB, Turing sm_75). Companion:
PPT-LAT-STATE §5.09, PPT-LAT-Roadmap §21, CONTRACT-SPEED, engine
`src/backends/cuda/cuda_forward.cu` + `tests/{test_qwen3_decode_cuda.c,
bench_gemv_int8.cu}`, memory `project-stage-beta-rtx2060`.

## The honest arc (with the corrections — no spin)

This session shipped three numbers that were WRONG before they were right. The
corrections are the point; they are why the final numbers are trustworthy.

1. **BETA.2 "12.65×" → ~1.06× (CUDA graphs).** First commit (`ebcbedb`) timed
   the per-step path COLD (first in a fresh process: CUDA lazy module load +
   cuBLAS JIT/heuristic) against the graph path WARM (second). With a warmup
   pass + `n_gen=256` + clocks pinned, graphs are a real but small **~6%**.
   Launch overhead was never the dominant wall — **cold-start was** (~13×
   first-decode penalty; a persistent warm daemon captures it for free).
2. **BETA.3a "Q8 slower"/"2.81×" → regime-dependent.** Short-window jitter
   (n_gen=24 ≈ 0.3s, readings swung 32/88/92) then a throttled-memory-clock
   artifact. `nvidia-smi -lgc` locks only the SM clock; a weight-GEMV is
   *memory*-bound, so its tok/s tracked the free-running GDDR6 clock. With BOTH
   clocks at full speed the 0.6B decode is **overhead-bound** — f32 == Q8 ==
   Q4 == ~91 tok/s, all converge (weight matmuls aren't the bottleneck at that
   scale; Amdahl).
3. The real win lives in the **isolated GEMV sweep**, where the matmul is the
   only thing measured.

## Position-indirect CUDA-graph decode (BETA.2)

A captured graph freezes every node's args; the per-step loop changes them
(embed reads `dseq+pos`, KV-store offset, attn ctx/shared-mem, argmax target).
Fix: hold `pos` in a device scalar `int *dpos`; new kernels `k_embed_at`,
`k_rope_dyn`, `k_kv_store`, `k_attn_decode_dyn`, `k_argmax_at`, `k_incr_pos`
dereference it, so topology + params stay constant → `cudaStreamBeginCapture`
once, `cudaGraphLaunch` ×n_gen. cuBLAS SGEMM + arena-dequant kernels are
capture-safe; prompt ingest stays per-step; fixed attn shared-mem = P floats,
48 KB sm_75 guard. `SP_CUDA_DECODE_GRAPH=1`.

## The fused dp4a GEMV + the bandwidth ladder (BETA.3)

`SP_CUDA_DECODE_INT8=1` routes packed matmuls through a fused GEMV that reads the
1-byte (Q8) / 0.5-byte (Q4) arena codes **straight from VRAM** — no f32 scratch
materialization — with dynamic per-vector int8 activation quant and `__dp4a`
INT8·INT8→INT32. Tuned kernels: warp-per-row, 128-bit `int4` loads,
`__shfl_down_sync` reduction. The Q4 kernel unpacks nibbles → int8 in the ALU
(free under memory-bound). **Per-tensor precision dispatch** (`DevTensor.prec`,
from the arena's per-row precision) sends each matmul to the right kernel — this
is what makes K-quant mixes (Q4_K_M keeps the head/embeddings at Q8, body Q4)
correct.

**ISOLATED GEMV SWEEP** (`tests/bench_gemv_int8.cu`, single-token M=1, both clocks
pinned, host-reference correctness gate):

| bytes/weight | path | speedup vs f32 @N≥12K | eff GB/s |
| ------------ | ---- | --------------------- | -------- |
| 4.0 | f32 cuBLAS SGEMV | 1.0× (baseline) | ~290 (86% of 336 peak, bus-saturated) |
| 1.0 | int8 dp4a GEMV | ~3.8× | ~280 |
| 0.5 | Q4 dp4a GEMV | **~7.06×** | ~260 |

Each halving of bytes/weight ~doubles throughput, tracking the byte ratio (4:1,
8:1) minus a shrinking margin (Q4's ~7% nibble-unpack ALU tax). Crossover
(overhead → bus-bound) ≈ N=2K: the 0.6B matmuls sit below it (and are masked by
decode overhead → int8/Q4 tie f32 there); a 12B (hidden ~3840, FF ~15360) sits
firmly in the ~7× regime. Q4 correctness vs host ref: **max rel err 1.34e-7**.

## Production wiring + the bug the gate caught

Q4-dp4a wired into `qwen3_decode_cuda` (ingest + per-step + graph-capture). The
production gate caught a bug the isolated bench could not (it used uniform
synthetic Q4): the `SP_ARENA=q4` arena is MIXED PRECISION; dispatching on the
GLOBAL arena precision read the Q8 head as Q4 → **Q4 top-1 0/256**. Fix:
`DevTensor` carries a host-side per-TENSOR `prec` (from `row_prec[0]` + a
uniformity scan → dequant fallback for mixed rows); `gemv_w_packed` dispatches on
`W->prec`. LESSON: isolated benches validate kernel MATH; production gates
validate the DATA-STRUCTURE handoff.

## Gates (all green)

| gate | result |
|---|---|
| `M_QWEN3_DECODE_CUDA` | **28/28** — f32 / Q8 / Q4 / `.sp-model` all 256/256 top-1 lossless (dp4a == dequant graph), graph == per-step byte-exact, decode == prefill teacher-forced |
| `bench_gemv_int8` Q4 correctness | max rel err 1.34e-7 vs host reference |
| `.sp-model` adapter (`2138f89`) | older `arch_struct_size=56` artifacts load via growth-discipline min-copy |

## Commits

Engine: `ebcbedb` (graphs) → `664fae1` (warmup correction) → `2138f89`
(.sp-model adapter min-copy) → `bd87e99` (dp4a int8) → `3d43705` (dp4a v2 +
regime correction) → `050fd84` (Q4 dp4a bench) → `a6c9d9f` (Q4 wired to decode +
per-tensor prec) → `17666f0` (README). Lattice: CONTRACT-SPEED updates +
`stage-alpha-closed-beta-opened-2026-06-06` tag lineage.

## Methodology rules (now standing)

1. No GPU tok/s number without **warmup** + **long window (n_gen≥256)** + **both
   clocks pinned** (`-lgc` locks SM only; GDDR6 must be at full speed for a
   memory-bound GEMV; GeForce `-lmc` is flaky — it auto-boosts under load).
2. Confirm the kernel is on the **binding bottleneck** (Amdahl) before claiming a
   win — at 0.6B the decode is overhead-bound, not bandwidth-bound.
3. **Trust within-run ratios over absolutes** (clock/thermal drift moves the
   absolute even when locked; the ratio is measured back-to-back).
4. Isolated bench = kernel math; production gate = data-structure handoff. Both.

## Next

Stage Eta (Gemma4-CUDA, branch `stage-eta-gemma4-cuda`) — the per-layer-geometry
forward + decode where the ~7× Q4 win drives a real tok/s number on the 12B.
Resume at ETA.1 (adapter + weightless V-norm). See
`project-stage-eta-gemma4-cuda` + Roadmap §21/§19.
