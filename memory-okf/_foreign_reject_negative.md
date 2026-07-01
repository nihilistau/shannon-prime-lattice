# Foreign-reject via cheap signals = HONEST NEGATIVE (needs pairwise query×fact judge)

The hypothesis "the multi-signal combiner's value is foreign-rejection" is DISCONFIRMED. Receipt: `shannon-prime-system-engine/tests/fixtures/G-FOREIGN-REJECT-2026-07-01.log` (live 12B, 61 in-memory paraphrase queries vs 40 minted foreign queries, captured global-Q → L5).

**Distributions (in-memory PARA should accept; FOREIGN should reject):**
- top1 L5-cos: para 0.955 vs **foreign 0.965** (foreign HIGHER — no separation).
- margin(top1-top2): 0.022 vs 0.021 (identical).
- max Jaccard: para 0.151 vs **foreign 0.325** (foreign MORE lexically similar — shared "what is the largest..." scaffolding).

**Reject gates @ 85% para-accept:** L5-cos-alone → 80% foreign FALSE-accept; margin → 85%; Jaccard → 100% (useless); **multi-signal (L5 AND margin) → 80% (== L5 alone, NO improvement).**

**Root cause:** the reject decision is intrinsically QUERY×FACT (does the retrieved fact ANSWER this query?), NOT query-similarity. Foreign factual questions are structurally identical to in-memory factual questions, so L5 (encodes question TYPE) co-locates them and Jaccard is confounded by shared scaffolding. No query-SIDE threshold can tell whether the answer is in memory — the query looks the same either way. So the "combine two orthogonal cheap signals" thesis does NOT solve foreign-reject; the cheap signals are all confounded at the query level.

**Right tool:** a pairwise (query, candidate-fact) relevance/entailment check — the generative judge SP_B3_JUDGE (already in engine; reads candidate TEXTS, picks the answerer or [NULL]) or a learned cross-encoder head. NOT a cheap signal-agreement gate.

**Silver lining (observed):** with tau=0 forcing spurious recall on foreign queries, the served 12B still answered correctly FROM PARAMETRIC ("Mars has two moons", "Glass is primarily silica") — it largely IGNORES irrelevant recalled context. So a moderate SP_RECALL_L5_TAU + the model's robustness bounds the damage; the judge is the principled reject when a spurious fact would actually mislead.

**Net for the multi-head/combiner idea:** proven that L5-cosine alone is the deployable recall selector (86.89% para live); the combiner beats it on neither recall (L5 subsumes) nor foreign-reject (all cheap signals confounded). The combiner is retired for this task; foreign-reject is a judge/cross-encoder problem.
