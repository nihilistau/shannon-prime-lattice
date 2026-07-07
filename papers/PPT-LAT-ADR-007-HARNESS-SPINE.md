---
type: design
title: "ADR-007 — The Harness Spine: decide → execute → verify as the agent's one pipeline"
description: "Ports the engine Spine (ADR-002, spine.rs: immutable LatentView → priority-folded Deciders → discrete LatentDecision → Executor) into the harness, where the same logic had scattered (persona tags in an interceptor, hygiene inline in the agency tick, recall ad-hoc) — and adds the stage ADR-006 made law: a VERIFIER that re-checks the executor's own claim. One tiny fold (TurnView → Deciders → Decisions → Executors → Verifiers → SpineReceipts), three stock deciders realized (persona_tags post-turn, hygiene on the KAIROS tick, ranked-recall pre-turn), receipts on every decision. The gateway's post-turn persona shift and the agency tick's hygiene now run THROUGH the spine; a VERIFIED persona shift emits a live {persona, changed:true} SSE event so the UI chip updates mid-conversation. Additive: nothing changes unless a caller routes through run_spine."
tags: [design, adr, spine, decide-execute, verify, harness, personality, memory, hygiene, recall, sse, receipts]
timestamp: 2026-07-07T00:00:00Z
resource: shannon-prime-lattice/papers/PPT-LAT-ADR-007-HARNESS-SPINE.md
sp_status: "REALIZED (offline-GREEN): spine + persona/hygiene deciders wired (gateway post-turn, agency tick); recall decider built, wiring opt-in"
sp_gate: "G-PK2-SPINE (offline) + G-PK2-SSE-V2 (persona-change event) — harness tests/"
sp_commit: "opens on harness cf42f99 (wave 2); builds on ADR-002 (engine Spine) + ADR-006 (verify law)"
sp_repro: "python tests/g_pk2_spine_offline.py"
---

# ADR-007 — The Harness Spine

**Status: REALIZED (offline-GREEN) for the persona + hygiene seams; recall decider built, wiring
opt-in.** Builds on **ADR-002** (the engine Spine) and **ADR-006** (verify-before-accept).

## 1. Context

The engine's `spine.rs` proved the shape (G-SPINE-ONECONFIG, byte-for-byte with inline): an
immutable **LatentView** folded through priority-ordered **Deciders** into a discrete
**LatentDecision**, applied by an **Executor** the deciders cannot touch — a compiler-enforced
boundary that collapsed a ~1500-line env-branch ladder. The harness, meanwhile, accreted the
same decision logic in scattered forms: persona tags parsed in `PersonalityStateInterceptor`,
registry hygiene inline in the agency tick, recall ad-hoc per call-site. Scattered decisions
can't be receipted, prioritized, or verified uniformly.

## 2. Decision — one tiny fold, plus the Verifier stage

`harness/control/spine.py`:

    TurnView (frozen: phase pre|post|tick, user_text, reply)
      → Decider.decide(view) -> [Decision(kind, payload)]     # pure, CANNOT side-effect
      → executors[kind](decision) -> result                    # the only side-effecting stage
      → verifiers[kind](decision, result) -> bool              # ADR-006: check the claim
      → SpineReceipt(kind, decider, ok, verified, result, ms)  # every decision auditable

It is a fold, not a framework: ~150 lines, no registry, no inheritance tax. The **Verifier** is
the stage the engine Spine doesn't have yet — the executor's success is re-checked against the
world (re-read persona.md; re-run verify_registry), and a failed check is an honest
`VERIFY_FAIL` receipt, never a silent lie. This is ADR-006's law made structural.

## 3. The stock deciders (realized)

- **persona_tags (post-turn, prio 30):** reply carries `[MOOD:]/[VOICE:]/[TRAIT:±]` →
  `persona_shift` decision → executor = the existing `apply_personality_tags` (PF-B3 — reused,
  not rebuilt) → verifier re-parses persona.md and confirms the tagged mood/voice actually
  landed. Wired into the gateway: after the streamed answer, a VERIFIED shift emits a final
  `{"persona": state, "changed": true}` SSE event — the UI chip updates mid-conversation.
- **hygiene (tick, prio 40):** `verify_registry` says NEEDS COMPACTION → `compact_registry`
  decision → verifier re-runs the report and confirms clean. The agency tick now routes through
  `run_tick()` (receipts in the on_round stream) instead of inline calls.
- **recall (pre-turn, prio 20, opt-in):** ranked token-overlap memory search
  (`search_memories_ranked`, new) over the user's message → `inject_recall` decision carrying
  the top facts. The executor is a marker (prompt assembly is the caller's); wiring into the
  gateway prompt is deliberately opt-in — the engine's L5 path stays authoritative when armed.

## 4. Memory expansion riding this ADR

`search_memories(query)` (ranked, scales past the `list_memories` dump) + `memory_stats()`
(count / provenance mix / minted fraction). Tool tiering respects the banked ≤6-tools rule:
the HOT chat set stays `[list, count, remember, forget]`; provenance/search/stats live in the
OKFS extra tier (`load_tools` on demand).

## 5. SSE additions riding this ADR

- `{"hb": ts}` keep-alive every 5s while the agent computes (a long prefill no longer looks
  dead); pure-delta clients never see it.
- `{"persona": state, "changed": true}` on a verified mid-conversation persona shift.
- Console `index.html` now renders tool cards (`{tool}`), the personality chip (`{persona}`),
  and pulses on heartbeats — the operator can watch the organism think.

## 6. Honest scope / next

Persona + hygiene seams are spine-routed and gated offline; recall wiring is opt-in and ungated
live (faithfulness interactions with the engine L5 path need their own gate before default-on).
The engine Spine and the harness Spine are mirrors, not one implementation — unifying them
(e.g. the harness posting decisions to an engine `/v1/spine` surface) is future work, as is
promoting more seams (task-loop step policy, tool-set selection, NIGHTSHIFT admission) into
deciders. The fold is deliberately boring; the value is receipts + the verify stage everywhere.
