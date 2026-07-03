---
type: contract
title: "CONTRACT — Data-Generation + Classifier + Finetuning Framework (reuse CosySim, feed the SP telemetry flywheel)"
description: "The phased build plan for turning the LM-B2 telemetry flywheel into a closed self-improvement loop: seed from public corpora + live telemetry -> labelled MEM-OKF-class data -> QLoRA finetune -> A/B eval -> promote. Every brick lifts a PROVEN CosySim module and re-points its telemetry reader at our content-addressed corpus. Anti-rebuild by construction."
tags: [contract, datagen, finetune, cosysim, telemetry, flywheel, adr-005]
timestamp: 2026-07-03T00:00:00Z
resource: shannon-prime-lattice/papers/CONTRACT-DATAGEN-FINETUNE.md
sp_status: GREEN-LIVE
sp_gate: "G-DF-CONVERT · G-DF-SEED · G-DF-TRAIN-CLOUD · G-DF-EVAL · G-DF-DEPLOY · G-DF-LIVE · G-DF-PARITY · G-DF-AUTOTRAIN"
sp_commit: "engine 6d418a4 / harness bfaa4eb"
sp_repro: "each brick's tests/G-DF-*.log; recon = MEM-OKF 6e70a998"
---

# CONTRACT — Data-Generation + Finetuning Framework

> ★ **PHASE COMPLETE (2026-07-03).** All bricks GREEN. The self-improvement loop is CLOSED and
> AUTONOMOUS: **DF-B1** convert · **DF-B2** seed · **DF-B3** train (Colab T4, adapter on HF) ·
> **DF-B4** eval+promote (0.5B generalizes 20%→83.3%, promoted) · **DF-B6** deploy (harness curator,
> CPU) · **DF-B5** auto-train trigger · plus **G-DF-LIVE** (curator corrects the served store live,
> engine reconcile-on-edit) and **G-DF-PARITY** (the deployed 0.5B **BEATS** the 12B model_classify
> it replaces, 0.83 vs 0.33 vs ground truth — the 12B was the weak classifier all along). Every
> brick lifts a named CosySim module; nothing rebuilt. The active mem_class model is
> `KnackAU/sp-mem-class-adapter` in `datagen/model_registry.json`.

## 0. Why now, and the governing rule

The LM-B2 flywheel is **end-to-end and self-filling** (G-LM-SSE + G-HARNESS-TELEMETRY-SSE +
-AUTOCOLLECT): every delivered turn's decision + outcome is durably, content-addressedly,
redacted-ly collected into a growing corpus. This contract turns that corpus into a **closed
self-improvement loop**: data -> train -> eval -> promote -> better decisions -> more data.

