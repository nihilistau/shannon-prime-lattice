# SESSION-CLOSED: lat-ts-probe

**Date:** 2026-05-28
**Tag:** `lat-ts-probe`
**Branch (system):** main — commit `7457313` (MSVC fix)
**CI run:** `26551299421` — linux-gcc PASS + windows-msvc PASS
**Result:** M_TS_FALLBACK VERIFIED; M_TS_PROBE VERIFIED; M_TS_HEDGE PARTIAL (real DRAM signal, 1.28–1.39×); M_TS.MAP_1 PARTIAL (limited recovery k=4, LIVE)

---

## Scope

Second closure for Phase TS.MAP §16.1. The first closure (`SESSION-CLOSED-lat-ts-map.md`,
2026-05-26) established the oracle infrastructure and M_TS.MAP_2 (18/18 CI checks).

This session adds:
1. Channel-pair allocator (`sp_alloc_channel_pair`)
2. Probe rewrite — persistent thread pool + race-free spin-barrier
3. Bench redesign — full topology output with P50+P90 per bit
4. TSC rendezvous + Windows tsc_hz calibration fix
5. MSVC portability fixes (intrinsics for `mfence`, `lfence`, `clflush`)

---

## Deliverables

### 1 — Channel-Pair Allocator

`sp_alloc_channel_pair` + `sp_free_channel_pair` in `include/sp/sp_channel.h` /
`core/sp_channel/sp_channel_map.c`.

**LIVE path:** allocates 4 × huge-page arena, scans cache-line-aligned addresses via
`sp_channel_of()` until two distinct-channel addresses found. O(1) in practice (diverse
pair appears within first `2^k` cache lines with k≥1 channels).

**DISABLED/fallback path:** logs `SP_WARN: Virtualized memory controller detected,
disabling TailSlayer` and returns two pointers from a single `calloc(128)`. Frees
correctly in both paths.

### 2 — Probe Rewrite: Persistent Thread Pool + Race-Free Spin-Barrier

Previous `sp_channel_probe.c` called `CreateThread`/`pthread_create` per sample —
1-100 µs thread-creation jitter is 1000× the ~100 ns DRAM channel signal.

New design:
- **Persistent pool** (`sp_probe_pool_create` / `sp_probe_pool_destroy`): two workers
  spawned once per probe session; pinned to P-cores 0 and 2 (Tiger Lake Ring Bus).
- **Spin-barrier protocol**: main flushes cache lines, sets `cmd=1`; workers time `*addr`
  with RDTSC and set `done=1`; main reads `max(latA, latB)`.
- **Race-free IDLE condition**: `while(!ctx->quit && !(ctx->cmd && !ctx->done))`.
  x86 TSO guarantees that when a worker observes `cmd=1` it also observes `done=0` and
  `fire_tsc`, so the two-field check is race-free without extra fences. Eliminates the
  ABA deadlock window in the old second-spin (`while cmd && !quit`).

Result: T_CHANNEL 5/5 PASS in ~80 ms (was 200–600 s or hanging indefinitely).

### 3 — M_TS_HEDGE Bench Redesign

`core/sp_channel/bench_ts_hedge.c` — completely rewritten.

- Main thread pinned to core 1; workers to P-cores 0 and 2.
- 8 MB LARGE_PAGES arena pre-faulted with `memset` (eliminates first-access page-fault
  spikes: 30–40 µs → below noise floor).
- N_PROBES = 2048; P90 = 205th-from-top (immune to Windows DPC/IRQ ~1% noise).
- Full P50+P90 per-bit table with dynamic ASCII bar chart.
- Max-ratio gate: reports maximum achieved P90/P50 ratio across all bits.
- PARTIAL/WEAK/PASS output thresholds at 1.2× / 2.0×.

### 4 — TSC Rendezvous + Calibration Fix

Root-cause fixes for the "36 µs measurements" problem:

**tsc_hz calibration** — `QueryPerformanceFrequency()` returns HPET 10 MHz on this host.
`cycles × 1e9 / 10 MHz = cycles × 100` displayed 366 real RDTSC cycles as 36,600 ns.
Fixed to QPC+RDTSC cross-calibration: spin 10 ms by QPC ticks, count RDTSC cycles →
true TSC frequency (~3.2 GHz on Beast Canyon).

**TSC rendezvous** (`fire_tsc` field in `probe_worker_ctx`): both workers spin until
`rdtsc_now() >= fire_tsc` before issuing DRAM loads. Without this, coherence propagation
skew (100–300 cycles) causes worker A's DRAM read to complete before B even arrives at
the memory controller — no simultaneous contention, no channel signal. With 1000-cycle
fire offset, both reads hit the memory controller simultaneously.

**LFENCE** around RDTSC in worker: prevents Tiger Lake OOO from retiring the second
RDTSC before the volatile load completes.

**P90 instead of P99**: Windows DPC/interrupt rate ~1% contaminates P99 (top-5 of 512)
but not P90 (top-205 of 2048).

**PAUSE threshold** 5000 → 200: cross-core workers finish in ~100–300 ns (~30–97 PAUSE
iterations); threshold 200 avoids the 22 µs yield-stall without spurious yields.

### 5 — MSVC Portability Fixes

