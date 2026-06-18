---
type: session-handoff
title: "SESSION PLAN — lat-3-hx-mode-d-rpc (Sprint A, Path B)"
description: "Date: 2026-05-29"
tags: [session-handoff]
timestamp: 2026-05-29T01:12:56Z
resource: shannon-prime-lattice/papers/SESSION-PLAN-lat-3-hx-mode-d-rpc.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# SESSION PLAN — lat-3-hx-mode-d-rpc (Sprint A, Path B)
**Date:** 2026-05-29  
**Scope:** Phase 3-HX Mode-D Sprint A — IPC bridge ALONE (no DMA-BUF allocator, no Halide AOT, no Axum integration).  
**Admission path:** **B — `DSPRPC_CONTROL_UNSIGNED_MODULE`** (NOT testsig). Selected after pre-flight surfaced missing testsig fixture; Path B is validated in prior cohort at `shannon_prime_hexagon.c:93-100,148-154`.

---

## 1. Stage 0a — Pre-flight Results

### Host (Windows)

| Check | Status | Detail |
|---|---|---|
| `C:\Qualcomm\Hexagon_SDK\5.5.6.0` | ✓ | `remote.h` at `incs\remote.h`; `AEEStdErr.h` at `incs\stddef\AEEStdErr.h` |
| `C:\Qualcomm\HALIDE_Tools\2.4.07` | ✓ | `hl_signnow.cmd` / `hl_signsav.cmd` / `hl_signuse.cmd` (NOT used by Path B) |
| `libcdsprpc.so` aarch64-android | ✓ | `SDK\ipc\fastrpc\remote\ship\android_aarch64\libcdsprpc.so` |
| `adb` on PATH | ✓ | `D:\Files\Android\pt-latest\platform-tools\adb.exe` |
| Rust `aarch64-linux-android` target | ✓ | Installed via `rustup target add aarch64-linux-android` (2026-05-29) |
| `qaic.exe` | ✓ | `SDK\ipc\fastrpc\qaic\bin\qaic.exe` |
| `hexagon-clang` | ✓ | `SDK\tools\HEXAGON_Tools\8.7.06\Tools\bin\hexagon-clang` |

### Device (S22U, R5CT22445JA, SM-S908E "b0q", Android 15)

| Check | Status | Detail |
|---|---|---|
| `adb devices` | ✓ | Single device, authorized |
| `vendor.fastrpc.process.attrs` | ✓ | empty (NOT 0x8 — Signed PD admission possible; but Path B uses Unsigned PD) |
| `/data/local/tmp/` writable | ✓ | OK |
| `/vendor/lib64/libcdsprpc.so` | ✓ | 405,304 bytes, root:root |
| `/vendor/lib/rfsa/adsp/bm2n*.bin` | ✓ | CDSP firmware present |
| `/vendor/etc/*testsig*` | ❌ | **Absent — Path A blocked; Path B selected** |

Per [[reference-signed-pd-developer-path]] Path B: admission via `remote_session_control(DSPRPC_CONTROL_UNSIGNED_MODULE, &data, sizeof(data))` BEFORE `remote_handle_open`. Validated production pattern in lattice-llama cohort.

---

## 2. Stage 0b — Reference Summary

### Production FastRPC API (`remote.h`)

- **Open**: `remote_handle_open(const char *name, remote_handle *ph)` — `remote.h:793`. `name` is the URI; returns 0 = success.
- **Invoke**: `remote_handle_invoke(remote_handle h, uint32_t dwScalars, remote_arg *pra)` — `remote.h:803`. `dwScalars` is built by `REMOTE_SCALARS_MAKE(method_idx, n_in_bufs, n_out_bufs)` macro at `remote.h:113`.
- **Close**: `remote_handle_close(remote_handle h)` — `remote.h:811`.
- **Session control** (admission): `remote_session_control(uint32_t req, void *data, uint32_t datalen)` — `remote.h:840`. With `req = DSPRPC_CONTROL_UNSIGNED_MODULE` (enum value 2 at `remote.h:641`) and `data = struct remote_rpc_control_unsigned_module { int domain; int enable; }` (`remote.h:423-428`).

### Domain identifiers (`remote.h:122-145`)

```
ADSP_DOMAIN_ID = 0,  ADSP_DOMAIN = "&_dom=adsp"
CDSP_DOMAIN_ID = 3,  CDSP_DOMAIN = "&_dom=cdsp"   ← V69 cDSP on S22U
```

### Wire types (`remote.h:161-210`)

- `remote_handle = uint32_t`
- `remote_arg` is a union of `remote_buf { void *pv; size_t nLen }` or remote_handle.

### Error code (`AEEStdErr.h`)

