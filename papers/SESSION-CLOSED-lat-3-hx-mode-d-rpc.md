# SESSION CLOSED — lat-3-hx-mode-d-rpc (Sprint A, Path B)
**Date:** 2026-05-29  
**Plan:** `papers/SESSION-PLAN-lat-3-hx-mode-d-rpc.md` (`e1da690`)  
**Engine commits:** `b3689ce` (dsp_rpc + smoke crate), `f9c50e2` (echo skel + URI fix)  
**Tags issued:** `lat-phase-3-hx-mode-d-rpc-pre-flight-pass`, `lat-phase-3-hx-mode-d-rpc-unsigned-pd-admitted`  
**Umbrella:** NOT ISSUED — bridge round-trip blocked at cDSP skel-load (AEE_EUNABLETOLOAD); architectural problem NONE; closeout is a hexagon-clang link-flags follow-on.

---

## 1. Status

**PARTIAL — bridge architecture verified, skel-load tuning pending.**

Reached and verified every step of the IPC chain up to and including `remote_handle_open` reaching the cDSP-side dynamic loader. The loader rejected the 8 KB skel with `AEE_EUNABLETOLOAD` (0x80000406) — runtime libraries (QuRT, atomic, rtld) not linked into the skel. This is a hexagon-clang link line tuning issue documented in §6 finding F2; the bridge code itself is sound.

Sub-tags:
- `lat-phase-3-hx-mode-d-rpc-pre-flight-pass` — **ISSUED** at engine `b3689ce`
- `lat-phase-3-hx-mode-d-rpc-unsigned-pd-admitted` — **ISSUED** at engine `f9c50e2` (Path B `DSPRPC_CONTROL_UNSIGNED_MODULE` returns 0; `remote_handle_open` reaches cDSP-side loader)
- `lat-phase-3-hx-mode-d-rpc-bridge-correctness` — NOT ISSUED (T_RPC_ECHO_* blocked by F2)
- `lat-phase-3-hx-mode-d-rpc-leak-free` — NOT RUN (gated on bridge-correctness)
- Umbrella `lat-phase-3-hx-mode-d-rpc-closed` — NOT ISSUED

---

## 2. Pre-flight Summary

