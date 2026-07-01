---
type: index
title: "START HERE — Shannon-Prime navigable map"
description: "The 2-minute orientation: what Shannon-Prime is, the 5 repos, the canonical doc set in reading order, the verified state, the anti-rebuild law, and the forward roadmap. Written 2026-07-01 after a verified ground-truth re-grounding (Phase 0 fleet audit)."
tags: [index, map, onboarding, navigation]
timestamp: 2026-07-01T00:00:00Z
resource: shannon-prime-lattice/papers/START-HERE.md
sp_status: GREEN-LIVE
sp_gate: none
sp_commit: TBD
sp_repro: "doc map; verified against code+commits+gates by the Phase 0 fleet audit 2026-07-01"
---

# START HERE — Shannon-Prime

**What it is.** A fully-local, byte-exact Gemma-4-12B (OK_Q4B) served on a single 12 GB RTX 2060 by `sp-daemon`, with an exact-integer discrete-algebra substrate (the PPT-ARM architecture), O(1) persistent conversation memory, autonomous memory agency, and a cross-family latent transport (Telepathy). Bit-exact is the invariant floor; the value is the envelope (compression · long context · multi-device · speed). See `PPT-LAT-RFC-001-Universal-Discrete-Architecture.md` for the why.

**State in one line (2026-07-01).** The organism is built and live: byte-exact 12B forward, O(1) persistent KV, learned recall (B3-WC + diffusion judge), memory agency (forget/decide/merge), and a parked-but-proven Telepathy bridge — all gated GREEN with receipts. The frontier is cross-family *live* execution, multi-device CRT, speed (WIRE-CPU), and native consolidation. Verified receipts: `VERIFIED-SCOREBOARD.md`. Faithfulness is now closed end-to-end (L5-cosine recall 86.89% + a zero-inference attribute-gate that closes the zero-prior/private-data hole); the generative judge is parked; SWARM/DHT is re-elevated to a primary axis AND now **built end-to-end** — the SP-SWARM mesh (L0 QUIC transport, L1 content addressing, L2 have/want replication, L3 Ed25519 provenance, L4 C2-SimHash discovery) is GREEN across 9 gates, cross-language byte-parity with the Python prototype, and integrated into `sp-daemon` behind a default-off `swarm` feature; remaining work is multi-host deployment only (2026-07-01).

## The 5 repos

| repo | role |
|---|---|
| **shannon-prime-lattice** | umbrella — `papers/` (this doc set), `demos/`, integration glue, the OKFS + MEM-OKF knowledge stores |
| **shannon-prime-system** | the math core — exact-integer primitives (O_K, dual-prime CRT-NTT, Frobenius, exact islands, ARM two-ring KV) + the frozen L1 C ABI |
| **shannon-prime-system-engine** | the engine + `sp-daemon` + CUDA backend + memory agency + the served chat |
| **shannon-prime-harness** | the Python agent harness — tool calling, tiered conversation memory, the agency loop |
| **Position_Is_Arithmetic** | the public face — the receipts-first paper series + `LEDGER.md` |

## Read in this order

1. **`VERIFIED-SCOREBOARD.md`** — what is actually built (commit + gate per claim) and what is open. *Start here for status.*
2. **`PPT-LAT-KEYSTONE.md`** — the detailed current-state map (the organism, end to end).
3. **`PPT-LAT-Roadmap.md`** — the forward plan (the 4 axes below).
4. **`PPT-LAT-RFC-001-Universal-Discrete-Architecture.md`** — the architecture + design rationale.
   - **`PPT-LAT-ADR-002-DECIDE-EXECUTE-SPINE.md`** — the governing law (decide in latent, execute in clean text, never fuse; deciders don't execute).
   - **`PPT-LAT-FINDINGS-LEDGER.md`** — the measured constants / layers / levers / boundaries + per-test ledger.
5. **`PPT-LAT-Theory.md`** (math, read-first for the substrate) + **`PPT-LAT-Systems-v1.md`** (systems narrative).
6. **Reference:** `PPT-LAT-FRAMEWORK-API.md` (call surface) + `PPT-LAT-FRAMEWORK-INDEX.md` (grep index: keyword→location, flags, gates, SHAs). *These supersede the older `PPT-LAT-KEYSTONE-API.md`.*
7. **Interface specs (frozen):** `PPT-LAT-L1-ABI-v0.md`, `PPT-LAT-SP-MODEL-v0.md`.
8. **Build / ops:** `BUILD-ENV-TOOLCHAIN.md` (clean-build chain, clang-cl), `RUNBOOK-cloud-compute.md`.
9. **Live contracts (per-sprint records):** `CONTRACT-CHAT-FULLSTACK.md`, `CONTRACT-BYTEEXACT-forward.md`, `CONTRACT-NIGHTSHIFT-CURATOR.md`.
10. **The frontier specs:** `PPT-LAT-TELEPATHY-LatentBridge-spec.md` + `PPT-LAT-TELEPATHY-Qwen-forward-SCOPE.md`.

Full catalog of everything in `papers/`: `index.md`.

## The anti-rebuild law (non-negotiable — this project has rebuilt the same subsystem 12+ times)

**Before building ANY subsystem, look it up first.** It probably already exists.

```
python tools/okf_mem.py lookup --root memory-okf "<keywords>"
```

Two knowledge systems back this:
- **SP-OKF** — every knowledge doc carries receipts-first frontmatter (`sp_status/sp_gate/sp_commit/sp_repro`). Validate: `python tools/okf_validate.py papers` (gate `G-OKF-CONFORM`). Spec: `SP-OKF-PROFILE.md`.
- **MEM-OKF** — a content-addressed LUT→summary→full anti-rebuild store (`tools/okf_mem.py`, `memory-okf/`). Verify: `python tools/okf_mem.py verify --root memory-okf`. Spec: `MEMORY-OKF-PROFILE.md`. At session end, bank durable "X already exists — don't rebuild" facts.

If a lookup returns a "DO NOT REBUILD" entry, trust it and **wire/port the existing thing**; do not re-implement and do not retrain already-trained weights.

## The forward roadmap — 4 axes

1. **Sovereign Telepathy** — make cross-family delegation fully in-engine (native Qwen transmit). *Next build task: Telepathy v1.*
2. **CRT residue split** — run a model across discrete devices by shipping CRT residues, not float tensors (RFC-001 Trick #1).
3. **Absolute faithfulness** — force the model to obey episodic memory over parametric priors.
4. **Native consolidation** — port the host-Python XBAR tooling + T4 Frobenius of weights down to C/Rust; single-binary deployment.
5. **SP-SWARM / DHT memory mesh (PRIMARY, re-elevated 2026-07-01; L0–L4 BUILT + GREEN + integrated 2026-07-01)** — private, content-addressed, signed replication of MEM-OKF across the operator's nodes (rides byte-exact content addressing + the receipt ledger). Blueprint (*why* + rejected mechanics): `PPT-LAT-DESIGN-SWARM-MEMORY-MESH.md`. Call surface (*how*: `sp_swarm` crate, QUIC/Ed25519 wire, `SP_SWARM_*` flags, gates): `PPT-LAT-MESH-API.md`. **Remaining = multi-host deployment only.**

Detail + open edges: `PPT-LAT-Roadmap.md` and `PPT-LAT-KEYSTONE.md §12`.

## Archived

Historical material lives in `papers/Archived/`: `sessions/` (82 frozen per-cell `SESSION-*` records, provenance only), `superseded/` (older versions whose content is folded into a current doc — e.g. `PPT-LAT-Systems.md` v0, `gate-receipts.md`). Kept for history; **not current state**.
