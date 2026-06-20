---
type: design
title: "DESIGN — native DiffusionGemma port to the O_K/Q4B engine (no llama.cpp/ggml; PR 24423 = oracle only)"
description: "Staged native-implementation plan for the diffusion-gemma arch + entropy-bound sampler + heterogeneous MoE in the Shannon-Prime engine. Reference = PR 24423 (_diffgemma_reference/ARCH-NOTES.md). Each stage gates byte-exact / output-parity against the PR-24423 oracle. Default-off null floor on the diffusion overlay."
tags: [diffusion-gemma, native-port, phase-5, moe, cuda, o_k, q4b, diffusion-judge]
timestamp: 2026-06-21T00:00:00Z
resource: shannon-prime-lattice/papers/DESIGN-diffgemma-native-port.md
sp_status: DESIGN
sp_gate: "per-stage oracle-parity gates (pre-registered below)"
sp_commit: TBD
sp_repro: "reference _diffgemma_reference/ (PR 24423 head ef5e2dcce); oracle build D:/F/llama-diffgemma-pr24423"
---

# DESIGN — native DiffusionGemma port (O_K/Q4B engine)

**Mandate (CONTRACT-PPT-LAT-PHASE-5 §5):** write the diffusion-gemma arch + MoE + entropy-bound sampler into OUR CUDA/engine backends. **No llama.cpp/ggml in the shipped engine.** PR 24423 is the **reference** (`_diffgemma_reference/`) + the **parity oracle** ONLY. G-DIFFJUDGE-1 already justifies the build (diffusion judge 96.9% recall@1 > AR 85.7%).

**The good news (from ARCH-NOTES §1):** the diffusion-gemma backbone IS the AR gemma4 MoE graph we already run (`gemma4-common.h` shared verbatim: attention + shared-expert dense MLP + 128-expert MoE). So ~70% is the existing `cuda_forward.cu` gemma4 path + the MoE router/experts. The genuinely-new surface is **four diffusion pieces + the MoE geometry/transcode**, each small and bounded.

## The new surface (everything else is the existing gemma4 backbone)
- **D1 — region-aware bidirectional mask** over `[prompt | canvas]` (split `P = n_tok - canvas_len`): prompt query→causal (SWA-clipped), canvas query→bidirectional over all prompt+canvas (SWA layers: last n_swa-1 prompt + all canvas). THE structural win.
- **D2 — encoder/decoder split:** canvas embedding = `rmsnorm_noscale(embed*sqrt(d))` (prompt = plain `embed*sqrt(d)`); per-layer output scalar differs by region (encoder = `enc_layer_output_scale` tensor, decoder = the normal `layer_scalar`).
- **D3 — self-conditioning (SC) gated MLP:** decoder-only `SC_{pre_norm,gate,up,down}` feeds the PREVIOUS step's raw canvas logits back into the current canvas embedding. Step 0 gated off (zero SC), graph shape stable.
- **D4 — entropy-bound renoise sampler** (`diffusion-sampling.cu`, ~180 LOC, self-contained): random-init canvas → per-step forward → per-pos (argmax, entropy, multinomial denoiser) → accept lowest-entropy prefix under the MI `entropy_bound`, renoise the rest to fresh random → output = stable argmax canvas → adaptive stop (argmax stable `stability_threshold` steps AND mean-entropy < `confidence_threshold`).
- **M — MoE geometry + heterogeneous split:** Gemma-4-MoE (128 experts/8 used) in `sp_transcode` (reuse qwen35moe ~70%) + the 2-GPU/2-CPU expert split (Optane cold tier exists).

