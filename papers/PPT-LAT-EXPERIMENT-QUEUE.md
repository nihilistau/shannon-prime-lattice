---
type: design
title: "Experiment Queue — the faithfulness-selection frontier + adjacent axes (2026-07-03)"
description: "A prioritized, falsifiable experiment ledger opened after the selector campaign CLOSED (G-WCHEAD-SAMETEMPLATE: same-template instance selection is a REPRESENTATION limit of the global-Q/K features). Every convicted lever operated on the SAME collapsed features; new experiments only count if they bring NEW signal or move disambiguation off the retrieval key. Seven experiments in three tiers (sidestep the ceiling / test the representation / new axes), each with hypothesis, cheapest decisive test, and a pre-registered decision rule."
tags: [design, experiment-queue, faithfulness, selection, same-template, representation, delivery, swarm, geodesic, roadmap]
timestamp: 2026-07-03T00:00:00Z
resource: shannon-prime-lattice/papers/PPT-LAT-EXPERIMENT-QUEUE.md
sp_status: ACTIVE
sp_gate: "E1 DONE (obey 22->25 but leak 0->4, authority dilution) · E2 CONVICTED (yes/no can't separate same-template, both framings) · E8 two-stage = NEW recommended next · E3-E7 QUEUED (G-E1-E2-DELIVERY)"
sp_commit: "opened after engine 933ea88 (G-WCHEAD-SAMETEMPLATE) + lattice 6d06b6b; E1/E2 run this session"
sp_repro: "per-experiment repro lines below; layer-probe seed = _v3_corpus/layer_probe.py on _b3_wc/b3_data_v3.npz"
---

# Experiment Queue — faithfulness-selection frontier + adjacent axes

**Context (where this opens).** The selector campaign is CLOSED. Every cross-pick lever is
convicted with a receipt: rerank (correct buried >8), lexical overlap (adversarial
paraphrase), name-the-subject micro-forward (names the ANSWER, leaks), margin-NULL
(net-negative), veto head (outcome-neutral), and a LEARNED W_c relevance head
(`G-WCHEAD-SAMETEMPLATE`: 0% held-out top-1 across r×wd×dropout×seed). The residual —
~8/30 same-template cross-picks on the adversarial V3 counterfact corpus — is a
**representation limit** of the periodic global-Q/K features, not a tuning gap. Shipped
faithfulness stands: **systemecho delivery + question-space keys = 21-22/30 obey @ 0 leak**
on the crucible, **~100% on unique-subject** recall (the needle regime = real episodic memory).

**The frame.** All convictions operated on the SAME collapsed features. A new experiment
counts only if it (a) brings NEW signal (a different capture layer / token-position / raw
text), or (b) moves disambiguation OFF the retrieval key (deliver candidates, let generation
choose), or (c) opens a different axis entirely (mesh, transport, attend-don't-select).

**Seed probe (free, run 2026-07-03).** `_v3_corpus/layer_probe.py` on the existing
`b3_data_v3.npz`: per-global-layer raw cosine with the STATEMENT-space mean-K episode rep
scores 1.9-6.5% top-1 (best = global-17), all-layer concat 0%. CONFOUNDED (statement-space
rep, which we know collapses) — it does NOT test question-space per-layer keys; it only
re-confirms statement-space is hopeless at every layer and hints global-17 carries marginally
more instance signal. The clean layer test is E3.

---

## Tier 1 — cheap, sidesteps the selection ceiling

### E1 — Full-candidate / template-family delivery (let GENERATION disambiguate)
**Hypothesis.** The decode sees the full query; the retrieval key does not. If the correct
fact is IN the delivered context, generation picks the right same-template instance better
than the selector picks at retrieval time. (Note: for the 8 cross-picks the correct fact is
buried at L5 rank >8, so "top-3" would miss it — the honest test delivers the full candidate
set or the template family.)
**Cheapest test.** No routes change: a harness posts, per V3 query, a systemecho-style
context listing ALL 30 grown facts (and a family-only variant) + the paraphrase, `auto_recall:false`;
measure obey/leak vs the 21-22/30 baseline.
**Decision.** Full-context obey → ~30/30 @ 0 leak ⇒ selection dissolves into "deliver the
family, read at generation"; ship a coarse family-deliver (family detection ≪ instance
selection). If leak climbs or obey stalls ⇒ generation ALSO collapses same-template ⇒ the
limit is the model's, not the selector's.
**Cost.** ~15 min (one harness run). Receipt: `G-E1-FULLCTX-DELIVERY`.
**RESULT (2026-07-03, `G-E1-E2-DELIVERY`): OBEY 25/30 (+3 over baseline) but LEAK 0→4.**
Generation-time disambiguation WORKS — recovered hamlet/starry_night/evolution (retrieval
cross-picks the L5 key buried). But dumping 30 facts DILUTES per-fact authority ⇒ 4 leaks
(fuji→Japan, kenya, colosseum, dynamite) — the 0-leak property of single-fact systemecho is
lost. A real obey gain traded against a leak regression. → drives E8 (two-stage) + family-scope.