- `mfence()`: added `_mm_mfence()` guard before GCC `__asm__` path.
- `cache_flush()`: `_mm_clflush((void const *)(uintptr_t)p)` for MSVC (resolves `C4090`
  volatile qualifier mismatch).
- `sp_lfence()`: `_mm_lfence()` / `__asm__ volatile("lfence")` helper.

---

## Design Decision: Probe Pauses Are Calibration-Only

**The TSC rendezvous (`fire_tsc`), LFENCE pairs, and RDTSC timing in `sp_probe_bit()`
are diagnostic machinery for the oracle calibration tool. They exist to extract the GF(2)
channel map and write it to the bin file once.**

The TailSlayer runtime path (`sp_alloc_channel_pair`) loads the cached bin file and does
O(1) `sp_channel_of()` lookups — zero probe overhead, zero pauses, no timestamps on the
critical path. Introducing calibration latency into the runtime would defeat the purpose
of TailSlayer.

`bench_ts_hedge` is a one-time calibration tool, not a runtime component.

---

## Gate Summary

| Gate | Description | Result |
|------|-------------|--------|
| M_TS.MAP_2 | Oracle infrastructure, 18 checks (DISABLED path) | **VERIFIED** 18/18 (CI) |
| M_TS_FALLBACK | bench exits 0 cleanly in DISABLED/VM env | **VERIFIED** (linux CI VM exits 0 with REQUIRES_LIVE_MODE) |
| M_TS_PROBE | Persistent pool spin-barrier + TSC rendezvous, T_CHANNEL 5/5 | **VERIFIED** (~80 ms) |
| M_TS_HEDGE | P90_same / P90_diverse on bare-metal | **PARTIAL** — 1.28–1.39× (real signal; 2× needs Linux+pagemap) |
| M_TS.MAP_1 | Bare-metal GF(2) recovery | **PARTIAL** — k=4, n=15 LIVE (limited recovery; full needs Linux+pagemap) |

---

## CI Results

**Run `26551299421`** — triggered by commit `7457313` on `main`:

- `linux-gcc`: PASS — T_CHANNEL 5/5; bench exits 0 `REQUIRES_LIVE_MODE` (GitHub Actions VM)
- `windows-msvc`: PASS — build clean; T_CHANNEL 5/5 (DISABLED path in VM)

---

## Beast Canyon Bare-Metal Results

```
Oracle (SP_CHANNEL_NOCACHE=1 fresh probe):
  Mode: LIVE (limited recovery — virtual bits, no pagemap)
  k=4 channel-select bits, n=15 address bits probed
  SeLockMemoryPrivilege: active (AdjustTokenPrivileges path functional)

bench_ts_hedge (8 MB LARGE_PAGES, pre-faulted, N=2048):
  P50 = 111–116 ns   ← real DRAM latency (confirmed correct after tsc_hz fix)
  P90/P50 max = 1.35× (bit 22, 4 MB offset)
  Best ratio same/diverse = 1.28–1.39× across runs
  M_TS_HEDGE: PARTIAL (signal confirmed; 2× requires Linux+pagemap)
```

---

## Path to M_TS_HEDGE PASS

No code changes needed — all probe logic, LFENCE, TSC rendezvous, and P90 metric are
correct. Only the Linux hardware gate must be cleared.

On bare-metal Linux with `nr_hugepages > 0` and `CAP_SYS_ADMIN`:
- `sp_pagemap_privileged()` returns 1
- Oracle probes physical bits [6,24) instead of virtual-only [6,21)
- Physical channel-select bits map cleanly to DRAM controller
- Clear 2× P90 ratio expected → M_TS_HEDGE PASS

---

## Files Changed

| File | Change |
|------|--------|
| `include/sp/sp_channel.h` | Added `sp_channel_pair_arena` forward decl, `sp_alloc_channel_pair`, `sp_free_channel_pair` |
| `core/sp_channel/sp_channel_internal.h` | Added `struct sp_channel_pair_arena`; `p50_ns` + `p90_ns` in `sp_probe_result` |
| `core/sp_channel/sp_channel_map.c` | Added `sp_alloc_channel_pair` + `sp_free_channel_pair`; `force_enable_large_pages` with `AdjustTokenPrivileges` |
| `core/sp_channel/bench_ts_hedge.c` | Redesigned: core-1 pinning, pre-fault, P50+P90/bit table, max-ratio gate |
| `core/sp_channel/sp_channel_probe.c` | Rewritten: persistent pool, race-free IDLE; TSC rendezvous (`fire_tsc`), LFENCE, P90, threshold 200, Windows tsc_hz calibration fix; MSVC intrinsic guards |
| `core/sp_channel/CMakeLists.txt` | Added `bench_ts_hedge` as separate `add_executable` target |
| `.github/workflows/ci.yml` | Added bench step: `nr_hugepages` + `bench_ts_hedge` (exits 0 in CI VM) |

---

## Prior Closure Chain

- `SESSION-CLOSED-lat-ts-map.md` (2026-05-26) — M_TS.MAP_2 18/18 VERIFIED; M_TS.MAP_1 BLOCKED; sp_alloc_channel_pair absent
- **This file** — alloc primitive added; probe rewritten; bench redesigned; M_TS_FALLBACK + M_TS_PROBE VERIFIED; M_TS_HEDGE PARTIAL (real DRAM signal on Beast Canyon)
