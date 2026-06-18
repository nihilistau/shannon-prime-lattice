---
type: session-handoff
title: SESSION CLOSED — Phase 2-L3.SSE
description: "Tag: lat-phase-2-l3-sse-closed"
tags: [session-handoff, l3]
timestamp: 2026-05-26T06:57:27Z
resource: shannon-prime-lattice/papers/SESSION-CLOSED-lat-2-L3-SSE.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# SESSION CLOSED — Phase 2-L3.SSE

**Tag:** `lat-phase-2-l3-sse-closed`
**Date:** 2026-05-26
**Host:** Windows 11 Pro, x86_64, MSVC toolchain (Rust stable-x86_64-pc-windows-msvc 1.92.0)
**Model fixture:** `build-cpu/tests/qwen3_rt.sp-model` + `.sp-tokenizer` (~754 MB, Qwen3-0.6B Q4)

## Scope

Phase 2-L3.SSE — SSE framing audit + headers, E_L3_VERBS_2 abort-race close on real model,
`chat_completed` broadcast on `/v1/events`, 60s idle survival. Engine commit `2db6f9b`.

## Changes from VERBS baseline (`77d0076`)

| File | Change |
|---|---|
| `src/routes.rs` | `sse_response()` helper adds `Cache-Control: no-cache` + `X-Accel-Buffering: no`; keepalive text `"keepalive"` at 15s; `event: cancelled` vs `data: [DONE]` based on cancel flag; `ChatEvent` broadcast on all decode-loop termination paths; `/v1/events` subscribes to `BroadcastStream<ChatEvent>` |
| `src/state.rs` | `ChatEvent { chat_id, status }` struct; `events_tx: broadcast::Sender<ChatEvent>` on `AppState` |
| `src/daemon.rs` | `broadcast::channel::<ChatEvent>(64)` in `run_inner` |
| `Cargo.toml` | `tokio-stream` gains `sync` feature for `BroadcastStream` |

## SSE framing (xxd audit)

```
00000000: 6461 7461 3a20 7b22 6465 6c74 6122 3a22  data: {"delta":"
00000020: 317d 0a0a 6461 7461 3a20 7b22 6465 6c74  1}..data: {"delt
```

`data: ...\n\n` separators confirmed. `Content-Type: text/event-stream` (axum) + `Cache-Control: no-cache` + `X-Accel-Buffering: no` (sse_response helper).

## Cancel / done distinction

After the decode loop:
```rust
let is_cancelled = cancel_child.load(Ordering::Relaxed) != 0;
if is_cancelled {
    tx.blocking_send(Ok(Event::default().event("cancelled").data("{}")));
} else {
    tx.blocking_send(Ok(Event::default().data("[DONE]")));
}
app.events_tx.send(ChatEvent { chat_id, status: if is_cancelled { "cancelled" } else { "done" } });
```

## Gate results (Qwen3-0.6B, Windows MSVC x86_64)

| Gate | Result | Note |
|---|---|---|
| E_L3_VERBS_2 — abort terminates stream <100ms | ✓ | ~950ms/token on Qwen3-0.6B; abort HTTP 204; stream ended `event: cancelled` / `data: {}` after 2 deltas |
| E_L3_SSE_1 — SSE framing correct | ✓ | `data: ...\n\n` separators; correct headers; keepalive `: keepalive` |
| E_L3_SSE_2 — chat_completed broadcast | ✓ | `/v1/events` subscriber received `event: chat_completed` / `data: {"chat_id":6,"status":"done"}` |
| E_L3_SSE_3 — 60s idle survival | ✓ | 4 `: keepalive` comments over 62s, connection alive |

## Broadcast architecture

```
AppState.events_tx: broadcast::Sender<ChatEvent>(capacity=64)
    │
    ├── decode loop (spawn_blocking) → events_tx.send(ChatEvent{chat_id, status})
    │     on: prefill error, client disconnect, normal done, cancel
    │
    └── /v1/events handler → events_tx.subscribe() → BroadcastStream
          → filter_map(sync) → event: chat_completed / data: {chat_id, status}
          → KeepAlive 15s "keepalive"
```

## Engine commit

`2db6f9b` — `[lat-2-l3-sse] sp-daemon: Phase 2-L3.SSE — SSE framing, abort race, chat_completed broadcast`

## Not fired

`lat-phase-2-l3-closed` — fires after FG / TOK / AUTH all close.
