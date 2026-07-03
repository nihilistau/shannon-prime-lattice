---
type: memory
title: PRE-FLIGHT NEGATIVE: learned W_c relevance head does NOT generalize same-template instance discrimination (0% holdout); campaign CLOSED (G-WCHEAD-SAMETEMPLATE)
description: Trained the W_c relevance head (existing machinery: SP_B3_QDUMP + b3_make_dataset + b3_train_wc_holdout) on 108 positive + 20 foreign queries over the 30 V3 same-template episodes. Held-out-EPISODE generalization: train-diagonal 96.6/64.4/97.7% but HOLDOUT top-1 = 0% across r={16,4,8} x wd/dropout x seed; misses cross-pick onto TRAINED same-template episodes; foreign-reject 100%. The head MEMORIZES trained episodes, learns ZERO generalizable subject-matching -> useless for novel live episodes. THE LAST UNCONVICTED CROSS-PICK LEVER IS NOW CONVICTED. Same-template instance-selection is a REPRESENTATION limit of the global-Q/K features, not a tuning gap. DO NOT retry a learned metric on the same features expecting generalization. NOT SHIPPED (pre-flight RED = no deployed head, per ADR-003). SCOPE: V3 is adversarial worst case; unique-subject recall ~100% (needle regime) so real episodic memory is fine. Shipped faithfulness: systemecho + question-space keys = 21-22/30 obey @ 0 leak. Future: only a DIFFERENT feature (earlier/lexical capture layer, or cross-encoder over raw tokens) could move it - test vs this held-out bar.
timestamp: 2026-07-03T07:24:05Z
resource: engine 933ea88
sp_status: GREEN
sp_gate: G-WCHEAD-SAMETEMPLATE
sp_commit: engine 933ea88
sp_repro: run_v3_qdump.bat + b3_make_dataset.py --live + b3_train_wc_holdout.py _b3_wc/b3_data_v3.npz --r 16 --wd 1e-3; receipt G-WCHEAD-SAMETEMPLATE.log
mem_kind: episode
mem_addr: 90fa9ecc2eaa9b31
tags: [wc-head, relevance-head, same-template, holdout, pre-flight-negative, cross-pick, representation-limit, selector-ceiling, V3, episode, tier-2]
mem_tier: full
---

ï»¿G-WCHEAD-SAMETEMPLATE â€” PRE-FLIGHT NEGATIVE (robust): a learned W_c relevance head does
NOT generalize same-template instance discrimination to NOVEL episodes. Holdout top-1 = 0%
across 3 configs. The last unconvicted cross-pick lever is now CONVICTED. (2026-07-03)
=========================================================================================
Follow-on to G-QKEYS-MINTFIX (which proved the V3 cross-pick ceiling is STRUCTURAL
same-template L5 collapse, not key quality). The only lever not yet convicted was a LEARNED
same-template relevance head. This is its pre-flight â€” built on the EXISTING machinery
(anti-rebuild): SP_B3_QDUMP capture seam + b3_make_dataset.py + b3_train_wc_holdout.py + the
deployed WcHead (SP_B3_WC). No new training architecture written.

DESIGN: W_c : R^HD->R^r learns a relevance metric S(query,episode) over the RICHER
per-position global-K features (not the L5-mean that collapses): projected QÂ·K attend,
logsumexp over positions, mean over (layer,head); InfoNCE over [episodes,NULL] + hard-neg
hinge. This is the same head that scored 360/361 on the UNIQUE-SUBJECT needle corpus
(G-CHAT-B3-WC-DIV2). The question: does it separate SAME-TEMPLATE novel episodes?

DATA (all reproducible): _v3_corpus/manifest.jsonl = 30 V3 episodes Ã— canonical question
(from ep.q) + model-generated paraphrases = 108 positive queries; foreign_queries.txt = 20
NULL. Captured each query's last-token global-Q via SP_B3_QDUMP (run_v3_qdump.bat +
b3_make_dataset.py --live) -> _b3_wc/b3_data_v3.npz (128 Q vectors + 30 episode K from ep.k).

