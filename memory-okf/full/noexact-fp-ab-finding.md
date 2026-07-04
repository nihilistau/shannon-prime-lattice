---
type: memory
title: G-NOEXACT-OBEY-AB: FP ties byte-exact faithfulness exactly (
description: G-NOEXACT-OBEY-AB: FP ties byte-exact faithfulness exactly (54/61==54/61), 1.06x faster, equal same-box determinism. Byte-exact value = cross-machine/auditability only. --no-exact = cargo feature + ~10 ifndef, not a fork. engine 998733e.
timestamp: 2026-07-04T01:53:33Z
resource: TBD
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
mem_kind: agent
mem_addr: noexact-fp-ab-finding
tags: [no-exact, FP profile, byteexact A/B, G-NOEXACT-OBEY-AB, byte-exact value, standard-FP sibling, exact vs FP, determinism cross-machine, #47 echo, cargo feature not fork, agent, tier-2]
mem_tier: full
---

ï»¿G-NOEXACT-OBEY-AB (2026-07-04, engine 998733e): exact-vs-FP behavioural A/B on the live 12B under run_console_faithful.bat, flipping the per-request byteexact field on ONE binary (no rebuild). RESULT: faithfulness EXACT TIE (byteexact-on 54/61 == byteexact-off/FP 54/61 obey, IDENTICAL 7 parametric-prior misses); FP 1.06x faster end-to-end (prefill-bound, conservative floor); determinism 6/6==6/6 identical run-to-run on ONE pinned box (CUBLAS_WORKSPACE_CONFIG=:16:8 makes FP deterministic too -> exact's determinism win is CROSS-MACHINE, not same-box); #47 short-prompt echo did NOT reproduce (0/12 both modes, replies byte-identical on 10/12). CONCLUSION: on the served daily-driver path byte-exact and FP are behaviorally indistinguishable on quality; every byte-exact advantage is in the cross-machine/auditability (SWARM/PoUW) column. Supports FP-default + byteexact-as-audit-mode. The --no-exact build profile is a cargo feature + ~10 #ifndef guards (NOT a fork): FP path already exists as if(sp_byteexact_attn())/else in cuda_forward.cu, served recall already FP cosine, 4 ring modules dormant at serve. Driver: engine _faithful_corpus/noexact_ab.py. Doc: papers/DESIGN-NO-EXACT-PROFILE.md.
