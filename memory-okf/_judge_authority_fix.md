# Judge-path authority loss: ROOT-CAUSED + FIXED (delivered texts[slot] cruft, not clean ep.text)

The judge PICK delivery lost context-authority — right pick, but the model answered parametric (tallest→Everest, planet→Jupiter, romeo→Shakespeare) instead of the planted fact. Root-caused via the operator's terse `dpos+1` hint (which sent me to scrutinize the delivery token-path).

## What it was NOT (ruled out by reading + a probe)
- NOT cache pollution: `reset_cold` confirmed OK, `dpos=0` after reset (probe log). Gemini's watermark/truncate was dead code — nothing to truncate.
- NOT a position offset: `replay_dir` is request-supplied (None here), synthesis `dpos` identical to L5-direct (both = aug_head.len()).
- NOT the format: after the earlier delivery fix, the aug format matches L5-direct exactly.

## The bug (found by reading the candidate assembly)
The judge delivered `mem_text = texts[slot]`, and `texts[slot]` is built by **detokenizing the episode's raw `ep.tok` turn** (captured "with forced BOS + trailing \n" = chat-template cruft, routes.rs ~L1632-1650). L5-direct delivers the **clean `ep.text` manifest field**. The cruft-laden text inside "Context (authoritative, current): {…}" gave the model a messy context → it fell back to parametric.

## The fix (engine 4ff75d1)
`let mem_text = if !ep.text.trim().is_empty() { ep.text.clone() } else { texts[slot].clone() };` — deliver the clean manifest text (identical to L5-direct), fall back to the detokenized turn only for live episodes with no manifest.

## Validated live (judge_test, authority-fixed)
planet→**Saturn**, romeo→**Marlowe**, tallest→**K2**, closest→**Venus**, fastest→**lion** — all now OBEY the planted facts (all were parametric pre-fix). Authority restored.

## Remaining (NOT the authority bug)
Judge-shortlist recall on the n=8 subset (~50-62%) is still below L5-direct's 86.89% — that's the recall lost to the L5-shortlist + judge-pick step (France/ocean/japan missed), plus the model resisting a few absurd planted facts (ocean→Pacific, japan→yen = truth over the planted counter-fact). The ADR-002 §8.1 reorder (L5-direct OWNS delivery; judge only VETOES/NULLs) recovers the full 86.89% recall AND keeps the reject. That reorder is the next build.

## Meta
The `dpos+1` hint was right in spirit (a subtle per-turn delivery detail) — the actual culprit was the token SOURCE (raw-turn vs manifest), not a position offset. Reading the metal beat both my cache hypothesis and the watermark narrative.