- `AEE_SUCCESS = 0`
- Host-side offset = `0x00000000`; Hexagon-side offset = `0x80000400`
- `AEE_ERPC = AEE_EOFFSET + 0x200` → **0x80000600** when surfaced from cDSP to host. Per [[reference-signed-pd-developer-path]] root-cause map: usually skel-not-signed + no Path B/C admission negotiated.

### Path B sequence (target for Sprint A)

```c
// 1. Open libcdsprpc.so dynamically (Rust libloading)
// 2. Resolve remote_session_control, remote_handle_open, remote_handle_invoke, remote_handle_close
// 3. struct remote_rpc_control_unsigned_module { .domain = 3, .enable = 1 };
//    remote_session_control(DSPRPC_CONTROL_UNSIGNED_MODULE=2, &data, sizeof(data));
//    → cDSP grants Unsigned PD admission for this process
// 4. remote_handle_open("file:///libshannonprime_echo_skel.so?_dom=cdsp", &handle);
//    → loads the UNSIGNED skel into Unsigned PD; no signature check
// 5. remote_handle_invoke(...) round-trips test payload
// 6. remote_handle_close(handle)
```

---

## 3. API Decision

Rust module at `shannon-prime-system-engine/tools/sp_daemon/src/dsp_rpc.rs`. Types:

```rust
pub struct FastRpcSession {
    _lib: libloading::Library,         // keep loaded so symbol ptrs stay valid
    fn_session_control: ...,
    fn_handle_open:  ...,
    fn_handle_invoke: ...,
    fn_handle_close:  ...,
    handle: u32,
}

#[repr(C)]
pub union RemoteArg {
    buf: RemoteBuf,
    h:   u32,
}

#[repr(C)]
pub struct RemoteBuf {
    pub pv:   *mut std::ffi::c_void,
    pub nlen: usize,
}
```

---

## 4. Module Signature

```rust
impl FastRpcSession {
    /// Open Unsigned PD on CDSP_DOMAIN_ID=3 via remote_session_control, then
    /// open the skel handle. `skel_name` is the URI (e.g.
    /// "file:///libshannonprime_echo_skel.so?_dom=cdsp").
    pub fn new(skel_name: &str) -> Result<Self, SpErr> { ... }

    /// scalars = REMOTE_SCALARS_MAKE(method, n_in, n_out);
    /// args slice length must equal n_in + n_out.
    pub fn invoke(&self, scalars: u32, args: &mut [RemoteArg]) -> Result<(), SpErr> { ... }
}

impl Drop for FastRpcSession {
    fn drop(&mut self) {
        // remote_handle_close; ignore errors but log.
    }
}

/// Helper: build the dwScalars u32 (remote.h:105-111)
pub fn make_scalars(method: u32, n_in: u32, n_out: u32) -> u32 {
    ((method & 0x1f) << 24) | ((n_in & 0xff) << 16) | ((n_out & 0xff) << 8)
}
```

## 5. Error Mapping

```rust
#[derive(Debug)]
pub enum SpErr {
    LibLoad(String),       // libloading::Library::new failed
    Symbol(&'static str),  // Library::get<symbol> failed
    UnsignedPdReject(i32), // remote_session_control returned non-zero
    SignatureMismatch(i32),// remote_handle_open returned 0x80000600 (AEE_ERPC)
    HandleOpen(i32),       // other non-zero from remote_handle_open
    Invoke(i32),           // remote_handle_invoke returned non-zero
}
```

Map 0x80000600 → `SignatureMismatch` with diagnostic text naming the five root causes from [[reference-signed-pd-developer-path]]. Any other non-zero from `_open` → `HandleOpen(rc)`. Per anti-pattern rule: do NOT widen the 0x80000600 mapping.

---

## 6. Echo Skel Design

Minimal C source at `shannon-prime-system-engine/src/backends/hexagon/echo_skel/`:

**`echo.idl`**:
```c
#include "AEEStdDef.idl"
interface echo {
    long ping(in sequence<octet> in_buf, rout sequence<octet> out_buf);
};
```

**`echo_imp.c`** (DSP-side implementation):
```c
#include "AEEStdErr.h"
#include "echo.h"   // qaic-generated
int echo_ping(const unsigned char *in, int in_len,
              unsigned char *out, int out_len, int *out_lenWritten) {
    int n = (in_len < out_len) ? in_len : out_len;
    for (int i = 0; i < n; i++) out[i] = in[i];
    *out_lenWritten = n;
    return AEE_SUCCESS;
}
```

Build (no signing — Path B uses Unsigned PD):
1. `qaic.exe -mdll -I incs/stddef echo.idl` → `echo.h`, `echo_stub.c`, `echo_skel.c`
2. `hexagon-clang -O3 -mv69 -G0 -shared -fPIC -I... echo_skel.c echo_imp.c -o libshannonprime_echo_skel.so -lhexagon`
3. `adb push libshannonprime_echo_skel.so /data/local/tmp/`

