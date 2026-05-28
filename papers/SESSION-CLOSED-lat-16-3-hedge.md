# SESSION CLOSED — lat-16-3-hedge
**Date:** 2026-05-29  
**Tag:** `lat-phase-16-3-hedge-closed`  
**System commit:** `416417b`  
**Status:** CLOSED (implementation + tests PASS; LIVE bench result documented as FAIL with findings)

---

## 1. Status

**Correctness: CLOSED** — T_HEDGE 5/5 PASS on plain malloc arenas; channel-independent.  
**LIVE bench: FAIL** — M_TS_HEDGE_PROD ratio 3.886× P99 (hedge/baseline) on Beast Canyon. Not WEAK as predicted in plan §5 — actual cause was same-channel placement, not L3 residency. Findings documented in §4.

Per `feedback-no-silent-gate-revisions`: FAIL is reported as FAIL. The primitive is correct; the bench reveals a missing prerequisite (huge pages + physical-bit probing) for the LIVE gate to be meaningful on this host.

---

## 2. Deliverables

**`include/sp/sp_channel.h`** — 4 new public declarations added (+ `#include "sp/spinor_block.h"`):
- `sp_hedge_read64_replica(a, b, out)` — stream replica hedge
- `sp_hedge_read_pair64(a, b, out_a, out_b)` — CRT-residue pair hedge
- `sp_hedge_read_block(a, b, n_bytes, out_a, out_b)` — general byte-length block
- `sp_hedge_read_spinor(a, b, out)` — typed 63-byte Spinor replica

**`core/sp_channel/sp_hedge.c`** — implementation:
- `SP_PREFETCH` macro: `_mm_prefetch(..., _MM_HINT_NTA)` on MSVC; `__builtin_prefetch(..., 0, 0)` on GCC/Clang; no-op fallback
- All volatile-read patterns. No `_mm_pause`, no threads, no TSC rendezvous, no LFENCE on the hot path.

**`core/sp_channel/test_sp_hedge.c`** — 5 correctness tests wired to ctest as `T_HEDGE`.

**`core/sp_channel/bench_sp_hedge.c`** — LIVE bench with flat-array access; DISABLED path exits 0.

---

## 3. Architectural Discipline Citation

**Canonical in-tree disclaimer** (bench_ts_hedge.c, line 8):

> "The TSC rendezvous (fire_tsc), LFENCE pairs, and percentile measurement are diagnostic machinery that exists only here — TailSlayer's runtime path (sp_alloc_channel_pair) loads the cached bin file and does O(1) channel selection with zero probe or pause overhead."

`sp_hedge.c` implements THAT runtime path. The oracle apparatus (two-thread race, LFENCE-bracketed RDTSC, spin barrier, TSC rendezvous) lives in `sp_channel_probe.c` only and was not copied into `sp_hedge.c`.

**TailSlayer reference** (`hedged_reader.hpp`): TailSlayer uses per-replica worker threads pinned to separate cores. The sp_hedge primitives mirror the channel-parallel goal in a single-thread idiom: PREFETCH both channels, LOAD both (or one + warm the other), letting the out-of-order CPU pipeline the two channel fetches in-flight simultaneously. No thread creation, no synchronisation, no signal.

**Replica semantics corrected** relative to the original spec language: the replica hedge warms channel B for the NEXT iteration in a stream of reads (load-balancing), not "winner-takes-all" per-call. Doc comment in sp_hedge.c reflects this.

---

## 4. Correctness Test Results

| Test | Description | Result |
|---|---|---|
| T_HEDGE_PAIR_1 | pair64: out_a/out_b byte-identical to serial reads | **PASS** |
| T_HEDGE_REPLICA_1 | replica: out == src when a == b, sweep 32 values | **PASS** |
| T_HEDGE_BLOCK_1 | block: memcmp(out, src)==0 for sizes 1,7,8,63,64,65,256,4096 | **PASS** |
| T_HEDGE_SPINOR_1 | spinor: 63-byte block round-trip; both replica + non-replica b | **PASS** |
| T_HEDGE_DISABLED | all 4 primitives correct on plain malloc (no channel map) | **PASS** |

99 checks, 0 fails.

