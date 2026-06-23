---
type: design
title: "Diffusion-judge throughput: the resident-cascade strategy + ranked levers + the 3-way native bake-off"
description: "A receipts-first plan to maximize judge throughput on a 12GB / PCIe-gen3-x8 box. The 26B-A4B diffusion judge is host-to-device streaming-bound; the strategy is a confidence-gated cascade (resident E2B -> resident 12B -> streamed diffusion) plus three throughput levers for the expensive path, settled by a pre-registered 3-way native bake-off. Separates MEASURED facts from TARGETS, and native judge accuracy from the external oracle."
resource: shannon-prime-lattice/papers/DESIGN-DIFFJUDGE-THROUGHPUT.md
tags: [diffusion-judge, throughput, cascade, moe, pcie-bound, prefix-kv, gemma4-12b, gemma4-e2b, bake-off, boundary-thesis]
timestamp: 2026-06-24T00:00:00Z
sp_status: DESIGN
sp_gate: none
sp_commit: TBD
sp_repro: "n/a (design doc); the bake-off protocol (section 5) is the falsifiable gate"
---

# Diffusion-judge throughput: the resident-cascade strategy

**Thesis:** stop paying the 14 GB expert-streaming tax on every judge query. Route most queries to **resident** models (no PCIe streaming) and spend the streamed 26B diffusion judge only on the contested residual. This trades nothing we have measured and attacks the one bottleneck telemetry actually shows.

> **Receipts-first scope (read before trusting any number here).** This doc is DESIGN. Two discipline rules apply throughout: (1) every accuracy figure is tagged **MEASURED** (with its corpus + config) or **TARGET** (a number to measure, not yet measured); (2) we never quote the diffusion judge's **external-oracle** 95.6% as if it were our **native** judge -- those are different things and conflating them is the error that has dogged this campaign. The cascade below is a *structure*; the numbers that decide whether to build it come from section 5's bake-off, not from this prose.

## 1. The bottleneck (MEASURED)

A diffusion-judge forward is **host-to-device PCIe-streaming-bound**, not compute- or canvas-bound:
- the 26B-A4B MoE at OK_Q4B is **~14 GB**; the RTX 2060 has **12 GB** VRAM, so it does not fit. Active experts stream host->device over **PCIe gen3 x8 (~6.2 GB/s)** every forward.
- the wins that landed this session all attacked the *stream*, not the math: `SP_DG_SCRATCHREUSE` (default-on, ~1.46x, engine `e31c70d`) removed the per-expert malloc/free sync; `SP_DG_ASYNC` (byte-exact, engine `2a1c830`) overlapped the upload with compute; the "integrated cache" probe moved only ~5%. Per-forward wall-time tracks **expert bytes moved**, confirming the bound.
- `SP_DG_PREFIXKV` (answer-lossless, `G-DG-PREFIXKV-PARITY` GREEN; production ~1.5-1.6x at CANVAS=256/STEPS=4) cuts the per-step *work* by forwarding only the canvas -- but each step still streams its experts, so the bound stands and the cascade is still the lever.

**Corollary that sorts every idea:** anything that moves **fewer expert bytes** (smaller routing breadth, resident hot experts) or **fewer times** (batching, cascading) helps; running independent diffusions "in parallel" pays the 14 GB stream N times and is *slower* unless batched into one stream.

## 2. The reframe: resident beats streamed, and the VRAM budget is the real constraint

The model-size intuition inverts on this hardware. A **Gemma-4-12B at OK_Q4B is ~7 GB -- it FITS, fully resident, zero streaming** (it is already the served chat model at ~26 tok/s). On the *judge* workload a resident 12B is plausibly **both faster and more accurate** than the streamed 26B diffusion judge. So "bigger streamed model" does not dominate "smaller resident model" here -- it is the other way around for the common case.

The honest constraint Gemini's draft glossed: **all three models cannot be fully resident at once.** A workable budget on 12 GB:
- **Gemma-4-E2B** (OK_Q4B, ~1-1.5 GB) resident -- the cheap sentinel.
- **Gemma-4-12B** (OK_Q4B, ~7 GB) resident -- and it is the **same weights already resident for serving chat**, so the judge reuses them for free (no extra load).
- that leaves **~3-4 GB** for KV caches + the diffusion Stage-3 **streaming double-buffers + a hot-expert reservoir**. The diffusion model is NOT co-resident; it streams into that residual window only when Stage-3 fires.

