---
type: design
title: "ADR-005 — The Living Memory System: reconciliation, the telemetry flywheel, and adaptive classification"
description: "The MEM-OKF/ADR-004 store is unified and policy-driven; this ADR makes it LIVING: (1) live reconciliation so a memory the harness/agent writes is served by the engine WITHOUT a restart — a hybrid of an idle-gated NIGHTSHIFT reconciler + an explicit /v1/memory endpoint, deliberately NOT a new trained head; (2) a TELEMETRY FLYWHEEL — every recall/deliver/decline decision + output is receipted (PoUW SpinorReceipt) and logged as a class-redacted telemetry-okf record, becoming the data to tune thresholds, finetune models, and detect drift; (3) ADAPTIVE CLASSIFICATION — a tiered classifier (deterministic heuristic at capture -> NIGHTSHIFT model-refine on idle -> optional model-emitted [MEM_CLASS] tag via the StreamProcessor channel), telemetry-driven, with a learned head deferred until the data warrants it; (4) PERSONALITY as first-class (persona.md live-edit + persona/agent-persona classes, system delivery). Composes the existing toolbox — PoUW ledger, events_tx/SSE, StreamProcessor inline tags, Nexus ingest/embed/query, the agency curator loop, content-addressing — rather than new machinery."
tags: [design, adr, living-memory, mem-okf, reconciliation, hot-reload, telemetry, flywheel, classification, personality, nightshift, pouw, sse, nexus, decide-execute]
timestamp: 2026-07-03T00:00:00Z
resource: shannon-prime-lattice/papers/PPT-LAT-ADR-005-LIVING-MEMORY.md
sp_status: DESIGN
sp_gate: "phased: G-LM-RECONCILE (hot-reload) · G-LM-TELEMETRY (flywheel + redaction) · G-LM-CLASSIFY (adaptive) — see CONTRACT-LIVING-MEMORY"
sp_commit: "opens after engine 6c84ca1 (G-STORE-MERGE) + lattice 260c554; builds on ADR-004 (memory governance) + MEM-OKF v2"
sp_repro: "per CONTRACT-LIVING-MEMORY brick gates"
---

# ADR-005 — The Living Memory System

**Status: DESIGN.** Builds on **ADR-004** (memory as a governing layer) + **MEM-OKF v2**; the
build phases live in **[CONTRACT-LIVING-MEMORY](CONTRACT-LIVING-MEMORY.md)**.

## 1. Context — what "living" adds to a store that is already unified

The store is content-addressed, policy-bearing, and read+written by both engine and harness
(`G-STORE-MERGE`). Three gaps remain between "unified" and "alive":

1. **It's boot-static.** The engine merges the store at startup; a memory the agent writes
   mid-session is not served until a restart.
2. **It's amnesic about itself.** The system makes rich decisions every turn (which entry, at
   what margin, delivered how, declined why, in how many ms) and throws them away. There is no
   data to tune the thresholds, finetune a model, or notice drift.
3. **Its classes are fixed by a heuristic.** `classify_mem_class` is deterministic and coarse;
   there is no path for a mis-classification to be corrected, nor for classification to improve.

The design principle: **compose the toolbox, don't grow it.** Every lever below already exists
— PoUW ledger + `SpinorReceipt` (audit), `events_tx`/SSE (channel), the harness `StreamProcessor`
inline-tag extractor (`[TAG:value]` metadata riding the token stream), Nexus ingest/embed/query
(sink + vector tier), the agency `run_agency_scheduler` idle curator (NIGHTSHIFT), `persona.md`
(live personality), content-addressing (free cache invalidation).

## 2. Decision 1 — LIVE RECONCILIATION (a hybrid, explicitly NOT a head)

**A memory written into the store is served without a restart, via two complementary paths:**

* **Idle reconciler (the general path)** — an idle-gated background thread on the engine (the
  NIGHTSHIFT pattern the harness already runs as `run_agency_scheduler`): poll the store's
  `full/` mtime (or `notify` watch); on change, and only when the daemon is idle
  (`tokens_per_sec < ε`, the existing metrics gate), MINT keys for NEW/changed concepts, drop
  episodes named by `mem_links.supersedes`, and swap them into the live recall set. Batch, cheap,
  never starves a live turn.
* **Explicit `/v1/memory` endpoint (the interactive path)** — when the agent stores a fact
  mid-conversation, the harness POSTs `{addr}` (or the concept) to the engine, which mints +
  merges that ONE concept immediately, so it is recallable on the very next turn. Low-latency,
  no polling wait.

**Why not a head:** reconciliation is I/O + a per-concept key-mint, not a classification the
model must learn; a head adds training cost and latency for a job a filesystem watch + the
existing mint path already do. (Learned heads were also convicted for the harder selection
problem, `G-WCHEAD-SAMETEMPLATE`.)

**Cache invalidation (Decision 1b):** content-addressing does most of the work — an EDIT changes
the sha256 → a NEW `full/<addr>.md` → no cache → mint; the old addr is superseded (`mem_links`).
For a rare in-place edit, the `full/<addr>.l5` cache carries a body-hash stamp; a mismatch
re-mints. No manual invalidation.

## 3. Decision 2 — THE TELEMETRY FLYWHEEL (the data that makes it self-improving)

**Every DECIDE→EXECUTE decision + its output is recorded, once, as structured, class-redacted
telemetry — one stream across engine and harness.** This is the highest-leverage new capability:
it turns the running system into a data generator.

* **What is logged (per turn):** query (or a hash for private turns), the recall decision
  (selected entry addr, `mem_class`, cos, top1−top2 margin, chosen `delivery_mode`,
  deliver/decline/pass), the OUTCOME (obey/leak/decline where derivable, e.g. against a known
  corpus), the OUTPUT (text or a hash), and TIMINGS (prefill_s, decode_s, tok/s). A compact,
  fixed schema (CONTRACT §Telemetry-Schema).
