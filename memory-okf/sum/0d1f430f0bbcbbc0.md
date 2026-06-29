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
tags: [MTP gemma4 draft, grafted EAGLE heads on backbone, not separate e2b, AltUp PLE are forward heads not draft, VRAM cheap graft, batched verify prerequisite, operator insight, CONTRACT-C4-SPECDECODE corrected, gemma4 ideal MTP host, agent, tier-1]
mem_tier: summary
mem_full: 0d1f430f0bbcbbc0
---

# MTP draft = grafted EAGLE heads on the gemma4 backbone (VRAM-cheap), NOT e2b; AltUp/PLE are forward heads not draft heads; batched-verify still required

Operator insight (right): draft = small EAGLE/Medusa heads grafted on the resident 12B (same vocab, ~hundreds MB, near-zero VRAM), not a separate e2b (doesn't fit). gemma4 is graft-shaped (AltUp/PLE ~250MB) = ideal host, BUT AltUp/PLE are FORWARD heads (current-token, gemma4.c:131), not draft heads -> draft heads are new/trained, hosted as a graft. Real speedup needs: (1) batched target-verify verb, (2) grafted draft heads. Corrects C4.

Full context: [full/0d1f430f0bbcbbc0.md](../full/0d1f430f0bbcbbc0.md)
