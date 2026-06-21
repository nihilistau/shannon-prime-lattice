---
type: convention
title: "MEM-OKF — the content-addressed tiered memory (one format for the agent AND the XBAR/NIGHTSHIFT organism)"
description: "An extension of SP-OKF: a content-addressed, three-tier (LUT -> summary -> full) memory that serves BOTH the agent's working memory (don't-rebuild facts) and the XBAR organism's episodic store. Addressed by content hash (sha256 for text, the C2 256-bit LSH signature for latent episodes), curated by NIGHTSHIFT (offline), receipted by PoUW (the address is the join key), audited by a runnable gate (G-MEM-OKF-CONFORM). The Tier-0 LUT is small enough to ride in context every session — that is the structural answer to the rebuild-from-scratch failure."
tags: [mem-okf, okf, memory, content-addressed, lut, nightshift, pouw, xbar, convention, anti-rebuild]
timestamp: 2026-06-21T00:00:00Z
resource: shannon-prime-lattice/tools/okf_mem.py
sp_status: ACTIVE
sp_gate: G-MEM-OKF-CONFORM
sp_commit: TBD
sp_repro: "python tools/okf_mem.py verify --root memory-okf"
---

# MEM-OKF — the content-addressed tiered memory

**This extends [SP-OKF](SP-OKF-PROFILE.md); it does not replace it.** SP-OKF gave us the *format* (markdown + receipts-first frontmatter) and a *flat* index. MEM-OKF adds the missing piece: a **content-addressed, progressively-disclosed pointer store** that the agent reads to *not rebuild what exists*, and that the XBAR/NIGHTSHIFT organism uses to store and recall episodes — **the same shape, the same tooling, the same curator, the same receipt ledger.** One format, two callers.

## 0. Why this exists (the failure it targets)

The project's recurring failure is **rediscovery-by-rebuild**: a session doesn't know (or trust) that a working subsystem already exists, so it reconstructs it. `prompt.md` already says "re-proving the stack from scratch is the failure mode this project has hit 20+ times" — naming it didn't stop it, because a passive doc has to be read and believed. MEM-OKF's structural lever: the **Tier-0 LUT is tiny and always-loadable** (it rides in context like `MEMORY.md`), each line is a content hash the agent can *follow* for depth, and the chain is **auditable by a runnable gate**. "Did the agent have this knowledge" becomes verifiable, not hoped-for. The seeded proof: `lookup rewind` returns "Rewind already exists: L1 verb `sp_session_register_kvdecode_backend` … DO NOT REBUILD" — the exact fact whose loss caused a full-engine rewrite.

## 1. The three tiers (progressive disclosure, made concrete)

Every memory — agent fact OR organism episode — is one **content-addressed object** at three disclosure depths. You pay only for the depth you follow (this is what keeps live context O(1)).

| tier | file | what | who reads it |
|---|---|---|---|
| **Tier-0 LUT** | `LUT.md` | one row/object: `addr \| kind \| keys \| one-line summary \| status \| ->sum`. Tiny, **always-loadable**. | every session, by keyword `lookup` |
| **Tier-1 summary** | `sum/<addr>.md` | the distilled, in-context summary; points down (`mem_full: <addr>`). For an episode = NIGHTSHIFT's canonical-fact distillation. | when a LUT hit looks relevant |
| **Tier-2 full** | `full/<addr>.md` | the complete context (text) **or** a blob pointer (episode: the Ring-2/Optane KV payload). | only when depth is actually needed |

Each tier is a conformant SP-OKF concept (`type: memory` + the receipts-first frontmatter), so a vanilla OKF consumer and `okf_validate.py` both read it, and **everything links**.

## 2. The address (one role, two primitives)

The address is a **content-derived, fixed-width identifier** — the dedup key, the integrity check, and the PoUW join key, all at once.

- **Agent / text concept** → `sha256(normalized_body)[:16]`. Deterministic; `verify` recomputes it and fails on any tamper.
- **Latent / organism episode** → the existing **C2 256-bit LSH signature** *is already the content address* (Hamming-comparable, period-6-rebased to the gemma4 global layers). Pass it as `--addr`; Tier-2 is a blob pointer to the Ring-2 payload.

Same *role*, modality-appropriate *primitive*. Content-addressing buys free dedup (re-adding identical content is idempotent) and a cheap audit.

## 3. The shared lifecycle (this is the unification)

