---
type: design
title: "ADR-003 (proposal) — Flow Matching as the continuous transport of the DECIDE tier"
description: "Rectified Flow / Flow Matching is the exact-integer-friendly, deterministic transport that parametrizes the latent DECIDE tier of ADR-002. The affine interpolant x_t=(1-t)x0+t·x1 and label v*=x1-x0 carry natively on the O_K dual-prime substrate (no sqrt-alpha schedule, no Langevin noise); the learned velocity field v_θ(x_t,t) IS a spine Decider (a latent head). This ADR sets the falsifiable path: measure coupling STRAIGHTNESS on the idle F3 residuals FIRST, then a lightweight FM head for (a) faithfulness steering, (b) 1-step EAGLE-draft verification, (c) recall-as-flow. Honest scope: FM bridges the DECIDE tier to exact-integer determinism — it does NOT make tokens continuous (the token projection stays the clean-text EXECUTE tier). That is ADR-002, not a departure from it."
tags: [design, adr, flow-matching, rectified-flow, latent-transport, faithfulness, spine, decide-execute, capture_feat]
timestamp: 2026-07-03T00:00:00Z
resource: shannon-prime-lattice/papers/PPT-LAT-ADR-003-FLOW-TRANSPORT.md
sp_status: DESIGN
sp_gate: "pre-flight: G-FLOW-STRAIGHTNESS (measure F3 coupling curvature) before any head is trained"
sp_commit: "proposal — no engine change until the straightness pre-flight is GREEN"
sp_repro: "idle data: F3 with/without-sys-prompt residuals (capture_feat); measure transport curvature"
---

# ADR-003 (proposal) — Flow Matching as the DECIDE-tier transport

## 1. The claim, stated precisely

Flow Matching (rectified flow) is **the continuous transport that the ADR-002 DECIDE tier
has been missing a principled parametrization for.** Two properties make it fit the canon:

* **Substrate-native.** The forward process is a pure affine combination,
  `x_t = (1-t)·x0 + t·x1`, and the regression target is `v* = x1 - x0`. On a quantized time
  grid `t ∈ {0, 1/N, …, 1}` these are exact-integer operations — they carry on the O_K
  dual-prime CRT-NTT ring with NO float drop. This is the opposite of DDPM, whose
  `sqrt(alpha)` schedules + Langevin noise are structurally hostile to the exact substrate.
  FM strips the stochasticity out of the transport layer.

* **A velocity field is a Decider.** `v_θ(x_t, t)` reads a residual (a latent) and returns a
  vector (a decision-relevant quantity). In the spine (`spine.rs`) that is precisely a
  `LatentHead` → `Decider`. FM does not add a new tier; it is the natural continuous
  parametrization of the tier the spine already composes.

## 2. Which bridge this is (and which it is NOT)

The honest answer to "is this the bridge between the continuous manifold and our discrete
substrate?": **yes — for the DECIDE tier, not the EXECUTE tier, and that is exactly right.**
FM makes the latent *decision* layer exact-integer-native and deterministic. It does NOT make
*tokens* continuous — the projection latent→token (argmax/sample) remains the discrete
sampling of the manifold, i.e. the clean-text EXECUTE tier. So: FM velocity field DECIDES
(steer / verify / select) in exact-integer latent; the token projection EXECUTES in clean
symbol. That is ADR-002 verbatim. The "bridge" is that FM gives the DECIDE side a deterministic,
auditable, substrate-friendly physics — the same physics the byte-exact forward already wants.

## 3. Where it is a bet, not a certainty (Shannon-Prime honesty)

* **Straight lines are not free.** Rectified-flow trajectories are only straight if the
  coupling `(x0, x1)` is near-optimal-transport OR after *reflow* (retraining on the model's
  own couplings). On a RANDOM coupling the marginal field is curved (the crossing trajectories
  in the reference slides — the "X" — average into a bent flow), and a 1-step Euler then has
  large truncation error. OUR couplings are NOT random: they are a specific conditional map
  (parametric-latent → faithful-latent, given the context), which CAN be near-straight. But
  that is an empirical question, and it gates everything. **Measure straightness before you
  build.**
* **Steering ≠ guaranteed faithfulness.** "Add `v_θ` to the residual to move parametric→faithful"
  is activation/representation steering. It sometimes works (refusal, sentiment directions) and
  sometimes degrades coherence. FM gives it a *principled training objective* (regress to `v*`)
  instead of a hand-picked direction — a real improvement — but whether the injected velocity
  moves the OUTPUT distribution toward the faithful answer WITHOUT wrecking coherence is
  falsifiable, not assumed. The project already solves faithfulness via the clean-text
  text-in-context path at 88.52% obey / 0 leak (G-ONECONFIG-LIVE). The FM steering head is an
  ALTERNATIVE latent mechanism that must EARN its place against that baseline.
