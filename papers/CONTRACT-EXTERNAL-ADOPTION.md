---
type: contract
title: "CONTRACT — External-systems adoption campaign (Waves 1–4, items A1–A5 / B1–B6)"
description: "The build contract governing the adoption of the best ideas from Icarus, OpenSelfRevise, and the latent/looped-reasoning paper cluster into Shannon-Prime, as specified in PPT-LAT-COMPARE-EXTERNAL-SYSTEMS-2026-07. Pre-registers every gate (pass criteria fixed BEFORE the build), the per-item lifecycle (pre-flight → build → gate → receipt → scoreboard), and the null-floor discipline. No item is DONE until its named gate is GREEN with a reproducing command and a committed receipt."
tags: [contract, adoption, campaign, gates, mem-okf, recall, coconut, looped, okf, discipline]
timestamp: 2026-07-08T00:00:00Z
resource: shannon-prime-lattice/papers/CONTRACT-EXTERNAL-ADOPTION.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: "per-item gate commands enumerated in §3"
---

# CONTRACT — External-systems adoption campaign

Governs the implementation of [PPT-LAT-COMPARE-EXTERNAL-SYSTEMS-2026-07](PPT-LAT-COMPARE-EXTERNAL-SYSTEMS-2026-07.md). Read that design doc first; this contract is the build discipline.

## 1. Rules of engagement (binding)

1. **Pre-flight before every item.** `python tools/okf_mem.py lookup --root memory-okf <kw>` + grep the tree. An item that duplicates an existing capability is a DEFECT — extend, do not rebuild. Record the pre-flight in the item's receipt.
2. **Null-floor discipline.** Every runtime change is behind an `SP_*` flag that is a **byte-identical no-op when unset**. Prove it: SHA of the relevant output with the flag off == pre-change.
3. **Pre-registered gate.** Each item's pass criteria (§3) are fixed here BEFORE the build. No silent gate revision; if a criterion proves wrong, amend it here in the same change with a note, never in the dark.
4. **Receipts-first.** A gate result is a committed log under `tests/fixtures/<item>/` (or engine equivalent) with the exact reproducing command. Claims without a receipt are DRAFT, not GREEN.
5. **Beat the incumbent.** Any learned/heuristic replacement for a deployed mechanism must beat it head-to-head on the real metric before it earns wiring (per the deployed-selector rule).
6. **Honest-negative is a valid outcome.** If an item fails its gate, it is recorded HONEST-NEGATIVE with the evidence and parked — not tuned until it passes.
7. **Scoreboard + ledger.** On GREEN, add a row to `VERIFIED-SCOREBOARD.md` (commit + gate) and a line to the project `LEDGER.md`. Register new `SP_*` flags in KEYSTONE §7.

## 2. Per-item lifecycle (the loop we run for each)

`pre-flight → contract-check (this doc) → implement (flagged, null-floor) → write gate harness → run gate (locked clocks for perf/GPU) → receipt → evaluate → GREEN ⇒ scoreboard+ledger ; else HONEST-NEGATIVE+park`.

## 3. Pre-registered gates

### Wave 1 — memory / knowledge (pure-Python + Rust daemon)

**A4 · `G-OKF-DISCOVERY-CLASS`** (pure Python, sandbox).
`okf_mem classify` labels a candidate write RETRIEVAL / SEARCH / DISCOVERY over the live store.
PASS iff on the labelled fixture: (a) an exact-copy of an existing entry ⇒ RETRIEVAL/exact (reject under `--strict`); (b) a light paraphrase of an existing entry ⇒ RETRIEVAL (rebuild, high Jaccard) — NOT DISCOVERY; (c) a genuinely novel entry (terms absent from store) ⇒ DISCOVERY with high residual; (d) a recombination of two existing entries ⇒ SEARCH (mid overlap); (e) a candidate claiming DISCOVERY but with near-zero residual is WARNed as a likely rebuild. Deterministic (same input → same verdict).
Repro: `python tools/tests/test_okf_classify.py`.

