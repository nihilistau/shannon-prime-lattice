# SESSION CLOSED — lat-16-3-1-bulk
**Date:** 2026-05-29  
**Plan:** `SESSION-PLAN-lat-16-3-1-bulk.md` (`ae29ab6`)  
**System commits:** `fba47d1` (impl), `d942b90` (tests), `af6f530` (bench)  
**Tags issued:** `lat-phase-16-3-hedge-throughput-closed`, umbrella `lat-phase-16-3-hedge-closed` — user accepted 1.25× channel speedup as production-acceptable on this host (Hyper-V virt-bit-only map); spec's ≥2× target retained as aspirational for bare-metal hosts.

---

## 1. Status

**Bulk API: CLOSED** — `sp_hedge_read_bulk` shipped; T_HEDGE 8/8 PASS (63 checks; +3 new BULK tests).  
**Bench rework: CLOSED** — `setvbuf` fix + serial-256MB vs parallel-2-worker comparison.  
**Throughput gate: CLOSED (user-accepted at 1.25×)** — measured P99 ratio 0.797× = ~1.25× speedup. Gate threshold (≤ 0.50 PASS) was conceived for bare-metal hosts where baseline is channel-bottlenecked; on this host (Hyper-V, virt-bit-only channel map, Tiger Lake AVX2 memcpy already exploiting both channels via prefetcher) baseline is not channel-bound, so 1.25× is the achievable speedup and accepted as the deliverable.  
**Umbrella `lat-phase-16-3-hedge-closed`: ISSUED** — all three sub-tags (correctness, pool, throughput) now in place.

---

## 2. Deliverables

### Bulk API (`fba47d1`)
- `sp_hedge_worker_ctx` gains `atomic_uintptr_t dst_addr` on line 0 (pad 32 → 24 B; struct stays 128 B)
- Worker hot path reads `dst_addr` (relaxed, ordered by acquire fence on `src_addr`) and memcpys to it
- `sp_hedge_read_pair` (back-compat): caller sets `dst_addr = &result_inline[0]` before publishing `src_addr`; post-spin copy unchanged
- `sp_hedge_read_bulk` (new): caller sets `dst_addr = caller buffer` directly; no intermediate copy
- N=1 fallback: direct `memcpy(dst_a, src_a, n_bytes)`; `src_b`/`dst_b` ignored

### Tests (`d942b90`)
- `T_HEDGE_BULK_SMALL` — 8 KB transfer, dst_a/dst_b bitwise-identical
- `T_HEDGE_BULK_LARGE` — 1 MB transfer, same invariant
- `T_HEDGE_BULK_N1_FALLBACK` — N=1 pool; dst_a = src_a; dst_b untouched (sentinel intact)
- All 8 T_HEDGE tests PASS (63 total checks)

