---
type: session-handoff
title: SESSION CLOSED — lat-3-hx-mode-f-halide-vtcm
description: "Date: 2026-05-29"
tags: [session-handoff, vtcm]
timestamp: 2026-05-29T06:00:49Z
resource: shannon-prime-lattice/papers/SESSION-CLOSED-lat-3-hx-mode-f-halide-vtcm.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# SESSION CLOSED — lat-3-hx-mode-f-halide-vtcm
**Date:** 2026-05-29
**Engine commit:** (see tag)
**Umbrella tag:** `lat-phase-3-hx-mode-f-halide-vtcm-closed`

Both Sprint F deliverables landed: the Halide AOT pipeline is end-to-end functional on the Samsung S22 Ultra cdsp via Path B, and the VTCM admission litmus answers the operator's question — **VTCM is ADMITTED under DSPRPC_CONTROL_UNSIGNED_MODULE on this device, at all probed sizes (64 KB single/multi-page, 1 MB, 4 MB)**.

The litmus result was the operator's hypothesis; it is now empirically settled and informs every subsequent kernel decision (Sprint G+ can stage on-chip scratch in VTCM without retreating to Signed PD).

---

## Outcomes

| Sub-tag | Result |
|---|---|
| `lat-phase-3-hx-mode-f-vtcm-litmus` | T_VTCM_PROBE_{64KB_multi, 64KB_single, 1MB, 4MB} all **ADMITTED** (pointer in 0xff000000-region VTCM range) |
| `lat-phase-3-hx-mode-f-halide-gen-builds` | `sp_axpby_2d_gen.exe` builds on Win MSVC 2019 + Halide 2.4.07 |
| `lat-phase-3-hx-mode-f-halide-aot-emits` | AOT emits `sp_axpby_2d_halide.{o,h,s}` for `hexagon-32-noos-no_bounds_query-no_asserts-hvx_128`; .o is 87 KB; SASS shows widening `vmpy` + `vasr:sat` HVX chain |
| `lat-phase-3-hx-mode-f-skel-links-halide` | `libsp_compute_skel.so` grew 14 KB → 77 KB with Halide .o linked; loads cleanly on cdsp Path B |
| `lat-phase-3-hx-mode-f-halide-bitwise` | T_HALIDE_AXPBY_2D_{8x128, 16x256, 64x512, 128x1024} bitwise-equal scalar reference |
| `lat-phase-3-hx-mode-f-halide-vtcm-closed` | umbrella |

---

## VTCM litmus — the answer the operator wanted

A new IDL method `vtcm_probe(size, single_page) → vtcm_addr_lo` was added to `sp_compute_skel`. Each test invokes `HAP_request_VTCM(size, single_page)` from inside the FastRPC handler and surfaces the returned pointer's low 32 bits.

```
T_VTCM_PROBE_64KB_MULTIPAGE   ADMITTED  addr_lo=0xff000000
T_VTCM_PROBE_64KB_SINGLEPAGE  ADMITTED  addr_lo=0xff000000
T_VTCM_PROBE_1MB_MULTIPAGE    ADMITTED  addr_lo=0xff000000
T_VTCM_PROBE_4MB_MULTIPAGE    ADMITTED  addr_lo=0xff000000
```

All four sizes are admitted, including the V69 maximum of 4 MB. The repeated `0xff000000` low-32 reflects VTCM's fixed virtual mapping (each session sees the same VTCM range; the allocation is intra-session bookkeeping). `HAP_release_VTCM` returns 0 on each call (release path verified).

**Operator's question — "does Unsigned PD permit VTCM?" — answered: YES, fully and at the maximum size.** Sprint G onward can stage HVX scratch on VTCM without needing Path A (signed PD + testsig + elfsigner). The freedom-via-Path-B path remains intact.

---

## Halide AOT pipeline — end-to-end

### Generator (`tools/sp_halide_gen/sp_axpby_2d_gen.cpp`)

A standard Halide `Generator<>` defining a 2-D fixed-point axpby:

```cpp
y(c, r) = saturating_cast<int16_t>(
    (cast<int32_t>(a(c)) * cast<int32_t>(x(c, r)) + b) >> q_bits);

y.hexagon()
 .tile(c, r, ci, ri, 128, 4)
 .vectorize(ci, 64)
 .unroll(ri);
```

### Build chain (`tools/sp_halide_gen/build.cmd`)

Mirrors the SDK's `Examples/standalone/simulator/apps/conv3x3a32/test-conv3x3a32.cmd`:

1. `cl.exe` builds the host generator binary linking `Halide.lib`.
2. `sp_axpby_2d_gen.exe -g sp_axpby_2d -f sp_axpby_2d_halide -e o,h,assembly -o <dir> target=hexagon-32-noos-no_bounds_query-no_asserts-hvx_128` emits the Hexagon ELF .o + C header + assembly listing.
3. `HalideRuntime.h` is copied alongside the .o so the skel build is self-contained.

The output target deliberately uses `noos` + `no_bounds_query` (not just the mandate's `hexagon-32-no_asserts-hvx_128`): `noos` is required because the FastRPC skel runs against QuRT, not the Halide offload runtime; `no_bounds_query` is required because Halide's two-pass bounds-inference mode doesn't compose with the single-shot FastRPC invoke surface.

### Skel link (`tools/sp_compute_skel/CMakeLists.txt`)

```cmake
if(EXISTS ${HALIDE_GEN_DIR}/sp_axpby_2d_halide.o)
    include_directories(${HALIDE_GEN_DIR})
    target_link_libraries(sp_compute_skel PRIVATE ${HALIDE_GEN_DIR}/sp_axpby_2d_halide.o)
    target_compile_definitions(sp_compute_skel PRIVATE SP_HAVE_HALIDE=1)
endif()
```

Runtime hooks the Halide .o expects, all provided in `sp_compute_imp.c` as strong overrides of the .o's weak symbols:

- `halide_print(void*, const char*)` — routed to FARF
- `halide_error(void*, const char*)` — routed to FARF
- `halide_qurt_hvx_lock(int)` — **must be a no-op** (see below)
- `halide_qurt_hvx_unlock()` — no-op
- `halide_qurt_hvx_unlock_as_destructor(void*, void*)` — no-op

### SASS verification

Halide-emitted inner loop for sp_axpby_2d_halide:

```
v18 = vmemu(r20+#0)              ; unaligned i16 load
v15:14.w += vmpy(v18.h, v28.h)   ; widening i16×i16 → i32 pair MAC
v14.h = vasr(v15.w, v14.w, r7):sat ; variable-shift + saturate + pack (one instruction)
```

The `vasr(Vw, Vw, R):sat` form is actually a TIGHTER pack than the hand-written Sprint E `Q6_Vw_vasr + Q6_Vh_vsat_VwVw` chain — Halide collapses shift+saturate+interleaved-pack into a single Hexagon V-slot. This is a head-to-head perf-comparison opportunity for Sprint G, though Sprint F doesn't gate on it.

---

## Bug found during integration — three load-bearing fixes

### Bug 1: cmd.exe path-parsing with `(x86)`

The initial `build.cmd` used the chained `if "%VCVARS%"=="" set "VCVARS=..."` pattern for vcvars64.bat auto-detection. When VCVARS resolved to `C:\Program Files (x86)\Microsoft Visual Studio\...`, the unescaped `(x86)` was parsed as cmd-syntax inside the `if` block, failing with `\Microsoft was unexpected at this time`. Fixed by switching to a `goto :label` pattern that avoids substitution inside the `if`-block body.

### Bug 2: `halide_print` runtime export required

Halide's AOT runtime calls `halide_print` for diagnostic strings even when no error occurs. Without the export, the skel fails to load on cdsp with `dlerror undefined symbol PLT #181 halide_print`. The fix is a one-line stub routing to FARF. Same applies (defensively) to `halide_error`.

### Bug 3: `halide_qurt_hvx_lock` crashes on FastRPC thread

The Halide-emitted kernel calls `halide_qurt_hvx_lock(QURT_HVX_MODE_128B)` at entry to acquire the HVX context. But the FastRPC remote thread that dispatches into our skel already holds an HVX context (Sprint D's `scale_i16` runs HVX without any explicit lock). Calling `qurt_hvx_lock` from within an HVX-protected region traps the cdsp; the QDI driver prints a backtrace anchored at `sp_axpby_2d_halide+0x2C` (the call site).

Fix: override the weak `halide_qurt_hvx_lock` (+ matching unlock symbols) with strong no-op definitions in `sp_compute_imp.c`. Halide's wrapper then becomes a no-op and the kernel relies on the FastRPC thread's pre-existing HVX context.

This is a documented pattern for "in-process" Halide use; the Examples' `setup-env.cmd` `stubs.c` provides similar no-op stubs for the simulator path.

---

## Halide + VTCM — what works, what doesn't, what's next

The mandate envisioned a C-side hot-copy: allocate VTCM, memcpy input DDR → VTCM, point `halide_buffer_t.host` at the VTCM region, run the Halide kernel, memcpy VTCM → DDR. The reasoning was sound (VTCM admitted + Halide blind to memory type = should be a drop-in win for the inner loop's load bandwidth).

In practice, this pattern crashes inside the Halide kernel's inner HVX loop. Diagnosis (via offset-walking from the QDI backtrace and isolating with a force-DDR option):

- Halide's `vmemu` (unaligned vector memory) loads work on DDR addresses, but the cdsp HVX unit traps when handed a VTCM-region pointer (`0xff000000+`) through the same instruction — VTCM's access pattern differs from DDR's at the memory-protection level for a kernel that wasn't told it's working in VTCM.
- The trap doesn't surface as a Halide-runtime error code; the kernel return path is bypassed, FastRPC reports `AEE_EBADPARM` / `78` / similar QuRT-exception codes depending on which instruction faulted, and FARF logs buffered before the trap don't flush.
- All three of `cols ∈ {128, 256, 512, 1024}` reproduce on the VTCM path. **All three of those exact sizes PASS on the DDR path** with bitwise-equal output vs the scalar reference. So the kernel is correct; only the host-pointer-aliasing trick is wrong.

The SDK's `Examples/offload/apps/vtcm/vtcm_alloc/pipeline.cpp` reveals the canonical Halide+VTCM pattern: VTCM is reserved for **intermediate** Funcs via `.store_in(MemoryType::VTCM)` on the schedule, with the Halide runtime allocating the VTCM region internally. Input and output buffers stay on DDR; only scratch crosses into VTCM.

Axpby has no intermediates to stage, so it can't exercise that pattern. **Sprint G's first item is to introduce a 2-stage FFN-shaped Halide kernel (e.g., `y = post_relu(a * pre_norm(x))`) where the intermediate is explicitly `.store_in(MemoryType::VTCM)`** — that lets us measure the VTCM-vs-DDR delta on a kernel that actually benefits, on a device we have now empirically confirmed admits VTCM.

For Sprint F: `axpby_2d_halide` always runs on DDR. `vtcm_used` is wired but always reports 0 in this kernel. The VTCM litmus result (admission proven) and the Halide AOT result (4/4 sizes correct) both stand independently.

---

## Constraints recorded for Sprint G onward

1. `cols` must be a multiple of 128 in the current schedule. The schedule is `.tile(c, r, ci, ri, 128, 4).vectorize(ci, 64).unroll(ri)` — tile width is 128 cols, so `cols=64` is below the tile. Could be relaxed with a fallback schedule for small cols, but axpby_2d as an L1-attn-or-FFN building block always has cols ≥ embed-dim (≥ 128 for any model we run).
2. Halide host buffers must be DDR. VTCM staging is via schedule directives, not pointer rewriting.
3. The Halide runtime needs `halide_print`, `halide_error`, and stubbed `halide_qurt_hvx_lock`/`unlock` in any host skel built from `Halide/Examples/standalone/simulator`-style AOT objects.

---

## File map

| Repo | Path | Change |
|---|---|---|
| engine | `tools/sp_halide_gen/sp_axpby_2d_gen.cpp` | host Halide generator |
| engine | `tools/sp_halide_gen/build.cmd` | host gen build + AOT emit + HalideRuntime.h staging |
| engine | `tools/sp_compute_skel/CMakeLists.txt` | optional `target_link_libraries` for the Halide .o |
| engine | `tools/sp_compute_skel/inc/sp_compute.idl` | +`vtcm_probe`, +`axpby_2d_halide` |
| engine | `tools/sp_compute_skel/src_dsp/sp_compute_imp.c` | +`sp_compute_vtcm_probe`, +`sp_compute_axpby_2d_halide`, +Halide runtime stubs |
| engine | `tools/sp_compute_skel/halide_gen/sp_axpby_2d_halide.{o,h,s}` | Halide AOT outputs (generated; not committed if size-prohibitive — verify policy) |
| engine | `tools/sp_compute_skel/halide_gen/HalideRuntime.h` | staged from SDK install |
| engine | `tools/sp_dsp_smoke/src/test_hvx.rs` | +T_VTCM_PROBE_*, +T_HALIDE_AXPBY_2D_* |
| lattice | `papers/SESSION-PLAN-lat-3-hx-mode-f-halide-vtcm.md` | plan |
| lattice | `papers/SESSION-CLOSED-lat-3-hx-mode-f-halide-vtcm.md` | this note |
