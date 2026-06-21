---
type: index
title: lattice papers/ bundle — progressive-disclosure map
description: "Entry point for the Shannon-Prime lattice papers bundle as an SP-OKF concept directory. Separates the living docs (STATE, Roadmap, the active contracts, the RFCs, the SP-OKF/MEM-OKF profiles, the STATUS-MAP, the fleet brief, ABI, runbook) from the session archive. An agent entering papers/ reads this first, then jumps — it does not read the 8,500-line roadmap top to bottom. Refreshed 2026-06-21 with the unified recall organism RFC, the NIGHTSHIFT curator, MEM-OKF, and the two-strike forward plan."
tags: [okf, index, papers, progressive-disclosure]
timestamp: 2026-06-21T00:00:00Z
resource: shannon-prime-lattice/papers/SP-OKF-PROFILE.md
sp_status: ACTIVE
sp_gate: G-OKF-CONFORM
sp_commit: TBD
sp_repro: python tools/okf_validate.py papers
---

# lattice papers/ bundle — progressive-disclosure map

This directory is the umbrella-repo knowledge bundle, treated as an SP-OKF (Shannon-Prime profile of the Open Knowledge Format) concept directory. Format spec: [SP-OKF-PROFILE.md](SP-OKF-PROFILE.md). Every `*.md` here carries SP-OKF frontmatter (`type` + `title/description/tags/timestamp/resource` + receipts-first `sp_status/sp_gate/sp_commit/sp_repro`).

**You are an agent entering `papers/`. Read this map, then jump.** Do NOT read the 8,500-line roadmap top to bottom. Supersession order for current truth: **STATE > contract run records > the Roadmap's amendment blocks > the Roadmap body.** Bootstrap: `../prompt.md` → [PPT-LAT-STATE.md](PPT-LAT-STATE.md) → the MEM-OKF Tier-0 LUT → the active contract.

Validate with gate **G-OKF-CONFORM**: `python tools/okf_validate.py papers` (run from the lattice repo root).

## 0. Start here (the bootstrap, in order)

1. [PPT-LAT-STATE.md](PPT-LAT-STATE.md) — the PROVEN ledger. *Trust it; re-prove only with concrete cause.* (20th rewrite.)
2. [PPT-LAT-Roadmap.md](PPT-LAT-Roadmap.md) — the forward plan; read the top AGENT-NAVIGATION box (live NEXT = two strikes), not the historical body.
3. [STATUS-MAP-2026-06-21.md](STATUS-MAP-2026-06-21.md) — box-by-box ground-truth (GREEN-LIVE / default-off / design-only). Read when "two memories disagree."
4. [DESIGN-FLEET-OVERHAUL-BRIEF.md](DESIGN-FLEET-OVERHAUL-BRIEF.md) — the honest-tier vocabulary + anti-overclaim rules every doc obeys.
5. [RFC-ORGANISM-unified.md](RFC-ORGANISM-unified.md) — the current synthesis of the whole recall organism.

## 1. Living docs (read these first)

**Project state & plan**
- [PPT-LAT-STATE.md](PPT-LAT-STATE.md) — the proven living record (`project-state`).
- [PPT-LAT-Roadmap.md](PPT-LAT-Roadmap.md) — the forward plan (live NEXT = Strike 1 NIGHTSHIFT criterion-5 → Strike 2 OOD diffusion kill-test) (`roadmap`).
- [STATUS-MAP-2026-06-21.md](STATUS-MAP-2026-06-21.md) — box-by-box honest-tier ground-truth of the recall organism (`project-state`).
- [DESIGN-FLEET-OVERHAUL-BRIEF.md](DESIGN-FLEET-OVERHAUL-BRIEF.md) — canonical grounding + honest-tier vocabulary + anti-overclaim checklist (`design`).
- [ROADMAP-KAIROS.md](ROADMAP-KAIROS.md) — the KAIROS roadmap (`roadmap`).
- [gate-receipts.md](gate-receipts.md) — claim → receipt registry (`index`).