## Staged plan + pre-registered oracle-parity gates (default-off = byte-identical null floor)
- **N0 — TRANSCODE (CPU, startable NOW; GPU-free).** Add `SP_ARCH_DIFFUSION_GEMMA` to `sp_transcode`: parse the diffusion-gemma GGUF (the §3 keys: `diffusion.canvas_length`, `eb_*`, `general.attention.causal=false`) + the new tensors (`enc_layer_output_scale`, `SC_*`); reuse the gemma4 + MoE-3D-expert transcode for the backbone. Write `diffusiongemma-26B-A4B.sp-model` (OK_Q4B experts). **Gate G-DG-N0:** every mapped tensor present (hard-error on missing, like --st); header carries canvas_len + eb params; round-trip dequant rms within Q4B threshold. (No GPU — runs while G-DIFFJUDGE-1 holds the card.)
- **N1 — bidirectional region mask (CUDA).** New `k_attn_diffusion` mask kernel: prompt-causal / canvas-bidirectional, SWA-aware. **Gate G-DG-N1:** logits of a `[prompt|canvas]` forward bit-close (FP-reduction tol) to the PR-24423 oracle on the SAME tokens; default-off (`SP_DIFFUSION` unset) = the existing causal gemma4 path byte-identical.
- **N2 — encoder/decoder scalar + canvas rmsnorm embedding.** **Gate G-DG-N2:** per-region scaled residual matches oracle; reuse the byte-exact RMSNorm island.
- **N3 — self-conditioning gated MLP.** **Gate G-DG-N3:** SC feedback (prev-logits → canvas embed) matches oracle; step-0 zero-SC verified.
- **N4 — entropy-bound sampler (CUDA, port `diffusion-sampling.cu`).** Argmax exact, Z/entropy to ~1e-4; **constrained {tags,NULL} variant** = mask non-tag canvas logits to -INF (the sampler's existing mechanism). **Gate G-DG-N4:** same canvas output as the oracle on a fixed seed; the constrained judge variant reproduces G-DIFFJUDGE-1 recall on the corpus.
- **N5 — MoE Gemma-4 geometry + heterogeneous GPU/CPU split.** **Gate G-DG-N5:** PPL/forward parity vs oracle; VRAM fits 12GB with 2-resident/2-paged experts; tok/s measured.
- **N6 — native diffusion JUDGE in the daemon (Stage-2 selector).** Replace the AR judge with the native diffusion canvas judge; **Gate G-DG-N6:** match G-DIFFJUDGE-1 recall + beat the AR foreign-reject wobble, on the live `_needle_corpus_div`.
- **(later) N7 — T8 DRAFTER:** diffusion drafts a 256-canvas block, AR 12B verifies exact (lossless). The zero-risk speed win.

## Non-negotiables
Reference-first (read `_diffgemma_reference/*.cpp/.cu` file:line before each kernel). Every stage gates byte-exact/output-parity vs the PR-24423 oracle. `SP_DIFFUSION` overlay default-off = byte-identical to the current AR engine. The four nonlinear islands (RMSNorm etc.) reuse the existing exact-integer kernels. Anti-contamination: our code, our O_K/Q4B containers — only the algorithm is referenced.

## ⚠ SEQUENCING CORRECTION (2026-06-21, discovered at N1a — verify-the-tree)
N1a (loader) landed GREEN (`sp_model_to_diffusion_gemma` bridge, gate G_DG_N1 26/26, engine `68cd7ff`). But reading the tree revealed the "~70% reuse" is true at the MATH level only: **the engine's CUDA forward (`cuda_forward.cu`) is DENSE-ONLY — there is NO MoE/expert support on the GPU path** (no router, no top-8, no expert GEMM). The MoE forward exists ONLY on the CPU core (`qwen36.c`). DiffusionGemma is a 128-expert/8-used MoE. So **a CUDA MoE backbone (N5a) is a PREREQUISITE for the N1b region-aware forward**, not a late stage. N5 splits: **N5a = CUDA MoE forward** (port `qwen36.c` MoE → `cuda_forward.cu`: F32 router GEMV → top-8 softmax → per-expert OK_Q4B dp4a over the fused `ffn_gate_up_exps` + `ffn_down_exps`, weighted-sum; gate **G-DG-N5a** byte-exact vs the CPU MoE on one block) — comes FIRST; **N5b = heterogeneous GPU/CPU expert split** (the later 2-resident/2-paged optimization) — stays late. Once N5a exists, N1b is the small region-aware overlay (mask + canvas-rmsnorm-embed + enc/dec scalar) behind `SP_DIFFUSION`.

## Start order (CORRECTED)
N0 (transcode) ✓ → N1a (loader) ✓ → **N5a (CUDA MoE forward — the discovered prerequisite)** → N1b (region-aware [prompt|canvas] overlay + oracle logit-parity) → N2 (enc/dec scalar+rmsnorm, folds into N1b) → N3 (self-cond) → N4 (entropy sampler) → N5b (hetero MoE split) → N6 (native judge) → N7 (drafter).
