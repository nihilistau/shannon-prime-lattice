---
type: contract
title: "CONTRACT — PRODUCT KEYSTONE-2: from organism to product"
description: "The post-KEYSTONE product campaign (2026-07-07): unblock the prefill stall, expand the harness into a real coding/agentic system, tighten the tiered memory into MEM-OKF v2, and grow the personality + served UI into a product surface. Four tranches, each gated, each default-off = null floor."
tags: [contract, campaign, product, harness, agency, memory, mem-okf, persona, ui, prefill]
timestamp: 2026-07-07T00:00:00Z
resource: shannon-prime-lattice
sp_status: ACTIVE
sp_gate: "G-PK2-* (per-tranche, §T1–§T4)"
sp_commit: TBD
sp_repro: "per-tranche DONE-WHEN commands, §T1–§T4"
---

# CONTRACT — PRODUCT KEYSTONE-2

> Foundation: [PPT-LAT-KEYSTONE.md](PPT-LAT-KEYSTONE.md) (the organism, ~90% built, live).
> This contract is the campaign that turns the organism into a **product**: robust under real
> load, able to *do work* (code, tools, agency), with memory it can trust and a face worth using.
> Discipline unchanged: receipts-first, pre-registered gates, default-off = byte-identical null
> floor, no number without a command + a row.

## 0. Priorities (operator, 2026-07-07)

1. Coding / agentic functionality
2. Expand the harness system
3. Expand the personality system
4. Tighten + expand the memory system (MEM-OKF v2)
5. Expand the UI

Cross-cutting surfaces named: ADR-002..005, XBAR, NIGHTSHIFT, L5, decoder, execute, KAIROS,
the Spine, the heads, Telepathy, SSE, the inject seam.

## T1 — PREFILL STALL (the root blocker; do first)

**Problem** (`project_daemon_prefill_stall`, engine `START-HERE-prefill-stall.md`): daemon
prefill wedges forever at n≈1000–1700 tokens. max_tokens=1 also stalls ⇒ PREFILL. Blocks the
agent gateway (persona+tools ≈ >1000-tok prompts) and long chats — i.e. blocks priorities 1–3.

**Diagnosis targets** (recon 2026-07-07, `cuda_forward.cu`):
- H1: kernel-launch error is *silent* until the `cudaStreamSynchronize` at the end of
  `gemma4_kv_prefill` (~:4630); the launch-check at ~:4364 reads `cudaGetLastError` too late.
- H2: per-token prefill loop queues n×~48-layer kernel launches (~85k at n=1765) with **zero
  intermediate sync** — stream-queue exhaustion wedges the driver.
- H3: `attn_shm = Pmax*4` shared-memory sizing / Pmax bound.

**Fix shape:** periodic mini-sync (every 256 tokens) inside the prefill loop + pre-launch error
check + Pmax/shm validation at open. All engine-local, no ABI change.

**DONE-WHEN (G-PK2-PREFILL):** `SP_WORDS=1300 python tests\perf\_g_bigprompt_probe.py` →
`got_DONE=True`; then n=299 regression still GREEN; then gateway `_g_memory_check.py` on :8800
completes. Receipt `tests/perf/G-PK2-PREFILL.log`.

## T2 — CODING / AGENTIC + HARNESS EXPANSION

The harness already has: ephemeral `<tool>` calling (`run_with_tools`), memory/conversation
tools, system tools (shell/python/web/file), sandboxed coding tools, the agency round +
KAIROS scheduler, the :8800 gateway (persona live-read). Expansion = **depth + robustness**:

- **E1 Agentic task loop:** a `run_task(goal)` multi-step loop (plan → act → observe → check),
  bounded steps + budget, task state persisted to MEM-OKF (resumable), honest failure surface.
- **E2 Coding campaign tools:** workspace-scoped edit (anchored find/replace, not whole-file),
  patch-apply + diff receipt, test-runner tool (`run_pytest`), git status/diff (read-only first).
- **E3 Robustness:** malformed-tool-call recovery (re-prompt with the parse error, N retries),
  tool timeout + output truncation tiers (head+tail), loop/no-progress detector.
- **E4 KAIROS agency growth:** the maintenance round gains a *work queue* (operator-posted tasks
  the organism advances on ticks), receipted per tick.

**DONE-WHEN:** G-PK2-TASKLOOP (a 3-step coding task — write module + test, run tests, fix a
seeded failure — completes E2E on the live 12B through the gateway); G-PK2-TOOLROBUST (seeded
malformed/timeout/looping tool scenarios all recovered, receipts); existing H1–H7 stay GREEN.

## T3 — MEMORY: MEM-OKF v2

- **M1 Provenance lane** (vision `emergent_provenance`): every registry fact + MEM-OKF record
  carries `src` (turn/episode/operator/consolidator + timestamp); recall recites provenance on
  demand ("where did I learn that?").
- **M2 Extraction hardening:** consolidator pulls convo facts into MID reliably (dedupe via
  token-overlap vs registry before append; the DECIDE/MERGE layer already handles conflicts).
- **M3 Registry hygiene:** compaction pass (drop superseded/forgotten tombstones), integrity
  check tool (`okf_mem verify`), size/age telemetry in `/v1/metrics`.
- **M4 Tier plumbing:** `recall_conversations` quality pass + capabilities corpus refresh; keep
  the Jaccard @0.6 verifier as the production gate (26B cascade stays retired).

**DONE-WHEN:** G-PK2-PROVENANCE (fact stored → "where did you learn X?" → correct source
recited); G-PK2-MEMHYGIENE (verify tool GREEN on live stores; compaction preserves recall on a
before/after probe set); G-FORGET/G-DECIDE/G-MERGE regression GREEN.

## T4 — PERSONALITY + UI

- **P1 Persona:** structured `persona.md` v2 (identity / voice / values / self-knowledge
  sections), gateway hot-reload (exists) + a persona *editor* in the console; persona changes
  are memory events (provenance: operator-set).
- **P2 Self-knowledge:** capabilities corpus refresh post-T2 (the organism can state its own
  new tools), seeded via `_seed_capabilities.py`.
- **U1 Console v2 (`index.html`):** tool-call display (render `<tool>` calls + results as
  cards in the stream), memory browser pane (registry facts + MEM-OKF LUT, read-only first),
  persona editor textarea (POST to gateway), SSE robustness (reconnect, abort button wired).
- **U2 Telemetry pane:** /v1/metrics poll (VRAM, tok/s, memory counts).

**DONE-WHEN:** G-PK2-UI (chat + tool cards + memory pane + persona edit round-trip live on
:8800/:3000); G-PK2-PERSONA (persona edit → next turn reflects it → provenance recorded).

## Order & rules

T1 → T2 → (T3 ∥ T4). Git ops native PowerShell only (mount CRLF-churns). Large-file reads on
the mount truncate — verify via native tools. One daemon at a time (12B fills the 2060).
Pre-flight `okf_mem lookup` before building any new capability. Every mechanism lands behind a
default-off flag or additive endpoint; the null floor is byte-identical.
