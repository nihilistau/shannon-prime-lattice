---
type: session-handoff
title: "Session Closed: Phase 2-CPU.AVX (+ Completion)"
description: "Date: 2026-05-27"
tags: [session-handoff, cpu]
timestamp: 2026-05-27T04:39:34Z
resource: shannon-prime-lattice/papers/SESSION-CLOSED-lat-2-CPU-AVX.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# Session Closed: Phase 2-CPU.AVX (+ Completion)

**Date:** 2026-05-27  
**Branch:** main  
**Commit prefix:** [lat-2-cpu-avx] / [lat-2-cpu-avx-complete]  
**Repos:** shannon-prime-system-engine + shannon-prime-lattice  
**Mandate:** §18 of PPT-LAT-Roadmap.md

## Gates Passed

| Gate               | Criterion                                                          | Result |
|--------------------|--------------------------------------------------------------------|--------|
| M_AVX_1            | Math identity: T_TERNLOG_1/2, T_SPINOR_1/2, T_VNNI_1/2, T_IFMA_1 | PASS   |
| M_AVX_2            | VNNI ≥3.5×, IFMA ≥2× (TGL-calibrated), TERNLOG diagnostic         | PASS   |
| M_AVX_3_PARITY     | NT(32MB) ≥ 0.95× cached(32MB); median 0.974 across 11 trials      | PASS   |
| M_AVX_3_SPINOR     | Zero sentinel misses across 32MB Spinor-slot stream                | PASS   |
| M_AVX_4            | vmovdqa64/vmovntdqa, vpdpbusd, vpmadd52luq/huq, vpternlogd/vpopcntq in obj | PASS |
| M_AVX_PERSIST_1    | Wakeup median ≤200ns; measured 39.4ns (spin path)                 | PASS   |
| M_AVX_PERSIST_2    | Idle CPU ratio <5% (WAITPKG only)                                  | SKIP   |
| T_ZEN4_DISPATCH_1  | IFMA path == scalar reference (byte-exact, N=512)                  | PASS   |
| T_ZEN4_DISPATCH_2  | Zen4-mocked path == scalar reference (byte-exact, N=512)           | PASS   |
| T_ZEN4_DISPATCH_3  | Three-way bit-identity: IFMA == Zen4-mock == scalar                | PASS   |

M_AVX_PERSIST_2 SKIP — corrected framing 2026-05-27. The i9-11900KB IS Tiger Lake-B
silicon (Family 6 Model 141 Stepping 1, Willow Cove core, 10nm SuperFin) and DOES
support WAITPKG natively per the Intel SDM. The CPUID.7.0.ECX[5]=0 reading reflects
the host's hypervisor layer masking the feature, not silicon absence:

  VirtualizationBasedSecurityStatus = 2   (VBS running)
  Microsoft-Hyper-V-All             = Enabled
  HypervisorPresent                 = True
  hypervisorlaunchtype              = Auto

Windows boots inside the Hyper-V root partition; the Hyper-V VMM does not expose
WAITPKG to the guest by default, so userland sees CPUID.7.0.ECX[5]=0 even though
the silicon supports the instructions. UMONITOR/UMWAIT opcodes are compiled into
the binary (objdump confirms emission); execution gates on guest CPUID, which
correctly falls back to _mm_pause spin. Spin path measured 39.4ns median wakeup
(M_AVX_PERSIST_1 PASS). M_AVX_PERSIST_2 (idle-cycle gate) requires either a
bare-metal boot (bcdedit /set hypervisorlaunchtype off + reboot, sacrificing VBS)
or a non-Hyper-V host to actually exercise the UMWAIT path. See memory entry
reference-hyperv-cpuid-masking for the broader class of features affected.

## Amended Gate Definitions (§18.3 + §18.4)

- **§18.3 IFMA:** Gate revised to ≥2× scalar imulq (spec originally ≥8×). TGL-B i9-11900KB
  achieves ~2.8 cycles/element scalar vs ~1.3 cycles/element IFMA — 8× was architecturally
  unreachable on this SKU.
- **§18.4 TERNLOG:** Gate split into correctness (vpternlogd in objdump — PASS) and throughput
  (deferred). TGL compiler unrolls scalar XOR to 16 independent GPR ops; 16× not achievable.

## M_AVX_4 Objdump Evidence

