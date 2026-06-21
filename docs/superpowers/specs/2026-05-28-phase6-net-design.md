---
type: design
title: "Phase 6-NET: Multi-Node CRT Sharding over QUIC — Design Spec"
description: "Date: 2026-05-28"
tags: [design]
timestamp: 2026-05-27T16:30:34Z
resource: ./docs/superpowers/specs/2026-05-28-phase6-net-design.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---

# Phase 6-NET: Multi-Node CRT Sharding over QUIC — Design Spec

**Date:** 2026-05-28  
**Repository:** `shannon-prime-system-engine` (`tools/sp_daemon/`)  
**Status:** APPROVED — ready for implementation planning

---

## 1. Motivation

The CRT dual-prime fields Z_q1 and Z_q2 are mathematically independent. Each
prime's NTT residue array can be computed by a separate physical node and
streamed to a coordinator for Garner reconstruction — with no ordering
dependency between the two streams.

TCP serializes all data on a connection, creating Head-of-Line blocking: a
delayed q1 packet holds up q2 delivery at the OS level. QUIC streams on a
single connection are delivered independently. This topology uses QUIC to
match the mathematical independence of CRT fields to the network independence
of independent streams.

---

## 2. Scope and Anti-Scope

**In scope:**
- New Rust QUIC transport module in `tools/sp_daemon/`
- Wire protocol for residue streams
- Coordinator Garner assembly loop with FFI to existing `sp_ntt_crt`
- Integration tests (M_NET_1, M_NET_2, M_NET_3)
- Session state document `papers/SESSION-STATE-lat-6-NET.md`

**Out of scope:**
- Modifying math-core C code (`sp_ntt_crt` is consumed as-is)
- Production TLS identity (ephemeral self-signed certs in this phase; will
  eventually integrate Phase 5 ed25519 dominance identity)
- Multi-hop / n>2 shard topologies
- Softmax, temperature, probability — discrete argmax only (invariant)

---

## 3. File Layout

```
tools/sp_daemon/
├── Cargo.toml                      modified — add 4 new deps
├── src/
│   ├── lib.rs                      NEW — pub mod network; pub mod ntt_ffi;
│   ├── main.rs                     unchanged
│   ├── network/
│   │   ├── mod.rs                  NEW — pub mod quic_shard;
│   │   └── quic_shard.rs           NEW — QUIC transport, coordinator loop
│   └── ntt_ffi.rs                  NEW — manual FFI for sp_ntt_crt
└── tests/
    └── test_quic_shard.rs          NEW — M_NET_1 / M_NET_2 / M_NET_3
```

`[lib]` and `[[bin]]` coexist in the same Cargo package without conflict.
Integration tests in `tests/` import from the `[lib]` target.

---

## 4. Cargo.toml Additions

```toml
quinn   = { version = "0.11", features = ["rustls"] }
rustls  = { version = "0.23", features = ["ring"] }
rcgen   = { version = "0.13", features = ["ring"] }
dashmap = "6"
```

`sp_ntt_crt` is already in `build.rs` MODULES — no build script changes.

---

## 5. Wire Protocol

### 5.1 Stream Granularity

One QUIC **unidirectional stream** per residue block. The worker calls
`connection.open_uni()`, writes the 64-byte header + N×4-byte payload,
then finishes (closes) the stream. The coordinator calls
`connection.accept_uni()` in a loop.

Each block occupies its own QUIC stream ID. QUIC delivers stream IDs
independently at the protocol layer — this is the HoL bypass.

### 5.2 Per-Stream Byte Layout

```
Offset   Size    Field
──────   ──────  ──────────────────────────────────────────────────────
  0       8      seq_id         u64 LE — global sequence counter
  8       4      token_pos      u32 LE — token position in context
 12       4      layer_id       u32 LE — transformer layer index
 16       1      prime_selector u8     — 0 = q1 (1073738753)
                                          1 = q2 (1073732609)
 17      47      _pad           [0u8; 47]
 64      N×4     residues       N × u32 LE, N ∈ {128, 256, 512}

Total stream bytes: 64 + N×4
```

