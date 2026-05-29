# SESSION-PLAN — lat-2-l3-fg-cross-compile

**Sprint:** Phase 2-L3.FG-CROSS-COMPILE — math-core C ABI for aarch64-android
**Date:** 2026-05-30
**Commit prefix:** `[lat-2-l3-fg-cc]`
**Predecessor:** Sprint J.5 (`lat-phase-4-sprint-j5-closed`) host-gated the L1
C-ABI + sieve paths (Option A); `/v1/chat` + `/v1/pouw/ledger` return 501 on
android. This sprint flips `sp_no_link` OFF and removes those 501s.

---

## 1. Pre-flight results (Stage 0)

**J.5 intact.** `lat-phase-4-sprint-j5-closed` present; `sp_no_link` still set
at build.rs:52,81 (android chat/ledger = 501); `sp_dsp_smoke` /
`sp_dual_dispatch_smoke` (K v0.alpha surface) untouched.

**Portability — GO (no NEON port).** The math-core `core/` is **x86-free by
design**, stated in-source:
- `forward_kernels.c:3` — *"No x86 intrinsics: the math core stays portable
  across every backend's host."*
- `forward_dispatch.c:9` — the AVX2 reduction lives in the engine backend, not
  here; the math core is the scalar reference.
- `forward.c` includes only `sp/*` + `stdlib/string/math/stdio`.

`grep` for `immintrin|_mm512_|__x86_64__|__builtin_ia32|AVX512|<xmmintrin>`
across all `core/*.c` → **0 matches**. The AVX-512 SIMD (Phase 2-CPU.AVX) is in
the engine's `src/backends/cpu/`, which is **not** in build.rs's 17-lib link
set. **No Stage-0 STOP needed** — this is straightforward NDK targeting.

**Host already links the scalar `core/` forward**, not the AVX backend — so the
android binary runs the identical numerical path (see §6 gate reframe for the
libm caveat).

**CMake scaffolding exists.** Engine `CMakeLists.txt:24`
`option(SP_ENGINE_TARGET_ANDROID …)`; the math-core submodule
(`lib/shannon-prime-system/CMakeLists.txt`) builds via `sp_add_module` with
generic `SP_C_FLAGS` (no `-march`), linking `m`. Building it standalone with the
NDK `android.toolchain.cmake` yields the 17 `.a`.

**bindgen surface is small.** `sp_l1.h` includes `<stdint.h>`, `<stddef.h>` +
`sp/*`. On android bindgen needs `--sysroot=<NDK sysroot>` + `--target=
aarch64-linux-android` (the real use of the sysroot arg J.5 found unnecessary
because J.5 *skipped* bindgen).

**Garner symbols resolve but stay gated by scope.** The J.5 link wall
(`ntt_crt_recombine`, `ntt_free` via `run_garner_loop`) are bare-name symbols in
`core/ntt_crt/ntt_crt.c` — i.e. in lib `sp_ntt_crt`, one of the 17. So after
this sprint they *would* link. `run_garner_loop` nonetheless stays
`cfg(not(android))`: it is NTT-CRT shard recombination for the inference
cluster, out of L3.FG scope (chat + ledger). Mesh "continues from J.5" = empty
peer_map.

---

## 2. Library inventory + minimum-viable set

All 17 (build.rs `MODULES`), all in `lib/shannon-prime-system/core/<dir>`, all
CMake `sp_<name>` STATIC targets, all portable scalar C, bindgen-independent
(they consume `sp/*.h`, no generated bindings):

| Lib | chat? | ledger? |
|-----|:---:|:---:|
| sp_forward | ✓ | |
| sp_forward_dispatch | ✓ | |
| sp_forward_kernels | ✓ | |
| sp_model | ✓ | |
| sp_arena | ✓ | |
| sp_frobenius | ✓ | |
| sp_poly_ring | ✓ (NTT-attn overlay) | |
| sp_vht2 (spinor) | ✓ (KV block) | |
| sp_weight_dtype | ✓ | |
| sp_gguf / sp_io_format / sp_io_hash | ✓ (model load) | |
| sp_sieve | | ✓ |
| sp_kste | | ✓ |
| sp_ntt_crt | (poly_ring dep) | ✓ |
| sp_ok_arith | | ✓ |
| sp_session | ✓ (Rust ffi target) | |

