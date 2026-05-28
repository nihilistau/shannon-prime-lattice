# SESSION CLOSED — lat-16-3-hedge (persistent-pool revision)
**Date:** 2026-05-29  
**Tags:** `lat-phase-16-3-hedge-correctness-closed`, `lat-phase-16-3-hedge-pool-closed`  
**System commits:** `1727f88` (impl), `4f62fd6` (tests), `7d38aa8` (bench)  
**Umbrella tag:** NOT ISSUED — throughput gate FAIL; see §4.

---

## 1. Status

**Correctness: CLOSED** — T_HEDGE_* 5/5 PASS (49 checks). Pool lifecycle CLOSED.  
**Throughput: FAIL** — M_TS_HEDGE_PROD ratio 662× (hedge/baseline P99). Finding documented in §4.

---

## 2. Deliverables

**`include/sp/sp_channel.h`** — replaced PREFETCH+LOAD API (416417b, wrong pattern) with persistent-pool API:
- `sp_hedge_pool` opaque typedef
- `sp_hedge_pool_create(out, core_ids, n_channels, max_bytes)` — N=1 fallback supported
- `sp_hedge_pool_destroy(pool)`
- `sp_hedge_read_pair(pool, a, b, n_bytes, out_a, out_b)` — hot path
- `sp_hedge_read_spinor(pool, a, b, out_a, out_b)` — typed 63-byte wrapper

**`core/sp_channel/sp_hedge.c`** — persistent-pool implementation:
- `sp_hedge_worker_ctx`: 128-byte cache-line-aligned struct (2 lines; no false sharing)
- Worker hot path: `load_acquire(src_addr)` → `memcpy(result_inline, src, n_bytes)` → `store_relaxed(src_addr=NULL)` → `fetch_add_release(completion)`. No CLFLUSH, TSC, or LFENCE.
- Workers drain pending work before checking `should_exit` (prevents caller livelock).
- v1 limits: `n_channels ≤ 2`, `n_bytes ≤ 64` (covers uint64 + Spinor 63 bytes).

---

## 3. Reference-Pattern Citations

**Primary pattern** — `hedged_reader.hpp:124,138-152` (Laurie TailSlayer, `HedgedReader`):
- Line 124: `workers_[i] = std::thread(&HedgedReader::worker_func, this, i)` — persistent threads spawned at create
- Lines 138-152: `worker_func` body — `pin_to_core` once, `wait_work` callback, `get_next_logical_index_address`, `final_work(*target_addr)`
- Line 29 comment: `detail::` TSC/LFENCE/CLFLUSH are timing dev tools, NOT on production hot path

**Framework reused** — `sp_channel_probe.c::sp_probe_pool_create/destroy`:
- Cache-line-aligned struct allocation (`_aligned_malloc` / `posix_memalign`)
- Thread spawn pattern (CreateThread / pthread_create)
- Shutdown: signal quit, join all threads

**New production worker_func body** (does NOT copy oracle apparatus):
- Oracle: clflush + TSC rendezvous + LFENCE-bracketed timed read
- Production: atomic load-acquire → memcpy → atomic store + fetch_add

**In-tree disclaimer** (bench_ts_hedge.c line 8):
> "The TSC rendezvous (fire_tsc), LFENCE pairs, and percentile measurement are diagnostic machinery that exists only here — TailSlayer's runtime path (sp_alloc_channel_pair) loads the cached bin file and does O(1) channel selection with zero probe or pause overhead."

---

## 4. Correctness Results

| Test | Description | Result |
|---|---|---|
| T_HEDGE_POOL_CREATE_DESTROY | Create + immediate destroy; clean teardown | **PASS** |
| T_HEDGE_PAIR_1 | uint64 pair reads byte-identical; sweep 16 random pairs | **PASS** |
| T_HEDGE_SPINOR_1 | 63-byte block reads correct (both out_a and out_b) | **PASS** |
| T_HEDGE_N1_FALLBACK | N=1 pool = memcpy of side a; out_b unchanged | **PASS** |
| T_HEDGE_REPEATED | 10000 sequential reads through same pool, all correct | **PASS** |