ZERO-BUILD PRE-PROBE (existing wc_deploy.bin, needle-trained, on V3): 1/30 correct-rank-1
(vs L5-cosine 22/30) â€” OOD-degenerate, one episode magnets every query. Inconclusive on
its own (OOD blob) but motivated the same-template retrain.

RETRAIN + HELD-OUT-EPISODE GENERALIZATION (b3_train_wc_holdout.py; 20% episodes held out
ENTIRELY from train softmax + loss; each held-out episode's paraphrases scored vs ALL 30
episodes + NULL, (E+1)-argmax; top-1 iff the matched held-out episode wins):
  r=16 wd=1e-3           : train-diagonal 84/87=96.6%  HOLDOUT 0/21=0.0%  foreign-reject 20/20
  r=4  wd=1e-2 drop=0.2  : train-diagonal 56/87=64.4%  HOLDOUT 0/21=0.0%  foreign-reject 20/20
  r=8  wd=3e-3 drop=0.1 s3: train-diagonal 84/86=97.7%  HOLDOUT 0/22=0.0%  foreign-reject 20/20
  Holdout misses are SYSTEMATIC: ->trained-needle 16/10/15, ->NULL 4/10/7, ->other-holdout 1/1/0.

VERDICT â€” ROBUST PRE-FLIGHT NEGATIVE. The head MEMORIZES the training episodes (96.6%
in-sample) but transfers NOTHING to unseen same-template episodes (0% across capacity +
regularization + seed). A held-out "who-invented-X" episode's paraphrase cross-picks onto a
TRAINED same-template episode â€” the exact structural collapse, now in W_c space. Because a
DEPLOYED head must place NOVEL live episodes it never trained on, 0% holdout = useless in
production. The features (global-Q Ã— global-K at the periodic global layers, W_c-projected
attention) do NOT carry a generalizable query-subject<->episode-subject matching signal that
transfers to unseen subjects; foreign-reject IS learnable (100%), instance-within-template
is not.

CAMPAIGN CLOSED. Every cross-pick lever is now convicted with a receipt:
  rerank (correct buried >8) Â· lexical subject-overlap (adversarial paraphrase) Â·
  name-the-subject micro-forward (names the ANSWER, leaks) Â· margin-NULL (net-negative) Â·
  veto head (outcome-neutral) Â· LEARNED relevance head (0% holdout, THIS receipt).
The same-template instance-selection ceiling is a REPRESENTATION limit, not a tuning gap.

SCOPE / PRACTICAL IMPACT (honest): the V3 corpus is an ADVERSARIAL worst case â€” 30 novel
counterfacts in tight same-template families. Real episodic memory is closer to the
UNIQUE-SUBJECT needle regime where L5-cosine already recalls ~100% (G-CHAT-B3-WC-DIV2
360/361). So this ceiling bounds the worst case, not the typical case. Shipped faithfulness
stands: systemecho delivery + question-space keys (fixed minting) = 21-22/30 obey @ 0 leak
on the crucible; unique-subject recall ~100%.

NOT SHIPPED: no deployed head (pre-flight RED = do not wire, per ADR-003 discipline). KEPT:
the capture+train pipeline + b3_data_v3.npz + manifest (fully reproducible) so a future
FEATURE change (a different/earlier capture layer that may carry subject lexically, or a
cross-encoder over raw tokens) can be tested against this exact held-out bar.

REPRO: run_v3_qdump.bat (SP_B3_QDUMP) + python tools/xbar_lsh/b3_make_dataset.py --live
--manifest _v3_corpus/manifest.jsonl --foreign _v3_corpus/foreign_queries.txt --registry
_v3_corpus/registry.jsonl --qdir _b3_wc/qdump_v3 --out _b3_wc/b3_data_v3.npz ; then
python tools/xbar_lsh/b3_train_wc_holdout.py _b3_wc/b3_data_v3.npz --r 16 --wd 1e-3.
Gen: _v3_corpus/gen_manifest.py. ENV: engine 18a22dc + this commit; RTX 2060 12GB, gemma4-12b-b1.
