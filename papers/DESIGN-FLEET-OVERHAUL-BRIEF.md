---
type: design
title: "FLEET OVERHAUL BRIEF — canonical grounding for the 4-repo doc rewrite (2026-06-21)"
description: "The single source of truth every README/AGENTS/docs-rewrite subagent must work from. Encodes the TRUE current state with honest tiers, the OKFS/SP-OKF + MEM-OKF knowledge system, the recall-organism architecture, per-repo roles + deliverables, and the binding anti-overclaim rules. Public READMEs render on GitHub — every claim must be verified against PPT-LAT-STATE.md + git log; no invented results, no stale paths, no GREEN-LIVE where it is gated-GREEN."
tags: [overhaul, readme, agents, okfs, sp-okf, mem-okf, fleet, grounding, anti-overclaim]
timestamp: 2026-06-21T00:00:00Z
resource: shannon-prime-lattice/papers/PPT-LAT-STATE.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: "verify every claim: git -C <repo> log --oneline -20; read papers/PPT-LAT-STATE.md + STATUS-MAP-2026-06-21.md"
---

# FLEET OVERHAUL BRIEF

**Audience:** the subagents rewriting `README.md` / `AGENTS.md` / docs on each of the 4 repos. **Read this fully, then read your repo's `PPT-LAT-STATE.md` (or equivalent) + `git log`, and VERIFY before you write a single claim.** These READMEs are public on GitHub.

## 0. The binding rules (non-negotiable)

1. **No overclaim. Verify every factual claim against `papers/PPT-LAT-STATE.md` + `git log --oneline` + the actual tree.** If you can't cite a commit/gate/file for a claim, cut it.
2. **Honest tiers, exact words.** Use this vocabulary and never inflate:
   - **GREEN-LIVE** — gated GREEN AND active on the served path by default (e.g. the 12B chat with W_c recall).
   - **gated-GREEN / default-off** — passes its gate but is behind an `SP_*` flag (null floor when unset). *NOT* "live." (e.g. the NIGHTSHIFT curator, byte-exact forward.)
   - **BUILT / WIRED** — in-tree + compiles + primitive-gated, not yet end-to-end gated.
   - **DESIGN** — spec'd, unbuilt. **HONEST-NEGATIVE** — measured + refuted, kept on the record.
