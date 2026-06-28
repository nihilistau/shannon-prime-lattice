---
type: index
title: "STAGING — rebuild execution tracker (stages → gates → artifacts → status)"
description: "The live tracker for executing the 2026-06 rebuild roadmap. One row per stage/gate with its owner repo, the staged artifact, and status (STAGED = scaffold written here / RUNNABLE = passes in any env / METAL = needs the dev box). Updated as gates go green. Companion to ROADMAP-REBUILD-2026-06 and CONTRACT-C4-SPECDECODE-DSPARK."
tags: [index, staging, rebuild, roadmap, gates, tracker]
timestamp: 2026-06-28T00:00:00Z
resource: shannon-prime-lattice/papers/STAGING-REBUILD-INDEX.md
sp_status: DESIGN
sp_gate: G-REGROUND
sp_commit: TBD
sp_repro: "bash staging/specdecode/run_stage0_battery.sh (here-tier); metal-tier listed therein"
---

# STAGING — rebuild execution tracker

> Plan: [ROADMAP-REBUILD-2026-06](ROADMAP-REBUILD-2026-06.md) · Spec-decode contract: [CONTRACT-C4-SPECDECODE-DSPARK](CONTRACT-C4-SPECDECODE-DSPARK.md) · V4 transfer: [DESIGN-DEEPSEEK-V4-TRANSFER](DESIGN-DEEPSEEK-V4-TRANSFER.md) · proven record: [PPT-LAT-STATE](PPT-LAT-STATE.md) · as-built: [PPT-LAT-KEYSTONE](PPT-LAT-KEYSTONE.md).
> **Staging area:** `shannon-prime-lattice/staging/specdecode/` — additive scaffolding; **nothing here is spliced into proven code paths** until the operator applies + compiles + gates it on the dev box (this is the anti-drift rule: no rewriting proven systems in isolation).

## Done this session (staged + the runnable receipts)

| Artifact | Path | State |
|---|---|---|
| Spec-decode contract (C4 addendum) | `papers/CONTRACT-C4-SPECDECODE-DSPARK.md` | STAGED, OKF-GREEN |
| DeepSeek-V4 transfer writeup | `papers/DESIGN-DEEPSEEK-V4-TRANSFER.md` | STAGED, OKF-GREEN |
| Rebuild roadmap | `papers/ROADMAP-REBUILD-2026-06.md` | STAGED, OKF-GREEN |
| Corrected architecture diagram | `papers/diagram-specdecode-corrected.svg` | STAGED |
| **G-PONCELET-CORR kill-test + receipt** | `staging/specdecode/g_poncelet_corr.py` + `.synthetic.log` | **RUNNABLE — GREEN (oracle killed: QR 0.50, φ≈0)** |
| Stage-0 battery (here-tier + metal manifest) | `staging/specdecode/run_stage0_battery.sh` | **RUNNABLE — here-tier 3/3 GREEN** |
| G-SPEC-WIRE spec-decode chat loop | `staging/specdecode/spec_chat_wire.rs.draft` | STAGED (apply+gate on metal) |
| Anti-rebuild facts banked | `memory-okf/` (4 rows) | DONE — `okf_mem verify` GREEN |

## Stage → gate matrix

### Stage 0 — RE-GROUND (`G-REGROUND`)
| Gate | Repo | Status | How |
|---|---|---|---|
| G-OKF-CONFORM | lattice | **GREEN** | `python tools/okf_validate.py papers` (140/140) |
| G-MEM-OKF-CONFORM | lattice | **GREEN** | `okf_mem verify --root memory-okf` |
| Anti-rebuild facts banked | lattice | **DONE** | spec_step / router=Rademacher / Poncelet-killed / byte-exact-proven |
| Forward + organism battery (M_GEMMA4, M_QWEN36, byte-exact, H1–H7, B3-WC, judge) | engine + harness | METAL | `run_stage0_battery.sh` [METAL] tier |
| Engine↔core fork-tax inventory closed | system + engine | TODO | de-dup forwards/dequant/row_bytes/arch-id; one source = shannon-prime-system |

### Stage 1 — WIRE GAP (`G-WIRE-*`, `G-O1-KV`)
| Gate | Repo | Status |
|---|---|---|
| G-WIRE-CUDA / -CPU / -VULKAN (shells call integer + Spinor-KV, bit-exact vs oracle) | engine | DESIGN |
| G-O1-KV (continued-cache decode == fresh re-prefill, VRAM O(1)) | engine | DESIGN (ABI verb exists: `sp_session_register_kvdecode_backend`) |

