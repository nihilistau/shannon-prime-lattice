---
type: memory
title: TELE-11 honest negative: answer-fidelity fails (strict 0.000); bridge transmits, can't confer answering on 0.5B
description: TELE-11 HONEST NEGATIVE: answer-labeled fidelity (lever c) does NOT achieve task-answering at this scale. STRICT exact-match (first token==gold) = 0.000 on 53 held-out short verifiable Q->A; the lenient 0.321 was an ARTIFACT (degenerate repetition like '11111111' gaming out.startswith(gold); 30.2pct of outputs are degenerate garbage). CE dropped (adapter learned to emit something) but ZERO answers correct. ROOT CAUSE (not the adapter/objective): the bridge faithfully transmits the QUESTION (TELE-10b reconstruction real) but cannot make a 0.5B delegate MORE CAPABLE - a tiny coder can't compute '17x2' even from text, and a pure soft-latent prefix is a harder channel than text. BOUNDARY: Telepathy MOVES structured thought across families (proven); it does NOT confer ANSWERING on a weak delegate - task-correctness is bottlenecked by the DELEGATE's intrinsic capability, not the transport. CONSEQUENCE: for real task-delegation use a CAPABLE delegate (+ possibly text-grounded conditioning), not more adapter tuning. Always check SAMPLES not just the metric (the startswith gate was gamed; strict_eval.py exposed it).
timestamp: 2026-06-30T01:57:32Z
resource: engine feat/mtp
sp_status: RED
sp_gate: STRICT exact-match 0.000 (honest negative)
sp_commit: engine feat/mtp
sp_repro: python tools/telepathy/strict_eval.py
mem_kind: episode
mem_addr: ae44d0be6aebc659
tags: [telepathy, answer-labeled, honest-negative, task-answering-fails, delegate-capability-bottleneck, metric-gaming, strict-eval, TELE-11, boundary, episode, tier-2]
mem_tier: full
---

BLOB POINTER (Tier-2 = external payload)

blob: tele11:ae44d0be6aebc659
kind: episode
Full context is the latent/binary payload at the blob path (Ring-2 / Optane). Address = C2 LSH signature / provided id.
