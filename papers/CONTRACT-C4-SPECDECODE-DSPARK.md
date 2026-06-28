---
type: contract
title: "CONTRACT-C4-SPECDECODE — a DSpark draft source onto the proven MTP/T8 loop"
description: "C4 addendum. The verify/rollback machinery (spec.rs, sp_session_clone/rewind, Theorem T8) is already PROVEN and byte-exact; the binding constraint is draft acceptance, not the loop. This contract imports DSpark's actual contributions (hybrid parallel→sequential draft head + a learned acceptance-length scheduler + the accept-length eval harness), adds byte-exact cross-island speculation as the novel win, and kills the Gemini Poncelet/KSTE grafts with a pre-registered falsification."
tags: [contract, c4, mtp, speculative-decoding, dspark, t8, byte-exact, draft-model, scheduler]
timestamp: 2026-06-28T00:00:00Z
resource: shannon-prime-lattice/papers/CONTRACT-C4-SPECDECODE-DSPARK.md
sp_status: DESIGN
sp_gate: G-SPEC-ACCEPT-12B
sp_commit: TBD
sp_repro: "stages + gates in §7; kill-test in §5.1"
---

# CONTRACT-C4-SPECDECODE — a DSpark draft source onto the proven MTP/T8 loop

> **Parent:** [RFC-001](PPT-LAT-RFC-001-Universal-Discrete-Architecture.md) §5 (MTP), [CONTRACT-C4-C5-C6-decisions](CONTRACT-C4-C5-C6-decisions.md), Theorem **T8** in [PPT-LAT-Theory](PPT-LAT-Theory.md) §11.5.
> **Frame:** this is **not a new subsystem**. It is the *unparking of C4* (P2 lead, substrate now proven) plus the one missing ingredient. Anti-rebuild pre-flight is binding (`okf_mem lookup mtp`, `grep spec_step`).

## 0. The one line

The draft→verify→commit loop is **built and proven byte-exact**. The verify is byte-exact token-id equality (T8), not a probability or a geometric oracle. The **only** thing missing for a real speedup is a **high-acceptance draft source**. DSpark is a recipe for exactly that. Everything else in the June Gemini thread was decoration around this single gap.

## 1. PROVEN — do NOT rebuild (cite, reuse, wire)

| Piece | Where | Status |
|---|---|---|
| `spec_step(target, draft, …, k)` — draft K by argmax → target verifies sequentially by **argmax equality** (no softmax, no prob ratio) → rewind on reject | engine `tools/sp_daemon/src/spec.rs` | **[WIRED]** callable; *not* called from `/v1/chat` |
| `sp_session_clone` (deep-copy hist+KV, f32 + Spinor modes) / `sp_session_rewind` (O(1) watermark decrement) / atomic `cancel_flag` | `sp_l1.h` 203–206; `core/session/sp_session.c` 773–824 | **[PROVEN]** — ABI frozen at `lat-phase2-contract-frozen` |
| **T8** — MTP draft = the next-K Poncelet orbit in $R_q$; batched draft+verify **bit-identical** to K sequential forwards on the accepted prefix; **T8.1 no ghost contamination** after rollback ($\mathbb{Z}_q$ rewind is clean, not "subtly wrong") | Theory §11.5 | **[PROVEN-theory]** |
| C4 measured loop: `SP_MTP=1`, Qwen3-0.6B-f16, prompt-lookup NG=2, **2.67× fewer forward passes**, `mean_accept=1.78/8`, **`bit_identical_to_greedy=1`** at K=8 | engine `b602ddf`, `tests/sp_toks.c` | **[PROVEN]** machinery; rollback-lossless gate met |
| Byte-exact forward substrate (the reason draft and verify agree to the bit) | `SP_BYTEEXACT`, G-BYTEEXACT-FORWARD-12B (off 4.6665 / on 4.6569) | **[PROVEN]** |
| Draft model load path (`--draft-model`/`--draft-tokenizer`, creates a draft session) | `daemon.rs` 137–150 | **[WIRED]** singleton, never cloned per-turn / never used |

**The honest negative that defines the work:** the same C4 record shows that on real prose/code, prompt-lookup drafting nets **0.87× — a small loss.** The verify machinery is sound; the *draft source* is too weak. That is the contract.

## 2. The binding constraint — acceptance, not the loop

Speedup ≈ (mean accepted tokens per verify) ÷ (draft cost ratio). Our verify is free of numerical slack (T8.1), so acceptance is bounded purely by **how well the draft predicts the target's argmax**. Levers, in order of leverage:

1. a trained draft head that actually models the target (DSpark) — **the lead**;
2. an adaptive K so we stop drafting before acceptance craters (DSpark scheduler);
3. the qwen35moe NextN block (field `q36_nextn_predict_layers` exists; the forward is a Stage-2b/2c **stub** — a separate build, not on this critical path).

