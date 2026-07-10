---
type: design
title: "ADR-B1-LIFT — 12B reasoning-curriculum SFT (RunPod QLoRA), with Coconut as an optional ingredient"
description: "The design for the deferred B1-LIFT: a well-designed reasoning-curriculum QLoRA finetune of gemma-4-12b on RunPod (RTX 6000, 96GB), reframed by the B1-LIFT proxy finding (the reasoning win lives in the training CURRICULUM/weights, +62 pts, not in the test-time continuous-thought loop, +2 pts). Scopes the goal as a broad reasoning + memory-grounded-multi-hop SFT (valuable for many reasons beyond Coconut), treats the Coconut latent channel as an optional efficiency variant, reuses the GREEN-LIVE datagen/finetune lane (CONTRACT-DATAGEN-FINETUNE) + the p2b RunPod bake, and confronts the real integration question (preserve the byte-exact OK_Q4B serving path). Ends with the OPEN DECISIONS to refine before the run."
tags: [design, adr, sft, qlora, reasoning, coconut, curriculum, runpod, finetune, byte-exact, okf]
timestamp: 2026-07-09T00:00:00Z
resource: shannon-prime-lattice/papers/PPT-LAT-ADR-B1-LIFT-12B-SFT.md
sp_status: DESIGN
sp_gate: "G-COCONUT-LIFT-12B (to be run after the design is refined + the RunPod bake)"
sp_commit: TBD
sp_repro: "TBD — RunPod p2b unit + DF eval/promote"
---

# ADR-B1-LIFT — 12B reasoning-curriculum SFT

Implements the deferred **B1-LIFT** of [CONTRACT-EXTERNAL-ADOPTION](CONTRACT-EXTERNAL-ADOPTION.md). This is a **design to refine** (operator asked to design it better before spending the RunPod hour) — §8 lists the open decisions.

## 0. What the proxy taught us (the reframe)

G-COCONUT-LIFT-PROXY (GPT-2, synthetic 4-hop): NoCoT 7.1% → Coconut 69.9% OOD (+62.7), ceiling full-CoT 89.6%. **But the same trained model with thoughts OFF still scored 67.9% — the test-time continuous-thought loop added only ~+2 pts.** Conclusion: **the reasoning win is baked into the weights by the training CURRICULUM, not delivered by inference-time latent compute.** Therefore B1-LIFT is best scoped not as "make Coconut work on the 12B" but as **a well-designed reasoning-curriculum SFT of the 12B** — of which the Coconut latent channel is an *optional* ingredient, not the point.

## 1. Decision / scope

Run a **QLoRA reasoning SFT of gemma-4-12b-b1** on RunPod (RTX 6000, 96 GB) whose objective is a durable lift in **multi-hop / compositional reasoning** and — our differentiator — **memory-grounded multi-hop** (chaining facts recalled from MEM-OKF). The Coconut latent-thought curriculum is offered as an *optional variant* to compare against a standard CoT-SFT baseline; the primary deliverable is the reasoning lift in the weights. The byte-exact OK_Q4B serving path must survive (§6).

## 2. Value model (drives the priorities)

- **High lever (do well):** the data + curriculum. The proxy's +62 came from here. Spend the design effort on data quality, diversity (the B3-campaign lesson: corpus diversity was the binding constraint), and the memory-grounded angle.
- **Low lever (optional):** the test-time latent loop (SP_COCONUT), +2 pts. Wire it only if the faithful variant (learned projection + `read_logits`) is cheap relative to its value — likely a later, separate step.
- **Table stakes:** don't regress byte-exact determinism, recall/faithfulness (the ONE-CONFIG 88.5% obey), or the memory agency heads.

## 3. Data design (the crux — refine in §8)

Three streams, content-addressed, converted through the DF privacy choke point (redaction law: never emit secret text):
1. **Synthetic multi-hop** (scale the proxy generator to 3–6 hops, larger entity/relation space, compositional-OOD split) — cheap, controllable, the proven signal.
2. **Public reasoning corpora** — GSM8K, ProsQA/ProntoQA (planning-heavy, where latent reasoning wins most), StrategyQA, and a CoT-distilled slice; pulled from HF, class/difficulty-balanced (DF-B2 seed generator scaffold).
3. **Memory-grounded multi-hop (our differentiator)** — synthesize questions whose answer requires chaining ≥2 facts from a MEM-OKF/faithful-corpus-style store, delivered as "Context (authoritative): …" (the served recall format). This teaches the 12B to *reason over recalled memory*, directly compounding A1–A5 + the L5 recall path.

