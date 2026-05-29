# SESSION PLAN — lat-3-hx-mode-d-hvx (Sprint D MVP)
**Date:** 2026-05-29  
**Goal:** Ship the first HVX-vectorized fixed-point compute kernel through the Sprint A/B/C bridge. Prove that the dispatch chain (HTTP → FastRPC → DmaBuffer → V69 cDSP → HVX vector ops → DmaBuffer-out → HTTP response) carries actual SIMD work, bitwise correctly and faster than scalar.

---

## 1. Scope decision

**Sprint D MVP = HVX-vectorized axpby kernel, hand-written in C with HVX intrinsics or auto-vectorized loops.** The Halide AOT generator-pipeline (write generator C++ on Windows host, link `target=hexagon-...`, integrate `.a` into skel) is **Sprint E** follow-on — the build chain is non-trivial on Windows (Halide.lib + LLVM-DLL linker, generator harness wrangling), and Sprint D's purpose is proving the math goes through the bridge, not building the AOT pipeline.

The eventual Mode D production destination — full FFN with HardSwish-approximated SwiGLU per `reference/ISP_ENGINE.md` — sits behind both Sprint D and §16.5 KSTE integration. Sprint D's MVP scope is one kernel; the architecture for adding more is identical.

### Kernel choice — fixed-point axpby

```c
// y[i] = saturate_i16((a * x[i] + b) >> q_bits)
//   x, y are int16_t buffers of length N
//   a, b, q_bits are int32 scalars
```

Why this:
- Matches the HardSwish polynomial fragment (`(up_val * swish_factor) / (six << Q_BITS)`) from `ISP_ENGINE.md:205-210`
- HVX vectorizes trivially at 64 int16 elements per vector
- Easy bitwise verification against a scalar reference
- Clean perf comparison (scalar memcpy → DSP axpby)

---

## 2. Architecture

### sp_compute_skel (new workspace, mirrors sp_echo_skel structure)

```
tools/sp_compute_skel/
  inc/sp_compute.idl        - interface sp_compute : remote_handle64 {
                                 long axpby(in long n, in long a, in long b, in long q_bits,
                                            in sequence<octet> x_buf, rout sequence<octet> y_buf);
                              };
  src_dsp/sp_compute_imp.c  - sp_compute_open/_close + sp_compute_axpby:
                                 cast x_buf to int16_t*, y_buf to int16_t*,
                                 run axpby loop using HVX-friendly C
                                 (hexagon-clang auto-vectorizes the int16
                                  multiply+shift+saturate to HVX VMPYHV/VASR
                                  with -mhvx -mhvx-length=128B already set
                                  by the SDK CMake template).
  CMakeLists.txt            - SDK template mirroring sp_echo workspace
  build.cmd                 - wraps build_cmake hexagon
```

### dsp_axum_server extension (Sprint C bin gets a new route)

`POST /v1/dsp/axpby` — JSON body:
```json
{
  "a": <i32>, "b": <i32>, "q_bits": <i32>,
  "x_base64": "<base64-encoded int16 LE buffer>"
}
```

Response:
```json
{ "y_base64": "<base64-encoded int16 LE buffer>" }
```

JSON keeps the Sprint D test framework portable (curl/PowerShell can hit it); raw octet-stream binary like Sprint C's `/v1/dsp/echo` would also work, but JSON makes the scalar args (a/b/q_bits) cleaner without a separate query string.

Alternative kept simple: a SECOND raw-octet endpoint `POST /v1/dsp/axpby_bin` where the body is `[a:i32 le][b:i32 le][q_bits:i32 le][x:i16 le ...]` packed; response is `[y:i16 le ...]`. Removes the base64 overhead for perf testing.

I'll ship the binary variant only — simpler, faster, sufficient for Sprint D MVP. JSON wrap = Sprint E if needed.

### dsp_rpc.rs — no changes

The FastRpcSession + DmaBuffer surface from Sprint A+B is unchanged. The new IDL method just lives in a new skel; the smoke binary opens TWO FastRpcSessions (one per skel URI) or uses just the new one.

For Sprint D MVP simplicity: use ONE smoke harness against the new `sp_compute_skel` skel; the echo path from Sprint A is regression-tested separately.

---

## 3. HVX vectorization approach

`hexagon-clang -O3 -mv69 -mhvx -mhvx-length=128B -fvectorize` will auto-vectorize the straight C loop:

```c
for (int i = 0; i < n; i++) {
    int32_t acc = (int32_t)a * (int32_t)x[i] + b;
    acc >>= q_bits;
    if (acc > 32767) acc = 32767;
    if (acc < -32768) acc = -32768;
    y[i] = (int16_t)acc;
}
```

The compiler will emit V69 HVX instructions (`Vh = vmpy(Vh, Rh):sat`, `Vh = vasr(Vh, Rh):sat`, etc.) automatically. We can verify by dumping the SASS with `hexagon-llvm-objdump -d` on the skel.

**If auto-vectorization doesn't produce HVX**, fall back to explicit intrinsics via `<hexagon_protos.h>` / `<hvx_hexagon_protos.h>`. Sprint D plan says: try auto first; intrinsics is the fallback (~20 LOC change).

---

## 4. Tests

### On-device via `dsp_axum_server`

| Test | What | Expected |
|---|---|---|
| `T_HVX_AXPBY_BITWISE_64` | N=64 i16 elements, random a/b/q_bits | bitwise == scalar reference |
| `T_HVX_AXPBY_BITWISE_1024` | N=1024 (16 HVX vectors) | bitwise == scalar reference |
| `T_HVX_AXPBY_BITWISE_65536` | N=65536 (1024 HVX vectors) | bitwise == scalar reference |
| `T_HVX_AXPBY_SATURATE` | a*x[i]+b exceeds i16 range | output clamped to ±32767 |
| `T_HVX_AXPBY_VS_SCALAR` | 1000-iter 64 KB element-wise wall, HVX-on-DSP vs host scalar Rust | DSP path measurably ≠ scalar host (no specific gate — finding) |

### Sub-tag taxonomy

- `lat-phase-3-hx-mode-d-hvx-skel-builds`  — sp_compute_skel CMake build + push succeeds
- `lat-phase-3-hx-mode-d-hvx-bitwise`       — all T_HVX_AXPBY_BITWISE_* + T_HVX_AXPBY_SATURATE pass
- `lat-phase-3-hx-mode-d-hvx-vectorized`    — hexagon-llvm-objdump confirms HVX instructions emitted (V instructions in the SASS dump)
- Umbrella: `lat-phase-3-hx-mode-d-hvx-closed`

---

## 5. Commit plan

| # | Content |
|---|---|
| 1 | Plan (this file) — lattice |
| 2 | sp_compute_skel workspace + axpby imp + SDK CMake — engine |
| 3 | dsp_axum_server: add POST /v1/dsp/axpby_bin handler + open second FastRpcSession (or restructure for both skels) — engine |
| 4 | Smoke test (PowerShell + curl) verified on device — engine |
| 5 | Closure + sub-tags + umbrella — lattice |

---

## 6. Out of scope (explicit Sprint E candidates)

- Halide generator pipeline (write generator C++ + link AOT .a into skel)
- Real FFN with SwiGLU/HardSwish (gated on §16.5 KSTE for the actual model integration)
- VTCM staging (V69 has 256 KB; explicit `HAP_compute_res_acquire_cached` to back the kernel's hot working set)
- DMA prefetch for hiding L2 miss latency in the inner loop

These compose on top of the bridge Sprint D establishes; the lifting is purely additive.
