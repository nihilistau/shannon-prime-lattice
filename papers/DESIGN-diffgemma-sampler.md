---
type: design
title: "DESIGN — N3 self-conditioning + N4-full entropy-bound denoise sampler (native DiffusionGemma judge)"
description: "Reference-first spec for the multi-step entropy-bound denoising loop + self-conditioning on the native diffusion_gemma_forward_cuda, and the constrained {tags,NULL} denoise judge. Built ONLY if the single-forward G-DIFFJUDGE-NATIVE run comes back low; also the substrate for the N7 drafter. Reference = PR 24423 (_diffgemma_reference/diffusion-sampling.cu read in full + ARCH-NOTES §2)."
tags: [diffusion-gemma, sampler, entropy-bound, self-conditioning, phase-5, native-port, diffusion-judge, drafter]
timestamp: 2026-06-21T00:00:00Z
resource: shannon-prime-lattice/papers/DESIGN-diffgemma-sampler.md
sp_status: DESIGN
sp_gate: "G-DG-N4 / G-DG-N3 / G-DIFFJUDGE-NATIVE-full (pre-registered below)"
sp_commit: TBD
sp_repro: "reference _diffgemma_reference/diffusion-sampling.cu + ARCH-NOTES §2; forward = engine 8309d90 diffusion_gemma_forward_cuda"
---

# DESIGN — N3 self-conditioning + N4-full entropy-bound sampler