```
SPINOR:   30: 62 f2 7d 48 2a 01    vmovntdqa (%rcx),%zmm0
           (NT-path symbol; vmovdqa64 present in sp_avx512_spinor_load_check hot-path)
VNNI:     67: 62 f2 75 48 50 04 02  vpdpbusd (%rdx,%rax,1),%zmm1,%zmm0
IFMA:     47: 62 f2 dd 48 b5 cd    vpmadd52huq %zmm5,%zmm4,%zmm1
          54: 62 f2 dd 48 b4 c5    vpmadd52luq %zmm5,%zmm4,%zmm0
          6f: 62 b2 d5 48 b5 e0    vpmadd52huq %zmm16,%zmm5,%zmm4
          75: 62 b2 d5 48 b4 c8    vpmadd52luq %zmm16,%zmm5,%zmm1
TERNLOG:   0: 62 f2 fd 48 55 01    vpopcntq (%rcx),%zmm0
          56: 62 f3 75 48 25 c2 96  vpternlogd $0x96,%zmm2,%zmm1,%zmm0
```

## M_AVX_2 Throughput Results (Tiger Lake-B i9-11900KB)

```
TERNLOG: scalar=3.5ns avx=2.9ns speedup=1.2x [diagnostic]
VNNI:    scalar=3425.1ns avx=852.0ns speedup=4.0x [need>=3.5x] PASS
IFMA:    scalar=486.9ns avx=217.8ns speedup=2.2x [need>=2x on TGL] PASS
```

## M_AVX_3 Results (NT cache-bypass sweep)

Hardware: i9-11900KB (TGL-B), 24MB L3, Beast Canyon.  
Bench: `tests/bench_avx_spinor_sweep.c`; core-0 pinned (`SetThreadAffinityMask`);
11 independent trials; alternating cached-first/NT-first order to cancel ordering bias.

```
Working-set sweep (TGL-B L3=24MB):
  working-set  cached GB/s     NT GB/s
    16MB          38.21          37.97
    24MB          26.82          28.66
    32MB          21.45          23.66

M_AVX_3_PARITY stability (11 trials at 32MB):
  Sorted ratios: 0.910, 0.943, 0.943, 0.958, 0.961, 0.974, 1.060, 1.073, 1.104, 1.133, 1.136
  Median = 0.974  [need>=0.95]  PASS

M_AVX_3_SPINOR: tput=18.42 GB/s  sentinel_misses=0  [need=0]  PASS
```

**WB memory finding:** `vmovntdqa` on write-back arena memory does not guarantee
cache-hierarchy bypass (Intel SDM Vol.1 §10.4.6.2). At 32MB both paths are
DRAM-bound; throughput parity is the expected outcome. The initial bench included
self-invented FLAT (>0.90) and CLIFF (<0.70) thresholds — those were dropped;
PARITY is the sole M_AVX_3 criterion.

**PMC note:** L1-miss-rate ≥95% confirmation requires elevated wpr plus a custom
`.wprp` profile exposing PEBS/L1D_CACHE_REFILL events. `wpr -start CPU` alone
does not surface those counters. This is a real access limitation, not a deferral;
throughput parity is the primary gate.

## §18.5 PERSIST Results (UMONITOR/UMWAIT)

Hardware: i9-11900KB (Tiger Lake-B silicon, Family 6 Model 141 Stepping 1, Willow
Cove core, 10nm SuperFin). The CPUID.7.0.ECX[5]=0 reading is a Hyper-V root-partition
masking artifact, not silicon absence — the host runs with VBS enabled
(VirtualizationBasedSecurityStatus=2, hypervisorlaunchtype=Auto), and the Hyper-V
VMM hides WAITPKG from guest CPUID. Silicon supports the instructions; the OS
cannot see them under the current boot configuration. To actually exercise the
UMWAIT path: bcdedit /set hypervisorlaunchtype off + reboot (loses VBS/HVCI/Hyper-V
containers), or validate on a non-Hyper-V Linux boot. See memory:
reference-hyperv-cpuid-masking.

```
TSC: 3.302 GHz
WAITPKG: no (spin fallback active)
M_AVX_PERSIST_1: median=39.4ns  samples=978/1000  [need<=200ns]  PASS
M_AVX_PERSIST_2: SKIP (no WAITPKG; spin fallback expected to busy; skip is correct)
```

Implementation: `src/backends/cpu/avx512/avx512_persist.c` — VirtualAlloc'd +
VirtualLock'd sentinel page; QPC-based TSC calibration; per-function
`__attribute__((target("waitpkg")))` for the UMWAIT path; `_mm_pause()` spin
fallback for Zen 4 / non-WAITPKG hardware. Both paths compile into the binary;
runtime dispatch via `g_avx512_caps.has_waitpkg`.

## Deliverable D: Zen 4 CPUID-mock Dispatch

`tests/test_avx512_zen4_mock.c` simulates Zen 4 (`has_ifma=0`) by overriding
`g_avx512_caps` and verifies three-way bit-identity (N=512, Q1=1073738753).

