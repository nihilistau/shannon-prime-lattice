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

**n=1 (s12) read (SUPERSEDED in part — see the n=6 correction below):** on s12 alone, F 8.67 < FILLER 9.50 << H 19.03, which read as "F preserves recall, H is recall-hostile (2× worse than noise)." That second half was an **outlier**, walked back below.

### n=6 HARDENING — 5 more valid spans (2026-06-09, B1, detached; receipts `_xbar/recall_multi/`)

Before letting the operating point anchor P2.b's λ schedule, hardened to n>1: 5 clean content-bearing spans (kl_dropped 0.25–1.25 spread, newline/empty degenerates excluded), contexts reconstructed from the local wiki stream + **`span_ok` verified** against each receipt, goldens pulled fresh from `KnackAU/xbar-p2b-run` + header-restamped to the inject row, all conditions position-matched (FILLER/F/H, span readback NLL @66). Per-span span-readback PPL:

| span | kl_drop | FILLER (null) | F (off-manifold) | H (on-manifold) | F vs null | H vs null |
|---|---|---|---|---|---|---|
| s12 (prior) | 0.25 | 9.50 | **8.67** | 19.03 | F better | **H WORSE** |
| s0 | 1.25 | 130.87 | **72.21** | 128.90 | F better | ≈neutral |
| s9 | 0.54 | 401.19 | **154.51** | 333.93 | F better | H better |
| s17 | 1.22 | 135.74 | 97.26 | **96.86** | F better | H better |
| s23 | 0.93 | 630.05 | **163.81** | 377.70 | F better | H better |
| s43 | 0.50 | 28.59 | 12.47 | **8.52** | F better | H better |

**CORRECTED VERDICT (n=6) — lean F as the robust default; the manifold penalty stays an EMPIRICAL dial, NOT a hard lock. The n=1 "Arm H is recall-hostile" claim is RETRACTED (s12 was an outlier).**
- **F robustly preserves recall: 6/6 spans beat the noise-filler null**, with large margins on the informative spans (s9 155 vs 401, s23 164 vs 630). The F-favorable direction is solid.
- **H is NOT recall-hostile in general.** It beats or ties the filler null on **5/6** spans (only s12 had H worse than noise); the "2× worse than noise / confident-wrong neighbor prediction / RFC §4 measured" reading does **not** generalize and is withdrawn.
- **F vs H is mixed:** F wins 4/6 (incl. every high-information span), H wins 2/6 (s17 ≈ tie, s43). The recall edge favors F, but it is span-dependent, not a law — the **"Mixed" branch** of the pre-stated falsification matrix.

**Consequence for P2.b training (§3c loss):** keep `λ·L_manifold` as the planned **swept hyperparameter** with the **F/free end as the prior** (it never hurt recall and won the informative spans); select the operating λ by the recall invariant on held-out episodes (§3c-1). Do **not** hard-lock to the hull limit (no consistent recall gain) and do **not** claim the manifold constraint is recall-hostile (n=6 refutes it). The §3c framework — sweep λ, select by recall — is unchanged and now empirically grounded.

**Methodology note (kept on the record):** the n=1 s12 verdict was a genuine overclaim caught by the n>1 hardening we ran *before* the number could anchor a cloud-training schedule — the exact value of "the magnitude wants n>1." Residual caveats: span-readback NLL is a strong content proxy (a query/cloze recall harness is the P2.b-training-time upgrade); absolute PPLs are large on low-context-predictability spans (the *relative* position-matched FILLER/F/H ordering is the signal, not the absolute value).

## 3e. PHASE 1 — ADAPTER FIRST RUN (G-P2b-1, 2026-06-09; A6000, self-terminating; pod 1bgv4i8h3ah5aw)

The trained adapter (`train_p2b.py`: span embeddings → bottleneck-d512 transformer → k=2 cross-attention queries → k pseudo-tokens; **11.3M params**, ≤50M ✓) amortizing the Phase-0 inversion. Same differentiable gold forward; loss = continuation-KL + λ·soft-min manifold (Arm-F, λ=0.1 — the n=6 F-prior). 200 train / 40 held-out wiki spans, 4 epochs. Local toy smoke + on-pod real smoke both green first (cost discipline). Receipts: HF `KnackAU/xbar-p2b-run` `results_p1/lam0.1/`.

| epoch | held-out recovery_med | readback F / null | F beats null |
|---|---|---|---|
| 0 | 0.124 | 4.23 / 4.36 | 22/40 |
| 1 | 0.190 | 4.20 / 4.36 | 25/40 |
| **2 (peak)** | **0.204** | 4.25 / 4.36 | 25/40 |
| 3 | 0.148 | 4.33 / 4.36 | 19/40 |

