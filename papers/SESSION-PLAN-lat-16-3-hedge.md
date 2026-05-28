# SESSION PLAN — lat-16-3-hedge: TS.HEDGE Production Primitives

**Date:** 2026-05-29  
**Spec:** PPT-LAT-Roadmap.md §16.3, amended 2026-05-28

---

## 1. Scope + Discipline

The §16.3 primitives are the OPPOSITE of the oracle machinery in `bench_ts_hedge.c`. The oracle (§16.1 TS.MAP) uses two-thread TSC rendezvous, LFENCE pairs, and spin barriers to measure DRAM channel timing. The production primitives use single-thread PREFETCH + LOAD — no pauses, no threads, no TSC rendezvous on the hot path.

**Canonical in-tree disclaimer** (from `bench_ts_hedge.c` line 8):
> "The TSC rendezvous (fire_tsc), LFENCE pairs, and percentile measurement are diagnostic machinery that exists only here — TailSlayer's runtime path (sp_alloc_channel_pair) loads the cached bin file and does O(1) channel selection with zero probe or pause overhead."

This plan implements THAT runtime path.

**TailSlayer reference:** `hedged_reader.hpp` uses a multi-threaded model where each replica is serviced by a dedicated worker thread pinned to a specific core. The sp_hedge primitives mirror the same goal (channel-parallel data access) in a single-thread idiom that fits the C math-core ABI.

---

## 2. API Decision

**Decision: Extend `include/sp/sp_channel.h`** — not a new header.

Justification:
- `sp_hedge_*` functions are direct consumers of the `sp_alloc_channel_pair` contract
- They belong to the same "channel-aware memory" framing
- One header keeps the API surface coherent for callers who use both allocator and hedge reads
- The roadmap §16.8 confirms §16.1–§16.3 live in `core/sp_channel/`

The header already depends on `<stdint.h>` and `<stddef.h>`. Add `#include "sp/spinor_block.h"` to satisfy `sp_hedge_read_spinor`.

---

## 3. Function Signatures (4 variants)

```c
/* ── Hedge-read primitives ─────────────────────────────────────────────────
 * All functions require `a` and `b` to be valid, readable pointers.
 * The caller is responsible for channel placement via sp_alloc_channel_pair.
 * These functions are CORRECTNESS-INDEPENDENT of channel topology: they return
 * bitwise-correct data even when a and b are on the same channel (CI/DISABLED).
 *
 * Prefetch hint: NTA (non-temporal) — correct for streaming Q8/Q4 arena and
 * Spinor KV reads where data is not reused within the same kernel call.
 * §16.5 TS.INTEGRATE-KSTE may warrant a T0-hinted variant for the KSTE
 * upper-tier hot set (reused per sieve walk). Not in this sprint.
 */

/* Replica hedge: a and b carry IDENTICAL data (caller's algebraic invariant,
 * e.g. replicated KV block).  Both channels are prefetched; the load streams
 * data from a while channel B's prefetch runs in parallel.  In a tight loop
 * of successive hedge reads, this warms channel B for the NEXT iteration —
 * channel-pair load balancing across a stream, not winner-takes-all per call. */
void sp_hedge_read64_replica(const void *a, const void *b, uint64_t *out);

/* Pair hedge: a and b carry INDEPENDENT data (e.g. q1 and q2 CRT residues).
 * Both channels are prefetched simultaneously; total latency ≈ max(lat_A, lat_B)
 * instead of lat_A + lat_B.  Results written to out_a and out_b. */
void sp_hedge_read_pair64(const void *a, const void *b,
                          uint64_t *out_a, uint64_t *out_b);

/* Block hedge: general n_bytes variant; interleaves PREFETCH with LOAD in
 * 64-byte (cache-line) strides.  Writes n_bytes from a→out_a, b→out_b.
 * Used as the inner primitive by sp_hedge_read_spinor. */
void sp_hedge_read_block(const void *a, const void *b, size_t n_bytes,
                         uint8_t *out_a, uint8_t *out_b);

/* Spinor hedge: typed 63-byte block; REPLICA semantic (caller's invariant:
 * a and b contain the same block on independent channels).  Writes a's content
 * to *out; channel B is warmed for stream-pipelining benefit. */
void sp_hedge_read_spinor(const sp_spinor_block_t *a,
                          const sp_spinor_block_t *b,
                          sp_spinor_block_t *out);
```

**Block-level decision:** Both `sp_hedge_read_block` (byte-length, general) and `sp_hedge_read_spinor` (typed 63-byte block). Spinor is the primary production consumer; block is needed for §16.4 CRT integration (arbitrary-size NTT residue windows). Both are public.

---

## 4. Prefetch Hint Choice

**NTA (`_MM_HINT_NTA` / `__builtin_prefetch(p, 0, 0)`)** for all functions in this sprint.

