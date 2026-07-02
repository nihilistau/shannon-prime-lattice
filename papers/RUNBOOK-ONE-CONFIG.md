---
type: runbook
title: "RUNBOOK — the ONE canonical end-to-end configuration (what loads, what's on, what's off, and why)"
description: "The single operator answer to 'what do I run and which flags are on': the load chain (model → daemon → console), the canonical flag set in three tiers (base-proven / verified-recommended / optional-verified), the explicit OFF list (parked + dead levers), the launcher map, and the one combined gate (G-ONECONFIG-LIVE) that must go GREEN before this config is called proven as a WHOLE. Written by the 2026-07-02 audit (AUDIT-2026-07-02.md); every flag row cites its receipt."
tags: [runbook, config, flags, launcher, one-config, operations]
timestamp: 2026-07-02T00:00:00Z
resource: shannon-prime-lattice/papers/RUNBOOK-ONE-CONFIG.md
sp_status: GREEN-LIVE
sp_gate: "G-ONECONFIG-LIVE v2 GREEN (2026-07-02 run-4): P 54/61 · S 3/3 zero-inference · F 2/2 · C 1 · Q 2/2 · X byte-identical"
sp_commit: "engine 8ae343b"
sp_repro: "run_console_faithful.bat then python _faithful_corpus/oneconfig_run.py; receipt engine tests/fixtures/chat_fullstack/G-ONECONFIG-LIVE.log (+G-DELIVERY-SWEEP.log)"
---

# RUNBOOK — the ONE canonical configuration

**Status: GREEN-LIVE (2026-07-02, engine `8ae343b`).** The combined stack passed `G-ONECONFIG-LIVE` v2 whole (§12): paraphrase recall 54/61 (== the selector ceiling, **0 parametric leaks** under the `systemecho` delivery), SNE zero-inference declines 3/3, hard-foreign 2/2 clean, multi-turn coherent (the recall-drops-history bug found+fixed), QONLY 2/2, byte-identical determinism. `run_console_faithful.bat` boots this exact config. Tier-1 additions since §3 was written: `SP_RECALL_QONLY=1`, `SP_RECALL_L5_PROMPT=systemecho`, `CUBLAS_WORKSPACE_CONFIG=:16:8`.

## 1. What loads (the chain)

```
gemma4-12b-b1.sp-model + .sp-tokenizer   (D:/F/shannon-prime-repos/models/)
  → sp-daemon.exe (tools/sp_daemon/target-wirecuda/release; build: cargo --features wire_cuda_backend[,swarm])
  → CUDA backend on the RTX 2060 (SP_DAEMON_BACKEND=cuda, int8 resident decode)
  → SWA ring (exact-integer, O(1) VRAM) + persistent conversation KV
  → recall stage-chain per turn: INT2 → B3-WC → Jaccard → L5 → judge   (each default-off; stages skip if a prior stage decided; routes.rs:1258/1346/1412/1517)
  → http://127.0.0.1:3000/  (console)   |   harness gateway (/v1/chat) on top
```

Episode store for recall: a registry.jsonl of episode dirs; **L5 recall requires the `ep.l5` sidecar** per episode (`recall.rs:235`) — today only `_faithful_corpus/eps/*` has them.

## 2. Tier 0 — base, proven, always on (the run_console.bat core)

