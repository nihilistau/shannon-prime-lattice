---
type: runbook
title: "RUNBOOK — the ONE canonical end-to-end configuration (what loads, what's on, what's off, and why)"
description: "The single operator answer to 'what do I run and which flags are on': the load chain (model → daemon → console), the canonical flag set in three tiers (base-proven / verified-recommended / optional-verified), the explicit OFF list (parked + dead levers), the launcher map, and the one combined gate (G-ONECONFIG-LIVE) that must go GREEN before this config is called proven as a WHOLE. Written by the 2026-07-02 audit (AUDIT-2026-07-02.md); every flag row cites its receipt."
tags: [runbook, config, flags, launcher, one-config, operations]
timestamp: 2026-07-02T00:00:00Z
resource: shannon-prime-lattice/papers/RUNBOOK-ONE-CONFIG.md
sp_status: DRAFT
sp_gate: "G-ONECONFIG-LIVE (PENDING — each flag individually gated GREEN; the combined stack is not yet gated as a whole)"
sp_commit: TBD
sp_repro: "run_console_faithful.bat (engine root, added 2026-07-02) then the §5 checklist"
---

# RUNBOOK — the ONE canonical configuration

**Status: DRAFT by policy.** Every flag below is individually gated GREEN (receipts cited). The *combined* stack has never been gated in one run — that is `G-ONECONFIG-LIVE` (§5), the first action of the audit plan. Until it's GREEN, this doc is the *intended* one-config, receipts-first honest.

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
| **`run_console_faithful.bat`** (new, 2026-07-02) | Tier 0 + Tier 1 | **the canonical one — AMBER until G-ONECONFIG-LIVE** |
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