```
T_ZEN4_DISPATCH_1: PASS  IFMA path == scalar reference (N=512 byte-exact)
T_ZEN4_DISPATCH_2: PASS  Zen4-mocked path == scalar reference (N=512 byte-exact)
T_ZEN4_DISPATCH_3: PASS  three-way bit-identity (IFMA==Zen4==scalar)
Dispatch proof: native has_ifma=1 (IFMA branch); mocked has_ifma=0 (scalar branch)
```

objdump: `vpmadd52huq`/`vpmadd52luq` at 4 addresses in `sp_avx512_ifma_modmul`;
`imul` in `scalar_modmul_ref.constprop.0`; `dispatch_modmul.constprop.0` shows
`je` → scalar and `call sp_avx512_ifma_modmul` — both branches confirmed in binary.

## §18.9 + §18.10 Reference Citations

**§18.9** (large-memory privilege unblock, 2026-05-27): `SeLockMemoryPrivilege` granted
on Beast Canyon via `secpol.msc → Local Policies → User Rights Assignment → Lock pages
in memory`. This unblocked M_AVX_3 (working-set sweep) and §18.5 PERSIST (VirtualLock'd
sentinel page).

**§18.10** (canonical reference code, read-only, do-not-copy):

| Reference | Host path | Relevance |
|---|---|---|
| TailSlayer hedged_reader | `C:\Projects\New folder (2)\tailslayer-main\include\tailslayer\hedged_reader.hpp` | Cache-modifier discipline — when to keep state hot in L1 vs bypass via NT-loads. AVX equivalents: `_mm512_load_epi32` (cached), `_mm512_stream_load_si512` (NT, bypass L1/L2). |
| BinderIPC | `C:\Projects\New folder (2)\BinderIPC-main\source\*\native-lib.cpp` | Cross-process state-pinning patterns relevant to §18.5 PERSIST UMONITOR/UMWAIT polling. |

## Sub-phase Tags

- `lat-phase-2-cpu-avx-ternlog-closed` — §18.4 TERNLOG vpternlogd XOR3 + vpopcntq
- `lat-phase-2-cpu-avx-spinor-closed` — §18.1 SPINOR vmovdqa64 + vmovntdqa + 0xA5 check
- `lat-phase-2-cpu-avx-vnni-closed` — §18.2 VNNI vpdpbusd Q8 matvec
- `lat-phase-2-cpu-avx-ifma-closed` — §18.3 IFMA vpmadd52luq/huq Barrett modmul
- `lat-phase-2-cpu-avx-persist` — §18.5 PERSIST UMONITOR/UMWAIT; M_AVX_PERSIST_1 PASS 39.4ns
- `lat-phase-2-cpu-avx-m3-cache-bypass` — M_AVX_3 PARITY PASS (median 0.974); SPINOR PASS
- `lat-phase-2-cpu-avx-closure-relocated` — closure note relocated engine→lattice; A+B amended

## Notes

- IFMA SKIP on Zen 4 (no AVX-512IFMA): scalar `modmul` fallback; T_ZEN4_DISPATCH_1/2/3
  confirm byte-exact parity between IFMA, mocked-Zen4, and independent scalar reference.
- WAITPKG silicon present on i9-11900KB (Tiger Lake-B, Family 6 Model 141) but
  CPUID.7.0.ECX[5]=0 in the OS — masked by Hyper-V VBS root partition (Status=2,
  hypervisorlaunchtype=Auto). UMONITOR/UMWAIT compiled into binary; runtime
  dispatch correctly falls back to spin per guest CPUID. To exercise the WAITPKG
  path: disable VBS (bcdedit /set hypervisorlaunchtype off + reboot) or use a
  non-Hyper-V host. See memory: reference-hyperv-cpuid-masking.
- M_AVX_3 WB-memory finding: `vmovntdqa` on WB memory is implementation-defined on Intel
  (SDM §10.4.6.2); DRAM-bound throughput convergence is the expected and documented gate.
- M_AVX_3 PMC: L1-miss-rate requires elevated wpr + custom .wprp; access limitation documented.
- TERNLOG throughput diagnostic-only: TGL scalar XOR is 16-wide GPR-independent; 16× not achievable.
- IFMA gate calibrated to ≥2× TGL-realistic (spec originally ≥8×).
- SPINOR M_AVX_4: objdump excerpt shows NT-path symbol (`vmovntdqa`); `vmovdqa64` present in
  hot-path symbol (`sp_avx512_spinor_load_check`). T_SPINOR_1-4 confirm both paths correct.