No explicit length field. The stream close boundary is authoritative:
`n_coeffs = (stream_total − 64) / 4`.

### 5.3 Rust Struct

```rust
#[repr(C)]
pub struct ShardBlockHeader {
    pub seq_id:         u64,
    pub token_pos:      u32,
    pub layer_id:       u32,
    pub prime_selector: u8,
    pub _pad:           [u8; 47],
}
const _: () = assert!(std::mem::size_of::<ShardBlockHeader>() == 64);
```

Serialization: manual LE byte slices per field. No serde, no protobuf.

### 5.4 ResidueBlock

```rust
pub struct ResidueBlock {
    pub header:   ShardBlockHeader,
    pub residues: Vec<u32>,
}
```

---

## 6. QUIC Endpoint API

### 6.1 TLS Bootstrap

At startup, generate an ephemeral self-signed certificate:

```
rcgen::generate_simple_self_signed(["localhost"])
  → CertificateDer + private key

Coordinator: rustls::ServerConfig → quinn::ServerConfig
Worker:      rustls::ClientConfig + SkipServerVerification verifier
```

`SkipServerVerification` implements
`rustls::client::danger::ServerCertVerifier` — accepts any server certificate.
This is the correct rustls 0.23 extension point for dev-mode TLS. A comment
marks it as the integration point for Phase 5 ed25519 identity in a later
phase.

### 6.2 Public Surface in `quic_shard.rs`

```rust
// Coordinator — binds, accepts connections, receives residue blocks
pub struct SpQuicCoordinator { endpoint: quinn::Endpoint }

impl SpQuicCoordinator {
    pub async fn bind(addr: SocketAddr) -> Result<Self>;
    pub async fn accept_connection(&self) -> Result<quinn::Connection>;
}

// Worker — dials coordinator, opens a fresh uni stream per block
pub struct SpQuicWorker { connection: quinn::Connection }

impl SpQuicWorker {
    pub async fn connect(local_addr: SocketAddr,
                         server_addr: SocketAddr) -> Result<Self>;
    pub async fn send_block(&self, block: &ResidueBlock) -> Result<()>;
}

// Receive one block from a uni stream (used by coordinator + tests)
pub async fn recv_block(stream: quinn::RecvStream) -> Result<ResidueBlock>;
```

---

## 7. Garner Assembly Loop & FFI

### 7.1 `ntt_ffi.rs`

Manual FFI following `sieve_ffi.rs` pattern. `sp_ntt_crt` already linked
via `build.rs` MODULES — no build script change needed.

```rust
pub enum NttCtx {}

extern "C" {
    pub fn ntt_init(n: u32) -> *mut NttCtx;
    pub fn ntt_free(ctx: *mut NttCtx);
    pub fn ntt_crt_recombine(
        ctx: *const NttCtx,
        x1:  *const u32,
        x2:  *const u32,
        out: *mut i64,
    );
    pub fn ntt_pointwise_mul(
        ctx:  *const NttCtx,
        a1: *const u32, a2: *const u32,
        b1: *const u32, b2: *const u32,
        out1: *mut u32, out2: *mut u32,
    );
}
```

### 7.2 `NttCtxHandle` — RAII wrapper

`ntt_ctx` is read-only after `ntt_init` (per `ntt_crt.h`); safe to share
across threads. Wrapped to implement `Send + Sync` and call `ntt_free` on drop:

```rust
struct NttCtxHandle(*mut NttCtx);
unsafe impl Send for NttCtxHandle {}
unsafe impl Sync for NttCtxHandle {}
impl Drop for NttCtxHandle {
    fn drop(&mut self) { unsafe { ntt_free(self.0); } }
}
```

### 7.3 Assembly Loop Data Structures

```rust
struct PendingBlock {
    q1:        Option<Vec<u32>>,
    q2:        Option<Vec<u32>>,
    token_pos: u32,
    layer_id:  u32,
}

pub struct GarnerResult {
    pub seq_id:    u64,
    pub token_pos: u32,
    pub layer_id:  u32,
    pub coeffs:    Vec<i64>,
}
```

