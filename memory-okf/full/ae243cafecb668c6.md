---
type: memory
title: B6 cheap looping/aliasing of gemma-4-12b REFUTED: adjacent-l
description: B6 cheap looping/aliasing of gemma-4-12b REFUTED: adjacent-layer weight cosine ~0 (best 0.012) vs ~0.98 viable; period-6 global/SWA interleave blocks whole-stack aliasing; looped variant needs heavy retrain. PARKED.
timestamp: 2026-07-08T19:24:57Z
resource: TBD
sp_status: HONEST-NEGATIVE
sp_gate: G-B6-LAYERSIM
sp_commit: TBD
sp_repro: none
mem_kind: agent
mem_addr: ae243cafecb668c6
mem_verified: unverified
mem_lifecycle: active
tags: [b6, recursive-gemma, looped-transformer, layer-similarity, aliasing, middle-looping, honest-negative, G-B6-LAYERSIM, agent, tier-2]
mem_tier: full
---

B6 recursive/looped Gemma-4-12b — CHEAP looping/aliasing REFUTED (G-B6-LAYERSIM, offline bf16 probe).
Adjacent-layer weight cosine similarity across the 48 decoder layers is ~0.000 for q/k/v/o/up/down_proj and only ~0.005-0.012 for gate_proj (mid-band 0.0067, peak 0.0117 near L12-16/L33-35) — about two orders of magnitude below the ~0.98 that makes weight-sharing/looping viable (arXiv 2502.17416). No contiguous high-similarity middle band. Per-output-row cosine on down_proj agrees (~0.000), so it is genuine directional orthogonality, not a scale artifact (Frobenius norm ratios ~1.0 across depth = uniform scale, orthogonal direction). STRUCTURAL blocker: Gemma-4 interleaves attention shapes at period 6 (8 V-less GLOBAL layers L%6==5 vs 40 SWA), so whole-stack aliasing is impossible regardless of similarity; a loop block must span a full 6-layer period. CONSEQUENCE: a looped/recursive Gemma is NOT a cheap alias-and-finetune (Relaxed-Recursive 2410.20672 init-from-layers assumption does not hold here) — it needs heavy near-from-scratch training of the shared block. B6 PARKED as high-cost/low-priority. Caveat: raw-weight cosine ignores permutation/rotation equivalence (layers could be similar up to hidden-basis permutation), but low raw cosine is the correct first-order signal for 'is aliasing cheap' — the answer is a clear no. Source D:/Files/Models/Gemma4/gemma-4-12b-bucket/model.safetensors; receipt engine tests/fixtures/b6_probe/G-B6-LAYERSIM.log.
