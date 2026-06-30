---
type: memory
title: P2-A recalibrated ring-ON: ~40K resident ceiling (was ~24K ring-off/broken)
description: Ring-ON (after the set_var->KvOpenCfg fix, engine 0478345): Pmax=40000 ring_W=1024 allocates clean (used 11985/77 free MiB, edge). Ring-OFF 40K OOM'd because the 40 SWA layers were full-cache (~6.4GB@40K); ring-ON SWA fixed ~167MB. Resident ceiling ~40K hard / ~36K safe (was ~24K measured ring-off). 8 global layers (32KB/tok) are the O(n) floor beyond 40K => P3 global eviction is the path past 40K.
timestamp: 2026-06-30T12:30:49Z
resource: engine 0478345
sp_status: GREEN
sp_gate: 1 targeted daemon load (Pmax=40000 ring-on, no OOM)
sp_commit: engine 0478345
sp_repro: SP_DAEMON_KVDECODE_RING_W=1024 SP_DAEMON_KVDECODE_PMAX=40000 -> register OK + RING mode
mem_kind: agent
mem_addr: f135f0fdce7e1cd0
tags: [P2-A, VRAM, ceiling, ring, Pmax, 40000, recalibrated, 2060, OKV, agent, tier-2]
mem_tier: full
---

P2-A recalibrated (ring-ON, engine 0478345): Pmax=40000 ring_W=1024 ALLOCATES clean (RING mode fires, register OK, used 11985 MiB / 77 free = the edge). Ring-OFF 40K OOM'd (40 SWA full-cache ~6.4GB at 40K); ring-ON SWA fixed ~167MB. So resident ceiling ~40K HARD (safe ~36K), up from the ~24K measured ring-off (silently broken). Globals (8 layers x 4KB/tok = 32KB/tok) are the O(n) floor beyond ~40K -> P3 global eviction is the path past 40K.
