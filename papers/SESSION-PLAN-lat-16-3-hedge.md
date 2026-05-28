# SESSION PLAN — lat-16-3-hedge (persistent-pool revision)
**Date:** 2026-05-29  
**Supersedes:** session 416417b (PREFETCH+LOAD single-thread — wrong pattern)  
**Spec revision:** PPT-LAT-Roadmap.md §16.3 amended 2026-05-29 late (commit 22e7971)

---

## 1. Reference Summary (Stage 0 reads)

### TailSlayer hedged_reader.hpp

`HedgedReader` (lines 76-218) is a C++ template that implements **multi-replica hedged reads** via a persistent worker pool:

- **Line 7**: `#include <thread>` + `#include <atomic>` — production pattern is multi-threaded, not single-thread.
- **Lines 23-25**: `CORE_MEAS_A=11`, `CORE_MEAS_B=12`, `CORE_MAIN=14` — worker threads are pinned to DEDICATED cores, separate from the caller. Affinity set ONCE at startup.
- **Line 122-127** (`start_workers`): `workers_[i] = std::thread(worker_func, this, i)` — N persistent threads spawned at pool creation, not per-read.
- **Lines 138-152** (`worker_func`): Each worker does:
  1. `pin_to_core(cores_[i])` — affinity set inside the thread function
  2. `std::size_t read_index = wait_work(WaitArgs...)` — waits for a signal (user-provided callback; in production this is the trigger that a new KV value is ready to read)
  3. `T* target_addr = get_next_logical_index_address(i, read_index)` — compute address for this worker's replica
  4. `final_work(*target_addr, WorkArgs...)` — read and process; no TSC, no LFENCE
- **Lines 154-155**: `std::array<int, N> cores_{}; std::array<std::thread, N> workers_{}` — both arrays held for pool lifetime.
- **Line 29** (detail:: comment): "These functions are really only used as timing examples for dev purposes" — the TSC/LFENCE/CLFLUSH machinery is diagnostic only, not on the production hot path.

### Mapping to math-core C99

| Laurie (C++) | Math-core (C99) |
|---|---|
| `std::atomic<T*>` | `_Atomic(const void *)` via `<stdatomic.h>` |
| `wait_work(WaitArgs...)` — user-pluggable callback | Hard-coded atomic-spin on `src_addr != NULL`; cores are dedicated so atomic-spin is the only reasonable production sync |
| `final_work(*addr, WorkArgs...)` — user-pluggable | Hard-coded `memcpy(ctx->local_result, src, ctx->n_bytes)` |
| `std::array<std::thread, N>` | `HANDLE hThreads[N]` (Windows) / `pthread_t tids[N]` (POSIX) |
| `setup_replica_cores()` sets cores_[] | Caller passes explicit `core_ids[]` to `sp_hedge_pool_create` |
| `insert(T val)` writes all N replicas | NOT present — lattice pool is read-only; caller provides two already-allocated addresses |

### Framework reuse from sp_channel_probe.c

The oracle pool (`sp_probe_pool`) already implements the correct C99 lifecycle:
- Lines 255-300: `sp_probe_pool_create` — aligned malloc, thread spawn (CreateThread/pthread_create), affinity set inline after spawn
- Lines 303-317: `sp_probe_pool_destroy` — set quit=1, wait join, free
- Lines 96-108: `probe_worker_ctx` — 128-byte cache-line aligned struct with control words and payload

I REUSE this lifecycle shape and struct-alignment technique; I write a NEW worker_func body that does `memcpy + completion-count increment` instead of `clflush + TSC rendezvous + timed LFENCE read`.

---

## 2. Divergences from Reference

| Aspect | Laurie | Math-core |
|---|---|---|
| Data replication | `insert()` writes N replicas | Caller provides 2 pre-allocated replica addresses via `sp_alloc_channel_pair` |
| wait_work | User-pluggable callback | Atomic-spin on `src_addr` (hard-coded) |
| N | Template parameter | Runtime param to `pool_create`; default N=2 |
| N=1 fallback | Not needed (N ≥ 2 asserted) | Supported: `pool_create(n=1)` spawns no thread; `read_pair` is `memcpy(out_a, a, n)` |

---

## 3. API Decision

**Extend `include/sp/sp_channel.h`** — same module, same channel-aware memory framing. The hedge pool is the production read primitive for channel-pair-allocated memory; it belongs with `sp_alloc_channel_pair`. No new header.

---