**A3 · `G-MEM-MDL`** (pure Python).
Deterministic description-length gate for merge/supersede, model-call preserved as fallback.
PASS iff on the labelled {true-supersede, true-merge, keep-both} set: MDL-first + model-fallback accuracy ≥ model-only accuracy at a measured reduction in model-calls; **a MERGE that would drop a key-term present in A∪B is always rejected (0 fact-loss)**.
Repro: `python tools/tests/test_mem_mdl.py`.

**A5 · `G-OKF-ASK`** (upsert pure Python; ask needs served daemon).
PASS iff: `upsert-block` edits only the region between `SP_GENERATED:<key>` markers (idempotent; human text outside preserved byte-for-byte); `okf_mem ask` answers with only in-bundle `[[addr]]` citations and **declines (0 confabulation) when the answer is absent** from the retrieved set.
Repro: `python tools/tests/test_okf_upsert.py` (block); ask-gate on the served daemon.

**A1 · `G-MEM-LIFECYCLE`** (Rust routes.rs + okf_mem verify; Windows build).
PASS iff: after a supersede the old addr still resolves on disk and is excluded from the live recall set; `SP_MEM_ROLLBACK` restores the last `verified` ancestor and marks intermediates `rolled_back`; `okf_mem verify` rejects an illegal transition (e.g. `verified` at capture, `contradicted→verified`); **null-floor**: registry SHA with `SP_MEM_LIFECYCLE=0` == pre-change.

**A2 · `G-RECALL-TAINTSAFE`** (Rust recall.rs; Windows build; blocked by A1).
PASS iff: a `contradicted`/`superseded` episode is never delivered on the hot path but IS returned under `SP_RECALL_AUDIT=1`; a verified vs unverified near-tie resolves to verified; recall@1 on the 61-fact all-active corpus unchanged; **null-floor** SHA with flag off == pre-change.

### Wave 2 — latent reasoning (engine + GPU + finetune)

**B3 · `G-LOOP-STABLE`** — for any `SP_COCONUT` run, `‖h_t‖₂` stays bounded across the max thought budget; a deliberately unstable config is flagged by the monitor.

**B1 · `G-COCONUT`** — on a held-out multi-hop set, `SP_COCONUT=n (n>0)` beats `n=0` by a pre-registered margin at fixed decode budget; answer tokens after `<eot>` are byte-exact vs the null path for a non-thinking prompt; the thought loop is deterministic (bit-identical thought states run-to-run under locked clocks). **null-floor**: `SP_COCONUT=0` ⇒ chat byte-identical to current.

**B2 · `G-COCONUT-ACT`** — matches/beats fixed-n accuracy at fewer average thoughts; halting deterministic; harder queries provably ponder longer.

### Wave 3 — engine + research

**B4 · `G-KVTILE`** — prefill output bit-identical to the null path (SHA); report measured HBM/DDR-traffic reduction and wall-time delta at locked SM+mem clocks / fresh process / warmup. A null result (already at the memory floor) is an acceptable HONEST-NEGATIVE.

**B5 · `G-DPLR-MEM`** — offline DPLR memory over pooled/content-bearing vectors beats L5-direct+tau head-to-head on the 61-fact + SNE sets before earning any wiring. Contained in an offline harness.

### Wave 4 — model variant (training sprint)

**B6 · `G-RECURSIVE-GEMMA`** — a recursive/looped Gemma variant matches base 12B within a pre-registered quality delta (PPL + recall/faithfulness suite) at measurably lower VRAM and/or higher tok/s; byte-exact/deterministic; every number clock-locked. Step-1 (adjacent-layer cosine-similarity probe) is a cheap go/no-go BEFORE any training.

## 4. Status ledger (this campaign)

