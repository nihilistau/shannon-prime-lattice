# SESSION PLAN — lat-phase-f6: Dual-Server Consolidation

**Created:** 2026-05-29  
**Scope:** Merge the operator-console HTTP server (port 3000) into the single main API HTTP server (port 8080). One Router, one axum::serve, one port.

---

## 1. Route Inventory

### Main API Server (port 8080, `server.rs::build_router`)

| Route | Handler | File:Line | Role |
|---|---|---|---|
| `GET /v1/metrics` | `v1_metrics` | `routes.rs:44` | Real — TPS, session pos |
| `POST /v1/chat` | `v1_chat` | `routes.rs:86` | Real — messages/prompt/max_tokens/stop, JSON-delta SSE |
| `POST /v1/abort/:id` | `v1_abort` | `routes.rs:286` | Real — cancel by chat_id |
| `GET /v1/receipts` | `v1_receipts` | `routes.rs:299` | Real — PoUW store snapshot |
| `GET /v1/peers` | `v1_peers` | `routes.rs:312` | **STUB** — always returns `{"peers":[]}` |
| `GET /v1/events` | `v1_events` | `routes.rs:321` | Real — broadcast SSE (chat + mint) |

### Operator Console Server (port 3000, `console.rs::start_operator_console`)

| Route | Handler | File:Line | Role |
|---|---|---|---|
| `POST /v1/chat` | `chat_handler` | `console.rs:86` | Real — spec decode + AR fallback; `prompt: String` only |
| `GET /v1/chat/stream` | `chat_stream_stub` | `console.rs:376` | Stub — returns JSON placeholder |
| `GET /v1/node/telemetry` | `node_telemetry` | `console.rs:45` | Real — WS; `dht_peers_active` from `peer_map` |
| `GET /v1/mesh/peers` | `mesh_peers` | `console.rs:301` | Real — JSON from `peer_map` |
| `GET /v1/pouw/ledger` | `pouw_ledger` | `console.rs:334` | Real — SSE from `events_tx` |
| Static fallback | `ServeDir("frontend_mockups")` | `console.rs:389` | Frontend mockups |

---

## 2. Consolidation Decision

**Survivor: `routes.rs` + `server.rs` on `--port` (default 8080)**

Rationale:
- `routes.rs::v1_chat` has the richer input surface (messages/prompt/prompt_tokens/max_tokens/stop) + chat_id metrics. These are load-bearing for any compliant client.
- `console.rs::chat_handler` has spec decode but is superseded for this sprint (Phase D2 re-wire pending).
- All four "real" console routes (`node_telemetry`, `mesh_peers`, `pouw_ledger`, static) are self-contained and can be lifted directly into `routes.rs` without changes to their bodies.

**Deletions:**
- `console.rs::v1_chat` (`chat_handler`) — Phase D spec decode intentionally deferred to Phase D2.
- `routes.rs::v1_peers` stub — replaced by real `/v1/mesh/peers` from console.
- `--console-port` / `SP_CONSOLE_PORT` flag — deleted from `Cmd::Start` and `Cli`.
- The second `axum::serve` in `daemon.rs` — deleted.
- `console.rs` file — deleted entirely after handler migration.

---

## 3. Handler Migration Table

| Source | Target | Action |
|---|---|---|
| `console.rs::node_telemetry` | `routes.rs::v1_node_telemetry` | Move; rename to pub; add route `/v1/node/telemetry` |
| `console.rs::telemetry_loop` | `routes.rs::telemetry_loop` | Move; stays private |
| `console.rs::NodeTelemetry` | `routes.rs::NodeTelemetry` | Move struct |
| `console.rs::mesh_peers` | `routes.rs::v1_mesh_peers` | Move; rename to pub; add route `/v1/mesh/peers` |
| `console.rs::PeerInfo` | `routes.rs::PeerInfo` | Move struct |
| `console.rs::pouw_ledger` | `routes.rs::v1_pouw_ledger` | Move; rename to pub; add route `/v1/pouw/ledger` |
| `console.rs::format_kste_receipt` | `routes.rs` | Move private helper |
| `console.rs::decode_le_u64_hex` | `routes.rs` | Move private helper |
| `console.rs::chat_stream_stub` | `routes.rs::v1_chat_stream_stub` | Move; rename to pub; add route `/v1/chat/stream` |
| `console.rs::chat_handler` | **DELETED** | Phase D spec decode → Phase D2 re-wire |
| `console.rs::emit_token` | **DELETED** | Only used by chat_handler |
| `console.rs::mk_sse` | **DELETED** | Only used by chat_handler |
| `console.rs::ChatRequest (console)` | **DELETED** | Superseded by `routes.rs::ChatRequest` |
| `console.rs::build_console_router` | **DELETED** | Replaced by `server.rs::build_router` |
| `console.rs::start_operator_console` | **DELETED** | Second axum::serve removed |
| `routes.rs::v1_peers` | **DELETED** | Stub replaced by real `v1_mesh_peers` |
| `server.rs` fallback | Add `ServeDir("frontend_mockups")` | Was on console only; move to consolidated router |
| `server.rs` CORS | Add `CorsLayer::permissive()` | Was on console only |

---

## 4. Target `server.rs::build_router`

```rust
pub fn build_router(state: Arc<AppState>) -> Router {
    Router::new()
        .route("/v1/metrics",        get(v1_metrics))
        .route("/v1/chat",           post(v1_chat))
        .route("/v1/chat/stream",    get(v1_chat_stream_stub))
        .route("/v1/abort/:id",      post(v1_abort))
        .route("/v1/receipts",       get(v1_receipts))
        .route("/v1/events",         get(v1_events))
        .route("/v1/node/telemetry", get(v1_node_telemetry))
        .route("/v1/mesh/peers",     get(v1_mesh_peers))
        .route("/v1/pouw/ledger",    get(v1_pouw_ledger))
        .fallback_service(ServeDir::new("frontend_mockups"))
        .layer(CorsLayer::permissive())
        .with_state(state)
}
```

---

## 5. Gate Changes for Smoke Re-Run

After consolidation:
- All gates hit `--port` (8080/8081) — no `--console-port`
- G_SMOKE_1: `http://127.0.0.1:8080/v1/mesh/peers` (now on main server)
- G_SMOKE_2: WS `ws://127.0.0.1:8080/v1/node/telemetry` (or soft via mesh/peers)
- G_SMOKE_3: `http://127.0.0.1:8080/v1/pouw/ledger`
- G_SMOKE_4: `http://127.0.0.1:8080/v1/chat` — format change: was raw text, now `{"delta":"...","chat_id":N}` JSON. Token sequence is identical (same argmax AR path). Smoke parsing updated to extract `delta` and count non-`[DONE]` events.

---

## 6. Open Questions Resolved Before Coding

- **spec decode**: Intentionally lost in this sprint. Named as Phase D2 follow-on in closure note. NOT silently dropped.
- **`--peer` back-compat**: Kept as-is (F4+F5 already handles this).
- **PID file collision**: Out of scope (Phase F5 finding #4 in smoke closure).