**VERDICT — G-P2b-1 WEAK POSITIVE (telemetry; band NOT pinned). NOT the kill, NOT a clean pass.**
- **The adapter generalizes:** held-out recovery is **0.15–0.20 — clearly > 0** on spans it never trained on, so it learns a transferable span→pseudo-token mapping, not per-span overfitting. The pre-stated falsification (recovery ≈ 0 → amortized 6→2 dead) **did not trigger.** Amortization is viable.
- **But ~5× below the inversion ceiling** (Phase 0 per-span: ~0.94 free / ~0.73 hull; this amortized adapter: ~0.20). The generalization gap is the new problem.
- **Recall marginal:** readback-F barely beats the noise null (4.25 vs 4.36; F_beats_null ≤25/40) — compressions preserve a little content, not a lot.
- **Overfitting by epoch 3** (recovery 0.204→0.148, F_beats_null 25→19) on only 200 spans → the lever is **more training data + early-stop at the held-out peak**, NOT more epochs.

**Consequence / next (no λ-sweep yet):** sweeping λ on a weak adapter is premature. The next run closes the gap — **scale train spans (~1–2k) + early-stop**, possibly a larger adapter / longer span budget — then re-assess G-P2b-1; only once the adapter is strong does the λ-sweep (the operating-point refinement, F-prior) become meaningful. The §3c framework is intact; this run pins the *bottleneck* (data/amortization capacity), not λ.

## 3f. PHASE 1b — corpus-leakage correction + the scaled run (launched 2026-06-09, pod ahwa6mfim1q9yk)

**A flaw in the §3e "scale spans" plan, caught on review before spending.** The wiki corpus is **5,432 tokens**. The Phase-1 run drew 200 train + 40 val spans from ~5,338 start positions → spans ~22 tokens apart → each "held-out" val context **overlaps a training context by ~42/64 tokens**. So the **0.20 held-out recovery was optimistic** (the val set wasn't truly novel), and naïvely scaling to 2,000 spans on the same corpus drives train/val overlap toward 100% — destroying the held-out gate. The lever is therefore **a bigger, more diverse corpus with a disjoint train/val split**, not span count on the same data. (We verify the operator/Gemini "2k spans" framing rather than execute it blindly: literally true span-count, wrong on the data.)

**Fix, built + smoked:** (1) tokenized `_wiki_head64k.raw` (65 KB) with the real gemma-4 tokenizer → a **~16k-token corpus** (~3× larger); (2) `train_p2b.py` gains a **DISJOINT train/val split** (`--val-frac`: val spans sampled only from the tail corpus region — zero context leakage) and **early-stop / best-checkpoint** (`adapter_best.pt`; the Phase-1 run shipped the overfit *final* epoch, not the epoch-2 peak). Local toy re-smoke green (clean split + best-checkpoint verified). **Run launched** (A6000, self-terminating): 2,000 spans, 6 epochs, λ=0.1, clean split, early-stop → `results_p1b/lam0.1`. This makes the next G-P2b-1 read **clean**: if recovery still ~0.20 on the leakage-free split, that's the honest amortized-generalization number; if it rises with the larger corpus, data-scale is confirmed as the lever (the operator's capacity-vs-data hypothesis) and we then sweep λ. If it *drops* (the prior 0.20 was leakage), the gap is larger than thought and a still-bigger corpus / different architecture is next. Telemetry-then-pin; band still unpinned. **First p1b attempt (ahwa6mfim1q9yk) failed at the on-pod smoke** (~$0.10, self-terminated before the batch): the on-pod tokenizer wrote space-separated ids on one line, but `train_p2b.py` parsed the corpus newline-per-id (`[int(x) for x in open(f)]`) — fixed to `.read().split()`. The local toy smoke can't catch this (toy path skips the file parse); the **on-pod real-smoke gate caught it pre-batch** — exactly its job. Re-launched **pod 6noo1gnegghfcl**.

## 3g. PHASE 1b — CLEAN-SPLIT RESULT + the correction (DONE 2026-06-08 23:52 UTC, pod 6noo1gnegghfcl self-terminated; cost-capped ✓)

Receipts: HF `KnackAU/xbar-p2b-run` `results_p1b/lam0.1/` (`receipts_train.json`, `adapter_best.pt`, `adapter_final.pt`). Provenance: 11.296M-param adapter, k=2, n=6, ctx=64, cont=24, d=512, enc 2L, nhead 8, lr 3e-4, λ=0.1, tau=1.0, seed 20260609; ~16k-token corpus; 2000 train / 100 val spans; **disjoint split** `train [1,12046) | val [12046,16062)` (banner-confirmed, zero context leakage); 6 epochs, early-stop on `recovery_med`.

