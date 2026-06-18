---
type: session-handoff
title: SESSION CLOSED — Phase 2-L3.VERBS
description: "Tag: lat-phase-2-l3-verbs-closed"
tags: [session-handoff, l3]
timestamp: 2026-05-26T06:28:46Z
resource: shannon-prime-lattice/papers/SESSION-CLOSED-lat-2-L3-VERBS.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# SESSION CLOSED — Phase 2-L3.VERBS

**Tag:** `lat-phase-2-l3-verbs-closed`
**Date:** 2026-05-26
**Host:** Windows 11 Pro, x86_64, MSVC toolchain (Rust stable-x86_64-pc-windows-msvc 1.92.0)

## Scope

Phase 2-L3.VERBS — wire all 6 HTTP/SSE routes to real L1 calls in the
`sp-daemon` crate (`shannon-prime-system-engine/tools/sp_daemon/`).
The CORE scaffold (Phase 2-L3.CORE, engine commit `6a35f39`) provided the
single `/v1/metrics` stub; VERBS wires the rest.

## Routes implemented

| Route | Method | Behaviour |
|---|---|---|
| `/v1/chat` | POST | `sp_session_clone` → `sp_prefill_chunk` → greedy `sp_decode_step` decode loop → SSE `data: {"delta":"<N>","chat_id":K}` stream + `data: [DONE]` |
| `/v1/abort/{id}` | POST | Flip per-chat `cancel_flag` (Arc<AtomicI32>); L1 observes at next layer boundary → SP_ECANCEL → decode loop exits. Returns 204/404. |
| `/v1/metrics` | GET | Live `session_pos` (base session stays at 0); real `tokens_per_sec` (lifetime average); `phase: "lat-phase-2-l3-verbs-closed"` |
| `/v1/receipts` | GET | Stub `{"receipts":[],"cursor":null}` |
| `/v1/peers` | GET | Stub `{"peers":[]}` |
| `/v1/events` | GET | Infinite SSE keep-alive (15s ping comment via axum KeepAlive) |

## Request shape (VERBS debug path)

```json
{"prompt_tokens": [1, 2, 3], "max_tokens": 8}
```

Accepts raw token IDs instead of text. BPE text→tokens deferred to Phase
2-L3.TOK: the `fx_q4` fixture has `vocab=48` (synthetic), so a full BPE
encoder over it is meaningless. The gate criteria are about streaming wiring,
not tokenization.

## Session cloning model

The base session (`AppState.session`) stays at position 0 forever. Each
`/v1/chat` request:
1. Acquires the base-session Mutex **only during `sp_session_clone`** (sub-ms)
2. Registers the child session in the `Sessions` table with a fresh
   `Arc<AtomicI32>` cancel flag
3. Spawns a `tokio::task::spawn_blocking` decode loop (off the tokio worker
   threads — `sp_decode_step` is sync/CPU-bound)
4. Returns the SSE stream immediately (before decode starts)

`sp_session_clone` is the speculative-decoding fork primitive from day one;
each concurrent `/v1/chat` is independent.

## cancel_flag ownership

```
Arc<AtomicI32>  ←── cancel_child (in spawn_blocking closure)
      │
      └──────────── Sessions table entry (keyed by chat_id)
                          │
                          └──── sessions.abort(id) → flag.store(1)
                                     ↑
                               /v1/abort/{id} handler
```

Raw pointer (`*mut c_int`) passed to `sp_session_clone` points to the same
`AtomicI32` allocation. L1 reads it with relaxed ordering at each layer
boundary; nonzero → `SP_ECANCEL` → `decode_step` returns `Err` → loop breaks.

## Gate results (fx_q4 fixture, Windows MSVC x86_64)

| Gate | Result | Note |
|---|---|---|
| E_L3_VERBS_1 — chat streams ≥1 delta + [DONE] | ✓ | 4 deltas + `[DONE]` observed with `max_tokens=4` |
| E_L3_VERBS_2 — abort terminates stream <100ms | Mechanism ✓ | Fixture limitation: fx_q4 fills its 255-token context in ~15ms (context full → SP_ECONTEXT_FULL → decode exits), shorter than abort HTTP round-trip (~65ms). Cancel-flag wiring is correct; timing gate deferred to real-model verification (Phase 2-L3.SSE). |
| E_L3_VERBS_3 — two parallel chats, no corruption | ✓ | Distinct `chat_id`s (3, 4); both received independent SSE streams and `[DONE]` |

## FFI probe binary

`src/bin/probe.rs` — throwaway binary proving the three new FFI calls are
sound before SSE was wired around them:

```
arch: vocab=48 n_layers=2 hidden=32
base session created
clone OK
prefill(3) OK — logits[0..3] = [1.1911265, -1.5769597, 0.929561]
decode(1) OK — position=4, logits[0..3] = [-1.5281981, 1.1459001, 1.0068274]
PROBE PASS
```

## New session.rs methods

- `SpModel::arch_info()` → `ffi::sp_arch_info` (vocab_size for logits buffer)
- `SpSession::clone_session(cancel: Arc<AtomicI32>)` → `SpSession`
- `SpSession::prefill_chunk(tokens: &[i32], logits: &mut [f32])`
- `SpSession::decode_step(token: i32, logits: &mut [f32])`

## Engine commit

`77d0076` — `[lat-2-l3-verbs] sp-daemon: Phase 2-L3.VERBS — wire all 6 routes to L1`

## Not fired

`lat-phase-2-l3-closed` — fires after SSE / FG / AUTH all close.