**Knowledge system (auditability discipline)** (`convention`)
- [SP-OKF-PROFILE.md](SP-OKF-PROFILE.md) — the format (Shannon-Prime profile of Google's Open Knowledge Format v0.1 + receipts-first frontmatter); gate `G-OKF-CONFORM` (`tools/okf_validate.py`).
- [MEMORY-OKF-PROFILE.md](MEMORY-OKF-PROFILE.md) — the content-addressed LUT→summary→full anti-rebuild store (one format for agent facts AND latent episodes); **lookup-before-build pre-flight is binding**; gate `G-MEM-OKF-CONFORM`.

**Contracts** (`contract`) — the build/gate contracts:
- [CONTRACT-CHAT-FULLSTACK.md](CONTRACT-CHAT-FULLSTACK.md) — the served 12B chat on the full substrate (GREEN: coherent + byte-exact + O(1) + single-entry + **B3-WC autonomous learned-head recall LIVE**).
- [CONTRACT-NIGHTSHIFT-CURATOR.md](CONTRACT-NIGHTSHIFT-CURATOR.md) — the offline curator (PoUW ledger → ablation oracle → MEM-OKF); gated-GREEN-on-synthetic, criterion-5 live PENDING = **Strike 1**.
- [CONTRACT-BYTEEXACT-forward.md](CONTRACT-BYTEEXACT-forward.md) — the exact-integer byte-exact forward (`SP_BYTEEXACT`, gated-GREEN; external 2-GPU check carried forward).
- [CONTRACT-PPT-LAT-PHASE-5.md](CONTRACT-PPT-LAT-PHASE-5.md) — Phase 5 (the diffusion-judge lane) — settled by **Strike 2**'s OOD kill-test.
- [CONTRACT-PPT-ARM-LAT-INTEGRATION.md](CONTRACT-PPT-ARM-LAT-INTEGRATION.md) — the organism-assembly integration matrix (Built/Theory/Refuted).
- [CONTRACT-C1-sp-model-OK-container.md](CONTRACT-C1-sp-model-OK-container.md), [CONTRACT-C2-ARM-spinor-kv-two-ring.md](CONTRACT-C2-ARM-spinor-kv-two-ring.md), [CONTRACT-C4-C5-C6-decisions.md](CONTRACT-C4-C5-C6-decisions.md)
- [CONTRACT-KAIROS-K0-K1.md](CONTRACT-KAIROS-K0-K1.md), [CONTRACT-SPEED-wire-tok-s.md](CONTRACT-SPEED-wire-tok-s.md)
- XBAR campaign: [P1](CONTRACT-XBAR-P1-inception-probe.md), [P2](CONTRACT-XBAR-P2-pseudo-token.md), [P2b](CONTRACT-XBAR-P2b-adapter.md), [P3](CONTRACT-XBAR-P3-ring-on-exec.md), [R3](CONTRACT-XBAR-R3-consolidation.md), [C1-lite](CONTRACT-XBAR-C1-lite-curator.md), [C2 memo loop](CONTRACT-XBAR-C2-memo-curator-loop.md)

**Interface** (`abi`)
- [PPT-LAT-L1-ABI-v0.md](PPT-LAT-L1-ABI-v0.md) — the frozen L1 ABI (incl. §6b `sp_session_register_kvdecode_backend`).
- [PPT-LAT-SP-MODEL-v0.md](PPT-LAT-SP-MODEL-v0.md) — the `.sp-model` container format (OK_Q4B).

**Design / RFC / theory / spec** (`design`)
- RFCs: [RFC-ORGANISM-unified.md](RFC-ORGANISM-unified.md) — **CURRENT** synthesis (served 12B chat + live W_c RECALL + ablation ADMISSION oracle + NIGHTSHIFT curator + MEM-OKF + PoUW; boundary thesis; diffusion judge = open fork); [RFC-XBAR-auditable-latent-crossbar.md](RFC-XBAR-auditable-latent-crossbar.md) — the predecessor (Exec + Memo sharing Ring 2); [PPT-LAT-RFC-001-Universal-Discrete-Architecture.md](PPT-LAT-RFC-001-Universal-Discrete-Architecture.md) — the north-star preamble.
- Theory/systems: [PPT-LAT-Theory.md](PPT-LAT-Theory.md) (READ FIRST before math work), [PPT-LAT-Systems-v1.md](PPT-LAT-Systems-v1.md) (current synthesis), [PPT-LAT-Systems.md](PPT-LAT-Systems.md) (superseded).
- Diffusion-judge lane (UNPROVEN / in the drawer — gated on **Strike 2**): [DESIGN-diffusion-lane.md](DESIGN-diffusion-lane.md), [DESIGN-diffgemma-native-port.md](DESIGN-diffgemma-native-port.md), [DESIGN-diffgemma-sampler.md](DESIGN-diffgemma-sampler.md), [DESIGN-diffgemma-n5b-reservoir.md](DESIGN-diffgemma-n5b-reservoir.md).
- Other design notes: [DESIGN-tiered-crossbar-latent-terminal.md](DESIGN-tiered-crossbar-latent-terminal.md), [DESIGN-VSA-ring3-holographic.md](DESIGN-VSA-ring3-holographic.md), [MODE_D_DESIGN_DRAFT.md](MODE_D_DESIGN_DRAFT.md).
- Plans/specs/investigations: [PLAN-SPEED-WIRE-CPU-V3-memory-layout.md](PLAN-SPEED-WIRE-CPU-V3-memory-layout.md), [PHASE-4-MEMO-M0-CHOICE.md](PHASE-4-MEMO-M0-CHOICE.md), [GGUF-INVEST-qwen36-35B-A3B.md](GGUF-INVEST-qwen36-35B-A3B.md) (qwen35moe mislabel corrected in STATE §1; GGUF lane dead — safetensors-direct only).

**Operations** (`runbook`)
- [RUNBOOK-cloud-compute.md](RUNBOOK-cloud-compute.md) — RunPod/Colab/HF cloud-run procedure.

**Release** (`session-handoff`)
- [RELEASE-KAIROS-KAI2-KAI3.md](RELEASE-KAIROS-KAI2-KAI3.md)

## 2. Archive (read only for per-cell detail)

`SESSION-CLOSED-*`, `SESSION-STATE-*`, `SESSION-PLAN-*` (all `session-handoff`) are the closed-session record — historical, kept for provenance. They hold per-gate detail and closure receipts but are NOT current state; treat them as archival unless cited from a living doc. Browse by filename prefix:
- `SESSION-CLOSED-lat-*` — closed lattice work items.
- `SESSION-CLOSED-stage-*` — closed stage milestones.
- `SESSION-STATE-lat-*` — captured mid-flight states.
- `SESSION-PLAN-lat-*` — the plans that produced them.

Superseded specs: [PPT-LAT-Systems.md](PPT-LAT-Systems.md) (→ Systems-v1); the GGUF lane (dead). Predecessor XBAR contracts (P1/P2/P2b/C1-lite/C4-C5-C6) sit under Contracts above for provenance.

## 3. Honest tiers (apply when reading any claim here)

- **GREEN-LIVE** — gated GREEN and served by default (the 12B chat; the W_c recall head).
- **gated-GREEN / default-off** — passes its gate, behind an `SP_*` flag, null floor when unset (byte-exact forward; NIGHTSHIFT curator).
- **BUILT / WIRED** — in-tree + primitive-gated, not yet end-to-end gated (PoUW; KAIROS windowing).
- **DESIGN / UNPROVEN** — spec'd or built but the deciding gate is unwon (the native diffusion judge; the 95.6% is the external llama.cpp oracle's, our native single-forward was falsified ~25%).
- **HONEST-NEGATIVE** — measured + refuted, kept on the record (the structure-on-content levers; the 32k NIAH MISS).

## 4. Bundle shape

| group | count (approx) |
|---|---|
| contracts | ~15 |
| living state/roadmap/status-map/brief/abi/runbook/convention/index | ~12 |
| design/rfc/theory/spec | ~18 |
| session archive (CLOSED/STATE/PLAN) + release | ~80 |
| **total .md** | **~125** |
