---
type: memory
title: PF-B5: system-curatable personality (consolidate_personality
description: PF-B5: system-curatable personality (consolidate_personality) — extract transcript shifts, prune traits, snapshot to memory-okf-personality tier. G-PF-CURATE GREEN e35cfdf.
timestamp: 2026-07-04T00:47:02Z
resource: TBD
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
mem_kind: agent
mem_addr: pf-b5-personality-curation
tags: [PF-B5, personality curation, consolidate_personality, memory-okf-personality, G-PF-CURATE, NIGHTSHIFT personality, system-curatable personality, personality snapshot, agent, tier-2]
mem_tier: full
---

ï»¿PF-B5 GREEN (harness e35cfdf): consolidate_personality (harness/personality/curator.py) curates the personality the way NIGHTSHIFT curates memory. (1) EXTRACTS shifts the model expressed in a transcript by reusing PF-B3 apply_personality_tags on assistant turns; (2) PRUNES/dedups stale traits (MAX_TRAITS=8); (3) SNAPSHOTS personality to content-addressed memory-okf-personality/full tier (mem_class persona, mem_owner self, mem_delivery system). Deterministic, no model call. Wired into harness/control/agency.py consolidate_current gated SP_PERSONALITY (best-effort, never breaks memory consolidation). G-PF-CURATE PASS: transcript shifts extracted (mood/voice/+trait/-trait), duplicate trait pruned, OKF snapshot written. DON'T REBUILD: personality curator already exists at harness/personality/curator.py. Repro: python tests/h_personality_curate.py.