### Stage 2 — SPEC-DECODE (`G-SPEC-ACCEPT-12B`) — full plan in the C4 contract
| Gate | Repo | Status |
|---|---|---|
| G-SPEC-WIRE (spec_step in /v1/chat; null-floor bit-identical) | engine daemon | DRAFT staged (`spec_chat_wire.rs.draft`) |
| G-SPEC-BASELINE-12B (pin accept-length + tok/s, prompt-lookup floor) | harness | DESIGN (eval harness) |
| **G-PONCELET-CORR (kill the oracle)** | lattice/harness | **GREEN (synthetic)** — live hook pending engine draft-log |
| G-SPEC-ACCEPT-12B (DSpark hybrid draft head beats floor; tok/s > 1.0×) | engine + harness | DESIGN |
| G-SPEC-SCHED (learned acceptance-length scheduler on B3-WC infra) | daemon | DESIGN |
| G-SPEC-ISLAND (cross-island byte-exact draft/verify) | system + daemon | DESIGN → Stage 3 |

### Stage 3 — ENVELOPE (`G-ENVELOPE-TOKS`, `G-DUALGPU-RESIDUE`, `G-CTX-SCALE`)
| Gate | Repo | Status |
|---|---|---|
| G-ENVELOPE-TOKS (beat the bar; attack memory-layout, not ALU) | engine | DESIGN (SP-Q8 39.52 vs llama 52.8 today) |
| G-DUALGPU-RESIDUE (2-device output bit-identical; residue < tensor bytes) + 2-physical-GPU byte-exact check | system + engine | DESIGN (external blocker: 2nd card) |
| G-CTX-SCALE (router fidelity at high budget; close the 32k-MISS-at-64×) | engine | DESIGN |

### Stage 4 — FAITHFULNESS + AGENCY (`G-FAITHFUL`, `G-NIGHTSHIFT-B4-LIVE`, `G-KAIROS-SOAK`)
| Gate | Repo | Status |
|---|---|---|
| G-FAITHFUL (tiered recall survives window-scroll/restart) | harness + daemon | DESIGN |
| G-NIGHTSHIFT-B4-LIVE (criterion 5: live in-distribution capture) | engine | PENDING (criteria 1–4 GREEN) |
| G-KAIROS-SOAK (≥24h) | engine | PENDING (release-held) |

### Stage 5 — COMPRESSION DRAWER (`G-T4-FROB-WEIGHTS`)
| Gate | Repo | Status |
|---|---|---|
| G-T4-FROB-WEIGHTS (Frobenius π^k of model weights, recon-faithful top-1) | system + engine | DESIGN (validated lever, untouched) |
| Native-C XBAR/VSA port | system | DESIGN |

## Do-this-next (ordered)
1. **Run the Stage-0 [METAL] battery** on the dev box (`run_stage0_battery.sh` prints the commands) → confirm the organism is still GREEN from clean. Fix any red before extending.
2. **Close G-PONCELET-CORR live**: have the engine emit `{residue, accepted}` per drafted position during one `SP_MTP=1` run; `python g_poncelet_corr.py --live draft_log.jsonl` → expect ρ≈0; file the negative.
3. **Apply `spec_chat_wire.rs.draft`** into the daemon; gate G-SPEC-WIRE-NULLFLOOR (default-off bit-identical) then G-SPEC-WIRE-PARITY (self-draft).
4. **Stand up G-SPEC-BASELINE-12B** in the harness (accept-length + tok/s) → set the bar `X`.
5. Begin **C4-SPEC-DRAFT** (DSpark hybrid head, trained on regenerated byte-exact features) and **Stage 1 WIRE** in parallel (independent).

## Anti-rebuild facts banked (memory-okf)
- `spec_step` exists in `spec.rs` (PROVEN, 2.67× fewer forwards) — build a draft source, don't rebuild the loop.
- recall router = ±1 Rademacher (rank-16, oracle-perfect); **KSTE falsified as router** — signature only.
- Euler/Poncelet confidence oracle **killed** (G-PONCELET-CORR) — honest negative.
- byte-exact O_K forward (√−163, dual-prime CRT-NTT) is **PROVEN on 12B** — the cross-device spec-decode guarantee.
