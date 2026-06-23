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
tags: [prefix-KV, prefixkv, llm_graph_input_attn_diffusion_decode, diffusion-gemma decode variant, self-cond not load-bearing, native judge weak, Cola E1, prefix-KV valid, agent, tier-1]
mem_tier: summary
mem_full: c0fab8ec85e6eb75
---

# prefix-KV is VALID (reference ships a decode variant); self-cond NOT load-bearing (corrects earlier fact)

CORRECTS earlier facts: (1) the diffusion-judge recall regression / self-cond-load-bearing claim is WITHDRAWN -- self-cond correctly wired (test_diffjudge_denoise.c:437), 8.3% is native-judge weakness (95.6% is external oracle), iterative-denoise-rescue REFUTED. (2) prefix-KV VALID -- reference prompt is causal-over-prompt (never attends canvas), reference ships llm_graph_input_attn_diffusion_decode (forward only canvas/step); 6.9e-4/NaN was FALSE. NEXT=port the decode variant; re-run SP_DG_PREFIXKV_PROOF first.

Full context: [full/c0fab8ec85e6eb75.md](../full/c0fab8ec85e6eb75.md)