| epoch | held-out recovery_med | readback F / null | F beats null |
|---|---|---|---|
| init (untrained) | 0.141 | 5.58 / 5.26 | 57/100 |
| 0 | 0.104 | 3.83 / 3.87 | 43/100 |
| 1 | 0.132 | 3.64 / 3.87 | 58/100 |
| 2 | 0.127 | 3.72 / 3.87 | 46/100 |
| 3 | 0.113 | 3.76 / 3.87 | 52/100 |
| 4 | 0.085 | 3.96 / 3.87 | 45/100 |
| **5 (best)** | **0.171** | 3.797 / 3.873 | 54/100 |
| final | 0.164 | 3.744 / 3.873 | 51/100 |

**CORRECTION ON THE RECORD (no spin).** A mid-run console snapshot (uploaded ep0–ep4 only) drove an over-claimed verbal verdict — *"recovery dropped below untrained init (0.141→0.085), the signature of a network actively unlearning, never beats init, dead end"* — which the operator amplified. **The final epoch (ep5=0.171, final=0.164) falsifies it.** The ep4 dip to 0.085 was a transient in a **high-variance, non-monotone** single-seed trajectory; the best and final epochs both land **above** untrained init (0.141). The truncated log produced the overclaim; the full receipt corrects it. Correction attached, not silently downgraded.

**VERDICT — G-P2b-1 on the leakage-free split: WEAK / INCONCLUSIVE on recovery, NEGATIVE on the recall invariant. Band NOT pinned.**
- **Recovery — leakage was real but modest.** Leaky §3e peak 0.204 → clean best **0.171** (~0.03 inflation, not the evaporation the partial log suggested). Training clears untrained init (0.141) by only **~+0.03**, and that margin sits *inside* the epoch-to-epoch noise band (0.085–0.171 on one seed). A faint positive pulse, **not bankable without multi-seed** repetition.
- **Recall invariant — the operative gate — at chance.** Best epoch `F_beats_null` 54/100, `readback_F` 3.797 ≈ `readback_null` 3.873. On the axis the Curator actually selects on (read a span back from its pseudo-tokens), the k=2 compressions carry **no above-noise span identity**. This is the load-bearing negative and it is unambiguous.
- **Net:** the §3e "weak positive / amortization viable" claim is **retracted as leakage-inflated**; the corrected signal is too weak (recovery) and absent (recall) to call the mechanism working. But it is **not** the hard dead-end declared from 5/6 epochs — the recovery pulse over init is real if fragile.

**Consequence / next.** The bottleneck is **mechanism, not data scale** (the larger clean corpus did not lift recovery materially, and recall stayed at chance). Two falsifiable forks before any λ-sweep (λ-sweep on a chance-level recall signal remains premature): (1) **capacity/structure of the write** — k>2 pseudo-tokens and/or a larger adapter, testing whether the 6→k bottleneck is simply too tight for a selectable code; (2) **the loss itself** — continuation-KL + soft-min manifold optimizes *next-token continuation*, not *span recoverability*; add an explicit **readback/reconstruction term** so the objective rewards the recall invariant directly rather than hoping it falls out of continuation. Multi-seed (≥3) any next run before pinning a band — the single-seed variance here (±0.04 epoch-to-epoch) is the reason this read stays INCONCLUSIVE rather than positive.

## 3h. FORK-2 — readback-CE loss + recall-margin early-stop, 3 SEEDS (PRE-REGISTERED, launched 2026-06-09, pod tpau7g2lwe1hny, H100 PCIe)

**Diagnosis (from §3g):** the Phase-1b loss (`L_KL + λ·L_manifold`) commands *continuation*, not *recoverability* — the optimizer correctly discards span identity because nothing penalizes its loss; recall sat at chance. Embedding-distance reconstruction (cosine/L2 to source tokens) was REJECTED: `manifold_pen` already constrains embedding space, and Arm-F-vs-H proved spatial proximity to source embeddings does NOT predict through-model recall. The loss must be computed at the END of the forward pass.

**Intervention (Fork-2, minimal):** the eval recall metric `readback_nll` (teacher-force the span's own tokens after the k pseudo-tokens, NLL through the FROZEN gold forward) was already written but returned `.item()`. Made a differentiable twin → added `+ λ_read · L_readback` to the loss (`--lam-read`, `--loss-mode`). Now the training objective IS the eval metric — no proxy, same `forward_logits` path. **Early-stop realigned:** selects on the recall margin (`readback_null_med − readback_F_med`) when `lam_read>0`, NOT continuation recovery (selecting on a metric you don't optimize lets noise pick the checkpoint). Contrastive/InfoNCE DEFERRED (needs a batch-negative refactor; one variable at a time — add readback-CE alone, reach for contrastive only if CE plateaus).

