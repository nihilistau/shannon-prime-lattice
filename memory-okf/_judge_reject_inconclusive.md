# Sequential pass→block reject (L5 + judge) = INCONCLUSIVE (ad-hoc binary judge harness inadequate)

The operator's idea — sequential (not fused, per TELE-12): L5 PASSES the top-1 fact, a judge BLOCKS if it doesn't answer — is sound and is the right direction for foreign-reject. But my ad-hoc single-call binary judge harness did NOT resolve it. Receipt: `shannon-prime-system-engine/tests/fixtures/G-JUDGE-REJECT-2026-07-01.log`.

## Why inconclusive (harness inadequacy, NOT a concept result)
- "answer"-framing judge → 43/43 in-mem "NO" (0% accept): the corpus facts are PLANTED-FALSE, so the model judged TRUTH not RELEVANCE → NO to every false fact.
- "relevance"-framing judge (truth-decoupled topic match) → 23/23 in-mem "NO", 0 YES anywhere.
- eot_bias 0..4, FRESH daemon (clean KV) AND polluted cache: on 6 trivially-obvious cases the served model emits "NO" + GARBAGE tokens ("دبستان", "```") for every case. Off-distribution degeneration, not judgment.
- DIAGNOSIS: a naive binary YES/NO classification prompt drives the quantized gemma-4-12b (tuned for the faithfulness chat, not classification) off-distribution. This says nothing about the pass→block concept.

## The right tool already exists
SP_B3_JUDGE (routes.rs) — a SELECTION judge over tagged candidates with anti-position-bias shuffling, validated 85.7% recall@1 on _needle_corpus_div. To resolve pass→block properly: run the reject through SP_B3_JUDGE on (query, top-few-facts incl. the L5 top-1), NOT an ad-hoc binary prompt. Deliberate build.

## Settled in this thread (durable)
1. L5-cosine recall = SHIPPED win (86.89% para live, G-L5-RECALL-LIVE, default-off on main).
2. Query-SIDE reject gates (L5 / Jaccard / margin, single or combined) genuinely FAIL on the clean foreign set (~90% foreign false-accept @85% para-accept) — foreign factual Qs are structurally identical to in-mem ones (L5 encodes question TYPE; Jaccard confounded by scaffolding). This held on the CLEAN v2 foreign set (the earlier v1 set was 30/40 contaminated — my error, corrected).
3. Judge-BASED reject = right direction, UNRESOLVED by ad-hoc harness; needs SP_B3_JUDGE.
4. The served model IGNORES irrelevant recalled context (answers foreign Qs from parametric even with a spurious fact force-injected) → bounds the real-world damage of an imperfect reject.

## Honesty note
The v1 foreign set was contaminated (I didn't check it against the 61 corpus topics before running), which biased the first reject result pessimistic. Re-ran clean (v2) — the query-side negative held. The judge test is inconclusive due to my harness, NOT a forced negative. Do not cite "judge reject fails"; cite "unresolved, needs SP_B3_JUDGE."
