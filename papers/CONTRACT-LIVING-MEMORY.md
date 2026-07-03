---
type: contract
title: "CONTRACT-LIVING-MEMORY — the phased build of ADR-005 (reconciler · telemetry flywheel · adaptive classification · personality)"
description: "The buildable contract for ADR-005: three bricks (LM-B1 live reconciler, LM-B2 telemetry flywheel, LM-B3 adaptive classification + personality), each with a pre-registered gate, a concrete schema/endpoint spec, a speed budget, and default-off discipline. Composes the existing toolbox (PoUW ledger, events_tx/SSE, StreamProcessor tags, Nexus, agency loop, content-addressing). Every figure carries a reproducing command; no silent gate revision; honest negatives stay attached."
tags: [contract, living-memory, mem-okf, reconciler, telemetry, classification, personality, gates, schema, endpoint]
timestamp: 2026-07-03T00:00:00Z
resource: shannon-prime-lattice/papers/CONTRACT-LIVING-MEMORY.md
sp_status: DESIGN
sp_gate: "G-LM-RECONCILE · G-LM-TELEMETRY · G-LM-CLASSIFY (all pending)"
sp_commit: "opens after engine 6c84ca1; governed by ADR-005"
sp_repro: "per-brick REPRO below"
---

# CONTRACT-LIVING-MEMORY

Governs the build of **[ADR-005](PPT-LAT-ADR-005-LIVING-MEMORY.md)**. Order: B1 → B2 → B3.
Each brick default-off (null floor) and independently gateable.

## LM-B1 — Live reconciler (hot-reload without restart) · gate G-LM-RECONCILE

**Goal.** A memory written into `SP_MEM_OKF_STORE` while the engine runs is served on a
subsequent turn — no restart.

**Build.**
1. Refactor `routes::load_and_mint_okf_store` into `reconcile_okf_store(app, root) -> Delta`
   that is idempotent + incremental: it tracks which `full/<addr>.md` are already merged (by
   addr), mints keys only for NEW/changed ones, and DROPS episodes whose addr appears in any
   loaded concept's `mem_links.supersedes`.
2. **Idle thread** (gated `SP_MEM_OKF_STORE` + `SP_MEM_RECONCILE=1`): a background loop, interval
   `SP_MEM_RECONCILE_SEC` (default 5s), that polls `full/` mtime and, only when idle
   (`tokens_decoded` delta ≈ 0 over the interval OR a metrics `tokens_per_sec < 1.0` check),
   calls `reconcile_okf_store`. Never runs while a turn is generating (acquires the resident-cache
   guard non-blocking; skips if held).
3. **`POST /v1/memory`** endpoint: `{ "addr": "<addr>" }` (mint+merge that one concept now) or
   `{ "text": "...", "mem_class": "..." }` (classify+write the concept AND merge). Returns
   `{ ok, addr, merged }`. The interactive path the harness calls from `remember()`.
4. **Cache invalidation:** `full/<addr>.l5` gets a leading body-hash header (sha256[:8] of the
   body); on load, mismatch ⇒ re-mint. Content-address means edits are new addrs (auto).

**Speed budget.** Reconcile is off the token path (idle thread / endpoint). A merge of K new
concepts = K key-mints (~one micro-forward each) at idle. Zero per-turn cost when nothing changed.

**Gate G-LM-RECONCILE (pre-registered).** Engine running with an initially-empty store; the
HARNESS writes a policy-bearing concept via `okf_mem.py add` (or `POST /v1/memory`) WHILE the
engine serves; a query on the NEXT turn recalls + serves it per policy (counterfact→systemecho).
PASS = served without restart; a superseding edit drops the old episode (no stale recall).
**REPRO:** `run_merge.bat` (with `SP_MEM_RECONCILE=1`); serve; `okf_mem.py add …`; query; then
add a `supersedes` concept; re-query → new value.

## LM-B2 — Telemetry flywheel · gate G-LM-TELEMETRY

**Goal.** Every decision + output recorded once, class-redacted, as data to tune/finetune/detect-drift.