| flag | value | why | receipt |
|---|---|---|---|
| `SP_DAEMON_BACKEND` | `cuda` | resident 12B decode | CONTRACT-CHAT-FULLSTACK |
| `SP_DAEMON_KVDECODE` | `1` | CUDA kv-decode path | G-WIRE-CUDA-DECODE-GEMMA4 32/32 |
| `SP_CUDA_DECODE_INT8` | `1` | int8 resident decode | chat_fullstack arc |
| `SP_DAEMON_KVDECODE_RING_W` | `2048` | SWA ring window (O(1) VRAM; ring==ring-off byte-identical) | B2-ring `7eb7231` |
| `SP_DAEMON_KVDECODE_PMAX` | `20000` | resident ceiling on the 2060 | chat_fullstack |
| `SP_PERSIST_KV` | `1` | O(1) persistent conversation KV (ON==OFF byte-identical) | G-PERSIST-KV-PARITY `d211fd2` |
| `SP_EOT_BIAS` | `4.0` | clean turn-stop | FINDINGS-LEDGER §2 |
| byte-exact chat decode | default-ON per request (`byteexact` absent ⇒ true; routes.rs:411) | build-independent determinism | S1 `58b6c2d` |

Note: `SP_BYTEEXACT` (the full exact-integer *forward*, `69c0588`) is a separate, heavier audit mode — default-off, turn on only for auditability runs.

## 3. Tier 1 — the verified faithfulness edge (default-off in code; ON in the canonical config)

| flag | value | why | receipt |
|---|---|---|---|
| `SP_AUTO_RECALL_DEFAULT` | `1` | served console gets recall without per-request flag (routes.rs:424) | — |
| `SP_RECALL_REGISTRY` | `_faithful_corpus\registry.jsonl` | the episode store with ep.l5 sidecars | G-L5-RECALL-LIVE |
| `SP_RECALL_L5` | `1` | the graduated selector — L5-cosine, 86.89% paraphrase obey | G-L5-RECALL-LIVE `d9099cd` |
| `SP_RECALL_L5_TAU` | `0.30` | below-τ = no recall; silently rejects genuine foreign | G-HARDFOREIGN-L5DIRECT |
| `SP_RECALL_ATTR_GATE` | `1` | zero-prior/private-data shield; zero-inference symbolic decline | G-SNE-ATTRGATE-ZEROINF `fc2e846` |
| `SP_RECALL_ATTR_TAU` | `0.5` | ≥50% salient-word absence ⇒ decline | G-SNE-ATTRGATE |

**Deliberately NOT set with Tier 1:** `SP_B3_WC`. The stage-chain would run W_c *before* L5; W_c+L5 combined is ungated. The FINDINGS rule is "natural facts → L5+text; novel high-entropy needles → W_c+replay" — if you need both live, that's the `G-ONECONFIG-WC` extension gate (§5), not an assumption.

## 4. Tier 2 — optional, individually verified, opt-in per purpose

| flag | enables | receipt | note |
|---|---|---|---|
| `SP_B4_NIGHTSHIFT=1` | live between-turn memory growth | G-CHAT-B4-NIGHTSHIFT-provenance `3ccba61` | criterion-5 closed 2026-07-02 |
| `SP_NIGHTSHIFT_OFFLINE=1` | offline curator (model-call extractor + ablation admit) | G-NIGHTSHIFT-CURATOR `6107f3e` | batch job, not serve-time |
| `SP_SWARM=1` (+ `--features swarm` build, `SP_SWARM_ROOT`, `SP_SWARM_INTERVAL_S`) | MEM-OKF mesh replication | G-SWARM-* (9 gates) | localhost-proven; multi-host open |
| `SP_TELEPATHY_CHAT=1` | routed turns delegate to the qwen coder (clean text, ⟦delegate⟧ markers) | G-TELEPATHY-CHAT-LIVE `50200eb` | coder is CPU ~0.8 tok/s by design |
| `SP_BYTEEXACT=1` | exact-integer 12B forward (audit mode) | G-BYTEEXACT-FORWARD-12B `69c0588` | perf cost; off = byte-identical null floor |
| harness: `SP_GATEWAY_PREWARM=1` | gateway pre-warm | harness `4d02914` | opt-in |

## 5. OFF list — parked and dead (never in the canonical config)