That budget is tight but plausible, and it is itself a thing to **measure** (peak VRAM with E2B+12B resident + diffusion streaming) before committing -- listed as a bake-off variable in section 5.

## 3. The tiered confidence-gated cascade

Three stages, cheapest first; a query escalates only when the current stage is **uncertain**. The gating signal is the **Shannon entropy `H` of the answer-row token distribution** (the constrained {tags, NULL} logits at the answer position): low `H` = confident = commit the tag; high `H` = escalate. Two thresholds, `tau1` (E2B->12B) and `tau2` (12B->diffusion), are tuned on a held-out calibration set to a target system recall -- they are the knobs that trade speed for accuracy.

| Stage | Model | VRAM profile | Accuracy (HONEST) | Role |
|---|---|---|---|---|
| **1 -- Sentinel** | Gemma-4-E2B | resident, ~1-1.5 GB, no streaming | **TARGET / unmeasured** as a judge | triage 100% of queries; commit the easy/high-confidence ones (`H < tau1`), escalate the rest |
| **2 -- Adjudicator** | Gemma-4-12B (generative) | resident, ~7 GB (shared with served chat), no streaming | **MEASURED 85.7% recall@1 on `_needle_corpus_div` (Phase 4); OOD UNMEASURED** | handle the escalated bulk; commit if `H < tau2`, else escalate |
| **3 -- Arbitrator** | diffusion-26B-A4B | **streamed** (~14 GB over PCIe), `SP_DG_ASYNC` + `SP_DG_PREFIXKV` | **CEILING 95.6% external oracle / 94.4% OOD@K8; NATIVE is config-dependent and being re-measured** (reduced-config 8.3%; full CANVAS=256/STEPS=12 early signal ~54%@13, in-flight, small-N) | the bidirectional reranker; fires only on the contested residual (`H >= tau2`), where its higher ceiling justifies the PCIe tax |

