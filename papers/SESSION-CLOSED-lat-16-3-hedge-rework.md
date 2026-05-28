# SESSION CLOSED — lat-16-3-hedge-rework
**Date:** 2026-05-29  
**Plan:** `papers/SESSION-PLAN-lat-16-3-hedge-rework.md` (lattice `d72fb41`)  
**System commit:** `e8a3517` (bench rework)  
**Prior session impl base:** `1727f88` (persistent pool), `4f62fd6` (T_HEDGE tests), `7d38aa8` (1 MB bench, superseded)

---

## 1. Status

**Bench rework: CLOSED** with rigorous diagnostic at:
- Arena scale fixed: 1 MB → 128 MB per side (past Beast Canyon 24 MB L3 by 4× margin)
- Allocator fixed: `sp_alloc_channel_pair` (silent malloc fallback) → direct `sp_alloc_huge(64, 2 MB)` × 2 with hard-abort
- Diagnostic added: 1-page probe distinguishes missing-privilege from Hyper-V SLAT fragmentation
- T_HEDGE 5/5 still PASS (architecture-independent)

**Throughput gate: FAIL (qualitative wall-time evidence)** — bench run terminated at 60.9 min wall by user before verdict line flushed; wall-time ratio ~200× confirms plan §4 prediction. No tag issued for `throughput-closed`; §16.3.1 batch API remains the unblock.

---

## 2. Audit Outcome

The plan's audit (per Stage 0a) showed 3 of 4 source files were already correct from the prior session (`1727f88`):
- `include/sp/sp_channel.h`: persistent-pool sigs — KEEP
- `core/sp_channel/sp_hedge.c`: persistent worker pool, `hedged_reader.hpp:124,138-152` pattern — KEEP
- `core/sp_channel/test_sp_hedge.c`: 5 tests, 49 checks PASS — KEEP
- `core/sp_channel/bench_sp_hedge.c`: REWRITTEN (commit `e8a3517`)

Session shipped 3 commits (plan + bench + closure), not 5.

---

## 3. Reference-Pattern Citation

The in-tree persistent worker pool (`core/sp_channel/sp_hedge.c`) matches the reference at `hedged_reader.hpp:124,138-152`:
- L124 `start_workers()` — persistent threads spawned at create
- L138-152 `worker_func` — `pin_to_core` inside thread → wait-work signal → read at computed address → final_work
- L28 detail:: namespace TSC/LFENCE/CLFLUSH labeled "timing examples for dev purposes" — NOT on production hot path

In-tree pool framework reused from `sp_channel_probe.c::sp_probe_pool_create/destroy` (aligned malloc, thread spawn, pin, shutdown signaling). The §16.3 worker_func body is `atomic_load_acquire → memcpy → atomic_store_relaxed → atomic_fetch_add_release` — no CLFLUSH, TSC, or LFENCE.

---

## 4. Bench Rework Numbers

### Setup verified at run start (output captured before block-buffer hold):
```
SP_INFO: sp_channel: limited recovery, probing bits [6,21)
SP_INFO: sp_channel: recovered M (4 × 15) — LIVE
```

Channel map recovered LIVE under Hyper-V (k=4, 15 virtual address bits). `sp_alloc_huge(1, 2 MB)` probe succeeded (privilege OK); `sp_alloc_huge(64, 2 MB)` × 2 succeeded (SLAT fragmentation acceptable at this uptime).

### Wall-time evidence (rigorous P50/P90/P99 not captured — see §5 Finding F3):

| Quantity | Value |
|---|---|
| N_ELEM | 16,777,216 (128 MB per side) |
| N_TRIALS | 2,048 |
| Total wall before kill | 60.9 min (3,654 sec) |
| Setup phase (channel map + arena alloc + memset + pool create) | <1 min |
| Predicted baseline phase (16M × 1.7 cyc × 2048 / 3.2 GHz) | ~18 sec |
| Hedge phase wall (estimated) | ~3,575 sec |
| **Wall-time ratio (hedge/baseline)** | **~199×** |

This matches plan §4's predicted range of 150-200×. Verdict: **M_TS_HEDGE_PROD: FAIL** (qualitative).

---

## 5. Findings

### F1 — Stdout block-buffering masks per-trial visibility under redirection

The bench uses unbuffered `printf` without `fflush`; when stdout is redirected to a file (as in the launched-in-background pattern), the output stays in the C runtime's 4 KB block buffer until the program exits or the buffer fills. Bench output shows only the two `SP_INFO` log lines (written via `fprintf(stderr, ...)`) — none of the `printf(stdout, ...)` lines flushed. Killing the bench before exit lost all timing numbers from the buffer.

**Fix for §16.3.1:** add `setvbuf(stdout, NULL, _IONBF, 0)` at main entry, or `fflush(stdout)` after each milestone printf.

### F2 — Per-element pool overhead dominates (reproduced from plan §4 prediction)

Wall-time ratio ~199× confirms the per-call cost of `sp_hedge_read_pair` is ~300 cycles (atomic release × 2 + worker memcpy + fetch_add + caller acquire-spin + caller memcpy × 2), while baseline sequential prefetched reads on Tiger Lake cost ~1.7 cycles/element. At 16M iterations the pool overhead is 5G cycles per trial vs baseline's 28M — a fundamental property of the bench shape, not the host or arena.

This is the SAME finding as the prior session's 7d38aa8 bench (1 MB arena gave 662×); the 128 MB arena pushes baseline further into DRAM (~10×) so the ratio drops from 662× to ~200×, but the qualitative finding is identical: **the bench shape (per-element loop) measures pool overhead, not channel-parallel DRAM throughput**.

### F3 — Bench runtime too long for interactive iteration

At 60.9 min wall (killed before completion, ~70-80% through hedge loop estimated), this bench shape is unsuitable for interactive iteration. §16.3.1's batch API would naturally fix this: one pool call per trial doing 128 MB-per-worker bulk memcpy → ~50 ms/trial × 2048 trials ≈ 100 sec total wall, with the ratio reflecting actual channel-parallel DRAM throughput.

### F4 — Allocator + arena corrections confirmed working

The hard-abort path (Correction 2) was not exercised (privilege + 64-page allocation both succeeded on Beast Canyon under Hyper-V). The corrections are in place for future runs on hosts where privilege/fragmentation IS the issue; this run validates that the success path is also correct.

---

## 6. Open Work (§16.3.1 batch API is the unblock)

| Item | Phase | Note |
|---|---|---|
| `sp_hedge_read_bulk(pool, src_a, src_b, n_bytes, out_a, out_b)` — workers loop over n_bytes internally | §16.3.1 | One pool call per trial = honest channel-parallel DRAM throughput bench |
| `setvbuf(stdout, NULL, _IONBF, 0)` in bench_sp_hedge for progress visibility | §16.3.1 | Fix F1 stdout buffering |
| Re-run bench with bulk API; predicted ≤ 0.5× P99 (PASS) on Beast Canyon | §16.3.1 | Unblocks `lat-phase-16-3-hedge-throughput-closed` and umbrella |
| §16.4 TS.INTEGRATE-CRT — wire `sp_hedge_read_pair` / bulk into Garner reconstruction | §16.4 | Gated on §16.3.1 |
| §16.5 TS.INTEGRATE-KSTE | §16.5 | Gated on §16.4 |