### E2 — Binary yes/no grounding gate (honest decline, no leak vector)
**Hypothesis.** "Does *fact* answer *query*? yes/no" is more reliable than the parked A/B/C
rerank AND never surfaces the answer (the leak mode that killed name-the-subject). It won't
un-bury the correct fact, but it can REJECT the wrong same-template magnet ⇒ decline instead
of confidently-wrong.
**Cheapest test.** For the 8 cross-picks: ask yes/no for (query, correct-fact) and (query,
magnet-fact); measure separation. Also on the 22 correct as controls.
**Decision.** correct→YES, magnet→NO cleanly ⇒ a grounding filter + decline trigger; wire as
a spine Decider (Deliver→Decline). Muddy ⇒ drop.
**Cost.** ~20 min. Receipt: `G-E2-YESNO-GROUNDING`.
**RESULT (2026-07-03, `G-E1-E2-DELIVERY`): CONVICTED — 0/9 separation in BOTH framings.**
"Does the fact ANSWER the question?" → all NO (invokes TRUTH; counterfacts are false).
"Is it ABOUT the same thing?" (topicality, truth ignored) → the MAGNET also gets YES
(dynamite-question and radium-fact are the same "who-discovered-a-scientific-thing" topic —
exactly why it's a magnet). Not a usable filter or decline trigger. E2 closed.

---

### E8 — Two-stage delivery (select-in-full-context, generate-single-fact-authoritative)
**NEW, surfaced by E1+E2.** E1 proved generation CAN disambiguate same-template when it sees
the candidates; its only defect is that multi-fact context dilutes the single-fact authority
that gives 0 leak. **Two-stage:** (1) SELECT — full-candidate (or family-only) context →
"which numbered fact answers this?" → an INDEX (generation's disambiguation, no value spoken
⇒ no leak); (2) GENERATE — deliver THAT single fact with systemecho authority (0-leak).
**Hypothesis.** Captures E1's +3 obey AND keeps systemecho's 0 leak. **Test.** Two-call
harness on V3; measure obey/leak. **Decision.** obey ≥ 25 @ leak ≤ 1 ⇒ wire as the recall
executor (a spine two-step: Decide-index → Execute-single). **Cost.** ~20 min. `G-E8-TWOSTAGE`.

---

## Tier 2 — test whether the representation limit is fundamental or layer-specific

### E3 — Question-space per-layer key sweep (the clean version of the seed probe)
**Hypothesis.** An earlier/more-lexical layer carries the instance-subject that the periodic
global-L5 discards (seed hinted global-17). **Test.** Mint each episode's QUESTION key at
EVERY layer (extend the mint + `SP_B3_QDUMP` to dump all layers), match per-layer, re-run the
exact held-out bar (`b3_train_wc_holdout`) per layer. **Decision.** Any layer ≫ 0% holdout ⇒
dual-key deploy (structure-layer for paraphrase robustness + subject-layer for instance).
All ≈ 0% ⇒ the limit is confirmed representation-wide. **Cost.** ~1-2 hr. `G-E3-LAYER-SWEEP`.

### E4 — Subject-token position max-match
**Hypothesis.** The subject token ("dynamite") sits at a specific position; max-over-position
query-token↔episode-token similarity separates where mean/attention pooling washes it out.
**Test.** Per-token query capture; offline max-match on the V3 set. **Decision.** Correct
subject-token pair is the global max ⇒ a position-aware selector. **Cost.** ~1 hr. `G-E4-TOKPOS`.

---

## Tier 3 — new axes, higher ceiling

### E5 — SWARM 2-node MEM-OKF replication (re-elevated PRIMARY)
First falsifiable brick of the memory mesh (`PPT-LAT-DESIGN-SWARM-MEMORY-MESH`):
content-addressed, signed replication of the store across two nodes (libp2p noise / X25519 /
Ed25519 / ChaCha20-Poly1305 — audited crypto, not rolled). **Gate.** byte-exact addr-join +
receipt-ledger consistency across nodes. **Cost.** multi-session. `G-E5-SWARM-2NODE`.

### E6 — GEODESIC rung 2 (ADR-003 pre-registered)
Per-layer `capture_feat` tap at the TELE-2 seam (~global 16-22); re-run straightness +
steering there — rung 1 was an honest negative at the FINAL layer (final-norm expresses not
causes). **Decision.** Tier-A straightness + causal steer at the seam ⇒ FM head earns a build.
**Cost.** ~half-session. `G-FM-STEER-OBEY-RUNG2`.

### E7 — Attend-don't-select (RAG-in-cache)
The reframe: keep all episodes' K resident and let the live decode ATTEND over the memory
bank at generation time instead of pre-selecting one. Selection may be the wrong abstraction;
attention sees the full query. Rides the xbar / Ring-3 integer substrate. **Gate.**
attend-over-N beats select-1 obey on V3 @ 0 leak. **Cost.** high (architectural). `G-E7-ATTEND`.

---

## Order of attack
E1 → E2 (this session, cheap, attack the residual where the full query is visible) → then
branch: if E1/E2 clear it, the ceiling is moot; if not, E3 (representation) or pivot to E5
(SWARM, the primary forward axis). E6/E7 are the bigger swings held in reserve.
