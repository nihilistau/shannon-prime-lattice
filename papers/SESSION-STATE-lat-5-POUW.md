---
type: session-handoff
title: SESSION STATE — Phase 5 PoUW / Friedman Sieve
description: "Date: 2026-05-27"
tags: [session-handoff, pouw]
timestamp: 2026-05-27T14:13:53Z
resource: shannon-prime-lattice/papers/SESSION-STATE-lat-5-POUW.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# SESSION STATE — Phase 5 PoUW / Friedman Sieve

**Date:** 2026-05-27
**Tag:** lat-phase-5-pouw-state
**Status:** STATE — M_POUW_1 VERIFIED (C layer); M_POUW_2 SOURCE DONE (hardware gate pending); M_POUW_3 PENDING

---

## Algorithm Specification

### Friedman Sieve

The sieve maintains a **Pareto-optimal frontier** of KSTE signatures under
the combined Tier-0 + Tier-1 dominance partial order.

**Combined strict dominance**: candidate `c` strictly dominates frontier
member `f` iff:
- `sp_kste_tier0(c, f)` ∈ {SP_DOMINATES, SP_EQUIVALENT}, AND
- `sp_kste_tier1(c, f)` ∈ {SP_DOMINATES, SP_EQUIVALENT}, AND
- at least one tier returns SP_DOMINATES (not both SP_EQUIVALENT).

**Sieve-fold event**: emitted when a candidate strictly dominates ≥1 frontier
members.  The dominated members are removed and the candidate is added.
Candidates absorbed by (dominated by or equivalent to) any frontier member
are discarded silently.  Candidates incomparable to all frontier members
extend the frontier without emitting an event.

**Random walk**: synthetic KSTE candidates are generated from random int16
values in the Tier-0 (bytes 8–19) and Tier-1 (bytes 20–55) label regions,
with frozen v1 header bytes (version=1, branch=3, depth=3).

---

## Receipt Wire Format (frozen v1, 152 bytes)

```
[  0..  7]  magic        "SPRCPT01" (8 bytes, no NUL)
[  8.. 71]  kste_sig     64-byte KSTE tree (sp_kste_tree_t.bytes)
[ 72..103]  seq_hash     SHA-256(kste_sig.bytes)
[104..135]  pubkey       ed25519 verifying key (32 bytes)
[136..143]  round        uint64 LE, global sieve-fold counter
[144..151]  minted_at_ns uint64 LE, CLOCK_REALTIME nanoseconds
```

The 152-byte payload is signed with ed25519 (Rust ed25519-dalek v2).
The 64-byte ed25519 signature accompanies the receipt in the stored
`ReceiptRecord` (`sig_hex`) and is verifiable against `pubkey`.

---

## Gate Summary

| Gate      | Description                                              | Status           |
|-----------|----------------------------------------------------------|------------------|
| M_POUW_1  | Sieve correctness: known-dominating sequence found, event emitted, seq_hash verifies | **VERIFIED (C layer)** |
| M_POUW_1  | ed25519 signature verifies against node pubkey (daemon) | PENDING (daemon runs; no live model for end-to-end test) |
| M_POUW_2  | AVX-512 ternlog bench ≥5× over scalar sieve             | SOURCE DONE — `bench_sieve_hw.c` + `M_POUW_2` CTest registered; LIVE run blocked by VBS |
| M_POUW_3  | TTFT degradation ≤5% under concurrent mining            | PENDING (requires live model + load test) |

---

## What Is Built

### math-core (`shannon-prime-system`, `core/sieve/`)

`include/sp/sp_sieve.h` — Public API + receipt schema constants.

`core/sieve/sp_sieve.c` — Pure C99 Pareto-frontier maintenance.
- `sp_sieve_evaluate()`: in-place compaction + seq_hash via `sp_sha256`.
- Depends on `sp_kste` (Tier-0/Tier-1) and `sp_io_hash` (SHA-256).

`core/sieve/sieve_test.c` — M_POUW_1 fixture:
- **T_POUW_1**: [sig_lo, sig_hi] → 1 fold event, sig = sig_hi, seq_hash = SHA-256(sig_hi.bytes)
- **T_POUW_2**: dominated candidate discarded, 0 events
- **T_POUW_3**: incomparable pair extends frontier, 0 events
- **T_POUW_4**: SP_ESIEVE_FULL on frontier overflow
- **T_POUW_5**: receipt layout offsets (152 bytes, all SP_RECEIPT_OFF_* constants)
- **T_POUW_6**: multi-fold batch (3-element chain, 2 events in order)

