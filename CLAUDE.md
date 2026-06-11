# CLAUDE.md — shannon-prime-lattice

**This is Shannon-Prime. Read `prompt.md` in this repo FIRST — it is the canonical session bootstrap** (what the project is, current state, methodology, the machine, the doc map, how the operator works). This file is the short version.

**Repo role:** umbrella — `papers/` (STATE, Roadmap, the C2/SPEED/XBAR contracts, RFC-XBAR, RUNBOOK), `demos/`, `tests/`, integration glue. The math core is `shannon-prime-system`; the engine is `shannon-prime-system-engine`.

**Current campaign:** XBAR — the auditable latent crossbar (Exec = gemma-4-12B + Memo curator, token-free receipted memory). Public face: `Position_Is_Arithmetic` (receipts-first papers + `LEDGER.md`).

**Non-negotiables (full detail in `prompt.md` §3/§4/§7):**
- **Receipts-first.** No number without a reproducing command + a `LEDGER.md` row. Bit-exact-when-off. Scope travels with every figure. Gates: parity / deflection(<2%) / poison; telemetry-then-pin; **no silent gate revision — surface upstream**; honest negatives stay attached.
- **Check the code + commits + `git status`/`git fetch` BEFORE trusting memory or a summary.** STATE (`papers/PPT-LAT-STATE.md`) is the PROVEN record — read it, trust it, re-prove only with concrete cause.
- **Gemini is a valued collaborator but we verify** — read the actual paper/code, fix/improve its suggestions, map onto our discrete substrate; never blindly adopt.
- **Drive by default.** Make the obvious call; surface only genuine forks, and recommend. No filler, no closers.
- Anti-contamination: do not copy from `shannon-prime/` or `shannon-prime-engine/`.

**Start:** read `prompt.md` → `papers/PPT-LAT-STATE.md` + `papers/PPT-LAT-Roadmap.md` + active contract → `MEMORY.md` → check the tree → confirm next falsifiable step → execute, gate, commit/push, bank memory.

**Environment & credentials (added 2026-06-11):** the toolbox — compute lanes (RunPod=bake / Colab=prototype / gws=Google APIs), the three shells and their traps, storage law, account map — lives in **`ENVIRONMENT.md`** (this repo, read it before touching any cloud). Secrets live ONLY in `D:\F\shannon-prime-repos\archive\notes_and_stuff\creds\claude-credentials.txt` (outside all repos; paths-not-values everywhere else; renewal procedures inside). **Where things stand right now** — in-flight runs, the decision queue — is **`SESSION-HANDOFF.md`** (this repo; update it at every session end).