**Local gradient smoke (GREEN, pre-cloud):** readback-only training on 8 fixed toy spans drove `readback_F_med` 6.217→6.000 and `F_beats_null` **4/8 (chance) → 8/8** on the optimized spans — the through-model gradient lowers the NLL and makes the payload selectable. Default path (`lam_read=0`) byte-inert (original Phase-1b loss). 

**Run config:** λ_read=0.25 (scale-matched: KL+manifold ran ~0.7, real-12B readback NLL ~3.7 → 0.25·3.7≈0.9 ≈ co-equal with KL — neither dominates), single value ×**3 seeds {20260609,20260610,20260611}** (the §3g single-seed ±0.04 variance is why last read was inconclusive). Else identical to clean §3g: 16k corpus, disjoint val-frac 0.25, 2000/100 spans, 6 epochs, recall-margin early-stop. Sequential on ONE pod (one gated-weight download — 3 concurrent downloads risk HF rate-limit; operator's call). H100 PCIe (~4× A6000; operator: wall-time matters). On-pod real-smoke now exercises the readback path. Self-terminating trap. Receipts → HF `results_fork2/seed_<s>/`.

**PRE-STATED FALSIFICATION MATRIX (locked before spend; multi-seed makes each conclusive):**
- **WORKS** → held-out `F_beats_null` robustly > chance (≥~60/100 lower-bound across ALL 3 seeds) AND recovery doesn't collapse (≥~0.10) → mechanism viable → THEN sweep λ_read + reconsider k.
- **TENSION** → recall rises but continuation-recovery collapses → the two objectives fight at k=2 → evidence-backed trigger for k>2 (Fork 1).
- **CEILING** → `F_beats_null` stays ~50 across all seeds EVEN while directly optimizing readback → k=2 cannot carry a selectable code → information-theoretic ceiling established as a byproduct → Fork 1 / rethink injection point.

Fork-2 strictly dominates Fork-1: it either fixes recall, or its failure mode hands us Fork-1's ceiling readout for free. Orchestration: bootstrap_fork2{,b}.sh / stage_fork2.py / launch_pod_fork2{,b}.py / fetch_fork2.py in _xbar/p2b/. VERDICT pending STATUS=DONE (no verdict from in-flight logs — §3g lesson).

### Fork-2 RESULT — WORKS, CONFIRMED across 3 seeds (DONE 2026-06-09; receipts HF `results_fork2/seed_<s>/`)

Ops note: seed 20260609 ran on H100 PCIe (pod tpau7g2lwe1hny) — a GPU-mismatch (batch=1 is latency-bound; H100 gave A6000 wall-speed at 28% util / ~6× cost). Caught mid-run; seed-1 salvaged via the RunPod web terminal (`cat` + HF `upload_folder`), H100 terminated, seeds 2&3 cascaded to A6000 (pod p2ydnrm83s3urm, per-seed upload, self-terminated ✓). ~$11 all-in vs ~$24 to ride. Lessons banked: match GPU to workload profile; upload per-unit.

**Recall invariant (the operative gate), final epoch:**

| seed | F_beats_null | recall margin (null−F) | recovery_med |
|---|---|---|---|
| 20260609 | 82/100 | 3.870−3.430 = 0.440 | 0.192 |
| 20260610 | 80/100 | 3.765−3.461 = 0.305 | 0.168 |
| 20260611 | 84/100 | 4.167−3.891 = 0.276 | 0.181 |
| **§3g baseline (no readback term, same harness)** | **58/100 ≈ chance** | **≈ 0** | **0.171** |

Best-epoch (recall-margin early-stop) F_beats_null: 78 / 83 / 72 (median 78). Final: 80–84 (median 82).

**VERDICT — G-P2b-1 / recall invariant: WORKS, reproducible.** (1) Recall robustly off chance — every seed 80–84/100 final (6–7σ from p=0.5 at n=100), tight across initializations → not a lucky draw, the §3g single-seed-variance trap does not recur. (2) Recall margin reliably positive (~0.28–0.44 NLL; F below null every seed). (3) **No TENSION** — recovery held at ~0.17–0.19 (≈ §3g's 0.171, not collapsed) → k=2 carries continuation **and** a selectable identity simultaneously. (4) **Causal attribution clean** — §3g (identical corpus/split/architecture, no readback term) sat at chance; the *only* change is `+λ_read·L_readback`, and it flipped recall decisively. The Fork-2 diagnosis is validated: the loss must be computed at the END of the forward (through-model readback), not via embedding-distance proxies (`manifold_pen` already failed that).

**Scope kept honest:** single λ_read=0.25, single corpus, single architecture (k=2, 11.3M). This establishes the **mechanism works**; it is NOT yet the pinned operating point. Recovery (~0.18) is still ~5× below the Phase-0 per-span inversion ceiling (~0.94 free / 0.73 hull) — the adapter now generalizes AND is selectable, but is not at the inversion ceiling (a separate data/capacity optimization, not required for WORKS).

**NEXT (now unlocked):** λ_read sweep {0.1, 0.25, 0.5, 1.0} (best seed or ≥3-seed at the top candidates) to pin the operating point on the recall margin — the §3c/§3d selection, now grounded on a working signal. Then: close the recovery gap (k>2 and/or larger adapter, the deferred Fork-1, now justified by evidence not guesswork) and the contrastive/InfoNCE uniqueness term (deferred from §3h — reach for it if the sweep plateaus). The P2.b adapter now produces Curator-selectable pseudo-tokens — the keystone the XBAR Memo/consolidation lanes were blocked on.

### Fork-2 λ_read SWEEP — tradeoff curve (DONE 2026-06-09; pod iaun2xu3ep5b5n A6000, self-terminated ✓; receipts HF `results_sweep/lam_<v>/`)

Single-seed scan (seed 20260609) of the NEW points {0.1, 0.5, 1.0}, anchored on the 3-seed λ=0.25 (recall 80–84, recovery ~0.18). best = recall-margin early-stop checkpoint.

| λ_read | F_beats_null (best) | margin null−F | recovery (best) | readback_F | sustained (final F_beats_null) |
|---|---|---|---|---|---|
| 0.1 | 73/100 | 0.49 | 0.190 | 3.383 | **NO — 48/100 (decays to chance)** |
| 0.25 (3-seed) | 78–82 | 0.40–0.55 | ~0.19 | ~3.32–3.46 | yes (80–84) |
| **0.5** | **84/100** | **0.56** | **0.206** | 3.315 | yes (81) |
| 1.0 | 78/100 | 0.59 | **0.154** | 3.280 | yes (78), recovery cannibalized |

Reads: (1) raw recall (readback_F) improves monotonically with λ (3.38→3.32→3.28). (2) **λ=0.1 is unstable** — peaks at epoch 1 (73) then decays to chance by final (48); too weak to *sustain* the signal (early-stop caught a transient). (3) **λ=1.0 is the TENSION branch** — recall sustained but recovery collapses 0.21→0.15; strictly worse than 0.5 (pays recovery for raw-recall gain that doesn't even lift F_beats_null). (4) **λ=0.5 is the knee** — max F_beats_null (84) with recovery still at peak (0.206).

**VERDICT (scan):** usable band **[0.25, 0.5]**; avoid ≤0.1 (unstable) and ≥1.0 (tension). **λ=0.5 is the candidate operating point**, BUT its edge over the 3-seed-confirmed λ=0.25 sits *inside* the λ=0.25 seed spread → NOT pinned on n=1 (the single-seed lesson). DECISION step: 3-seed confirm at λ=0.5 vs the λ=0.25 anchor; if 0.5 holds its edge across seeds it's the operating point, else 0.25 stands (already confirmed). Either way the band is locked. THEN: close the recovery gap (k>2 / larger adapter — Fork-1, now evidence-justified) and contrastive if it plateaus.

## 3i. FORK-1 k-SWEEP — the compression/recovery Pareto front (PRE-REGISTERED; **DONE 2026-06-09 21:16 UTC** — STATUS=DONE, pod l4e73rex8m3sxs self-terminated ✓; receipts + adapters HF `results_ksweep/k_<v>/` + `job.log`)

**Pre-registered design (locked in `bootstrap_ksweep.sh` before spend):** vary ONLY k (pseudo-token count) at the adopted λ_read=0.5 (the §3h-sweep knee); span n=6 fixed; seed 20260609; identical corpus / disjoint split / 11.3M architecture as §3g/§3h. k ∈ {1,3,4,6}; k=2 is the held 3-seed anchor. **k=6 (=n, NO compression) is the DIAGNOSTIC CONTROL — it separates compression-limit from adapter-limit:** if removing the bottleneck sends recovery toward the per-span inversion ceiling (~0.94/0.73), the 6→k squeeze was the binding constraint (lever = k); if recovery stays ~0.2 regardless of k, the d=512/11.3M adapter caps recovery (lever = adapter capacity/data — Fork-1's capacity arm — NOT more tokens). Single-seed scan → 3-seed confirm at the knee. Per-k upload inside the loop + self-terminating trap (the Fork-2 ops lessons applied).

Landed so far (BEST = recall-margin early-stop checkpoint):

| k | comp (6/k) | F_beats_null | margin null−F | recovery_med |
|---|---|---|---|---|
| 1 | 6× | **88/100** | **0.579** | 0.101 |
| 2 (anchor, 3-seed) | 3× | 84 | 0.56 | **0.206** |
| 3 | 2× | 72 | 0.453 | 0.184 |
| 4 | 1.5× | 70 | 0.448 | 0.186 |
| 6 (control) | 1× | 60 | 0.260 | 0.155 |

(k=6 FINAL epoch: recovery 0.191 / recall 71 — beats its own recall-margin best checkpoint; single-seed trajectory noise, same character as §3g. Both readings sit inside the adapter-limited band, so the verdict below is insensitive to checkpoint choice. k=4 FINAL similarly wobbles to 77.)

Interim reads (NO verdict from a partial scan — the §3g lesson; verdict waits on `STATUS=DONE` + k=6):
1. **Dilution confirmed** — recall falls monotonically with k across FOUR points (88→84→72→70): more pseudo-tokens dilute the address key.
2. **Recovery plateaus at k=2** (0.101 → 0.206 → 0.184 → 0.186; k≥2 flat within noise) — capacity for continuation stops paying after two vectors; the adapter-limited tell.
3. **Recall and recovery ANTI-CORRELATE along k** — k=1 is the *most selectable* address (88/100, best margin) at half the recovery; addressability and continuation capacity pull in opposite directions along this axis.

**Pre-stated k=6 predictions (written before its receipt):** adapter-limited ⇒ recovery_k6 ≈ 0.18–0.22 with recall sliding further (~60s); compression-limited ⇒ recovery_k6 breaks well above ~0.25 toward the inversion ceiling. If adapter-limited holds, k=2 stands as the product-maximizing knee and the next lever is adapter width/depth/data; k>2 is retired as a recovery lever.

### k-SWEEP VERDICT (2026-06-10) — **ADAPTER-LIMITED; both pre-stated predictions hit; k=2 confirmed as the operating knee**

1. **The control answers the question.** k=6 = ZERO compression — the adapter merely re-encodes 6 tokens as 6 vectors — and recovery did **not** rise: 0.155 best / 0.191 final, inside the pre-stated adapter-limited band and nowhere near the ≥0.25-toward-ceiling branch. Removing the 6→k bottleneck buys *nothing*. The recall prediction hit too: k=6 best = **60/100, the predicted "~60s" dilution endpoint.** ⇒ The ~0.2 recovery cap belongs to the **adapter (capacity/data/objective), not the compression ratio.** The 6→2 squeeze is FREE relative to no compression.
2. **Dilution confirmed across the full curve:** recall 88→84→72→70→60 (best-checkpoint), monotone over five points spanning 6×→1×. More pseudo-tokens = a more diluted address key; k=1 is the sharpest address in the family.
3. **k=2 dominates:** best recovery on the curve (0.206) AND near-best recall (84/100) — strictly better than every k≥3 on BOTH axes, and it is the only 3-seed-confirmed point. k=1 trades half the recovery (0.101) for +4 recall — a niche, not the knee.
4. **Scope honest:** single-seed scan at k∈{1,3,4,6} (±~0.04 recovery / ±~5 recall per the §3g/§3h spread); the verdict rests on the *shape* (monotone dilution + flat plateau + control-no-lift), which is robust to per-point noise, and the knee itself is already multi-seed.

**CONSEQUENCE (the Fork-1 pivot, evidence-forced):** **k is retired as a recovery lever.** The gap to the 0.94 per-span inversion ceiling is an *adapter* problem: capacity (d512 width / 2-layer depth / 11.3M params, contract cap ≤50M), training data volume, and the deferred contrastive/InfoNCE uniqueness term. **Operating point pinned at k=2, λ_read ∈ [0.25, 0.5]** (the remaining decision: 3-seed confirm of λ=0.5 vs the 0.25 anchor). Next run = the capacity arm at the pinned point, recall-invariant primary, ≥3 seeds before any band is pinned.

## 3j. THE CAPACITY ARM — width/depth grid at the pinned point (PRE-REGISTERED 2026-06-10, before spend)

**Design:** hold EVERYTHING at the §3i pinned point — k=2, n=6, λ=0.1, λ_read=0.5, loss-mode both, 16k corpus, disjoint val-frac 0.25, 2000/100 spans, 6 epochs, recall-margin early-stop — and vary ONLY adapter architecture, **×3 seeds {20260609,10,11} per config** (gains are hunted above a ~±0.02 noisy floor; single-seed is inadmissible here by standing rule). Param counts computed from the real `train_p2b.py` Adapter (in/out E=3840 projections ≈4M fixed/side; encoder ≈12d²/layer):

| config | params | role |
|---|---|---|
| d512 / L2 | 11.3M | baseline — **doubles as the deferred 3-seed λ=0.5-vs-0.25 confirm** (the λ=0.25 anchor is the existing 3-seed; this leg closes the band decision) |
| d1024 / L2 | ~37.3M | width-heavy arm |
| d512 / L4 | ~17.6M | depth-heavy arm |
| d1024 / L3 | ~49.9M | combined, AT the ≤50M cap (d1024/L4 = ~62M would bust it — rejected, no silent cap amendment) |

Width/depth arms are NOT param-matched (37.3 vs 17.6M) — they read as width-heavy vs depth-heavy; the capacity axis proper is the monotone series 11.3→17.6→37.3→49.9M. Bootstrap enforces the cap mechanically (computes params pre-run; CAP-EXCEEDED = skip + log). Hardware: A6000 (batch=1 latency-bound — the banked GPU-matching rule; the 12B backward dominates, the +50M adapter ≈ +0.6 GB optimizer state). 12 runs ≈ 21 GPU-h ≈ $7, split over two self-terminating pods (per-RUN upload).

**PRE-STATED FALSIFICATION MATRIX (locked before spend):**
- **CAPACITY-WORKS** → some expanded config's 3-seed median recovery ≥ ~0.25 (clears the 0.206 baseline by ≥2× seed spread) with F_beats_null ≥ ~75 → capacity is the lever; continue along the winning axis (and data next).
- **NOT-CAPACITY (data/objective-limited)** → all configs flat ~0.20 — or *worse* via faster overfit on 2000 spans (early-stop will show best-epoch ≪ final) → capacity retired at this data scale; fork = data volume/diversity, then the contrastive/InfoNCE uniqueness term.
- **RECALL-TENSION** → recovery rises but F_beats_null drops materially (<~70) → added capacity is being spent blurring the address key → contrastive term and/or λ_read upward before more width/depth.

Cross-config comparisons are within-grid (identical data/split/seeds); the §3i k=2 anchor is the external reference. VERDICT only on STATUS=DONE × both pods, all 12 receipts (standing rule).

### CAPACITY-ARM VERDICT (2026-06-10; both pods DONE + self-terminated ✓, 12/12 rc=0; receipts HF `results_cap/{a,b}/`) — **NOT-CAPACITY**

**Calibration first (pre-committed):** baseline d512L2 @λ_read=0.5, 3-seed BEST recovery = 0.206/0.138/0.148 → **median 0.148, spread ±0.034** (the n=1 "0.206" anchor seed confirmed as the lucky draw). Re-derived WORKS bar ≈ median + 2×spread ≈ **0.22** — the original 0.25 line survives calibration; thresholds did not need weakening to produce this verdict (the conservative direction).

| config | params | recovery med (3-seed BEST) | recall med | tells |
|---|---|---|---|---|
| d512L2 baseline | 11.3M | 0.148 | **84** | seed 20260611 FINAL collapsed (0.075 / 43-100) — λ=0.5 late-training instability on 1/3 seeds |
| d512L4 depth | 17.6M | 0.145 | 84 | flat |
| d1024L2 width | 37.3M | 0.151 | **72** | early-stop @epoch 1; finals decay (one to 49/100) |
| d1024L3 combined | 49.9M | 0.168 | **68** | early-stop @epochs 2–4; finals decay |

1. **NOT-CAPACITY:** every config's recovery median sits inside the baseline noise band; 4.4× parameters bought zero recovery. The §3j matrix's overfit signature fired exactly as pre-named (large adapters peak at epoch 1–2 then decay on the same 2000 spans). **The ~0.18 plateau is DATA/OBJECTIVE-limited, not architecture-limited.** Width and depth are retired as recovery levers at this data scale.
2. **Capacity actively harms the address key:** d1024 recall medians 72/68 vs 84 — added capacity is spent memorizing, blurring selectivity. The smallest adapter is Pareto-optimal on BOTH axes.
3. **The λ-confirm leg resolved itself (bonus):** baseline λ=0.5 3-seed median 0.148 ± 0.034 with one final-epoch collapse, vs the §3h λ=0.25 3-seed anchor at **0.181 median, tight (0.168–0.192), recall 80–84 sustained, zero collapses**. λ=0.5's n=1 edge was seed luck. **OPERATING POINT PINNED: k=2, λ_read=0.25, d512/L2 (11.3M).** The keystone component is deliberately small — excellent for deployment (Memo co-residency in 12 GB).
4. **NEXT (the pre-registered NOT-CAPACITY fork):** (a) **data volume/diversity** — the 16k-token corpus / 2000 spans is the suspected binding constraint (large adapters overfitting it is the tell); scale corpus 10–100× + spans ~10× at the pinned point, 3 seeds, same matrix discipline; (b) if data plateaus → the deferred **contrastive/InfoNCE uniqueness term** (the §3h deferred lever); (c) the Phase-0 per-span ceiling (~0.94) remains the honest reference — amortization has captured ~19% of it so far.
5. **Kairos/NIGHTSHIFT implication (on the record):** the recall invariant — the Curator's actual currency — is strong and stable at the pinned point (80–84/100). Consolidation with ~0.18 recovery is *lossy gist memory by construction*, which is what Ring 3 was designed to be; **G-R3-LOSS is the load-bearing bound** (un-compressible episodes stay verbatim in Ring 2 — a valid outcome, not a failure). K1/NIGHTSHIFT is therefore NOT blocked by this verdict; it inherits a high-selectivity, bounded-loss substrate with the loss gate doing the governing.

Cost: 12 runs ≈ 22 GPU-h ≈ $7.3 (A6000 ×2, per-run upload, clean self-termination both pods).

## 3l. THE DATA ARM — corpus scale at the pinned point (PRE-REGISTERED 2026-06-10, before spend)

**Design:** hold the PINNED operating point — **k=2, λ_read=0.25, d512/L2 (11.3M)** — and vary ONLY data: corpus 16k tokens → **~1.4M tokens** (~85×; wikitext-103-raw-v1 TRAIN split head, fetched on-pod from the public HF dataset — fresh articles, no fixture entanglement), train spans 2,000 → **20,000** (~10×; spans now ~50 tokens apart vs ~8 — the §3f overlap confound structurally collapses), val 100 spans from the disjoint tail (val-frac 0.25, fully unseen articles), 3 epochs (60k steps ≈ 5× prior total optimization), recall-margin early-stop, **×3 seeds {20260609,10,11}**, one seed per pod (A6000 ×3, staggered launches), per-epoch upload, self-terminating, 12 h timeout/run. Yardstick: the §3h λ=0.25 3-seed anchor (recovery median **0.181**, recall 80–84) — same config, old data. Honesty note pre-stated: the anchor itself carried residual train/val context-overlap advantage; the clean-corpus number may shift either way at epoch 0 — the matrix bands below judge, not a single delta.

**PRE-STATED FALSIFICATION MATRIX (locked before spend):**
- **DATA-WORKS** → 3-seed median recovery (BEST) **≥ 0.25** (clears the calibrated noise bar) with recall median ≥ 75 → data was the binding constraint; next = another data decade or bank the win and proceed to P3/NIGHTSHIFT with the improved adapter.
- **PARTIAL** → median ∈ (0.20, 0.25] → real lift above the noise band but short of the bar → one more data decade AND begin the contrastive refactor in parallel.
- **OBJECTIVE-LIMITED** → median ≤ 0.20 → with capacity (§3j) and data both exhausted, the loss itself is the binding constraint → unsheathe **contrastive/InfoNCE** (the §3h-deferred batch-negative refactor of `train_p2b.py`) as the next contract leg.
- **Recall guard (all branches):** recall median < 75 → the objective is trading the address key for recovery → contrastive becomes mandatory, not optional.

Cost: 3 runs ≈ ~29 GPU-h ≈ **~$10** (A6000 ×3 parallel, ~10 h wall). VERDICT only on STATUS=DONE ×3 (standing rule).

## 4. Compute plan & receipts

RunPod/Colab A100-class, bf16 HF checkpoint from the proven bucket (the 4.68-gold weights — the ONLY trusted source, STATE doctrine). All cloud runs export: config echo (banner = printed env/args), dataset manifest hashes, loss curves, golden-pair archives. Receipts land in `_xbar/p2b/` + the contract run-record; ledger row only on the agreed gates green. **Ops upgrades banked from the Phase-0 runs:** the pod bootstrap must **periodic-upload its log** (RunPod community API returns no telemetry — flying blind otherwise; the operator had to pull the console log manually); validate the corpus is *coherent before* inverting (greedy 90-tok generation degenerates — use continue-narrative seeds + shorter gen + sampling if a fluent baseline is ever needed).

## 5. Convergence note (why this is the home stretch's keystone)

P2.b's adapter is: the deployable injector (XBAR-P exit) · Memo's compaction organ (XBAR-C2: ring consolidation = compress episodic spans to pseudo-token state under the same fidelity gates) · the modality template (XBAR-M swaps the source encoder) · NIGHTSHIFT's worker (consolidation pass = adapter applied offline under promote-on-accept). One trained component, four lanes served. The open Memo-body decision is logged in RFC v1: with the adapter as the organ, Memo v1 may be *adapter + tiny ring-block encoder* rather than the 0.5B M.0 stub.
