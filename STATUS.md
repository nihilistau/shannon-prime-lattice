# STATUS — shannon-prime-lattice

**Date:** 2026-08-29  
**Class:** `STANDING` — substrate / docs / OKF. **Not absorbed by Kairos.**

This repo is the umbrella for the Shannon-Prime *organism*: papers, contracts, OKF/MEM-OKF, scoreboard, and the map of the math core + engine.

## What stays here (does **not** move to Kairos)

- **SP-SWARM / DHT** — L0 QUIC, L1 content addressing, L2 have/want replication, L3 Ed25519 provenance, L4 C2-SimHash discovery. Mesh of MEM-OKF across nodes.
- **Byte-exact exact-integer forward** — `O_K`, dual-prime CRT-NTT, four exact islands, `SP_BYTEEXACT`.
- **NTT / CRT / Frobenius / ARM / Ring-3 VSA** primitives and their papers.
- **SP-OKF + MEM-OKF** knowledge discipline, KEYSTONE, VERIFIED-SCOREBOARD, ADRs.
- The five-repo organism map (lattice / system / system-engine / harness / Position_Is_Arithmetic).

## What *did* grow a sibling

The **companion harness + durable memory loop** continued in:

- [Kairos](https://github.com/nihilistau/Kairos) (public)
- [shannon-prime-kairos](https://github.com/nihilistau/shannon-prime-kairos) (private working tree)

Those repos orchestrate an OpenAI-compatible local companion. They are **not** a replacement for this arithmetic substrate, the swarm mesh, or the 12B engine.

## Agent rule

If you landed here looking for "the current Shannon-Prime product":

1. **Arithmetic / DHT / byte-exact / papers** → stay. Start at `papers/START-HERE.md`.
2. **Chat companion / night-pass memory / profile-driven daemon** → [Kairos](https://github.com/nihilistau/Kairos).
3. Do not average this tree with Kairos and pick one README as law.
