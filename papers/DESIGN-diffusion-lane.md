---
type: design
title: "DESIGN — the diffusion lane (DiffusionGemma applications, banked 2026-06-11)"
description: "Status: [DESIGN] — nothing here is open work."
tags: [design, diffusion]
timestamp: 2026-06-11T04:27:27Z
resource: shannon-prime-lattice/papers/DESIGN-diffusion-lane.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# DESIGN — the diffusion lane (DiffusionGemma applications, banked 2026-06-11)

**Status:** [DESIGN] — nothing here is open work. Strict sequencing: no diffusion item starts
before the current P2.b/P3 arc closes; the T8 drafter is formally QUEUED as the first diffusion
application when the KAIROS loop (or the C4/MTP lane) next opens. Authors: Knack + Claude +
Gemini (Gemini's first-pass Curator pitch corrected on the record, §3).

**Ground truth (blog.google, 2026-06-10; verified, not summarized from chat):** DiffusionGemma =
26B-total / 3.8B-active MoE, Apache 2.0, experimental, built on Gemma 4 + Gemini Diffusion.
**Discrete MASKED diffusion** — "canvas of random placeholder tokens → iterative refinement,
locking in correct tokens" — NOT continuous-noise denoising. 256-token blocks, bidirectional
attention in-block, up to 4× tok/s on dedicated GPUs (1000+ H100, 700+ RTX 5090), **18 GB VRAM
quantized**, output quality explicitly BELOW AR Gemma 4, speedup strongest at low concurrency,
and (their own footnote) requires high arithmetic intensity — bandwidth-bound silicon sees less.
Prior art in-house: the quickborn server already prototyped phase-based diffusion-draft
speculative decoding; this is the first strong pretrained backbone for that lane.

## The four placements (priority order)

1. **T8 DRAFTER (the headline; zero quality risk).** The C4/MTP machinery's standing negative is
   "needs a real draft source" (prompt-lookup 0.87× on real prose; draft→verify→byte-exact-accept
   + O(1) watermark rollback all PROVEN, engine 145bf43). A small/quantized diffusion model
   drafts an N-token block compute-bound; the AR Exec verifies the block in ONE parallel forward
   — weights read once for N tokens, converting the memory-bound decode into the compute-dense
   batch. **Verification is exact, so drafter quality only affects hit-rate, never output** —
   the inverse risk profile of every other diffusion use. Slots into CONTRACT-C4, no new lane.
2. **G-R3-LOSS INSTRUMENT (consolidation-time ONLY).** Conditional reconstruction of the
   verbatim Ring-2 span from the k=2 gist, run during NIGHTSHIFT *while the verbatim still
   exists*; the measured reconstruction delta becomes the bounded-loss coefficient ε attached to
   the gist as its certificate. **HARD RULE: recall-time gist upsampling presented as memory is
   FORBIDDEN** — that is §4's "confidently fabricated history" built on purpose (Gemini's
   first-pass pitch, corrected). Any served reconstruction carries the provenance tag (RFC §3.1
   backlog lane) + its ε. The Exec needing verbatim pulls Ring 2, period.
3. **C1L.3 MERGE/INFILL EDITOR.** Bidirectional in-block attention is an infilling engine (the
   release's own pitch: in-line editing, code infilling) — the natural mechanism for
   merge-adjacent-similar consolidation rewrites, under the same propose→gate→promote/rewind
   loop as every curator action.
4. **KAIROS IDLE SPECULATION.** During idle ticks the drafter speculates likely futures
   (branch prediction, ROADMAP-KAIROS §2); on wake, T8-verify; on miss, O(1) rewind. Converts
   idle FLOPs into latency credit with the same zero-quality-risk guarantee as #1.

**NON-placement:** the Exec does NOT become a diffusion model. Not for Gemini's interrupt reason
(masked diffusion CAN early-exit — every step yields a full block estimate) but because the
entire proven substrate — rings, ±1 recall, the KV crossbar, X-R1, O(Δ) event appending — is AR
KV-cache physics; a bidirectional block model has no cache in our sense, so XBAR does not
transfer. AR keeps the kernel interruptible at token granularity for free.

## Hardware honesty (Beast Canyon)

26B MoE @ ~18 GB quantized does not fit the 2060-12GB as-is; sm_75's weak tensor ALU compresses
the 4× well below the 5090/H100 figures (same caveat the blog's footnote makes for Apple
Silicon). Two consolations: (a) prototyping runs on the Colab A100 lane natively; (b) the
26B/3.8B-active geometry is the IDEAL **Stage-Gamma expert-streaming benchmark** — the
qwen35moe machinery (reducing .sp-model transcode, arena rank-3 expert paths, f32 router,
Optane cold tier) was built for exactly this shape. Operator-reported context point: the qwen
35B-A3B already runs hybrid on this host with experts split GPU/CPU at ~40 tok/s
(operator-reported, not a ledger row) — DiffusionGemma-through-the-SP-envelope on a 12 GB card
would be a citable-class demo if the lane ever warrants it. llama.cpp support "arriving soon" =
a future oracle for parity gates, per the established shootout discipline.

## Consonance note

The §3.2 audio lane's non-AR FiLM vocoder is this same parallel-refinement principle in audio —
the release independently validates that direction. The masked-discrete formulation (categorical
tokens, no continuous latents) is the diffusion family most compatible with the Z_q substrate
doctrine if any component is ever rebuilt lattice-native.