## 4. API Signatures

```c
/* Opaque pool handle. Persistent N-thread worker pool, one thread per channel,
 * each pinned to core_ids[i] at startup (hedged_reader.hpp:124,138-152 pattern). */
typedef struct sp_hedge_pool sp_hedge_pool;

/* Create at daemon/module startup. Spawns n_channels threads, pinned to
 * core_ids[i]. max_bytes is the max n_bytes accepted per sp_hedge_read_pair call;
 * larger requests return SP_EBADARG. Default: 64 (covers uint64 + Spinor).
 * N=1: no thread is spawned; read_pair degenerates to direct memcpy of side a.
 * Returns SP_ENOMEM on allocation failure, SP_EBADARG on NULL args. */
sp_status sp_hedge_pool_create(sp_hedge_pool **out,
                               const int *core_ids,
                               size_t n_channels,
                               size_t max_bytes);

void sp_hedge_pool_destroy(sp_hedge_pool *pool);

/* Hot path: caller publishes (a, b, n_bytes) to worker slots via atomic
 * store-release; each worker sees the slot, reads its address via memcpy into
 * a worker-local buffer, increments a shared completion counter (release);
 * caller spins on completion count == n_channels (acquire), then copies
 * worker-local results to out_a / out_b.
 *
 * N=1 fallback: memcpy(out_a, a, n_bytes); out_b unchanged.
 * Requires n_bytes <= max_bytes (set at pool_create). NOT reentrant. */
sp_status sp_hedge_read_pair(sp_hedge_pool *pool,
                             const void *a, const void *b,
                             size_t n_bytes,
                             void *out_a, void *out_b);

/* Spinor wrapper: exactly 63 bytes, both channels.
 * out_a and out_b each receive their respective block (not replica — both
 * outputs are populated so the CRT path can work with both residues). */
sp_status sp_hedge_read_spinor(sp_hedge_pool *pool,
                               const sp_spinor_block_t *a,
                               const sp_spinor_block_t *b,
                               sp_spinor_block_t *out_a,
                               sp_spinor_block_t *out_b);
```

---

## 5. Worker_func Design

### Context struct (two cache lines; no false sharing)

```c
/* Line 0 (0-63): should_exit + core_id + n_bytes + src_addr.
 * Line 1 (64-127): local_result[64] (or malloc'd for larger max_bytes). */
typedef struct {
    _Atomic(int)           should_exit;      /* set by pool_destroy */
    int                    core_id;
    size_t                 n_bytes;          /* set by caller before publish */
    _Atomic(const void *)  src_addr;         /* NULL = idle, non-NULL = work */
    char                   _pad[...];        /* pad to 64 bytes */
    uint8_t                local_result[64]; /* result buffer (line 1) */
} sp_hedge_worker_ctx;
```

For `max_bytes > 64`, `local_result` is a malloc'd pointer (separate allocation).

### Completion counter

Shared `_Atomic(int) completion` in the pool struct. Reset to 0 by caller before each read. Workers do `atomic_fetch_add(completion, 1, release)` after memcpy.

### Worker function (the production hot path)

```c
static THREAD_RETURN_T sp_hedge_worker_func(void *arg) {
    sp_hedge_worker_ctx *ctx = arg;
    sp_hedge_pin_to_core(ctx->core_id);  /* affinity set ONCE, inside thread */

    while (!atomic_load_explicit(&ctx->should_exit, memory_order_relaxed)) {
        /* Idle spin: wait for src_addr to become non-NULL.
         * No _mm_pause: cores are dedicated; full-speed spin for sub-µs latency. */
        const void *src;
        while ((src = atomic_load_explicit(&ctx->src_addr, memory_order_acquire))
               == NULL) {
            if (atomic_load_explicit(&ctx->should_exit, memory_order_relaxed))
                return THREAD_RETURN_VAL;
        }
        /* Drain the work — always complete after seeing non-NULL src.
         * should_exit check NOT re-checked here: worker drains pending work
         * before exiting to prevent caller from spinning forever on completion. */
        memcpy(ctx->local_result, src, ctx->n_bytes);
        atomic_store_explicit(&ctx->src_addr, NULL, memory_order_relaxed);
        atomic_fetch_add_explicit(ctx->completion, 1, memory_order_release);
    }
    return THREAD_RETURN_VAL;
}
```

