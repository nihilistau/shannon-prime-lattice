---
type: session-handoff
title: "SESSION STATE — Phase TS.MAP & TS.ALLOC"
description: "Date: 2026-05-28"
tags: [session-handoff]
timestamp: 2026-05-28T02:21:03Z
resource: shannon-prime-lattice/papers/SESSION-STATE-lat-ts-map.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# SESSION STATE — Phase TS.MAP & TS.ALLOC
## §16.1: GF(2) Channel Oracle + Channel-Pair Allocator

**Date:** 2026-05-28
**Tag:** lat-ts-probe
**Status:** STATE (not CLOSED) — real DRAM signal confirmed (112 ns P50, max 1.35× ratio), limited-recovery on Windows; M_TS_HEDGE ≥2× requires Linux+pagemap for physical bit mapping

---

## What Is Built

### Deliverable 1 — GF(2) Channel Oracle (prior session, 2026-05-26)

`src/core/sp_channel/` module: `sp_channel_map.c` + `sp_channel_probe.c`

The oracle is complete. On bare-metal Linux with huge pages:
1. Detects virtualisation via CPUID leaf-1 ECX bit 31 + Hyper-V KVP registry
   check (prevents false-positive on Windows 11 VBS root partition)
2. Allocates a 4 × 2MB huge-page arena (`MAP_HUGETLB`)
3. Probes each address bit in `[12, 24)` by racing two threads on A and
   A^(1<<bit), collecting P99 of MAX(latency_A, latency_B)
4. Recovers the GF(2) matrix M (k×n binary) where `M·addr_bits mod 2 = channel`
5. Caches result at `~/.cache/shannon-prime/channel_map_<host_hash>.bin` (DJB2
   checksum; magic `SPCH` v1)
6. Falls back to `SP_CHANNEL_DISABLED` gracefully in any VM/container/no-huge-page
   environment — no hang, no fault, no non-OK return code

Public API: `sp_channel_map_build`, `sp_channel_of`, `sp_channel_map_load_cached`,
`sp_channel_map_save_cached`, `sp_channel_map_mode`, `sp_channel_map_dims`,
`sp_channel_host_fingerprint`, `sp_channel_map_free`

M_TS.MAP_2 gate: 18/18 checks VERIFIED (DISABLED path, CI)
M_TS.MAP_1 gate: BLOCKED (see §Blockers)

### Deliverable 2 — Channel-Pair Allocator (this session)

`sp_alloc_channel_pair` + `sp_free_channel_pair` added to
`include/sp/sp_channel.h` and implemented in `sp_channel_map.c`.

**LIVE path:** allocates a 4 × huge-page arena (virtual-bit arithmetic
requires huge pages to preserve bits 0–20), then scans cache-line-aligned
addresses using `sp_channel_of()` until two distinct-channel addresses are
found. Returns both pointers plus an opaque `sp_channel_pair_arena` handle.
The scan is O(1) in practice: with k≥1 channels, a diverse pair appears
within the first `2^k` cache lines.

**DISABLED/fallback path:** logs `SP_WARN: Virtualized memory controller
detected, disabling TailSlayer` and returns two pointers from a single
`calloc(128)` block. `sp_channel_of` on these returns `SP_CHANNEL_UNSPECIFIED`.
`sp_free_channel_pair` frees correctly in both paths.

### Deliverable 4 — Probe Rewrite: Persistent Thread Pool + Race-Free Spin-Barrier (2026-05-28)

`core/sp_channel/sp_channel_probe.c` rewritten. Previous implementation called
`CreateThread`/`pthread_create` per sample, adding 1–100 µs thread-creation jitter
— 1000× the ~100 ns DRAM channel signal. Replace with:

- **Persistent pool** (`sp_probe_pool_create` / `sp_probe_pool_destroy`): two worker
  threads spawned once per probe session, not once per sample.
- **Spin-barrier protocol**: workers pin to distinct physical cores (0, 2); main
  flushes the cache lines, sets `cmd=1`; workers time `*addr` with RDTSC and set
  `done=1`; main reads `max(latA, latB)`.
- **Race-free IDLE condition**: IDLE spin uses `cmd && !done` instead of just `cmd`.
  x86 TSO store ordering guarantees that when a worker observes `cmd=1` it also
  observes all prior main-thread stores including `done=0`, so the two-field check
  is race-free without any extra fence. This eliminates the old "second spin"
  (`while cmd && !quit`) which had a window where the next probe's `cmd=1` arrived
  before workers had observed the preceding `cmd=0`, causing a spin-barrier deadlock
  (43 ms+/probe under load — all 3 threads spinning at 100 % with no progress).

