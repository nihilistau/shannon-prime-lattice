---
type: audit
title: "AUDIT 2026-07-10 (part 2) — agent stack, tool calling, UI, FastMCP layer, ADR-011/012 disposition"
description: "Why 'none of the agentic abilities work': the gateway wasn't in the request path. Fence-drift tool-parse fix for the reason model; FastMCP server + bridge; console gateway-autodetect + persona editor; ADR-012 committed (ordered submodule→engine)."
tags: [audit, agent, tool-calling, mcp, fastmcp, gateway, ui, adr-011, adr-012]
sp_status: GREEN
sp_gate: "G-MCP-SERVER 3/3; parser fence-drift 5/5; G-PK2-TOOLROBUST 10/10; G-PK2-SPINE 9/9; G-PK2-SPINE-2 12/12; smoke 10/10; live gateway tool round observed on the daemon log (n=1494→1746 tool_output feedback)"
sp_commit: "harness 97489b4; engine 4d307fd; math-core submodule 36c2da3"
sp_repro: "run_console_agent.bat; python tests/h_mcp_server.py; gateway_probe (typed SSE)"
---

# AUDIT 2026-07-10 (part 2) — agent stack, UI, MCP, ADR-011/012

## 1. Root cause: "ephemeral tool calling / spine / python / coding / agentic = dead"

**Nothing in the agent code was broken.** The entire agentic stack (run_with_tools
ephemeral tool calling, ADR-007 spine, coding tools, task loop, typed SSE with tool
cards, persona endpoints) lives in the harness gateway on **:8800** — and the gateway
was not in the request path:

- The console (served by the daemon at :3000) posts chat to `location.origin` = :3000
  unless `localStorage['sp_chat_endpoint']` is manually set. The daemon's `/v1/chat`
  is a plain token streamer: no tool execution, no `{tool}`/`{persona}` events.
- Result: the model (prompted by nothing, but SFT-primed) emits `tool_code` fences
  that stream **verbatim into the transcript** — the "fabricated tool calls" — and
  no cards ever render.
- `operator.html` (the only persona editor) targets :8800 unconditionally; with no
  gateway process, every load/save fails → "personality editing stopped working".
- The old `run_gateway.bat` armed NOTHING (`SP_SPINE_TOOLSET`/`SP_SPINE_RECALL`/
  `SP_PERSONALITY` all unset) and pointed memory at the stale `_seed_corpus`
  registry, so even a running gateway was half-blind.

## 2. Second real defect: fence drift on the reason model

Live probing through the armed gateway exposed a genuine parser gap: the
reason-SFT model emits fence **variants** — ```` ``` tool_code ```` (space after the
backticks) and ` ```python ` fences wrapping tool calls. The old detector
(`"```tool" in text`) and parser (`^```tool_code` exact) missed both → the fence
streamed raw even on :8800. **Fixed** (harness 97489b4):

- `_TOOLCODE_RE` is space-tolerant; new `_ANYFENCE_RE` accepts `python`/`py`/`tool`
  fences whose parsed call names are **known tools only** (genuine code-example
  answers still pass through untouched).
- `agent_chat_stream`: any fence-leading generation is a tool CANDIDATE resolved by
  the parser at generation end (unparsed fences flush as-is; cost = fence-leading
  answers are flushed whole rather than token-streamed).
- Malformed-fence recovery triggers on the space variant too.
- Parser unit gate 5/5; G-PK2-TOOLROBUST still 10/10; live: the daemon log shows the
  tool round executing (prompt n=1494 → n=1746 with ```tool_output``` fed back).

## 3. Fixes + new capability shipped

- **`run_gateway_system.bat`** — armed gateway (:8800): `SP_SPINE_TOOLSET=1`,
  `SP_SPINE_RECALL=1`, `SP_PERSONALITY=1`, `SP_MCP_TOOLS=1`, production
  `_memory_live` registry.
- **`run_console_agent.bat`** — one-shot stack: daemon (reason model) + gateway.
- **Console gateway-autodetect** (index.html): probes `:8800/health` every 8s and
  routes chat there when up (manual `sp_chat_endpoint` still wins). Header pill
  shows `agent · :8800` vs `direct · :3000`. `{recall}`/`{toolset}`/`{authority}`
  typed events now render as note cards; tool cards unchanged.
- **Persona editing in the main console**: right-pane personality panel (live
  voice/mood/trait chips, polled + event-driven) + a full persona.md editor modal
  (GET/POST `/v1/persona`, provenance-recorded). operator.html still works as before.
- **FastMCP layer** (harness `harness/mcp_server/`, MCP-README.md):
  `python -m harness.mcp_server` exposes the system's hands (fs/shell/powershell/
  python/web_search/web_fetch/get_time/memory + `custom_tools.py`) to ANY MCP
  client; the **bridge** (`mcp_servers.json` + `SP_MCP_TOOLS=1`) mounts external
  MCP servers' tools into the served model's tool loop (native names win; extras
  land in the load-on-demand tier so the ≤6-tool rule holds). New tools:
  `get_time`, `web_fetch`, `disk_free` (example custom). Gate **G-MCP-SERVER 3/3**.

## 4. ADR-011/012 disposition — COMMITTED (ordered), not removed

ADR-011 (FFN-only CPU offload) was already committed. ADR-012 (contiguous
full-layer CPU tail, `SP_G4_CPU_TAIL_FULL`) sat uncommitted with a dirty submodule.
Review: code complete and clean, default-off with a **provable byte-identical null
floor** (flag unset ⇒ original path untouched), honest-negative on speed (K=8 3.14
tok/s vs FFN-only 3.25 — sync-bound hypothesis refuted) but a real gated VRAM
lever, and the ADR-012 doc had already shipped in lattice. Committed in the required
order: math-core submodule `36c2da3` → engine pointer + `cuda_forward.cu` `4d307fd`.

**Binary drift note:** `sp-daemon.exe` (built 07-08 23:03) predates the last daemon
src commit (`837fb5f`, 07-09) while containing the then-uncommitted ADR-012 code.
A clean rebuild reconciles both — do it at the next natural daemon restart
(delete sp-daemon.exe first; cargo won't relink on a .cu-only change).

## 5. Multi-head status (from the wiring audit)

SpecTest veto: wired + armed in the reason/everything launchers, head file present
(15,384 B). B3-WC selector: wired, deliberately unarmed in daily launchers
(superseded by L5). Route head: wired, weights present, unarmed (telepathy not in
the daily serve). INT-2: wired, unarmed (algorithmic, no weights). No missing
weight files; no dead flags found.

## 6. Known residuals / follow-ups

1. Agent-gateway turns are slow (~2-5 min with tool rounds): each round re-prefills
   a ~1.5k-token tool preamble; SP_PERSIST_KV reuse doesn't apply across the
   tool_output extension pattern. The roadmap's O(1)-conversation-KV work is the
   real fix.
2. `SP_AGENCY_TASKS` scheduler (`run_agency.py`) is not started by any launcher —
   posted goals sit pending unless it runs; add to `run_console_agent.bat` if the
   task queue becomes daily-use.
3. The daemon binary rebuild (§4).
4. Gateway `/v1/chat` non-typed fallback for legacy clients is untouched.