## 3. What we import from DSpark (the real, sound contributions)

### 3.1 Hybrid parallel→sequential draft head — `C4-SPEC-DRAFT`
DFlash (which we already lived) drafts the whole block in parallel; acceptance craters deep in the block because token *t+3* is blind to the realized *t+1*. Eagle3 drafts sequentially and gives up throughput. **DSpark's actual idea:** a heavy **parallel** pass for throughput, then a lightweight **sequential** pass that re-conditions each position on its realized predecessors. We adopt that head shape verbatim.

Critical clarity Gemini blurred: **the draft is approximate-and-fast; only the verify is exact.** Do not try to make the draft itself geometrically/integer-exact — that is wasted effort. The draft is an ordinary small (float or quantized) model trained on the target's outputs; its job is acceptance rate, nothing more. It feeds the proven exact `spec_step`.

### 3.2 Learned acceptance-length scheduler — `C4-SPEC-SCHED` (L3 policy, not math-core)
The *only* legitimate role for a "confidence" signal here is **how many tokens to draft**, a pure throughput knob (our uploaded DSpark viz calls its objective "Compute Wasted"). Train a small head that predicts P(accept) per draft position; truncate K when the expected marginal accept × token-value drops below the draft+verify cost. **Reuse the B3-WC infrastructure** (InfoNCE, the learned `WcHead`/`wc_score` in `recall.rs`) — that is our proven learned-head stack; do not invent a new one. Placement: this is **orchestration policy → L3 daemon** (per RFC §8 "no math truth in L3" cuts both ways — no *policy* in math-core). Unify it later with the §2.3 System-1/System-2 crossover oracle (same load-aware predictor, two outputs).

### 3.3 The accept-length eval harness — `C4-SPEC-EVAL` (do this FIRST)
DeepSpec ships an eval that reports **mean accepted tokens / step** and wall-clock speedup over gsm8k / math500 / humaneval / mbpp / mt-bench / alpaca / arena-hard-v2. **Our C4 record has exactly one measured accept-length (1.78/8 on a 0.6B with prompt-lookup) and none on the 12B.** Stand up an equivalent harness in `shannon-prime-harness` against the live `spec_step` before building anything. No number, no claim.

## 4. The novel win — byte-exact cross-island speculation — `C4-SPEC-ISLAND`

Standard speculative decoding silently assumes draft and target share a numerical environment; cross-device float drift (edge draft / server verify, or even two GPU SKUs) causes **spurious rejections** that crater accept-length. Our forward is byte-exact on the dual-prime CRT-NTT $O_K$ substrate (G-BYTEEXACT), so **draft-on-island-A and verify-on-island-B produce bit-identical logits → zero acceptance loss from numerics.** This is something float speculative decoding structurally cannot do, it composes with Trick #1 (draft on island A, verify on B/C), and it generalizes off the phone to *any* heterogeneous fleet (dual-GPU, CPU+GPU, mesh peers). Ship residues, not tensors, on the verify hand-off (RFC §2.2 CRT bandwidth bypass).

**Implementation caveat (real, from the code):** `sp_session_clone` deliberately does **not** propagate the persistent `kvdecode_backend` (the resident CUDA cache is single-owned); a clone falls back to math-core reference decode (`sp_session.c` 792–799). So a cross-island draft/verify split needs an explicit decode-backend story per island — design it; don't assume clone carries it. The CRT-residue-beats-full-tensor bandwidth model is itself **[TARGET]** (RFC §10.2) — gate it.

## 5. What we REJECT, and why (the Gemini grafts)

### 5.1 The Poncelet/Euler "confidence oracle" — KILL, with a pre-registered falsification `G-PONCELET-CORR`
Gemini borrowed a **real** term — T8 already calls the K-step draft "the next K positions of the Poncelet orbit in $R_q$." The error is the bolted-on accept test: `rhs = x³+Ax+B mod q₁`, then Euler's criterion (Legendre symbol) as accept/reject. For any integer mod a prime, being a quadratic residue is a ~50/50 coin — exactly $(q_1-1)/2$ residues qualify — so the oracle is a fair coin uncorrelated with token correctness, and a *binary, non-monotone* one at that (so not even a graded confidence). The QR-of-$-163$-mod-$p$ test is real in our theory but classifies **prime splitting in $O_K$** (Theory §1.4), not tokens — that is the category error. And it is **unnecessary**: T8's accept test is byte-exact equality, already built and cheaper. A 50/50 truncation oracle would discard half of good speculation → it strictly *hurts*.
- **Kill-test (cheap, an afternoon):** draft ≈10k tokens; log the Euler-criterion verdict and the actual byte-exact accept/reject; compute correlation ρ. **Pre-registered prediction: ρ ≈ 0.** If so, the oracle is dead-on-arrival and is filed as an honest negative — same shelf as the nine refuted B3 recall signals.