3. **No stale paths or dead results.** Remove/repoint anything that no longer exists. The GGUF lane is dead (safetensors-direct only). The 32k NIAH MISSed (honest negative — keep it). Diffusion judge is UNPROVEN (oracle number is llama.cpp's, not ours).
4. **Receipts-first.** Every headline number carries its gate + commit. No number without a reproducing path.
5. **OKF frontmatter** on every knowledge `.md` you create/touch (`type/title/description/tags/timestamp/resource` + `sp_status/sp_gate/sp_commit/sp_repro`). Run `python tools/okf_validate.py <bundle>` before committing (lattice tool; engine/system can reference it).
6. **GitHub-friendly:** Mermaid or ASCII diagrams, a clear top badge line, a navigation section. Human-readable AND agent-navigable.

## 1. The TRUE current state (verify, then summarize — do not copy blind)

**The project:** Shannon-Prime — a byte-exact, exact-integer (O_K = Z[(1+√−163)/2], dual-prime CRT-NTT) substrate running a frozen **Gemma-4-12B** (OK_Q4B) on one **RTX 2060 12GB**, with a token-free, receipted conversational-memory organism (XBAR). Public face: `Position_Is_Arithmetic` (receipts-first papers + `LEDGER.md`).

**GREEN-LIVE (served by default):**
- **Coherent + byte-exact + O(1)-context 12B chat** on a single latent entry point (`gemma4_kv_inject_seq`). `CONTRACT-CHAT-FULLSTACK`, engine →`7eb7231`.
- **Autonomous episodic recall via the learned latent W_c head** (`SP_B3_WC`, `recall.rs`/`routes.rs`). `G-CHAT-B3-WC-DEPLOY`/`-DIV2` (360/361 recall + 50/50 foreign-reject), engine `edc8079`.

**gated-GREEN / default-off (passes its gate, behind a flag):**
- **Byte-exact exact-integer forward** (`SP_BYTEEXACT`): `G-BYTEEXACT-FORWARD-12B` (OFF 4.6665 byte-identical null floor / ON 4.6569 parity / run-to-run bit-identical). = exact arithmetic / cross-machine determinism / AUDITABILITY, **NOT compression**. Engine `69c0588` + math-core `d9d96f3`.
- **NIGHTSHIFT offline curator** (`run_kairos_curator`, `SP_NIGHTSHIFT_OFFLINE`): 12B model-call `ep.secret` extractor → causal-ablation admit (TAU=−8) → MEM-OKF emit. **`G-NIGHTSHIFT-CURATOR` criteria 1-4 GREEN on the SYNTHETIC gate** (novel "8-FALCON-7729" collapse −33.59 ACCEPT / parametric "Paris" 0.00 REJECT). **Criterion 5 (B4 distributional/provenance fix) CLOSED live** (commit `3ccba61`; `G-CHAT-B4-NIGHTSHIFT-provenance.log`: live==curated 9.858, novel in-band + foreign-reject; residual novel-instance recall now on the L5-cosine hot path). Engine `9ad7ede`→`9ee4668`→`6107f3e`→`3ccba61`.
- **XBAR memory on the exact-integer O_K substrate** (Ring-3 bind, Frobenius Ring-2 store, organism loop). `G-R3-BIND-on-O_K`, `G-R2-FROB`, `G-XBAR-ORGANISM-FULL`.

**The recall-organism architecture (fixed + recorded):** the **causal ablation oracle (TAU=−8) is the official ADMISSION gate** (teacher-forced knockout; novel memory collapses ≪ −8, parametric ≈ 0); the **latent W_c head** (`SP_B3_WC`) is the **live RECALL selector**; the **native Diffusion Judge is UNPROVEN, in the drawer** pending an OOD kill-test (it must beat W_c head-to-head before earning N5b — its 95.6% is the *external* llama.cpp oracle's number, not ours; our native single-forward was falsified ~25%).

**PROVEN / citable headline numbers:** gemma-4-12B **26.1 tok/s @ wikitext PPL 5.12 on one RTX 2060-12GB** (LEDGER 06-R10); the gemma-4 **GGUF ecosystem ships broken weights** (gold forward PPL 4.68 vs GGUF 192–506) → safetensors-direct is the only trusted path; two-ring **910× resident-KV shrink @32k, 8× sparsification @ +0.69% PPL** (512-proven; the **32k NIAH MISSed** — honest negative).

## 2. The new knowledge system (the headline shift to document everywhere)

- **SP-OKF** (`papers/SP-OKF-PROFILE.md`) — Shannon-Prime's profile of Google's **Open Knowledge Format v0.1**: every knowledge `.md` is a concept with `type` + the receipts-first frontmatter; cross-linked; validated by `tools/okf_validate.py` (gate `G-OKF-CONFORM`).
- **MEM-OKF** (`papers/MEMORY-OKF-PROFILE.md`, `tools/okf_mem.py`, `memory-okf/`) — the **content-addressed, tiered (LUT→summary→full) anti-rebuild memory**, addressed by sha256 (text) / C2-LSH-sig (latent episode). One format for agent facts AND XBAR/NIGHTSHIFT episodes; curated by NIGHTSHIFT, receipted by PoUW. **The `okf_mem lookup` pre-flight is binding: before building anything, look it up — a new file for an existing capability is a defect (this project has rebuilt the same subsystems 20+ times).**
- **HISTORY (this overhaul)** — a hashed, MEM-OKF-style tiered commit-history doc per repo (`tools/okf_history.py` → `HISTORY.md`): Tier-0 LUT of milestones (the git hash IS the content address), dig deeper via `git show <hash>`. Reference it in every README + AGENTS.md.
- **AGENTS.md (this overhaul)** — per-repo agent-navigation doc: how an agent should enter, what to read first (prompt.md → STATE → MEM-OKF LUT → HISTORY → active contract), the pre-flight, the non-negotiables. Human + agent readable.

## 3. Per-repo roles + deliverables

Each subagent: (a) READMEs current + honest + diagrammed; (b) `AGENTS.md`; (c) `HISTORY.md` (via `okf_history.py`); (d) align that repo's knowledge docs to OKF frontmatter + remove stale paths; (e) `okf_validate` where applicable; (f) commit + push; (g) report back what changed (files + key claims, with the commits you cited).

- **`shannon-prime-lattice`** (umbrella): papers/STATE/roadmap/contracts/RFC + the OKFS/MEM-OKF tooling. README = the project front door (what it is, the organism, the knowledge system, navigation). This repo OWNS `okf_validate.py`/`okf_mem.py`/`okf_history.py`.
- **`shannon-prime-system-engine`** (the inference engine): CUDA/CPU backends, `sp_transcode`, `sp_daemon` (the served chat + W_c recall + NIGHTSHIFT curator), the gates. README = the engine surfaces + how to build/run + current gated capabilities (honest tiers).
- **`shannon-prime-system`** (the math core): the clean O_K/CRT-NTT/exact-islands/ARM core, frozen L1 ABI. README = the math substrate + the ABI + what's frozen.
- **`Position_Is_Arithmetic`** (public papers): the receipts-first paper series + `LEDGER.md`. README = the public narrative + the papers index + the honest headline results (incl. the 32k MISS). Keep public claims conservative.

## 4. Anti-overclaim checklist (run before committing any README)

- [ ] Every gate/number cites a commit or `LEDGER.md`/STATE row.
- [ ] No "GREEN-LIVE" on anything default-off (curator, byte-exact = gated-GREEN).
- [ ] Diffusion judge = UNPROVEN/in-drawer; 95.6% labeled as the external oracle's.
- [ ] No dead paths (GGUF lane, removed dirs); honest negatives kept (32k MISS).
- [ ] OKF frontmatter on new knowledge docs; `okf_validate` GREEN.
- [ ] Diagrams render on GitHub (Mermaid/ASCII).