```
   live turn / write                      idle
        │                                   │
        ▼                                   ▼
   PoUW ledger  ──reads──►  NIGHTSHIFT (offline curator)  ──writes──►  MEM-OKF store
  (64B SpinorReceipt,        distill raw turn/episode →                 full/<addr>.md (Tier-2)
   addr = join key)          canonical in-distribution form             sum/<addr>.md  (Tier-1)
                                                                        LUT.md row     (Tier-0)
        ▲                                                                   │
        └───────────────── recall (W_c / judge ranks the LUT) ◄────────────┘
```

- **Writer = XBAR (live) + NIGHTSHIFT (offline).** XBAR writes an episode at admission time (C2 sig = addr, NL gloss = LUT row, KV payload = Tier-2 blob). The agent writes a fact when it learns something durable. One `add` interface, two callers.
- **Curator = NIGHTSHIFT, offline (expanded).** Wakes on idle, reads the PoUW receipt log, distills each raw turn/episode into the three tiers, computes the address, dedups by address. **This is also the fix for the open B4 bug:** distilling live turns into *canonical, in-distribution* Tier-1 form is exactly what makes consolidated episodes match the curated `ep.k` distribution the W_c head trained on (the live-vs-curated shape mismatch that breaks foreign-reject today).
- **Receipt = PoUW (`pouw_ledger.rs`).** Every write mints a 64-byte `SpinorReceipt` whose payload carries the object's address. The ledger is the provenance log; the address joins ledger ↔ store. Auditable end-to-end: object → receipt → full context, all by one hash.
- **Recall = rank the LUT.** Tier-0 lookup (keyword for the agent; cue-sig Hamming for the organism) → candidate addrs + one-line summaries → follow to Tier-1 → optionally Tier-2. The deployed **W_c head and any future diffusion judge are both just learned Tier-0→Tier-1 rankers over this store** — the store is the substrate beneath both selectors.

## 4. The gate — G-MEM-OKF-CONFORM (auditability as a runnable check)

`python tools/okf_mem.py verify --root <root>`:
1. every `full/<addr>.md`: `mem_addr == filename`; for `agent` kind, `sha256(body)[:16] == addr` (text-tamper detector);
2. every `sum/<addr>.md`: `mem_full` resolves to an existing full object;
3. every LUT row: its `addr` has both a `sum/` and a `full/`; keys + summary non-empty;
4. no orphans (full/sum not indexed by the LUT).
Exit non-zero on any error. **Bit-exact-when-off preserved:** the store is additive; an empty/unused store is a strict null floor. Seeded pilot: **4 objects, 0 errors → GREEN.**

## 5. Tooling + layout

- **`tools/okf_mem.py`** (no deps): `add` (write all 3 tiers + LUT row, compute addr) · `lookup <kw>` (keyword search over the LUT) · `expand <addr> [--full]` (follow the pointer chain) · `verify` (the gate). `--root` is parameterized → **project-agnostic** (any project gets a store with `MEM_OKF_ROOT=<dir>`).
- **Store layout:** `<root>/LUT.md` (Tier-0) · `<root>/sum/<addr>.md` (Tier-1) · `<root>/full/<addr>.md` (Tier-2) · `<root>/index.md`. The shannon-prime store is `shannon-prime-lattice/memory-okf/`.
- **Relationship to the harness `MEMORY.md`:** the auto-memory `MEMORY.md` is already a Tier-0-ish flat index; MEM-OKF adds the content-addressed Tier-1/Tier-2 depth + the verify gate + the PoUW hash join. They coexist; `MEMORY.md` points at the LUT.

## 6. The always-loaded discipline (wired into the bootstrap)

The only thing that defeats rebuild-by-default is making "does this already exist?" cheap and unskippable. Therefore, in `prompt.md` §8 and every repo CLAUDE.md: **before building any subsystem, `lookup` it in the MEM-OKF LUT (and `grep` the tree). A new file for an existing capability is a defect.** The LUT is small enough to load every session; the pre-flight is one command. New `type`s still register in [SP-OKF-PROFILE §2](SP-OKF-PROFILE.md) first; `type: memory` already covers all three tiers.

## 7. Honesty (what is built vs specified)

- **Built + gated today (text/agent tier):** `okf_mem.py` add/lookup/expand/verify, seeded with the real don't-rebuild facts, G-MEM-OKF-CONFORM GREEN.
- **Specified, maps onto existing components (latent/episode tier):** the episode address = the C2 sig (exists), Tier-2 blob = the Frobenius Ring-2 store (exists), the curator = NIGHTSHIFT (exists, default-off, B4 bug open), the receipt = `pouw_ledger.rs` (exists, default-off). Wiring NIGHTSHIFT to emit the three tiers + record the addr in the ledger is the follow-on build — additive, default-off = null floor, receipts-first per stage. No frozen-ABI change.