### 5.2 KSTE as the sequential Markov / draft head — category error
KSTE is an **order-invariant, lossy structural signature** (Frobenius-invariant; magnitude→depth; sign→B/C swap), and STATE §4 already **adversarially falsified KSTE as a recall router** (permuted decoys indistinguishable; the directional ±1 Rademacher rank-16 projection is the proven router instead). A draft head must *generate* the next-token distribution; KSTE is many-to-one and cannot be decoded back to a token. Keep KSTE for dedup/dominance only. (Possible residual role: a cheap structural *pre-filter* on a draft block before verify — but verify is already exact and cheap, so it only earns its place if measured.)

### 5.3 "38TB → 300GB via 120× Spinor compression" — conflation
The 38TB is DeepSpec's **target-feature cache** for *draft training*; the "120×" is *inference KV*, and is unmeasured hype — the proven numbers are **Spinor ~3.5×/f32 (lossy: ~6.5% argmax flips, NOT a bit-exact overlay)** and **Ring-2 effective-context 400–1190×** (C2.1). Worse, KSTE is lossy/order-invariant, so compressing the regression target through it deletes the very signal the draft head learns. The sound move is §6.

## 6. Training data — regenerate, don't cache — `C4-SPEC-DATA`
DeepSpec caches 38TB because re-running a float target is nondeterministic-enough and expensive. **Our target forward is byte-exact and deterministic** (G-BYTEEXACT), so target features are *reproducible on demand*: regenerate during draft training instead of caching, trading 38TB of storage for deterministic recompute — and getting **train/serve feature parity for free**, which a float pipeline can never guarantee. If a cache is still wanted for speed, store features **lossless** in OK_Q4/Spinor and *measure* the real ratio (expect single-digit–to–10×, not 120×).

## 7. Stages + gates

| Stage | Deliverable | Gate (pre-registered) | Repo |
|---|---|---|---|
| `C4-SPEC-WIRE` | call `spec_step` from `/v1/chat`; clone the draft session per turn; single-token fallback when no draft | **G-SPEC-WIRE** — served chat with draft == served chat without, **bit-identical tokens** (null-floor preserved), `SP_BYTEEXACT` on | engine daemon |
| `C4-SPEC-EVAL` | accept-length + speedup harness over the DeepSpec task set, on the live 12B | **G-SPEC-BASELINE-12B** — pin mean-accept/step + tok/s for prompt-lookup draft (the honest floor) | harness |
| `C4-SPEC-PONCELET` | the kill-test | **G-PONCELET-CORR** — ρ(Euler-verdict, byte-exact accept) ≈ 0 → file negative | harness |
| `C4-SPEC-DRAFT` | DSpark hybrid parallel→sequential draft head for gemma-4-12B, trained on regenerated target features | **G-SPEC-ACCEPT-12B** — mean-accept/step **> prompt-lookup baseline by ≥ X** AND end-to-end **tok/s > 1.0× single-token** at `SP_BYTEEXACT` parity | engine + harness |
| `C4-SPEC-SCHED` | learned acceptance-length scheduler (B3-WC infra), L3 policy | **G-SPEC-SCHED** — adaptive-K beats best fixed-K on tok/s at equal output; later unify with System-1/2 oracle | daemon |
| `C4-SPEC-ISLAND` | cross-island draft/verify (clone decode-backend story), CRT-residue hand-off | **G-SPEC-ISLAND** — edge-draft/server-verify tokens **bit-identical** to monolithic; residue-bytes < full-tensor bytes | system + daemon |

`X` (the accept-length lift bar) is set after G-SPEC-BASELINE-12B, not guessed.

## 8. Files to touch (and the ones to leave alone)
- **Touch:** `daemon/src/routes.rs` (wire spec_step + per-turn draft clone + multi-token stop/sampler handling), `daemon/src/spec.rs` (extend to scheduler hook), harness `tests/` (eval + kill-test), a new draft-train script in harness reading regenerated features.
- **Reuse as-is:** `spec.rs::spec_step`, `sp_session_clone/rewind`, `recall.rs WcHead` (for the scheduler), the byte-exact islands. **Do not** add an oracle to `math-core`. **Do not** re-implement the transaction/rollback — T8 + the watermark already own it.

## 9. Open questions
- Draft architecture for a 12B target: standalone small SP model vs gemma-4 NextN head vs Medusa-style heads on the resident model? (NextN forward is a stub today.)
- Does the hybrid sequential pass run on CPU/Hexagon while the parallel pass is on GPU (Trick #1 split), and does the clone decode-backend gap (§4) make that net-positive?
- Temperature > 0: the discretized-sampling accept contract (RFC §5 open question) — byte-exact accept under sampling needs a frozen RNG/quantized-sampling spec before spec-decode is correct off argmax.
