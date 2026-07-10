---
type: memory
title: SP_RECALL_L5 LIVE-GREEN: paraphrase obey 86.89% on served 12B (vs Jaccard 8%)
description: L5 query-key recall WIRED + GATED LIVE on served gemma-4-12B (engine main d9099cd, merged feat/l5-recall, default-off). G-L5-RECALL-LIVE-2026-07-01: paraphrase OBEY 53/61=86.89% (LEAK7 OTHER1) vs deployed Jaccard ~8.2%; matches offline 88.5%. Exact-query alignment perfect (cos=1.000). Wiring: Episode.l5key + recall::l5_query_embed(global-layer-5 mean-heads+L2norm)+cos512+load_episode_l5key(ep.l5 sidecar); routes.rs SP_RECALL_L5 cosine-match->TEXT-in-context, gated after Jaccard. 7 leaks=hard parametric conflicts. Combiner (Jaccard+L5+KSTE-MD) does NOT beat L5 alone (redundant/dead); value=foreign-reject(untested). Serve _faithful_serve_l5.bat; keys write_ep_l5.py. Follow-ups: capture-side ep.l5 for live episodes; gate/max J+L5; scale >61.
timestamp: 2026-07-01T03:09:13Z
resource: engine main d9099cd (merge feat/l5-recall)
sp_status: GREEN
sp_gate: G-L5-RECALL-LIVE-2026-07-01
sp_commit: engine main d9099cd (merge feat/l5-recall)
sp_repro: _faithful_serve_l5.bat + write_ep_l5.py + SP_FAITHFUL_USE_PARA=1 python tests/perf/_g_faithful_recall.py
mem_kind: agent
mem_addr: a68effca6cdacdaa
tags: [L5, recall, SP_RECALL_L5, live, GREEN-LIVE, paraphrase, faithfulness, 86.89, wired, ep.l5, combiner, directional, agent, tier-2]
mem_tier: full
---

# SP_RECALL_L5 is LIVE-GREEN — paraphrase recall cracked on the served 12B (86.89%)

The L5 finding is now WIRED + GATED LIVE on the real served gemma-4-12B. The faithfulness paraphrase wall (Jaccard ~8%) is broken.

**Wiring (engine branch `feat/l5-recall`, release build 0 errors):** `Episode.l5key` + `recall::l5_query_embed` (global-layer-5 mean-heads + L2-norm of read_global_q) + `recall::cos512` + `recall::load_episode_l5key` (reads `<dir>/ep.l5`); `routes.rs` `SP_RECALL_L5` branch cosine-matches the live query L5 vs each episode's ep.l5 key, delivers episode TEXT in-context (F2b), gated after Jaccard. Default-off (`SP_RECALL_L5` unset) = byte-identical null floor.

**Live gate `G-L5-RECALL-LIVE-2026-07-01`** (61 fact-conflicts, paraphrase queries, tau=0.30, ep.l5 keys = exact-question L5 staged by write_ep_l5.py):
- **paraphrase OBEY = 53/61 = 86.89%** (LEAK=7, OTHER=1) vs deployed Jaccard ~8.2%; matches offline prediction 88.5% within noise.
- exact-query alignment perfect: EXACT France->fct_000 cos=1.000->"Lyon"; EXACT Brazil->fct_019 cos=1.000->"Recife".
- 7 leaks = hard parametric conflicts (Sun-is-a-star, Mona-Lisa-Louvre, Everest-Asia, Olympics-4yr, photosynthesis-CO2) where the planted counter-fact loses to unshakeable knowledge; 1 OTHER = safe abstain.

**Combiner (rep_combine.py):** gated (Jaccard-else-L5) or learned-logistic over [Jaccard,L5,KSTE-MD] does NOT beat L5 alone — L5 already does 100% exact / ~88% para, so Jaccard is redundant and KSTE-MD is dead on this DIRECTIONAL axis (learned weight ~0.14, MD-only para=0%). The multi-signal head's remaining value is foreign-reject/abstention calibration (untested — no foreign queries in corpus), NOT recall@1.

**Serve:** `tools/sp_daemon/_faithful_serve_l5.bat` (SP_RECALL_L5=1). Keys staged via `_faithful_corpus/write_ep_l5.py`.

**Follow-ups:** (1) capture-side ep.l5 write for LIVE-captured episodes (currently only disk episodes have keys; live-captured get Vec::new()); (2) gate/max Jaccard+L5 in one selector for exact+para; (3) scale beyond n=61; (4) foreign-reject test for the combiner.
