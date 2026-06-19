---
type: index
title: lattice papers/ bundle — progressive-disclosure map
description: Entry point for the Shannon-Prime lattice papers bundle as an SP-OKF concept directory; separates the living docs (state, roadmap, contracts, ABI, design, runbook) from the session archive.
tags: [okf, index, papers, progressive-disclosure]
timestamp: 2026-06-18T00:00:00Z
resource: shannon-prime-lattice/papers/SP-OKF-PROFILE.md
sp_status: ACTIVE
sp_gate: G-OKF-CONFORM
sp_commit: TBD
sp_repro: python tools/okf_validate.py papers
---

# lattice papers/ bundle

This directory is the umbrella-repo knowledge bundle, treated as an SP-OKF (Shannon-Prime profile of the Open Knowledge Format) concept directory. Format spec: [SP-OKF-PROFILE.md](SP-OKF-PROFILE.md). Every `*.md` here carries SP-OKF frontmatter (`type` + `title/description/tags/timestamp/resource` + receipts-first `sp_status/sp_gate/sp_commit/sp_repro`).

Validate with gate **G-OKF-CONFORM**: `python tools/okf_validate.py papers` (run from the lattice repo root).

## Living docs (read these first)

**Project state & plan**
- [PPT-LAT-STATE.md](PPT-LAT-STATE.md) — the proven living record (`project-state`).
- [PPT-LAT-Roadmap.md](PPT-LAT-Roadmap.md) — phase plan (`roadmap`).
- [ROADMAP-KAIROS.md](ROADMAP-KAIROS.md) — the KAIROS roadmap (`roadmap`).
- [SP-OKF-PROFILE.md](SP-OKF-PROFILE.md) — this knowledge standard (`convention`).
- [gate-receipts.md](gate-receipts.md) — claim → receipt registry (`index`).

**Contracts** (`contract`) — the build/gate contracts:
- [CONTRACT-BYTEEXACT-forward.md](CONTRACT-BYTEEXACT-forward.md) — the byte-exact forward (GREEN on the 12B).
- [CONTRACT-CHAT-FULLSTACK.md](CONTRACT-CHAT-FULLSTACK.md) — the served 12B chat on the full substrate (GREEN: coherent + byte-exact + O(1) + single-entry + **B3-WC autonomous learned-head recall LIVE**).
- [CONTRACT-C1-sp-model-OK-container.md](CONTRACT-C1-sp-model-OK-container.md), [CONTRACT-C2-ARM-spinor-kv-two-ring.md](CONTRACT-C2-ARM-spinor-kv-two-ring.md), [CONTRACT-C4-C5-C6-decisions.md](CONTRACT-C4-C5-C6-decisions.md)
- [CONTRACT-KAIROS-K0-K1.md](CONTRACT-KAIROS-K0-K1.md), [CONTRACT-SPEED-wire-tok-s.md](CONTRACT-SPEED-wire-tok-s.md)
- XBAR campaign: [P1](CONTRACT-XBAR-P1-inception-probe.md), [P2](CONTRACT-XBAR-P2-pseudo-token.md), [P2b](CONTRACT-XBAR-P2b-adapter.md), [P3](CONTRACT-XBAR-P3-ring-on-exec.md), [R3](CONTRACT-XBAR-R3-consolidation.md), [C1-lite](CONTRACT-XBAR-C1-lite-curator.md), [C2 memo loop](CONTRACT-XBAR-C2-memo-curator-loop.md)

**Interface** (`abi`)
- [PPT-LAT-L1-ABI-v0.md](PPT-LAT-L1-ABI-v0.md) — the frozen L1 ABI.

**Design / RFC / theory / spec** (`design`)
- RFCs: [RFC-XBAR-auditable-latent-crossbar.md](RFC-XBAR-auditable-latent-crossbar.md), [PPT-LAT-RFC-001-Universal-Discrete-Architecture.md](PPT-LAT-RFC-001-Universal-Discrete-Architecture.md)
- Theory/systems: [PPT-LAT-Theory.md](PPT-LAT-Theory.md), [PPT-LAT-Systems.md](PPT-LAT-Systems.md), [PPT-LAT-Systems-v1.md](PPT-LAT-Systems-v1.md), [PPT-LAT-SP-MODEL-v0.md](PPT-LAT-SP-MODEL-v0.md), [SP-LAT-FRONTENDS.md](SP-LAT-FRONTENDS.md)
- Design notes: [DESIGN-diffusion-lane.md](DESIGN-diffusion-lane.md), [DESIGN-tiered-crossbar-latent-terminal.md](DESIGN-tiered-crossbar-latent-terminal.md), [DESIGN-VSA-ring3-holographic.md](DESIGN-VSA-ring3-holographic.md), [MODE_D_DESIGN_DRAFT.md](MODE_D_DESIGN_DRAFT.md)
- Plans/specs/investigations: [PLAN-SPEED-WIRE-CPU-V3-memory-layout.md](PLAN-SPEED-WIRE-CPU-V3-memory-layout.md), [PHASE-4-MEMO-M0-CHOICE.md](PHASE-4-MEMO-M0-CHOICE.md), [SPEC-gemma4-tokenizer-dispatch.md](SPEC-gemma4-tokenizer-dispatch.md), [SPEC-qwen35moe-GDN.md](SPEC-qwen35moe-GDN.md), [GGUF-INVEST-qwen36-35B-A3B.md](GGUF-INVEST-qwen36-35B-A3B.md)

**Operations** (`runbook`)
- [RUNBOOK-cloud-compute.md](RUNBOOK-cloud-compute.md) — RunPod/Colab/HF cloud-run procedure.

**Release** (`session-handoff`)
- [RELEASE-KAIROS-KAI2-KAI3.md](RELEASE-KAIROS-KAI2-KAI3.md)

## Archive

`SESSION-CLOSED-*`, `SESSION-STATE-*`, `SESSION-PLAN-*` (all `session-handoff`) are the closed-session record — historical, kept for provenance. They default to `sp_status: ACTIVE` (not individually triaged); treat them as archival unless cited from a living doc. Browse them by filename prefix:
- `SESSION-CLOSED-lat-*` — closed lattice work items.
- `SESSION-CLOSED-stage-*` — closed stage milestones.
- `SESSION-STATE-lat-*` — captured mid-flight states.
- `SESSION-PLAN-lat-*` — the plans that produced them.

## Bundle shape

| group | count (approx) |
|---|---|
| contracts | 13 |
| living state/roadmap/abi/runbook/convention/index | ~9 |
| design/rfc/theory/spec | ~16 |
| session archive (CLOSED/STATE/PLAN) + release | ~80 |
| **total .md** | **120** (incl. this index + gate-receipts) |