* **The concrete win condition (why it's worth the bet):** the text-in-context path pays a
  delivery re-prefill — the 71s turn-4 brick (G-RECALL-DEADSCAN-SKIP §C). A latent steering
  head that biases the residual toward faithfulness AVOIDS the re-prefill entirely. So the FM
  head is not just "another way to be faithful" — it is potentially a MUCH cheaper way, with a
  measurable target: match/beat 88.52% obey at a fraction of the latency, with no coherence loss.

## 4. Uses across the system (beyond speculative decoding)

1. **Faithfulness steering head (the roadmap's Faithfulness Head, now with a training physics).**
   `x0` = parametric-answer residual, `x1` = faithful-answer residual (the idle F3 captures).
   Train `v_θ` to regress `v* = x1 - x0`; a 1–2 step Euler update steers the residual toward the
   faithful state. A spine `Decider` that injects the velocity — decide in latent, execute in
   clean text. **Win:** avoid the delivery re-prefill.
2. **1-step EAGLE/MTP draft verifier (resurrect the parked diffusion judge).** The native
   diffusion judge died on iterative denoise (too many forwards, I/O-blocked, ~50% plateau).
   An FM velocity head verifies in ONE forward: given the draft-token latent `x_t`, if
   `x_t + v_θ` lands near the accepted-token latent, ACCEPT; else REJECT. O(1)/draft, exact-integer,
   a spine Decider emitting Accept/Reject. This is the most falsifiable near-term prototype.
3. **Recall AS a flow (the multi-target field).** The reference "conditional velocity field
   `v_t(·|x1)`" slides with multiple targets `x1, x1', x1''` are LITERALLY a memory bank as flow
   attractors: the field points the query latent toward whichever stored episode is conditionally
   nearest. That subsumes L5 cosine (cosine is a crude 1-step approximation of the flow
   direction). Potentially the recall SELECTOR itself, not just the judge.
4. **FM as the UNIVERSAL training framework for the whole head bank (the meta-insight).**
   ADR-LATENT-NATIVE-UNIFICATION says every symbolic gate graduates to a latent head. FM gives a
   UNIFORM way to train ANY of them: define source residual + target residual, regress the
   velocity. Recall head, route head, safety head, tool-detect head — each is a conditional
   velocity field to a different target, all with the same `v* = x1 - x0` objective. The spine
   COMPOSES heads; flow matching TRAINS them. That is the deep unification.
5. **Deterministic, auditable sampler.** The ODE is deterministic + affine ⇒ the sample path is
   reproducible + cross-machine-identical by construction — the auditability axis the byte-exact
   substrate already targets.
6. **26B diffusion-gemma reframe (#37).** The parked 26B masked-diffusion LM (arch 9,
   "underperforming") reframed as a rectified flow could decode in 1–4 steps instead of 12+ —
   the flow-matching answer to the #37 backlog.
7. **Reflow as a NIGHTSHIFT self-distillation loop.** Rectified-flow's reflow (straighten
   trajectories by retraining on your own couplings) is offline — a natural NIGHTSHIFT job: the
   system straightens its own steering fields between turns.

## 5. The falsifiable path (receipts-first — measure before you build)

**Pre-flight gate `G-FLOW-STRAIGHTNESS` (one afternoon, engine untouched):** on the idle F3
residual pairs (parametric `x0` vs faithful `x1`, from `capture_feat`), measure the transport
**curvature** — how far the true conditional path deviates from the straight interpolant. Cheap
proxies: (a) cosine(`x1-x_t_mid`, `x1-x0`) across t; (b) the residual of a 1-step Euler vs the
true endpoint; (c) coupling-crossing rate. **If straight enough** (low curvature) ⇒ few-step FM
is viable ⇒ train the lightweight head. **If curved** ⇒ reflow needed, or it is inherently
multi-step ⇒ re-scope. This one measurement de-risks the entire direction and is the honest
first step. FIRST confirm the F3 faithfulness residuals are actually captured on disk (the ADR
says "engine untouched until data is in hand") — `_b3_wc/` holds the W_c selector data, not
obviously the F3 with/without-prompt residuals; the capture may still be a TODO.

**Then, in order:** (1) FM-judge for EAGLE drafts (most falsifiable, 1-forward, own gate vs
current accept-rate); (2) faithfulness steering head, gated vs the 88.52% text-in-context
baseline (obey + coherence + latency); each wired as a spine `Decider` (decide in latent,
execute in clean text). Every head default-off with a byte-exact null floor.

## 6. Fit with the canon
ADR-002 (Decide→Execute): HELD — FM decides in latent, tokens execute in clean text.
ADR-LATENT-NATIVE-UNIFICATION: this IS the training physics for the Faithfulness Head + the
head bank. Spine (`PPT-LAT-SPINE-FRAMEWORK`): an FM velocity head is a `LatentHead`/`Decider`.
O_K substrate: affine + quantized-t transport is exact-integer native. Nothing here contradicts
a proven result; it proposes the transport that the DECIDE tier was missing, with a measurement
gate in front of the build.
