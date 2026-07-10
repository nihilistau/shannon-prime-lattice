---
type: memory
title: AUDIT 2026-07-10 pt2: agentic stack was gateway-wiring dead + reason-model fence drift; FastMCP layer shipped; ADR-012 committed
description: Agentic abilities dead = gateway :8800 not in the path (console posts :3000; run_gateway.bat armed nothing) PLUS reason-model fence drift ('` tool_code' space / '`python' wrappers) the parser rejected. Fixed both; console now autodetects the gateway + has a persona editor; FastMCP server+bridge shipped (G-MCP-SERVER 3/3); live-verified {tool}/{recall} events + real execution. ADR-012 committed ordered (36c2da3->4d307fd). Residual: model garbles numeric tool results when paraphrasing.
timestamp: 2026-07-10T03:09:53Z
resource: harness 97489b4; engine 4d307fd; math-core 36c2da3; lattice ef6cb18
sp_status: GREEN
sp_gate: G-MCP-SERVER 3/3 + live gateway probe (tool event + execution) + toolrobust/spine/smoke suites held
sp_commit: harness 97489b4; engine 4d307fd; math-core 36c2da3; lattice ef6cb18
sp_repro: run_console_agent.bat; python tests/h_mcp_server.py; gateway_probe.py
mem_kind: agent
mem_addr: 6baa9fa3efef7b2a
mem_verified: unverified
mem_lifecycle: active
tags: [audit-2026-07-10-pt2, agent stack, gateway 8800, tool calling dead, fence drift, tool_code space, python fence, run_gateway_system, run_console_agent, fastmcp, mcp server, mcp bridge, SP_MCP_TOOLS, gateway autodetect, persona editor, ADR-012 committed, numeric transcription residual, agent, tier-2]
mem_tier: full
---

AUDIT 2026-07-10 part 2 (agent stack / UI / MCP / ADR-012): user-reported "ephemeral tool calling, spine, python calls, coding, agentic abilities do not work at all; tool cards + persona editing gone".
ROOT CAUSE 1 (wiring, not code): the ENTIRE agentic stack lives in the harness gateway :8800; the console posts to :3000 unless localStorage sp_chat_endpoint is set, and no launcher started an ARMED gateway (run_gateway.bat arms nothing + points memory at stale _seed_corpus). Daemon /v1/chat streams raw model text -> tool_code fences visible ("fabricated tool calls"), no {tool}/{persona} events, operator.html persona editor dead against a missing :8800.
ROOT CAUSE 2 (real parser gap, found live): the reason-SFT model drifts fences - '``` tool_code' (space) and '```python' around tool calls; old detector ("```tool" in s) + strict regex missed both -> fence streamed raw EVEN through the gateway. FIX (harness 97489b4): space-tolerant _TOOLCODE_RE; _ANYFENCE_RE accepts python/py/tool fences ONLY when parsed call names are known tools (code-example answers pass through); agent_chat_stream treats any fence-leading generation as a tool candidate resolved by the parser; malformed-recovery matches the space variant. Parser gate 5/5, G-PK2-TOOLROBUST 10/10 held.
SHIPPED: run_gateway_system.bat (armed: SP_SPINE_TOOLSET+SP_SPINE_RECALL+SP_PERSONALITY+SP_MCP_TOOLS, production registry); run_console_agent.bat (one-shot daemon+gateway); console gateway-AUTODETECT (probes :8800/health, agent/direct pill, manual override wins) + persona panel with live chips + persona.md editor modal (GET/POST /v1/persona) + {recall}/{toolset}/{authority} note cards.
FASTMCP LAYER (harness/mcp_server, MCP-README.md, gate h_mcp_server.py G-MCP-SERVER 3/3): FastMCP server exposes system tools (fs/shell/powershell/run_python/web_search/web_fetch/get_time/memory + custom_tools.py auto-registered) to any MCP client; bridge.py mounts mcp_servers.json servers' tools into run_with_tools via SP_MCP_TOOLS=1 (native names win; extras land in the load-on-demand tier so the <=6-tool rule holds). New native tools get_time/web_fetch. fastmcp 3.4.4 installed host-side.
LIVE VERIFIED through the armed gateway on the reason model: Q1 get_time -> {tool} typed event (the UI card) + tool-derived answer; Q2 '```python run_python(...)' fence-drift case -> parsed, EXECUTED, {recall}+{tool} events; persona GET/POST green.
HONEST RESIDUALS: (1) the reason model GARBLES numeric tool results when paraphrasing (said 3334 for a tool-printed 3304; reformatted+wrong time) at temp 0.6/rep 1.3 - plumbing green, transcription fidelity is a model-quality issue (candidate fixes: verbatim-echo rule tightening, temp drop on post-tool round); (2) agent turns are slow (~2-5 min: ~1.5k-token tool preamble re-prefilled every round; O(1)-convo-KV is the real fix); (3) SP_AGENCY_TASKS scheduler not started by any launcher; (4) sp-daemon.exe predates commit 837fb5f while containing then-uncommitted ADR-012 code - rebuild at next restart (delete exe first, .cu-only changes do not relink).
ADR-012 DISPOSITION = COMMITTED (not removed): code complete, default-off SP_G4_CPU_TAIL_FULL with provable byte-identical null floor, honest-negative on speed, real VRAM lever; ordered commit math-core 36c2da3 -> engine 4d307fd (submodule-first, clears -dirty pointer).
