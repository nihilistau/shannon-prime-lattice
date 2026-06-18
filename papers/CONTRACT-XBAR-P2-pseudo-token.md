---
type: contract
title: "CONTRACT XBAR-P2 — Pseudo-token injection (the deployable mechanism, and the stall fix)"
description: "Parent: RFC-XBAR §5 stage P2 · CONTRACT-XBAR-P1 (CLOSED, ledger X-R1)."
tags: [contract, xbar]
timestamp: 2026-06-08T00:18:32Z
resource: shannon-prime-lattice/papers/CONTRACT-XBAR-P2-pseudo-token.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# CONTRACT XBAR-P2 — Pseudo-token injection (the deployable mechanism, and the stall fix)

**Parent:** RFC-XBAR §5 stage P2 · CONTRACT-XBAR-P1 (CLOSED, ledger X-R1). **Status:** P2.a DRAFT (spec'd 2026-06-08).
**One line:** move the injection point from the KV cache (P1's blunt instrument) to the **residual entry** — overwrite the embedding-level vector at the target steps and let the real forward mint every layer's K/V natively. This is the mechanism a trained adapter (P2.b) will drive, and the predicted fix for the dragon-stall attractor.

## 1. Why the entry point matters (the gravity-well theory, falsifiable)

P1's 6-row KV transplant is **static**: the same frozen rows attended at every decode step — a self-reinforcing attractor when the payload is dense (operator's "gravity well"; measured as 3/15 dragon trials at 9.4% distinct-token ratio, low-PPL *because* repetitive). An embedding-level seed is **reprocessed contextually**: the forward mints position- and layer-varying KV from it, the same way it does for real tokens. Prediction, stated before running: **dragon incorporation persists AND distinct% recovers above the degeneracy line.** If it doesn't, the stall is not an artifact of KV-staticness and P2.b's adapter has a harder job than assumed.

## 2. Architecture wrinkle on the record (AltUp/PLE)

gemma4 gathers `per_layer_token_embd` **by token id** at every step. A pseudo-token has no id, so P2.a injects the **main residual stream only** — the PLE lane keeps carrying the host token's per-layer embedding. Stated up front: if steering comes out weaker than P1's, the AltUp side-lane is the first suspect, and a deployment adapter on AltUp models needs a PLE strategy (nearest-token id, or a second adapter head). Measured, not assumed.

## 3. Harness (engine, per-step path, same discipline as P1)

- `SP_XBAR_EMB_CAPTURE=<file>` — at steps `ROW..ROW+NROWS-1` of ingest, dump the post-embed-scale entry vector `x` (E f32 each, appended; XBE1 header). Capturing from a **donor run** yields artifact-native, correctly-scaled entry vectors — no bf16/quant mismatch.
- `SP_XBAR_EMB=<file>` — at the same steps, overwrite `x` with the payload rows (H2D before PLE/layers).
- Banner getenv-echo; graph declines; payload row/n_rows/E validated.
- α-blends built host-side from captured payloads: `x_mix = α·x_donor + (1−α)·x_neutral`.

## 4. Protocol & gates (P2.a)

Prompts p1 (quiet room) + p5 (detective), concepts tel + drg, donors = the P1.c donor prompts; inject steps 9..14.

| Gate | Criterion |
|---|---|
| **G0E_NULL** | capture the neutral run's own entry vectors, re-inject them → bit-identical to B0 |
| **G1E_STEER** | α=1.0: lexical incorporation + own-family rank movement comparable to P1 Arm A on the same prompt/concept (parity band: best-rank within ~1 order) — KV minted natively must steer at least as cleanly as transplanted KV |
| **G2E_DOSE** | α=0.5 sits between B0 and α=1.0 on own-family ranks (embedding-space dose-response — the adapter's control knob) |
| **G3E_RECOVERY** | the falsification gate: dragon trials' distinct% recovers above 25% (P1 stalls: 9.4%) while incorporation persists |

Receipts: `_xbar\p2\`. No training in P2.a; P2.b (the learned adapter) is gated on these results.

---

## 5. P2.a RUN RECORD — 2026-06-08 (11 runs; mechanism PROVEN, gravity-well theory PARTIALLY falsified)

Engine: `SP_XBAR_EMB_CAPTURE` / `SP_XBAR_EMB` (XBE1 payloads, entry vectors captured artifact-native from donor ingest — zero scale mismatch by construction). Receipts `_xbar\p2\runs.log`.

| Gate | Verdict | Numbers |
|---|---|---|
| **G0E_NULL** | **PASS** | self-captured entry vectors re-injected → bit-identical to B0 |
| **G1E_STEER** | **PASS 3/4 on rank parity, 4/4 on incorporation** | α=1.0: p1_tel **214→1** (beats Arm A's →6) with fully coherent narration; p1_drg 1472→**2**; p5_drg 1402→**1** with full scene (*"The dragon's roar echoed through the room, causing the desk to shake violently"*); p5_tel rank 46 vs Arm A's 2 (1.4 orders short — the one parity miss) yet produced the campaign's most striking output: ***"Hello?" he asked… "This is the police. We need to speak with"* — the detective answered the phone in dialogue**, which the family-token detector cannot see (metric blind spot, noted) |
| **G2E_DOSE** | **PASS** | α=0.5 sits between B0 and α=1.0 on every own-family rank (tel 10614→222; drg 18931→45) — embedding-space dose control confirmed. Honest attachment: both α=0.5 continuations degenerate to empties within ~6 tokens — **linear blends fall off the embedding manifold**; the inter-token space is thin |
| **G3E_RECOVERY** | **PARTIAL 1/2 — theory partially falsified** | p5_drg recovers decisively (29.7% distinct vs P1's 9.4%, coherent scene). p1_drg does NOT (15.6%) — and degenerates into a **new attractor** (looping the "Continue this story:" template echo), different from P1's newline collapse. The stall is therefore **not purely KV-staticness**. Prime suspect, as pre-registered in §2: the PLE/AltUp side-lane still carries the *neutral* tokens' per-layer embeddings while the main stream carries dragon — a per-layer semantic contradiction the model resolves by looping |

**Mechanism findings, banked:** (1) α=1.0 entry injection is a *ghost prompt* — the model integrates the injected vectors as if they were real tokens (natively-minted KV everywhere), and steers as strongly as or stronger than the KV transplant; (2) the deployable adapter's true job, sharpened by G2E + G3E: output vectors **on the embedding manifold** (not linear blends), and on AltUp models supply a **PLE strategy** (nearest-token id or a second adapter head). These two constraints ARE the P2.b spec.

**P2.a CLOSED.** P2.b (learned adapter, training) is a compute project gated on an extracted dataset; its loss targets the P1 dose-response curve + the two constraints above.

> **FORMAL CORRECTION — 2026-06-09 consolidation pass (no silent revision; the
> banked finding above is amended, not erased).** The §5 "prime suspect" for the
> p1 dragon stall — the PLE/AltUp side-lane carrying the neutral tokens' per-layer
> embeddings — is **falsified by architecture ground truth**: the dense 12B has
> **PL=0, no PLE/AltUp lane at all** (STATE §5.12, llama.cpp reference read; the
> engine guards every PLE call behind `if (PL)`, and our B1 artifact runs PL=0).
> §2's wrinkle statement was written from the E-series geometry and does not apply
> to the deployment target. Replacement hypotheses, both testable and neither yet
> proven: (a) **context contradiction** — the ghost prompt's rows 9–14 say
> "dragon" while the surviving rows 15+ still narrate the quiet room; (b)
> **baseline-attractor amplification** — p1's own B0 already exhibits the
> "Continue this story:" echo loop that the stalled trial collapses into, while
> p5's B0 does not; the stall follows the prompt's pre-existing attractor.
> Consequences inherited by P2.b: the `L_PLE` loss term and second adapter head
> are DROPPED for the 12B target (one-line note kept for future E-series
> deployments, which do carry PLE); the stall is tracked empirically via a
> **distinct% stall-rate metric in adapter training/selection** since no clean
> mechanistic account survives.
