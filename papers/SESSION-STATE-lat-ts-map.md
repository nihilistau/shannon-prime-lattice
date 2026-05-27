# SESSION STATE — Phase TS.MAP & TS.ALLOC
## §16.1: GF(2) Channel Oracle + Channel-Pair Allocator

**Date:** 2026-05-27
**Tag:** lat-phase-ts-map-alloc
**Status:** STATE (not CLOSED) — infrastructure complete, M_TS_HEDGE pending bare-metal Linux

---

## What Is Built

### Deliverable 1 — GF(2) Channel Oracle (prior session, 2026-05-26)

`src/core/sp_channel/` module: `sp_channel_map.c` + `sp_channel_probe.c`

The oracle is complete. On bare-metal Linux with huge pages:
1. Detects virtualisation via CPUID leaf-1 ECX bit 31 + Hyper-V KVP registry
   check (prevents false-positive on Windows 11 VBS root partition)
2. Allocates a 4 × 2MB huge-page arena (`MAP_HUGETLB`)
3. Probes each address bit in `[12, 24)` by racing two threads on A and
   A^(1<<bit), collecting P99 of MAX(latency_A, latency_B)
4. Recovers the GF(2) matrix M (k×n binary) where `M·addr_bits mod 2 = channel`
5. Caches result at `~/.cache/shannon-prime/channel_map_<host_hash>.bin` (DJB2
   checksum; magic `SPCH` v1)
6. Falls back to `SP_CHANNEL_DISABLED` gracefully in any VM/container/no-huge-page
   environment — no hang, no fault, no non-OK return code

Public API: `sp_channel_map_build`, `sp_channel_of`, `sp_channel_map_load_cached`,
`sp_channel_map_save_cached`, `sp_channel_map_mode`, `sp_channel_map_dims`,
`sp_channel_host_fingerprint`, `sp_channel_map_free`

M_TS.MAP_2 gate: 18/18 checks VERIFIED (DISABLED path, CI)
M_TS.MAP_1 gate: BLOCKED (see §Blockers)

### Deliverable 2 — Channel-Pair Allocator (this session)

`sp_alloc_channel_pair` + `sp_free_channel_pair` added to
`include/sp/sp_channel.h` and implemented in `sp_channel_map.c`.

**LIVE path:** allocates a 4 × huge-page arena (virtual-bit arithmetic
requires huge pages to preserve bits 0–20), then scans cache-line-aligned
addresses using `sp_channel_of()` until two distinct-channel addresses are
found. Returns both pointers plus an opaque `sp_channel_pair_arena` handle.
The scan is O(1) in practice: with k≥1 channels, a diverse pair appears
within the first `2^k` cache lines.

**DISABLED/fallback path:** logs `SP_WARN: Virtualized memory controller
detected, disabling TailSlayer` and returns two pointers from a single
`calloc(128)` block. `sp_channel_of` on these returns `SP_CHANNEL_UNSPECIFIED`.
`sp_free_channel_pair` frees correctly in both paths.

### Deliverable 3 — M_TS_HEDGE Bench

