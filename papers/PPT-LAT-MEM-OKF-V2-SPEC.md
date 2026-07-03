---
type: convention
title: "MEM-OKF v2 — the policy-bearing, compounding memory format (OKF ⋈ Karpathy LLM-wiki ⋈ the Decide→Execute spine)"
description: "The v2 spec for Shannon-Prime's memory. Extends OKF v0.1 (portable markdown+frontmatter concepts) and MEM-OKF v1 (content-addressed LUT→summary→full tiers) with a PER-ENTRY POLICY BLOCK: each memory declares how it wants to be retrieved, delivered, and declined — the API-like contract that lets the ADR-004 spine dispatch the RIGHT proven tool per entry (zero-inference decline for secrets, systemecho for counterfacts, two-stage for same-template, recite for unique facts). Realizes Karpathy's LLM-wiki (a compounding, cross-linked, self-maintained store with Ingest/Query/Lint) on our substrate, and makes the memory format a governing control surface co-equal with the spine."
tags: [mem-okf, okf, memory, policy, retrieval, delivery, decline, spine, decide-execute, karpathy-llm-wiki, convention, content-addressed]
timestamp: 2026-07-03T00:00:00Z
resource: shannon-prime-lattice/tools/okf_mem.py
sp_status: DESIGN
sp_gate: "G-MEM-OKF-CONFORM (v2: validates the policy block) + G-MEMPOLICY-V3 (policy-driven V3 delivery hits each class's proven number)"
sp_commit: "extends MEMORY-OKF-PROFILE (v1) + SP-OKF-PROFILE; opens with ADR-004"
sp_repro: "python tools/okf_mem.py verify --root memory-okf ; policy harness (pending)"
---

# MEM-OKF v2 — the policy-bearing, compounding memory format

**Lineage.** [OKF v0.1](SP-OKF-PROFILE.md) (portable markdown+frontmatter concepts, `type`
required, permissive consumption) → [SP-OKF](SP-OKF-PROFILE.md) (receipts-first extension) →
[MEM-OKF v1](MEMORY-OKF-PROFILE.md) (content-addressed LUT→summary→full tiers, `okf_mem.py`).
**v2 adds one thing: a per-entry POLICY BLOCK** so the entry itself governs its retrieval,
delivery, and decline — the leverage the faithfulness tests uncovered (each proven tool is
right for a different class of memory; see [ADR-004](PPT-LAT-ADR-004-MEMORY-GOVERNANCE.md) §1).

## 0. The one idea

A memory is not just text to retrieve — it is text **plus a contract for how to serve it
safely**. v1 answered *where is it* (content address, tiers). v2 answers *how must it be
retrieved and delivered, and when must the system refuse* — declared by the memory, enforced
by the spine. This is what makes MEM-OKF an API, not a blob store.

## 1. A v2 concept (still 100% OKF-conformant)

Every memory remains one OKF concept file with `type: memory` + the SP receipts-first fields
(v1). v2 adds an additive **policy block** (OKF explicitly permits producer keys; a vanilla
OKF consumer ignores it, our spine reads it). It lives in the Tier-2 `full/<addr>.md` and is
mirrored (compact) into the Tier-0 LUT row so the policy is visible at lookup time.

```yaml
---
type: memory
title: "UK currency (revised)"
description: "The United Kingdom now uses the krona as its currency."
tags: [uk, currency, counterfact]
timestamp: 2026-07-03T...Z
sp_status: ACTIVE
mem_addr: 9f3a...           # v1: content address (sha256 text / C2 sig latent)
mem_kind: agent            # v1: agent | episode
mem_tier: full             # v1
# ---- v2 POLICY BLOCK (the new contract) ----
mem_class: counterfact                    # sets the default policy (§3)
mem_retrieval: {key: l5-question, selector: cosine, tau: 0.30, entity_guard: false}
mem_delivery: systemecho                  # how EXECUTE serves it
mem_authority: overrides-prior            # overrides-prior | supplements | private
mem_decline: {when: [], message: ""}      # when the system must refuse (empty = never)
mem_confidence: 0.90
mem_provenance: <pouw-addr>               # join key to the receipt ledger
mem_links: {supersedes: [<addr>], same_template: [<addr>, <addr>]}
---
```

## 2. The policy fields (the API schema)

| field | values | meaning | grounded in |
|---|---|---|---|
| `mem_class` | private-secret · counterfact · same-template · fact · preference · episodic-event | the kind of knowledge; sets defaults | the receipts (§3) |
| `mem_retrieval.key` | l5-question · exact-token · c2-sig | what the entry is indexed by | question-space keys (`G-QKEYS-*`) |
| `mem_retrieval.selector` | cosine · family · exact | how a query matches it | L5 cosine; family for same-template |
| `mem_retrieval.tau` | float | match threshold | 0.30 (L5) |
| `mem_retrieval.entity_guard` | bool | require a shared high-entropy token (private-data safe) | attr-gate paraphrase guard |
| `mem_delivery` | systemecho · attr-gate-strict · two-stage · recite · system · route:&lt;t&gt; · pass | the EXECUTE arm | the delivery sweep + E1/E2/E8 |
| `mem_authority` | overrides-prior · supplements · private | how forcefully to assert it | delivery framing |
| `mem_decline.when` | [attribute-absent, family-ambiguous, low-margin, zero-inference] | conditions that force a refusal | attr-gate; margin |
| `mem_decline.message` | string | the fixed decline string (streamed at the ZERO-decode seam) | `G-SNE-ATTRGATE-ZEROINF` |
| `mem_confidence` | float | curator/PoUW confidence | NIGHTSHIFT |
| `mem_provenance` | pouw-addr | receipt-ledger join key | `pouw_ledger.rs` |
| `mem_links` | {supersedes, same_template, cites} | the wiki graph edges | Karpathy §5 |