**Why no post-spin should_exit check:** if the worker sees `src_addr != NULL`, it MUST drain the work (memcpy + completion increment) regardless of `should_exit`. Otherwise, if `pool_destroy` sets `should_exit` while a `read_pair` call is in progress, the worker exits without incrementing completion and the caller spins forever. Workers exit only from the idle spin (src_addr == NULL path).

### Caller side (sp_hedge_read_pair)

```
1. Reset pool->completion = 0 (relaxed — ordered by release-acquire on src_addr)
2. For each worker i: set ctx[i].n_bytes = n_bytes  (non-atomic; visible via release below)
3. For each worker i: atomic_store(ctx[i].src_addr, srcs[i], release)
4. Spin: while (atomic_load(pool->completion, acquire) < n_channels) {}
5. Copy ctx[0].local_result → out_a, ctx[1].local_result → out_b
```

Memory ordering correctness:
- Step 2 (write n_bytes) is sequenced-before step 3 (release store to src_addr)
- Worker's acquire load on src_addr synchronizes-with step 3's release store
- Therefore worker sees n_bytes correctly at step 2 ✓
- Worker's fetch_add release (step D) synchronizes-with caller's acquire load (step 4)
- Therefore caller sees local_result correctly at step 5 ✓

---

## 6. Bench Design

### LIVE path (requires huge pages + channel map)

1. `sp_channel_map_build` (loads cached .bin — already on dev host, no re-probe)
2. If DISABLED: print `M_TS_HEDGE_PROD: REQUIRES_LIVE_MODE`, exit 0
3. `sp_alloc_channel_pair(m, &ptr_a, &ptr_b, &arena)` — 1 MB each side
   - Pre-fault both with `memset(ptr_a, 0x42, 1MB); memset(ptr_b, 0xBE, 1MB)`
4. `sp_hedge_pool_create(&pool, core_ids={0,2}, n=2, max_bytes=8)`
5. Bind caller thread to core 1 (CORE_MAIN analogue; separate from worker cores)
6. **Baseline body:** 131072 sequential volatile uint64 reads from `ptr_a`.  
   RDTSC start → loop → RDTSC end → record cycles. 2048 trials.
7. **Hedge body:** 131072 `sp_hedge_read_pair(pool, &a64[i], &b64[i], 8, &ra, &rb)`.  
   Same trial count. Same RDTSC bracketing.
8. Sort each trial array; compute P50 / P90 / P99 per body.
9. Gate: `P99(hedge) / P99(baseline)`:
   - ≤ 0.50 → `M_TS_HEDGE_PROD: PASS`
   - ≤ 0.85 → `M_TS_HEDGE_PROD: WEAK`
   - > 0.85 → `M_TS_HEDGE_PROD: FAIL`

No LFENCE inside the inner loop. No per-element RDTSC. Whole-loop cycles only.

### Why this bench should PASS (not WEAK as the prior attempt predicted)

The prior attempt (commit 416417b) placed both arrays on the SAME logical channel via virtual-bit-only probing (no huge pages). `sp_alloc_channel_pair` with huge pages GUARANTEES physical-channel diversity (using pagemap on Linux / huge-page fixed VA on Windows). With real channel diversity, the two workers read from different DDR channels simultaneously; P99 speedup ≈ 2× is achievable.

The dev host (Beast Canyon) has the cached channel map .bin already; bench runs under normal Hyper-V conditions (SeLockMemoryPrivilege already wired in the daemon startup chain).

---

## 7. Files Modified / CMake

| Action | File |
|---|---|
| UPDATE (new API) | `include/sp/sp_channel.h` — add pool typedef + 4 function decls |
| REPLACE (416417b wrong pattern) | `core/sp_channel/sp_hedge.c` |
| REPLACE | `core/sp_channel/test_sp_hedge.c` |
| REPLACE | `core/sp_channel/bench_sp_hedge.c` |
| UPDATE | `core/sp_channel/CMakeLists.txt` — targets unchanged, sources unchanged |

`sp_hedge.c` already in sp_channel sources from 416417b — no CMake change needed for source list. The test and bench targets are already registered.

---

## 8. Sub-tag Taxonomy

- `lat-phase-16-3-hedge-correctness-closed` — T_HEDGE_* all bitwise PASS
- `lat-phase-16-3-hedge-pool-closed` — pool lifecycle (create, repeat reads, destroy) clean
- `lat-phase-16-3-hedge-throughput-closed` — M_TS_HEDGE_PROD gate PASS on bare metal
- `lat-phase-16-3-hedge-closed` — umbrella after all three