`core/sp_channel/bench_ts_hedge.c` — standalone executable wired in
`CMakeLists.txt` as a separate `add_executable` target (not via
`sp_add_module`'s `TEST=`, which allows only one test target).

**DISABLED path:** exits 0 with:
```
M_TS_HEDGE: REQUIRES_LIVE_MODE (DISABLED — VM/container/no huge-pages)
            Grant SeLockMemoryPrivilege (Windows) or run on bare-metal Linux.
```

**LIVE path** (bare-metal Linux, not yet run):
1. Builds map, allocates 4 × huge-page arena
2. Runs `sp_probe_bit` for all bits in `[CHAN_BIT_LO, CHAN_BIT_HI)` with
   256 samples each
3. Picks lowest-P99 diverse bit (`is_same_channel=0`) and highest-P99
   same-channel bit (`is_same_channel=1`)
4. Verifies ratio P99_same / P99_diverse ≥ 2.0 → M_TS_HEDGE PASS

---

## Gate Summary

| Gate | Description | Status |
|------|-------------|--------|
| M_TS.MAP_2 | Oracle infrastructure, 18 checks (DISABLED path) | **VERIFIED 18/18** |
| M_TS.MAP_1 | Oracle bare-metal GF(2) recovery ≤60s | BLOCKED (§Blockers) |
| M_TS_FALLBACK | bench exits 0 cleanly in DISABLED/VM env | **VERIFIED** |
| M_TS_HEDGE | P99_same / P99_diverse ≥ 2.0 on bare-metal | PENDING (§Blockers) |

---

## Blockers

### SeLockMemoryPrivilege (Windows)

`VirtualAlloc(MEM_LARGE_PAGES)` requires `SeLockMemoryPrivilege`. This privilege
is absent by default on Windows 11 even as Administrator. Without it, huge-page
allocation fails → oracle returns DISABLED → both M_TS.MAP_1 and M_TS_HEDGE
cannot run.

**To unblock on Windows:**
1. `secpol.msc` → Local Policies → User Rights Assignment
2. "Lock pages in memory" → add your user account
3. Log out and back in (privilege takes effect at next logon token)
4. Re-run `bench_ts_hedge.exe` — should enter LIVE path

**Alternatively:** run on bare-metal Linux (CI target). `MAP_HUGETLB` succeeds
without elevated privilege if the kernel has huge pages reserved
(`/proc/sys/vm/nr_hugepages > 0`).

### Hyper-V CPUID false positive

Windows 11 with VBS/Hyper-V sets CPUID leaf-1 ECX bit 31 on the root partition
(bare metal). The oracle correctly handles this via the Hyper-V vendor check
(`0x40000000 = "Microsoft Hv"`) + KVP registry key check — KVP is absent on
the root partition, so the oracle proceeds to the huge-page gate rather than
reporting DISABLED. The remaining block is solely the privilege gate above.

---

## Files Changed (this session)

| File | Change |
|------|--------|
| `include/sp/sp_channel.h` | Added `sp_channel_pair_arena` forward decl, `sp_alloc_channel_pair`, `sp_free_channel_pair` |
| `core/sp_channel/sp_channel_internal.h` | Added `struct sp_channel_pair_arena` definition |
| `core/sp_channel/sp_channel_map.c` | Added `sp_alloc_channel_pair` + `sp_free_channel_pair` implementation |
| `core/sp_channel/bench_ts_hedge.c` | New: M_TS_HEDGE bench with DISABLED-path graceful exit |
| `core/sp_channel/CMakeLists.txt` | Added `bench_ts_hedge` as separate `add_executable` target |

---

## Test Results (this session)

```
T_CHANNEL_BUILD_VIRT_1:    PASS
T_CHANNEL_OF_DISABLED_1:   PASS
T_CHANNEL_CACHE_RT_1:      PASS
T_CHANNEL_BUILD_BARE_1:    PASS
T_CHANNEL_HEDGE_BENCH_1:   PASS

T_CHANNEL: 5/5 PASS (0 failures)

bench_ts_hedge (DISABLED path):
  M_TS_HEDGE: REQUIRES_LIVE_MODE (DISABLED — VM/container/no huge-pages)
              exit=0  ← M_TS_FALLBACK VERIFIED
```

---

## What Is NOT Done

- M_TS.MAP_1: bare-metal oracle calibration ≤60s — requires huge-page privilege
- M_TS_HEDGE: ≥2× P99 improvement proof — requires huge-page privilege
- Integration into `sp_session` or CRT — deferred to `TS.INTEGRATE`

---

## Path to Closure

This phase closes to `SESSION-CLOSED-lat-ts-map.md` when both M_TS.MAP_1 and
M_TS_HEDGE pass on bare-metal Linux CI. No code changes are needed — only
the privilege/hardware gate must be cleared.

---

## Prior Closure Chain

- `SESSION-CLOSED-lat-ts-map.md` (2026-05-26) — M_TS.MAP_2 18/18 VERIFIED;
  M_TS.MAP_1 BLOCKED; sp_alloc_channel_pair noted as absent
- **This file** — alloc primitive added, bench written, M_TS_FALLBACK VERIFIED