| Item | Gate | Status | Receipt |
|---|---|---|---|
| A4 | G-OKF-DISCOVERY-CLASS | ✅ GREEN (7/7 + real-data 193-entry rebuild rejected) | tests/fixtures/okf_classify/G-OKF-DISCOVERY-CLASS.log |
| A3 | G-MEM-MDL | ✅ GREEN (9/9, 0 fact-loss invariant, 50% model-calls saved) | tests/fixtures/mem_mdl/G-MEM-MDL.log |
| A5 | G-OKF-ASK | ⏳ upsert-block GREEN (10/10); `ask` half needs served daemon | tests/fixtures/okf_upsert/G-OKF-UPSERT.log |
| A1 | G-MEM-LIFECYCLE | ✅ GREEN core: Python 11/11 + daemon unit `supersede_marks_not_deletes` PASS + null-floor diff-verified + A2-live confirms superseded is excluded from recall. DEFERRED (small follow-on): `SP_MEM_ROLLBACK` live 1→0 trigger (on-disk lifecycle field already supports the flip). | tests/fixtures/mem_lifecycle/G-MEM-LIFECYCLE-{py,unit}.log |
| A2 | G-RECALL-TAINTSAFE | ✅ GREEN (LIVE, perf daemon, _faithful_corpus): superseded fct_000 excluded from L5 ranking; `SP_RECALL_AUDIT=1` re-includes it; only delta = the flag. Null-floor by data. | tests/fixtures/mem_lifecycle/G-RECALL-TAINTSAFE-live.log |
| B3 | G-LOOP-STABLE | ✅ GREEN (8/8: converging→STABLE ρ̂0.97; exploding→DIVERGENT ρ̂1.33 + Parcae fix). Analyzer ready to wire into B1's thought loop. | tests/fixtures/loop_stability/G-LOOP-STABLE.log |
| B1 | G-COCONUT-ENGINE / -LIFT / -LIFT-PROXY | ✅ ENGINE GREEN (null-floor, determinism, STABLE, coherent; zero-CUDA). ✅ LIFT-PROXY GREEN (Colab G4, GPT-2, synthetic 4-hop): NoCoT 7.1% → Coconut 69.9% OOD (+62.7, ≥60% ✓). ★ KEY FINDING: the win is the CURRICULUM (weights), NOT test-time thoughts — coco self-ablation N=4 vs N=0 = only +2.0 pts. ⏳ LIFT-12B (RunPod bake) = a reasoning-curriculum SFT; SP_COCONUT inference loop is a small add-on. | tests/fixtures/coconut/G-COCONUT-LIFT-PROXY.log ; HF KnackAU/sp-coconut-proxy |
| B2 | G-COCONUT-ACT | PENDING (rides on B1-LIFT — the halting head is trained with the channel) | — |
| B4 | G-B4-FEASIBILITY | ⛔ HONEST-NEGATIVE: prefill attention already fused/on-chip (scores in shared mem, no HBM score matrix) → B4's win pre-captured; bottleneck is weight-GEMM dequant not attention; prod prefill is per-token (no query batch to tile); SWA windows fit L2. Redirect perf to the dp4a weight-dequant lane. | tests/fixtures/b4_probe/G-B4-FEASIBILITY.log |
| B5 | G-DPLR-MEM | ⛔ HONEST-NEGATIVE: on content-bearing (bge) vectors DPLR delta-rule == plain cosine (75.4% vs 77%), both LOSE to L5 ~85%; erase clean but not lossless (perturbs 9-10 neighbors) vs A1's lossless supersede. Redundant for our path. PARKED. | tests/fixtures/dplr/G-DPLR-MEM.log |
| B6 | G-B6-LAYERSIM (step-1 probe) | ⛔ HONEST-NEGATIVE (cheap path): adjacent-layer weight cosine ~0.000 (best gate_proj 0.012) vs ~0.98 loop-viable; no middle band; period-6 global/SWA interleave blocks whole-stack aliasing. Cheap alias-and-finetune REFUTED — a looped Gemma needs heavy retraining. Full G-RECURSIVE-GEMMA PARKED. | tests/fixtures/b6_probe/G-B6-LAYERSIM.log |

Updated as items land. GREEN rows also appear in `VERIFIED-SCOREBOARD.md`.
