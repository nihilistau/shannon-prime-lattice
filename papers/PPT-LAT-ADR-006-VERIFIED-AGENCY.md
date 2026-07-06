---
type: design
title: "ADR-006 — Verified Agency: the product control plane (verify-before-accept, typed SSE, the coding loop)"
description: "Turns the KEYSTONE organism into a product that can be trusted to DO work. Four decisions: (1) VERIFY-BEFORE-ACCEPT as system law — no agent 'done' claim (task loop, NIGHTSHIFT admission, DECIDE/MERGE) is accepted on the model's word; an objective predicate must pass, closing the confabulation gap found live (a 12B declared it fixed code its edit never touched). (2) The AGENTIC TASK LOOP — a bounded, resumable, receipted multi-step run_task with a work queue the KAIROS tick drains, extending the Spine's Decide→Execute to multi-turn work. (3) TYPED SSE v2 — the gateway stream carries {delta} PLUS typed {tool}/{progress}/{persona} events so the UI can render tool cards, prefill progress, and personality-state without breaking the {delta}-only contract. (4) MEM-OKF v2 as the substrate — provenance lane + hygiene as first-class, the data verify/telemetry reads. Composes the existing toolbox (Spine deciders, run_with_tools, events_tx/SSE, the agency curator, content-addressing); no new engine machinery on the hot path."
tags: [design, adr, agency, verify, task-loop, sse, tools, mem-okf, provenance, personality, spine, decide-execute, product]
timestamp: 2026-07-07T00:00:00Z
resource: shannon-prime-lattice/papers/PPT-LAT-ADR-006-VERIFIED-AGENCY.md
sp_status: DESIGN (D1/D2/D4 realized offline-GREEN this session; D3 SSE v2 phased)
sp_gate: "G-PK2-TOOLROBUST (verify-gate + task loop) · G-PK2-MEMOKF-V2 (provenance/hygiene) · G-PK2-UI-ENDPOINTS (surfaces) · G-PK2-SSE-V2 (typed events, phased) · G-PK2-PREFILL (the unblock)"
sp_commit: "opens on harness 047500a + engine 067e6b0 (PK2 wave 1); builds on ADR-005 (living memory) + ADR-002 (Decide→Execute Spine)"
sp_repro: "harness/tests/g_pk2_*_offline.py + engine/tests/perf/G-PK2-PREFILL.log"
---

# ADR-006 — Verified Agency

**Status: DESIGN, with D1/D2/D4 realized + offline-GREEN this session (PRODUCT KEYSTONE-2).**
Builds on **ADR-005** (living memory) and **ADR-002** (the Decide→Execute Spine). Where ADR-002
made a single turn a clean decision→execution and ADR-005 made memory living, ADR-006 makes the
organism a product that can be *trusted to act over many turns* — because every claim of success
is checked, not taken on faith.

## 1. Context — the gap KEYSTONE-2 exposed

The prefill unblock (G-PK2-PREFILL) let the organism finally take long, tool-laden turns. The
first thing it did with that freedom was **confabulate**: given a failing test and coding tools,
the served 12B emitted *"DONE: I've fixed the add() function"* while its `edit_file` had never
landed — the file was byte-unchanged (G-PK2-TASKLOOP-E2E, 2026-07-07). The loop had trusted the
model's word. This is not a 12B quirk; it is the general failure mode of any agent that reports
its own success. The product-grade answer is a **control plane that verifies**.

## 2. Decision 1 — VERIFY-BEFORE-ACCEPT (system law)

**No self-reported completion is accepted without an objective check.** The predicate is
supplied by the caller and is cheap and external to the model's narrative:

- **Task loop:** `run_task(verify=…)` — a `DONE:` claim is accepted only if `verify()` returns
  true (e.g. `pytest` exit 0, a file contains an anchor, an endpoint returns 200). A false claim
  is fed back verbatim ("your DONE did not pass verification — look again") and the loop
  continues. Realized + gated (G-PK2-TOOLROBUST, the verify-gate case).
- **NIGHTSHIFT admission** already embodies this (teacher-forced causal-ablation: a fact is
  admitted only if ablating it measurably degrades the forward — the fact must *earn* its place).
  ADR-006 names it as the same law: memory admission is verify-before-accept.
- **DECIDE/MERGE** (memory agency) is verify-before-accept on conflict: a supersede fires only on
  the "cannot both be true" test, not on the model's say-so.

This is the Spine principle (ADR-002) extended one level: a Decider proposes, an Executor acts,
**and a Verifier gates the executor's own claim of success.** Verification is a first-class
control-plane stage, not a prompt request ("please don't lie").

## 3. Decision 2 — THE AGENTIC TASK LOOP (multi-turn Decide→Execute)

`run_task(goal, verify, max_steps, budget_s)` — a bounded, **resumable**, receipted multi-step
loop: plan → act (one tool round) → observe → persist state → repeat, stopping on a *verified*
DONE, a BLOCKED, or the step/wall-clock budget. State is a content-addressed `TaskState` JSON
(atomic write) under `SP_TASK_ROOT`, so a crash or restart resumes from the last saved step.