**T_SIEVE: 37/37 checks PASS**

### Daemon (`shannon-prime-system-engine/tools/sp_daemon/`)

| File | Change |
|------|--------|
| `Cargo.toml` | Added `ed25519-dalek = "2"`, `rand = "0.8"` |
| `build.rs` | Added `("sieve", "sp_sieve")` to MODULES link list |
| `src/sieve_ffi.rs` | Manual FFI: `SpKsteTree`, `SpSieveEvent`, `sp_sieve_evaluate` extern |
| `src/mining.rs` | Background mining loop: synthetic KSTE generation, sp_sieve_evaluate FFI, receipt packing, ed25519 signing, broadcast DaemonEvent::Mint |
| `src/state.rs` | `DaemonEvent` enum (Chat/Mint), `ReceiptRecord`, AppState + `inference_active`, `receipt_store`, `node_signing_key` |
| `src/routes.rs` | `v1_chat`: `InferenceGuard` sets/clears `inference_active`; `v1_events`: handles both DaemonEvent variants; `v1_receipts`: returns actual store |
| `src/daemon.rs` | Generates ed25519 node keypair at startup, populates new AppState fields, spawns mining task |
| `src/main.rs` | Added `mod mining; mod sieve_ffi;` |

`cargo check`: clean (0 errors, 5 pre-existing dead_code warnings).

---

## Blockers

### M_POUW_2: AVX-512 Throughput

The `sp_avx512_ternlog_kste_round` function exists in the engine's AVX-512
backend (`avx512_ternlog.c`).  A `bench_sieve_hw.c` comparing scalar
`sp_sieve_evaluate` vs the ternlog path is the M_POUW_2 deliverable.
Blocked by: AVX-512 masked by VBS on this host (CPUID.7.0.EBX[16]=0 under
Hyper-V root partition).

**To unblock**: run on bare-metal Linux with AVX-512 hardware, or configure
Hyper-V to expose AVX-512 feature bits to the root partition.

### M_POUW_3: Concurrent TTFT Survival

The inference_active flag is wired; the mining loop backs off with a 50ms
sleep when inference is active.  The TTFT gate requires running a live
inference load test alongside the mining loop and measuring token latency.
Blocked by: no model is loaded in the test environment.

---

## What Is NOT Done

- End-to-end ed25519 verify test (requires daemon startup + model)
- Integration of KSTE-of-actual-KV-cache candidates (§16.5 TS.INTEGRATE-KSTE)

### Completed since initial STATE

`bench_sieve_hw.c` (`tests/` in engine, commit 159a8e1):
- Registered as CTest `M_POUW_2` under `SP_ENGINE_WITH_AVX512`
- DISABLED path: prints `REQUIRES_LIVE_MODE` and exits 0 when AVX-512F absent
- LIVE path: benchmarks `sp_avx512_ternlog_kste_round` vs `sp_sieve_evaluate`, gate ≥5×
- Links `sp_engine` + `sp_sieve`; `cargo build --release` clean (sp_sieve.lib resolves)

`sp_sieve_hash_ptx` (`src/backends/cuda/ptx_hash.cuh`, commit 159a8e1):
- GPU analog of `sp_avx512_ternlog_kste_round` (§18.4, imm8=0x96)
- One lane of the 16-wide XOR3 KSTE mixing step via `ptx_xor3`
- Caller supplies values from positions `lane`, `(lane+1)%16`, `(lane+5)%16`

---

## Path to Full Closure

Phase 5 closes to `SESSION-CLOSED-lat-5-POUW.md` when:
1. M_POUW_2: `bench_sieve_hw.c` reports ≥5× speedup on AVX-512 hardware
2. M_POUW_3: TTFT degradation ≤5% on a timed load test with mining active
3. M_POUW_1 daemon: ed25519 signature verifies in an integration test

No math-core code changes needed for M_POUW_2 or M_POUW_3 — those are
hardware and integration gates.

---

## Prior Closure Chain

- `SESSION-STATE-lat-ts-map.md` (2026-05-27) — TS.MAP/TS.ALLOC state;
  M_TS_FALLBACK VERIFIED; M_TS_HEDGE blocked by SeLockMemoryPrivilege
- **This file** — Phase 5 PoUW/Friedman Sieve; M_POUW_1 C layer VERIFIED;
  daemon wired; hardware gates PENDING
