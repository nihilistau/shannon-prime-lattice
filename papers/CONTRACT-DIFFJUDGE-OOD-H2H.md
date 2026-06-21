---
type: contract
title: "CONTRACT — G-DIFFJUDGE-OOD-H2H: the zero-shot OOD kill-test (W_c vs diffusion judge)"
description: "Pre-registered (falsification stated BEFORE the result): a fair, bounded-K, out-of-distribution head-to-head between the learned latent W_c recall head (holdout-trained) and the zero-shot diffusion judge (llama.cpp 26B oracle), to settle whether the Phase-5 native diffusion lane (incl. N5b) is worth building. Includes the measured W_c OOD floor; the diffusion number is PENDING (oracle baking). Surfaces the architectural finding that W_c is an in-distribution memorizer, not an OOD generalizer."
tags: [diffusion-judge, w_c, ood, kill-test, recall, phase-5, n5b, pre-registration, contract]
timestamp: 2026-06-22T00:00:00Z
resource: shannon-prime-system-engine/tools/xbar_lsh/diffjudge_recall_test.py
sp_status: DESIGN
sp_gate: "G-DIFFJUDGE-OOD-H2H (pre-registered; diffusion leg PENDING)"
sp_commit: TBD
sp_repro: "W_c: python tools/xbar_lsh/wc_bounded_ood.py | diffusion: tools/xbar_lsh/diffjudge_recall_test.py --corpus _needle_corpus_ood --window 8 (receipt tests/fixtures/chat_fullstack/G-DIFFJUDGE-OOD-H2H.log)"
---

# CONTRACT — G-DIFFJUDGE-OOD-H2H (the OOD kill-test)

**Falsification stated up front, before the diffusion number lands.** This settles Strike 2: does the unproven 26B diffusion judge earn the Phase-5 native build (incl. the N5b resident reservoir), or is the lane retired?

## 1. Why the naive comparison is junk (the confound the pre-flight caught)

The cited "W_c 360/361 vs diffusion 95.6%" is **apples-to-oranges**: W_c's 360/361 is **full-registry** (E+1-way argmax over all 91 episodes), the diffusion judge's 95.6% is **bounded-K** (true + K−1 distractors). And the **deployed** W_c trained on all of div, so div needles are *in-distribution* for it. A fair test must (a) use the **same bounded-K task** for both, (b) on **held-out OOD** needles, (c) with the **holdout-trained** W_c (not the deployed memorizer).

## 2. Protocol (same task, same corpus, same metric)

- **Corpus:** `_needle_corpus_ood/` = the 18 held-out div needles (`holdout_eps` from `lsh_Wc_f32_holdout.npz`) + the div foreign queries. Both selectors score the *identical* held-out queries.
- **Task:** bounded-K, **K=8** (true + 7 random distractors, shuffled; foreign → NONE/NULL). Metric: **recall@1** + **foreign-reject**.
- **W_c:** the holdout-trained head (trained on the other 80%, never saw these 18), scored by its own `logsumexp`-mean relevance over the K candidates + s0 (`wc_bounded_ood.py`, pure numpy over `b3_data_div.npz`). **No bake.**
- **Diffusion:** `diffjudge_recall_test.py --corpus _needle_corpus_ood --window 8` → the llama.cpp 26B-A4B Q4_K_M oracle (`llama-diffusion-cli`), zero-shot tag selection. **Bake** (26B CPU-offload on the 2060, multi-hour).

## 3. Measured W_c OOD floor (DONE, receipts-first)

`b3_train_wc_holdout_fast` (seed 0, 20% holdout = 18 needles): **full-registry HOLDOUT top-1 = 8/72 = 11.1%**, foreign-reject 92.0% (true OOD episode median rank 21 of 91). `wc_bounded_ood.py` (50 distractor seeds):

| K | W_c OOD recall@1 | foreign-reject |
|---|---|---|
| 4 | **46.7%** (sd 4.2) | 98.4% |
| 8 | **28.3%** (sd 3.1) | 96.9% |

**Architectural finding (load-bearing):** W_c is an **in-distribution memorizer, not an OOD generalizer** — 99.7% on trained needles, 28–47% bounded on unseen ones, with misses going to *other held-out needles*. Consequence: **NIGHTSHIFT-curated NEW episodes are OOD for the deployed head** — it cannot recall them without a retrain. A zero-shot Stage-2 adjudicator is therefore the *structural* fix for the growing-memory loop, not a luxury. The diffusion judge is being tested for exactly that role (it is inherently bounded — you cannot fit 70 episode texts in a 256-token canvas — so it can only ever be Stage-2, never the Stage-1 router).

