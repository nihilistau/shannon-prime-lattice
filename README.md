# shannon-prime-lattice

Umbrella project for a decentralized cooperative AI training and inference architecture built on a single math object: the prime-factored coordinate lattice with the dominance order $\preceq_d$ (Friedman-Kruskal homeomorphic embedding) and the CRT cyclotomic ring.

This repo contains:

- `papers/` — theory, systems, and roadmap papers (PPT-LAT-*)
- `prompt.md` — bootstrap / context-priming for working sessions
- `tests/` — integration tests spanning the math core and engine (added Phase 6+)
- `demos/` — phase demos (two-node sharded inference, DHT crawler, end-to-end pilot)

Math core lives in [shannon-prime-system](../shannon-prime-system).
Inference engine lives in [shannon-prime-system-engine](../shannon-prime-system-engine).

Discord: https://discord.gg/rre9XZmvV

## Status

**Phase 0 — bootstrap.** Papers and prompt landed; clean rebuild of math core and engine starts at Phase 1. See `papers/PPT-LAT-Roadmap.md`.

## Reading order

1. `papers/PPT-LAT-Theory.md` — math foundations (the lattice, $\preceq_d$ as wqo, CRT, HRR, the unified role of $\preceq_d$ across the stack)
2. `papers/PPT-LAT-Systems.md` — architecture (six layers, protocols, failure modes, two-token economy)
3. `papers/PPT-LAT-Roadmap.md` — implementation phases (0..12), contracts, tests, offload pattern
4. `prompt.md` — bootstrap prompt for new sessions

## Hard rules of this project

- **Anti-contamination.** No code or designs copied from the older `shannon-prime/` or `shannon-prime-engine/` repos. References to the prior math (KSTE, Friedman sieve, ARM, CRT NTT, Position-as-Arithmetic) are conceptual; implementations are rebuilt from scratch.
- **Contract system.** Each phase has a fixed deliverable list and test gate. No marking a phase complete without all contract items.
- **Offload pattern.** Each session ends with a `papers/SESSION-STATE-lat-<phase>.md` so the next session can pick up cleanly.

## License

AGPL-3.0-or-later. See `LICENSE`. Commercial licensing available — contact the copyright holder.