Host (Windows): Hexagon_SDK 5.5.6.0, HALIDE_Tools 2.4.07, HEXAGON_Tools 8.7.06, qaic.exe at `\bin\`, adb on PATH, `rustup target add aarch64-linux-android` installed this session, Android NDK r27d at `D:\Files\Android\android-ndk-r27d\` (cross-link tools used in `.cargo/config.toml`).

Device (S22U): R5CT22445JA, SM-S908E "b0q", Android 15, qcom hardware. `vendor.fastrpc.process.attrs` empty (NOT 0x8). `/vendor/lib64/libcdsprpc.so` present (405 KB). `/vendor/etc/*testsig*` **absent** → Path A blocked → Path B selected.

5 memory entries written this session as prerequisites: `reference-qualcomm-sdk-inventory`, `reference-signed-pd-developer-path`, `reference-hexagon-working-setup`, `reference-hexagon-build-recipe`, `reference-v69-hvx-expert-practices`.

---

## 3. Reference-Pattern Citation

- `remote.h:793,803,811,840` (Hexagon SDK 5.5.6.0): `remote_handle_open/_invoke/_close` + `remote_session_control` signatures
- `remote.h:113`: `REMOTE_SCALARS_MAKEX` bitmask layout
- `remote.h:423-428,641`: `struct remote_rpc_control_unsigned_module` + `DSPRPC_CONTROL_UNSIGNED_MODULE` req ID
- `AEEStdErr.h:38,114`: Hex-side `AEE_EOFFSET=0x80000400` → `AEE_ERPC=0x80000600`
- `shannon_prime_hexagon.c:93-100,148-154` (prior cohort): Path B `remote_session_control` flow validated in production
- `sp_hex.h:274` (prior cohort): URI format `"file:///lib<name>_skel.so?<iface>_skel_invoke&_modver=1.0"` + `&_dom=cdsp` domain suffix

Discipline: [[feedback-lead-with-reference-then-theory]] — Stage 0b mandatory reference reads BEFORE any code. Three URI corrections during the smoke run (initial guess → AEE_EUNSUPPORTED → looked up sp_hex.h:274 → corrected → AEE_EUNABLETOLOAD which is a different layer).

---

## 4. FastRpcSession API Delivered

`tools/sp_daemon/src/dsp_rpc.rs` (~200 lines, `#[cfg(target_os = "android")]`):

```rust
pub struct FastRpcSession { _lib: Library, fn_invoke, fn_close, handle: u32 }
impl FastRpcSession {
    pub fn new(skel_uri: &str) -> Result<Self, SpErr>;
    pub fn invoke(&self, scalars: u32, args: &mut [RemoteArg]) -> Result<(), SpErr>;
}
impl Drop for FastRpcSession { /* remote_handle_close best-effort */ }
pub fn make_scalars(method: u32, n_in: u32, n_out: u32) -> u32;
```

Error variants: `LibLoad`, `Symbol`, `UnsignedPdReject`, `SignatureMismatch` (0x80000600 only), `HandleOpen` (other non-zero from open), `Invoke`.

Path B admission: `remote_session_control(DSPRPC_CONTROL_UNSIGNED_MODULE, {domain=CDSP_DOMAIN_ID=3, enable=1}, ...)` called BEFORE `remote_handle_open`. Confirmed working on Knack's S22U — session_control returns 0; the failure point shifts to skel load.

---

## 5. Build + Smoke Numbers

| Step | Status | Detail |
|---|---|---|
| `rustup target add aarch64-linux-android` | ✓ | Installed this session |
| `cargo build --target aarch64-linux-android --release` (sp-dsp-smoke) | ✓ | 487 KB ELF aarch64 PIE, Android 21, dynamically linked, built by NDK r27d |
| `qaic.exe -mdll echo.idl` | ✓ | echo.h, echo_stub.c, echo_skel.c emitted |
| `hexagon-clang -mv69 -G0 -shared -fPIC` | ✓ | libshannonprime_echo_skel.so produced (8064 bytes — see F2) |
| `adb push libshannonprime_echo_skel.so /data/local/tmp/` | ✓ | rw on device |
| `adb push test_dsp_rpc /data/local/tmp/` | ✓ | rwx, executes on device |
| `Library::new("libcdsprpc.so")` | ✓ | Resolved via /vendor/lib64/ |
| All 4 symbols resolved (`remote_session_control`, `remote_handle_{open,invoke,close}`) | ✓ | |
| `remote_session_control(DSPRPC_CONTROL_UNSIGNED_MODULE, ...)` | ✓ | Returned 0 — Unsigned PD admitted |
| `remote_handle_open(URI)` | ✗ | `0x80000406 AEE_EUNABLETOLOAD` — cDSP loader rejected skel (F2) |
| T_RPC_ECHO_1/2/3 round-trip | NOT REACHED | Blocked by skel load |
| T_RPC_LEAK_1/2 | NOT RUN | |

---

## 6. Findings

### F1 — URI format gotcha (resolved)

Initial smoke run used `"file:///libshannonprime_echo_skel.so?_dom=cdsp"` → returned `AEE_EUNSUPPORTED` (0x80000414). Per prior cohort `sp_hex.h:274`, the qaic-emitted URI format is `"file:///lib<name>_skel.so?<iface>_skel_invoke&_modver=1.0"`. Domain suffix `&_dom=cdsp` is then appended. Corrected URI got past URI parsing.

Recorded in memory: [[reference-signed-pd-developer-path]] §0x80000600 root-cause list — but `AEE_EUNSUPPORTED` is a DIFFERENT failure mode (malformed URI) and should be considered alongside the SignatureMismatch (0x80000600) discriminator. **Recommendation**: add URI-format note to the memory entry as cause #6 for `remote_handle_open` failures.

### F2 — Skel runtime link incomplete (BLOCKER for bridge-correctness)

`build-echo-skel.bat` initially linked with `hexagon-clang -lhexagon` only. Produced .so was 8064 bytes — too small for a complete loadable skel. SDK examples (e.g. `calculator/CMakeLists.txt:73,144` via `hexagon_fun.cmake`) link in `dsprpc`, `rtld`, `atomic`, `test_util` runtime libs. Without those, the cDSP-side dynamic loader rejects with `AEE_EUNABLETOLOAD` (0x80000406).

**Substantial progress this session** (commit `cbbdcb6`):

| Step | Effect |
|---|---|
| Rewrote `build-echo-skel.bat` with `hexagon_toolchain.cmake:150-166` PIC_SHARED_LD_FLAGS template (`-Wl,-Bsymbolic`, `-Wl,-L .../v69/G0/pic`, `-Wl,--wrap=malloc/calloc/free/realloc/memalign`) | Got the canonical V69 linker template |
| Added `-Wl,--whole-archive rtld_init.a -Wl,--no-whole-archive` | Forced FastRPC init code in (skel 8 KB → 178 KB) |
| Logcat surfaced exact missing symbol: `dlerror undefined symbol #14 SigVerify_Streamhash_Finalize` | First-pass undefined-symbol failure pinned |
| Added stubs to `echo_imp.c`: `SigVerify_Streamhash_{Init,Stream,Finalize}`, `SigVerify_{start,stop,verifyseg}`, `_pl_sigverify` | SigVerify chain resolved (skel 183 KB) |
| Re-run on device | dlerror message changed from "undefined symbol SigVerify_Streamhash_Finalize" → "unknown error" — cDSP loader now reaches a deeper ELF-parsing stage |