---

## 7. Smoke Harness Design

`tools/sp_daemon/tests/test_dsp_rpc.rs` — gated on `target_os = "android"`. Cross-compile via `cargo build --target aarch64-linux-android --tests`, push binary to device, run.

- `T_RPC_ECHO_1` — 16-byte deterministic pattern; verify round-trip bytes.
- `T_RPC_ECHO_2` — 4 KB pattern.
- `T_RPC_ECHO_3` — 1 MB pattern (close to FastRPC marshal boundary; baseline malloc'd buffers — Sprint B owns rpcmem).
- `T_RPC_LEAK_1` — 1000 create/invoke/drop cycles; verify host FDs stable via `/proc/<pid>/fd`.
- `T_RPC_LEAK_2` — same; verify no `fastrpc_shell_3` process accumulation on device (`ps -A | grep fastrpc_shell` count stable).

Path B-specific: T_RPC_UNSIGNED_PD_ADMITTED — verify `FastRpcSession::new` succeeds AFTER `DSPRPC_CONTROL_UNSIGNED_MODULE` returns 0. Inspect cDSP process type via `remote_session_control(FASTRPC_REMOTE_PROCESS_TYPE, ...)`; expect `PROCESS_TYPE_UNSIGNED = 1` (`remote.h:493-495`).

NOT testing in this sprint: signed-PD-specific features (VTCM, HMX), bad-signature error mapping (no signed skel exists in Path B; defer T_RPC_SIG_1 to a future Sprint A.2 if Path A becomes available).

---

## 8. Cargo + CMake Wiring

`Cargo.toml`:
```toml
[target.'cfg(target_os = "android")'.dependencies]
libloading = "0.8"
```

Build target chain:
```
.cargo/config.toml:
  [target.aarch64-linux-android]
  linker = "<NDK>/toolchains/llvm/prebuilt/windows-x86_64/bin/aarch64-linux-android21-clang.cmd"
```

NDK path: needs to be found on host. Quick fix: bake `ANDROID_NDK_ROOT` env var. Defer if NDK not present — Sprint A may need an NDK install step.

Skel build: standalone `Makefile` or `.bat` in `src/backends/hexagon/echo_skel/` invoking qaic + hexagon-clang directly. NOT in the main CMake (echo is a DSP build, not an ARM-host build).

Deploy helper: `scripts/deploy-s22u-echo-skel.bat` — mirrors `reference/ISP_ENGINE.md` deploy-s22u.bat pattern. Pushes skel + test binary; sets `ADSP_LIBRARY_PATH="/data/local/tmp;"` (trailing semicolon per [[reference-hexagon-working-setup]]) before running test.

---

## 9. Sub-tag Taxonomy

- `lat-phase-3-hx-mode-d-rpc-pre-flight-pass` — all Stage 0a checks green (testsig MISSING noted; Path B selected)
- `lat-phase-3-hx-mode-d-rpc-bridge-correctness` — T_RPC_ECHO_1/2/3 PASS
- `lat-phase-3-hx-mode-d-rpc-unsigned-pd-admitted` — T_RPC_UNSIGNED_PD_ADMITTED PASS (was -signed-pd-admitted in original prompt; renamed for Path B)
- `lat-phase-3-hx-mode-d-rpc-leak-free` — T_RPC_LEAK_1/2 PASS
- Umbrella `lat-phase-3-hx-mode-d-rpc-closed` after all 4

---

## 10. Anti-patterns (carry forward)

- Don't widen 0x80000600 mapping to catch other errors — five named causes per [[reference-signed-pd-developer-path]]; conflating loses diagnostic precision.
- Don't skip `DSPRPC_CONTROL_UNSIGNED_MODULE` before `remote_handle_open` on Path B — failure mode is silent 0x80000600 that masquerades as signing problem.
- Don't add rpcmem/DMA-BUF in this sprint — Sprint B scope.
- Don't add Halide/VTCM/Signed-PD features to the echo skel — minimum viable handshake.
- Don't bake NDK path into a commit; reference via `ANDROID_NDK_ROOT` env var or Knack-host config.

---

## 11. Commit Plan

| # | Content |
|---|---|
| 1 | Plan (this file) — lattice |
| 2 | dsp_rpc.rs + Cargo.toml addition — engine |
| 3 | echo skel C sources + build script — engine |
| 4 | test_dsp_rpc.rs + .cargo/config.toml for NDK linker — engine |
| 5 | Closure note + tags — lattice |

PUSH plan BEFORE code. Stages 2/3/4 ship per commit on engine; closure pushed last on lattice.

**Mid-session blocker check**: if Android NDK linker missing on host, Stage 4 cross-compile fails. Document blocker in closure, ship Stages 1-3 as PARTIAL, file NDK install as follow-on.
