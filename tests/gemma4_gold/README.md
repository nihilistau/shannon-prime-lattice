# gemma4_gold — the hand-written full-precision reference (T2 GOLD)

**The number: gemma-4-12b full-precision wikitext chunk-0 PPL = 4.6776** —
where llama.cpp scores 397–505 on the identical fixture. llama.cpp's gemma4
stack is ~100× broken on this model; these scripts are the reference until
the forward-vs-conversion fork resolves. See CONTRACT-SPEED §ADDENDUM
2026-06-07 for the formal amendment and consequence chain.

> **RESOLVED (2026-06-08, kept for the record — the paragraph above is the
> pre-resolution framing):** the discriminator ran — gold arithmetic over the
> GGUF's own dequantized tensors REPRODUCES the breakage (pre-fix 271–364;
> post-June-5 rebuilt GGUF still 192.9) ⇒ the **artifacts are condemned,
> llama.cpp's forward is exonerated**. The GGUF lane is dead for this model;
> the trusted weight path is Safetensors Direct (`sp_transcode --st`).
> Full record: CONTRACT-SPEED (RESOLUTION) + STATE §5.13; public LEDGER 06-R8.

## Instruments

- `_t2_manual_forward.py` — from-scratch torch forward off the official bf16
  safetensors (`D:\Files\Models\Gemma4\gemma-4-12b-bucket`) + config alone.
  No transformers, no llama.cpp. Receipt: `_t2_gold.log` (PPL 4.6776,
  targets at max-logit nll≈0.001). Needs ~24 GB RAM (holds bf16 weights).
- `_t2b_gguf_forensics.py` — GGUF↔safetensors tensor diff. Killed the
  +1-norm converter theory (q/k_norm byte-identical); found three different
  `layer_scalar` sets across QAT / Q4_K_M / safetensors (QAT retrain drift).
- `_t2c_gold_on_gguf.py` — THE DISCRIMINATOR (queued): gold arithmetic over
  the QAT GGUF's own dequantized tensors + its rope_freqs table. Streaming
  (row-gather embed, per-layer load/free, chunked tied head; ~1.5 GB peak).
  Single-digit ⇒ llama.cpp FORWARD condemned; ~400 ⇒ GGUF CONVERSION
  condemned. Partial log `_t2c_v2.log` (blocked on host memory wedge).

## Proven gemma-4-12b conventions (validated by the 4.68)

Plain-multiplier RMSNorm (NOT gemma-classic 1+w); V-less globals — V = the
RAW K projection (pre-k_norm), weightless RMS-norm, never roped; attention
scale 1.0; partial rotary 0.25 on globals via the rope_freqs factor table
(1.0 ×64 pairs, then 1e30 = frozen) over θ=1e6; SWA full-rotation θ=1e4;
GeGLU gelu_pytorch_tanh; sandwich norms; per-layer `layer_scalar` after the
FFN residual; embed ×√3840; tied head; softcap tanh(z/30)·30.

Fixture: `_g4_12b_wiki_tokens.txt` (llama-dumped, verified == HF
tokenizer.json 5431/5431). Protocol: chunk 0 of 512, BOS first, score
targets [256,512), teacher-forced f32 log-softmax.
