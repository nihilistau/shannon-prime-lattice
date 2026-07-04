---
type: memory
title: #47 diagnosed: short-prompt echo = system-prompt recital on 
description: #47 diagnosed: short-prompt echo = system-prompt recital on contentless prompts, in exact AND FP equally. byteexact exonerated; premise refuted; no quality-fix argument for FP profile.
timestamp: 2026-07-04T02:20:38Z
resource: TBD
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
mem_kind: agent
mem_addr: echo-47-diagnosed
tags: [#47, byteexact echo, system-prompt echo, G-ECHO-HUNT-47, contentless prompt, echo not byteexact, short prompt echo, agent, tier-2]
mem_tier: full
---

ï»¿G-ECHO-HUNT-47 (2026-07-04, engine): #47 'byteexact-default-on echoes short prompts' DIAGNOSED. Ran plain chat config (run_console_chat.bat, recall OFF) x 30 short/adversarial prompts x byteexact true/false. FINDING: the echo is REAL but is SYSTEM-PROMPT recital on contentless prompts (Sure./Continue. -> 'You are Shannon-Prime...'; What? -> FP echoes), and it occurs in exact AND FP about EQUALLY (exact ~3, FP ~3). byteexact is EXONERATED as the cause; #47's 'float is the correct answer' premise is REFUTED. FP does NOT fix it. The real fix is a prompting/decoding change for contentless turns, orthogonal to exact-vs-FP. CONSEQUENCE: no 'quality fix' argument for the --no-exact FP profile -> it stands on portability+speed alone (G-NOEXACT-OBEY-AB). DON'T re-hunt: #47 cause known. Driver engine _faithful_corpus/echo_hunt_47.py.