| flag | verdict | receipt |
|---|---|---|
| `SP_B3_JUDGE` / `SP_B3_JUDGE_L5` | **PARKED** — 0 benefit over L5+τ; PASSed 15/18 hard-foreign | G-HARDFOREIGN-JUDGE |
| `SP_RECALL_STRICT` | **DEAD** — over-declines valid matches 0/4 | G-SNE-STRICT-OVERDECLINE |
| `SP_RECALL_JACCARD` | **SUPERSEDED** by L5 as selector (kept as the delivery verifier @0.6 internally) | FINDINGS §2 |
| `SP_B3_DISPOSER` / `SP_B3_TAU_QK` | telemetry/labeler only, not serve-time | B3 arc |
| `SP_DG_*` (diffusion judge cascade) | judge retired from the recall path; prefix-KV decision pending separately | SCOREBOARD "contradictions" §1 |

## 6. Launcher map

| launcher | config | status |
|---|---|---|
| `run_console.bat` | Tier 0 only (RING_W=1024 there — harmonize to 2048) | proven baseline |
| **`run_console_system.bat`** (new, 2026-07-03 — **THE SYSTEM / daily driver**) | Tier 0 + Tier 1 + `SP_B4_NIGHTSHIFT=1` + `SP_NIGHTSHIFT_PERSIST=1` on the **PRODUCTION registry** `_memory_live\registry.jsonl` (starts EMPTY, grows live, persists) | **GREEN — `G-B4-GROW-RECALL-L5`** (grow 4/5 paraphrase-recall from empty + foreign clean + survives restart; engine `934f853`). Required fixes shipped: `mint_live_ep_l5` (grown episodes get `ep.l5` at capture — L5-visible immediately) + the cold-start fix (EMPTY registry now ARMS recall instead of disabling it) |
| `run_console_everything.bat` (2026-07-03) | `run_console_system.bat` + the SPECTEST veto head (`SP_SPECTEST` + `SP_SPECTEST_HEAD`) | **LIVE-PLAY — composition UNGATED as a whole** (each part gated: oneconfig / B4-seal / SPECTEST-V2; V3 safety PASS, promotion pending question-space keys). Recall turns hold the stream by design. Not canonical until the composition earns its own gate. |
| `run_console_faithful.bat` (2026-07-02) | Tier 0 + Tier 1 on the 61-fact TEST corpus | **GATE-ONLY** — never a daily driver: a live chat against the test registry leaked an SNE code (2026-07-03 serve campaign). Use for `G-ONECONFIG-LIVE` re-gates exclusively. **Keep this row + the launcher in lockstep — doc-update law: any flag change to a launcher lands in this table in the same commit.** |
| `run_console_recall.bat` | Tier 0 + W_c (superseded selector) | keep for W_c/needle experiments; not the default |
| `run_console_nightshift.bat` | W_c + B4 (missing SP_PERSIST_KV/SP_EOT_BIAS — fix or retire) | experimental |
| `run_gateway.bat` / `run_agency.bat` | harness on top of a running daemon | unchanged |

## 7. G-ONECONFIG-LIVE — the gate that makes this doc GREEN

One served run under `run_console_faithful.bat`, one log: (1) 5 paraphrase queries against `_faithful_corpus` facts → ≥4 recalls with text-in-context delivery; (2) 3 SNE mismatched-attribute queries → 3 declines each logging "no gemma4 decode"; (3) 2 general-knowledge foreign → NULL (no recall, clean answer); (4) 6-turn conversation with SP_PERSIST_KV → coherent, ring VRAM flat; (5) re-run same seed → byte-identical stream. Receipt → `tests/fixtures/chat_fullstack/G-ONECONFIG-LIVE.log`, then flip this doc's `sp_status` to GREEN and update SCOREBOARD.

Extension (optional): `G-ONECONFIG-WC` = same + `SP_B3_WC` enabled; verifies W_c NULL falls through to L5 without stealing natural-fact queries (routes.rs stage order).

## 8. G-ONECONFIG-LIVE run 1 — RED (2026-07-02, receipt `tests/fixtures/chat_fullstack/G-ONECONFIG-LIVE.log`)

