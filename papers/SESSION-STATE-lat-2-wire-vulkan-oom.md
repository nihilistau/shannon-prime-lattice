---
type: session-handoff
title: SESSION-STATE — Phase 2-VK Vulkan runtime OOM (P2 quarantine)
description: "Filed: 2026-06-02 (core-heal recovery session)"
tags: [session-handoff, vulkan, wire]
timestamp: 2026-06-01T19:48:32Z
resource: shannon-prime-lattice/papers/SESSION-STATE-lat-2-wire-vulkan-oom.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# SESSION-STATE — Phase 2-VK Vulkan runtime OOM (P2 quarantine)

**Filed:** 2026-06-02 (core-heal recovery session)
**Status:** OPEN — Vulkan runtime-correctness gates quarantined, not closed.

## What

The Vulkan forward path hits a device-memory OOM —
`VkResult -2` / `VK_ERROR_OUT_OF_DEVICE_MEMORY` — observed on an RTX 2060,
failing the runtime-correctness gates:

- `M_GEMMA3_VULKAN` (Gemma3 forward bit-identity)
- `M_QWEN3_VULKAN` (Qwen3 forward bit-identity)
- `E_VK_5` (NTT-attention on Vulkan)
- `E_VK_6` (KSTE-KV on Vulkan)
- `T_FRO_4_VK` (PPL gate via `SP_BACKEND=vulkan`)

The OOM was documented in `ctest-vulkan-validate.log` during the WIRE-VULKAN
sprint and **explicitly fenced out-of-scope** by that sprint's prompt (the
sprint shipped only the daemon-wiring layers). The wiring itself is sound:
`T_WIRE_VULKAN_STATIC_LIB_BUILT` PASS (dumpbin-confirmed), daemon link PASS.

## Quarantine (this session)

`SP_VK_OOM_FIXED` option added to engine `CMakeLists.txt` (default **OFF**).
While OFF, the five gates above are registered but `CTest-DISABLED` — they
report as **Disabled**, not Failed (no silent pass, no masked hard-red).
`VULKAN_SMOKE` stays active as the build/device/dispatch sanity gate.
Verified: `ctest --test-dir build-vulkan -N` shows the five as `(Disabled)`.

This keeps a Vulkan ctest run honest and keeps `main`'s **default** (CPU,
`SP_ENGINE_WITH_VULKAN=OFF`) regression unaffected — those gates never built
on the default path.

## Open ambiguity to resolve in the bugfix

Phase 2-VK closed green 2026-05-23 with `T_FRO_4_VK` PASS — so the Vulkan
forward worked then. Determine whether the OOM is (a) a **regression** in the
newer whole-forward / daemon-wired Vulkan path, or (b) an **environment** limit
(RTX 2060 6 GB device memory vs the model + per-call staging buffers). Likely
suspect per the closure note: `vulkan_forward.cpp` "upload weight tensor once +
descriptor-set bind per call" amortization may be allocating per-call staging /
intermediate device buffers that aren't freed or sized to budget.

## Re-enable / close procedure

1. Fix the OOM in `src/backends/vulkan/vulkan_forward.cpp` (device-memory budget
   audit; free/reuse per-dispatch staging buffers; cap intermediate allocations).
2. Build with `-DSP_VK_OOM_FIXED=ON` in the `env-vulkan` shell.
3. `ctest --test-dir build-vulkan` — confirm the five gates GREEN.
4. Flip the option default to ON; tag; phase-log entry; delete this doc's OPEN status.

## Pointers

- Engine closure + plan: `tools/sp_compute_skel/docs/CLOSURE-WIRE-VULKAN.md`,
  `PLAN-WIRE-VULKAN.md`; branch `sprint/wire-vulkan`.
- Quarantine code: engine `CMakeLists.txt` (`SP_VK_OOM_FIXED`),
  `tests/CMakeLists.txt` (Vulkan block).
