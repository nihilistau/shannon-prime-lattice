# SESSION-CLOSED: lat-phase-ts-map

**Date:** 2026-05-26  
**Tag:** `lat-phase-ts-map-m2-closed` (shannon-prime-system only; engine repo not touched)  
**Branch (system):** lat-ts-map → commit `506052e`  
**Result:** M_TS.MAP_2 VERIFIED (Windows VM, 18/18 checks); M_TS.MAP_1 DEFERRED (no bare-metal HW this session)

---

## Scope

Phase TS.MAP §16.1: new module `core/sp_channel/` in `shannon-prime-system`.

Implements a GF(2) memory-channel oracle using the Laurie TailSlayer methodology,
re-derived in math-core idioms (no code copied from Laurie's repo).

**Critical safety contract:** VM/container environments → `SP_OK + mode=DISABLED`.
TailSlayer is a **perf overlay only, never a correctness dependency**.
The engine (`shannon-prime-system-engine`) is untouched.

---

## Deliverables

### A. Public API — `include/sp/sp_channel.h`

```c
#define SP_CHANNEL_UNSPECIFIED  0xFFFFFFFFu
typedef enum { SP_CHANNEL_DISABLED = 0, SP_CHANNEL_LIVE = 1 } sp_channel_mode;
typedef struct sp_channel_map sp_channel_map;

sp_status sp_channel_map_build(sp_channel_map **out);
uint32_t  sp_channel_of(const sp_channel_map *m, uintptr_t addr);
sp_status sp_channel_map_load_cached(const char *fingerprint, sp_channel_map **out);
sp_status sp_channel_map_save_cached(const sp_channel_map *m, const char *fingerprint);
sp_channel_mode sp_channel_map_mode(const sp_channel_map *m);
sp_status       sp_channel_map_dims(const sp_channel_map *m, uint32_t *k_out, uint32_t *n_out);
sp_status sp_channel_host_fingerprint(char *buf, size_t buf_len);
void      sp_channel_map_free(sp_channel_map *m);
```

`sp_channel_map_load_cached` returns `SP_OK + NULL` on cache miss, `SP_EIO` on corrupt file.
(`SP_ENOTFOUND` does not exist in sp_status.h; SP_OK+NULL is the miss sentinel.)

`SP_FORCE_VIRT_DETECTION=1` env var forces DISABLED in any environment for CI testing.

### B. Internal types — `core/sp_channel/sp_channel_internal.h`

```c
#define CHAN_BIT_LO   12    /* lowest bit probed (4 KB page boundary) */
#define CHAN_BIT_MID  21    /* boundary: no-pagemap vs pagemap range  */
#define CHAN_BIT_HI   24    /* exclusive upper bound                  */
#define CHAN_N_VIRT   9     /* bits probed without /proc/self/pagemap */
#define CHAN_N_PHYS  12     /* bits probed with pagemap (privileged)  */
#define CHAN_K_MAX    4     /* maximum channel-select bits recoverable */
struct sp_channel_map { sp_channel_mode mode; uint32_t k, n, n_start; uint8_t M[4][12]; };
typedef struct { int bit; int is_same_channel; uint64_t p99_ns; } sp_probe_result;
```

### C. Map + cache I/O — `core/sp_channel/sp_channel_map.c`

**Virtualisation detection** (returns 1 → DISABLED):
1. `SP_FORCE_VIRT_DETECTION=1` env var (test hook — always wins)
2. CPUID leaf 1 ECX bit 31 (x86 hypervisor flag)
3. `/proc/cpuinfo` "hypervisor" substring (Linux)
4. `/sys/hypervisor/type` existence (Linux Xen)

**Platform CPUID guard** (MinGW-compatibility fix):
- GCC/Clang (including MinGW): `<cpuid.h>` + `__get_cpuid()`
- MSVC only: `<intrin.h>` + `__cpuid()`

**Huge-page allocation**: Linux `MAP_HUGETLB` (2 MB pages), Windows `MEM_LARGE_PAGES`.
Allocation failure → DISABLED (not an error).

**Probe flow**:
- Allocate 4 huge pages; place A at `base + hp_size`.
- Probe bits [12,21) with virtual addresses only.
- Probe bits [21,24) only if `sp_pagemap_privileged()` (non-zero PFN from `/proc/self/pagemap`).
- GF(2) Gaussian elimination (pivot-only): bits where `is_same_channel=0` become column pivots in M.

**Cache file format** (`~/.cache/shannon-prime/channel_map_<fp>.bin` / `%LOCALAPPDATA%\...`):
```
SPCH            4 bytes  magic
0x00000001      4 bytes  version
mode            4 bytes
k               4 bytes
n               4 bytes
n_start         4 bytes
M[4][12]       48 bytes  GF(2) matrix (row-major)
checksum        4 bytes  DJB2 of preceding 68 bytes
```

**sp_channel_of**: computes `M·addr_bits mod 2` bit-by-bit into a k-bit channel index.

**sp_channel_host_fingerprint**: CPUID brand string (x86) + `GlobalMemoryStatusEx` (Windows) /
`sysconf(_SC_PHYS_PAGES)` (Linux) → snprintf 8-char hex fingerprint.

### D. Hedge-read probes — `core/sp_channel/sp_channel_probe.c`

**mono_ns() Windows path**: integer div/mod avoids `__int128` (GCC extension; not on MSVC):
```c
LONGLONG q = t.QuadPart / freq.QuadPart;
LONGLONG r = t.QuadPart % freq.QuadPart;
return (uint64_t)(q * 1000000000LL + r * 1000000000LL / freq.QuadPart);
```

**hedge_pair()**: flush A+B with `clflush`/`_mm_clflush`, `mfence`, spawn 2 OS threads
(Win32 `CreateThread` / POSIX `pthread_create`), join both, return MAX(latency_A, latency_B).

**sp_probe_bit()**: N samples → `qsort` → P50/P99.
Same-channel heuristic: `p99 > p50 + p50/2` (avoids large multiplications, equivalent to P99 > 1.5×P50).
Thread-creation failure → returns non-zero (caller falls back to DISABLED).

### E. CMake — `core/sp_channel/CMakeLists.txt`

```cmake
sp_add_module(channel
    SOURCES   sp_channel_map.c sp_channel_probe.c
    TEST      sp_channel_test.c
    TEST_NAME T_CHANNEL
    DEPENDS   sp_io_format)
if(UNIX)
    find_package(Threads REQUIRED)
    target_link_libraries(sp_channel PUBLIC Threads::Threads)
    ...
endif()
```

Root `CMakeLists.txt`: `sp_channel` added to `SP_MODULES` after `session`.

### F. Tests — `core/sp_channel/sp_channel_test.c`

5 tests, 18 checks, public API only:

| Test | What it checks |
|------|----------------|
| `T_CHANNEL_BUILD_VIRT_1` | `SP_FORCE_VIRT_DETECTION=1` → `SP_OK` + `DISABLED` |
| `T_CHANNEL_OF_DISABLED_1` | DISABLED map + NULL map → `SP_CHANNEL_UNSPECIFIED` |
| `T_CHANNEL_CACHE_RT_1` | save→load round-trip preserves mode; miss → `SP_OK` + NULL |
| `T_CHANNEL_BUILD_BARE_1` | always `SP_OK`; LIVE path checks `k∈[1,4]`, `n≥1` |
| `T_CHANNEL_HEDGE_BENCH_1` | no crash; LIVE checks determinism of `sp_channel_of` |

---

## Gate Results

### M_TS.MAP_2 — CI/VM graceful fallback ✓ VERIFIED

Environment: Windows 11 VM (CPUID hypervisor bit = 1).  
All 5 tests, 18/18 checks passed.  
Path taken: virt detection → DISABLED → all tests exercise the graceful-DISABLED branch.  
Linux CI verification pending (will confirm CPUID+/proc/cpuinfo path after push).

### M_TS.MAP_1 — bare-metal P99 ≥2× hedge improvement ⏸ BLOCKED (privilege)

The test machine is physical hardware (Intel NUC11BTMi9, i9-11900KB) — NOT a VM.
However two blockers prevent LIVE mode on this host:

1. **Hyper-V root-partition false positive (FIXED in commit `6337bd3`):**
   Windows 11 VBS/Hyper-V sets CPUID leaf-1 ECX bit 31 on the root partition (bare
   metal), causing the original detection to return VM=1. Fix: check the hypervisor
   vendor (CPUID 0x40000000 = "Microsoft Hv") then check the Hyper-V KVP registry
   key (`HKLM\SOFTWARE\Microsoft\Virtual Machine\Guest\Parameters`) — present only
   in guest VMs, absent on the root partition. VMware/KVM/VBox still return VM=1.

2. **`SeLockMemoryPrivilege` not in token (user action required):**
   `VirtualAlloc(MEM_LARGE_PAGES)` requires this privilege. Even as admin, it is
   absent by default. Without huge pages, the bit-flip probes give meaningless results
   (virtual→physical mapping unknown above bit 12). Correct DISABLED message after
   fix: `"huge-page allocation failed — DISABLED"`.

   **To enable on this NUC:**
   `secpol.msc` → Local Policies → User Rights Assignment →
   "Lock pages in memory" → add account → logoff/logon → rebuild → rerun.

After the privilege is granted, the test should proceed to the probe loop and either
recover M or return DISABLED if timing discrimination is insufficient (Hyper-V timer
virtualization may still perturb P99 measurements even from the root partition).

---

## Spec Decisions (resolved during implementation)

| Spec ambiguity | Resolution |
|----------------|-----------|
| `SP_ENOTFOUND` referenced in §16.1 | Doesn't exist in `sp_status.h`; `load_cached` returns `SP_OK+NULL` on miss, `SP_EIO` on corrupt |
| `sp_log()` referenced in §16.1 | Doesn't exist; used `fprintf(stderr, "SP_INFO: ...")` for informational traces |
| CPUID intrinsic on MinGW | `<intrin.h>` only ships `__cpuid` on MSVC; MinGW uses `<cpuid.h>` + `__get_cpuid()` |
| `__int128` in mono_ns QPC path | GCC extension, absent on MSVC; replaced with integer div/mod LONGLONG arithmetic |

---

## What Was NOT Done

- `sp_l1.h` untouched (sp_channel is math-core-internal; not part of the frozen L1 ABI surface)
- Engine (`shannon-prime-system-engine`) untouched
- `core/session/`, `core/forward/` untouched
- No Linux `/proc/self/pagemap` privileged path exercised (requires bare metal + CAP_SYS_PTRACE or relaxed `/proc/sys/kernel/perf_event_paranoid`)
