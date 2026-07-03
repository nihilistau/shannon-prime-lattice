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
tags: [wc-head, relevance-head, same-template, holdout, pre-flight-negative, cross-pick, representation-limit, selector-ceiling, V3, episode, tier-1]
mem_tier: summary
mem_full: 90fa9ecc2eaa9b31
---

# PRE-FLIGHT NEGATIVE: learned W_c relevance head does NOT generalize same-template instance discrimination (0% holdout); campaign CLOSED (G-WCHEAD-SAMETEMPLATE)

Trained the W_c relevance head (existing machinery: SP_B3_QDUMP + b3_make_dataset + b3_train_wc_holdout) on 108 positive + 20 foreign queries over the 30 V3 same-template episodes. Held-out-EPISODE generalization: train-diagonal 96.6/64.4/97.7% but HOLDOUT top-1 = 0% across r={16,4,8} x wd/dropout x seed; misses cross-pick onto TRAINED same-template episodes; foreign-reject 100%. The head MEMORIZES trained episodes, learns ZERO generalizable subject-matching -> useless for novel live episodes. THE LAST UNCONVICTED CROSS-PICK LEVER IS NOW CONVICTED. Same-template instance-selection is a REPRESENTATION limit of the global-Q/K features, not a tuning gap. DO NOT retry a learned metric on the same features expecting generalization. NOT SHIPPED (pre-flight RED = no deployed head, per ADR-003). SCOPE: V3 is adversarial worst case; unique-subject recall ~100% (needle regime) so real episodic memory is fine. Shipped faithfulness: systemecho + question-space keys = 21-22/30 obey @ 0 leak. Future: only a DIFFERENT feature (earlier/lexical capture layer, or cross-encoder over raw tokens) could move it - test vs this held-out bar.

Full context: [full/90fa9ecc2eaa9b31.md](../full/90fa9ecc2eaa9b31.md)
