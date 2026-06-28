---
type: roadmap
title: "REBUILD ROADMAP (2026-06) — re-ground on the proven foundation, then assemble the full system"
description: "A focused, staged plan to stop the drift (proven systems forgotten / rewritten / used in isolation) and assemble the whole Shannon-Prime organism across all five repos into one running, gated machine. Organizing principle: CONSOLIDATE before EXTEND. Each stage cites what is already PROVEN (reuse, do not rebuild), what changes, what is new, with a falsifiable gate and the repo it lands in."
tags: [roadmap, rebuild, foundation, envelope, spec-decode, wire-gap, okf, five-repos]
timestamp: 2026-06-28T00:00:00Z
resource: shannon-prime-lattice/papers/ROADMAP-REBUILD-2026-06.md
sp_status: DESIGN
sp_gate: G-REGROUND
sp_commit: TBD
sp_repro: "per-stage gates in §3; Stage 0 is the from-clean regression battery"
---

# REBUILD ROADMAP (2026-06)

> **Read first:** [PPT-LAT-KEYSTONE](PPT-LAT-KEYSTONE.md) (as-built map) · [PPT-LAT-STATE](PPT-LAT-STATE.md) (proven record) · [PPT-LAT-Theory](PPT-LAT-Theory.md) (the math) · [RFC-001](PPT-LAT-RFC-001-Universal-Discrete-Architecture.md) (north star).
> **Companion contracts spawned with this roadmap:** [CONTRACT-C4-SPECDECODE](CONTRACT-C4-SPECDECODE-DSPARK.md), [DESIGN-DEEPSEEK-V4-TRANSFER](DESIGN-DEEPSEEK-V4-TRANSFER.md).

## 0. The problem this roadmap fixes

The diagnosis, stated plainly: **we strayed.** Proven subsystems were forgotten, re-derived, or left running in isolation. Two concrete, current examples found while writing this:

- **`spec_step` already exists, proven byte-exact** (engine `spec.rs`; `SP_MTP=1` → 2.67× fewer forwards, `bit_identical_to_greedy=1`) — yet the June thread proposed building a brand-new "DSpark loop" and a (broken) geometric oracle, unaware C4 was already 90% built.
- The **WIRE gap**: the envelope (compression/speed) is *only realized once the backend shells call the integer + Spinor-KV primitives*; several shells still run scalar f32, so the proven primitives sit unused in production.

So the organizing principle is **CONSOLIDATE before EXTEND**: re-ground on the proven foundation and get the *whole* organism running and gated from clean, **before** adding the next capability. The anti-drift discipline (MEM-OKF lookup-before-build, SP-OKF conformance, the STATE ledger as truth) is not overhead here — it is the point.

**The gating rule (do not violate):** gate every stage on **its own** correctness/metric — bit-exact output, the kernel's own throughput, the compressor's own ratio — **never on assembled-system tok/s** (STATE §0). System numbers are system gates, measured only when the envelope is assembled (Stage 3).

## 1. The foundation we build on (PROVEN — reuse, do not rebuild)

| Proven asset | Evidence | Reuse in |
|---|---|---|
| PPT forward bit-exact to llama.cpp (qwen3/2.5, gemma3/4, **qwen35moe 256-expert MoE**) | M_GEMMA4, M_QWEN36 | everything |
| Byte-exact $O_K=\mathbb{Z}[(1+\sqrt{-163})/2]$ forward, dual-prime negacyclic CRT-NTT (q1=1073738753, q2=1073732609, M≈2⁶⁰), 4 exact islands (RMS/softmax/GELU/RoPE-CORDIC) | G-BYTEEXACT-FORWARD-12B (off 4.6665 / on 4.6569) | Stages 1–3 |
| `spec_step` + `sp_session_clone/rewind` + atomic cancel + **T8** (clean $\mathbb{Z}_q$ rollback) | `spec.rs`, `sp_l1.h` 203–206, Theory §11.5, engine `b602ddf` | Stage 2 |
| C1 reducing `.sp-model` (OK_Q4, output-lossless: 17% qwen35moe / 50% Qwen3-0.6B) | C1 CLOSED | Stage 1 |
| C2 two-ring KV: Spinor **~3.5×/f32** (lossy), ±1 Rademacher rank-16 router (oracle-perfect 8/8), Ring-2 **400–1190× effective ctx**, Optane 7.57 µs/read | C2.1/C2.2 | Stages 1, 3 |
| Served organism GREEN-LIVE: chat, learned W_c recall + reject, memory agency (forget/decide/merge), harness H1–H7, tiered memory, KAIROS consolidation, deterministic Jaccard judge | KEYSTONE §9 | Stage 4 |

