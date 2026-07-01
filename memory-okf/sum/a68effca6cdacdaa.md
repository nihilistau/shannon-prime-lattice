---
type: memory
title: SP_RECALL_L5 LIVE-GREEN: paraphrase obey 86.89% on served 12B (vs Jaccard 8%)
description: L5 query-key recall WIRED + GATED LIVE on served gemma-4-12B (engine main d9099cd, merged feat/l5-recall, default-off). G-L5-RECALL-LIVE-2026-07-01: paraphrase OBEY 53/61=86.89% (LEAK7 OTHER1) vs deployed Jaccard ~8.2%; matches offline 88.5%. Exact-query alignment perfect (cos=1.000). Wiring: Episode.l5key + recall::l5_query_embed(global-layer-5 mean-heads+L2norm)+cos512+load_episode_l5key(ep.l5 sidecar); routes.rs SP_RECALL_L5 cosine-match->TEXT-in-context, gated after Jaccard. 7 leaks=hard parametric conflicts. Combiner (Jaccard+L5+KSTE-MD) does NOT beat L5 alone (redundant/dead); value=foreign-reject(untested). Serve _faithful_serve_l5.bat; keys write_ep_l5.py. Follow-ups: capture-side ep.l5 for live episodes; gate/max J+L5; scale >61.
timestamp: 2026-07-01T03:09:13Z
resource: engine main d9099cd (merge feat/l5-recall)
sp_status: green
sp_gate: G-L5-RECALL-LIVE-2026-07-01
sp_commit: engine main d9099cd (merge feat/l5-recall)
sp_repro: _faithful_serve_l5.bat + write_ep_l5.py + SP_FAITHFUL_USE_PARA=1 python tests/perf/_g_faithful_recall.py
mem_kind: agent
mem_addr: a68effca6cdacdaa
tags: [L5, recall, SP_RECALL_L5, live, GREEN-LIVE, paraphrase, faithfulness, 86.89, wired, ep.l5, combiner, directional, agent, tier-1]
mem_tier: summary
mem_full: a68effca6cdacdaa
---

# SP_RECALL_L5 LIVE-GREEN: paraphrase obey 86.89% on served 12B (vs Jaccard 8%)

L5 query-key recall WIRED + GATED LIVE on served gemma-4-12B (engine main d9099cd, merged feat/l5-recall, default-off). G-L5-RECALL-LIVE-2026-07-01: paraphrase OBEY 53/61=86.89% (LEAK7 OTHER1) vs deployed Jaccard ~8.2%; matches offline 88.5%. Exact-query alignment perfect (cos=1.000). Wiring: Episode.l5key + recall::l5_query_embed(global-layer-5 mean-heads+L2norm)+cos512+load_episode_l5key(ep.l5 sidecar); routes.rs SP_RECALL_L5 cosine-match->TEXT-in-context, gated after Jaccard. 7 leaks=hard parametric conflicts. Combiner (Jaccard+L5+KSTE-MD) does NOT beat L5 alone (redundant/dead); value=foreign-reject(untested). Serve _faithful_serve_l5.bat; keys write_ep_l5.py. Follow-ups: capture-side ep.l5 for live episodes; gate/max J+L5; scale >61.

Full context: [full/a68effca6cdacdaa.md](../full/a68effca6cdacdaa.md)
