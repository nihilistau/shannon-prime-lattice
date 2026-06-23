---
type: design
title: "Cola DLM → the Shannon-Prime stack: what transfers, what's a train-time bet, what's aspirational"
description: "Receipts-first mapping of Unified-Cola (block-causal continuous-latent diffusion LM) onto PPT/ARM/LAT/XBAR/NIGHTSHIFT. The gold is that block-causal attention EXPLAINS our prefix-KV refutation; the honest correction is that block-causal is a train-time property, not an inference-time mask flip."
resource: https://zhao-yian.github.io/Unified-Cola/blog/2026/unified-cola-en/
tags: [cola, diffusion-lm, block-causal, latent-diffusion, flow-matching, prefix-kv, diffusion-judge, north-star, boundary-thesis]
timestamp: 2026-06-24T00:00:00Z
sp_status: DESIGN
sp_gate: none
sp_commit: TBD
sp_repro: "n/a (design doc) — falsifiable experiments E1-E4 enumerated in body, each default-off null-floor"
---

# Cola DLM → the Shannon-Prime stack

**One line:** Cola is a strong **north-star** for a *future* SP block-causal continuous-latent diffusion core — it would make our convicted prefix-KV lever *exact* and dodge the 262K-vocab softmax that bit us tonight — but it is a **model/training bet, not a `cuda_forward.cu` edit on the model we have.** The ~2x diffusion-judge speedup we shipped this session (scratch-reuse x async) is real and lives on the current bidirectional model; Cola is the bigger, separate bet stacked on top, paid for in training, not inference.

> Receipts-first scope: this doc separates (A) what is **verified** against our own measurements, (B) what is a **train-time property** we can only get by training, and (C) what is **aspirational**. Gemini's mapping is a useful skeleton but over-literal in two of three places; the corrections are called out inline. Source read 2026-06-24 from the Unified-Cola blog (`resource` above); the underlying arXiv preprint ID is to be confirmed before any external citation.

## 1. What Cola actually is (verified from the source)

Three pillars, all genuinely in the paper:

1. **Block-causal MMDiT.** Text is generated in **blocks** (paper uses block size B=16 — the same order as our diffusion-judge canvas). Attention is **causal *across* blocks, bidirectional *within* a block.** The mask is deliberately structured so the answer block cannot leak backward into the condition — "attention-mask-as-task-semantics."
2. **Text VAE → continuous latent.** Tokens are encoded into a *continuous* latent space; diffusion runs in that latent, **not** over the discrete vocabulary. The giant final-vocab softmax is avoided in the diffusion loop.
3. **Rectified-flow / flow-matching.** Velocity-prediction with straight-line trajectories, which cuts the number of sampling/training steps versus score-based DDPM.

These are real and mutually reinforcing. The question is which of the three maps onto our discrete, exact-integer substrate — and at what cost.

## 2. THE GOLD (verified): block-causal EXPLAINS our prefix-KV refutation

This is the one place Cola pays off immediately as *understanding*, and it is a vindication, not a new idea.

This session's `SP_DG_PREFIXKV` fast path was convicted: we measured that the prompt's K/V is **not canvas-invariant** — `max|fresh - cached prompt K/V| = 6.9e-4` on a matched needle (flips low-confidence argmax) and **NaN / uniform collapse** on a foreign one. The premise of prefix-KV (cache the prompt K/V once, reuse it across denoise steps) was **refuted empirically** (see the N6 prefix-KV record in `memory/` and `STATUS-MAP`). We crash-fixed the path (a wild host read from uninitialised MoE routing tables, `calloc` fix, engine `5276662`) precisely so the premise could be *measured* — and it fails.

Cola tells us **why**, exactly: diffusion-gemma's attention is **bidirectional** over `[prompt | canvas]`, so the prompt attends *forward* into the **noisy, changing** canvas. Therefore the prompt's K/V shifts every denoise step — by construction. Cola's block-causal mask (causal across blocks, bidirectional within) makes the condition's K/V **independent of the answer block** → prompt K/V becomes canvas-invariant → **prefix-KV becomes exact and free.** Our lever was not *wrong*; it was *unreachable on a bidirectionally-trained model.*