Pending buffer: `DashMap<u64, PendingBlock>` — lock-free concurrent access
prevents the independent QUIC streams from serializing each other during
high-throughput shard assembly.

### 7.4 Assembly Loop API

```rust
pub async fn run_garner_loop(
    coordinator: SpQuicCoordinator,
    ntt_n:       u32,                         // 128, 256, or 512
    results_tx:  mpsc::Sender<GarnerResult>,
) -> Result<()>
```

Logic:
1. Accept connection loop; per connection spawn an async task.
2. Task loops: `accept_uni()` → `recv_block()` → insert into `DashMap`.
3. After each insert, if both `q1` and `q2` are present for `seq_id`:
   extract both, call `ntt_crt_recombine` through FFI, send `GarnerResult`.
4. Remove the pending entry after reconstruction.

---

## 8. Integration Tests (`tests/test_quic_shard.rs`)

Each test uses a distinct loopback port range to prevent cross-test
interference. All tests are `#[tokio::test]`.

### M_NET_1 — Topology scaffold (ports 8081–8083)

Bind coordinator on `:8081`. Worker A connects from `:8082`, Worker B from
`:8083`. Each worker sends one probe `ResidueBlock` (N=128) on its own uni
stream. Test asserts both connections are accepted and both streams arrive.
Pure topology verification — no math.

### M_NET_2 — Math identity (ports 8084–8086)

```
N = 128
q1_residues[i] = i % Q1   (synthetic, in [0, Q1))
q2_residues[i] = i % Q2   (synthetic, in [0, Q2))

// scalar reference: direct FFI, no network
expected = ntt_crt_recombine(ntt_init(128), q1_residues, q2_residues)

// network path
run_garner_loop(coord_8084, N=128) → mpsc::channel<GarnerResult>
worker_a.send_block(seq_id=42, prime_selector=0, residues=q1_residues)
worker_b.send_block(seq_id=42, prime_selector=1, residues=q2_residues)

result = channel.recv()
assert_eq!(result.seq_id, 42)
assert_eq!(result.coeffs, expected)    // bit-identical Garner reconstruction
```

### M_NET_3 — HoL bypass with timeout (ports 8087–8088)

Worker A's block 0 has a `tokio::time::sleep(200ms)` injected before
`send_block` (simulates a slow sender on q1). Block 1 is sent immediately.
The coordinator accepts both streams concurrently:

- **Block 1** is wrapped in `tokio::time::timeout(100ms)` — must arrive within
  100ms of the test start.
- **Block 0** is wrapped in `tokio::time::timeout(500ms)` — arrives after the
  200ms sleep; ample deadline.

The falsifiability argument: if the implementation serialized both blocks onto
a single shared QUIC stream, block 1 would be queued behind block 0's delayed
send and arrive at ~200ms, **exceeding the 100ms deadline**. Per-block
`open_uni()` delivers block 1 independently at ~0ms, well within 100ms.

Final assertion: both seq IDs arrive; block 1's 100ms timeout does not fire.

---

## 9. Closure Gates

| Gate     | Description                                                 | Status  |
|----------|-------------------------------------------------------------|---------|
| M_NET_1  | 3-node loopback topology: workers dial coordinator, streams established | PENDING |
| M_NET_2  | Garner reconstruction bit-identical to scalar C reference   | PENDING |
| M_NET_3  | HoL bypass: q2 stream not blocked by delayed q1 stream (timeout assertion) | PENDING |

Phase 6-NET closes to `SESSION-CLOSED-lat-6-NET.md` when all three gates pass
on `cargo test` in the daemon crate.

---

## 10. Open Items / Future Work

- Replace `SkipServerVerification` with Phase 5 ed25519 dominance identity
  (the keypair already exists in `daemon.rs`; integration is a later phase)
- `run_garner_loop` currently creates a new `ntt_ctx` per reconstruction;
  a future optimization passes a shared `Arc<NttCtxHandle>` instead
- Extend to n>2 shards when additional prime pairs are defined
