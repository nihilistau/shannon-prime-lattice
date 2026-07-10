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
tags: [L5, layer-localized, recall, paraphrase, faithfulness, LN-1, correction, global-Q, cosine, jaccard, method-change, deployable, kste_md-directional, agent, tier-2]
mem_tier: full
---

# ★ L5 RECALL FINDING — the fact signal is layer-localized (cracks the LN-1 paraphrase wall)

**Corrects the LN-1 "last-token global-Q is content-poor" conclusion.** The content is NOT absent — it is concentrated in **global layer 5**, and averaging all 8 global layers destroyed it. Receipt: `system tests/fixtures/G-REP-LAYER-L5-2026-07-01.log` (harnesses `tests/rep_sweep.py`, `rep_layer.py`, `rep_hybrid.py`, `kste_md_confirm.c`), real gemma-4-12B faithfulness captures, n=61.

- **Per-layer exact→paraphrase recall@1** (last-token global-Q, mean over heads): L0 1.6 / L1 1.6 / L2 4.9 / L3 6.6 / L4 19.7 / **L5 85.2** / L6 78.7 / L7 8.2. All-layer average = 11.5%. Greedy subset picks **L5 alone**.
- **Deployable win — L5 query-key recall (cosine, query-to-query) on the 61 fact-conflicts:** EXACT 100% / **PARAPHRASE 88.5%**, vs the deployed Jaccard selector's 100% / **8.2%**. This is the paraphrase wall that ended the faithfulness arc.
- **Combine L5 + Jaccard by GATE/max, NOT sum** (naive z-sum hybrid = 49%, worse than L5 alone, because it dilutes the strong L5 signal with near-random Jaccard paraphrase scores).

## Sub-findings
- **KSTE-MD is the WRONG tool for this signal.** On the L5 rep: cosine 85% vs KSTE-MD 3.3% (ratio 1.43×). The L5 fact signal is DIRECTIONAL/angular (cosine sees it); kste_md reads magnitude-profile shape (orthogonal geometry) → blind to it. kste_md was the catalyst that prompted the sweep, not the fix. kste_md stays a magnitude-shape dedup primitive (INPUT-GATED, see c90d457).
- **Q-vs-K cosine is floor at every layer** (query and key are different subspaces). The 85%/88.5% is QUERY-space (query-to-query). Matching an incoming query against a stored EPISODE-K needs the learned W_c projection (try W_c fed L5-only) OR store an L5 query-space key per episode.

## The method change to make (do NOT keep averaging layers)
Use the **global-layer-5, mean-over-heads, 512-d** last-token query embedding as the recall/selection key, matched by cosine (query-to-query), gated with Jaccard for exact. The data is ALREADY captured — `read_global_q` emits all 8 global layers; the selector just needs to index L5 instead of averaging. Live wiring: routes.rs/recall.rs select L5; store per-episode L5 query-key; cosine match. Verify live layer-index ordering == offline index 5 first.

## Honest scope
n=61 (small) — 88.5% needs a scale confirm. L5 is within the captured 8 global layers (period-6 set {5,11,...,47}); confirm the live ordering. This is a QUERY-space result; deploying against stored K-episodes needs the W_c-fed-L5 or L5-query-key change above.