**MV set for chat:** forward, forward_dispatch, forward_kernels, model, arena,
frobenius, poly_ring, ntt_crt, vht2, weight_dtype, gguf, io_format, io_hash,
session. **MV for ledger:** sieve, kste, ntt_crt, ok_arith.
**Decision: build all 17.** The union is already ~16/17, porting cost is zero,
and a complete set avoids a second cross-compile round when endpoints expand.

---

## 3. Cross-compile strategy (CMake)

Build the math-core submodule standalone with the NDK toolchain — *not* the
whole engine (which would pull `src/backends`):

```
cmake -S lib/shannon-prime-system -B build-android-libs \
  -DCMAKE_TOOLCHAIN_FILE=<NDK>/build/cmake/android.toolchain.cmake \
  -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-21 \
  -DSP_SYSTEM_BUILD_TESTS=OFF
cmake --build build-android-libs --config Release
```
→ `build-android-libs/core/<module>/libsp_<module>.a` (17 archives).
A Windows helper `tools/sp_daemon/build-android-libs.bat` wraps this (NDK path +
toolchain file), mirroring J.5's `build-android.bat` pattern.

---

## 4. Daemon link + bindgen strategy (build.rs)

- **Flip `sp_no_link`:** on android, instead of the early `return`, set
  `SP_SYSTEM_BUILD_DIR` to `build-android-libs` and emit
  `cargo:rustc-link-lib=static=sp_<module>` for all 17 + `cargo:rustc-link-lib=
  dylib=m` (NDK libm). Link order: high-level → primitive (existing MODULES
  order is already topological).