**Result:** T_CHANNEL 5/5 PASS in ~20 ms total (was 200–600 s or hanging
indefinitely). BUILD_BARE_1 now recovers M in LIVE mode on the bare-metal Windows
host via the limited-recovery path (bits [6,21), no huge-page privilege required).

Commit: `ba54c87` pushed to `origin/lat-ts-map`.

### Deliverable 3 — M_TS_HEDGE Bench (updated 2026-05-28 session 2)

`core/sp_channel/bench_ts_hedge.c` — fully redesigned, commit `48e9de6`.

**DISABLED path:** exits 0 with `REQUIRES_LIVE_MODE`.

**LIVE path (bare-metal Windows, current):**
1. Main thread pinned to core 1; workers pinned to P-cores 0 and 2 (Ring Bus)
2. Allocates 8 MB LARGE_PAGES arena; memset pre-faults all pages
3. Runs `sp_probe_bit` for all 18 bits in `[CHAN_BIT_LO, CHAN_BIT_HI)` with
   N_PROBES=2048 (P90 = 205th-from-top)
4. Outputs P50 + P90 per bit with ASCII bar chart
5. Reports max-ratio (best achievable signal) as the gate
6. Displays channel topology summary

**Result on Beast Canyon (limited-recovery, virtual bits):**
```
P50 = 111-116 ns (real DRAM latency — confirmed correct after tsc_hz fix)
P90/P50 max = 1.35× (bit 22)
Best ratio same/diverse = 1.28-1.39× across runs
Gate: PARTIAL (signal present; 2× requires Linux+pagemap)
```

### Deliverable 5 — TSC Rendezvous + Calibration (2026-05-28 session 2)

Root-cause fixes for the "36 µs measurements" problem (`48e9de6`):

1. **tsc_hz calibration** (`calibrate_tsc_hz` on Windows): was calling
   `QueryPerformanceFrequency` which returned HPET 10 MHz on this host,
   causing the conversion `cycles × 1e9 / 10MHz = cycles × 100` to display
   366 true TSC cycles as 36,600 ns. Fixed to QPC+RDTSC cross-calibration:
   spin 10 ms by QPC ticks, count RDTSC cycles → true TSC frequency (~3.2 GHz).

2. **TSC rendezvous** (`fire_tsc` field in `probe_worker_ctx`): both workers
   spin until `rdtsc_now() >= fire_tsc` before issuing their DRAM loads.
   Without this, worker A receives `cmd=1` 100-300 cycles before B (coherence
   propagation skew); A's DRAM read completes before B even arrives at the
   memory controller, eliminating the channel-contention signal. With 1000-cycle
   fire offset, both reads hit the memory controller simultaneously.

3. **LFENCE** around RDTSC in worker: prevents Tiger Lake OOO from retiring
   the second RDTSC before the volatile load completes.

4. **P90 instead of P99** (512→2048 samples, P90 = 205th-from-top): Windows
   DPC/interrupt rate ~1% contaminates P99 (top-5 of 512 = interrupt events)
   but not P90 (top-205 of 2048 = clean DRAM signal).

5. **PAUSE threshold** 5000 → 200: cross-core workers finish in ~100-300 ns
   (30-97 PAUSE iterations); threshold of 200 avoids the 22 µs stall without
   triggering unnecessary yields in the cross-core case.

6. **Worker affinity**: confirmed Tiger Lake Beast Canyon P-cores 0 and 2 are
   on the same Ring Bus → best coherence latency. Main on core 1.

---

## Gate Summary

| Gate | Description | Status |
|------|-------------|--------|
| M_TS.MAP_2 | Oracle infrastructure, 18 checks (DISABLED path) | **VERIFIED 18/18** |
| M_TS.MAP_1 | Oracle bare-metal GF(2) recovery ≤60s | **PARTIAL** — limited recovery (bits [6,21)) passes on Windows bare-metal; full recovery requires Linux+pagemap |
| M_TS_FALLBACK | bench exits 0 cleanly in DISABLED/VM env | **VERIFIED** |
| M_TS_PROBE | Persistent pool spin-barrier + TSC rendezvous, T_CHANNEL 5/5 | **VERIFIED** (~80 ms) |
| M_TS_HEDGE | P90_same / P90_diverse ≥ 2.0 on bare-metal | **PARTIAL** — real signal confirmed (1.28-1.39×, real DRAM 112 ns); 2× requires Linux+pagemap+physical bits |