### The honest correction to "just flip the mask in cuda_forward.cu"

Block-causal is a **train-time property the weights are fit to.** Cola is *pretrained from scratch* under block-causal masks. diffusion-gemma was trained bidirectional — our own 6.9e-4 / NaN measurement is the proof the prompt is *meant* to see the canvas. Forcing a causal mask at **inference** feeds the network an attention pattern it never learned → degraded or garbage output, not a free speedup. So:

- **Refuted as a tonight-edit:** there is no inference-only mask flip that yields lossless prefix-KV on the current model. (Falsifiable — see E2.)
- **Valid as a model bet:** a block-causal *finetune* (or a from-scratch SP block-causal latent-diffusion core) makes prefix-KV exact. Cost = training, not a kernel patch. (See E4.)

This retires the prefix-KV question *correctly*: stop trying to cache invariants that the bidirectional model does not have; either eat the recompute (current `SP_DG_WCACHE` / sealed N5c path) or change the model.

## 3. The genuinely transferable kernel: diffuse in a compressed latent, avoid the vocab softmax

The real, portable lesson under the Text-VAE pillar is: **keep the diffusion in a compressed continuous latent and never touch the 262K-token vocabulary softmax inside the loop.**

The poetry is that **tonight's bug was literally a vocab-space softmax over-read** — `dg_k_softmax_rows` over `V = 262144` (`dg_self_cond`), a canvas-length mismatch that read uninitialised memory. Cola's entire point is to *not be there*: diffuse in latent, decode to vocab once at the end. A latent-diffusion core would have made that whole class of bug structurally impossible.

We are unusually well-positioned to take this kernel, because **we already own an exact-integer latent substrate**: the dual-prime negacyclic CRT-NTT ring (`core/ntt_crt` + `core/poly_ring`, frozen primes q1=1073738753 q2=1073732609, `O_K = Z[(1+sqrt(-163))/2]`). That is our "continuous latent" analog — except exact and auditable rather than float. The mapping that is *real*:

- **Cola's Text VAE latent  ~=  our O_K latent + the single latent entry point** `gemma4_kv_inject_seq` (text-via-seam == prefill, bit-identical — already GREEN in `CONTRACT-CHAT-FULLSTACK`). We already inject/score/replay in a latent the model consumes; we do not have a *diffusion* over it.
- **Cola's "avoid the vocab softmax"  ~=  our XBAR memory already operating on C2 signatures / Ring-3 superpositions, not tokens.** The token-free receipted-memory thesis and Cola's latent-diffusion thesis are the same instinct from two directions.

## 4. The PPT/ARM/LAT/XBAR/NIGHTSHIFT mapping — honest about loose vs real

Gemini's 1:1 acronym mapping is an elegant *metaphor*; do not take it literally. Where it is loose, it is a **label collision**, not an architecture match:

| Cola piece | Gemini's mapping | Honest verdict |
|---|---|---|
| Block-causal DiT mask | "prefix-KV salvation via mask change" | **Real insight, wrong mechanism.** Explains the refutation (§2); but it is train-time, not an inference mask flip. |
| Text VAE (continuous latent) | PPT / XBAR / LAT / ARM all at once | **Partly real.** The transferable kernel (diffuse-in-latent, skip vocab softmax) maps onto our O_K ring + `gemma4_kv_inject_seq` (§3). The 1:1-to-every-acronym part is a stretch. |
| Cola's autoregressive text decoder | "= our ARM" | **Label collision.** Our **ARM is the two-ring KV episodic memory** (Rademacher recall router + Ring-2 store), not an AR decoder. Same three letters, different organ. |
| Flow matching | "= NIGHTSHIFT" | **Aspirational** (§5). |

The thing to carry forward from PPT/ARM/LAT/XBAR is not a renaming — it is that our substrate *already* satisfies two of Cola's hard requirements (an exact latent we inject into; token-free memory operations). What we lack is a *diffusion process defined over that latent*. That gap is the whole bet.

