---
type: memory
title: MTP draft = grafted EAGLE heads on the gemma4 backbone (VRAM-cheap), NOT e2b; AltUp/PLE are forward heads not draft heads; batched-verify still required
description: Operator insight (right): draft = small EAGLE/Medusa heads grafted on the resident 12B (same vocab, ~hundreds MB, near-zero VRAM), not a separate e2b (doesn't fit). gemma4 is graft-shaped (AltUp/PLE ~250MB) = ideal host, BUT AltUp/PLE are FORWARD heads (current-token, gemma4.c:131), not draft heads -> draft heads are new/trained, hosted as a graft. Real speedup needs: (1) batched target-verify verb, (2) grafted draft heads. Corrects C4.
timestamp: 2026-06-28T07:40:49Z
resource: 0bcaeff
sp_status: DESIGN
sp_gate: MTP-arch-corrected
sp_commit: 0bcaeff
sp_repro: none
mem_kind: agent
mem_addr: 0d1f430f0bbcbbc0
tags: [MTP gemma4 draft, grafted EAGLE heads on backbone, not separate e2b, AltUp PLE are forward heads not draft, VRAM cheap graft, batched verify prerequisite, operator insight, CONTRACT-C4-SPECDECODE corrected, gemma4 ideal MTP host, agent, tier-2]
mem_tier: full
---

ï»¿MTP-on-gemma4 draft architecture (operator insight, corrected + verified 2026-06-28). RIGHT draft source = GRAFTED draft heads on the resident 12B backbone (EAGLE/Medusa: predict t+1..t+K from the backbone hidden state), small (~hundreds of MB), same vocab, near-zero extra VRAM -- NOT a separate gemma4-e2b model (4.65GB, does not fit beside the 9.4GB 12B on the 12GB 2060). gemma4 is the PERFECT host: already graft-shaped (AltUp + per-layer embeddings PLE machinery, ~250MB). PRECISE CORRECTION (verified gemma4.c:125,131 + cuda k_altup_ipl): gemma4's existing AltUp/PLE heads are FORWARD-pass heads (current-token per-layer embeddings gathered by current token id, injected into the layer stack) -- NOT next-token draft heads, so NOT a drop-in draft. The draft heads are NEW (EAGLE-style, trained on the target's backbone features) but HOSTED as a graft like AltUp/PLE = VRAM-cheap. TWO prerequisites for real speedup: (1) BATCHED target-verify verb in the kvdecode path (K draft tokens -> K logits in ONE forward; the daemon spec_step verifies SEQUENTIALLY = no speedup, banked separately), (2) the grafted EAGLE draft heads (trained). NOTE '10% less cache' is DeepSeek-V4's KV-compression (separate); MTP gives forward-COUNT speedup, not cache reduction. CORRECT CONTRACT-C4-SPECDECODE: draft = grafted EAGLE heads on the 12B backbone (not e2b); verify = batched verb; both required; gemma4's graft-friendliness (AltUp/PLE) is why it's the ideal MTP host.