**Honest negatives that stay attached (do not re-litigate):** NTT-attention is *slower* than fp32 dot at HD≤256 (the win is compression + bandwidth-bypass + integer pipes + multi-device, not NTT-per-op); KSTE is **not** a recall router (adversarially falsified — ±1 Rademacher is); per-vector Spinor is ~3.5×, **not** 120× (the 120×/unlimited headline lives in Ring-2 effective-context); structure-on-content compression (Möbius/entropy/T2-on-weights) is measured-inert.

## 2. The five repos and who owns what

| Repo | Role | This roadmap touches it in |
|---|---|---|
| `shannon-prime-lattice` | umbrella: papers, contracts, roadmap, OKF tooling, MEM-OKF | every stage (the record) |
| `shannon-prime-system` | math core (C): O_K, NTT-CRT, exact islands, ARM two-ring, L1 ABI | Stage 1 (de-fork, wire), Stage 5 |
| `shannon-prime-system-engine` | engine + backends (C/CUDA/Rust) + resident daemon + agency | Stages 1, 2, 3, 4 |
| `shannon-prime-harness` | Python agent: tools, conversation memory, agency loop, eval harness | Stages 2, 4 |
| `Position_Is_Arithmetic` | public face: receipts-first papers + LEDGER | cross-cutting (publish each gate) |

## 3. The stages

### Stage 0 — RE-GROUND (the anti-drift stage) · gate `G-REGROUND`
**Goal:** make the proven record the single source of truth and prove the *whole* organism still runs from a clean checkout.
- **Run it from clean** (KEYSTONE §10): daemon + seed + agency + chat; replay the GREEN-LIVE gate battery (G-BYTEEXACT-FORWARD-12B, G-CHAT-FULLSTACK, G-CHAT-B3-WC-DEPLOY, G-FORGET/DECIDE/MERGE, G-HARNESS-H1…H7). Any red = a regression to fix before anything new.
- **Close the engine↔core fork tax:** inventory the duplicated forwards / dequant / row_bytes / arch-id enums (RFC §10.6); make `shannon-prime-system` the one source, engine vendors it via the submodule. "One object."
- **Bank the anti-rebuild facts:** `okf_mem add` rows for the things that got re-derived ("spec_step exists in spec.rs — don't rebuild", "the recall router is ±1 Rademacher, not KSTE", "byte-exact forward is PROVEN"), so the next session can't re-stray.
- **Gate `G-REGROUND`:** full KEYSTONE gate battery green from clean; fork-tax inventory closed (a list, each item either de-duped or ticketed); `okf_validate.py papers/` GREEN.

