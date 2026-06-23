---
type: memory
title: prefix-KV is VALID (reference ships a decode variant); self-cond NOT load-bearing (corrects earlier fact)
description: CORRECTS earlier facts: (1) the diffusion-judge recall regression / self-cond-load-bearing claim is WITHDRAWN -- self-cond correctly wired (test_diffjudge_denoise.c:437), 8.3% is native-judge weakness (95.6% is external oracle), iterative-denoise-rescue REFUTED. (2) prefix-KV VALID -- reference prompt is causal-over-prompt (never attends canvas), reference ships llm_graph_input_attn_diffusion_decode (forward only canvas/step); 6.9e-4/NaN was FALSE. NEXT=port the decode variant; re-run SP_DG_PREFIXKV_PROOF first.
timestamp: 2026-06-23T17:55:48Z
resource: TBD
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: read _diffgemma_reference/diffusion-gemma.cpp:43-54 + tests/test_diffjudge_denoise.c:437
mem_kind: agent
mem_addr: c0fab8ec85e6eb75
tags: [prefix-KV, prefixkv, llm_graph_input_attn_diffusion_decode, diffusion-gemma decode variant, self-cond not load-bearing, native judge weak, Cola E1, prefix-KV valid, agent, tier-2]
mem_tier: full
---

# prefix-KV is VALID + the self-cond was NOT load-bearing (CORRECTS the earlier "self-cond load-bearing" fact)

Verified 2026-06-24 from direct source reads (Cola E1 + harness adjudication). Two corrections to facts banked earlier the same day:

1. **The "diffusion-judge recall regression / self-cond load-bearing" claim is WITHDRAWN.** The harness self-conditioning is CORRECTLY wired (test_diffjudge_denoise.c:437 `if (use_sc && have_prev)` -> step-0 plain forward, steps 1+ feed prior logits; matches the reference step-0-gated-off SC). The killed native run scored 5/60=8.3%. 95.6% is the EXTERNAL llama.cpp oracle; our native judge was always ~25% single-forward (f8f76a5). The "iterative multi-step denoise rescues the native judge" hypothesis is REFUTED (8.3% not better than ~25%). The dg_self_cond OOB fix is a genuine correctness fix; it did NOT cause a regression. SP_DG_ASYNC byte-exact + default-off, no block.

2. **prefix-KV is VALID on the current model.** Reference _diffgemma_reference/diffusion-gemma.cpp:43-54 + ARCH-NOTES.md:40-52: prompt queries are causal-over-prompt and NEVER attend canvas; only canvas queries are bidirectional. So prompt K/V is canvas-invariant by construction, and the reference SHIPS a prefix-KV decode variant llm_graph_input_attn_diffusion_decode (rectangular [P+C,C], cache prompt K/V, forward only the canvas per step). Our 6.9e-4/NaN refutation was FALSE (fp-noise + the now-fixed OOB NaN). NOT a train-time property, NOT a Cola finetune. NEXT = PORT that decode variant (the real diffusion-judge speedup); re-run SP_DG_PREFIXKV_PROOF first. Cola block-causal does NOT map to prefix-KV.