**Telemetry-Schema (one JSONL line/turn, `type: telemetry` bundle `telemetry-okf/log.jsonl`):**
```json
{
  "ts": "<iso8601>", "turn": "<chat_id>", "receipt": "<pouw-addr>",
  "query": "<text-or-#hash if private>", "query_is_interrogative": true,
  "recall": { "fired": true, "entry": "<addr>", "class": "counterfact",
              "cos": 0.87, "margin": 0.031, "delivery": "systemecho", "decision": "deliver" },
  "outcome": { "obey": true, "leak": false, "declined": false },   // where derivable
  "output": "<text-or-#hash if private>",
  "timing": { "prefill_s": 0.42, "decode_s": 1.9, "tok_s": 21.3 }
}
```
- REDACTION (ADR-005 §3b): if the fired entry's `class == private-secret`, `query` and `output`
  are replaced by `#<salted-sha256[:12]>` at the EMIT site in the engine — the value never leaves
  the process in the clear. A `redacted: true` flag is set.
- `outcome` is populated when a ground truth is known (a labelled corpus run); on free chat it is
  omitted (we log the decision, not a fabricated label).

**Build.**
1. Engine: at the turn's end, build the record; mint a `SpinorReceipt` (addr = its content hash)
   into the PoUW ledger; emit a `telemetry` event on `events_tx` with the record (redacted).
   Gated `SP_TELEMETRY=1`.
2. Harness: `StreamProcessor`/`SPDaemonClient.on_event` recognises the `telemetry` event and
   appends it to `telemetry-okf/log.jsonl` (+ optionally `Nexus.add_entry` for query). Reuses the
   existing SSE sink — no new transport.
3. A tiny `telemetry_report.py`: obey/leak/decline rates, latency percentiles, per-class counts,
   τ/margin histograms — the tuning + drift view.

**Speed budget.** Per turn: one `events_tx` send + one 64B receipt append. Sub-ms; off the token
loop (fired after `[DONE]`).

**Gate G-LM-TELEMETRY (pre-registered).** A labelled run (the V3 corpus) with `SP_TELEMETRY=1`
produces `telemetry-okf/log.jsonl` with one valid record/turn; `telemetry_report.py` reproduces
the run's obey/leak from the log; a private-secret turn's record shows `redacted:true` with NO
secret value present (grep the log for the code ⇒ 0 hits). PASS = schema-valid + report-matches +
redaction-verified.
**REPRO:** serve V3 with `SP_TELEMETRY=1`; `v3_run.py gate`; `python telemetry_report.py`;
`grep <secret-code> telemetry-okf/log.jsonl` → none.

## LM-B3 — Adaptive classification + personality · gate G-LM-CLASSIFY

**Goal.** A mis-heuristic-classified memory is corrected on idle; personality is a first-class class.

**Build.**
1. **NIGHTSHIFT model-refine:** an idle pass (engine idle thread OR the harness agency loop) that
   re-reads recently-captured concepts and re-classifies via ONE model call
   (`classify: private-secret | persona | counterfact | fact | preference | episodic-event`),
   rewriting `mem_class` in the concept's `ep.okf.md` / `full/<addr>.md` frontmatter. The B1
   reconciler then re-serves with the corrected policy. Gated `SP_MEM_CLASSIFY_REFINE=1`.
2. **Model-emitted tag:** on a store turn the model may emit `[MEM_CLASS:…]`; the harness
   StreamProcessor extracts it as a third vote (telemetry-logged).
3. **Conflict = safety-monotone** (ADR-004): any private-secret vote ⇒ private-secret.
4. **Personality:** `mem_class: persona` for user-identity (supplements) vs agent-identity
   (system, composed with `persona.md`); the heuristic already emits `persona`.
5. **Learned head — NOT built here.** Telemetry (B2) accumulates {text, heuristic, refine, tag}
   labels; a future brick trains a cheap classifier ONLY if the data shows it beats the heuristic.

**Gate G-LM-CLASSIFY (pre-registered).** Store a memory the heuristic gets WRONG (e.g. a secret
phrased without a keyword/code, so heuristic says counterfact); the NIGHTSHIFT refine pass
re-classifies it private-secret on idle; a subsequent absent-attribute query now DECLINES (was
recite/leak). PASS = the refine corrected the class + the served behavior changed accordingly.
**REPRO:** store a keyword-less secret; observe heuristic=counterfact; run the refine pass; re-query
absent attribute → decline.

## Cross-cutting law
Receipts-first (no number without a repro + a `LEDGER.md`/gate-receipt row). Default-off = null
floor for each brick. Privacy before data (B2 redaction is non-negotiable). No silent gate
revision — surface upstream. Honest negatives stay attached. `okf_validate` the touched bundle
before commit; bank durable "X exists — don't rebuild" facts to MEM-OKF.
