---
type: session-handoff
title: SESSION PLAN — lat-16-3-hedge-rework (bench corrections)
description: "Date: 2026-05-29"
tags: [session-handoff]
timestamp: 2026-05-28T18:11:31Z
resource: shannon-prime-lattice/papers/SESSION-PLAN-lat-16-3-hedge-rework.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# SESSION PLAN — lat-16-3-hedge-rework (bench corrections)
**Date:** 2026-05-29  
**Prior session:** `lat-16-3-hedge` (1727f88, 4f62fd6, 7d38aa8) shipped the persistent pool migration; bench at 7d38aa8 used 1MB arena via `sp_alloc_channel_pair` (silent malloc fallback path).  
**This session scope:** Bench-only rework. Arena 1MB→128MB; direct `sp_alloc_huge` with hard-abort + diagnostic. Three commits total (plan, bench, closure), not five.

---

## 1. Stage 0a — Audit Table (honest)

| File | At 416417b | At 7d38aa8 (current HEAD) | This Session |
|---|---|---|---|
| `include/sp/sp_channel.h` | single-thread PREFETCH+LOAD sigs | persistent-pool API (sp_hedge_pool typedef + create/destroy + read_pair/read_spinor) | **KEEP** — already correct |
| `core/sp_channel/sp_hedge.c` | inline PREFETCH+LOAD bodies | persistent worker pool (`hedged_reader.hpp:124,138-152` pattern); atomic-acquire spin → memcpy → fetch_add | **KEEP** — already correct |
| `core/sp_channel/test_sp_hedge.c` | 5 tests on plain malloc (channel-independent bitwise) | 5 tests on the pool API (POOL_CREATE_DESTROY / PAIR_1 / SPINOR_1 / N1_FALLBACK / REPEATED) — all PASS | **KEEP** — 49 checks PASS |
| `core/sp_channel/bench_sp_hedge.c` | flat-array PREFETCH bench | pool-based bench, **but** uses `sp_alloc_channel_pair` (8 MB 4-page arena, indirect, can silently fall back to malloc); N_ELEM = 131072 = 1 MB ≪ Beast Canyon 24 MB L3 | **REWRITE** |
| `core/sp_channel/CMakeLists.txt` | target list | unchanged | **KEEP** |

**Outcome:** Of 4 source files in the audit, 3 are KEEP and 1 is REWRITE. The original session prompt anticipated 5 commits (plan + 2 impl + bench + closure); this session is 3 commits (plan + bench + closure) because the implementation work landed in the prior session.

---

## 2. Stage 0b — Reference Summary

### `hedged_reader.hpp` (TailSlayer)
- **L7**: `<thread>` + `<atomic>` — multi-threaded, atomic signals
- **L23-25**: `CORE_MEAS_A=11, CORE_MEAS_B=12, CORE_MAIN=14` — dedicated cores for workers + main isolation
- **L28**: detail:: namespace (TSC/LFENCE/CLFLUSH) is "timing examples for dev purposes" — NOT production
- **L122-127**: `start_workers()` — persistent threads spawned at create
- **L138-152**: `worker_func` — pin_to_core once, wait_work, compute addr, final_work(*addr)
- **L155**: `workers_{}` array held for pool lifetime

The persistent-pool architecture is in tree (commit 1727f88). This rework does NOT touch the pool architecture.

---

## 3. Bench Redesign — Three Corrections + 1-Page Diagnostic

### Correction 1: Arena size scaled past L3

Per the spec amendment patch in this session's prompt:
- Beast Canyon i9-11900KB L3 = 24 MB (Intel ARK)
- Formula: `N_ELEM × 8 ≥ 4 × L3_size = 96 MB`
- Use 128 MB per side for clean margin: `N_ELEM = 16 × 1024 × 1024 = 16M elements`
- Allocation: `sp_alloc_huge(64, 2*1024*1024)` per side (64 × 2MB huge pages = 128 MB)

### Correction 2: Direct `sp_alloc_huge` + hard-abort

Replace `sp_alloc_channel_pair` (which has silent malloc fallback at line 654 of `sp_channel_map.c`) with two direct `sp_alloc_huge(64, 2MB)` calls per side. On failure: hard-abort with diagnostic distinguishing privilege vs fragmentation:

```c
/* Pre-flight: 1-page probe to distinguish privilege from fragmentation */
void *probe = sp_alloc_huge(1, hp_size);
if (!probe) {
    /* 1-page fails → privilege issue (SeLockMemoryPrivilege missing or token stale) */
    print "M_TS_HEDGE_PROD: REQUIRES_LIVE_MODE — privilege not granted"
    print "  Fix: secpol.msc → User Rights → Lock Pages in Memory → add account → logoff+logon"
    exit 0;
}
sp_free_huge(probe, 1, hp_size);

/* Full allocation: 64 pages × 2 MB per side */
arena_a = sp_alloc_huge(64, hp_size);
arena_b = sp_alloc_huge(64, hp_size);
if (!arena_a || !arena_b) {
    /* 1-page OK but 64-page fails → Hyper-V SLAT fragmentation */
    print "M_TS_HEDGE_PROD: REQUIRES_LIVE_MODE — 64-page allocation failed (1-page OK)"
    print "  Fix: reboot fresh; run bench early in uptime to defragment"
    print "       OR temporarily flip Hyper-V off (bcdedit /set hypervisorlaunchtype off; reboot)"
    cleanup; exit 0;
}
```

`sp_alloc_huge` already prints `GetLastError()` internally (sp_channel_map.c:233-235); the bench's role is to interpret the failure mode (1-page vs 64-page).

### Correction 3: Pre-fault (already in tree, preserve)

`memset(arena_a, 0x42, 128MB); memset(arena_b, 0xBE, 128MB)` immediately after allocation. Mandatory to evict first-access page-fault latency outliers from timing samples.

### Channel-of sampling (for the closure note's clarity)

Before the bench loop, sample `sp_channel_of(m, arena_a + i*64)` for i in {0, 16384, 32768, ...} and print the distribution. Channel-diversity at cache-line granularity is what the hedge benefits from; the arena base address's channel placement is NOT the operative property.

---

## 4. Expected Outcome (arithmetic before measurement)

The previous session's F2 finding (per-element pool overhead) is NOT addressed by the arena-size change. Per-element pool round-trip cost on Tiger Lake:

- atomic release × 2 (publish to two workers) + worker memcpy + fetch_add release + caller acquire-spin until completion==2 + caller memcpy × 2 from worker_local
- Empirical cost: ~300 cycles per call (cache-coherence round-trip + acquire-spin latency)

For N_ELEM = 16M (16,777,216) iterations:
- Baseline (sequential prefetched reads): ~1.7 cyc/element × 16M ≈ 28M cycles
- Hedge total: 16M × 300 cycles ≈ 5.0G cycles
- **Predicted ratio: ~150-200× SLOWER** (same magnitude finding as prior 662×; both bigger arenas push baseline further into DRAM but per-element overhead scales linearly with N_ELEM too)

**Honest prediction filed in plan:** the bench will FAIL with ratio ~150-200×. The finding then reproduces and confirms F2: the per-element bench loop measures pool overhead, not channel-parallel DRAM throughput. The correct bench is **batch reads** (one pool call per trial, workers do bulk memcpy of 64MB-per-worker simultaneously) — which is the §16.3.1 batch API work item filed at the end of the prior session's closure.

If the prediction is wrong (bench surprises with PASS or WEAK), the closure note has the frame. If it confirms, the closure note is "F2 reproduced at 128 MB arena; batch API §16.3.1 confirmed as the right unblock."

---

## 5. Sub-tag Taxonomy (revised)

- `lat-phase-16-3-hedge-correctness-closed` — already issued at the prior session's `4f62fd6` (T_HEDGE 5/5 PASS, 49 checks); not re-issued
- `lat-phase-16-3-hedge-pool-closed` — already issued at the prior session's `1727f88` (persistent pool lifecycle clean); not re-issued
- `lat-phase-16-3-hedge-rework-bench-closed` — new sub-tag for this session's bench rework
- `lat-phase-16-3-hedge-throughput-closed` — gated on §16.3.1 batch API (separate session); NOT issued this run

---

## 6. CMake + CI

No changes. `bench_sp_hedge.c` is already a CMake target; rewriting the file does not change the target list. `cargo test` does not exercise sp_channel; T_HEDGE remains the gate for that area and is unchanged.