49 checks, 0 fails.

---

## 5. Bench Numbers (Beast Canyon LIVE)

Channel placement: `ptr_a channel=0, ptr_b channel=1` — channel-diverse confirmed.

| Body | P50 (cyc) | P90 (cyc) | P99 (cyc) |
|---|---|---|---|
| baseline | 222,578 | 271,182 | 308,156 |
| hedge | 102,015,460 | 135,585,444 | 204,174,322 |
| ratio | 458× | 500× | **663×** |

**M_TS_HEDGE_PROD: FAIL** — ratio 662× P99 (hedge is 662× SLOWER).

---

## 6. Findings

### F1 — Per-element pool overhead dominates sequential reads

The bench runs 131072 `sp_hedge_read_pair` calls in a tight loop. Each call involves:
1. `atomic_store_release` × 2 (publish addresses to worker slots)
2. Worker wakes, does `memcpy` of 8 bytes
3. `atomic_fetch_add_release` (completion)
4. Caller's `atomic_load_acquire` spin loop until completion == 2
5. `memcpy` × 2 (copy worker results to caller output)

The cache-coherence round-trip across cores costs ~300 cycles on Tiger Lake. Baseline sequential reads cost ~1.7 cycles/element (hardware prefetcher + L1 hits). Ratio: 300 / 1.7 ≈ 176×. Actual ratio: 662× (two atomic round-trips × cache pressure from result copies).

### F2 — Correct use case: sparse KV reads, not tight loops

The persistent-pool is designed for Laurie's use case: `wait_work(signal)` → one read per external event (e.g., per decode step). The bench specification ("131072 sequential reads per trial") is wrong for this API.

**Correct bench** for the pool API:
- **Option A (batch reads):** One pool call per trial that reads the full 1MB. Workers each do a sequential memcpy of 1MB from their side. Compare to single-thread reading 2MB sequentially (both sides). Expected speedup: ~2× (parallel DDR channels). Requires `sp_hedge_read_bulk()` API extension.
- **Option B (cold individual reads):** One pool call per trial, with clflush before each trial to force DRAM access. Compare to single-channel cold read. Expected P99 improvement: TREFI tail probability drops from p → p² (where p ≈ 0.1% per read).

**Production amortization:** In actual inference (28 layers × 32 heads = 896 KV reads per decode step), if each call is 63 bytes at DRAM latency (~300ns = ~960 cycles), pool overhead (300 cycles) = 31% overhead — still net negative without batch API.

### F3 — Two prior wrong framings

- **2026-05-28 (original):** "two read threads per-read" — conflated with §16.1 oracle TSC rendezvous pattern
- **2026-05-29 morning:** "single-thread PREFETCH+LOAD" — reasoned from theory without reading `hedged_reader.hpp`
- **2026-05-29 late (this session):** "persistent pool, per-element atomic round-trips" — correct pattern (matches hedged_reader.hpp) but wrong bench shape

Meta-lesson: **read the reference first, then theory** (see `feedback-lead-with-reference-then-theory`).

---

## 7. Open Work

| Item | Phase | Notes |
|---|---|---|
| `sp_hedge_read_bulk(pool, src_a, src_b, n_bytes, out_a, out_b)` — batch API; workers loop over n_bytes | §16.3.1 | Enables 2× throughput bench and honest PASS gate |
| Re-run bench with bulk API and 2MB arena (1MB per side) vs sequential 2MB baseline | §16.3.1 | Predicted PASS with channel-diverse arenas |
| §16.4 TS.INTEGRATE-CRT: wire `sp_hedge_read_pair` / `sp_hedge_read_bulk` into Garner CRT reconstruction (q1/q2 residue reads) | §16.4 | |
| §16.5 TS.INTEGRATE-KSTE: `sp_hedge_read_spinor` for KSTE upper-tier traversal | §16.5 | |
| v1 limit lift: `n_channels > 2`, `n_bytes > 64` (for bulk) | §16.3.1 | |