**Resolution order (per ADR-004 law 4, strictest wins):** explicit per-entry field →
`mem_class` default → global safe default (`recite`, `supplements`, no decline). A
`private-secret` class CANNOT be overridden to `systemecho`/`two-stage`/full-context — the
validator rejects the downgrade.

## 3. Class defaults (the proven mapping)

Same table as ADR-004 §3 (single source: this doc). Each row is a PROVEN tool, now selected by
the entry's own class rather than a global flag:

- **private-secret** → retrieval exact-token+entity_guard · delivery attr-gate-strict · decline
  zero-inference on attribute-absent · authority private. *(SNE crucible: 80→0 confab, 5→0 leak.)*
- **counterfact** → l5-question cosine · systemecho · overrides-prior. *(22/30 @ 0 leak.)*
- **same-template** → family-scoped retrieval · **systemecho** delivery (two-stage REFUTED,
  `G-MEMPOLICY-V3`: 22/3 ≤ systemecho) · low-confidence flag. *(Delivery is PERFECT given the
  right entry — 30/30 @ 0 leak; the residual is the selection ceiling `G-WCHEAD-SAMETEMPLATE`,
  not delivery, so no delivery trick fixes it.)*
- **fact** (unique subject) → l5-cosine · recite · supplements. *(~100% needle recall.)*
- **preference/persona** → l5-cosine · system · supplements.
- **episodic-event** → c2-sig/l5 · recite-or-summary · supplements. *(XBAR organism.)*

## 4. The API surface (what the spine calls)

MEM-OKF v2 IS an API over the store. The contract (realized by `okf_mem.py` + the spine):

```
retrieve(query, view) -> [Entry]        # each Entry honors its OWN mem_retrieval
Entry.policy                            # mem_class + mem_delivery + mem_decline + …
decide(Entry, view)  -> LatentDecision  # ADR-004 RecallPolicyDecider: policy -> Deliver/Decline/Route/Pass
execute(LatentDecision) -> stream       # the ADR-002 executor; decline at the zero-decode seam
lint()                -> [issue]        # NIGHTSHIFT health-check (contradictions, orphans, mis-class)
```

The Tier-0 LUT row carries a compact policy hint (`class/delivery`) so a lookup already reveals
how an entry will be served — progressive disclosure of *policy*, not just content.

## 5. Karpathy LLM-wiki, instantiated on our substrate

The wiki is a **compounding, cross-linked, self-maintained** store — not re-derived per query.
The three Karpathy operations map onto our components:

- **Ingest** = XBAR (live admission) + NIGHTSHIFT (offline curator): read the turn/episode,
  distill to the 3 tiers, **assign `mem_class` + policy**, and write `mem_links` — including
  the crucial `supersedes` edge ("new data contradicts old", e.g. the krona counterfact
  supersedes the pound prior) and `same_template` edges (so a family is navigable ⇒ family-scoped
  retrieval + two-stage become cheap). One source touches many pages, LLM-maintained.
- **Query** = policy-driven recall (§4): retrieve by each entry's key, decide by its policy,
  execute at the clean seam. Good answers can be **filed back** as new entries (compounding).
- **Lint** = NIGHTSHIFT health-check: contradiction pairs without a `supersedes` edge, orphan
  entries, stale `sp_status`, `same_template` clusters missing links, and — new for v2 —
  **policy conformance** (a `private-secret` with a non-strict delivery is a lint failure).

`index.md` (content catalog) and `log.md` (chronological, `## [date] ingest|query|lint`) are the
OKF reserved files; the Tier-0 `LUT.md` is the always-loadable content+policy index.

## 6. Conformance — G-MEM-OKF-CONFORM v2

`python tools/okf_mem.py verify --root <root>` keeps the v1 checks (address integrity, tier
pointers, no orphans) and ADDS the policy gate:
1. every entry with a policy block: `mem_class` ∈ vocab; `mem_delivery` ∈ vocab; `mem_decline`
   well-formed (a non-empty `when` requires a `message`).
2. **safety monotonicity:** `mem_class: private-secret` MUST have `mem_delivery` ∈
   {attr-gate-strict} and a `zero-inference` decline — a secret with a leaky delivery is a RED.
3. `mem_links` targets resolve (broken links tolerated per OKF, but `supersedes`/`same_template`
   to a missing addr is a warn).