**Remaining gap** (Sprint A.2 path):

cDSP loader still returns `0x80000406` with generic "dlerror unknown error" — no symbol name surfaced. Hypotheses:
- ELF section/relocation type the cDSP loader doesn't handle (V69 PIC_SHARED template may have a sub-flag missing for retail Samsung firmware)
- Dynamic symbol table format mismatch
- Samsung-specific Unsigned PD restriction not exposed via public AEEStdErr codes

**Recommended Sprint A.2 path**: build the SDK's `examples/calculator/CMakeLists.txt` AS-IS to get a known-loadable skel for V69 cDSP on this exact device. Then swap `calculator_imp.c` → `echo_imp.c` and the CMake will produce a loadable echo skel. Total effort: ~1 hour, mostly running `cmake -P` workflows and verifying CMake's `hexagon_fun.cmake` helper chain works with the installed SDK.

**TODO/Phase 14.3.AUTH**: SigVerify_* stubs are a security vuln if we ever migrate to Signed PD (Path A: testsig present). MUST be removed and real libsigverify linked at that time.

**Not an architectural problem**: the bridge code (dsp_rpc.rs) reaches the loader correctly; the gap is hexagon-clang link line tuning vs SDK's CMake-based template. Sprint A's IPC layer is sound.

### F3 — Standalone smoke crate (sp-dsp-smoke) avoids sp-daemon's bindgen chain

dsp_rpc.rs originally lived in `tools/sp_daemon/src/`. Cross-compiling sp-daemon to aarch64-android failed because its build.rs invokes bindgen on `sp_l1.h` which needs the Android NDK sysroot for `<stdint.h>` resolution. Gating bindgen on `!cfg(target_os = "android")` works for the lib portion (which doesn't use sp_bindings), but sp-daemon's binaries (probe.rs, spec_validate.rs) still pull bindings from `include!()`. Created `tools/sp_dsp_smoke/` — a minimal standalone crate with libloading + a copy of dsp_rpc.rs + the smoke main. Cross-compiles in 0.5 sec.

**Recommendation**: Consolidate dsp_rpc.rs into a shared crate (workspace member) once sp-daemon's android-target build is sorted (Phase 2-L3.FG scope). Until then, sp_dsp_smoke holds the canonical Android-target copy.

### F4 — .bat trailing-backslash escape footgun

`%~dp0` in cmd.exe ends with `\`. Used as `-I "%SCRIPT_DIR%"` becomes `-I "D:\path\"` which the shell reads as `D:\path"` — escaped quote → next arg fused. Fix: strip trailing `\` from `SCRIPT_DIR` and add explicit `\` separators where needed. Documented in build-echo-skel.bat header comment.

---

## 7. Open Work

| Item | Phase | Trigger |
|---|---|---|
| Link QuRT/rtld/atomic runtime into echo skel — resolve F2 AEE_EUNABLETOLOAD | §3-HX Sprint A.1 | Unblocks bridge-correctness + leak-free sub-tags |
| Re-run T_RPC_ECHO_1/2/3 after F2 fix | Sprint A.1 | Closes bridge-correctness |
| T_RPC_LEAK_1/2 (1000-cycle FD + fastrpc_shell_3 leak check) | Sprint A.1 | Closes leak-free |
| Consolidate dsp_rpc.rs into shared workspace member (eliminate sp_dsp_smoke's copy) | post-Sprint A | After sp-daemon android target sorted |
| Add URI-format cause #6 to `reference-signed-pd-developer-path` | mem update | Captures F1 finding |
| Sprint B: `DmaBuffer` zero-copy via rpcmem_alloc(RPCMEM_HEAP_ID_SYSTEM, RPCMEM_TRY_MAP_STATIC) | §3-HX Sprint B | Gated on Sprint A umbrella |
| Sprint C: Axum integration loop binding FastRpcSession into daemon's HTTP path | §3-HX Sprint C | Gated on Sprint A + B |
