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
tags: [audit-2026-07-10-pt2, agent stack, gateway 8800, tool calling dead, fence drift, tool_code space, python fence, run_gateway_system, run_console_agent, fastmcp, mcp server, mcp bridge, SP_MCP_TOOLS, gateway autodetect, persona editor, ADR-012 committed, numeric transcription residual, agent, tier-1]
mem_tier: summary
mem_full: 6baa9fa3efef7b2a
---

# AUDIT 2026-07-10 pt2: agentic stack was gateway-wiring dead + reason-model fence drift; FastMCP layer shipped; ADR-012 committed

Agentic abilities dead = gateway :8800 not in the path (console posts :3000; run_gateway.bat armed nothing) PLUS reason-model fence drift ('` tool_code' space / '`python' wrappers) the parser rejected. Fixed both; console now autodetects the gateway + has a persona editor; FastMCP server+bridge shipped (G-MCP-SERVER 3/3); live-verified {tool}/{recall} events + real execution. ADR-012 committed ordered (36c2da3->4d307fd). Residual: model garbles numeric tool results when paraphrasing.

Full context: [full/6baa9fa3efef7b2a.md](../full/6baa9fa3efef7b2a.md)
