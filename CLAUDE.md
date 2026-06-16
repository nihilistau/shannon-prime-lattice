# CLAUDE.md — shannon-prime-lattice

**This is Shannon-Prime. Read `prompt.md` in this repo FIRST — it is the canonical session bootstrap** (what the project is, current state, methodology, the machine, the doc map, how the operator works). This file is the short version.

**Repo role:** umbrella — `papers/` (STATE, Roadmap, the C2/SPEED/XBAR contracts, RFC-XBAR, RUNBOOK), `demos/`, `tests/`, integration glue. The math core is `shannon-prime-system`; the engine is `shannon-prime-system-engine`.

**Current campaign:** XBAR — the auditable latent crossbar (Exec = gemma-4-12B + Memo curator, token-free receipted memory). Public face: `Position_Is_Arithmetic` (receipts-first papers + `LEDGER.md`).

**Current edge (2026-06-16):** XBAR P3 + Phase C CLOSED (KV O(1)); KAIROS time/agency axis CLOSED (KAI-1/1b/1c + crucible + 6h soak GREEN). **KAI-2 latent interrupt CLOSED, BOUNDED** (seam `gemma4_kv_inject` GREEN; static `KAI2Codec` packet missed the pivot — sequence-positional wall). **KAI-3 audio-port CLOSED GREEN** (`gemma4_kv_inject_seq`, N-frame sequence, 8/8 metal pivots) — the BRIDGE into the **GNA "EAR" line** (real audio via the NUC GNA 2.0), a *separate-but-related sibling* of KAIROS sharing the same inject seam, NOT a replacement. NEXT = **GNA Stage 2 (#154)** (real audio front-end), then pivot BACK to XBAR/KAIROS latent memory. Live state: `SESSION-HANDOFF.md` + `CURRENT-STATE-OF-PROJECT.md`.

**Non-negotiables (full detail in `prompt.md` §3/§4/§7):**
- **Receipts-first.** No number without a reproducing command + a `LEDGER.md` row. Bit-exact-when-off. Scope travels with every figure. Gates: parity / deflection(<2%) / poison; telemetry-then-pin; **no silent gate revision — surface upstream**; honest negatives stay attached.
- **Check the code + commits + `git status`/`git fetch` BEFORE trusting memory or a summary.** STATE (`papers/PPT-LAT-STATE.md`) is the PROVEN record — read it, trust it, re-prove only with concrete cause.
- **Gemini is a valued collaborator but we verify** — read the actual paper/code, fix/improve its suggestions, map onto our discrete substrate; never blindly adopt.
- **Drive by default.** Make the obvious call; surface only genuine forks, and recommend. No filler, no closers.
- Anti-contamination: do not copy from `shannon-prime/` or `shannon-prime-engine/`.

**Start:** read `prompt.md` → `papers/PPT-LAT-STATE.md` + `papers/PPT-LAT-Roadmap.md` + active contract