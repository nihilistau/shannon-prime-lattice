---
type: memory
title: #47 FIXED: no-repeat-ngram guard seeded with prompt tokens o
description: #47 FIXED: no-repeat-ngram guard seeded with prompt tokens on greedy path (SP_NO_REPEAT_NGRAM=3, chat launcher only). Echo killed, name/brevity preserved. Gotcha: env parse needs .trim(). engine 47b82ed.
timestamp: 2026-07-04T03:02:38Z
resource: TBD
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
mem_kind: agent
mem_addr: echo-47-fix
tags: [#47 fix, G-ECHO-FIX, no-repeat-ngram, anti-echo, SP_NO_REPEAT_NGRAM, system-prompt recital, contentless prompt, sampler ngram, env trim parse gotcha, agent, tier-2]
mem_tier: full
---

ï»¿G-ECHO-FIX (#47, engine 47b82ed): the contentless-prompt SYSTEM-PROMPT recital ('Sure.' -> 'You are Shannon-Prime, a local AI. Keep replies short.') is FIXED on the plain chat path. Root cause: at temp=0 the sampler is strict argmax with NO anti-echo (repetition_penalty tracks only GENERATED tokens, not the prompt). FIX: no-repeat-ngram guard seeded with the PROMPT tokens, applied on the greedy path (sampler.rs ban_repeat_ngram + no_repeat_ngram param + set_ngram_prefix; routes.rs reads SP_NO_REPEAT_NGRAM, seeds prefix=prompt tokens). n=3. Enabled ONLY in run_console_chat.bat (recall OFF); OFF in run_console_faithful.bat so faithful recitation + G-ONECONFIG obey untouched. Default unset=0=byte-identical null floor. LIVE result: 'Sure.'->'You're welcome.', name preserved ('I am Shannon-prime'), 2+2->4 concise. Residual: 'Continue.' paraphrases the persona (not verbatim) - acceptable. GOTCHA banked: env parse must v.trim().parse() - a launcher 'set VAR=3 ' trailing space made value '3 ' -> parse fail -> silently 0 -> guard never fired (cost 2 rebuilds to find). Also convicted: blanket -8 penalty on ALL prompt tokens kills echo BUT blocks the model's own name + causes rambling -> use the surgical ngram ban not a blanket penalty.
