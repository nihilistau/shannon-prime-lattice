---
type: session-handoff
title: SESSION PLAN — lat-16-3-1-bulk
description: "Date: 2026-05-29"
tags: [session-handoff]
timestamp: 2026-05-28T19:54:43Z
resource: shannon-prime-lattice/papers/SESSION-PLAN-lat-16-3-1-bulk.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# SESSION PLAN — lat-16-3-1-bulk
**Date:** 2026-05-29  
**Scope:** Ship `sp_hedge_read_bulk` + `setvbuf` bench fix. Issue throughput-closed + umbrella on PASS.

---

## 1. Goal

Unblock the throughput gate (M_TS_HEDGE_PROD) by adding a batch API that amortizes pool overhead across one bulk transfer rather than N atomic round-trips. Per prior closure (`1956785`) F2: per-element pool overhead (~300 cyc/call) dominates baseline (~1.7 cyc/element) at the per-element bench shape; bulk amortizes to ~300 cyc / 128 MB ≈ negligible.

---

## 2. API Decision (per user)

**Bulk only** — `read_pair` stays on `result_inline` path; `read_bulk` writes directly to caller buffers. KV production hot-path optimization (replacing intermediate copy in `read_pair`/`read_spinor`) deferred to §16.3.2.

```c
/* §16.3.1 batch hedge: workers write n_bytes directly into caller-provided
 * dst_a / dst_b in parallel.  Amortizes pool overhead across the whole
 * transfer.  n_bytes is unbounded (caller manages buffer sizes).
 * NOT reentrant (single pool serves one bulk read at a time). */
sp_status sp_hedge_read_bulk(sp_hedge_pool *pool,
                             const void *src_a, void *dst_a,
                             const void *src_b, void *dst_b,
                             size_t n_bytes);
```

N=1 fallback: direct memcpy of src_a → dst_a; src_b/dst_b ignored.

---

## 3. Implementation

Add `atomic_uintptr_t dst_addr` to `sp_hedge_worker_ctx` (line 0; reduce `_pad` from 32 to 24 bytes; struct stays 128 bytes total).

Worker function reads both `src_addr` (acquire) and `dst_addr` (relaxed; ordered by `src_addr` release on caller side):

```c
const uintptr_t dst = atomic_load_explicit(&ctx->dst_addr, memory_order_relaxed);
memcpy((void*)dst, (const void*)raw, ctx->n_bytes);
```

**For `sp_hedge_read_pair` (existing):** caller sets `dst_addr = &result_inline[0]` before publishing `src_addr`. Post-spin memcpy from `result_inline` to `out_a`/`out_b` unchanged. Back-compat preserved.

**For `sp_hedge_read_bulk` (new):** caller sets `dst_addr = dst_a/dst_b` directly. No post-spin copy.

Files modified:
- `include/sp/sp_channel.h` — add `sp_hedge_read_bulk` decl
- `core/sp_channel/sp_hedge.c` — add `dst_addr` field, modify worker_func, update `read_pair`, add `read_bulk`

---

## 4. Tests

Append to `test_sp_hedge.c`:
- `T_HEDGE_BULK_SMALL` — bulk read of 8 KB; both dst_a and dst_b match src_a and src_b
- `T_HEDGE_BULK_LARGE` — bulk read of 1 MB; same invariant
- `T_HEDGE_BULK_N1_FALLBACK` — N=1 pool: dst_a = src_a; dst_b untouched

Existing T_HEDGE_PAIR_* tests must still PASS (worker_func change is transparent because caller sets `dst_addr = &result_inline[0]`).

---

## 5. Bench Rework

Modifications to `bench_sp_hedge.c`:
- Add `setvbuf(stdout, NULL, _IONBF, 0)` at main entry (fix F1 stdout buffering)
- Replace per-element loop with single `sp_hedge_read_bulk` call per trial
- Baseline = single-threaded sequential read of full 128 MB from arena_a (no worker pool, one volatile read loop)
- Hedge = one `sp_hedge_read_bulk(pool, arena_a, dst_a, arena_b, dst_b, 128 MB)` per trial
- Need `dst_a`/`dst_b` (128 MB each) — allocate via `sp_alloc_huge` or plain malloc (write side doesn't need huge pages for channel-of correctness; the SOURCE arenas already do)

### Predicted outcome

128 MB at single-channel DRAM bandwidth (~12 GB/s on Tiger Lake DDR4): ~10 ms/trial baseline. Bulk with 2 channels parallel (~24 GB/s aggregate): ~5 ms/trial. **Predicted ratio P99 ≈ 0.5×** → PASS at the spec threshold. 2048 trials × ~7.5 ms avg = ~15 sec total wall.

If actual result is 0.50-0.85× → WEAK (channel contention or memory-controller serialization caps benefit).  
If > 0.85× → FAIL (channel placement wrong, or bench shape still off).

---

## 6. Tag Plan (per user)

- `lat-phase-16-3-hedge-throughput-closed` — issued on PASS (ratio ≤ 0.5×)
- `lat-phase-16-3-hedge-closed` (umbrella) — issued on PASS, after the three sub-tags exist (correctness, pool, throughput)
- If WEAK or FAIL: closure note documents the empirical finding; tags not issued; surface upstream.

---

## 7. Commit Plan (~5 commits)

1. Plan (this file)
2. Header + impl: `sp_hedge_read_bulk` + worker_func dst_addr support
3. Tests: T_HEDGE_BULK_* (3 new)
4. Bench: setvbuf + switch to bulk API + dst buffer allocation
5. Closure note + tags

§16.3.2 (caller-buffer-direct in `read_pair`/`read_spinor` for KV hot path) filed as follow-on.
