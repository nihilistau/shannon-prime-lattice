---
type: session-handoff
title: SESSION CLOSED — lat-3-hx-mode-f1-vtcm-staging
description: "Date: 2026-05-29"
tags: [session-handoff, vtcm]
timestamp: 2026-05-29T06:21:35Z
resource: shannon-prime-lattice/papers/SESSION-CLOSED-lat-3-hx-mode-f1-vtcm-staging.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# SESSION CLOSED — lat-3-hx-mode-f1-vtcm-staging
**Date:** 2026-05-29
**Engine commit:** (see tag)
**Umbrella tag:** `lat-phase-3-hx-mode-f1-vtcm-staging-closed`

**Outcome A landed.** The C-side VTCM staging path for the Halide-AOT axpby kernel works end-to-end with the new ingredients. All 4 size cases (cols ∈ {128, 256, 512, 1024}) bitwise-equal the scalar reference with `vtcm_used=1` reported every call. 200/200 perf-bench iterations admitted VTCM and ran cleanly.

**The Sprint F closure note's "unviable" conclusion is empirically reversed.** The next paragraph explains how.

---

## What changed between Sprint F (fail) and Sprint F.1 (pass)

The pre-flight SASS discriminator was **inconclusive in the way the advisor anticipated**: even with `set_host_alignment(128)` declared on all three Inputs/Outputs in the generator, Halide still emitted 20× `vmemu` and 0× `vmem` in the inner-loop range of `sp_axpby_2d_halide.s`. So the codegen-level alignment hint did not reach the Hexagon backend in this configuration. By the original Sprint F theory ("`vmemu` doesn't tolerate VTCM"), this should have predicted another crash.

Device test: 4/4 PASS via VTCM. So `vmem`/`vmemu` was a red herring; that wasn't the discriminator. **Sprint F's root-cause attribution was wrong** even though its empirical "this attempt crashed" observation was correct.

The change-set between the two attempts:

| # | Change | Likely-load-bearing? |
|---|---|---|
| 1 | Generator: `set_host_alignment(128)` on x, a, y | Probably not (SASS unchanged) — defensive |
| 2 | Generator: `.prefetch(x, r, 2)` in the schedule | Possibly — emits dcfetch instructions; unclear if they were the prior crash trigger |
| 3 | Handler: `a` now staged in VTCM (Sprint F left it on DDR) | **Most likely the actual fix** — see below |
| 4 | Handler: per-buffer regions rounded up to 128-byte alignment | Defensive (test sizes were aligned anyway) |
| 5 | Handler: alignment guard before kernel call | Diagnostic; would have returned -1 not crashed |
| 6 | Handler: `halide_buffer_flag_host_dirty` set after memcpy | ABI-correct; effect unclear |
| 7 | Handler: dropped the y-buf sentinel scribble that Sprint F used for triage | Probable contributor — that scribble dirtied a DDR cache line for the same y_buf that Halide was supposed to write to in VTCM, plausibly causing a coherency miss |

The most likely real root cause of Sprint F's crashes is **#3** — mixing DDR (`a`) and VTCM (`x`, `y`) inside a single Halide kernel invocation. The kernel's prefetcher and load-pipelining may not handle the case where adjacent loads in the same packet target different memory regions cleanly under V69's cdsp MMU. Putting all three buffers in VTCM removes the mixed-region exposure.

This is unattributed in the sense that I did not isolate each change one-at-a-time (only the bundled change-set was tested). The honest claim is: **this combination works**; the minimal-fix singleton remains a Sprint G open question that doesn't gate further work.

---

## Outcomes

| Sub-tag | Result |
|---|---|
| `lat-phase-3-hx-mode-f1-vtcm-staging-bitwise` | T_HALIDE_AXPBY_2D_{8x128, 16x256, 64x512, 128x1024} PASS via VTCM (4/4 size cases, every call reports `vtcm_used=1`) |
| `lat-phase-3-hx-mode-f1-vtcm-staging-perf` | T_HALIDE_VTCM_PERF: 200 iter × 64×512 in **286.8 ms**; vtcm_admitted=200/200. (Wall-clock includes FastRPC round-trip + VTCM alloc/free + 2× memcpy + Halide kernel; per-kernel-only timing needs `HAP_perf_get_pcycles()` instrumentation, deferred to Sprint G.) |
| `lat-phase-3-hx-mode-f1-vtcm-staging-closed` | umbrella |

---

## What the Sprint F closure should now read

The Sprint F closure note (committed and pushed at lattice `b6e772d`) stated:

> "VTCM hot-copy DDR→VTCM, point `halide_buffer_t.host` at VTCM, run kernel, copy out — CRASHES inside the Halide kernel's inner HVX loop."

This is true for the specific attempt described there (which left `a` on DDR). It is NOT true as a general claim about Halide-with-VTCM-host-pointers, which is the load-bearing reading.

This Sprint F.1 closure supersedes that conclusion. Sprint F's tag set (`lat-phase-3-hx-mode-f-*`) is left intact for history — the artifacts at those tags are the actual code at that time and the closure document is part of the experimental record, including its now-known-wrong attribution. Sprint F.1 adds new tags rather than retroactively editing F's.

---

## Constraints recorded for Sprint G onward

1. All input/output buffers passed to a Halide kernel should live in the **same memory region** (all DDR or all VTCM); do not mix.
2. Per-buffer VTCM offsets should be **128-byte aligned** in case Halide's codegen at some point starts honoring `set_host_alignment` for HVX — alignment-guard the offsets defensively now.
3. `set_host_alignment(128)` in the generator does **not currently** flip codegen to `vmem` for this schedule on this Halide build (2.4.07) + target. If aligned codegen is wanted, exploration of `.bound()`, `.align_storage()`, or explicit dimension fixing is Sprint G work. The functional path runs fine with `vmemu` on VTCM.
4. Per-kernel timing of VTCM vs DDR cannot be measured from outside the skel (FastRPC round-trip dwarfs the kernel). Sprint G should add `HAP_perf_get_pcycles()` brackets around the `sp_axpby_2d_halide` call and surface the deltas as a rout scalar.

---

## File map (delta from Sprint F)

| Repo | Path | Change |
|---|---|---|
| engine | `tools/sp_halide_gen/sp_axpby_2d_gen.cpp` | +`set_host_alignment(128)` on x/a/y, +`.prefetch(x, r, 2)` |
| engine | `tools/sp_compute_skel/halide_gen/sp_axpby_2d_halide.{o,h,s}` | regenerated AOT outputs |
| engine | `tools/sp_compute_skel/src_dsp/sp_compute_imp.c` | rewrote VTCM hot-copy path in `sp_compute_axpby_2d_halide`; alignment guard; `host_dirty` flag |
| engine | `tools/sp_dsp_smoke/src/test_hvx.rs` | +T_HALIDE_VTCM_PERF (200 iter wall-time) |
| lattice | `papers/SESSION-PLAN-lat-3-hx-mode-f1-vtcm-staging.md` | plan with full Sprint-F-was-wrong disclosure |
| lattice | `papers/SESSION-CLOSED-lat-3-hx-mode-f1-vtcm-staging.md` | this note |
