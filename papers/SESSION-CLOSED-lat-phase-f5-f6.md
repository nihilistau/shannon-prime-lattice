---
type: session-handoff
title: SESSION CLOSED — lat-phase-f5-f6
description: "Date: 2026-05-29"
tags: [session-handoff]
timestamp: 2026-05-28T16:43:38Z
resource: shannon-prime-lattice/papers/SESSION-CLOSED-lat-phase-f5-f6.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# SESSION CLOSED — lat-phase-f5-f6
**Date:** 2026-05-29  
**Tag:** `lat-phase-f5-f6-closed`  
**Engine commits:** `542bf1d` (F5.1+F5.2), `8f66e3b` (F5.3), `b1ee71e` (F6)  
**Lattice commits:** `8643cbc` (F6 plan)

---

## 1. Status

**CLOSED** — all 6 smoke gates PASS post-consolidation; G_SMOKE_2 upgraded from soft to hard (keep-alive confirmed active=1 at later check time).

---

## 2. F5 Deliverables

### F5.1 — QUIC keep_alive_interval + max_idle_timeout (`542bf1d`)

`quic_shard.rs` — both `make_server_config` and `make_client_config`:
- `TransportConfig::keep_alive_interval(Some(Duration::from_secs(30)))`
- `TransportConfig::max_idle_timeout(Some(VarInt::from_u32(120_000).into()))` — 120,000 ms = 120s

Fixes lat-smoke-2node Finding #2 (~3 min idle disconnect). Confirmed: G_SMOKE_2 now shows `active=1` at the post-G_SMOKE_3 check time (~7 min after dial), up from `active=0` in the prior smoke.

### F5.2 — Explicit connection close-handler (`542bf1d`, same commit)

`quic_shard.rs::run_garner_loop` — after `peer_map.insert`, spawns a second task:
```rust
tokio::spawn(async move {
    conn_for_close.closed().await;
    peer_map_cleanup.remove(&remote_addr);
    tracing::info!("SP_INFO: QUIC peer disconnected: {remote_addr}");
});
```

The existing `peer_map_c.remove` at the end of the `accept_uni` loop is intentionally kept; DashMap::remove is idempotent. Both paths fire on connection close — the explicit watcher fires immediately, the accept_uni loop fires when the next stream open fails.

### F5.3 — `--peers` / SP_PEERS bootstrap-list dial (`8f66e3b`)

`--peers <addr,...>` (comma-separated, `SP_PEERS` env var) added to `Cmd::Start`. The existing `--peer` (singular, F4) is kept as back-compat alias. Both are dialed via `spawn_peer_dial()` — the F4 inline block refactored into a shared helper in `daemon.rs`. On parse/dial failure: log warn + skip, no crash.

---

## 3. F6 Deliverables

### F6 Plan (`8643cbc`, lattice repo)

`papers/SESSION-PLAN-lat-phase-f6.md` — route inventory, migration table, decision rationale, gate changes. Committed before any code.

### F6 Execute (`b1ee71e`, engine repo)

**Migrated from `console.rs` → `routes.rs`:**
- `v1_node_telemetry` (WS), `telemetry_loop`, `NodeTelemetry` struct
- `v1_mesh_peers`, `PeerInfo` struct
- `v1_pouw_ledger`, `format_kste_receipt`, `decode_le_u64_hex`
- `v1_chat_stream_stub`

**`server.rs::build_router`:** 4 new routes added; `/v1/peers` stub removed; `ServeDir("frontend_mockups")` + `CorsLayer::permissive()` added.

**Removed:** `--console-port` / `SP_CONSOLE_PORT` from `Cmd::Start`, `Cli`, `cmd_start`, `run_inner`. The second `axum::serve` in `daemon.rs` for the operator console removed. `console.rs` deleted.

Diff stat: 5 files, **136 insertions, 435 deletions**.

---

## 4. Route Migration Table (Actual)

| Source | Target | Action |
|---|---|---|
| `console.rs::node_telemetry` | `routes.rs::v1_node_telemetry` | Moved; renamed to pub |
| `console.rs::telemetry_loop` | `routes.rs::telemetry_loop` | Moved; private |
| `console.rs::NodeTelemetry` | `routes.rs::NodeTelemetry` | Moved |
| `console.rs::mesh_peers` | `routes.rs::v1_mesh_peers` | Moved; renamed to pub |
| `console.rs::PeerInfo` | `routes.rs::PeerInfo` | Moved |
| `console.rs::pouw_ledger` | `routes.rs::v1_pouw_ledger` | Moved; renamed to pub |
| `console.rs::format_kste_receipt` | `routes.rs` | Moved; private |
| `console.rs::decode_le_u64_hex` | `routes.rs` | Moved; private |
| `console.rs::chat_stream_stub` | `routes.rs::v1_chat_stream_stub` | Moved; renamed to pub |
| `console.rs::chat_handler` | **DELETED** | Phase D spec decode → Phase D2 re-wire (see §6) |
| `console.rs::emit_token` | **DELETED** | Only used by chat_handler |
| `console.rs::mk_sse` | **DELETED** | Only used by chat_handler |
| `routes.rs::v1_peers` | **DELETED** | Stub replaced by real `v1_mesh_peers` |

