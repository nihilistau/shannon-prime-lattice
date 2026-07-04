---
type: contract
title: "CONTRACT — the self-modifiable Personality framework (persona + self-model, tag/decorator control, curated)"
description: "A modifiable, SELF-modifiable personality for Shannon-Prime: how it acts (traits/voice/mood/boundaries) AND a self-model (facts about ITSELF, distinct from facts about the USER). The model curates its own personality via the existing tag + @decorator systems; NIGHTSHIFT/the curator also curates it; all stored in MEM-OKF, governed by ADR-002/ADR-004. Anti-rebuild: every brick EXTENDS a named existing seam (persona.md live-load, the @skill/tool-call loop, the StreamProcessor tags, the interceptor pipeline, MCPFramework state)."
tags: [contract, personality, persona, self-model, decorators, tags, adr-004, mem-okf]
timestamp: 2026-07-03T00:00:00Z
resource: shannon-prime-lattice/papers/CONTRACT-PERSONALITY.md
sp_status: "GREEN — PF-B1..B5 built+gated (self-modifiable AND system-curatable); PF-B6 deferred"
sp_gate: "G-PF-OWNERSHIP · G-PF-PERSONA · G-PF-TAGS · G-PF-DECORATORS · G-PF-CURATE (all GREEN)"
sp_commit: "harness a1c59ea (B1) · 27c5c3b (B2) · b72ece1 (B3) · d35a723 (B4) · e35cfdf (B5)"
sp_repro: "python tests/h_personality_{ownership,persona,tags,decorators,curate}.py; MEM-OKF 6e70a998"
---

# CONTRACT — the self-modifiable Personality framework

## 0. The vision (operator, 2026-07-03) + the governing rule

Shannon-Prime should have a **personality that is both modifiable and self-modifiable**: how it acts
(traits, voice, mood, boundaries), stored in a structured, live-editable file/tags, that the MODEL
can change about itself AND the SYSTEM (NIGHTSHIFT/the curator) can curate — the same way it curates
memory. It should also hold a **self-model**: facts about ITSELF ("I can read and write memories")
as a first-class category, distinct from facts about the USER. Integrated with the tag system, the
`@skill` decorators (ephemeral tool-calling), ADR-002 (Decide→Execute), MEM-OKF, NIGHTSHIFT, XBAR.

**Governing rule (anti-rebuild).** The harness ALREADY has every seam (recon banked this session).
Each brick EXTENDS a named module; nothing is rebuilt:
- `persona.md` + `harness/agent.py:load_agent_system()` — live-editable persona, injected as the
  system prefix ("edit it and the voice changes next turn").
- `harness/skills/skill.py` `@skill` + `SKILL_REGISTRY` + `harness/mcp/tools.py:run_with_tools()` —
  the decorator + registry + tool-call loop (the model emits a call, the harness executes it).
- `harness/inference/stream_processor.py` — already EXTRACTS `[MOOD]`/`[VOICE]`/`[ACTION]`/`[STAT]`
  inline tags (but does not persist them).
- `harness/mcp/comms_framework.py` `InterceptorPipeline` (pre/post-call, priority) + `MCPFramework`
  agent/session state nodes — the place to persist + hydrate personality state.
- `harness/skills/memory.py` `remember()/forget()` + the mem_class taxonomy (ADR-004) — extend to
  self-vs-user fact ownership.
- `harness/control/agency.py` + `consolidate_conversation()` (NIGHTSHIFT) — where curation hooks.

## 1. ADR framing (why this respects the spine)

Personality is a **DECISION** (how to act / what am I), emitted as a **clean symbolic token** — a tag
(`[TRAIT:concise]`), a decorator call (`set_trait("voice","dry")`), or a mem_class label
(`self-fact`) — which the **EXECUTOR** (persona.md / PersonalityState / the store) applies. Never
fuse latent into generation (ADR-002). Self-fact vs user-fact is a mem_class/authority distinction
(ADR-004): self-facts are the agent's own; user-facts are the operator's.

## 2. The bricks

