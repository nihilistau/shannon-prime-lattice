# CONTRACT XBAR-P2b — The span-compression adapter (the scalpel, trained)

**Parent:** CONTRACT-XBAR-P2 (P2.a CLOSED + the 2026-06-09 PLE correction) · RFC-XBAR v1 §5.
**Status:** SPEC (consolidated 2026-06-09, KnackAU + Gemini + Claude). The first *trained* component of the XBAR lane.
**One line:** train a small frozen-LM adapter that maps an n-token span's embeddings to **k < n on-manifold pseudo-tokens** that steer the frozen 12B identically to the full span — learned semantic compression. This is simultaneously the deployable injector (P2's exit) and **Memo's compaction organ** (XBAR-C2's core): P2.b and the curator converge here by design.

---

## 0. What changed in consolidation (vs the first brainstorm draft)

1. **The dataset is NOT `[concept token → its minted entry vector]`** — for a real token that map is the embedding row × √E, an identity we already own. The learnable problem is mapping *non-token* sources onto the manifold. Three sources, one recipe:
   - **(S1) multi-token span → k pseudo-tokens** (THIS contract): self-supervised, unlimited data from any corpus, and exactly the ring-compaction primitive Memo needs.
   - (S2) ring/Spinor episodic state → entry vectors (Memo read-side; after P3).
   - (S3) audio latents → entry vectors (XBAR-M, voxtral source; same recipe).