**The load-bearing caveat (the project's recurring trap):** Stage-3's *value proposition is its ceiling*, and that ceiling is currently the **external** llama.cpp oracle, not our native judge. If the running `G-DG-PREFIXKV` gate confirms the native judge is ~50-60% at full config, Stage-3 is only worth its streaming cost on the slice of queries where it beats a resident 12B -- which may be small. The cascade is therefore **contingent**: it is the right architecture *if and only if* the bake-off (section 5) shows a real accuracy band that Stage-3 owns and Stages 1-2 cannot. If the resident 12B matches or beats native diffusion across the board, the cascade collapses to "ship the resident 12B" and diffusion goes back in the drawer until N5b + the entropy-bound sampler close the native gap.

**Why E2B at all (not just 12B alone):** the 12B prefill over a multi-candidate prompt is not free; an E2B sentinel that resolves the obviously-easy queries in a fraction of the time raises aggregate throughput *iff* E2B is a usefully-calibrated filter. That "iff" is a TARGET to measure, not an assumption -- E2B may be too weak to filter, in which case Stage 1 is dropped and the cascade is 12B -> diffusion.

## 4. Throughput levers for the expensive path (ranked; each with a kill-criterion)

These optimize Stage-3 *when* it fires. Ranked by (value on the PCIe-streaming bound) x (low risk) x (reuses existing structure). Every figure here is a TARGET until its gate runs.

| # | Lever | Mechanism | Bottleneck term it cuts | Real risk (corrected) | Kill-criterion |
|---|---|---|---|---|---|
| 1 | **Canvas-width sweep** | run the judge at canvas in {16,32,64,128,256}; the answer is ONE tag token, the rest is scratch "thinking room" | fewer canvas tokens -> **fewer distinct MoE experts routed -> fewer expert bytes streamed** (hits the dominant term, not just FLOPs) | **off the trained canvas-256 distribution** (NOT "longer prompts" -- prompt length is independent of canvas length) | ship the smallest canvas whose recall stays within ~1 pp of canvas-256 AND whose expert-breadth/time drops measurably; else keep 256 |
| 2 | **Multi-query batching** | pack B candidates/queries into one forward so the expert stream is paid once for B judgments | **amortizes the 14 GB stream across B** (the highest-ceiling structural win; stacks on async) | harness needs a real batch dim + per-instance bookkeeping; MoE load-balancing across the batch | linear-ish speedup with B at fixed parity (base==batched picks); else cap B where parity holds |
| 3 | **Resident hot-expert reservoir (= N5b)** | lock the top-K most-routed experts into the residual VRAM window; stream only the cold tail | removes PCIe transfers for the **hot** experts every forward | VRAM contention with the resident 12B (section 2 budget); reservoir-miss path must stay correct | stream-bytes/forward drop >= ~30% with recall held; else the reservoir is too small to matter on this 12 GB box |

Note on **IQ2-resident** (make the whole 26B fit by quantizing to ~2-bit): it attacks the same goal as #3 but (a) the project already convicted sub-Q4 / structure-on-content compression as lossy-or-redundant vs OK_Q4B at gold PPL, (b) it needs an IQ2-equivalent in the sovereign `sp_transcode` pipeline (we ship OK_Q4B/OK_Q8), and (c) since A4B activates only ~4 B/forward, the resident-reservoir (#3, Q4B, no accuracy hit) reaches most of the same win at lower risk. **Rank IQ2 below #3** -- a feasibility note, not a primary lever.

## 5. The pre-registered 3-way native bake-off (the falsifiable gate)

Run immediately after `G-DG-PREFIXKV` completes (the GPU is then free). **One corpus, one config, three judges, same metric** -- the numbers pick the architecture, not the campaign's momentum.

- **Corpus:** the held-out OOD suite (90 needles + 50 foreign). OOD is the only honest battlefield (in-distribution flatters memorizers).
- **Config (identical for all three):** CANVAS=256, **STEPS matched to the reference oracle depth (48; see 5b -- STEPS=12 is a known under-denoising confound)**, greedy/temperature matched; full config, no reduced-canvas shortcuts (the 8.3% lesson).
- **Judges:** (A) Gemma-4-12B **generative** (the Phase-4 harness, re-measured on OOD); (B) diffusion-26B **native** at full config (this is what the running gate's LEG A measures); (C) Gemma-4-E2B as a standalone judge AND as a Stage-1 filter (calibration of `tau1`).
- **Variables tracked:** final-pick accuracy, retrieval recall@1, foreign-reject, aggregate latency (s/item), **peak VRAM** (validates the section-2 co-residence budget).

**Pre-registered decision rules:**
- **12B standalone promotion** -- if the resident 12B generative judge MATCHES OR BEATS native diffusion on OOD accuracy at comparable-or-better latency, **ship the resident 12B as the standalone adjudicator**; diffusion is benched until N5b + sampler-depth close its native gap. (Resident + already-wired + proven-native = the bird in hand.)
- **Cascade green-lit** -- if (and only if) native diffusion owns a real OOD accuracy band the 12B cannot reach, build the cascade, with E2B as Stage-1 **iff** its bake-off calibration shows it is a useful filter (else 12B->diffusion two-stage).
- **Both fail the bar** -- if neither native judge clears a usable OOD recall, the judge problem is an *accuracy* problem (native sampler / N5b), not a throughput problem, and this whole doc waits behind that.


## 5b. Why does the external llama.cpp oracle beat our native judge on the SAME model? (the divergence ladder)

A large same-model gap (external 95.6% vs native ~53% at CANVAS=256/STEPS=12, in-flight) is a code-divergence smell, NOT proof the native judge is inherently weak. Two confounds are already visible in our own telemetry, and they revise the gap downward before any bug-hunt:
- CANVAS: the killed run scored 8.3% at a reduced canvas; the same STEPS=12 at CANVAS=256 scores ~53%. Most of the "8.3%" was under-canvas.
- STEPS (depth): the native judge climbs monotonically with denoise depth -- single-forward ~25% to 12-step ~53%. The reference oracle ran 48 steps; we run 12 (a 4x under-denoise). Discrimination in diffusion comes from refinement, so capping at 12 likely strands much of the recall.

Ranked suspects, cheap to expensive to check (receipts-first):
1. DEPTH (12 vs 48 steps). Simplest, best-evidenced (the 25-to-53 climb). Test: re-measure native at STEPS=48. If recall climbs toward the oracle, the "weak native judge" was largely under-denoising. Highest information per GPU-hour -- do this first.
2. Self-conditioning divergence (identified in our OWN code). Our harness feeds the MASKED answer-row logits back as SC (tests/test_diffjudge_denoise.c:481-489 comment admits it); the reference feeds the RAW canvas logits. A masked/weakened SC signal degrades every refinement step. Test: feed raw (unmasked) canvas logits to SC.
3. Sampler divergence. We reimplemented the EntropyBoundSampler (temperature lerp, accept/renoise, adaptive stop); any drift from the reference (diffusion-sampling.cu) compounds over steps. Test: per-step trace vs the reference on ONE item -- the step where the canvas argmax diverges localizes it.
4. Quant (OK_Q4B vs the oracle Q4_K_M) -- likely SECONDARY. Different 4-bit quants; the once-cited "~40% attenuation" was on a degenerate all-BOS canvas (argmax-unstable), not a clean gap, and our OK_Q4B is PPL-gold (4.6665). Test: same-quant control only if 1-3 do not close it.
5. Forward divergence (region mask / enc-dec scalar / canvas rmsnorm embed / RoPE). N1b claimed structural verification but the diffusion forward was never byte-exact-gated like the 12B was. The per-step trace (#3) catches this too.

This corrects the bake-off (section 5): the native diffusion leg MUST run at the reference depth (STEPS=48, or a depth sweep), not 12 -- else we compare an under-denoised native judge against a full-strength resident 12B, an unfair fight that would wrongly bench diffusion. Depth-match first, then compare.
## 6. The honest fork + what this doc does NOT claim

The strategy reduces to one belief, and the bake-off supplies the evidence to hold it:

> **Do we believe the native diffusion judge can be made to reach ~90%+ (via N5b + entropy-bound sampler depth), or do we bank a proven native resident judge now and treat diffusion as a rare Stage-3 (or bench it)?**

That is a strategy call. This doc deliberately does **not** pre-decide it -- it builds the measurement that does.

**What this doc does NOT claim (anti-overclaim ledger):**
- it does NOT claim the cascade is the answer -- the cascade is *contingent* on the bake-off showing an accuracy band Stage-3 uniquely owns.
- it does NOT quote the diffusion judge's external-oracle 95.6% as a native capability -- our native number is config-dependent and being measured by the running gate.
- it does NOT claim a throughput number for any stage -- E2B/12B judge-throughput and the cascade's aggregate q/s are TARGETS, measured in the bake-off, not asserted.
- it does NOT claim the section-2 VRAM budget closes -- co-residence of E2B + 12B + diffusion-streaming on 12 GB is itself a measured variable.
- **throughput is premature if accuracy is absent.** Speeding up a weak judge buys fast wrong answers. The *cascade* (route most traffic to the cheap, proven path) is the one move that is robust regardless of how the accuracy question lands -- everything else is gated behind a judge that actually clears the OOD bar.

**Boundary-thesis fit:** this is an *engine/scheduling* optimization (where compute runs, how often), orthogonal to the O_K exact-arithmetic container. It composes with -- does not replace -- the byte-exact substrate, prefix-KV (answer-lossless), and async (byte-exact). None of these levers may touch the final picks.

## 7. Cross-links / receipts

- Bottleneck + the stream-attacking wins: `SP_DG_SCRATCHREUSE` (engine `e31c70d`), `SP_DG_ASYNC` (engine `2a1c830`), memory `project_perf_wholemachine.md`.
- prefix-KV (the per-step work cut, answer-lossless): `G-DG-PREFIXKV-PARITY.log` + `G-DG-PREFIXKV-PROD.log` (engine `tests/fixtures/chat_fullstack/`); design `papers/DESIGN-COLA-DLM-MAPPING.md` section 2.
- Stage-3 resident reservoir: `papers/DESIGN-diffgemma-n5b-reservoir.md` (N5b).
- The judge-architecture history (W_c Stage-1, diffusion Stage-2, the OOD kill-test): `papers/CONTRACT-DIFFJUDGE-OOD-H2H.md`, `papers/CONTRACT-CHAT-FULLSTACK.md`, `papers/RFC-ORGANISM-unified.md`.
- The 12B generative judge baseline (85.7%, Phase 4): `SESSION-HANDOFF.md` Phase-4 record + `project_generative_judge.md`.
- Forward task: T31 (formalize/ship prefix-KV) -> then this bake-off -> then cascade-or-standalone decision.
