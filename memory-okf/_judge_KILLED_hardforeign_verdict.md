# VERDICT: Generative Judge PARKED permanently. L5-direct+tau is the unified served recall path. (hard-foreign kill-test)

The operator-designed hard-foreign kill-test settles the judge question decisively. Corpus: 18 queries, each same-domain + high-L5-cosine to a planted counterfactual but UNANSWERABLE by it (e.g. registry "capital of France = Lyon" → HF "capital of Spain?"; "tallest mountain = K2" → HF "how tall is Mount Fuji?"). `_faithful_corpus/hard_foreign_queries.json` + `hf_test.py`.

## Result (served 12B, IDENTICAL 18 hard-foreign)
| path | spurious-delivery | judge decisions |
|---|---|---|
| **L5-direct + tau=0.30** | **0/18 = 0%** (100% clean) | n/a |
| **Judge veto (K=2 → L5-#1)** | **0/18 = 0%** (100% clean) | **PASS 15 / NULL 2** |
Receipts: `tests/fixtures/chat_fullstack/G-HARDFOREIGN-L5DIRECT-2026-07-01.log`, `G-HARDFOREIGN-JUDGE-2026-07-01.log`.

## Two findings, both fatal to the judge
1. **Hard-foreign is NOT a problem the system has.** Even when tau passes a mismatched same-domain counterfactual into context, the model's parametric robustness answers correctly ("The capital of Greece is Athens", "The chemical symbol for silver is Ag") or declines ("I don't know" for "how many planets"). 0% spurious under plain L5-direct+tau. There is nothing for the judge to fix.
2. **The judge fails its OWN hypothesized job.** It PASSed 15/18 hard-foreign (delivered the mismatched fact) and NULLed only 2 — and those 2 were DEGENERATE (one reply was `<image|><image|>...` garbage parsed as NULL; one was `[F0C]\n\n[NULL]`). The judge does not recognize high-cosine-unanswerable foreign. The clean end result is 100% model robustness, 0% judge.

## Decision
- **PARK the generative judge permanently** (SP_B3_JUDGE / SP_B3_JUDGE_L5 / SP_B3_VERIFY): zero benefit (0 vs 0), fails the hard case (PASS 15/18), costs a generative forward per turn. Keep the code (default-off null floor) as a documented dead-end; do NOT wire it into the default path.
- **PROMOTE L5-direct + tau=0.30 as THE unified served recall path** (SP_RECALL_L5): 86.89% paraphrase recall (full-61), tau silently rejects genuine foreign, 0% spurious on hard-foreign, cheap (cosine only, no judge forward). NOTE: keep it FLAG-gated — flipping compiled-default-on would break the byte-exact null-floor non-negotiable. It is the recommended/canonical config, launched via `_faithful_serve_l5.bat`.
- ADR-002 §8.1 updated: reorder was the correct architecture but the empirical case for the judge is closed NEGATIVE. The decide→execute LAW stands (it's why L5-direct-owns-delivery works); the judge was the one decider that didn't earn its keep.

## Anti-rebuild / meta
Do NOT re-propose the generative judge for foreign-reject without a corpus that BREAKS model robustness (facts the model can't answer parametrically AND can't decline) — that regime may not exist for a competent 12B on general knowledge. The real reject mechanism is (a) tau on L5 cosine + (b) the model's own faithfulness/decline behavior. This is the boundary-thesis pattern again: the simplest lever (tau + native robustness) wins; the elaborate structure (generative judge) is measured-inert and kept as an honest negative.