2. **PLE machinery dropped** for the 12B target (PL=0 — see the P2 contract's formal correction). E-series deployments would re-add a PLE head; out of scope here.
3. **Memory honesty:** freezing the 12B avoids optimizer state for weights, but the backward pass still requires activations through 48 layers (or checkpointing). Cloud-only (RunPod/Colab A100-class; 24 GB bf16 weights + checkpointed activations fit). The 2060 is the *deployment* target, never the training target.
4. **Stall-rate is a first-class metric.** No surviving mechanistic theory for the dragon stall (PLE falsified) → adapter training/selection tracks distinct% on steered continuations, and the trained adapter must not be *worse* than raw entry injection on it.

## 1. Phase 0 — Inversion (existence proof + golden targets + manifold map)

Per-instance soft-prompt optimization on the frozen bf16 12B (cloud): for a sampled span (n=4–8 tokens) inside a context, optimize k free vectors `ê₁..ê_k` (k ∈ {1,2}) at the span's positions to minimize CE/KL against the teacher's continuation (the model's own output given the full span). Two regularization arms, A/B:

- **Arm F (free + soft-min manifold penalty):** `L_man = λ·softmin_topK(‖ê − E_v‖²)` (logsumexp over the K nearest embedding rows — the hard `min` has unstable gradients at Voronoi boundaries; normalize by the embedding-norm distribution).
- **Arm H (convex-hull parameterization):** `ê = Σ_j softmax(s)_j · E_{idx_j}` over the K nearest rows — on-manifold by construction. (The α=0.5 P2.a failure blended two *distant* tokens; local-neighborhood combinations are a different object. Whether the local patch is flat enough is exactly what this arm measures.)

Deliverables: per-span golden `ê*` sets, the achievable-steering ceiling (KL gap vs full span as f(k, n)), and the measured local manifold geometry (how far off-hull do Arm-F optima sit?). **Falsification stated up front:** if inversion cannot find ANY k=2 vector pair matching a 6-token span within tolerance, amortized compression at that ratio is dead and the contract re-scopes to k≈n alignment (S2/S3 only).

## 2. Phase 1 — The adapter (amortize the inversion)

Architecture: small (≤ ~50M params) — span-token embeddings → encoder (few transformer/MLP layers) → k output vectors, parameterized per the winning Phase-0 arm. Trained on (S1) pairs sampled from wikitext + general corpus; loss = teacher-KL on the continuation + the manifold term + a distinct%-degeneration penalty on sampled rollouts.

## 3. Phase 2 — Deployment gate (the part nobody else has)

The adapter's output IS an XBE1 payload — P2.a's `SP_XBAR_EMB` knob is the deployment interface, already built and G0E-proven. Export adapter (tiny, f32), mint payloads host-side, inject on the 2060 against the **B1 quantized artifact**.

| Gate | Criterion |
|---|---|
| **G-P2b-0 (inversion existence)** | Phase 0: ≥⅔ of sampled spans admit a k=2 inversion within the KL tolerance band (band pinned by telemetry on the first 50 spans — telemetry-then-pin) |
| **G-P2b-1 (compression fidelity)** | frozen 12B with `A(span)` at k=2 (n=6): continuation KL/PPL within the pinned band of the full-span teacher, on held-out text |
| **G-P2b-2 (content survival)** | NIAH-style: a fact inside the compressed span remains answerable downstream (the curator's recall currency) |
| **G-P2b-3 (cloud→silicon parity)** | adapter-minted XBE1 payloads on the 2060/B1 artifact reproduce cloud steering (rank telemetry + incorporation), G0E null re-run green — the artifact-quantization gap is measured, not assumed |
| **G-P2b-4 (stall regression)** | distinct% on steered continuations ≥ raw-entry-injection baseline (P2.a receipts); gold-instrument PPL of steered text stays in the healthy band (the P1 G2v2 instrument, re-used) |

## 3a. PHASE 0 RESULT — G-P2b-0 RUN RECORD (2026-06-09, RunPod A6000, 50 spans × 2 arms)

The inversion ran on the real gemma-4-12B (gold bucket, byte-verified `google/gemma-4-12B`) via the HF-mediated autonomous pod. k=2, n=6, ctx=64, cont=24, 300 steps/span. Receipts: `KnackAU/xbar-p2b-run` `results/{p0_F,p0_H}/receipts_*.json` + golden `.pt`/`.xbe1` per span. Metric: recovery = 1 − kl_final/kl_span_dropped (fraction of the span-removal gap the k vectors close; 1.0 = perfect, 0 = no better than deleting the span).

| Arm | median gap closed | spans beat-drop | spans ≥50% | dist-to-nearest-token (manifold) |
|---|---|---|---|---|
| **F** (free + soft-min λ=0.1) | **0.936** | 50/50 | 50/50 | **18.80** — far off-manifold |
| **H** (convex-hull of K=64 neighbors) | **0.635** | 49/50 | 43/50 | **0.77** — on-manifold by construction |

**G-P2b-0 verdict: PASS (existence confirmed, decisively).** Two vectors recover a 6-token span's continuation distribution on the real 12B — 50/50 spans for both arms beat outright deletion; the premise that **6→2 span compression is achievable is no longer a hypothesis.** The inversion ceiling is ~94% gap-closure.

**The Pareto tension this maps (the load-bearing finding).** Recovery and manifold-adherence trade off, hard:
- **Arm F** finds vectors that recover ~94% of the information — but they live ~18.8 units off-manifold (~24× farther from any real token than Arm H). These are the **P2.a α=0.5 degeneration risk made manifest**: optimization *found* high-KL-recovery vectors precisely by leaving the manifold (λ=0.1 was too weak to hold them). 
- **Arm H** stays on-manifold (0.77) but the constraint costs ~30 points of recovery (64% vs 94%).

**The DECISIVE open question — teacher-forced KL ≠ free-generation coherence.** Recovery here is measured on the *continuation distribution* (teacher-forced). P2.a proved off-manifold vectors can *degenerate at free generation* despite plausible local stats. So Arm F's 94% is a **ceiling on recoverable information, NOT a guarantee of deployable generation.** Whether the off-manifold F vectors actually *generate coherently* — or degenerate like α=0.5 — is testable NOW on the 2060: inject a golden `.xbe1` via `SP_XBAR_EMB` and read the continuation. **This single local test decides P2.b's operating point:** if F-vectors generate cleanly, we take the higher recovery; if they degenerate, the manifold constraint (Arm H, or a λ-sweep Pareto point near it) is mandatory. It is the bridge from G-P2b-0 (existence) to G-P2b-1/G-P2b-3 (deployable fidelity).

**Pinned follow-ups:** (a) the on-silicon generation-coherence test above (local, free, decisive); (b) a λ-sweep tracing the F Pareto front (cloud) once (a) says which end we want; (c) hull-entropy median 3.05 vs ln(64)=4.16 says Arm H concentrates on ~6–8 effective neighbors — the adapter's hull head can be narrow. Cost of the run: ~$0.50 (A6000, ~1.5 h across two launches).

### G-P2b-3a ON-SILICON GENERATION TEST — run record 2026-06-09 (B1 quantized 12B, 2060)

Picked the most off-manifold-exploiting F span (s12, kl_final **0.0135**, dist-to-token **16.7**) vs its on-manifold H twin (0.066, 0.69); reconstructed the exact 64-token wikitext context; injected k=2 golden vectors at rows 64–65 via `SP_XBAR_EMB`; greedy free-gen 48 tokens on the B1 artifact. Real span = `" of the sons died in infancy"`. Receipts `_xbar/parity/`.

| arm | distinct% | continuation |
|---|---|---|
| **B0 real span** (control) | **15%** | "He was the son of the emperor." × loop |
| H on-manifold | 27% | "757, the youngest, was still alive. He" → newline collapse |
| F off-manifold | 29% | "He was the son of the king of the 750s…" fluent, on-topic, looping |
| drop (no span) | 42% | most diverse, on-topic |

**Verdict: INCONCLUSIVE-but-encouraging — the catastrophic-collapse hypothesis is NOT supported.** The decisive observation is the *control*: B0, fed the **real tokens**, degenerates *hardest* (15%, tight loop). This is the P1 greedy-wikitext confound (base/it-model on raw prose without a chat template loops under greedy decode) — so "degeneration" cannot be the clean falsification signal here, because it is present with ground truth. Within that limit: F's first sentence is coherent and on-topic, and F's distinct-rate (29%) ≥ H (27%) ≥ B0 (15%). **The off-manifold vector does not degrade generation relative to the real span it replaces; the α=0.5 immediate-collapse mode did not occur.** It does NOT earn a clean G-P2b-3 PASS — a subtler off-manifold gap could be masked by the looping baseline. **Clean re-test (the real G-P2b-3): re-run the cloud inversion on chat-template / coherent-generation contexts (the P1.b regime, where B0 is fluent), then repeat this parity test — degeneration becomes a meaningful signal only when the baseline is coherent.** Operating-point lean from this evidence: off-manifold is *tolerated* (favor the higher-recovery F end), pending the coherent-regime confirmation.

### G-P2b-3b COHERENT RE-RUN + parity — NEGATIVE RESULT, and the reframe (2026-06-09)

The coherent re-run executed (30 spans × 2 arms, model's-own-generation contexts; receipts `results_coherent/`). The kl-dropped-weighted Phase-0 numbers **confirmed the Pareto a second time**: on informative spans (kl_dropped ≥ 0.05), **Arm F 96.1% gap-closed at 17.0 off-manifold; Arm H 73.3% at 0.87 on-manifold** (H up from 64% on wikitext — the hull closes more on native data; F still leads, 8/3 paired). Existence + Pareto are now proven in two regimes.

**But the parity test it was built to enable FAILED — honest negative.** The `--coherent` seeds ("Write a short story about…") put the model in markdown-document mode; greedy 90-token generation degenerated into header-tag + newline loops (token 258882 = empty string, repeated) **even on the gold bf16 model**. The auto-selected "most-informative" span (s6, kl_dropped 5.4) was a `'\n\n'` newline span — a *loop-onset* artifact, not a semantic span. All four parity arms (B0/H/F/drop) emit the same `\n\n<h2><strong>` garbage. No fluent baseline ⇒ the test is invalid for its purpose.

**The real finding (third greedy baseline to degenerate — raw-wiki B0, P2.a-wiki, story-instruction): greedy decoding on this it-tuned model loops regardless of regime. Free-generation coherence is NOT a usable gate on this model+sampler.** The parity test was an attempt to shortcut the operating-point decision through generation; the shortcut does not work here.

**Reframe (the correct conclusion, not a consolation).** The operating point is NOT lockable by a parity test on a model whose every greedy baseline loops. It is a **P2.b training-time selection**: train with the manifold-penalty λ as a swept hyperparameter (the planned λ-sweep), and select the point with a generation metric robust to greedy looping — temperature-sampled generation, or gold-PPL + distinct% on a *validated-coherent* eval set, or the deployed curator's recall metric. Phase 0 (existence + Pareto, twice) is the durable result and is **CLOSED**; G-P2b-3 folds into P2.b training as the λ-selection gate rather than a standalone parity test. Cost of the coherent run: ~$0.40.

## 3c. The admissible P2.b training framework (agreed 2026-06-09 after the G-P2b-3 reframe)

Phase 0 closed existence + the Pareto; the operating point is selected **during training**, not pre-locked. The cloud loop sweeps the manifold penalty and selects with a metric robust to the greedy-looping instrument that failed G-P2b-3.

**Loss (multi-objective, per the Phase-0 arms):**
`L = L_KL(student ‖ teacher) + λ · L_manifold`, where `L_manifold` = the soft-min logsumexp over the nearest embedding rows (the Phase-0-stable Arm-F penalty; Arm-H's hull parameterization is the λ→∞ limit). Sweep **λ on a log scale** to export a spectrum of adapters from aggressive/abstract (Arm-F-like, ~94–96% recovery, off-manifold) to constrained (Arm-H-like, ~73%, on-manifold).

**Selection metrics (greedy-coherence is dead; these replace it):**
1. **PRIMARY — the Curator's Recall Invariant.** The adapter *is* Memo's compaction organ, so the deployed-task metric is the gate: compress an episode to each λ-density, then measure whether **Exec retrieves facts from the compressed episode** (NIAH/QA-over-episode). This is a *retrieval* signal, not a free-generation one — it structurally sidesteps the greedy-loop confound that broke G-P2b-3. The operating point is the λ that maximizes recall-at-budget on held-out episodes.
2. **SECONDARY — gold-PPL deflection via temperature-sampled rollouts.** PPL of validation continuations under the gold instrument, sampled (T>0) to break greedy loops, multi-seed for variance control. Cross-check, not the primary gate (carries sampling variance + a residual coherence-judgment problem).

**Why recall-primary is the Shannon-Prime choice:** it measures what the system is *for* (does the compressed memory still answer questions), it needs no fluent-baseline (the three-times-failed requirement), and it folds the old G-P2b-3 "operating point" question into a number with a receipt.

## 3d. THE RECALL-INVARIANT DECIDER — run record 2026-06-09 (local, B1, no cloud; the operating-point call the reframe deferred)

The §3c reframe made the Curator's Recall Invariant the PRIMARY selection metric and retired generation-parity. Rather than wait for P2.b training to apply it, this runs the recall invariant **directly on the Phase-0 golden vectors we already hold** — deciding the F-vs-H operating point with assets in hand, zero cloud spend, no P3.

**Design (the key discipline): the metric must be OUT-OF-OBJECTIVE.** Phase-0 inversion optimized the k=2 vectors to match the *continuation* distribution, so re-measuring continuation-KL just re-derives the training target (F wins by construction). The recall invariant instead probes **span-content readback**: teacher-force the span's own 6 tokens after the compressed prefix and score their NLL — "does the compressed memory predict its own contents." This is the G-P2b-2 content-survival gate at span granularity. Harness: existing `SP_XBAR_EMB` (inject k=2 at rows 64–65) **composes with** `SP_G4_SCORE` (teacher-force NLL from pos 66) in the same `gemma4_decode_cuda` prefill (`cuda_forward.cu:2043` entry-overwrite + `:1710` score lane — verified independent overlays; **no engine change**). Span s12 = `" of the sons died in infancy"`; all three injected conditions position-matched (span at 66–71, only rows 64–65 differ). Receipts `_xbar/recall/`.

| condition | rows 64–65 | span PPL | per-tok NLL |
|---|---|---|---|
| CTX floor | (none — span at 64) | 4.45 | 1.49 |
| **F off-manifold** (golden, dist 16.7) | F pseudo ×2 | **8.67** | **2.16** |
| FILLER null | token-0 ×2 (noise) | 9.50 | 2.25 |
| **H on-manifold** (golden, hull, dist 0.69) | H pseudo ×2 | **19.03** | **2.95** |

**VERDICT — operating point = F (off-manifold / high-recovery); the convex-hull manifold constraint is NOT recall-safe.** On the position-matched triple: **F (8.67) beats the noise-filler null (9.50); H (19.03) is 2× WORSE than noise.** The off-manifold F vectors preserve recoverable span content; the on-manifold H vectors *actively destroy* readback — the model predicts the span's *neighbor* tokens (the hull is built from the 64 nearest embedding rows) confidently and wrongly. This is RFC §4's "semantically-wrong-but-valid" failure **measured**: on-manifold-by-construction produces confident-wrong recall. The recall axis (the correct one per §3c) sharpens Phase-0's continuation-KL gap (F 94% vs H 73%) into a *much* harder recall gap, and reverses the naive "on-manifold is safer" intuition.

**Consequence for P2.b training (§3c loss):** the manifold penalty `λ·L_manifold` must be a **light regularizer toward the F end**, NOT pushed to the Arm-H hull limit — high λ buys geometric tidiness at the cost of recall. Sweep λ low; select by the recall invariant, expecting the optimum near the free/off-manifold end.

**Honest caveats (attached, per methodology):** (1) **n=1 span.** s12 only — the obvious second datapoint (s6, parity_co) is the degenerate empty-string-loop span from the failed G-P2b-3b coherent run (`span_ids` = `…258882×4`), invalid as content. Confirmation needs K more *valid* spans' goldens pulled from `KnackAU/xbar-p2b-run` (cheap) before the operating point is locked into the loss. (2) The CTX floor (4.45) ≪ all injected conditions — the span is highly context-predictable, so the absolute recall signal is small; the *valid* comparison is the position-matched F/H/FILLER triple, where the F<FILLER≪H ordering is large and one-directional. (3) span-token-NLL is a strong content-preservation proxy; a query/cloze recall harness is cleaner but needs per-span query design — a P2.b-training-time upgrade. The DIRECTION (favor F, hull is recall-hostile) is decisive; the magnitude wants n>1.

## 4. Compute plan & receipts

RunPod/Colab A100-class, bf16 HF checkpoint from the proven bucket (the 4.68-gold weights — the ONLY trusted source, STATE doctrine). All cloud runs export: config echo (banner = printed env/args), dataset manifest hashes, loss curves, golden-pair archives. Receipts land in `_xbar/p2b/` + the contract run-record; ledger row only on the agreed gates green. **Ops upgrades banked from the Phase-0 runs:** the pod bootstrap must **periodic-upload its log** (RunPod community API returns no telemetry — flying blind otherwise; the operator had to pull the console log manually); validate the corpus is *coherent before* inverting (greedy 90-tok generation degenerates — use continue-narrative seeds + shorter gen + sampling if a fluent baseline is ever needed).

## 5. Convergence note (why this is the home stretch's keystone)

P2.b's adapter is: the deployable injector (XBAR-P exit) · Memo's compaction organ (XBAR-C2: ring consolidation = compress episodic spans to pseudo-token state under the same fidelity gates) · the modality template (XBAR-M swaps the source encoder) · NIGHTSHIFT's worker (consolidation pass = adapter applied offline under promote-on-accept). One trained component, four lanes served. The open Memo-body decision is logged in RFC v1: with the adapter as the organ, Memo v1 may be *adapter + tiny ring-block encoder* rather than the 0.5B M.0 stub.