**Governing rule (anti-rebuild):** a COMPLETE pipeline already exists in **CosySim**
(`C:\Files\Models\CosySim\training\`) — recon banked at MEM-OKF `6e70a998`. We **lift** its proven
modules and replace only the CosySim-specific glue (its `engine.*` imports, its game 16-class
taxonomy, its absolute paths). We do NOT rebuild the trainer, the eval gate, or the promote logic.

## 1. The data contract (what flows)

Our corpus (`memory-okf-telemetry/records/<sha16>.json`, index `log.jsonl`):
- **decision record**: `{ts, query, redacted, recall:{entry, class, cos, margin, delivery, decision}}`
- **turn record**: `{ts, kind:"turn", query, redacted, turn:{entry, class, output, out_len, n_out, decode_s, tok_s, obeyed}}`

Join key = `query` (or its hash for secrets). A joined example = `{query -> class, delivery,
decision, output, obeyed, tok_s}`. **Privacy law travels:** private-secret records are already
redacted (query hashed, output `{sha,len}`) — the converter MUST skip `redacted:true` records for
any training set that would expose text (they carry no usable text anyway), and NEVER un-redact.

## 2. The target model (what we finetune FIRST)

**The mem_class classifier.** LM-B3 today classifies a memory with a **12B micro-forward**
(`model_classify`). The first finetune replaces that with a **small QLoRA classifier**
(Qwen2.5-0.5B, CosySim's live `router_v3` base) trained on the telemetry: `query/body -> mem_class`
∈ {private-secret, persona, preference, counterfact, fact, episodic-event}. This is the ideal first
target: small, high-value (kills a 12B call on the idle path), and the labels already exist in
every telemetry record. Later targets: the L5 selector reranker, the delivery-mode policy.

## 3. The bricks (each lifts a CosySim module)

| Brick | Deliverable | Lift from CosySim | Gate |
|---|---|---|---|
| **DF-B1** | **Telemetry -> labelled JSONL converter.** Read our content-addressed corpus, join decision+turn by query, emit Alpaca `{instruction, output}` (instruction=query/body, output=mem_class), filter `redacted`, dedup. | `training/prepare_from_live.py` (swap `_get_metrics_db()` for a reader over our JSONL; keep `merge_datasets`/`get_dataset_stats`) | `G-DF-CONVERT`: corpus -> JSONL, N examples, labels correct, 0 secret text |
| **DF-B2** | **Seed generator (public corpora).** Pull a HF dataset, run each item through the SP classifier path, emit MEM-OKF-class labelled examples to bootstrap before live volume exists. | `training/datasets/generate_router_v3.py` (replace the 16-class game taxonomy with our mem_class set; keep the template->jsonl scaffold) | `G-DF-SEED`: HF dataset -> ≥K labelled examples, class-balanced |
| **DF-B3** | **Finetune runner.** QLoRA train on the JSONL; Windows HF+PEFT fallback + Colab Unsloth notebook. Emits an adapter + GGUF. | `training/finetune_local.py` (`_finetune_unsloth`/`_finetune_hf`, dataset-agnostic) + `training/gemma_router_finetune.ipynb` (Colab) | `G-DF-TRAIN`: tiny LoRA trains on the JSONL -> adapter loads + classifies held-out |
| **DF-B4** | **A/B eval + registry + promote.** Benchmark candidate-vs-base on a held-out classify set; gate policy (NO_REGRESSION / MUST_IMPROVE / PARETO); register + promote the winner. Re-point the model-under-test bridge at SP inference. | `training/evaluation_gate.py` + `training/model_registry.py` + `training/promote_adapter.py` (replace `LMSTaskBridge` with an SP `/v1/chat` caller) | `G-DF-PROMOTE`: candidate vs base -> promote/review/reject decision persisted |
| **DF-B5** | **Auto-train trigger.** When the collected telemetry for a target crosses a count threshold, fire a training run; wire into the harness agency loop (idle-gated) alongside the sink. | `training/auto_train.py` (`check_and_train`, adjust thresholds) | `G-DF-AUTOTRAIN`: threshold crossed -> run fires -> new candidate registered |
| **DF-B6** | **Deploy the finetuned classifier.** Swap LM-B3's `model_classify` 12B micro-forward for the promoted small-classifier adapter behind a flag (default-off = 12B path). Close the loop. | (new glue; consumes DF-B4's registry `get_active`) | `G-DF-DEPLOY`: served refine uses the small classifier; parity vs 12B on the classify corpus; latency win |

## 4. Environment & placement

- **Where it lives:** a new `datagen/` (or `training/`) tier in **shannon-prime-harness** (the harness
  IS cosysim-lineage; the lifted modules belong beside the sink they consume). NOT a new repo.
- **Compute (three lanes, all already in OUR toolbox — ENVIRONMENT.md §2):**
  - **Local** (Beast Canyon, RTX 2060-12GB): HF+PEFT fp16 fallback (Unsloth needs Triton = Linux/
    Colab, silently falls back on Windows). Good for smokes + the tiny mem_class classifier.
  - **Colab (PROTOTYPE):** the `colab` CLI in WSL (`colab run --gpu T4 script.py`; secrets piped;
    always `colab stop`). CU account = "nihilistau" (nihilistcod). CosySim's Unsloth notebook maps
    straight onto this. ~8.5 A100-h cap — mechanism smokes + first real runs.
  - **RunPod (BAKE):** for multi-hour runs — **this lane EXISTS in our toolbox** (correcting the
    recon's "no RunPod in CosySim"): the HF-mediated SSH-free pattern in `papers/RUNBOOK-cloud-
    compute.md` + `_xbar/p2b/` scripts (cheapest-card-that-fits ladder A6000→L40S→…; per-unit
    receipt upload to the private HF dataset `KnackAU/xbar-p2b-run`; verify-then-terminate;
    reconcile `get_pods` twice after any launch error). DF-B3's cloud path REUSES this — wrap the
    generated `train.py` as a p2b unit; NOT net-new. Account = knack112358 (HF PRO + RunPod).
  - Deps: `unsloth transformers peft trl torch datasets`; `COSYSIM_TRAIN_PYTHON` env for the train
    interpreter. Receipts bus = HF (every cloud run streams receipts out per-unit).
- **Deps:** `unsloth transformers peft trl torch datasets`; `COSYSIM_TRAIN_PYTHON` env to point at
  a training env. The lifted modules already `try/except` their `engine.*` imports (degrade cleanly).
- **Privacy:** the redaction law from ADR-005 §3b is load-bearing here — the converter is the choke
  point; it must never emit a secret's text. Gate `G-DF-CONVERT` asserts 0 secret hits.

## 5. Order & exit

Build order: DF-B1 (converter) -> DF-B3 (train, on B1 output) -> DF-B4 (eval/promote) -> DF-B6
(deploy the classifier) -> DF-B2 (seed) + DF-B5 (auto-trigger) to make it standing. DF-B1 is the
first brick — it's small, it's the choke point for privacy, and it unblocks everything downstream.

**Exit criterion (phase done):** a telemetry-triggered run trains a small mem_class classifier on
the live corpus, A/B-beats the 12B micro-forward on the classify gate, is promoted by the registry,
and is deployed behind a flag on the served refine path — the self-improvement loop closed once,
end-to-end, with a receipt at each brick.
