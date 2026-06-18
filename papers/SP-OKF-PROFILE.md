---
type: convention
title: SP-OKF — Shannon-Prime's profile of the Open Knowledge Format
description: How Shannon-Prime structures all of its knowledge (papers, contracts, state, receipts, memories) as an OKF v0.1 bundle, with a receipts-first frontmatter extension and a validator that keeps it conformant.
resource: https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf
tags: [okf, knowledge, convention, control-structure, receipts-first]
timestamp: 2026-06-18T00:00:00Z
sp_status: ACTIVE
sp_commit: TBD
sp_gate: G-OKF-CONFORM
sp_repro: python shannon-prime-lattice/tools/okf_validate.py <bundle-dir>
---

# SP-OKF — Shannon-Prime's profile of the Open Knowledge Format

**Upstream:** Google Cloud's **Open Knowledge Format (OKF) v0.1** (12 Jun 2026), which formalises Karpathy's "LLM wiki" pattern into a portable, vendor-neutral standard: a *bundle* is a directory of markdown **concept** files, each with a small block of YAML frontmatter and a markdown body; concepts cross-link with ordinary markdown links to form a graph; `index.md` gives progressive disclosure and `log.md` gives chronological history. The only frontmatter field OKF *requires* is `type`; the reserved set is `type, title, description, resource, tags, timestamp`. "Just markdown, just files, just YAML frontmatter — no SDK, no runtime." (See `resource` above + `cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing`.)

**Why we adopt it:** our knowledge is *already* an LLM-wiki — markdown docs with YAML frontmatter (the `memory/` files), cross-links, a receipts-first ledger. OKF is the lingua franca that makes it portable, agent-consumable, and interoperable without lock-in. SP-OKF = OKF v0.1 **plus** a thin receipts-first extension, **minus** nothing. We stay 100% OKF-conformant (a vanilla OKF consumer can read our bundles); the SP fields are additive producer fields OKF explicitly permits.

## 1. Conformance: every SP knowledge concept

A concept is one `.md` file. Its path is its identity. It MUST carry YAML frontmatter with:

- `type` — **required** (OKF). From the SP type vocabulary (§2).
- `title`, `description` — short human strings (strongly recommended).
- `tags` — YAML list.
- `timestamp` — ISO-8601 UTC (last-meaningful-update).
- `resource` — a URL or repo path the concept points at (the code/commit/dataset it documents), when one exists.

Then the SP **receipts-first extension** (additive; the discipline baked into the frontmatter so every claim is auditable):

- `sp_status` — one of `GREEN | RED | DESIGN | HONEST-NEGATIVE | DRAFT | ACTIVE | SUPERSEDED`.
- `sp_gate` — the gate name that proves the concept (e.g. `G-BYTEEXACT-FORWARD-12B`), or `none`.
- `sp_commit` — the citable commit hash(es) the concept is anchored to, or `TBD`.
- `sp_repro` — the one-line command that reproduces the result, when applicable.

Body is free markdown. Cross-reference other concepts with **markdown links** to their relative path, e.g. `[byte-exact forward](../R1-reduction-order-immune-inference/paper.md)`. (The `memory/` bundle keeps its existing `[[name]]` wiki-links as an internal convenience; everything else uses standard markdown links so vanilla OKF consumers resolve the graph.)

`index.md` (per directory) = progressive-disclosure map of that sub-bundle. `log.md` = chronological change history (the `LEDGER.md` is the canonical project-wide `log.md`).

## 2. The SP `type` vocabulary

OKF leaves `type` to the producer; we fix a controlled vocabulary so consumers can filter:

| `type` | what it is | example bundle |
|---|---|---|
| `research-paper` | full arXiv-style preprint | `Position_Is_Arithmetic/research papers/` |
| `paper-bite` | short digestible "Papers series" note | `Position_Is_Arithmetic/papers/` |
| `paper-provenance` | the genuine-wins / literature-positioning / honest-status note attached to a research paper | `research papers/R*/provenance.md` |
| `contract` | a build/gate contract | `lattice/papers/CONTRACT-*.md` |
| `gate-receipt` | a single proven result + its command | `engine tests/fixtures/.../G-*.log` (indexed) |
| `roadmap` | phase plan | `lattice/papers/PPT-LAT-Roadmap.md` |
| `project-state` | the proven living record | `lattice/papers/PPT-LAT-STATE.md` |
| `session-handoff` | in-flight state | `lattice/SESSION-HANDOFF.md` |
| `abi` | a frozen interface spec | `lattice/papers/PPT-LAT-L1-ABI-v0.md` |
| `design` | a design/RFC doc | `lattice/papers/DESIGN-*`, `RFC-*` |
| `runbook` | operational procedure | `lattice/papers/RUNBOOK-*` |
| `lesson` | a banked failure/principle | `lattice/lessons.md` |
| `convention` | a standard (this doc) | `SP-OKF-PROFILE.md` |
| `memory` | a persistent-memory fact | `memory/*.md` |

New types are added here first (single source of truth), then used.

## 3. Bundles (where the knowledge lives)

Each of these directories is (or becomes) a conformant OKF bundle, each with an `index.md`:

- `Position_Is_Arithmetic/research papers/` — `research-paper` + `paper-provenance` (pilot: conformant first).
- `Position_Is_Arithmetic/papers/` — `paper-bite` (the digestible series). `LEDGER.md` = the project `log.md`.
- `shannon-prime-lattice/papers/` — `contract`, `roadmap`, `project-state`, `abi`, `design`, `runbook`.
- `memory/` (the agent's persistent memory) — `memory`. Already frontmatter-bearing; align the field names.
- (engine/system repo docs adopt the same frontmatter where they are knowledge, not code.)

## 4. Control structure — how it stays in place

1. **The validator** `shannon-prime-lattice/tools/okf_validate.py` (no deps): walks a bundle, checks every `.md` has conformant frontmatter (`type` required + reserved/SP fields well-formed + `sp_status` in range + markdown cross-links resolve), prints a per-file report, exits non-zero on any violation. This is gate **G-OKF-CONFORM**. Run it on a bundle before committing changes to it.
2. **The CLAUDE.md rule** (in every repo's CLAUDE.md): "All knowledge docs are SP-OKF concepts — carry the §1 frontmatter; new `type`s register in SP-OKF-PROFILE §2 first; run `okf_validate.py` on a touched bundle before commit." This is the agent-facing control that survives across sessions.
3. **`index.md` per bundle** is the entry point an agent reads first (progressive disclosure) — keep it current when concepts are added.
4. **No silent drift:** a concept whose `sp_status` or `sp_commit` goes stale is a conformance bug, surfaced by the validator, fixed in the same change.

## 5. Phased rollout (do not boil the ocean)

- **Phase 0 (this session):** ship this profile + the validator + the CLAUDE rule + memory; **pilot** = make `research papers/` fully conformant (frontmatter + `index.md` + `log.md` + per-paper `provenance.md`) and validate GREEN.
- **Phase 1:** align the `memory/` bundle frontmatter to §1 (it is closest); add `memory/index.md`.
- **Phase 2:** lattice `papers/` — add frontmatter to `contract`/`roadmap`/`state`/`abi`/`design` concepts (the largest set; do it in batches, validator-gated).
- **Phase 3:** index the engine `tests/fixtures/.../G-*.log` receipts as `gate-receipt` concepts (or an index that points at them), closing the loop so every paper/contract claim links to its receipt concept.

The format is the contract; the tooling at each end is swappable. We adopt OKF so our knowledge is portable the day anyone else speaks it — and so our own agents read one shape, no translation.
