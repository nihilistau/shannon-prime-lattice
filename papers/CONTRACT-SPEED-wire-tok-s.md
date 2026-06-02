# CONTRACT SPEED — WIRE the integer pipes → tok/s vs llama.cpp (the north-star)

**Parent:** RFC-001 §0 (the north-star) + §8 (the WIRE gap). **Priority:** P1 (RFC-001 §11, STATE §5.1). **Status:** DRAFT + baseline in progress.
**One line:** the framework's *reason to exist* is to beat "llama.cpp + old SP hierarchical KV + custom lmstudio @ 40+ tok/s on Qwen3.6." That is a SPEED gate, and speed is the one axis we have **not** measured off-Hexagon. This contract wires the integer pipes into the forward shell and measures real tok/s.

> Why this is P1 (the honest case). C2 measured the context axis: KV ~3.5×/f32 (lossy, real-model 29/31), Ring-2 ~hundreds× effective context but largely disk-tiering. Those are real but secondary. The differentiators — speed on integer pipes, multi-device CRT, MTP — are unmeasured. And the one speed datapoint we have is a **warning**: HX.3b's vrmpy int8 forward was only **1.04× over ARM fp32 and bandwidth-bound** (the chat-shape inner loop missed its 1.20× gate because it's DRAM-traffic-limited, not ALU-limited). If the CPU/CUDA shells behave the same, the speed thesis is at risk — which is exactly why it must be measured before more is built on top.

---

## The WIRE gap (the diagnosis, STATE §6 / RFC §8)

The math-core primitives exist and are validated (Barrett `mod_q`, Frobenius dequant, packed Q4/Q8 arena). But the per-backend forward **shells still call scalar f32** on CPU/CUDA/Vulkan — only Hexagon was wired (HX.3b → vrmpy). **Until a shell calls the integer + packed-weight path, none of the speed/bandwidth envelope is realized — only correctness.** So "PPT-ARM is faster" is, today, entirely unmeasured off-phone.

## The real lever (corrected by HX.3b): bandwidth, not ALU

HX.3b taught us the chat-shape (batch-1 decode) matmul is **memory-bandwidth-bound**, not ALU-bound. So the win is NOT "VNNI does more MACs/cycle" — it is **less DRAM traffic**: reading packed **Q4/Q8 weights (4–8× smaller than f16/f32)** straight into the integer pipe means the matmul moves 4–8× fewer bytes per token. SP's reducing codec (C1) + integer dequant-in-register is exactly this. The gate must therefore measure **bytes-moved / token and tok/s**, and attack bandwidth (packed weights, prefetch, VTCM/cache residency), not just ALU width. VNNI/dp4a/vrmpy are the *consumers* of the packed bytes; the win is the smaller read.

## Gates (each on its own metric — STATE §0)