- **The work queue:** `post_task` enqueues a goal; `advance_pending_task` runs the oldest one;
  the **KAIROS agency tick** drains one per idle tick (`SP_AGENCY_TASKS=1`). The organism advances
  operator-posted work between chats — the "auto rounds" of ADR-005 generalized from memory
  maintenance to arbitrary goals.
- **Tool discipline banked:** the focused ≤6-tool set (the 12B stalls exploring 14). Malformed-
  fence recovery + no-progress detection (identical call+result twice → self-break) keep a weak
  model from wedging. All realized + gated (G-PK2-TOOLROBUST 10/10).
- **Honest boundary:** the 12B reliably *drives* the loop but does not reliably *land* an
  autonomous multi-tool code edit — that is a model-capability ceiling, not a harness gap. The
  verify law means the ceiling shows up as an honest FAIL, never a confabulated pass. The lever
  is a stronger served model or a learned tool-use head (§6).

## 4. Decision 3 — TYPED SSE v2 (the product's nervous system)

Today the gateway streams `data: {"delta": "..."}`. A product UI needs to *see the organism
think*: which tool it called, how a long prefill is progressing, what its mood/voice is. SSE v2
adds **typed events on the same stream**, backward-compatible (a client that only reads `delta`
is unaffected):

| event | shape | UI render |
|---|---|---|
| token | `{"delta": "..."}` | the answer text (unchanged) |
| tool | `{"tool": {"name","args","result"}}` | a tool-call card in the stream |
| progress | `{"progress": {"stage","done","total"}}` | prefill/decode progress bar (the prefill telemetry, surfaced) |
| persona | `{"persona": {"voice","mood","traits"}}` | live personality-state chip |
| heartbeat | `{"hb": ts}` | keep-alive so a slow prefill never looks dead |

The events ride the existing `events_tx`/SSE machinery (ADR-005 §telemetry) and the `on_tool`
callback `run_with_tools` already emits. Phased gate G-PK2-SSE-V2.

## 5. Decision 4 — MEM-OKF v2 as the verified substrate

Verify and telemetry need clean, attributable memory. MEM-OKF v2 (realized this session,
G-PK2-MEMOKF-V2 6/6):

- **Provenance lane:** every fact carries `src` + `ts`; `provenance(fact)` answers "where/when
  did I learn X?". Provenance is what lets a verifier trust (or distrust) a memory, and what makes
  the telemetry flywheel (ADR-005 D2) auditable.
- **Hygiene as first-class:** `verify_registry` (malformed/dup/near-dup/unminted report) +
  `compact_registry`, run on the KAIROS tick alongside the agency round — the store curates
  itself. Near-dup admission guard keeps the extraction pass from bloating the registry.

## 6. Surface-area map (what each decision touches)

- **Task loop / verify:** `harness/control/task_loop.py` (`run_task`, `TaskState`, work queue),
  `harness/mcp/tools.py` (robustness guards). Realized.
- **SSE v2:** `harness/server/app.py` (`_native_chat_sse` typed events), `frontend_mockups/
  operator.html` + `index.html` (render). D3 phased.
- **MEM-OKF v2:** `harness/skills/memory.py` (provenance + hygiene), `conversation_memory.py`
  (consolidator provenance + capabilities self-knowledge). Realized.
- **Spine tie-in:** the Verifier is a new Spine stage class; the coding tools are Executors;
  the task loop is a Decide→Execute over many turns. No hot-path engine change.
- **Speed:** the batched packed-dp4a prefill GEMM (`SP_KV_PREFILL_DP4A`) — the cold-prefill
  bandwidth lever (keep OK_Q4B weights packed, no f32 materialization) — so long agentic prompts
  are fast, not just unblocked. Gate G-PK2-PREFILL-DP4A.

## 7. Speed & safety budget (non-negotiable)

- **Default-off is the null floor.** Every mechanism (verify, task queue, SSE v2 events, dp4a
  GEMM) is a flag or additive endpoint; unset = byte-identical to KEYSTONE-2 wave 1.
- **Verify is cheap.** A verifier that is expensive or itself a model call defeats the purpose;
  prefer deterministic external checks (exit codes, string presence, HTTP status).
- **Privacy inherited from ADR-005:** a private-secret value is never written to task state or a
  telemetry/SSE event; the decision is logged, the value is redacted.

## 8. Status / honesty

**Realized + offline-GREEN this session:** D1 verify-before-accept (task loop), D2 task loop +
work queue + robustness, D4 MEM-OKF v2 provenance/hygiene, plus the T1 prefill unblock that made
agentic turns possible and the dp4a GEMM speed lever. **Phased/next:** D3 SSE v2 typed events
(wire the gateway + UI render); the batched-under-ring prefill (so the dp4a lever helps the
production ring config, not only the cold ring-off batched path); a learned tool-use/coding head
or a stronger served model for reliable autonomous code-editing (the measured 12B ceiling).
The honest negative — a 12B cannot yet be trusted to autonomously land multi-tool code edits —
is *why* verify-before-accept is the load-bearing decision: the product is trustworthy because it
checks, not because the model is infallible.