Reasoning:
- Q8/Q4 weight rows: read once per matmul forward call, no reuse within the call
- Spinor KV blocks: read once per decode-step layer traversal
- NTA bypasses L2/L3 on write-back (reduces pollution of working caches)
- NTA on read fetches to L1 without warming L2/L3 unnecessarily

Documented caveat: for §16.5 KSTE upper-tier (256 KB hot set reused per sieve walk), T0 hint (`_MM_HINT_T0`) will be preferable. That variant is Phase F7+ scope; do not add it in this sprint.

---

## 5. Bench Design (Path A — honest WEAK/PARTIAL)

**Explicit cache-residency prediction (before measurement, per advisor directive):**

Beast Canyon (Tiger Lake) L3 = 12 MB. 1 MB bench data fits in L3 after trial 1 of 2048. Starting from trial 2, baseline and hedge both hit L3, not DRAM. The PREFETCH+LOAD pair gives ~2× benefit on cold DRAM misses; on L3 hits, the gain is minimal (~1.05–1.3×). Expected bench result: **WEAK** (ratio > 0.5×) or at best **PARTIAL** on Beast Canyon.

This is an honest finding, not a failure to implement correctly. The primitive is correct. The bench cannot demonstrate the full DRAM-channel benefit with 1 MB on a 12 MB L3 system.

The closure note will file `feedback-bench-cache-residency` and propose §16.3.1 as a follow-on bench with a properly sized arena (≥ 2× LLC = 24+ MB) to force cold DRAM access.

**Bench structure:**
1. Build channel map via `sp_channel_map_build`
2. If DISABLED: print `M_TS_HEDGE_PROD: REQUIRES_LIVE_MODE` and exit 0
3. LIVE path:
   a. Allocate 2× huge-page arena (via `sp_alloc_huge`, internal API) of size 8 MB
   b. Scan arena at 64-byte stride using `sp_channel_of` → collect ch0[] and ch1[] address lists
   c. If `count(ch0) < N_ELEM || count(ch1) < N_ELEM`: print shortage warning, use smaller N_ELEM
   d. `memset` both lists' memory to pre-fault pages
   e. `SetThreadAffinityMask` / `sched_setaffinity` to a P-core
   f. Time 2048 trials of:
      - Baseline: N_ELEM sequential reads from ch0[] only (loop, volatile u64 loads)
      - Hedge: N_ELEM `sp_hedge_read_pair64(ch0[i], ch1[i])` calls
   g. Sort trial times (TSC cycles); compute P50/P90/P99 per body
   h. Print results table
   i. Gate: `P99(hedge) / P99(baseline) ≤ 0.5` → PASS; `≤ 0.85` → WEAK; `> 0.85` → FAIL

**N_ELEM = 65536** (not 131072): the 8 MB arena at 64-byte stride gives exactly 131072 cache-line slots; with 2-channel interleaving, ~65536 per channel. Matches `0.5 × 131072`.

**Timing: TSC cycles** (not nanoseconds) — no calibration code required. Ratio is dimensionless.

**Inner loop:** NO `_mm_pause`, NO LFENCE per-element, NO per-element RDTSC. Outer RDTSC brackets the whole N_ELEM loop.

---

## 6. Gate Definition

| Ratio P99(hedge) / P99(baseline) | Verdict |
|---|---|
| ≤ 0.50 | `M_TS_HEDGE_PROD: PASS` |
| 0.50 < ratio ≤ 0.85 | `M_TS_HEDGE_PROD: WEAK` |
| > 0.85 | `M_TS_HEDGE_PROD: FAIL` |

Expected on Beast Canyon + 1MB + 12MB L3: **WEAK**. Per `feedback-no-silent-gate-revisions`, WEAK is reported as WEAK and not relabeled.

CI/VM gate: function exits 0 in DISABLED mode, bitwise correctness verified by T_HEDGE tests (channel-independent).

---

## 7. Files to Create

| File | Role |
|---|---|
| `include/sp/sp_channel.h` | Add 4 hedge declarations + `#include "sp/spinor_block.h"` |
| `core/sp_channel/sp_hedge.c` | Implement all 4 variants |
| `core/sp_channel/test_sp_hedge.c` | Correctness tests T_HEDGE_PAIR/REPLICA/BLOCK/SPINOR/DISABLED |
| `core/sp_channel/bench_sp_hedge.c` | Performance bench with LIVE/DISABLED path |
| `core/sp_channel/CMakeLists.txt` | Add sp_hedge.c to sp_channel sources; add test + bench targets |

---

## 8. Forbidden-Pattern Checklist (code review gates)

- [ ] No `_mm_pause` / `__pause` / spin loops in sp_hedge.c or bench_sp_hedge.c
- [ ] No `pthread_create` / `std::thread` / `CreateThread`
- [ ] No TSC rendezvous (`fire_tsc`, per-element RDTSC loop)
- [ ] No LFENCE surrounding the hedge loads
- [ ] No call into `sp_channel_probe.c` (oracle apparatus)
- [ ] Prefetch-then-volatile-load order maintained (prefetch must precede loads)