* **Substrate — ride what exists:** the **PoUW ledger** mints a 64-byte `SpinorReceipt` per
  decision (the tamper-evident audit envelope, addr = join key); the RICH record lives in a
  `type: telemetry` **telemetry-okf** bundle (JSONL, one line/turn) joined to the receipt by
  addr. `okf_validate` covers the bundle; `LEDGER.md`-style `log.md` gives the timeline.
* **Channel — the SSE metadata lane:** the engine emits a structured `telemetry` event on
  `events_tx` alongside the token deltas; the harness `StreamProcessor` (which already parses
  inline tags) SINKS it into the telemetry-okf store / Nexus. Same lane the model uses to emit
  `[MEM_CLASS:…]`. One channel, engine+harness.
* **PRIVACY IS A FIRST LAW (Decision 2b):** a `private-secret` turn logs the DECISION and the
  CLASS, **never the secret value** — the `mem_class` drives redaction at the emit site (the
  value is replaced by a salted hash). Telemetry can never become a leak the delivery path forbade.
* **Uses (why we collect it):** (1) **tune** — τ / margin / class-default sweeps from real
  distributions instead of the V3 fixture; (2) **finetune** — query→correct-delivery and
  text→correct-class pairs are a training set (a future classifier or a delivery-obey model);
  (3) **drift** — obey/leak/latency over time surface regressions the gates can't; (4) **feed**
  the adaptive classifier (Decision 3) and the tuning of ADR-004's class defaults.

## 4. Decision 3 — ADAPTIVE CLASSIFICATION (tiered, telemetry-driven, head deferred)

**Classification is a pipeline, not a single call — fast where it must be, accurate where it can be:**

1. **Heuristic at capture (instant, hot-path):** the deterministic `classify_mem_class`
   (private-secret / persona / counterfact) — so a memory is IMMEDIATELY usable and safe (a
   secret is walled off at once).
2. **NIGHTSHIFT model-refine (accurate, idle, off hot-path):** the agency/NIGHTSHIFT loop, on
   idle, re-reads recently-captured concepts and RE-CLASSIFIES via a model call ("classify this
   memory: private-secret | persona | counterfact | fact | preference | episodic-event | …"),
   rewriting `mem_class` in the concept's OKF frontmatter (which the reconciler then re-serves).
   This is "return to the offline NIGHTSHIFT" — a model call is fine when it's not on the turn.
3. **Model-emitted tag (free signal):** on the store turn, the model MAY emit `[MEM_CLASS:…]`
   inline; the `StreamProcessor` extracts it as a third vote. Costs nothing extra.
4. **Learned head — DEFERRED, data-gated:** telemetry logs the heuristic verdict, the NIGHTSHIFT
   verdict, and the tag; ONLY if the accumulated data shows a cheap learned classifier would beat
   the heuristic on the hot path do we train one (classification is more separable than selection
   — the veto head hit 0.90 AUC — so this may pay off, but we let the data decide, not a guess).

Conflict resolution follows ADR-004's **safety-monotone** rule: the strictest applicable class
wins (anything votes private-secret ⇒ private-secret).

## 5. Decision 4 — PERSONALITY as first-class

Two personas, both `system`-delivery, distinct:
* **agent-persona** — the agent's own identity/voice. Sourced from the live-editable `persona.md`
  (loaded per turn, no restart) AND `mem_class: persona` memories about the agent → composed into
  the system prompt.
* **user-persona / preference** — facts about the USER (`persona`/`preference` class,
  `supplements` authority) → delivered when relevant, not asserted over world knowledge.

The classifier (Decision 3) separates them by voice ("my name is" = user; agent-identity phrasing
= agent). Personality thus rides the same policy machinery — no special case.

## 6. Surface-area map (what each decision touches)

| decision | engine | harness | store |
|---|---|---|---|
| reconcile | idle thread + `/v1/memory` (`routes.rs`/`daemon.rs`) | agency loop signals; POST on `remember()` | `full/` mtime + `supersedes` |
| telemetry | `events_tx` emit + PoUW receipt (`pouw_ledger.rs`) | `StreamProcessor` sink → Nexus / telemetry-okf | `type: telemetry` bundle |
| classify | heuristic (`recall.rs`) | agency model-refine; `[MEM_CLASS]` tag | rewrite `mem_class` frontmatter |
| personality | `system` delivery (exists) | `persona.md` + persona memories | `mem_class: persona` |

## 7. Speed & safety budget (non-negotiable)

* **Hot path unchanged.** Reconcile + classify-refine + telemetry-emit are OFF the token path
  (idle thread / post-stream event). The per-turn add is ONE small `events_tx` send + ONE 64B
  receipt — sub-millisecond. No new forward on the answer path.
* **Default-off / null-floor everywhere.** `SP_MEM_OKF_STORE` (reconcile), `SP_TELEMETRY`
  (flywheel), `SP_MEM_CLASSIFY` (classify) each unset ⇒ byte-identical to today.
* **Privacy before data.** No telemetry write of a private-secret value, ever (Decision 2b).

## 8. Status / honesty
DESIGN. Every component it composes is BUILT (PoUW ledger, events_tx, StreamProcessor, Nexus,
agency loop, persona.md, the store-merge). What is NEW is the composition + the telemetry schema
+ the reconciler thread + the `/v1/memory` endpoint. The learned-classifier head is explicitly
NOT built now — it is data-gated on the telemetry the flywheel collects. Phases + gates:
CONTRACT-LIVING-MEMORY.