## 4. Kill-criterion (pinned BEFORE the diffusion result, against the measured floor)

At **K=8** (W_c = 28.3% recall / 96.9% reject):
- **Diffusion WINS (lane justified, N5b earns its build):** recall@1 **≥ W_c + 10pp** (i.e. ≥ ~38%, and realistically expected ~90%) **AND** foreign-reject **≥ 96.9%**.
- **Diffusion LOSES (Phase-5 native lane incl. N5b RETIRED on the record):** fails either bound.

No silent revision: the diffusion number fills in below when the bake completes; the verdict is whatever the pinned criterion returns.

## 5. RESULT (diffusion leg PENDING)

- W_c OOD K=8: **28.3%** recall / **96.9%** reject. ✅ measured (stands).
- Diffusion OOD K=8 run (2026-06-22, elapsed 3917s, `OOD_DIFF_DONE_0`): harness *printed* `recall@1 17/18 = 94.4% / foreign-reject 49/50 = 98.0%` — **but the run is INVALID (caveat 2 fired).**
- **Verdict: INCONCLUSIVE — oracle MALFUNCTIONED; the 94.4% is a scoring ARTIFACT, NOT a diffusion win.**

### Why the run is invalid (the run-health caveat catching a FALSE POSITIVE)

Every captured model reply is the identical llama.cpp init **warning** `'…W init: embeddings required'` — and a `grep` for the `_TAGPOOL` tag signature (`[consonant][digit][consonant]`) over the whole log returns **ZERO tags**. The judge **never emitted a single tag**. A working judge cannot score 17/18 correct-index with no tag output; the only explanation is a harness fallback leaking the ground-truth into `got` when `parse_tag` finds nothing. So the "94.4% / 98.0% / GATE GREEN" is a **scoring artifact of a malfunctioning oracle**, not a measurement. (Note also the harness's printed "GATE GREEN" is against the OLD G-DIFFJUDGE-1 bar of 85.7%, not this contract's §4 criterion — ignore it.)

**Had this been taken at face value, the project would have committed weeks to N5b on an oracle that judged nothing.** The run-health caveat (pre-registered §5) caught the false positive — the symmetric counterpart to the apples-to-oranges catch that earlier prevented a false *negative*.

### The fix (for the re-run)

The `'embeddings required'` warning is a `llama-diffusion-cli` invocation/build issue (likely needs a different flag set, or the `llama-diffusion-gemma-eval` binary, not `llama-diffusion-cli`). **Next session:** diff this invocation against the one that produced the valid G-DIFFJUDGE-1 95.6% (which DID emit tags), fix the oracle call, re-run, and **confirm real `_TAGPOOL` tags appear in the replies BEFORE applying §4.** Until then the Phase-5 fork stays OPEN (neither justified nor retired) and the W_c-is-a-memorizer finding (the day's real result) stands unaffected.

### Two caveats the next session must apply when reading the result

1. **Statistical power (small N).** The held-out set is 18 needles → ~72 matched queries; a recall proportion at N=72 has a ~±11% 95% CI. The **+10pp** bar is therefore at the noise floor *only if the result is marginal*. The test is decisive **because the expected gap is ~50pp** (W_c 28% vs diffusion's likely ~90%) — far outside the noise. **If diffusion lands marginal (≈35–48%), the honest call is INCONCLUSIVE → re-run with a larger held-out set, not a verdict.** Only a clearly large gap (or a clear miss below ~38%) is callable at this N.
2. **Run-health (the bake itself).** The 26B Q4_K_M (15.65 GB) runs CPU-offloaded on a 12 GB 2060 → very high model-load + first-query latency. As of launch+20min the process was alive but had emitted no query output yet (still loading is the likely cause; a hang looks identical). **Before trusting any number, confirm `_diffjudge_ood.log` actually progressed through queries** (per-query lines appearing, `OOD_DIFF_DONE_0`). If it stalled (no query output after ~1h), the kill-test is blocked on run-health — tune `--ngl`/subsample or run a smaller K/needle batch; do NOT report a partial/empty log as a "loss."
