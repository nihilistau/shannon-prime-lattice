# SESSION CLOSED — Phase 2-L3.CORE

**Tag:** `lat-phase-2-l3-core-closed`
**Date:** 2026-05-26
**Host:** Windows 11 Pro, x86_64, MSVC toolchain (Rust stable-x86_64-pc-windows-msvc 1.92.0)

## Scope

Phase 2-L3.CORE — axum scaffold wrapping the frozen L1 C ABI in a long-lived
HTTP daemon on `127.0.0.1:8080`. Sessions survive UI lifecycle events.
VERBS / SSE / FG / AUTH are subsequent sessions; `lat-phase-2-l3-closed`
fires only after all five sub-phases complete.

## Repo location chosen

**`shannon-prime-system-engine/tools/sp_daemon/`** alongside `sp_transcode`.

Rationale over `shannon-prime-lattice/sp-daemon/`:
- Direct relative paths in `build.rs` to the engine's math-core headers
  (`../../lib/shannon-prime-system/include/`) and built libs
  (`../../build-cpu/lib/shannon-prime-system/`).
- Consistent "tools that consume the engine" pattern (sp_transcode is a peer).
- Lattice repo carries only specs, papers, frontends — no compiled artefacts.

## Daemon binary

| Metric | Value |
|---|---|
| Binary name | `sp-daemon` |
| Release size | **2.7 MB** (Windows MSVC x86_64, stripped) |
| Crate | `shannon-prime-system-engine/tools/sp_daemon/` |
| Engine commit | `6a35f39` |

## FFI handle confirmation

`sp_session_position` is called at startup via the L1 FFI binding
(bindgen-generated from `include/sp/sp_l1.h`). The daemon log line
`L1 FFI OK — session_position=0` is printed before the listener opens.
`session_pos` is also returned in the `/v1/metrics` JSON so every
curl invocation independently confirms the FFI is live.

Session test suite (shannon-prime-system math-core): **119 checks, 0 fails**
(T_SESSION_BRIDGE, T_SESSION_PREFILL_PARITY, T_SESSION_GUARDS,
T_SESSION_DECODE_TRAJECTORY, T_SESSION_CLONE_REWIND, T_SESSION_CANCEL all
PASS), verifying that `sp_session_create` + `sp_session_position` are sound
before wiring the FFI into the daemon.

Fixture used: `shannon-prime-system/fx_q4.spm` + `fx_q4.spt`
(the math-core PARITY fixture, Qwen3 Q4, 88640 bytes).

## E_L3_1 gate results (Windows MSVC host)

| Measurement | Result | Gate |
|---|---|---|
| Model load → listen (cold start) | **~2 ms** | ≤ 200 ms ✓ |
| First TCP call (new connection) | **71 ms** | ≤ 200 ms ✓ |
| Warm call p50 (steady state) | **< 1 ms** | ≤ 50 ms ✓ |
| JSON well-formed | ✓ | ✓ |

Raw warm call measurements: 3.4ms / 0.88ms / 0.62ms / 0.73ms / 0.62ms.

## Deliverables

**A. Build target**
- Cargo crate; binary name `sp-daemon`.
- `build.rs` runs bindgen on `include/sp/sp_l1.h` (transitively includes
  `sp_model.h` and `sp_status.h`).
- Links all 16 math-core static libs via `SP_SYSTEM_BUILD_DIR` env var.
- Default path: `../../build-cpu/lib/shannon-prime-system` (engine MinGW/MSVC).
- Standalone math-core (Linux/GCC): set `SP_SYSTEM_BUILD_DIR` to
  `shannon-prime-system/build/`.
- aarch64-android: build.rs emits `sp_no_link` cfg flag and returns early
  (type-check only; device link is Phase 2-L3.FG scope).

**B. localhost:8080 binding**
- `SocketAddr::from(([127, 0, 0, 1], 8080))` — loopback only.
- `0.0.0.0` is never used; documented in `daemon.rs` (single-user
  developer-device assumption per `PPT-LAT-Roadmap §14.3.1`).

**C. GET /v1/metrics**
```json
{
  "tokens_per_sec": 0.0,
  "ram_svm_bytes":  0,
  "peers":          0,
  "phase":          "lat-phase-2-l1-closed",
  "session_pos":    0
}
```
`session_pos` is the live `sp_session_position` read — FFI proof.
Placeholder values for throughput/RAM/peers land in VERBS.

**D. Daemon lifecycle**
- `sp-daemon start --model <path> --tokenizer <path>`: spawns inner process
  with `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` on Windows /
  `setsid()` on Unix, writes `$TEMP/sp-daemon.pid`, parent exits.
- `sp-daemon stop`: reads PID file, `taskkill /PID n /F` (Windows) /
  `kill(SIGTERM)` (Unix), removes PID file. Graceful session drain is
  Phase 2-L3.FG scope.
- `sp-daemon reload`: no-op for v0.

## cancel_flag correction

Task brief specified `volatile _Atomic bool*` → `Arc<AtomicBool>`. Actual
`sp_l1.h:128` declares `volatile int *cancel_flag`. Rust side uses
`Arc<AtomicI32>`; raw pointer cast to `*mut c_int` is sound because
`AtomicI32` has the same layout as `c_int` and L1 only reads the flag
with relaxed ordering (documented in the header).

## Not fired

`lat-phase-2-l3-closed` — fires after VERBS / SSE / FG / AUTH close.
