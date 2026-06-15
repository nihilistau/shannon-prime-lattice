# DESIGN — Tiered Crossbar (Split-Brain) + the Latent Terminal (BANKED, 2026-06-15)

**Status: BANKED / PARKED.** This is a destination, not the current lane. We do **not** pivot the
topology while the single-model substrate primitives are still being verified. The discipline is
substrate-first: lock the complete platform (**SP PPT ARM LAT · XBAR · KAIROS · OMICRON · HOLON**)
on the resident 12B, *then* finetune / experiment / re-tier. This note exists so the idea is on the
record and the design corrections aren't lost. No receipts here — nothing below is measured yet.

---

## 1. The thesis (operator, 2026-06-15)

The 3-ring crossbar substrate is the **scale-invariant**; the model is a **swappable tenant**. The
pointer-shear, undo-journal (KAI-1c), O(1) ring rewind (KAI-1b), and `off[L]` episode indirection all
live at the tensor-routing layer and are agnostic to parameter count. **This is already demonstrated,
not hypothetical:** the KAI-1 harness ran the *same* logic on qwen3-0.6B (Path A) and gemma-4-12B
(Path B). So the same execution block drops into any tier interchangeably.

The inversion: instead of a heavy brain resident on the edge, run the **reflex tier** (a small
same-family model) resident — it maintains the fast loop — and let a **cerebrum tier** (a larger
same-family sibling, locally on a workstation or spun up in cloud) do deep cognition and hand its
conclusion *down* through the injection seam.

## 2. The tier ladder (why Gemma-4 was the right family bet)

Google shipped a same-vocab, same-architecture family — **E2B · E4B · 12B · 26B-A4B · 31B** (and
whatever odd counts come next). They share the **262K vocab and embedding geometry**. That shared
basis is the *enabling property* of the whole inversion (see §4). A plausible deployment ladder:

```
[ E2B / E4B reflex ]  --(injection seam)--  [ 12B mid ]  --(R3 consolidation)--  [ 26B/31B cerebrum, cloud-spun ]
   resident, R1(+R2)                            resident                              episodic / on-demand
```

## 3. Ring mapping — with the latency correction

Gemini's draft put the cerebrum "operating on R2/R3." **Correction:** in our latency model **R2 (the
action/episode log, spilled KV in Ring-2) must stay resident** on the reflex tier — if R1 attention
had to read R2 across the tier boundary, every heartbeat tick stalls on a remote recall. The clean
split is **R1 + R2 local**, and only **R3 (slow consolidation) crosses the tier boundary**, async and
off the hot path. The cerebrum's real job is therefore **not** to inject raw activations; it is to
**consolidate episodes into R3 directives the reflex recalls in its own basis** (the hippocampal →
neocortical link already specced in RFC v1.1). That sidesteps cross-model fidelity entirely.

## 4. The Latent Terminal (the custom "output model")

The operator's sharper form: build **our own** small model whose sole job is to accept latent inputs
and faithfully emit them — a *token vocoder* (the discrete-output twin of the voice lane's
latent→audio codec; structurally a spec-decode drafter / MTP head).

Four design locks:

- **Tap-depth is the cost, and it isn't free.** "Faithfully output the latent" is cheap only when the
  latent is *near the output*. A deep/abstract latent (the whole point of offloading cognition) still
  has to be pushed through the transform between the tap and the tokens — so a deep tap forces the
  actuator to *reconstruct the cerebrum's upper stack*. **Pareto frontier:** cerebrum-does-everything /
  thin head ⇄ shallow offload / fat actuator. Actuator size scales with how much reasoning you push
  upstream. Design *against* this knob; don't assume it away.
- **Tied-embedding reuse (the same-family payoff, made concrete).** Gemma ties word embeddings
  (`tie_word_embeddings: true`, 12B config). So the **final-residual → token** map *is the shared 262K
  embedding matrix transposed*. A final-tap actuator **reuses the family's output basis by
  construction** — the decode head already exists and is shared. This is the precise reason the family
  matters, beyond "compatible vocab."
- **Adapt, don't train from scratch.** From-scratch forfeits the shared basis — a tabula-rasa net has
  to *learn* the cerebrum's coordinate system, which re-creates the cross-model translation problem.
  "Our own model" = a **same-family adaptation** (fine-tuned E2B, or a thin head on the shared
  embedding), not zero.
- **Verify, don't trust.** Faithfulness is a **gate**, not a hope. Spec-decode / MTP byte-exact accept
  (we have it: MTP 1.65–1.76× with bit-identical verify) lets the cerebrum check the actuator's
  emission and reject on divergence. The actuator is *allowed* to be approximate because verify catches
  drift.

## 5. Corrections logged (so we don't repeat the Gemini framing)

- **Cross-model latent projection is unsolved and strictly *harder* than within-model injection.** Our
  own evidence: the P2.b campaign (span→k, six forks, top-1 ≤ 0.462, generation dead at k=2) showed
  latent-content fidelity is hard even within *one* shared basis. "A projection matrix" hand-waves the
  load-bearing research. The same-family + tied-embedding route is what makes it tractable at all.
- **Cloud-cerebrum vs. the north star.** A *cloud-critical* cerebrum reintroduces the network round-trip,
  privacy loss, and an offline failure mode KAIROS exists to delete. Only the **local** split-brain or a
  **verified** same-family link keeps the edge-autonomy thesis intact; the reflex must remain useful
  with the cerebrum absent.
- **No invented numbers.** Gemini's "~2,300 ms" / "<50 ms" tick figures are fabricated. Measured
  reality: the 12B daemon tick is ~8–17 s on the 2060 (scalar reference forward), engine path 26 tok/s.
  Any latency claim here waits for a receipt.

## 6. Why the current KAI-2 work is the first rung (not a detour)

The KAI-2 codec being trained now is the **input mirror** (event → latent → 12B). The Latent Terminal
is the **output mirror** (latent → small model → tokens). **Same injection seam, same thin-map-at-the-
embedding-port machinery, same verify discipline.** Proving the input side now *is* building the output
side's toolkit. You cannot do split-brain projection until within-model injection fidelity is proven, so
finishing KAI-2 is the necessary first rung of *any* version of this. Nothing forks.

## 7. Revisit trigger + pre-registered future gates (named, not run)

Revisit **after** the substrate platform is locked (XBAR P3 complete, KAIROS K-series closed, pillars
in place). Then, before building the terminal:

- **G-TERMINAL-NULL** — a same-family actuator reproduces the cerebrum's final-tap next-token
  distribution under byte-exact verify (fidelity is a gate, not a metric to hope toward).
- **G-TERMINAL-TAP** — tap-depth sweep: actuator size vs. offloaded-cognition Pareto, to pick the
  operating point.
- **G-TIER-PARITY** — same-family projection parity: E2B reads a 12B near-final latent and lands on the
  shared tied-embedding basis without a learned re-projection.

Cross-refs: RFC-XBAR (ring substrate), CONTRACT-KAIROS-K0-K1 §6.3 (the injection-seam codec this
reuses), RFC v1.1 R3 consolidation amendment, DESIGN-diffusion-lane (T8 drafter / verify prior art).