### Stage 1 — CLOSE THE WIRE GAP (realize the envelope in production) · gates `G-WIRE-*`, `G-O1-KV`
**Goal:** the envelope only *exists* once the shells call the integer + Spinor-KV primitives. This is the highest-leverage proven-but-unrealized work.
- Wire the CUDA / CPU(AVX2/VNNI) / Vulkan forward shells to the integer + Spinor-KV path (today several call scalar f32). Reuse the proven primitives; this is plumbing, not new math.
- **Persistent O(1) conversation KV** (open edge #1): wire `sp_session_register_kvdecode_backend` so a follow-up turn continues the cache instead of re-prefilling — **byte-identical to a fresh re-prefill**.
- **Gates (per backend, on its OWN metric):** `G-WIRE-CUDA`/`-CPU`/`-VULKAN` = bit-exact output vs the math-core oracle + the kernel's own throughput; `G-O1-KV` = continued-cache decode bit-identical to fresh re-prefill, VRAM flat O(1).

### Stage 2 — SPEC-DECODE (the DSpark integration) · gate `G-SPEC-ACCEPT-12B`
**Goal:** turn the proven-but-dormant spec loop into a real speedup by giving it a high-acceptance draft source. **Full plan: [CONTRACT-C4-SPECDECODE](CONTRACT-C4-SPECDECODE-DSPARK.md).** Order: wire `spec_step` into `/v1/chat` (`G-SPEC-WIRE`, null-floor bit-identical) → stand up the accept-length eval harness + pin the prompt-lookup baseline (`G-SPEC-BASELINE-12B`) → run the **Poncelet kill-test** (`G-PONCELET-CORR`, ρ≈0, file the negative) → train the **DSpark hybrid parallel→sequential draft head** on *regenerated* target features (`G-SPEC-ACCEPT-12B`, tok/s > 1.0× at byte-exact parity) → **learned acceptance-length scheduler** on the B3-WC infra (`G-SPEC-SCHED`). Cross-island spec-decode (`G-SPEC-ISLAND`) hands to Stage 3.

### Stage 3 — THE ENVELOPE GATES (measure the reason-to-exist) · gates `G-ENVELOPE-TOKS`, `G-DUALGPU-RESIDUE`, `G-CTX-SCALE`
**Goal:** the headline [TARGET]s that justify PPT-ARM. Now (and only now) measure assembled-system numbers.
- **tok/s vs the bar** (beat llama.cpp + old SP hier-KV; fair Q8-vs-Q8 is currently ~0.75×, bandwidth-bound — attack memory layout, not ALU): `G-ENVELOPE-TOKS`.
- **Dual-GPU / multi-device residue sharing** (RFC C3 + Trick #1; ship CRT residues, not tensors) and the **byte-exact cross-island speculation** from Stage 2: `G-DUALGPU-RESIDUE` = two-device output bit-identical to monolithic, residue bytes < full-tensor bytes. Includes the external **2-physical-GPU byte-exact check** (open edge #2).
- **Effective context at scale** + router fidelity at high budget (close the 32k-MISS-at-64× honestly — fix the router or state the regime): `G-CTX-SCALE`.

### Stage 4 — FAITHFULNESS + AGENCY DEPTH (harden the organism) · gates `G-FAITHFUL`, `G-NIGHTSHIFT-B4-LIVE`, `G-KAIROS-SOAK`
**Goal:** close the open organism edges so it is robust, not just demonstrable.
- **Deeper faithfulness via reliable tiered recall** (open edge #3): pull conversation facts into MID/LONG tiers so they survive window-scroll/restart — the structural answer to parametric-prior leakage (prompts are the patch).
- **NIGHTSHIFT criterion-5** (live B4, in-distribution on real chat turns — the one PENDING criterion of G-NIGHTSHIFT-CURATOR).
- **KAIROS ≥24h soak** (the held release gate for public paper 09).

### Stage 5 — VALIDATED COMPRESSION LEVERS (the honest drawer) · gate `G-T4-FROB-WEIGHTS`
**Goal:** the proven-but-deferred wins, taken only after the organism is solid.
- **T4 Frobenius π^k of the model weights** (open edge #4): the validated, untouched container-compression lever — distinct from the inert structure-on-content levers. `G-T4-FROB-WEIGHTS` = reconstruction-faithful at top-1, ratio measured.
- **Native-C XBAR/VSA port** (retire the host-Python tooling into `core/`).

## 4. What's proven / changed / new — the one-glance table

| Capability | Proven & reused | Changed (wired/de-forked) | New build |
|---|---|---|---|
| Byte-exact O_K forward | ✓ (12B GREEN) | shells → integer path (S1) | — |
| Spec-decode loop | ✓ spec.rs + T8 + ABI | wire to /v1/chat (S2) | draft head + scheduler (S2) |
| KV envelope | ✓ Spinor 3.5× + Ring-2 400–1190× | realize in shells (S1) | high-budget router fix (S3) |
| Multi-device | Trick #1 substrate, CRT | — | residue-share + cross-island spec (S3) |
| Organism (chat/memory/agency) | ✓ GREEN-LIVE | O(1) KV (S1) | faithfulness via tiers, B4-live (S4) |
| Weight compression | ✓ OK_Q4 reducing | — | T4 Frobenius (S5) |
| C5 MeMo / C6 cyclotomic paper | decision-level | — | stay `[SPECULATIVE]`/deferred until own gates |

## 5. Cross-cutting discipline (every stage)
1. **Anti-rebuild pre-flight (binding):** `python tools/okf_mem.py lookup --root memory-okf <keyword>` + grep the tree *before* building. A new file for an existing capability is a defect.
2. **Receipts-first:** no number without a reproducing command + a STATE/LEDGER row; default-off = byte-identical null floor; honest negatives stay attached.
3. **SP-OKF conformance:** every new knowledge doc carries the frontmatter; run `python tools/okf_validate.py papers` (gate G-OKF-CONFORM) before commit; new `type`s register in SP-OKF-PROFILE §2 first.
4. **Publish the gate:** each green gate → a paper-bite row in `Position_Is_Arithmetic/LEDGER.md`.

## 6. Sequencing rationale
S0 first because you cannot extend a foundation you cannot rebuild from clean. S1 before S2/S3 because spec-decode and the envelope numbers are meaningless on scalar-f32 shells. S2 before S3 because cross-island speculation (S3) needs the draft source (S2). S4/S5 last because they harden/extend an organism that must already be whole. Each stage is independently shippable and independently gated — no stage waits on a system number it cannot hit alone.
