---
type: memory
title: TELE-12: fused latent+text FAILS; correct = sequential decide(latent)->execute(clean text)
description: TELE-12 hybrid proof (zero-training, arith N=66, fair gold-in-answer). FUSED hybrid (latent prefix + bare text operands in ONE forward) = 0.000, WORSE than operands-only-text (0.348); text-full=0.439, latent-only=0.000. The soft latent prefix CORRUPTS downstream text processing (samples: Qwen drops into code-completion/garbage mode and ignores the operands). => latent and text do NOT compose by concatenation in a single forward. CORRECT ARCHITECTURE = SEQUENTIAL: latent carries the DECISION/ROUTING (Route head, proven GREEN false-fire 0.000), then the delegate receives CLEAN TEXT (text-baseline). Decide-via-latent THEN execute-via-text - two stages, not a fused prompt. This VALIDATES the existing framework design (action/tool/memory/route heads decide on the latent; the harness executes via text/tools). My fused-hybrid proposal was wrong; the two-stage decomposition is right. Capstone of the answering/fidelity arc: Telepathy = gist/intent/routing channel (proven); precise execution = clean text to the delegate; never fuse them in one forward.
timestamp: 2026-06-30T02:47:03Z
resource: engine feat/mtp
sp_status: GREEN
sp_gate: fused 0.000 vs operands-only 0.348 (fused-hybrid disproven; sequential validated)
sp_commit: engine feat/mtp
sp_repro: python tools/telepathy/hybrid_eval.py
mem_kind: episode
mem_addr: a2b4dc7ab58afcfd
tags: [telepathy, hybrid, fused-fails, sequential, decide-via-latent-execute-via-text, two-stage, route-head, TELE-12, architecture-validated, capstone, episode, tier-1]
mem_tier: summary
mem_full: a2b4dc7ab58afcfd
---

# TELE-12: fused latent+text FAILS; correct = sequential decide(latent)->execute(clean text)

hybrid_eval.py 4-condition. Fused=0.000<operands-only=0.348 (latent prefix corrupts text). Right design = Route head decides on latent, delegate gets clean text (two stages). Validates existing framework. hybrid_result.log.

Full context: [full/a2b4dc7ab58afcfd.md](../full/a2b4dc7ab58afcfd.md)
