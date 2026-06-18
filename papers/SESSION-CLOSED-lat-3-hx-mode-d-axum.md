---
type: session-handoff
title: SESSION CLOSED — lat-3-hx-mode-d-axum (Sprint C)
description: "Date: 2026-05-29"
tags: [session-handoff]
timestamp: 2026-05-29T02:30:25Z
resource: shannon-prime-lattice/papers/SESSION-CLOSED-lat-3-hx-mode-d-axum.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# SESSION CLOSED — lat-3-hx-mode-d-axum (Sprint C)
**Date:** 2026-05-29  
**Plan:** `papers/SESSION-PLAN-lat-3-hx-mode-d-axum.md` (`980f6b9`)  
**Engine commit:** `9fd039a`

**Tags issued at engine `9fd039a`:**
- `lat-phase-3-hx-mode-d-axum-route-host-build` ✓
- `lat-phase-3-hx-mode-d-axum-end-to-end` ✓
- `lat-phase-3-hx-mode-d-axum-concurrent` ✓
- **Umbrella: `lat-phase-3-hx-mode-d-axum-closed` ✓**

---

## 1. Status

**CLOSED.** All three sub-tags + umbrella issued. `POST /v1/dsp/echo` round-trip works end-to-end through axum → FastRpcSession + DmaBuffer → cDSP echo skel → response, on Knack's S22U via `dsp_axum_server`. Same route handler shipped in sp-daemon's routes.rs (host build returns 501 cleanly, ready for android when sp-daemon's bindgen chain is unblocked).

---

## 2. Deliverables (`9fd039a`)

### sp-daemon side

| File | Change |
|---|---|
| `src/state.rs` | `AppState.dsp_session: Option<Mutex<FastRpcSession>>` (cfg android) |
| `src/daemon.rs::run_inner` | Try `FastRpcSession::new` at startup on android; graceful degrade to None |
| `src/routes.rs::v1_dsp_echo` | Handler with 8 MB MAX_PAYLOAD; android does FastRPC, host returns 501 |
| `src/server.rs::build_router` | Registers `POST /v1/dsp/echo` |
| `src/main.rs` | `#[cfg(target_os="android")] mod dsp_rpc` |

### sp_dsp_smoke side — `[[bin]] dsp_axum_server` (NEW)

`tools/sp_dsp_smoke/src/axum_server.rs` — minimal axum server, 127.0.0.1:8081, same handler logic, standalone (no L1 ABI dependency). Cross-compiles to aarch64-android in 20.6 sec; 1.99 MB ELF.

Deps added (cfg target_os = "android"): `axum 0.7`, `tokio 1` (rt-multi-thread / macros / net / signal / sync), `bytes 1`.

---

## 3. Test Results

### Host side (`sp-daemon` on Windows x86_64)

| Test | Result |
|---|---|
| Host build clean | ✓ (5 pre-existing warnings, no new errors) |
| `T_AXUM_ROUTE_HOST_501` — POST /v1/dsp/echo returns 501 on host | **PASS** |

### Device side (S22U R5CT22445JA, `dsp_axum_server` + `adb forward tcp:8081 tcp:8081`)

| Test | Body size | Result |
|---|---|---|
| `T_AXUM_ECHO_16B`  | 16 B | **PASS** (bitwise) |
| `T_AXUM_ECHO_4KB`  | 4 KB | **PASS** (bitwise) |
| `T_AXUM_ECHO_1MB`  | 1 MB | **PASS** (bitwise) |
| `T_AXUM_413`       | 16 MB | **PASS** (413 Payload Too Large, no DSP touched) |
| `T_AXUM_CONCURRENT_4` | 4 × 64 KB parallel | **PASS** (all bitwise; Mutex serializes FFI cleanly) |
| Clean shutdown on SIGINT | — | ✓ no zombie processes |

---

## 4. Architecture Notes

### Concurrency model

`FastRpcSession::invoke` against a single handle from multiple threads is not guaranteed thread-safe by the FastRPC framework. Wrapped session in `Mutex<FastRpcSession>` so concurrent HTTP requests serialize at the FFI boundary. Verified by `T_AXUM_CONCURRENT_4` — 4 parallel curls all return bitwise-correct 64 KB bodies.

Per-request:
1. `spawn_blocking` so the tokio runtime isn't held during the FastRPC syscall
2. Lock the session mutex (blocks on contention)
3. `alloc_dma` two buffers (exact-size discipline)
4. Copy body into in_buf
5. `invoke` sp_echo_ping
6. Clone out_buf to Vec for response
7. Drop DmaBuffers + unlock

### Sprint B regression preserved

The `dsp_axum_server` binary uses the **same** `dsp_rpc.rs` Sprint B introduced. All Sprint A + B gates still pass when `test_dsp_rpc` is run (verified previously at `f73db35`).

### sp-daemon-on-android note

`sp-daemon` itself still doesn't cross-compile to aarch64-android because the `build.rs::bindgen` step requires the Android NDK sysroot to resolve `<stdint.h>` for `sp_l1.h`. That's a Phase 2-L3.FG / out-of-scope blocker. Sprint C's route handler in `routes.rs` is host-build-verified (returns 501); the moment sp-daemon's android target is unblocked, the handler activates end-to-end with no further code changes (the `#[cfg(target_os = "android")]` branches are already in place).

---

## 5. Findings

### F1 — `bytes` crate vs `axum::body::Bytes`

axum re-exports `bytes::Bytes` as `axum::body::Bytes`. The `dsp_axum_server` binary uses the re-export to avoid an explicit `bytes = "1"` dep on the smoke crate's direct surface — but the dep IS in Cargo.toml because tokio/axum both pull it.

### F2 — Concurrent requests with single FastRpcSession is fine

T_AXUM_CONCURRENT_4 confirmed that 4 parallel requests serialize cleanly through the Mutex. No invoke crashes, no handle corruption, all 4 responses bitwise correct. For higher throughput (Phase 4-MTP / Mode D production), a pool of sessions would let independent worker threads dispatch in parallel — Sprint D or later scope.

### F3 — Test framework: PowerShell vs curl

The dsp_axum_server is HTTP, so testing from PowerShell with `Invoke-WebRequest` worked but had quirks around binary body handling. `curl --data-binary @file.bin` is cleaner for shell-script-based CI; documented in plan §3 as the canonical verification command.

---

## 6. Open Work

| Item | Phase | Trigger |
|---|---|---|
| Unblock sp-daemon aarch64-android cross-compile (bindgen needs NDK sysroot) | Phase 2-L3.FG | When sp-daemon is deployed on-device for production |
| Sprint D / Mode D: Halide AOT FFN fusion via FastRpcSession + DmaBuffer | post-Sprint C | When KSTE upper-tier integration (§16.5) lands |
| Replace `Mutex<FastRpcSession>` with a small `Pool<FastRpcSession>` for parallel dispatch | post-Sprint D | When per-request throughput becomes the bottleneck |
| Consolidate `dsp_rpc.rs` (sp_daemon copy vs sp_dsp_smoke copy) into shared workspace member | post-Sprint A umbrella | Same as Sprint A/B open item |