Bit-exact-when-off preserved: an un-policied store passes v1 and skips the v2 checks.

## 8. The whole system as ONE — the single substrate

MEM-OKF v2 is not a component; it is **the format the entire system speaks**. Every subsystem
we built is a caller of one content-addressed, policy-bearing store — the engine reads it to
serve, the harness writes and curates it, NIGHTSHIFT consolidates it, and three retrieval tiers
serve it. No subsystem owns memory; they share it.

### 8.1 One store, four roles (nothing new to build — wire what exists)

| role | who (verified path) | what it does on the ONE store |
|---|---|---|
| **EXECUTE** (serve) | engine `tools/sp_daemon/src/{routes.rs,spine.rs}` | reads an entry's `mem_delivery`/`mem_decline` → ADR-004 Decide→Execute (systemecho / two-stage / zero-inference decline). The **served** path. |
| **INGEST** (write) | harness `harness/nexus/knowledge_pipeline.py` | validate → dedup(sha256) → quality-score → **classify + assign policy** → embed → auto-Q&A → write MEM-OKF tiers. |
| **CURATE** (NIGHTSHIFT) | harness `harness/control/agency.py` (idle-gated heartbeat; already named "nightshift") | the offline curator = model-driven consolidate/forget/merge → distil to Tier-1, cross-link (`supersedes`/`same_template`), dedup by address. **This IS NIGHTSHIFT** — the harness agency loop and the engine's NIGHTSHIFT are one organism, one store. |
| **RETRIEVE** (query) | harness `harness/nexus/query_router.py` (3-tier) + engine `recall.rs` (L5) | Q&A-cache → vector(`embedding_service.py`) → LLM-writeback, OR the latent L5-cosine on the served path, OR markdown search (qmd) at scale. All return candidates the policy then governs. |

The harness `harness/nexus/` (ingest/embed/query-router/SQLite) and `conversation_memory.py`
(SHORT/MID/LONG consolidation) are the **already-built** write+curate+search side — based on
CosySim/Nexus. MEM-OKF v2 is the **format contract** that makes their output directly
serveable by the engine spine without translation. One `memory-okf/` directory; the harness
writes it, the daemon reads it.

### 8.2 The retrieve() tier is pluggable (qmd / Nexus / L5) — policy is not

Retrieval is a swappable implementation behind one interface (`retrieve(query,view)->[Entry]`);
the **policy governs regardless of which retriever found the entry**:
- **latent L5-cosine** (engine `recall.rs`) — the served, question-space, paraphrase-robust path.
- **Nexus vector** (harness `embedding_service.py`, pluggable provider + hashing fallback + LRU) —
  the harness-side embedding search with per-tier confidence.
- **qmd** ([tobi/qmd](https://github.com/tobi/qmd), hybrid BM25+vector+LLM-rerank over markdown,
  CLI **and** MCP) — the scaled markdown search Karpathy names; drop-in for the `retrieve()`
  interface as the store grows past the always-loadable LUT. A curator/search tool, not a new store.

Because retrieval is decoupled from delivery, the same entry is found by L5 on the metal, by
Nexus-vector in the harness, or by qmd from the CLI — and served identically per its `mem_delivery`.

### 8.3 The loop (ingest → serve → curate), unified

```
   user turn ─► ENGINE spine (routes.rs)  ─reads policy─►  EXECUTE (systemecho/two-stage/decline)
        │                                                        │
     transcript                                                  ▼
        │                                              PoUW receipt (addr = join key)
        ▼                                                        │
   HARNESS ingest (knowledge_pipeline) ─classify+policy+embed─►  MEM-OKF v2 store  ◄─┐
        │                                                        ▲                  │
        └──► NIGHTSHIFT / agency loop (agency.py) ─consolidate, cross-link, dedup───┘
                                          (Lint: contradictions, orphans, policy-safety)
```

Everything joins on the **content address** (v1) + the **PoUW receipt** (provenance) + the
**policy** (governance). That is the system working as one: a single memory the whole stack
reads, writes, curates, and serves — engine, harness, NIGHTSHIFT, and every retriever alike.

## 9. Honesty — built vs specified

- **Built (v1, GREEN):** content-addressed tiers, `okf_mem.py` add/lookup/expand/verify, the
  agent store seeded with real don't-rebuild facts.
- **Built (harness side, CosySim/Nexus):** the ingest pipeline, embedding service, 3-tier query
  router, SQLite store, and the agency/NIGHTSHIFT curator loop (`harness/nexus/*`,
  `harness/control/agency.py`) — the write/curate/search half already runs.
- **Specified (v2, THIS doc + ADR-004):** the policy block + class defaults + the policy-driven
  spine dispatch + the v2 conformance checks. Each *delivery tool* it names is independently
  proven; the *composition* (per-entry dispatch) is what `G-MEMPOLICY-V3` will gate.
- **Reference impl (this session):** `okf_mem.py` gains the policy fields + v2 verify; a policy
  harness re-runs the V3 corpus with per-entry classes and measures obey/leak per class.