**Trigger:** build this iff the live single-forward `G-DIFFJUDGE-NATIVE` run (engine `3e791f6`/`8309d90`) returns low recall (the leading hypothesis: a step-0 forward is a blurry first guess; the oracle's 95.6% came from the FULL iterative denoising). It is ALSO the substrate the **N7 drafter** rides (block-diffusion draft → AR verify), so it is never wasted. **Reference-first done:** `_diffgemma_reference/diffusion-sampling.cu` read in full; host loop = ARCH-NOTES §2.

## Key simplification (grounds the effort)
The sampler is **pure vocab-space float math on the logits the forward already produces** — NO weights, NO O_K/Q4B quant. `diffusion_dense_sample_kernel` (one CUDA block per canvas position) computes, per position: argmax (parallel max-reduce), entropy `= logf(Z) - T/Z` with `Z=Σ exp(d)`, `T=Σ d·exp(d)`, `d = logit·inv_temp - max`, and a multinomial draw (first vocab-order v where cumulative `exp(d) ≥ r=u·Z`, via a 256-slice exclusive-scan so serial work is one slice not the whole vocab). **It ports near-verbatim into our CUDA backend** (drop the ggml_tensor wrapper; feed our device logits pointer + n_vocab + a per-position u[] of seeded uniforms; return argmax/entropy/sampled). Argmax exact; Z/entropy match the host worker to ~1e-4 (FP reduction order).

## N4-full — the entropy-bound denoise loop (host orchestration + the device kernel)
Host loop (mirror `diffusion_generate_entropy_bound`, ARCH-NOTES §2):
```
C = canvas_length (256); S = eb_max_steps (default 48; our GGUF omits eb_* -> use the recommended defaults:
  t_max 0.8 -> t_min 0.4 linear, entropy_bound 0.1, stability_threshold 2, confidence_threshold 0.005)
canvas[0..C) <- seeded random vocab ids          # deterministic RNG => reproducible
prev_argmax <- -1; held <- 0; prev_logits <- none
for step in 0..S:
    inv_temp = 1 / lerp(t_max, t_min, step/S)
    logits = diffusion_gemma_forward_cuda([prompt | canvas], self_cond = prev_logits if step>0 else off)
    (argmax[], entropy[], denoiser[]) = sample_kernel(logits, u=seeded_uniforms, inv_temp)   # the ported kernel
    order canvas positions by ASCENDING entropy
    cumE=0; for pos in order: accept[pos] = (cumE <= entropy_bound); cumE += entropy[pos]   # MI prefix bound
    for pos: canvas[pos] = accept[pos] ? denoiser[pos] : fresh_seeded_random      # renoise the uncertain
    output_canvas[pos] = argmax[pos]                                               # OUTPUT is always the argmax canvas
    held = (prev_argmax == argmax) ? held+1 : 0
    if held >= stability_threshold AND mean(entropy) < confidence_threshold: STOP  # adaptive early stop
    prev_argmax = argmax; prev_logits = raw canvas logits (for N3 self-cond)
return output_canvas
```
Notes: the reported answer is ALWAYS the stable argmax canvas (independent of the renoise draw). Adaptive stop usually halts well before S. Behind `SP_DIFFUSION` (default-off = the existing AR engine byte-identical).

**Gate G-DG-N4:** (a) the ported `sample_kernel` matches the reference device kernel argmax (exact) + entropy (~1e-4) on a fixed logit fixture; (b) the full loop on a FIXED seed produces the same `output_canvas` as the oracle `llama-diffusion-gemma-eval` (UNIFIED, same seed) — top-1 canvas agreement high (modulo the OK_Q4B vs Q4_K_M weight-quant delta in the forward, which is the documented confound — gate on argmax-canvas agreement, not byte-exact logits).

## N3 — self-conditioning (needed for multi-step quality)
The SC decoder-only gated MLP (tensors `self_cond_{pre_norm,gate,up,down}`, loaded in N1a) feeds the PREVIOUS step's raw canvas logits back into the CURRENT step's canvas embedding. Step 0: no previous → SC subgraph kept (stable graph shape) but gated OFF (zero SC). Implementation: after computing canvas logits at step t, keep them (`[n_vocab, C]`, ~268MB host or a persistent device buffer — prefer device per the reference `dev_sc`/`gpu_sampling` to avoid the host upload); at step t+1, the SC MLP `down(gelu(gate(pre_norm(prev_logits))) · up(...))` adds into the canvas embedding before layer 0. Reuse the existing GeGLU + RMSNorm kernels.
**Gate G-DG-N3:** the SC feedback (prev-logits → canvas-embed delta) matches the reference on a fixed prev-logits fixture; step-0 zero-SC verified (a 1-step run == the N1b single-forward, byte-identical).

## The constrained {tags,NULL} denoise JUDGE (the real deliverable)
Run the N4-full loop with the canvas answer position(s) HARD-MASKED to `{tag tokens, NULL}` (set every other vocab logit to -INF) BEFORE the sample kernel each step — so the canvas can only ever resolve to a tag or NULL, and the iterative refinement sharpens onto the right one (curing the single-forward Marlock-style miss). Reuse the N4 harness `tests/test_diffjudge_native.c` (the tag tokenization + the resident-model div-corpus loop are already built) — just swap the single-forward+argmax for the masked denoise loop.
**Gate G-DIFFJUDGE-NATIVE-full:** the constrained denoise judge reproduces the oracle's recall on `_needle_corpus_div` (target ≥ ~90% recall@1; oracle 95.6/96.0). THIS closes the native judge.

## Sequencing (only if the single-forward run is low)
N4-full sampler kernel port + host loop (G-DG-N4) → N3 self-conditioning (G-DG-N3) → constrained denoise judge (G-DIFFJUDGE-NATIVE-full) → N6 (wire the native judge into routes.rs, replacing the AR judge) → N7 (drafter: diffusion drafts a 256-block, AR 12B verifies exact). All behind `SP_DIFFUSION`, default-off = null floor; receipts-first per stage.

## Cost / honesty
Per-step forward ≈ 71s (the streamed 26B); up to 48 steps but adaptive stop usually cuts it. So a denoise judge query is ~minutes (vs the single-forward ~200s) — slower, but the native O_K/Q4B + N5b hetero expert split + the prompt-KV-cache decode path (DG_KVCACHE: prefill the prompt once, denoise only the canvas) are the levers to bring it down. The byte-exact-vs-Q4_K_M-oracle confound remains (different quants); the meaningful gate stays SELECTION fidelity.