Format per example follows the DF Alpaca shape `{instruction, output}` (+ a `steps` field for the Coconut staging variant). Curriculum = train on full CoT first, then (Coconut variant only) stage-replace reasoning steps with continuous thoughts, masking latents.

## 4. Method

- **Base:** gemma-4-12b-b1, 4-bit QLoRA (bitsandbytes NF4) + LoRA (rank + targets in §8; start r=16, target q/k/v/o + gate/up/down). Base frozen.
- **Objective A (baseline, recommended first):** standard CoT-SFT — question → verbalized steps → answer, label-masked on the answer+steps. This captures the proxy's curriculum value simply.
- **Objective B (optional Coconut variant):** the faithful latent curriculum (post-final-norm hidden → next input residual via a **learned projection** `W:R^3840→R^3840`, the piece the engine's zero-CUDA B1 deferred; staged; mask latents; n+1 sequential forwards). Compare B vs A head-to-head — only ship B if it beats A enough to justify the engine `read_logits` export + projection wiring.
- Trainer: reuse `datagen/cloud/train_colab.py` skeleton (HF-pull data → train → HF-push adapter → STATUS), retargeted as a RunPod p2b unit.

## 5. Compute (RunPod R6000 bake — reuse p2b)

RunPod RTX 6000 (96 GB) via the SSH-free HF-mediated `_xbar/p2b/` pattern (RUNBOOK-cloud-compute): `hf_stage` (train.py + data + bootstrap → private HF dataset) → `launch_pod` (base64 docker_args, env HF_TOKEN + RUNPOD_API_KEY) → `bootstrap.sh` `trap finish EXIT` (upload adapter + terminate on any exit) → `monitor` (backstop). QLoRA of a 12B fits comfortably in 96 GB (4-bit base ~7 GB + LoRA/optim/activations). Budget ~1–2 h, ~$0.33–0.5/h. Always verify-then-terminate; reconcile `get_pods` twice after any launch error. Creds by path only (HF token file, `~/.runpod/config.toml`).

## 6. Integration — preserve the byte-exact serving path (real open problem)

The served daemon runs the **OK_Q4B `.sp-model`** byte-exact. A trained QLoRA adapter must reach that path without breaking determinism. Two routes:
- **(i) merge + re-quantize (recommended):** merge LoRA into the bf16 base → run the existing GGUF→reducing→`.sp-model` OK_Q4B pipeline → a new `gemma4-12b-b1-reason.sp-model`, served exactly like today (byte-exact preserved by construction, selectable variant, canonical untouched). Gate: PPL + recall/faithfulness suite on the new model.
- **(ii) runtime LoRA in the CUDA decode:** apply LoRA deltas at decode — new kernel path, harder, risks the byte-exact envelope. Not recommended for v1.
- **Coconut latent (only if Objective B ships):** additionally add the `read_logits` D2H export (the faithful first-token-from-thought-logits the engine deferred) + host the learned projection `W` — an engine follow-on, gated separately.

## 7. Gate — G-COCONUT-LIFT-12B (pre-registered shape)

PASS iff, on held-out reasoning sets (multi-hop OOD + a public slice) the SFT'd 12B beats base by a pre-registered margin **AND** the DF promote gate (MUST_IMPROVE, margin) fires, **AND** no regression on the recall/faithfulness ONE-CONFIG suite, **AND** the re-quantized `.sp-model` is byte-exact/deterministic (SP_BYTEEXACT A/B). Coconut-variant B additionally must beat CoT-baseline A to earn its engine wiring. Eval reuses DF-B4 (`eval_colab.py` + `promote_run.py` + `model_registry.py`, register `model_type="reason-sft"`).

## 8. OPEN DECISIONS (refine before the run — the operator's "design it better")

1. **Data mix + sources** — weighting of synthetic vs public vs memory-grounded; how much to lean into memory-grounded-multi-hop (our unique value); which public sets; how much CoT-distillation and from where.
2. **Objective** — CoT-SFT (A) only, or also the Coconut latent variant (B)? (Proxy says A likely captures most value; B is the research bet.)
3. **LoRA config** — rank, target modules, learning rate, epochs; QLoRA vs a small full-FT.
4. **Wire the test-time latent loop at all?** — given +2 pts, maybe ship only the reasoning-SFT'd weights and leave SP_COCONUT as the (already-GREEN) engine mechanism, un-wired to the answer-logits path.
5. **Integration** — confirm route (i) merge+requant; verify the GGUF→.sp-model reduce pipeline round-trips a LoRA-merged model losslessly.
6. **Eval sets** — the held-out reasoning benchmark(s) + the no-regress recall/faithfulness suite + the byte-exact A/B.
7. **Scope creep guard** — this SFT could grow into a general instruction/reasoning tune; decide the boundary for v1.

## 10. DECISIONS (finalized 2026-07-09 — operator-delegated)

- **Integration route:** (i) **merge + re-quantize** → new selectable `gemma4-12b-b1-reason.sp-model` (canonical untouched). CONFIRMED.
- **Objective:** **A (CoT-SFT)** for this bake. The Coconut latent variant (B) is a SEPARATE later run (proxy: +2 pts test-time, not worth the engine `read_logits`+projection wiring for v1). SP_COCONUT stays the already-GREEN engine mechanism, un-wired to the logits path for now.
- **Data mix (≈10–14k examples; MEMORY-GROUNDED IS THE PRIORITY LANE), mirroring our REAL surfaces (per the surface survey):**
  - **~40% memory-grounded multi-hop (PRIORITY):** reason over `Context (authoritative…): {2–4 facts}` + the faithfulness system prompt → short faithful answer; **~25% of these are attribute-absent → the zero-inference decline** ("I do not have that information." / "I have a record for that entity, but it does not include that specific detail."). Teaches chain-facts + obey/decline faithfully. Also the multi-entry single-letter/`TAG=|EVIDENCE=` selector.
  - **~22% public + synthetic reasoning:** scaled synthetic multi-hop (3–6 hop, compositional-OOD) + a GSM8K CoT slice (generalization).
  - **~12% tool-calling in OUR format:** ```tool_code``` / ```tool_output``` round-trips (calculate/run_python + `load_tools` tiered), "answer using ONLY tool_output".
  - **~8% memory write/capture intents:** store/remember/forget → confirmations + mem_class behavior.
  - **~10% Hermes (`lambda/hermes-agent-reasoning-traces`, Apache-2.0):** subsampled (shorter/high-signal, prefer kimi deep-think), reformatted to our `tool_code` surface, `<think>`→plain reasoning lead-in (no tag surface change).
  - **~8% persona-consistent** answering wrapped with the Shannon-Prime system voice (reinforce the persona, not a separate skill).
  - Privacy: all through the DF redaction choke point — never emit secret text.
- **Config (generous — "give it a good chance"; SFT phase-change aware):** QLoRA 4-bit NF4; **LoRA r=64, α=128, dropout 0.05, target ALL linear (q,k,v,o,gate,up,down)**; LR 2e-4 cosine + warmup; **4–6 epochs with per-epoch held-out reasoning eval to SEE the grok/phase transition** (don't undertrain); seq 2048–4096; grad-accum to eff-batch ~32; bf16. Base frozen.
- **Compute:** RunPod, **cheapest-that-fits at launch** (`rp_plan.py` ladder — NOT hardcoded RTX 6000; the price fluctuates). Verify-then-terminate. Budget ~2–4 h.
- **Base on HF:** the SFT base = the bf16 the `.sp-model` derives from (`D:/Files/Models/Gemma4/gemma-4-12b-bucket`); upload once to a private HF repo so the pod can pull it.

## 9. Anti-rebuild pre-flight

Reuse: the DF framework (`datagen/` train/eval/promote/registry, `CONTRACT-DATAGEN-FINETUNE` GREEN-LIVE), the p2b RunPod lane (`_xbar/p2b/`), the OK_Q4B `.sp-model` reduce pipeline, the proxy datagen/trainer (`datagen/coconut/`, now committed). New = the scaled reasoning + memory-grounded curriculum, and (only for Objective B) the learned projection + engine `read_logits` export. No new repo, no new trainer/eval — retarget the proven modules.