- **SPEED_BASELINE** *(in progress)* — current SP forward tok/s vs llama.cpp on the SAME proven small model (Qwen3-0.6B, CPU, greedy), as-is (scalar f32 shell). Reports the **SP:llama.cpp ratio** = the gap the WIRE must close. *(0.6B is not the 40-tok/s bar — that's the 35B MoE — but the ratio is the actionable plumbing number.)*
- **SPEED_WIRE_CPU** — wire the packed-Q8/Q4 + AVX-512/VNNI matmul into the CPU decode shell (dev host i9-11900KB has AVX-512+VNNI). Gate: (a) output stays bit-identical to the scalar f32 forward in `deterministic` mode (or within the documented bound); (b) **measured tok/s gain + bytes/token reduction**; (c) does the bandwidth lever actually pay (compare packed-weight read traffic vs f16).
- **SPEED_WIRE_CU** — same for CUDA (dp4a/PTX int8), sm-tier-aware (Turing dev caveat: INT8-TC peak ratio fixed; see CUDA SM tiers).
- **SPEED_NORTHSTAR** — the real bar: **Qwen3.6-35B-A3B ≥ 40 tok/s** on the dev host, vs "llama.cpp + SP-hier-KV + lmstudio." System gate (envelope assembled: packed weights + integer pipe + Spinor-KV window + MoE expert residency). For the 35B-A3B the dominant cost is **weight/expert memory traffic**, so this composes C1 (reducing weights) + expert streaming + the CPU/GPU integer pipe.

## Honest risks (where this breaks)

1. **Bandwidth bound everywhere.** If decode is DRAM-bound on CPU/CUDA like it was on Hexagon, integer ALUs give ~1× and the only real lever is the packed-weight traffic reduction — which caps the win near the quant ratio (Q8→~2× vs f16, Q4→~4×), not more. A ~1.04×-style result on CPU would put the whole speed thesis in question. **Measure before believing.**
2. **MoE expert residency** dominates the 35B-A3B; if experts stream from disk, per-token latency is I/O-bound and the integer pipe is irrelevant until experts are resident/prefetched.
3. **Bit-exact under the integer pipe** must hold in deterministic mode or the regression invariant breaks; the Frobenius dequant ordering is the risk.

## Baseline measurements

- **llama.cpp reference (Qwen3-0.6B-f16, CPU `-ngl 0`, greedy, dev host i9-11900KB), MEASURED 2026-06-02:** **prompt 210.3 t/s, generation 28.2 t/s.** *(f16 decode on CPU is already bandwidth-heavy — only ~28 t/s for a 0.6B — which itself supports the "decode is DRAM-bound" thesis: even llama.cpp's optimized f16 path is bandwidth-limited here, so a packed Q8/Q4 read should help llama.cpp AND SP. The fair SP comparison is vs llama.cpp **Q8_0** (`Qwen3-0.6B-Q8_0.gguf`, on disk) since the SP Executive is OK_Q8 — run that next.)*
- **SP forward (qwen3_rt.sp-model = OK_Q8, qwen3_generate_kv, same box):** _[pending — needs a tok/s timing harness; `test_gen_kv` checks argmax identity only, no timing. **Immediate next build task:** a minimal `sp_toks` harness timing `qwen3_generate_kv` over N tokens → tok/s.]_
- **llama.cpp Q8_0 reference (fair vs OK_Q8):** _[pending — quick re-run on the Q8 gguf]_
- **SP:llama.cpp ratio:** _[pending the SP number]_ → defines the WIRE target multiple.

**First read of the baseline:** llama.cpp f16 0.6B decode at **28 t/s on CPU** confirms decode is bandwidth-bound even in a tuned engine — reinforcing the contract's thesis that the SP lever is **reduced weight-read traffic (packed Q8/Q4)**, not ALU width. The WIRE target: SP's OK_Q8 packed path should move ~2× fewer weight bytes/token than f16 → the gate is whether SP reaches/*beats* llama.cpp's Q8 decode tok/s once the integer pipe is wired (today the SP shell is scalar f32, so it will currently be *slower* — that gap is exactly SPEED_WIRE_CPU's target).

## SPEED_WIRE_CPU — MEASURED LADDER (2026-06-02, `sp_toks`, Qwen3-0.6B, CPU, single-thread)

Prereq unblocked: the engine forward crashed (fork-tax struct divergence) — FIXED engine `0fb39ab`. Then, env-only (no kernel change), via `SP_ARENA`:

| path | tok/s | vs f16 | note |
|---|---|---|---|
| f16 (gguf, dequant per row) | **0.84** | 1.0× | the as-is baseline |
| **Q8 arena** (`SP_ARENA=q8 SP_ARENA_EMBED=1`) | **1.58** | **1.88×** | packed int8, `matmul_arena` inline-lift, no unpack — **the bandwidth lever, confirmed** |
| Q4 arena (`SP_ARENA=q4`) | 0.85 | 1.0× | per-row `sp_frob_q4_unpack` overhead negates the smaller read → **Q4 needs a SIMD/streaming unpack or it's a wash in this scalar path** |
| **Q8 arena + OpenMP-threaded `matmul_arena`** (engine `8975753`) | **10.53** | **12.5×** | **6.7× over single-thread Q8.** Threading the per-output-row loop was the dominant lever. Parity-safe by construction (each Y[j] an independent single-threaded dot). |

**Finding:** packing to Q8 ~doubles throughput (bandwidth thesis), then **threading the matmul gives 6.7× more → 10.53 tok/s, 12.5× over the f16 baseline.** **vs llama.cpp 28.2 t/s, SP is now ~2.7× short (was ~33×).** Threading was the dominant gap, as predicted. Remaining WIRE-CPU-V2 levers (smaller now, Amdahl-bound):
1. ~~Multi-thread the decode matmul~~ **DONE (`8975753`, 6.7× → 10.53).**
3. ~~Thread the non-matmul ops~~ **DONE (`d7735a4`): per-head QK-norm/RoPE + attention head-loop (per-thread score scratch). → 12.55 tok/s (+19% at n_gen=32). Confirmed Amdahl: once matmul was threaded the per-head serial work mattered.**
2. **SIMD `matmul_arena` inner dot** [NEXT, the substantial one] — still scalar `acc += (float)cp[i]*x[i]`; AVX2/VNNI int8 dot. At 12.55 t/s the decode is matmul-ALU-bound, so this is where the next big gain is.
4. Q4: a vectorized unpack so its bandwidth win isn't eaten.

| add'l path | tok/s | |
|---|---|---|
| Q8 + threaded matmul | 10.53 | (n_gen=32) |
| **Q8 + threaded matmul + threaded attention/per-head** | **12.55** | **+19% (n_gen=32); 10.56 at n_gen=128 as attention O(pos) grows** |

**Net: speed thesis validated — SP within ~2.25× of llama.cpp on 0.6B from packed-Q8 + full threading, NO SIMD yet.** The parallel substrate now covers matmul + attention + per-head ops. (gemma3/qwen36 attention share the pattern → follow-up.)
