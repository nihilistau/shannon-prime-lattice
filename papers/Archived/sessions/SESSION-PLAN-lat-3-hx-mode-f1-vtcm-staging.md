---
type: session-handoff
title: SESSION PLAN — lat-3-hx-mode-f1-vtcm-staging (Sprint F.1 — retry)
description: "Date: 2026-05-29"
tags: [session-handoff, vtcm]
timestamp: 2026-05-29T06:20:52Z
resource: shannon-prime-lattice/papers/SESSION-PLAN-lat-3-hx-mode-f1-vtcm-staging.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# SESSION PLAN — lat-3-hx-mode-f1-vtcm-staging (Sprint F.1 — retry)
**Date:** 2026-05-29
**Goal:** Re-attempt the C-side VTCM staging path for the Halide-AOT kernel that the prior Sprint F closure declared unviable, with two new ingredients the prior attempt did not test.

---

## 1. Why a retry

Sprint F shipped `papers/SESSION-CLOSED-lat-3-hx-mode-f-halide-vtcm.md` with the conclusion:

> "VTCM hot-copy DDR→VTCM, point `halide_buffer_t.host` at VTCM, run kernel, copy out — CRASHES… Halide-emitted `vmemu` loads don't tolerate VTCM-region host pointers."

The operator's follow-up mandate disputes this with a load-bearing precision claim: the Halide AOT kernel can run against VTCM-backed buffers if (a) the generator declares `set_host_alignment(128)` so codegen can emit aligned `vmem` instead of unaligned `vmemu`, and (b) the schedule includes `.prefetch(input, y, 2)` so hardware prefetch is wired in.

Neither was set in the Sprint F generator. The advisor's call on this — "do the experiment" — is correct: the previous unviability conclusion was reached without testing the ingredients now on the table, so it is empirically unsettled, not refuted.

---

## 2. SASS-discriminator pre-flight (before any device cycle)

The hypothesis splits cleanly:

| If after rebuild | Then |
|---|---|
| Halide emits `vmem` (aligned) | The alignment hint reached codegen. Device test with VTCM hot-copy is the real experiment. |
| Halide still emits `vmemu` (unaligned) | The alignment hint did not propagate. Either codegen can't honor it for this schedule, or the `vmem`/`vmemu` axis is not the real discriminator. Test anyway, but with reframed expectations. |

`grep -c "= vmem("` and `grep -c "= vmemu("` on the inner-loop range of the regenerated `.s` answer it for free.

---

## 3. Generator changes (`tools/sp_halide_gen/sp_axpby_2d_gen.cpp`)

```cpp
void schedule() {
    x.dim(0).set_min(0);  /* …existing… */
    x.set_host_alignment(128);   // NEW
    a.set_host_alignment(128);   // NEW
    y.set_host_alignment(128);   // NEW

    if (get_target().has_feature(Target::HVX)) {
        y.hexagon()
         .tile(c, r, ci, ri, 128, 4)
         .vectorize(ci, 64)
         .unroll(ri)
         .prefetch(x, r, 2);     // NEW (mandate)
    }
}
```

Target string stays `hexagon-32-noos-no_bounds_query-no_asserts-hvx_128` — Sprint F proved `noos` and `no_bounds_query` are load-bearing for in-skel use; the mandate's shorter `hexagon-32-no_asserts-hvx_128` is a truncation to ignore.

---

## 4. Skel handler changes (`sp_compute_imp.c::sp_compute_axpby_2d_halide`)

```c
size_t n_a_a  = (cols * 2 + 127) & ~127;       // round up to 128
size_t n_xy_a = (rows * cols * 2 + 127) & ~127;
size_t need   = n_a_a + n_xy_a + n_xy_a;        // a, x, y

void *vtcm = HAP_request_VTCM(need, 0);
if (vtcm) {
    a_dev = vtcm;
    x_dev = vtcm + n_a_a;
    y_dev = vtcm + n_a_a + n_xy_a;
    if (((uintptr_t)a_dev | (uintptr_t)x_dev | (uintptr_t)y_dev) & 127)
        return -1;                              // advisor's alignment guard
    memcpy(a_dev, a_buf, cols * 2);
    memcpy(x_dev, x_buf, rows * cols * 2);
    *vtcm_used = 1;
} else {
    /* litmus says this branch won't fire on S22U, but keep it. */
    ...
    *vtcm_used = 0;
}

hbuf2_i16_init(&hx, …, x_dev, …);
hbuf2_i16_init(&hy, …, y_dev, …);
hbuf1_i16_init(&ha, …, a_dev, …);
hx.flags |= halide_buffer_flag_host_dirty;     // host-side wrote
ha.flags |= halide_buffer_flag_host_dirty;

int rc = sp_axpby_2d_halide(&hx, &ha, b, q_bits, &hy);

if (vtcm) {
    memcpy(y_buf, y_dev, rows * cols * 2);
    HAP_release_VTCM(vtcm);
}
```

Three deviations from the Sprint F attempt:

1. **All three buffers go to VTCM**, not just x and y. The Sprint F attempt left `a` on DDR; mixing DDR + VTCM in one kernel call is a candidate root cause of the prior crashes (the inner loop's prefetcher may not handle mixed-region loads).
2. **128-byte region alignment** — each per-buffer region is rounded up so adjacent offsets stay 128-aligned. (Sprint F did `x_dev=vtcm; y_dev=vtcm+n_xy` which happened to be aligned for the test sizes, but didn't enforce it.)
3. **`host_dirty` flag** set after the memcpy so Halide's ABI knows the host is the authoritative copy.

Names: `HAP_request_VTCM`/`HAP_release_VTCM` (real SDK names). The mandate's `HAP_vtcm_alloc`/`HAP_vtcm_free` don't exist — don't echo the typo into source.

---

## 5. Gates

- `lat-phase-3-hx-mode-f1-vtcm-staging-bitwise` — T_HALIDE_AXPBY_2D_{8x128, 16x256, 64x512, 128x1024} bitwise-equal scalar reference with `vtcm_used=1` reported every call
- `lat-phase-3-hx-mode-f1-vtcm-staging-perf` — T_HALIDE_VTCM_PERF reports wall-time for 200×(64×512) iterations through the full VTCM pipeline (informational; per-kernel timing requires Sprint G micro-bench tooling)
- `lat-phase-3-hx-mode-f1-vtcm-staging-closed` — umbrella

---

## 6. Two acceptable outcomes

- **A:** Bitwise PASS with `vtcm_used=1` on all 4 sizes. Sprint F's "unviable" conclusion is empirically reversed. Sprint F.1 lands the working VTCM staging path. Document which change made the difference if attributable (single-change discipline) or note that the change-set was bundled if not.
- **B:** Still crashes. The bundled change-set wasn't sufficient. Reframe to `.store_in(MemoryType::VTCM)` on an intermediate Func (the canonical SDK pattern) for Sprint G's 2-stage FFN-shaped kernel, where there's an intermediate to actually stage. The litmus + DDR Halide AOT results from Sprint F still stand.

Either outcome is publishable; the experimental discipline is the deliverable.

---

## 7. What this sprint does NOT do

- Per-kernel timing of VTCM vs DDR — needs in-skel `HAP_perf_get_pcycles()` instrumentation, deferred to Sprint G
- Auto-schedule, DMA, full FFN — Sprint G+
- `.store_in(MemoryType::VTCM)` exploration — Sprint G; only relevant if Sprint F.1 outcome B
