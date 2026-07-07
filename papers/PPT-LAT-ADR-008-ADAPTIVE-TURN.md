---
type: design
title: "ADR-008 — The Adaptive, Observable Turn: toolset selection, wired recall, and the receipt ring"
description: "Completes the ADR-007 Spine into a product turn: (1) ADAPTIVE TOOLING — a toolset decider picks WHICH ≤6 tools the turn advertises (coding/memory/core, deterministic keyword routing, null-floor on plain chat), so the banked '≤6 or the 12B stalls' constraint becomes 'the RIGHT 6 per turn'; (2) RECALL WIRED — the ADR-007 ranked-recall decider now injects matched facts as a system note in the gateway turn (SP_SPINE_RECALL=1, default-off) and emits a typed {recall} SSE event, gated LIVE for faithfulness (matched → fact stated; foreign → abstains, clean parametric answer); (3) THE RECEIPT RING — every spine decision (decide→execute→verify verdict) lands in an observable ring buffer served at /v1/spine and rendered as a panel pane: the operator can watch the organism decide. All default-off; null floor = wave-3 behavior."
tags: [design, adr, spine, toolset, recall, receipts, observability, sse, gateway, faithfulness]
timestamp: 2026-07-08T00:00:00Z
resource: shannon-prime-lattice/papers/PPT-LAT-ADR-008-ADAPTIVE-TURN.md
sp_status: "REALIZED: offline 12/12 (G-PK2-SPINE-2); live recall faithfulness gate G-PK2-RECALL-LIVE (see receipt)"
sp_gate: "G-PK2-SPINE-2 (offline) + G-PK2-RECALL-LIVE (live, daemon+gateway)"
sp_commit: "opens on harness 6cbfa61 (wave 3 spine)"
sp_repro: "python tests/g_pk2_spine2_offline.py; live: run_console.bat + _pk2_recall_gateway.bat + python -u tests/g_pk2_recall_live.py"
---

# ADR-008 — The Adaptive, Observable Turn

**Status: REALIZED.** Builds on ADR-007 (the Harness Spine) and ADR-006 (verify law).

## 1. Decision 1 — ADAPTIVE TOOLING (the toolset decider)

The banked lesson says a 12B picks reliably from ≤6 tools and stalls exploring 14. Wave 2 fixed
the COUNT; this fixes the CONTENT: a pre-turn `toolset_decider` (priority 10, deterministic
keyword routing, no model call) classifies the user's message — coding words → the focused
coding 6 (`read/write/edit_file/search/run_tests/run_command`), memory words → the memory set,
anything else → **no decision** (the caller's default set = null floor). A wrong pick degrades
to `load_tools` discovery, never to hard failure. Armed by `SP_SPINE_TOOLSET=1` in the gateway;
the chosen tier is emitted as a typed `{"toolset": tier}` SSE event.

## 2. Decision 2 — RECALL, WIRED AND GATED LIVE

ADR-007 built the ranked-recall decider but left wiring opt-in pending a faithfulness gate.
This ADR wires it (`SP_SPINE_RECALL=1`): matched facts are injected as a SYSTEM note
("use them faithfully; never contradict") immediately before the user's message, and a typed
`{"recall": facts}` event makes the injection observable. The live gate (G-PK2-RECALL-LIVE)
checks the two faithfulness poles on the real 12B through the gateway: a matched query must
fire the event AND state the fact; a foreign query must NOT fire and must answer cleanly from
parametric knowledge (no hijack). This is the harness-side text-in-context complement to the
engine's L5 path — when L5 is armed (`run_console_faithful.bat`), leave SP_SPINE_RECALL off
(one recall authority at a time; composing both is future work with its own gate).

## 3. Decision 3 — THE RECEIPT RING (observability)

`run_spine` now appends every receipt to a bounded ring (200), served at **`/v1/spine`** and
rendered as an operator-panel pane: decider → kind → verified|VERIFY_FAIL|unverified, result,
latency. The ADR-006 law is only as good as its visibility — a VERIFY_FAIL that no one sees is
a silent lie with extra steps. Now it's a red row on the panel.

## 4. Surfaces

`harness/control/spine.py` (+ring, +toolset_decider/toolset_for, +run_pre_turn),
`harness/server/app.py` (pre-turn wiring, `{recall}`/`{toolset}` events, `/v1/spine`),
`operator.html` (spine-receipts pane). Flags: `SP_SPINE_RECALL`, `SP_SPINE_TOOLSET`
(both default-off). Launcher: engine `_pk2_recall_gateway.bat` (the armed gateway).

## 5. Honest scope / next

Toolset routing is keyword-coarse by design (deterministic, zero latency); a learned router is
future work only if the coarse one measurably mispicks. The recall/L5 composition (both armed)
is explicitly ungated. Next seams for deciders: task-loop step policy, NIGHTSHIFT admission,
tool-argument validation. Next for the ring: persist to telemetry-okf (ADR-005 flywheel) so
receipts survive restarts.
