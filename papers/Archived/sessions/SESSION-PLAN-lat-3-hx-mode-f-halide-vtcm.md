---
type: session-handoff
title: SESSION PLAN — lat-3-hx-mode-f-halide-vtcm (Sprint F)
description: "Date: 2026-05-29"
tags: [session-handoff, vtcm]
timestamp: 2026-05-29T04:05:36Z
resource: shannon-prime-lattice/papers/SESSION-PLAN-lat-3-hx-mode-f-halide-vtcm.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# SESSION PLAN — lat-3-hx-mode-f-halide-vtcm (Sprint F)
**Date:** 2026-05-29
**Goal:** Stand up the Halide AOT generator path for a 2-D fixed-point axpby kernel and use it as the carrier for a hardware litmus test on `HAP_request_VTCM()` under our existing Path-B Unsigned PD admission.

---

## 1. Scope

| Item | Sprint F? |
|---|---|
| Halide AOT generator emitting Hexagon-native .o + .h | **YES** |
| In-skel VTCM litmus probe `HAP_request_VTCM(size, 0)` | **YES** |
| Branching: VTCM hot-copy path vs zero-copy DDR fallback | **YES** |
| New gate `T_HALIDE_VTCM_CHECK` invoking + parsing logcat | **YES** |
| Full FFN (HardSwish-SwiGLU) | NO — gated on §16.5 KSTE; this sprint ships axpby_2d |
| DMA prefetch (non-temporal HVX loads) | NO — Sprint G |
| Halide auto-schedule (Adams2019) | NO — manual `.tile(x,y,xi,yi,128,4).vectorize(xi).unroll(yi)` per mandate |

Rationale: the Halide AOT path is independent of the FFN content. Standing it up with a small kernel (axpby_2d) proves the toolchain + linkage + ABI work end-to-end; the FFN body is a content swap once the carrier is verified. VTCM availability under Unsigned PD is empirically unknown on this device — the litmus probe answers it cheaply on the same call surface.

---

## 2. Toolchain recipe (validated by reading the SDK)

`HALIDE_Tools 2.4.07` ships:

- `Halide/include/Halide.h`, `tools/GenGen.cpp` — generator front-end
- `Halide/lib/Halide.lib` (Windows import lib) — host link
- `Halide/Examples/standalone/simulator/apps/conv3x3a32/test-conv3x3a32.cmd` — the **canonical pure-Hexagon AOT recipe** that this sprint follows verbatim, sans the simulator-only `-lsim_qurt -lhexagon` link step (production skel already has QuRT)
- `Halide/Examples/offload/apps/vtcm/vtcm_alloc/pipeline.cpp` — VTCM intermediate scheduling pattern (not the path we take — we VTCM the input/output via the C skel, not via Halide `.store_in(MemoryType::VTCM)`)

Build chain per the SDK example:

```cmd
:: Host: build the generator
cl.exe /EHsc /I %HALIDE_ROOT%\include sp_halide_gen.cpp %HALIDE_ROOT%\tools\GenGen.cpp ^
       /link /libpath:%HALIDE_ROOT%\lib Halide.lib /out:sp_halide_gen.exe

:: AOT: emit Hexagon-native .o + .h
sp_halide_gen.exe -g sp_axpby_2d -f sp_axpby_2d_halide -o bin ^
                  -e o,h,assembly ^
                  target=hexagon-32-noos-no_bounds_query-no_asserts-hvx_128
```

**Target correction:** the mandate names `hexagon-32-no_asserts-hvx_128`; the SDK's tested target is `hexagon-32-noos-no_bounds_query-no_asserts-hvx_128`.  `noos` (no OS — bare-Hexagon, matches QuRT on cdsp) and `no_bounds_query` (Halide skips the runtime introspection path) are both load-bearing for in-skel use. The `no_asserts` part of the mandate is preserved.

Output: `bin/sp_axpby_2d_halide.o` (Hexagon ELF object) + `bin/sp_axpby_2d_halide.h` (C declaration including `halide_buffer_t` ABI). The `.o` links into `libsp_compute_skel.so` with `target_link_libraries(... PRIVATE sp_axpby_2d_halide.o)` (or as a CMake imported object).

---

## 3. Generator design — `sp_axpby_2d`