First run of the combined gate on the metal (merged `registry_oneconfig.jsonl` = 61 fct + 20 sne; runner `_faithful_corpus/oneconfig_run.py`): **P 3/5 · S 3/3 (0 spurious, 3/3 "no gemma4 decode") · F 2/2 clean · C 0/1 · X byte-identical → RED.** Not a false start — the gate did its job:

1. **P misses are the known envelope, not a regression.** One selector miss (france para → `fct_019` cos 0.915, a cross-episode grab) + one obedience miss (`fct_004` correctly selected+delivered, model answered parametric "Pacific"). Consistent with 86.89% live; N=5 is too small a slice. **Pre-registered spec revision (v2, surfaced not silent): P runs all 61 paraphrases, threshold ≥80%.**
2. **THE new finding — L5 fires on essentially every turn on a merged registry.** Serve log: hard-foreign "capital of Spain?" matched `fct_015` at cos **0.997** (absent=0.50, delivered); conversational "my designation is…" matched `sne_000`/`sne_007` at cos ~0.9 (absent=**1.00**, delivered). The in-registry cosine *background* is ≥0.9, so τ=0.30 gates nothing in practice (it only rejects out-of-*domain* text). Natural-fact turns survive on model robustness (F 2/2 clean — re-confirming G-HARDFOREIGN); but a conversational turn with an irrelevant fact injected derailed the reply (C: model echoed the system prompt). Also note lexical absence can NOT be the delivery gate: valid paraphrases also score absent=1.00 (why the entity-token guard exists).
3. **Candidate levers for run 2 (in order):** (a) a NULL/margin criterion — gate delivery on the top1−top2 L5 margin or a calibrated in-registry NULL floor, not absolute τ; (b) skip the recall stages entirely on non-interrogative/conversational turns (cheap deterministic pre-check, same spirit as the attr-gate); (c) if needed, per-registry τ calibration. Each needs its own mini-gate before rerunning the combined gate.

`sp_status` stays **DRAFT**. The per-flag capabilities remain individually VERIFIED; what is not yet green is the *composition* — which is precisely what this runbook exists to make honest.

## 9. Run 2 (2026-07-02, levers built + mini-gated) — RED again, and the real root surfaced

Levers from §8 executed receipts-first:

1. **Margin lever = HONEST NEGATIVE** (`G-L5-MARGIN-CALIB`, telemetry-then-pin over 93 labeled queries): correct-para margins (min 0.0011) fully overlap hard-foreign background (max 0.0474) — no τ_m keeps ≥80% while suppressing meaningfully; and SNE canonical margins are 0.0003–0.0007, so ANY margin gate breaks the SNE shield's 100% match recall. `SP_RECALL_L5_MARGIN` pinned **OFF** (code kept: always-on `RECALL-L5-MARGIN` telemetry).
2. **QONLY = GREEN** (`G-RECALL-QONLY-LEXICAL` 188/188 offline; live Q-phase 2/2 QONLY-SKIP, statements answered conversationally, no injection). Pinned **ON** in the launcher.
3. **v2 combined gate: RED** — P **26/61 (42.6%)** vs the pre-registered ≥49/61; S 3/3 (zero-inference) · F 2/2 · Q 2/2 · X byte-identical · C still miss.
4. **Root-cause hunt (the session's real yield): the 86.89% receipt is NOT REPRODUCIBLE.** Receipt-exact serve + the receipt's own harness on today's stack = **40.98%**; rebuilding the exact receipt commit (`a14fee4` src+Cargo.lock) still leaks the canary; model/CUDA-lib/driver/corpus all pinned-unchanged. Selection is stable; **delivery obedience on paraphrases is build/float-fragile** (within-run deterministic, cross-build divergent — the S1 FP-reorder lesson expressed as answer *content*). Scaled prompt (`SP_RECALL_L5_PROMPT=scaled`, now the launcher default) = **63.93%** today vs its own 85.2% receipt. Full matrix + pre-scoped next steps (SP_BYTEEXACT A/B first): engine `tests/fixtures/chat_fullstack/G-L5-OBEY-REPRO.log`. Scoreboard row downgraded (VERIFIED → REGRESSED).

**Consequence for this runbook:** Tier-1 stays honest-DRAFT; the composition gate cannot go GREEN until the obedience fragility is root-caused (byte-exact A/B is step 1). The C-phase miss is downstream of the same delivery issue (irrelevant-fact injection on interrogative conversational turns) — revisit after.

## 10. G-BX-OBEY-AB (2026-07-02) — byte-exact A/B answered: it's a COVERAGE GAP, not a refutation

`SP_BYTEEXACT=1` serve + the same 61-para harness → **61/61 answers byte-identical to the plain serve** (25/61 OBEY both). Reason (code-grounded): the served chat already runs byte-exact per request (routes.rs `byteexact` default-true → `gemma4_kv_byteexact_set` → exact islands + exact decode attention), so the env flag is a no-op there. The remaining float surface on the served path = the **prefill cuBLAS GEMMs** — outside the byte-exact envelope that `G-BYTEEXACT-FORWARD-12B` proved for the one-shot forward. Today's stack is strongly deterministic (4 serves byte-agree); the 07-01 receipt divergence therefore lived in that float-GEMM environment (cuBLAS algo/workspace under different VRAM pressure, or a session env var — the receipt carried no env dump; unrecoverable).

**Thesis sharpened, not refuted:** exact arithmetic IS the fix surface — the envelope just doesn't cover served prefill yet. Pre-scoped next: **N2 (cheap, first)** pin cuBLAS determinism (`CUBLAS_WORKSPACE_CONFIG`, math-mode pinning) and re-gate; **N1 (real)** extend the exact-integer substrate to the kv-path prefill GEMMs (same OK_Q4B/dp4a substrate the decode GEMV already uses); gate = two serves under deliberately different VRAM pressure produce byte-identical 61-para answers. Law extensions: obey receipts carry build SHA + same-day canary + **full SP_* env dump**; "byte-exact ON" claims must name the envelope. Receipt: engine `tests/fixtures/chat_fullstack/G-BX-OBEY-AB.log`.

## 11. N2 executed (2026-07-02) — perturbation matrix all-negative; the 07-01 divergence is BOUNDED-UNIDENTIFIED

Canary matrix (`G-CUBLAS-PIN-CANARY`): baseline / `CUBLAS_WORKSPACE_CONFIG=:16:8` / 768MiB VRAM ballast (free 11.7G→0.08G at load) / `SP_ENGINE_FP16=1` — **all four arms answer identically** ("The Pacific Ocean."), on top of the earlier no-flip arms (BX env 61/61, three rebuilds incl. exact `a14fee4` src+lock). Toolkit drift ruled out (machine PATH pins v13.2; all 5 toolkits + driver predate July). **Today's stack is deterministic under every tested perturbation; the 07-01 obey state is unreachable** — cause bounded-unidentified, un-testable residue = that session's process env + allocator state (no env dump in the receipt; the new law prevents recurrence). cuBLAS pin kept in the launcher as free insurance.

**Forward path (pre-scoped, next session): delivery-format sweep** — the composition's obey ceiling is now a prompt-engineering problem on the honest baseline (plain 40.98% / scaled 63.93%): sandwich fact+instruction, fact-echo framing, system-message delivery, one-shot exemplar; 12-item slice → best → full 61 → ≥80% ⇒ rerun `G-ONECONFIG-LIVE` v2. Each format = one `SP_RECALL_L5_PROMPT` value. **N1** (exact-integer prefill GEMM) after — it buys cross-environment determinism, not obey rate.

## 12. Delivery sweep executed + G-ONECONFIG-LIVE v2 GREEN (2026-07-02, engine `8ae343b`)

Sweep (`G-DELIVERY-SWEEP`, slice-16 → full-61): plain 40.98% < scaled 63.93% < sandwich (10/16) < factecho / system (11/16) < **`systemecho`** (fact as SYSTEM authority + verbatim-echo priming) = **88.52% OBEY, 0 LEAK on the full 61** — beats the unreproducible 07-01 receipt on today's stack. The structure of the win: 54/61 == the L5 selector's top-1 accuracy — **every correctly-selected episode was obeyed**; all 7 misses are selection cross-picks answered faithfully from the wrong fact. **Delivery obedience is solved; the obey ceiling is now the SELECTOR (88.5%).**

Run-3 of the combined gate then exposed a real bug the per-flag gates never could: **recall delivery discarded conversation history** (rebuilt the prompt from the last user message only) — turn-2 questions about turn-1 content were unanswerable on any recall turn, in any prompt variant. Fixed (plumb `orig_msgs`; `systemecho` preserves the conversation). Run-4: **GREEN across all six phases** (P 54/61 · S 3/3 zero-inference declines, 0 spurious · F 2/2 clean even under system-authority delivery of a mismatched fact · C multi-turn coherent · Q 2/2 QONLY-skips · X byte-identical). Receipts (with full env dump per the re-baseline law): engine `tests/fixtures/chat_fullstack/G-DELIVERY-SWEEP.log` + `G-ONECONFIG-LIVE.log`.

**The next ceiling (pre-scoped): the selector.** 7/61 cross-picks; margin lever convicted (§9); candidates = Jaccard+L5 fusion (exact+para in one selector, the original G-L5-RECALL-LIVE follow-up) or a cheap rerank over the L5 top-k shortlist.

## 13. Selector campaign CLOSED (2026-07-02, engine `fc3b0a8`) — every lever measured, ceiling accepted

The full honest ledger on the 7/61 same-template periphrasis cross-picks: **margin gate** CONVICTED (§9); **fact-text key2 + raw-query Jaccard fusion** INERT (`G-SEL-OFFLINE`; correct-in-top-3 = 59/61 was the prize); **judge top-3 rerank** PARKED (`G-SEL-RERANK-61`: fixes 5, breaks 4 — 25% break-rate on fired-correct; run-1 relearned the FINDINGS-#3 position-bias lesson, shuffle added); **query canonicalization** PARKED (`G-SEL-CANON`: three prompt framings, one failure mode — the 12B *answers* the periphrasis question instead of naming/rewriting the subject, and its parametric answer token collides with wrong planted facts, converting priors into selection errors). Two side-lessons banked: raw-argmax side-passes MUST mask the served suppress set (the `<image|>` spam, relearned+fixed in both micro-forward passes), and — meta — the engine's `.gitignore *.log` silently dropped every gate receipt of these sessions until a `git ls-files` check caught it (receipt adds now use `-f` + post-commit verify; the AUDIT §3 blanket-ignore finding biting the receipts themselves).

**Accepted state: L5-cosine top-1 = 54/61 (88.5%) on a deliberately-adversarial periphrasis corpus, composition GREEN with 0 leaks.** Diminishing returns declared — the residual idea (multi-phrasing ep.l5 keys accumulated per episode in live use) is design-noted but CANNOT be gated on this corpus (adding its paras as keys = training on the test set). The audit plan's bigger items outrank further selector work: **#2 artifact hole** (track small load-bearing files + `G-EP-REBUILD-BYTEEXACT`), **N1 exact prefill GEMM** (cross-env determinism), **SWARM multi-host**, **prefix-KV values call**.

## 15. SPEED_NORTHSTAR phase 2 — the operator backlog (2026-07-02, post-GPU-4)

The 35B ladder closed at **337× / 6.073 tok/s** (`G-MOE-GPU4-PINNED`; locality 32.6% killed the LRU). Phase-2 queue, operator-ordered:

1. **Serve it** (in progress): wire the qwen36 hybrid (state decode + GPU dense/experts/streaming) into `sp-daemon` — `/v1/chat` on `qwen36_step`, launcher, serve gate. The SPTB tokenizer parse in the daemon is already generic.
2. **MoE expert-count selection**: runtime top-k override (`SP_MOE_TOPK` / per-request) as a quality↔speed dial; gate = obey/PPL ladder at each k ∈ 1..8.
3. **MoE deliberate GPU/CPU split**: run resident-GPU and CPU expert lanes CONCURRENTLY per layer (host compute is idle while the GPU lane runs today); split policy from measured per-lane throughput.
4. **Redo the 26B diffusion GPU path with the 36B learnings** — it predates the view-DevTensor experts, pinned one-blob staging, one-sync-per-layer flow, and locality telemetry; operator reports it underperforming.
5. **Redo gemma4-12B CPU/GPU serve speed — INVESTIGATE THE DISCREPANCY FIRST**: the operator experiences **~1 tok/s** on the served chat vs the 26.1 tok/s receipt. Suspect #1: the served path's `byteexact` per-request default-ON (exact islands + exact decode attention, CUDA graph declined per B1) — auditability chosen over speed as the *default*; the 26.1 receipt likely measured the graph/float config. Re-baseline the SERVED path with an env dump (the re-baseline law), decide the default with data (e.g. byteexact on the *audit* flag, speed as default, or per-request), then apply any 36B-ladder learnings that transfer.

## 14. The four audit-plan items executed (2026-07-02, engine `8738be7`)

1. **Artifact hole — CLOSED (both halves).** Small load-bearing files tracked (162 files: registries, facts, 81 `ep.l5`, 61 `ep.mf`, harnesses, `wc_deploy.bin`) with verified `.gitignore` exceptions — including `!tests/fixtures/**/*.log`, which structurally fixes the discovered silent receipt-drop (`*.log` blanket rule had been eating every gate receipt; all rescued). The heavy 437MB `ep.k/ep.v` proved **byte-identically regenerable** (`G-EP-REBUILD-BYTEEXACT` GREEN: 12/12 SHA match vs the 07-01 originals across two serve restarts, via `/v1/capture` = `kv::capture_batched`) — disaster recovery = clone + model + one serve + `_seed_faithful.py`.
2. **N1 exact prefill GEMM — RESOLVED-ALREADY-CLOSED (`G-N1-RECON`).** `gemma4_kv_prefill` is a loop of `g4_kv_step` — the identical kernels as decode; under the one-config (`SP_CUDA_DECODE_INT8=1`) every matmul routes through the dp4a **integer** GEMV (cuBLAS is only the non-int8 fallback). The `G-BX-OBEY-AB` "prefill cuBLAS GEMMs" mechanism guess is corrected: no such GEMM executes on the served path. No build item follows.
3. **SWARM multi-host — DEFERRED (operator call):** meaningful only with a real second machine (cloud VM via the RunPod lane, or a LAN device). When available: build `sp-daemon --features swarm` on both, exchange Ed25519 roster entries, `SP_SWARM=1` + `SP_SWARM_ROOT`/`SP_SWARM_INTERVAL_S` per `PPT-LAT-MESH-API.md`, gate = cross-machine `G-SWARM-REPLICATE-CONVERGE` over the real MEM-OKF store.
4. **Prefix-KV default-on — MOOT-WHILE-PARKED.** The operator's challenge was correct: the 1.621× is a **06-24 receipt**, never re-measured, and its only consumer (the diffusion judge) is PARKED off the canonical path; the test binary isn't even built anymore and the full gate costs hours of 26B GPU. Disposition: `SP_DG_PREFIXKV` stays default-off; **if the judge un-parks, the re-baseline law mandates a fresh same-day speed+parity receipt before any promotion decision.**