| Brick | Deliverable | Extends (anti-rebuild) | Gate |
|---|---|---|---|
| **PF-B1** | **Fact ownership: self-fact vs user-fact.** Add `self-fact` (about the model) to the mem_class taxonomy alongside `persona`/`preference` (about the user); the classifier + curator learn/apply it; `remember_self()` vs `remember()` label at capture. | `classify_mem_class` (engine) + the DF curator's LABELS + `harness/skills/memory.py` | `G-PF-OWNERSHIP`: self-fact vs user-fact classified + stored + served distinctly |
| **PF-B2** | **Structured persona.md.** A machine-parseable block (identity / traits / voice / mood / boundaries / self-model) alongside the free prose; live-editable; `load_agent_system()` parses it + injects the CURRENT state into the system prefix. | `persona.md` + `harness/agent.py:load_agent_system()` | `G-PF-PERSONA`: edit a field → next turn reflects it; malformed block = graceful fallback to prose |
| **PF-B3** | **Tag persistence (self-modify via tags).** A `PersonalityStateInterceptor` (priority ~72, post-call) reads the `[MOOD]`/`[VOICE]`/`[TRAIT]` tags StreamProcessor already extracts, persists them to a `PersonalityState` node, and hydrates them back into the next turn's system prefix — the model self-modifies its mood/voice by emitting a tag. | `StreamProcessor` tags + `comms_framework.py InterceptorPipeline` + `MCPFramework` state | `G-PF-TAGS`: model emits `[VOICE:dry]` → persisted → next turn's prompt carries voice=dry |
| **PF-B4** | **@personality decorators (model-controlled).** Mirror `@skill`: `@personality_decorator` + `PERSONALITY_REGISTRY`, advertised in `run_with_tools`, so the model can CALL `set_trait/adjust_mood/remember_self/forget_trait` to DURABLY self-modify (writes persona.md / PersonalityState). | `@skill` + `SKILL_REGISTRY` + `run_with_tools()` | `G-PF-DECORATORS`: model calls `set_trait(...)` → persona.md updated → persists across turns |
| **PF-B5 ✅ GREEN** | **Personality curation (NIGHTSHIFT + MEM-OKF).** `harness/personality/curator.py consolidate_personality()` extracts the shifts the model expressed in a transcript (reuses PF-B3 tag extraction on assistant turns), prunes/dedups stale traits, and snapshots the personality into a content-addressed `memory-okf-personality/` tier (mem_class persona / mem_owner self). Wired into `agency.py consolidate_current` gated SP_PERSONALITY. Personality is now system-curatable, not only self-modifiable. | `consolidate_conversation()` seam + MEM-OKF + PF-B3 tags | `G-PF-CURATE` GREEN (e35cfdf): transcript shifts extracted, duplicate trait pruned, OKF snapshot written |
| **PF-B6** | **Personality head (DEFERRED, engine-native).** A purpose-built head — like the tool-call head but for personality — that detects in-forward when a turn should trigger a personality update/apply (SPINE `LatentHead` or a decorator-routed classifier). Parallels the mem_class LatentHead; deferred behind the tag/decorator path (PF-B3/B4) which covers it off the hot path first. | SPINE `LatentHead` / the tool-call head | `G-PF-HEAD` (deferred) |

## 3. Order & exit

Build order: **PF-B1** (ownership — the taxonomy the rest hangs on) → **PF-B2** (structured persona)
→ **PF-B3** (tag persistence — the cheapest self-modify) → **PF-B4** (decorators — durable self-modify)
→ **PF-B5** (curation — system self-modify). **PF-B6** stays deferred (engine-native, only if
in-forward personality routing is ever needed — same call as the mem_class LatentHead).

Lives in the **harness** (persona/tags/decorators/curation are harness-native, CosySim-lineage) +
a small mem_class taxonomy touch in the engine (PF-B1). Default-off / graceful-fallback throughout.

**Exit criterion:** the model, in one live run, (a) states a personal fact vs a self-fact and each
is stored/served in its own category, (b) changes its own voice via a tag that survives to the next
turn, (c) durably sets a trait via a decorator call, and (d) has that trait curated/persisted into
the personality tier by NIGHTSHIFT — a personality that is genuinely self-modifiable AND
system-curatable, governed by the spine.