No deviations from the plan.

---

## 5. Smoke Re-Run vs Original lat-smoke-2node

| Gate | lat-smoke-2node | lat-phase-f5-f6 (this run) | Notes |
|---|---|---|---|
| G_SMOKE_F4 | PASS — 8080+3000 | **PASS** — 8080 only, no console-port | F6 confirmed |
| G_SMOKE_1 | PASS — active=1, 127.0.0.1:50714 | **PASS** — active=1, 127.0.0.1:49889 | `--peers` flag (F5.3) used |
| G_SMOKE_2 | PASS (soft, active=0 at later check) | **PASS (hard)** — active=1 at later check | F5.1 keep-alive confirmed working |
| G_SMOKE_3 | PASS — 11 receipts/30s | **PASS** — 9 receipts/30s | Timing variance; floor=1 |
| G_SMOKE_4 | PASS strict — 35 tok, final `.` | **PASS strict** — 35 tok, final `.` | See §6 Finding A |
| G_SMOKE_TEARDOWN | PASS | **PASS** | Clean |

---

## 6. Findings

### Finding A — Chat handler divergence (silent before F6, now explicit)

Before F6: console.rs::chat_handler (port 3000) always applied the chat template via `tokenizer.apply_template`. routes.rs::v1_chat (port 8080) with `prompt:` input bypasses the chat template and encodes raw text. These were silently different on different ports.

After F6: both routes are on port 8080. Using `{"prompt": "..."}` now bypasses the chat template (hits `max_tokens=256` limit, generates 256 tokens of repetitive output). Using `{"messages": [{"role":"user","content":"..."}]}` triggers the chat template (generates the same 35-token response as the pre-F6 console path). The smoke was updated to use `messages:` format — this is the correct API surface for chat-template-aware requests.

**Implication for clients:** Any client previously posting `{"prompt": "..."}` to port 3000 will get different output when redirected to port 8080. Correct usage is `messages:` format. The `prompt:` raw-text form remains for bare-metal prompt injection.

### Finding B — Phase D spec decode explicitly deferred

`console.rs::chat_handler` contained Phase D speculative decode (`spec_step` + draft session). This handler is deleted in F6 and NOT migrated. `spec.rs::spec_step`, `spec.rs::argmax`, and `state::AppState::draft_session` are now dead code. G_SMOKE_4 passes because the smoke never loaded a draft model (AR-only path in both pre- and post-F6).

Phase D1 closure said "spec decode wired" — that was wired on the console port only. **Phase D2 re-wire pending: splice spec decode into `routes.rs::v1_chat` as a draft-session-conditional branch.** This is not a silent regression — it is intentional and named.

### Finding C — `spec.rs` dead code warnings

After F6, `cargo build --release` emits 3 new warnings:
```
warning: struct `SpecResult` is never constructed
warning: function `spec_step` is never used
warning: function `argmax` is never used
```

These are expected: spec.rs was consumed by chat_handler only. Phase D2 will bring them live again.

### Finding D — F5.1 keep-alive confirmed effective

G_SMOKE_2 at lat-smoke-2node showed `active=0` after ~7 minutes. This run showed `active=1` at the equivalent point. The 30s keep-alive interval successfully prevents idle timeout. The 120s `max_idle_timeout` provides a network-failure backstop.

---

## 7. What's Still Open

| Item | Phase | Trigger |
|---|---|---|
| Phase D2: splice spec decode into `routes.rs::v1_chat` (draft-session-conditional; `spec_step` path when `draft_session.is_some()`) | D2 | Explicit Phase D regression from F6 |
| Phase F7: QUIC connection retry with backoff (currently one-shot dial; if peer is down at startup, no retry) | F7 | Production hardening |
| Phase F7: mDNS / DHT gossip auto-discovery (removes need for `--peers` bootstrap list) | F7 | Multi-node topology |
| Phase F7: Per-node PID namespacing (`sp-daemon-<port>.pid`) to support `sp-daemon stop --port N` | F7 | Multi-node ops |
| Phase 14.3.AUTH: Replace `SkipServerVerification` + rcgen ephemeral cert with ed25519 dominance identity | AUTH | Production TLS |
| Clean up `spec.rs` dead_code warnings — either `#[allow(dead_code)]` until D2 or delete and restore from git at D2 | D2 / maintenance | Build hygiene |
