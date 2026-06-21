# AGENTS.md — how an agent enters and navigates shannon-prime-lattice

This is the **umbrella / front-door** repo for Shannon-Prime. It holds the
papers, the proven-state ledger, the contracts, and the **OKFS knowledge
tooling** (`okf_validate.py`, `okf_mem.py`, `okf_history.py`). The code lives
in the companion repos (`shannon-prime-system` = math core,
`shannon-prime-system-engine` = inference engine). This file tells a coding
agent how to come up to speed and what is binding.

---

## 0. Read order (do this first, in this order)

1. **`prompt.md`** — the canonical session bootstrap. What the project is, the
   current campaign, the methodology, the machine. Start here, every session.
2. **`papers/PPT-LAT-STATE.md`** — the PROVEN record (the "20th rewrite"
   ledger). Each line cites its evidence (commit / gate / closure). **Your
   default is TRUST.** Re-proving the whole stack from scratch is the failure
   mode this project has hit 20 times — don't.
3. **`papers/STATUS-MAP-2026-06-21.md`** — the verified box-by-box tier map
   (GREEN-LIVE / BUILT-DEFAULT-OFF / DESIGN-ONLY), written specifically to
   settle "two memories disagree." Read it when you're unsure what is actually
   live vs gated-off.
4. **`memory-okf/LUT.md`** — the MEM-OKF Tier-0 lookup table. Skim it; then run
   the lookup pre-flight below before building anything.
5. **`HISTORY.md`** — the hashed Tier-0 commit LUT (the short-hash IS the
   content address; `git show <hash>` for the full commit). Use it to place a
   claim in time.
6. **The active contract** — `papers/CONTRACT-*.md` for the lane you're
   touching (e.g. `CONTRACT-CHAT-FULLSTACK`, `CONTRACT-NIGHTSHIFT-CURATOR`,
   `CONTRACT-BYTEEXACT-forward`, `CONTRACT-C2`). Contracts carry the gates and
   the run records.

`CURRENT-STATE-OF-PROJECT.md` (repo root) is a human-readable synthesis if you
want narrative orientation; `papers/PPT-LAT-Theory.md` is the math foundation —
read it before touching the substrate.

---

## 1. The binding MEM-OKF lookup pre-flight (do this before building ANYTHING)

This project has rebuilt the same subsystems 20+ times because sessions forgot
what already existed. **A new file for a capability that already exists is a
defect, not progress.** So, before you write code or a new doc:

```bash
python tools/okf_mem.py lookup --root memory-okf <keyword>
```

…and `grep` the tree for the capability. If the LUT or the tree already has it,
**reuse it** — extend, don't rebuild. The store is content-addressed
(LUT → summary → full; sha256 for text, C2-LSH-sig for latent episodes); spec
is `papers/MEMORY-OKF-PROFILE.md`; verify with
`python tools/okf_mem.py verify --root memory-okf` (gate `G-MEM-OKF-CONFORM`).

At session end, bank durable "X already exists — don't rebuild" facts:
`python tools/okf_mem.py add …`.

---

## 2. Non-negotiables (these override convenience)

- **Receipts-first.** No number without a reproducing command + a `LEDGER.md` /
  STATE row. A claim you can't run isn't a claim.
- **Bit-exact when off.** Every mechanism is an `SP_*` flag, a strict no-op by
  default. **Unset == null floor == may LOOK broken** — check the flag before
  declaring anything broken. Verify the off-state is byte-identical to baseline.
- **Honest tiers, exact words.** Use the vocabulary and never inflate:
  **GREEN-LIVE** (gated GREEN *and* served by default) · **gated-GREEN /
  default-off** (passes its gate, behind a flag — NOT "live") · **BUILT/WIRED**
  (in-tree, primitive-gated, not yet end-to-end) · **DESIGN** (spec'd, unbuilt)
  · **HONEST-NEGATIVE** (measured + refuted, kept on the record). gated-GREEN is
  **not** GREEN-LIVE.
- **No silent gate revision.** If the implementation can't meet a spec'd gate,
  **surface upstream** and amend the contract formally — never retune fixtures,
  retreat to a weaker claim, or footnote a PASS.
- **Honest negatives stay attached.** The 32k NIAH MISS, the falsified KSTE
  router, the retired 34.2 tok/s headline — on the record on purpose; they
  prove the gates discriminate.
- **Check the code + commits + `git fetch` before trusting memory or a
  summary.** STATE is the proven record — trust it, re-prove only with concrete
  cause. Verify Gemini's claims against the tree.
- **Reference-first when porting** — read the reference (llama.cpp / the paper)
  with file:line before coding.
- **Anti-contamination** — do NOT read, copy, or vendor code from the archived
  `shannon-prime/` or `shannon-prime-engine/` repos.

---

## 3. The SP-OKF frontmatter rule (knowledge docs)

Every knowledge `.md` you create or touch under a bundle (`papers/`,
`memory-okf/`, `memory/`) is an SP-OKF concept and must carry the frontmatter:

```yaml
---
type: <one of the registered vocabulary in papers/SP-OKF-PROFILE.md §2>
title: "..."
description: "..."
tags: [...]
timestamp: 2026-06-21T00:00:00Z
resource: <relative path this concept is about>
sp_status: <GREEN | ACTIVE | DESIGN | ...>
sp_gate: <gate name or none>
sp_commit: <short hash or TBD>
sp_repro: "<reproducing command, or none>"
---
```

New `type`s register in `papers/SP-OKF-PROFILE.md` §2 **first** (single source
of truth). Before committing changes to a bundle, run the validator:

```bash
python tools/okf_validate.py papers     # gate G-OKF-CONFORM, must be GREEN
```

`README.md` and this `AGENTS.md` are plain top-level orientation docs (they are
not `papers/` concepts), so they intentionally do **not** carry frontmatter.
`HISTORY.md` carries `type: log` frontmatter because it is a generated MEM-OKF
artifact.

---

## 4. Repo-specific notes

- **OKFS tooling lives here.** `tools/okf_validate.py` (G-OKF-CONFORM),
  `tools/okf_mem.py` (the anti-rebuild store), `tools/okf_history.py`
  (regenerates `HISTORY.md`: `python tools/okf_history.py gen --repo . --out
  HISTORY.md --n 80`).
- **Submodule discipline.** The math core is also carried as a submodule inside
  the engine (`lib/shannon-prime-system`), so the standalone clone can diverge
  — `git fetch` + behind-check before building or committing.
- **Worktrees per concurrent agent.** Two agents on one repo → each in its own
  `git worktree add`.
- **Supersession order when documents disagree:** STATE > contract run records >
  Roadmap amendments > Roadmap body. The L1 ABI and `.sp-model` specs are
  frozen; everything else is amendable when reality contradicts it.
