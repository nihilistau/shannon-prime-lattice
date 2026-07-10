---
type: memory
title: L5 recall finding: fact signal is layer-localized (global L5) — cracks LN-1 paraphrase wall (100%/88.5%)
description: CORRECTS LN-1 'last-token global-Q content-poor'. Signal is LAYER-LOCALIZED in global layer 5; averaging 8 layers destroyed it. Per-layer exact->para recall@1: L5 85.2 / L6 78.7 / all-avg 11.5. DEPLOYABLE: L5 (mean-heads,512d) query-key cosine recall = 100% exact / 88.5% paraphrase on 61 fact-conflicts vs deployed Jaccard 100%/8.2% (the paraphrase wall that ended the faithfulness arc). Combine L5+Jaccard by GATE/max NOT sum (z-sum=49%, dilutes). SUB: kste_md is WRONG tool (directional signal; kste_md magnitude-shape-blind 3.3% vs cosine 85%); Q-vs-K cosine floor (diff subspaces -> W_c-fed-L5 or store L5 query-key). Data ALREADY captured (read_global_q emits 8 global layers; index L5). Receipt G-REP-LAYER-L5-2026-07-01. Honest: n=61 small, needs scale confirm + verify live layer ordering==offline L5.
timestamp: 2026-07-01T02:24:08Z
resource: system tests/rep_*.py + fixtures/G-REP-LAYER-L5-2026-07-01.log (see git log)
sp_status: GREEN
sp_gate: G-REP-LAYER-L5-2026-07-01
sp_commit: system tests/rep_*.py + fixtures/G-REP-LAYER-L5-2026-07-01.log (see git log)
sp_repro: python tests/rep_layer.py <eng>/_faithful_corpus/qdump <eng>/_faithful_corpus/qdump_para ; python tests/rep_hybrid.py ... facts.json
mem_kind: agent
mem_addr: aee79cba34bc759a
tags: [L5, layer-localized, recall, paraphrase, faithfulness, LN-1, correction, global-Q, cosine, jaccard, method-change, deployable, kste_md-directional, agent, tier-1]
mem_tier: summary
mem_full: aee79cba34bc759a
---

# L5 recall finding: fact signal is layer-localized (global L5) — cracks LN-1 paraphrase wall (100%/88.5%)

CORRECTS LN-1 'last-token global-Q content-poor'. Signal is LAYER-LOCALIZED in global layer 5; averaging 8 layers destroyed it. Per-layer exact->para recall@1: L5 85.2 / L6 78.7 / all-avg 11.5. DEPLOYABLE: L5 (mean-heads,512d) query-key cosine recall = 100% exact / 88.5% paraphrase on 61 fact-conflicts vs deployed Jaccard 100%/8.2% (the paraphrase wall that ended the faithfulness arc). Combine L5+Jaccard by GATE/max NOT sum (z-sum=49%, dilutes). SUB: kste_md is WRONG tool (directional signal; kste_md magnitude-shape-blind 3.3% vs cosine 85%); Q-vs-K cosine floor (diff subspaces -> W_c-fed-L5 or store L5 query-key). Data ALREADY captured (read_global_q emits 8 global layers; index L5). Receipt G-REP-LAYER-L5-2026-07-01. Honest: n=61 small, needs scale confirm + verify live layer ordering==offline L5.

Full context: [full/aee79cba34bc759a.md](../full/aee79cba34bc759a.md)