```cpp
// 2D fixed-point axpby. y[r,c] = sat_i16((a[c]*x[r,c] + b) >> q_bits)
class SpAxpby2d : public Halide::Generator<SpAxpby2d> {
public:
    Input<Buffer<int16_t>>  x{"x", 2};    // [rows, cols]
    Input<Buffer<int16_t>>  a{"a", 1};    // [cols]
    Input<int32_t>          b{"b"};
    Input<uint8_t>          q_bits{"q_bits"};
    Output<Buffer<int16_t>> y{"y", 2};

    Var c{"c"}, r{"r"}, ci{"ci"}, ri{"ri"};

    void generate() {
        Expr ax = cast<int32_t>(a(c)) * cast<int32_t>(x(c, r));
        Expr s  = (ax + b) >> q_bits;
        y(c, r) = saturating_cast<int16_t>(s);
    }

    void schedule() {
        if (get_target().has_feature(Target::HVX)) {
            const int vec = 64;  // 64 i16 lanes per HVX vector
            y.tile(c, r, ci, ri, vec * 2, 4)   // mandate: 128, 4
             .vectorize(ci, vec)
             .unroll(ri);
            y.dim(0).set_min(0); y.dim(1).set_min(0);
            x.dim(0).set_min(0); x.dim(1).set_min(0);
            a.dim(0).set_min(0);
        }
    }
};
HALIDE_REGISTER_GENERATOR(SpAxpby2d, sp_axpby_2d);
```

`.tile(c, r, ci, ri, 128, 4).vectorize(ci, 64).unroll(ri)` matches the mandate's `.tile(x,y,xi,yi,128,4).vectorize(xi).unroll(yi)` modulo variable names and the explicit vector width (`vec=64` is the i16 lane count of a 128-byte HVX vector — Halide infers it from the type but pinning it is defensive).

---

## 4. VTCM litmus test — skel-side

New IDL method:

```c
long axpby_2d_halide(in long rows, in long cols,
                     in long b, in long q_bits,
                     in  sequence<octet> a_buf,   // cols × i16
                     in  sequence<octet> x_buf,   // rows*cols × i16
                     rout sequence<octet> y_buf,  // rows*cols × i16
                     rout long vtcm_used);        // 1 if VTCM path taken, 0 if DDR fallback
```

Handler skeleton (`sp_compute_imp.c`):

```c
#include <HAP_vtcm_mgr.h>
#include "sp_axpby_2d_halide.h"

int sp_compute_axpby_2d_halide(remote_handle64 h,
        int rows, int cols, int b, int q_bits,
        const uint8_t* a_buf, int a_len,
        const uint8_t* x_buf, int x_len,
        uint8_t*       y_buf, int y_len,
        int* vtcm_used)
{
    size_t need = (size_t)rows * cols * 2;
    void* vtcm = HAP_request_VTCM((unsigned)need * 2 /* x+y */, 0 /* multi-page OK */);

    int16_t *x_dev, *y_dev;
    if (vtcm) {
        FARF(HIGH, "axpby_2d_halide: VTCM admitted (size=%zu)", need*2);
        x_dev = (int16_t*)vtcm;
        y_dev = (int16_t*)((uint8_t*)vtcm + need);
        memcpy(x_dev, x_buf, need);                  // ingress DDR→VTCM
        *vtcm_used = 1;
    } else {
        FARF(HIGH, "axpby_2d_halide: VTCM denied — zero-copy DDR fallback");
        x_dev = (int16_t*)x_buf;
        y_dev = (int16_t*)y_buf;
        *vtcm_used = 0;
    }

    halide_buffer_t hx = make_hbuf_2d(x_dev, cols, rows, sizeof(int16_t));
    halide_buffer_t hy = make_hbuf_2d(y_dev, cols, rows, sizeof(int16_t));
    halide_buffer_t ha = make_hbuf_1d((int16_t*)a_buf, cols, sizeof(int16_t));
    int rc = sp_axpby_2d_halide(&hx, &ha, b, (uint8_t)q_bits, &hy);

    if (vtcm) {
        memcpy(y_buf, y_dev, need);                  // egress VTCM→DDR
        HAP_release_VTCM(vtcm);
    }
    return rc;
}
```

`make_hbuf_*` are local helpers that fill a `halide_buffer_t` with the required Hexagon-host layout: `host = ptr`, `device = 0`, `type = {halide_type_int, 16, 1}`, `dimensions = 2`, `dim[].min = 0`, `dim[].extent`, `dim[].stride`, and the **128-byte alignment flag** in `flags` (`HALIDE_BUFFER_ALIGN_128` if exposed by HalideRuntime.h, else the bit Halide expects — verify at integration).

### What the litmus test tells us

Three observable outcomes; the test records which one fires:

1. `vtcm_used == 1` + logcat "VTCM admitted" → Unsigned PD permits VTCM on this device. Sprint G+ can use VTCM as the default kernel scratch. **Hypothesis the operator wants empirically tested.**
2. `vtcm_used == 0` + logcat "VTCM denied" + kernel-correct y_buf → VTCM blocked; zero-copy DDR works. Sprint G+ kernels rely on SMMU-mapped DDR (Sprint B's working path).
3. `vtcm_used == 0` + kernel-incorrect y_buf → Halide AOT linkage broken (separate from the VTCM question). Treat as a Sprint-F bug; the litmus result is inconclusive until linkage fixed.

Outcomes (1) and (2) both close Sprint F; (3) blocks it.

---

## 5. Gate taxonomy

- `lat-phase-3-hx-mode-f-halide-gen-builds` — host generator binary compiles + links against Halide.lib
- `lat-phase-3-hx-mode-f-halide-aot-emits` — generator successfully emits `sp_axpby_2d_halide.o` + `.h` for the hexagon-32 target (file exists, hexagon-llvm-objdump shows hvx instructions)
- `lat-phase-3-hx-mode-f-skel-links-halide` — `libsp_compute_skel.so` links cleanly with the Halide .o; loads on cdsp (no AEE_EUNABLETOLOAD regression)
- `lat-phase-3-hx-mode-f-halide-bitwise` — T_HALIDE_AXPBY_2D bitwise vs scalar reference (Rust-side `axpby_2d_ref`)
- `lat-phase-3-hx-mode-f-vtcm-litmus` — `T_HALIDE_VTCM_CHECK` records vtcm_used flag + logcat line; both outcomes (admitted/denied) are PASS, only invalid output FAILs
- `lat-phase-3-hx-mode-f-halide-vtcm-closed` — umbrella

---

## 6. Build order + commit plan

| # | Content | Repo |
|---|---|---|
| 1 | This plan | lattice |
| 2 | `tools/sp_halide_gen/{CMakeLists.txt, sp_halide_gen.cpp, build.cmd}` | engine |
| 3 | Run gen + check emit. AOT object lands at `tools/sp_compute_skel/halide_gen/sp_axpby_2d_halide.{o,h}` | engine |
| 4 | `sp_compute.idl` + `sp_compute_imp.c` add `axpby_2d_halide` method; CMake links the Halide .o; `build.cmd` runs the gen + the skel build | engine |
| 5 | `test_hvx.rs` adds T_HALIDE_AXPBY_2D + T_HALIDE_VTCM_CHECK | engine |
| 6 | On-device run + logcat capture; iterate | engine |
| 7 | Tags + closure note | both |

---

## 7. Risks + fallbacks

**R1: Halide AOT for Hexagon fails to emit on this Windows install.**
Most likely failure: `Halide.dll` can't find the Hexagon LLVM backend, or the `target=hexagon-32-...` parse rejects.
Diagnostic: run the SDK's own `conv3x3a32` example first to confirm the install is functional. If broken, fall back to building Halide ourselves or — Sprint F descopes to "VTCM litmus only" using the existing `sp_compute_axpby_hvx` (Sprint E) as the kernel carrier. The litmus answer is still useful even if Halide doesn't land.

**R2: Halide-emitted .o fails to link into `libsp_compute_skel.so`.**
The Halide .o uses Hexagon ABI, expects `halide_malloc`/`halide_free`/`halide_error_*` runtime symbols. The skel's existing PIC_SHARED link template handles malloc; the Halide-runtime symbols may need stubs or `--whole-archive` of `Halide/lib/cdsp/...` (need to verify; the offload example links a Halide DSP runtime skel — for in-process use we replicate just the runtime hooks).
Diagnostic: the link error names the missing symbol; stub it in `sp_compute_imp.c` mirroring the existing SigVerify-stub pattern (Sprint A.1 precedent).

**R3: `HAP_request_VTCM` returns NULL because Unsigned PD blocks it (the user-suspected case is the opposite — that it permits — but either is informative).**
This is the litmus outcome (2). Documented as PASS in §4. Not a build break.

**R4: Halide kernel y_buf wrong.**
Most likely cause: stride or alignment mismatch in the `halide_buffer_t` setup, or wrong dtype tag. Diagnostic: dump first 16 bytes of y_buf and the scalar-reference equivalent; the divergence pattern usually points at row-major vs col-major or off-by-one stride.

**R5: VTCM admitted but kernel runs slower than DDR.**
VTCM has setup cost; for small payloads the memcpy in/out can outweigh the cache-win. Measure both paths even on outcome (1). Sprint F's gate is "VTCM admitted OR denied" — perf comparison is reported but not gated; informs Sprint G.

---

## 8. What this sprint does NOT close

- Halide auto-schedule, prefetch, DMA — Sprint G
- Full FFN (HardSwish-SwiGLU) — gated on §16.5 KSTE
- VTCM for the Sprint-E `sp_compute_axpby_hvx` hot path — only the Halide kernel uses VTCM here; retrofitting the hand-written intrinsic kernel to VTCM is a follow-on once the litmus is known
- Replacing Sprint-E intrinsics with Halide-generated — Halide is added alongside, not in place of; head-to-head bench is informative for Sprint G
