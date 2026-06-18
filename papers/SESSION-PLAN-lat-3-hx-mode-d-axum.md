---
type: session-handoff
title: SESSION PLAN — lat-3-hx-mode-d-axum (Sprint C)
description: "Date: 2026-05-29"
tags: [session-handoff]
timestamp: 2026-05-29T02:18:41Z
resource: shannon-prime-lattice/papers/SESSION-PLAN-lat-3-hx-mode-d-axum.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# SESSION PLAN — lat-3-hx-mode-d-axum (Sprint C)
**Date:** 2026-05-29  
**Goal:** Bind `FastRpcSession` + `DmaBuffer` into an HTTP endpoint. Verify the full chain: HTTP request → axum handler → FastRPC → cDSP → response.

---

## 1. Scope decision (Stage 0)

Sprint C as originally framed says "bind FastRpcSession into daemon's HTTP path." The actual sp-daemon binary CANNOT currently cross-compile to aarch64-android because its `build.rs` runs bindgen on `sp_l1.h` which needs an Android NDK sysroot for `<stdint.h>` (Phase 2-L3.FG scope; documented in `SESSION-CLOSED-lat-3-hx-mode-d-rpc.md` F3).

So Sprint C ships TWO things:

1. **Route handler in sp-daemon's `routes.rs`** — compiles on host x86 with the dsp_rpc paths gated by `#[cfg(target_os = "android")]`. On host, the route returns `501 Not Implemented`. The code is ready to activate end-to-end the moment sp-daemon's bindgen-on-android is fixed (out of scope for Sprint C).

2. **End-to-end on-device verification via a minimal HTTP server** in `sp_dsp_smoke` as a new `[[bin]] dsp_axum_server` — listens on 127.0.0.1:8081, exposes the same `POST /v1/dsp/echo` handler, uses dsp_rpc directly. Cross-compiles cleanly to aarch64-android (no L1 ABI dep). Verified by `curl` from the device shell.

This gives both: the production wiring in the right place, AND on-device proof that the chain works.

---

## 2. Endpoint specification

```
POST /v1/dsp/echo
Content-Type: application/octet-stream
Body:           raw bytes (up to 8 MB per request)

Response 200 OK:
Content-Type: application/octet-stream
Body:           the same bytes echoed by the cDSP skel via sp_echo_ping

Response 501 Not Implemented:
                When running on non-Android host (route registered but DSP
                not reachable).

Response 500 Internal Server Error:
Body:           JSON {"error": "<SpErr variant>"}
                On FastRpcSession failure (alloc_dma, invoke, etc.)

Response 413 Payload Too Large:
                Body exceeds MAX_PAYLOAD (default 8 MB).
```

---

## 3. Architecture

### sp-daemon side (host build + future android build)

- `tools/sp_daemon/src/state.rs`: `AppState` gains `Option<Arc<Mutex<dsp_rpc::FastRpcSession>>>` field, only populated on android targets.
- `tools/sp_daemon/src/daemon.rs::run_inner`: tries `FastRpcSession::new(...)` at startup (android only); logs warning + sets None on failure (graceful degrade).
- `tools/sp_daemon/src/routes.rs`: new handler `v1_dsp_echo(State<AppState>, Bytes) -> Response`. On android with valid session: alloc_dma + ping + return. Otherwise: 501.
- `tools/sp_daemon/src/server.rs::build_router`: register `POST /v1/dsp/echo`.

### sp_dsp_smoke side (on-device verification)

- New `[[bin]] dsp_axum_server`: minimal axum server with the same handler.
- Uses the existing `dsp_rpc.rs` (mod-included).
- Listens on 127.0.0.1:8081 (no `0.0.0.0` per lattice §14.3.1 single-user-device rule).
- Brings up FastRpcSession at startup; serves until SIGTERM.

### Verification flow

```sh
# Build + push
cargo build --target aarch64-linux-android --release --bin dsp_axum_server
adb push target/.../dsp_axum_server /data/local/tmp/
adb shell chmod +x /data/local/tmp/dsp_axum_server

# Start in background
adb shell 'ADSP_LIBRARY_PATH="/data/local/tmp;" /data/local/tmp/dsp_axum_server &'

# From host: forward port + curl
adb forward tcp:8081 tcp:8081
curl -X POST --data-binary @random_16kb.bin -H "Content-Type: application/octet-stream" \
     http://127.0.0.1:8081/v1/dsp/echo \
     -o response.bin

# Verify
cmp random_16kb.bin response.bin && echo "OK"
```

---

## 4. Concurrency model

`FastRpcSession::invoke` against a single handle from multiple threads is NOT guaranteed thread-safe by the FastRPC framework. Wrap session in `Arc<Mutex<FastRpcSession>>` so concurrent HTTP requests serialize at the FFI boundary. Per-request:

1. Lock the session (blocks on contention)
2. Allocate two DmaBuffers (one per side)
3. Invoke ping
4. Copy out_buf to response
5. Drop DmaBuffers
6. Unlock

This is fine for Sprint C — verifies correctness. Throughput tuning (e.g., a pool of FastRpcSessions for parallel requests) is Sprint D / production.

---

## 5. Test plan

- **T_AXUM_ROUTE_HOST_501**: on x86 host build, `POST /v1/dsp/echo` returns 501. (sp-daemon side)
- **T_AXUM_ECHO_16B**: 16-byte body → 16-byte response, bitwise. (dsp_axum_server on device via adb forward + curl)
- **T_AXUM_ECHO_4KB**: 4 KB body round-trip.
- **T_AXUM_ECHO_1MB**: 1 MB body round-trip.
- **T_AXUM_413**: 16 MB body → 413 (payload too large).
- **T_AXUM_CONCURRENT_4**: 4 parallel curls hitting the endpoint simultaneously, all bitwise correct (verifies the Mutex serialization works).

---

## 6. Sub-tag taxonomy

- `lat-phase-3-hx-mode-d-axum-route-host-build` — sp-daemon host build with route handler compiles + T_AXUM_ROUTE_HOST_501 passes
- `lat-phase-3-hx-mode-d-axum-end-to-end` — dsp_axum_server T_AXUM_ECHO_* + T_AXUM_413 pass on device
- `lat-phase-3-hx-mode-d-axum-concurrent` — T_AXUM_CONCURRENT_4 passes
- Umbrella: `lat-phase-3-hx-mode-d-axum-closed`

---

## 7. Commit plan

| # | Content |
|---|---|
| 1 | Plan (this file) — lattice |
| 2 | sp-daemon: dsp_rpc.rs already there from Sprint A/B; add routes.rs::v1_dsp_echo + register in server.rs + AppState field — engine |
| 3 | sp_dsp_smoke: new `[[bin]] dsp_axum_server` with axum + the handler — engine |
| 4 | On-device run + iterate — engine (commit after green) |
| 5 | Closure + tags — lattice |

---

## 8. Out of scope

- Sprint D Halide AOT integration
- TLS / auth on the endpoint (single-user dev device per §14.3.1)
- LAN exposure (loopback only)
- Performance tuning beyond Sprint B's findings