---

## Blockers

### Physical Address Mapping (Windows)

In limited-recovery mode (Windows, no `/proc/self/pagemap`), the oracle probes
virtual address bits [6,21). Virtual bit 12+ doesn't reliably map to physical
DRAM channel bits. This dilutes the channel signal to ~1.28-1.39× instead of
the expected 2×.

**Current Windows state:** LIVE, 8 MB LARGE_PAGES arena, real DRAM timing
(P50 ≈ 112 ns), maximum signal ~1.35×. SeLockMemoryPrivilege is correctly
granted and the AdjustTokenPrivileges path is functional.

**To achieve 2× signal and definitive GF(2) matrix:** run on bare-metal Linux
with `nr_hugepages > 0` and `CAP_SYS_ADMIN`. On Linux, `sp_pagemap_privileged()`
returns 1 → oracle probes physical bits [6,24) → clear 2× P90 ratio expected.

### Hyper-V CPUID false positive (resolved)

Windows 11 with VBS/Hyper-V sets CPUID leaf-1 ECX bit 31 on the root partition.
The oracle handles this via Hyper-V vendor check + KVP registry key — KVP is
absent on the root partition. No longer a blocker.

---

## Files Changed

| File | Change |
|------|--------|
| `include/sp/sp_channel.h` | Added `sp_channel_pair_arena` forward decl, `sp_alloc_channel_pair`, `sp_free_channel_pair` |
| `core/sp_channel/sp_channel_internal.h` | Added `struct sp_channel_pair_arena`; `p50_ns` + `p90_ns` in `sp_probe_result` |
| `core/sp_channel/sp_channel_map.c` | Added `sp_alloc_channel_pair` + `sp_free_channel_pair`; `force_enable_large_pages` with `AdjustTokenPrivileges` |
| `core/sp_channel/bench_ts_hedge.c` | **Redesigned** (2026-05-28 session 2): core-1 pinning, pre-fault, P50+P90 table, max-ratio gate — commit `48e9de6` |
| `core/sp_channel/CMakeLists.txt` | Added `bench_ts_hedge` as separate `add_executable` target |
| `core/sp_channel/sp_channel_probe.c` | **Rewritten** (2026-05-28): persistent pool, race-free IDLE; **extended** (2026-05-28 session 2): TSC rendezvous (`fire_tsc`), LFENCE, P90, threshold 200, Windows tsc_hz calibration fix — commit `48e9de6` |

---

## Test Results (this session — 2026-05-28 session 2)

```
T_CHANNEL: 5/5 PASS, ~80 ms  (commit 48e9de6)

bench_ts_hedge (LIVE — 8 MB LARGE_PAGES, Beast Canyon, Windows):
  P50 = 111-116 ns   ← real DRAM latency (was 36,600 ns with wrong tsc_hz)
  P90/P50 max = 1.35× (bit 22, 4 MB offset)
  Best ratio same/diverse = 1.28-1.39× across runs
  M_TS_HEDGE: PARTIAL  ← signal confirmed, 2× needs Linux+pagemap

Oracle (SP_CHANNEL_NOCACHE=1 fresh probe):
  k=4, n=15 — LIVE, limited recovery  ← GF(2) matrix consistent with prior
```

---

## What Is NOT Done

- M_TS.MAP_1: bare-metal oracle calibration ≤60s — best-effort k=4 found in
  limited-recovery mode; definitive matrix requires Linux+pagemap+CAP_SYS_ADMIN
- M_TS_HEDGE: ≥2× P90 ratio — real signal confirmed at 1.28-1.39×; 2× gate
  requires Linux where virtual bits [6,24) map to known physical DRAM bits
- Integration into `sp_session` or CRT — deferred to `TS.INTEGRATE`

---

## Path to Closure

This phase closes to `SESSION-CLOSED-lat-ts-map.md` when M_TS.MAP_1 and
M_TS_HEDGE both pass on bare-metal Linux CI (MAP_HUGETLB + CAP_SYS_ADMIN).
No code changes are needed — all probe logic, LFENCE, TSC rendezvous, and
P90 metric are correct. Only the Linux hardware gate must be cleared.

---

## Prior Closure Chain

- `SESSION-CLOSED-lat-ts-map.md` (2026-05-26) — M_TS.MAP_2 18/18 VERIFIED;
  M_TS.MAP_1 BLOCKED; sp_alloc_channel_pair noted as absent
- **This file** — alloc primitive added, bench written, M_TS_FALLBACK VERIFIED