- **bindgen on android:** run it (don't skip), adding
  `BINDGEN_EXTRA_CLANG_ARGS` / `.clang_arg("--sysroot=<NDK sysroot>")` +
  `--target=aarch64-linux-android`. Generated fresh (not reused from host —
  bindings are regenerated per target by build.rs anyway).

---

## 5. Rust re-unification strategy (remove J.5 gates; host provably unchanged)

J.5 split host/android because the C ABI didn't link on android. That reason is
gone, so **re-unify** rather than grow a parallel android copy (less code, no
drift). Hard rule: every edit to a host-compiled item is cfg-neutral for host —
only *remove* `cfg(not(android))` (host no-op) or *add* `cfg(android)` blocks
(host no-op). **No host-logic refactor.**

- `main.rs`: drop `cfg(not(android))` from `ffi`/`session`/`sieve_ffi`/`mining`/
  `spec`/`tokenizer` mods (they now compile + link on android).
- `state.rs`: collapse the two `AppState`s into one; the J.5 android-only fields
  (`dsp_session`, `dsp_model`, `kv_cache`) + handles become `cfg(android)`
  additions on the unified struct. Host fields return for android (C ABI links).
- `daemon.rs`: collapse the two `run_inner`s; the DSP load block + `dsp_session`
  open become `cfg(android)` additions in the unified `run_inner`.
  `run_garner_loop` + `spawn_peer_dial` + the QUIC coordinator stay
  `cfg(not(android))` (scope, §1).
- `routes.rs`: un-gate the host handlers (chat/metrics/abort/receipts/telemetry/
  pouw_ledger); **delete** the android chat/ledger 501 stubs (real handlers run
  on both); `v1_dsp_model_info` + the android `v1_dsp_echo` stay `cfg(android)`.
- `server.rs`: re-unify `build_router` — host routes for both targets +
  `cfg(android)` DSP routes (`/v1/dsp/echo`, `/v1/dsp/model_info`).

**Dual-model footprint (on-device-verify risk):** android then loads the DSP
model (≈1.4 GB rpcmem, J.5) *and* the CPU model (754 MB mmap, chat) — ≈2.2 GB.
Should fit the S22U; watch for OOM/thermal during T_NO_REGRESSION.

---

## 6. Gate set

| Gate | Pass criterion |
|------|----------------|
| `T_C_CROSSCOMPILE` | all 17 libs produce `libsp_<m>.a` for aarch64-linux-android. |
| `T_DAEMON_LINK_ANDROID` | `sp_daemon` cross-compiles with `sp_no_link` OFF; ELF grows vs J.5's 5.5 MB; no new linker errors. |
| `T_CHAT_ENDPOINT` | **(REFRAMED — see below)** POST `/v1/chat` on android → 200 SSE with valid tokens; **top-1 greedy-argmax token sequence matches host** for a fixed prompt (bitwise best-effort, not required). |
| `T_LEDGER_ENDPOINT` | GET `/v1/pouw/ledger` on android → 200 SSE; receipts emit at a rate comparable to host. |
| `T_NO_REGRESSION` | J.5's 5 gates still pass; host build byte-behavior unchanged; `sp_dsp_smoke` + K v0.alpha dispatch unaffected. |

### T_CHAT_ENDPOINT reframe (load-bearing — pushback per the J.5 precedent)

The mandate specifies "bitwise-equal to host baseline." **This is likely
unachievable and is not a bug.** Per `reference-ecpu2-qknorm-precision-gate`,
scalar f32 cannot bit-match across implementations once QK-norm / transcendental
precision amplifies — and the decode path runs RoPE (`cosf`/`sinf`), softmax
(`expf`), and RMS/QK-norm via `math.h`. Host (x86 MSVC/MinGW libm) vs android
(aarch64 NDK libm) will diverge in the last ULPs of those transcendentals and in
fma-contraction. **Gate on greedy-argmax top-1 token-sequence equality** (the
decision-relevant invariant the Lattice actually depends on — discrete argmax,
per `feedback-lattice-not-default-engine`), with bitwise logits as best-effort
diagnostics only. If even top-1 diverges, *that* is a real bug → surface with
token-position-of-divergence + scalar-reference comparison (mandate's clause).

---

## 7. Sub-tags

- `lat-phase-2-l3-fg-cross-compile-libs` — 17 libs cross-compile (Stage 2).
- `lat-phase-2-l3-fg-cross-compile-link` — sp_no_link flip + bindgen sysroot.
- `lat-phase-2-l3-fg-cross-compile-chat` — chat endpoint live on android.
- `lat-phase-2-l3-fg-cross-compile-ledger` — ledger endpoint live on android.
- `lat-phase-2-l3-fg-cross-compile-no-regression` — J.5 + host + K regression.
- `lat-phase-2-l3-fg-cross-compile-closed` — umbrella.

---

## 8. Out of scope

- **Halide generators / dispatcher / compute_skel / sp_dsp_smoke** — K v0.beta's
  lane. Must merge cleanly with zero coordination; do not touch.
- **QUIC garner loop / mesh cluster** — stays `cfg(not(android))` by scope
  (its symbols would link, but it's not chat/ledger).
- **New endpoints; bridge changes; CMake-level math-core refactor; widening any
  working-precision contract for android** (a divergence is a bug, not a
  tolerance — per the anti-pattern).

---

## Execution order

1. Stage 2 (per lib group) `feat(l3-fg-cc)`: CMake android build → 17 `.a`.
2. Stage 3 (engine, single) `feat(l3-fg-cc)`: build.rs flip + bindgen sysroot +
   Rust re-unify; android cross-compiles with C ABI linked.
3. Stage 4 (engine) `test(l3-fg-cc)`: on-device chat (top-1 vs host) + ledger +
   J.5/host/K regression.
4. Stage 5 (lattice): closure + sub-tags.

**Plan pushed BEFORE code.** No new memory entries (the NDK-config-per-crate
quirk is captured-on-second-occurrence; this sprint adding `build-android-libs`
config may be that occurrence — evaluate at closure, file separately if so).