### Bench (`af6f530`)
- `setvbuf(stdout, NULL, _IONBF, 0)` at main entry — fixes F1 stdout buffering from prior session
- Baseline: SERIAL memcpy of both 128 MB sides (256 MB total via one thread) — fair comparison
- Hedge: ONE `sp_hedge_read_bulk` call (256 MB total split 128 MB per worker, parallel)
- Same total memory work; ratio measures channel-parallel speedup
- Total wall: ~60 sec (vs prior session's 60+ min — 60× improvement)

---

## 3. Bench Numbers (Beast Canyon LIVE under Hyper-V)

```
N_BYTES  = 134217728 (128 MB per side); N_PAGES = 64 × 2MB; N_TRIALS = 2048
Channel map: limited recovery, probing bits [6,21); M (4 × 15) — LIVE
```

| body | P50 (cyc) | P90 (cyc) | P99 (cyc) |
|---|---|---|---|
| baseline (256 MB serial) | 72,738,896 | 78,889,058 | 84,207,108 |
| hedge (256 MB parallel) | 58,166,558 | 62,665,188 | 67,098,366 |
| **ratio** | **0.800** | **0.794** | **0.797** |

Conversion at 3.2 GHz: baseline P99 ≈ 26 ms/trial; hedge P99 ≈ 21 ms/trial. Channel-parallel speedup ≈ 1.25× (the inverse of 0.797).

**M_TS_HEDGE_PROD: WEAK** (P99 ratio 0.797; 0.50 < ratio ≤ 0.85)

---

## 4. Findings

### F1 — Bulk API works and is fast

Pool overhead (~300 cyc per atomic round-trip) amortizes across the 128 MB transfer to ~2 ppm of trial time, confirming F2 from the prior session: per-element overhead was the problem, not the architecture. The architecture is correct; the bench shape now reflects channel-parallel DRAM throughput.

### F2 — Channel parallelism ~1.25× on this host, not 2×

The hedge produces a real speedup but well below the spec's 2× target. Likely causes:

- **Single-thread memcpy already approaches dual-channel bandwidth.** On Tiger Lake with hardware prefetchers + AVX2-wide memcpy, a single thread reading 128 MB sequentially naturally interleaves across both physical DDR channels via the controller's hash. Adding a second thread doesn't unlock 2× because the baseline isn't bottlenecked on one channel — it's already using both.
- **Write-allocate doubles the effective bandwidth.** memcpy reads dst before writing (write-allocate). Both baseline (read src + read+write dst across both sides) and hedge (same memory traffic distributed across 2 threads) hit the same total bandwidth ceiling.
- **Virtual-bit-only channel map** under Hyper-V (k=4, n=15) provides no physical-address steering. The hardware interleave is what produces the modest hedge benefit, not the software placement.

### F3 — Bench wall reduced from 60+ min to ~60 sec

The bulk API + `setvbuf` fix produced a usable bench. Per-trial wall ≈ 30 ms total; 2048 trials × 2 bodies ≈ 60 sec. Now suitable for interactive iteration. Per-trial progress prints visible in real time (no buffer hold).

### F4 — User-accepted gate revision (1.25× speedup accepted as deliverable)

The measured ratio 0.797× = 1.25× channel-parallel speedup. Per the spec's letter, this is WEAK (gate boundary 0.50). After reviewing the F2 finding (single-thread AVX2 memcpy on Tiger Lake already exploits both DDR channels via prefetcher + controller hash, so baseline is NOT channel-bottlenecked on this host), the user accepted 1.25× as the achievable speedup on this hardware/virtualization configuration and authorized issuing throughput-closed + umbrella tags. The spec's ≥2× target is retained as aspirational for bare-metal hosts where baseline IS channel-bound (see Open Work for re-test candidates).

This is NOT silent gate widening per `feedback-no-silent-gate-revisions`: the empirical finding (1.25× not 2×) was surfaced first; the user reviewed and made the explicit acceptance call; this closure note records both the empirical measurement and the acceptance decision verbatim.

---

## 5. Empirical Measurement vs Spec Threshold

- **Not FAIL** (>0.85): hedge IS measurably faster than serial baseline. The architecture works.
- **Not strict PASS** (≤0.50 per the original spec): hardware single-thread memcpy on Tiger Lake already exploits dual channels via prefetcher + controller hash; the marginal benefit from adding a second software thread is ~1.25×, not 2×.

The spec target ≥2× P99 was conceived for a host where the baseline is channel-bottlenecked. On Beast Canyon under Hyper-V with virtual-bit-only channel map, that condition isn't met. Per user direction (2026-05-29 mid-session): 1.25× channel speedup is acceptable for production deployment on this host class; gate accepted at 0.797 with the empirical finding documented.

---

## 6. Open Work

| Item | Phase | Rationale |
|---|---|---|
| Re-test on bare-metal Linux with pagemap access (full physical-bit channel map) | §16.3 follow-on | May lift WEAK → PASS if physical placement is the bottleneck |
| Re-test on AMD Zen 4 / Genoa (different prefetcher behavior; baseline may be channel-bound) | §16.3 follow-on | Different hardware may show stronger hedge benefit |
| §16.3.2 caller-buffer-direct in read_pair/read_spinor (KV hot path) | §16.3.2 | Production payoff for inference; not bench-blocking |
| §16.4 TS.INTEGRATE-CRT | §16.4 | Gated on lifting WEAK → PASS on a host where the gate is reachable |
| Investigate AVX-512 wide memcpy variant for baseline (probe whether AVX-512 saturates dual channels on this host even harder) | diagnostic | Falsifiability check on F2 hypothesis |
