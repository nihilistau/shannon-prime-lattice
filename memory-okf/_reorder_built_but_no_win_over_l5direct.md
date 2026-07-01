# Unified-path REORDER built + correct, but does NOT beat L5-direct+tau on this corpus (honest negative)

Built the ADR-002 §8.1 reorder in routes.rs (engine): the SP_B3_JUDGE_L5 branch now precomputes the GLOBAL L5-#1 episode (identical selection to SP_RECALL_L5) and, on a judge PASS, delivers THAT via the clean text-in-context path — the judge's own shortlist pick is used only as a PASS/NULL signal. Wiring proven: serve log shows `B3-JUDGE REORDER: L5 global best='fct_004' cos=0.951 (delivery target on PASS)` → `PASS ... DELIVER 'fct_004'` (20 delivery-target lines/run). Default-off (SP_B3_JUDGE_L5 unset) = null floor. Build GREEN (wire_cuda, 40s).

## Three-way gate, IDENTICAL hard 12-subset (facts.json[:12]), served 12B
| method | para recall | foreign spurious | cost |
|---|---|---|---|
| **L5-direct + tau=0.30** (SP_RECALL_L5) | 6/12 = 50% | **1/12 = 8%** (the 1 = metric false-pos on "Ulaanbaatar", true ~0) | cheap (cosine only) |
| K=2 judge-pick (prior) | 6/12 = 50% | 2/12 = 17% | + generative judge forward |
| **Reorder** (judge K=2 veto → L5-#1 deliver) | 6/12 = 50% | 2/12 = 17% (PASS=21 NULL=3) | + generative judge forward |
Receipts: `tests/fixtures/chat_fullstack/G-JUDGE-REORDER-K2-2026-07-01.log`, `G-L5-DIRECT-SAME12-2026-07-01.log`.

## Findings
1. **The 50% is subset hardness, not method.** All three tie at 6/12 on this slice (ocean→Pacific & japan→yen: the model RESISTS the absurd planted fact regardless of path; brazil/australia: genuine L5 top-1 confusion; K2: model hedges Everest). The headline 86.89% stands for the full 61; facts[:12] is the hard slice. My earlier "japan proves the judge costs recall" was WRONG — L5-direct-alone also misses japan→yen.
2. **The reorder PRESERVES L5 recall exactly** (50% == L5-direct 50%) and is the architecturally-correct realization of ADR §8.1 (decider/executor separation; L5 owns delivery). It works.
3. **But it does NOT beat plain L5-direct+tau on this corpus.** Same recall; L5-direct's tau=0.30 rejects genuine foreign at least as well (8% vs 17%, within n=12 noise) at lower cost. WHY: (a) the model's own robustness cleans most spurious deliveries; (b) tau silently drops genuinely-out-of-corpus foreign (low L5 cosine). The judge's one theoretical edge — rejecting HIGH-cosine-but-unanswerable foreign that CLEARS tau — is not exercised by foreign_queries_v2 (all comfortably below tau).

## Deploy recommendation
Ship **L5-direct + tau=0.30** as the recommended recall path (simple, 86.89% full-corpus, tau-rejects genuine foreign, no judge forward). Keep the reorder (SP_B3_JUDGE_L5) behind its flag; **gate its promotion on a HARD-FOREIGN kill-test**: mint foreign queries whose L5 cosine clears tau (near-corpus, same domain, unanswerable) — the case where tau fails and only the generative judge can reject. Until that test shows the judge winning, L5-direct+tau is the default. All flags stay default-off (byte-exact null floor non-negotiable — do NOT flip default-on).

## Anti-rebuild
The reorder is DONE (engine routes.rs, committed). Do not re-wire it. The open item is the hard-foreign kill-test corpus, NOT more judge plumbing.