---

## 5. Bench Numbers (Beast Canyon LIVE)

Channel map: `SP_INFO: limited recovery, probing bits [6,21) — LIVE` (k=4, 15 address bits, virtual-bit only).

Arrays: 2 × 512 KB flat arrays from `sp_alloc_huge(1, 2MB)` — huge-page alloc succeeded for arena. Both arrays base-address mapped to `ch=0` by `sp_channel_of`.

| Body | P50 (cyc) | P90 (cyc) | P99 (cyc) |
|---|---|---|---|
| baseline | 77,132 | 80,062 | 103,896 |
| hedge | 206,640 | 235,082 | 403,770 |
| ratio (hedge/baseline) | 2.679 | 2.936 | **3.886** |

**M_TS_HEDGE_PROD: FAIL** (P99 ratio 3.886 > 0.85).

**Why the hedge was slower:** Both arrays were placed on the same logical channel (`ch=0`) by the virtual-bit GF(2) map. The hedge issued twice as many reads through the same DDR bottleneck instead of pipelining through two independent channels. The ~2× expected slowdown from double-bandwidth became ~3.9× due to additional cache pressure and memory-controller serialisation.

---

## 6. Findings

### F1 — Physical-address probing is required for the LIVE gate to be meaningful

The channel map was recovered from **virtual address bits [6,21)** only (`limited recovery`). Without huge pages, the physical-to-virtual page mapping is random (ASLR). `sp_channel_of` classifies virtual addresses, not physical ones. The physical DDR channel is determined by physical address bits. Two virtual addresses on different logical channels may or may not be on different physical DDR channels depending on OS page placement.

`sp_alloc_channel_pair` is designed to handle this via huge-page probing (fixed virtual-physical mapping). The bench's direct `sp_alloc_huge` succeeded for the arenas but the channel classification was still virtual-bit only. As a result, both arrays were placed at virtual addresses that map to channel 0.

**Gate prerequisite for PASS**: Run as Administrator with `SeLockMemoryPrivilege` (same requirement as the oracle bench) to enable physical-bit probing and guarantee physical channel diversity.

### F2 — L3 cache residency (secondary concern)

The plan (§5 Path A) predicted WEAK from L3 residency. The actual failure came earlier (same-channel placement). Even with channel-diverse arrays, 512 KB per side fits in Beast Canyon's 12 MB L3 after trial 1. A meaningful DRAM-channel bench needs arrays ≥ 2× LLC = 24+ MB.

### F3 — Bench design iteration

Initial bench design used pointer arrays (ch0[], ch1[]) which added two levels of indirection per element, producing 4.5× slowdown vs baseline (diagnosed immediately). Redesigned to flat arrays with direct element access. The flat design correctly isolates the hedge primitive overhead from pointer-chasing overhead.

### F4 — Baseline-before-TailSlayer discipline (roadmap §16.8 requirement)

Per roadmap §4383–4386: Phase 4-SPEC M_SPEC_3 throughput must be measured WITHOUT TailSlayer first. This sprint delivers the production primitive and correctness gate. The throughput delta measurement (Phase 4-SPEC re-run post-hedge) is separate Phase TS.INTEGRATE scope.

---

## 7. Open Work

| Item | Phase | Depends On |
|---|---|---|
| Re-run bench as Administrator with SeLockMemoryPrivilege — physical channel diversity; expect PASS or WEAK (not FAIL) | §16.3.1 | SeLockMemoryPrivilege grant |
| Extend bench arena to ≥ 24 MB to force DRAM-cold P99 events | §16.3.1 | huge pages |
| §16.4 TS.INTEGRATE-CRT: wire `sp_hedge_read_pair64` into Garner reconstruction (CRT residue q1/q2 hedge read) | §16.4 | §16.3 closed |
| §16.5 TS.INTEGRATE-KSTE: `sp_hedge_read_spinor` into KSTE upper-tier sieve traversal; T0-hinted variant for reused hot set | §16.5 | §16.4 + Phase 5 |
| Phase 4-SPEC M_SPEC_3 re-measurement after §16.4 integration (baseline-before-TailSlayer discipline) | TS.INTEGRATE | §16.4 closed |
