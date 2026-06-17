# CLAUDE.md — shannon-prime-lattice

**This is Shannon-Prime. Read `prompt.md` in this repo FIRST — it is the canonical session bootstrap** (what the project is, current state, methodology, the machine, the doc map, how the operator works). This file is the short version.

**Repo role:** umbrella — `papers/` (STATE, Roadmap, the C2/SPEED/XBAR contracts, RFC-XBAR, RUNBOOK), `demos/`, `tests/`, integration glue. The math core is `shannon-prime-system`; the engine is `shannon-prime-system-engine`.

**Current campaign:** XBAR — the auditable latent crossbar (Exec = gemma-4-12B + Memo curator, token-free receipted memory). Public face: `Position_Is_Arithmetic` (receipts-first papers + `LEDGER.md`).

**Current edge (2026-06-17):** **Full XBAR stack CLOSED.** XBAR P3 CLOSED (P3.0→P3.4; G-P3-SHARED + G-P3-PPL +1.38%). **C2 Memo curator CLOSED** (Steps 1–3.1 + #222 + G-XBAR-ORGANISM step 1): 256-bit discrete hash resolver (r=256, TAU_BITS=168), G-MEMO-NULL bit-inert off, G-MEMO-LOOP promotes +0.000%/flags +40106.6%; #222 `gemma4_kv_replay` O(1) rewind (G-222 + G-222-WRAP GREEN; engine `b4b037a`/`24071bc`); organism ep_audio [48,114,512] uniform-512, sig self 211/256 margin +79, +1989% foreign-by-design ~0% matched (engine `6600cf4`). **Ring-3 Path A CLOSED** (R3.1–R3.4 GREEN, parameter-free): VSA/HRR NTT bind over Z_q, recall@1=1.0 to N=32, capacity recall@5≥0.90 to N=64, hit 0.000%/miss +8.04%, DUALROUTE + NIGHTSHIFT D=128 seal proves math (max 15 < CAP=32; engine `a64a916`). **GNA EAR CLOSED on physical silicon** (0.877 == emu == FP32). **Caveat:** C2/Ring-3 uses PERIOD=8; true 12B SWA period=6; all gates stand; period-6 rebase is next. **NEXT: period-6 rebase → full G-XBAR-ORGANISM loop** (cue→Ring-3 shortlist→#222 scan→promote). Live state: `SESSION-HANDOFF.md` + `CURRENT-STATE-OF-PROJECT.md`.

**Non-negotiables (full detail in `prompt.md` §3/§4/§7):**
- **Receipts-first.** No number without a reproducing command + a `LEDGER.md` row. Bit-exact-when-off. Scope travels with every figure. Gates: parity / deflection(<2%) / poison; telemetry-then-pin; **no silent gate revision — surface upstream**; honest negatives stay attached.
- **Check the code + commits + `git status`/`git fetch` BEFORE trusting memory or a summary.** STATE (`papers/PPT-LAT-STATE.md`) is the PROVEN record — read it, trust it, re-prove only with concrete cause.
- **Gemini is a valued collaborator but we verify** — read the actual paper/code, fix/improve its suggestions, map onto our discrete substrate; never blindly adopt.
- **Drive by default.** Make the obvious call; surface only genuine forks, and recommend. No filler, no closers.
- Anti-contamination: do not copy from `shannon-prime/` or `shannon-prime-engine/`.

**Start:** read `prompt.md` → `papers/PPT-LAT-STATE.md` + `papers/PPT-LAT-Roadmap.md` + active contract → `MEMORY.md` → check the tree → confirm next falsifiable step → execute, gate, commit/push, bank memory.

**Environment & credentials (added 2026-06-11):** the toolbox — compute lanes (RunPod=bake / Colab=prototype / gws=Google APIs), the three shells and their traps, storage law, account map — lives in **`ENVIRONMENT.md`** (this repo, read it before touching any cloud). Secrets live ONLY in `D:\F\shannon-prime-repos\archive\notes_and_stuff\creds\claude-credentials.txt` (outside all repos; paths-not-values everywhere else; renewal procedures inside). **Where things stand right now** — in-flight runs, the decision queue — is **`SESSION-HANDOFF.md`** (this repo; update it at every session end).