## 5. Flow-matching → NIGHTSHIFT: aspirational, gated on adopting a latent core

Rectified-flow's straight-line trajectories really do cut sampling/training steps — solid. But our **NIGHTSHIFT is an offline curator / causal-ablation-admit / consolidation loop** (model-call `ep.secret` extractor → teacher-forced knockout TAU=-8 → MEM-OKF emit), not a flow-matching trainer. "Flow matching just updates the latent vector field" only becomes *true* once a latent-diffusion core exists to update. Direction valid, specifics premature — do not wire flow-matching into NIGHTSHIFT before E3/E4 land.

## 6. Falsifiable next steps (cheap-first, each default-off = null floor)

Ordered by cost. Each is a real SP gate, not a vibe.

- **E1 — Read the reference mask (FREE, do first).** Read the reference diffusion-gemma attention mask in the reference impl: is `[prompt | canvas]` attention bidirectional, and is prompt<->canvas coupling intentional? This is already the open N6 adjudication question. If bidirectional is confirmed by the reference, prefix-KV *fundamentally* requires a block-causal model and the lever is RETIRED on the current weights. Gate: a documented file:line citation from the reference, no code.
- **E2 — Inference-only block-causal mask probe (cheap, EXPECTED to degrade).** Apply a block-causal mask to diffusion-gemma at inference behind `SP_DG_BLOCKCAUSAL` (default-off = byte-identical null floor). Measure PPL + recall delta vs the bidirectional baseline. The PREDICTION is degradation; a clean degradation is positive evidence that block-causal is a train-time property (and quantifies how far off-distribution it is). A surprise non-degradation would be a major, bankable finding. Falsifiable either way.
- **E3 — O_K-latent diffusion feasibility prototype (medium).** Scope whether our exact-integer O_K ring can host a small diffusion/flow process (a toy denoiser over injected latents) that decodes through `gemma4_kv_inject_seq` without the vocab softmax. Goal: a yes/no on "can we diffuse in our own latent at all," not performance.
- **E4 — Block-causal finetune bet (BIG, deferred).** The real unlock: LoRA / continued-pretrain diffusion-gemma under block-causal masks so the condition's K/V is canvas-invariant by training, making prefix-KV exact. This is the legitimate route to the speedup the refuted fast path was reaching for. Cost: a training run on cloud (RunPod bake lane). Deferred until E1/E2 justify it.

## 7. Boundary thesis + honest status

- **Status:** DESIGN / north-star. Nothing here is gated GREEN; the only *measured* claim is §2's, and it is a measured **negative** (prefix-KV refuted) that Cola now explains.
- **Boundary thesis intact:** O_K wins on **exact arithmetic** (the container). Cola's contribution is orthogonal — it is about the **process** (block-causal latent diffusion), not the container. The two compose: a future SP block-causal latent-diffusion core would run *on* the exact-integer O_K substrate, getting auditability (ours) + free prefix-KV and no vocab-softmax (Cola's).
- **Do not let the north-star eat the shipped win.** The ~2x diffusion-judge speedup (scratch-reuse default-on + async byte-exact) is on the bidirectional model we actually run today and is real. Cola changes the *next* model, not this one.

## 8. Cross-links / receipts

- Source: Unified-Cola blog (`resource` above), fetched 2026-06-24. arXiv ID TBC before external citation.
- Prefix-KV refutation: `memory/project_n6_prefixkv.md`, `papers/STATUS-MAP-2026-06-21.md`, engine crash-fix `5276662`.
- Latent entry point + byte-exact chat: `papers/CONTRACT-CHAT-FULLSTACK.md`.
- Exact latent substrate: `papers/CONTRACT-BYTEEXACT-forward.md`, math-core `core/ntt_crt` + `core/poly_ring`.
- This session's perf win (the thing Cola does NOT replace): `papers/DESIGN-diffusion-lane.md` + the perf synthesis carried in engine and memory.
