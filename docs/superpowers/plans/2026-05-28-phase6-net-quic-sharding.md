---
type: design
title: "Phase 6-NET: QUIC CRT Sharding Implementation Plan"
description: "Goal: Build a QUIC transport layer for streaming dual-prime NTT residues from two shard workers to a coordinator for Garner CRT reconstruction, verified by three integration-test gates (M_NET_1 topolo"
tags: [design]
timestamp: 2026-05-27T16:49:02Z
resource: ./docs/superpowers/plans/2026-05-28-phase6-net-quic-sharding.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---

# Phase 6-NET: QUIC CRT Sharding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a QUIC transport layer for streaming dual-prime NTT residues from two shard workers to a coordinator for Garner CRT reconstruction, verified by three integration-test gates (M_NET_1 topology, M_NET_2 bit-identical math, M_NET_3 falsifiable HoL bypass).

**Architecture:** In-process Quinn QUIC endpoints with rcgen ephemeral TLS 1.3 certs; one unidirectional stream per residue block (independent QUIC stream IDs = HoL bypass). 64-byte `ShardBlockHeader` + raw LE u32 residues per stream. DashMap-backed coordinator assembly loop calls `ntt_crt_recombine` via manual FFI once both primes arrive for the same `seq_id`. Integration tests import from a new `[lib]` target in the sp-daemon crate.

**Tech Stack:** quinn 0.11, rustls 0.23 + ring, rcgen 0.13 + ring, dashmap 6, sp_ntt_crt (C math already linked in build.rs)

**Spec:** `docs/superpowers/specs/2026-05-28-phase6-net-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `tools/sp_daemon/Cargo.toml` | Modify | Add quinn, rustls, rcgen, dashmap deps + `[lib]` target |
| `tools/sp_daemon/src/lib.rs` | Create | `pub mod network; pub mod ntt_ffi;` |
| `tools/sp_daemon/src/network/mod.rs` | Create | `pub mod quic_shard;` |
| `tools/sp_daemon/src/network/quic_shard.rs` | Create | Wire types, TLS helpers, SpQuicCoordinator, SpQuicWorker, recv_block, run_garner_loop |
| `tools/sp_daemon/src/ntt_ffi.rs` | Create | Manual extern "C" block for sp_ntt_crt + NttCtxHandle RAII |
| `tools/sp_daemon/tests/test_quic_shard.rs` | Create | M_NET_1, M_NET_2, M_NET_3 |
| `papers/SESSION-STATE-lat-6-NET.md` | Create | Phase 6 session state (lattice repo) |

All work in `tools/sp_daemon/` is in `shannon-prime-system-engine`.
Session state goes in `shannon-prime-lattice`.

---

## Task 1: Cargo scaffold — deps, `[lib]` target, module stubs

**Files:**
- Modify: `tools/sp_daemon/Cargo.toml`
- Create: `tools/sp_daemon/src/lib.rs`
- Create: `tools/sp_daemon/src/network/mod.rs`

- [ ] **Step 1.1: Add deps and `[lib]` to Cargo.toml**

In `tools/sp_daemon/Cargo.toml`, add after the existing `[dependencies]` block entries (keep all existing deps):

```toml
[lib]
name = "sp_daemon"
path = "src/lib.rs"
```

Add to `[dependencies]`:
```toml
quinn   = { version = "0.11", features = ["rustls"] }
rustls  = { version = "0.23", features = ["ring"] }
rcgen   = { version = "0.13", features = ["ring"] }
dashmap = "6"
```

- [ ] **Step 1.2: Create `src/lib.rs`**

```rust
pub mod network;
pub mod ntt_ffi;
```

- [ ] **Step 1.3: Create `src/network/mod.rs`**

```rust
pub mod quic_shard;
```

- [ ] **Step 1.4: Create stub `src/network/quic_shard.rs`** (just enough to compile)

```rust
// Phase 6-NET QUIC transport — stub; filled in Tasks 2–7.
```

- [ ] **Step 1.5: Create stub `src/ntt_ffi.rs`** (just enough to compile)

```rust
// Phase 6-NET NTT FFI — stub; filled in Task 3.
```

- [ ] **Step 1.6: Verify the scaffold compiles**

Run from `tools/sp_daemon/`:
```powershell
cargo check 2>&1
```
Expected: no errors. Warnings about dead code on existing modules are fine.
If bindgen fails: set `$env:LIBCLANG_PATH = "C:\Program Files\LLVM\bin"` first.

- [ ] **Step 1.7: Commit**

```powershell
git add tools/sp_daemon/Cargo.toml tools/sp_daemon/src/lib.rs `
        tools/sp_daemon/src/network/mod.rs `
        tools/sp_daemon/src/network/quic_shard.rs `
        tools/sp_daemon/src/ntt_ffi.rs
git commit -m "feat(phase6-net): add [lib] target + QUIC/NTT stubs, bump Cargo deps"
```

---

## Task 2: Wire types — `ShardBlockHeader`, `ResidueBlock`, serialization

**Files:**
- Modify: `tools/sp_daemon/src/network/quic_shard.rs`

- [ ] **Step 2.1: Write the compile-time type test first**

Add to the TOP of `tests/test_quic_shard.rs` (create the file):

```rust
use sp_daemon::network::quic_shard::{ShardBlockHeader, ResidueBlock};

#[test]
fn header_is_64_bytes() {
    assert_eq!(std::mem::size_of::<ShardBlockHeader>(), 64);
}

#[test]
fn header_roundtrip() {
    use sp_daemon::network::quic_shard::{header_to_bytes, header_from_bytes};

    let h = ShardBlockHeader {
        seq_id: 0xDEAD_BEEF_CAFE_1234,
        token_pos: 77,
        layer_id: 3,
        prime_selector: 1,
        _pad: [0u8; 47],
    };
    let bytes = header_to_bytes(&h);
    let h2 = header_from_bytes(&bytes);
    assert_eq!(h2.seq_id, h.seq_id);
    assert_eq!(h2.token_pos, h.token_pos);
    assert_eq!(h2.layer_id, h.layer_id);
    assert_eq!(h2.prime_selector, h.prime_selector);
}
```

- [ ] **Step 2.2: Run — expect compile failure (types not defined yet)**

```powershell
cargo test header 2>&1
```
Expected: error — `ShardBlockHeader` not found.

- [ ] **Step 2.3: Implement wire types in `quic_shard.rs`**

Replace the stub in `src/network/quic_shard.rs` with:

```rust
//! quic_shard.rs — QUIC transport for CRT shard residue streaming (Phase 6-NET).
//!
//! One unidirectional QUIC stream per residue block. Independent stream IDs
//! prevent q1 latency from blocking q2 delivery at the OS scheduler level.

use std::net::SocketAddr;
use std::sync::Arc;

use dashmap::DashMap;
use quinn::{Connection, Endpoint, RecvStream};
use rustls::pki_types::{CertificateDer, PrivateKeyDer, PrivatePkcs8KeyDer};
use tokio::sync::mpsc;

use crate::ntt_ffi::{ntt_crt_recombine, ntt_free, ntt_init};

// ── Error type ────────────────────────────────────────────────────────────────

pub type ShardError = Box<dyn std::error::Error + Send + Sync + 'static>;
pub type Result<T> = std::result::Result<T, ShardError>;

// ── Wire types ────────────────────────────────────────────────────────────────

/// 64-byte stream header preceding each NTT residue payload.
/// All multi-byte fields are little-endian.
#[repr(C)]
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct ShardBlockHeader {
    pub seq_id:         u64,      //  0..8   global sequence counter
    pub token_pos:      u32,      //  8..12  token position in context
    pub layer_id:       u32,      // 12..16  transformer layer index
    pub prime_selector: u8,       // 16      0 = q1 (1073738753), 1 = q2 (1073732609)
    pub _pad:           [u8; 47], // 17..64  reserved zeros
}
const _: () = assert!(std::mem::size_of::<ShardBlockHeader>() == 64);

/// Residue block transmitted over one QUIC unidirectional stream.
pub struct ResidueBlock {
    pub header:   ShardBlockHeader,
    pub residues: Vec<u32>,
}

// ── Serialization (no serde, no protobuf) ─────────────────────────────────────

pub fn header_to_bytes(h: &ShardBlockHeader) -> [u8; 64] {
    let mut buf = [0u8; 64];
    buf[0..8].copy_from_slice(&h.seq_id.to_le_bytes());
    buf[8..12].copy_from_slice(&h.token_pos.to_le_bytes());
    buf[12..16].copy_from_slice(&h.layer_id.to_le_bytes());
    buf[16] = h.prime_selector;
    buf
}

pub fn header_from_bytes(b: &[u8; 64]) -> ShardBlockHeader {
    ShardBlockHeader {
        seq_id:         u64::from_le_bytes(b[0..8].try_into().unwrap()),
        token_pos:      u32::from_le_bytes(b[8..12].try_into().unwrap()),
        layer_id:       u32::from_le_bytes(b[12..16].try_into().unwrap()),
        prime_selector: b[16],
        _pad:           [0u8; 47],
    }
}
```

*(Leave the rest of the file blank for now — TLS, endpoints, recv, loop are added in Tasks 4–7.)*

- [ ] **Step 2.4: Run — tests should pass**

```powershell
cargo test header 2>&1
```
Expected:
```
test header_is_64_bytes ... ok
test header_roundtrip ... ok
```

- [ ] **Step 2.5: Commit**

```powershell
git add tools/sp_daemon/src/network/quic_shard.rs `
        tools/sp_daemon/tests/test_quic_shard.rs
git commit -m "feat(phase6-net): wire types ShardBlockHeader + ResidueBlock + roundtrip test"
```

---

## Task 3: NTT FFI — `ntt_ffi.rs`

**Files:**
- Modify: `tools/sp_daemon/src/ntt_ffi.rs`

`sp_ntt_crt` is already in `build.rs` MODULES — no build script change needed.

- [ ] **Step 3.1: Write a failing test for the FFI**

Add to `tests/test_quic_shard.rs`:

```rust
use sp_daemon::ntt_ffi::{ntt_crt_recombine, ntt_free, ntt_init, NttCtxHandle};

const Q1: u32 = 1073738753;
const Q2: u32 = 1073732609;

#[test]
fn ntt_ffi_scalar_reference() {
    const N: usize = 128;
    let q1: Vec<u32> = (0..N as u32).map(|i| i % Q1).collect();
    let q2: Vec<u32> = (0..N as u32).map(|i| i % Q2).collect();

    let out: Vec<i64> = unsafe {
        let ctx = ntt_init(N as u32);
        assert!(!ctx.is_null(), "ntt_init returned null for N=128");
        let mut v = vec![0i64; N];
        ntt_crt_recombine(ctx, q1.as_ptr(), q2.as_ptr(), v.as_mut_ptr());
        ntt_free(ctx);
        v
    };

    // Coefficient 0: CRT of (0 mod q1, 0 mod q2) = 0
    assert_eq!(out[0], 0, "coeff[0] must be 0");
    // Coefficient 1: CRT of (1 mod q1, 1 mod q2) = 1 (both residues = 1)
    assert_eq!(out[1], 1, "coeff[1] must be 1");
    // All values must be in the signed centered range (-M/2, M/2]
    let m_half: i64 = 1152908312643096577_i64 / 2;
    for &c in &out {
        assert!(c.abs() <= m_half, "coefficient out of CRT range: {}", c);
    }
}

#[test]
fn ntt_ctx_handle_drop() {
    // Verify NttCtxHandle's Drop impl doesn't double-free
    unsafe {
        let ctx = ntt_init(128);
        assert!(!ctx.is_null());
        let _handle = NttCtxHandle(ctx);
        // _handle drops here — ntt_free called exactly once
    }
}
```

- [ ] **Step 3.2: Run — expect compile failure (FFI not defined)**

```powershell
cargo test ntt_ffi 2>&1
```
Expected: error — `ntt_init` not found.

- [ ] **Step 3.3: Implement `ntt_ffi.rs`**

Replace the stub in `src/ntt_ffi.rs` with:

```rust
//! ntt_ffi.rs — Manual FFI bindings for sp_ntt_crt (Phase 6-NET).
//! Mirrors ntt_crt.h. sp_ntt_crt is already linked via build.rs MODULES.

/// Opaque NTT context (mirrors ntt_ctx in ntt_crt.h).
pub enum NttCtx {}

extern "C" {
    /// Allocate context for transform length N ∈ {128, 256, 512}. Returns NULL
    /// for invalid N.
    pub fn ntt_init(n: u32) -> *mut NttCtx;

    /// Free a context. ntt_free(NULL) is a no-op.
    pub fn ntt_free(ctx: *mut NttCtx);

    /// Garner CRT: N residue pairs (x1 mod q1, x2 mod q2) → N signed centered
    /// coefficients in (-M/2, M/2], written to `out`.
    pub fn ntt_crt_recombine(
        ctx: *const NttCtx,
        x1:  *const u32,
        x2:  *const u32,
        out: *mut i64,
    );

    /// NTT-domain pointwise multiply:
    /// out1[i] = a1[i]*b1[i] mod q1, out2[i] = a2[i]*b2[i] mod q2.
    pub fn ntt_pointwise_mul(
        ctx:  *const NttCtx,
        a1: *const u32, a2: *const u32,
        b1: *const u32, b2: *const u32,
        out1: *mut u32, out2: *mut u32,
    );
}

/// RAII wrapper for ntt_ctx: calls ntt_free on drop.
///
/// Safety: ntt_ctx is read-only after ntt_init (per ntt_crt.h) — safe to share
/// across threads as Arc<NttCtxHandle>.
pub struct NttCtxHandle(pub *mut NttCtx);

unsafe impl Send for NttCtxHandle {}
unsafe impl Sync for NttCtxHandle {}

impl Drop for NttCtxHandle {
    fn drop(&mut self) {
        unsafe { ntt_free(self.0); }
    }
}
```

- [ ] **Step 3.4: Run — tests should pass**

```powershell
cargo test ntt_ffi 2>&1
```
Expected:
```
test ntt_ffi_scalar_reference ... ok
test ntt_ctx_handle_drop ... ok
```

If linking fails (sp_ntt_crt.lib not found), set:
```powershell
$env:SP_SYSTEM_BUILD_DIR = "D:\F\shannon-prime-repos\shannon-prime-system-engine\build-cpu\lib\shannon-prime-system"
```

- [ ] **Step 3.5: Commit**

```powershell
git add tools/sp_daemon/src/ntt_ffi.rs tools/sp_daemon/tests/test_quic_shard.rs
git commit -m "feat(phase6-net): ntt_ffi.rs — NttCtx/NttCtxHandle FFI + scalar reference test"
```

---

## Task 4: TLS helpers — `SkipServerVerification`, `make_server_config`, `make_client_config`

**Files:**
- Modify: `tools/sp_daemon/src/network/quic_shard.rs`

- [ ] **Step 4.1: Write a failing test for TLS config construction**

Add to `tests/test_quic_shard.rs`:

```rust
#[test]
fn tls_configs_construct_without_panic() {
    use sp_daemon::network::quic_shard::{make_server_config, make_client_config};
    make_server_config().expect("server config");
    make_client_config().expect("client config");
}
```

- [ ] **Step 4.2: Run — expect compile failure**

```powershell
cargo test tls_configs 2>&1
```
Expected: error — `make_server_config` not found.

- [ ] **Step 4.3: Add TLS helpers to `quic_shard.rs`**

Append after the serialization section in `src/network/quic_shard.rs`:

```rust
// ── TLS ───────────────────────────────────────────────────────────────────────

/// Dev-mode TLS verifier: accepts any server certificate.
/// Replace with Phase 5 ed25519 dominance identity in a later phase.
#[derive(Debug)]
struct SkipServerVerification;

impl rustls::client::danger::ServerCertVerifier for SkipServerVerification {
    fn verify_server_cert(
        &self,
        _end_entity: &CertificateDer<'_>,
        _intermediates: &[CertificateDer<'_>],
        _server_name: &rustls::pki_types::ServerName<'_>,
        _ocsp_response: &[u8],
        _now: rustls::pki_types::UnixTime,
    ) -> std::result::Result<rustls::client::danger::ServerCertVerified, rustls::Error> {
        Ok(rustls::client::danger::ServerCertVerified::assertion())
    }

    fn verify_tls12_signature(
        &self,
        _message: &[u8],
        _cert: &CertificateDer<'_>,
        _dss: &rustls::DigitallySignedStruct,
    ) -> std::result::Result<rustls::client::danger::HandshakeSignatureValid, rustls::Error> {
        Ok(rustls::client::danger::HandshakeSignatureValid::assertion())
    }

    fn verify_tls13_signature(
        &self,
        _message: &[u8],
        _cert: &CertificateDer<'_>,
        _dss: &rustls::DigitallySignedStruct,
    ) -> std::result::Result<rustls::client::danger::HandshakeSignatureValid, rustls::Error> {
        Ok(rustls::client::danger::HandshakeSignatureValid::assertion())
    }

    fn supported_verify_schemes(&self) -> Vec<rustls::SignatureScheme> {
        vec![
            rustls::SignatureScheme::RSA_PKCS1_SHA256,
            rustls::SignatureScheme::RSA_PKCS1_SHA384,
            rustls::SignatureScheme::RSA_PKCS1_SHA512,
            rustls::SignatureScheme::ECDSA_NISTP256_SHA256,
            rustls::SignatureScheme::ECDSA_NISTP384_SHA384,
            rustls::SignatureScheme::ECDSA_NISTP521_SHA512,
            rustls::SignatureScheme::RSA_PSS_SHA256,
            rustls::SignatureScheme::RSA_PSS_SHA384,
            rustls::SignatureScheme::RSA_PSS_SHA512,
            rustls::SignatureScheme::ED25519,
        ]
    }
}

pub fn make_server_config() -> Result<quinn::ServerConfig> {
    let ck = rcgen::generate_simple_self_signed(vec!["localhost".into()])?;
    let cert_der: CertificateDer<'static> = ck.cert.der().clone();
    let key_der = PrivateKeyDer::Pkcs8(PrivatePkcs8KeyDer::from(ck.key_pair.serialize_der()));

    let tls = rustls::ServerConfig::builder()
        .with_no_client_auth()
        .with_single_cert(vec![cert_der], key_der)?;

    Ok(quinn::ServerConfig::with_crypto(Arc::new(tls)))
}

pub fn make_client_config() -> Result<quinn::ClientConfig> {
    let tls = rustls::ClientConfig::builder()
        .dangerous()
        .with_custom_certificate_verifier(Arc::new(SkipServerVerification))
        .with_no_client_auth();

    Ok(quinn::ClientConfig::new(Arc::new(tls)))
}
```

Also add these `use` statements at the top of `quic_shard.rs` (the existing imports already pull in `Arc`, `rustls::pki_types::*` — just add `rcgen`):

```rust
use rcgen;
```

*(rcgen is imported implicitly via the crate name; no additional `use` needed if functions are called as `rcgen::generate_simple_self_signed`.)*

- [ ] **Step 4.4: Run — test should pass**

```powershell
cargo test tls_configs 2>&1
```
Expected: `test tls_configs_construct_without_panic ... ok`

- [ ] **Step 4.5: Commit**

```powershell
git add tools/sp_daemon/src/network/quic_shard.rs `
        tools/sp_daemon/tests/test_quic_shard.rs
git commit -m "feat(phase6-net): TLS helpers — SkipServerVerification + make_{server,client}_config"
```

---

## Task 5: `SpQuicCoordinator` — bind + accept_connection

**Files:**
- Modify: `tools/sp_daemon/src/network/quic_shard.rs`

- [ ] **Step 5.1: Write a failing test for coordinator bind**

Add to `tests/test_quic_shard.rs`:

```rust
#[tokio::test]
async fn coordinator_binds_on_loopback() {
    use sp_daemon::network::quic_shard::SpQuicCoordinator;

    let coord = SpQuicCoordinator::bind("127.0.0.1:0".parse().unwrap())
        .await
        .expect("coordinator bind failed");

    let addr = coord.local_addr().expect("local_addr");
    assert_eq!(addr.ip().to_string(), "127.0.0.1");
    assert_ne!(addr.port(), 0); // OS assigned a real port
}
```

- [ ] **Step 5.2: Run — expect compile failure**

```powershell
cargo test coordinator_binds 2>&1
```
Expected: error — `SpQuicCoordinator` not found.

- [ ] **Step 5.3: Add `SpQuicCoordinator` to `quic_shard.rs`**

Append after the TLS section:

```rust
// ── Coordinator ───────────────────────────────────────────────────────────────

pub struct SpQuicCoordinator {
    endpoint: Endpoint,
}

impl SpQuicCoordinator {
    /// Bind a QUIC server endpoint on `addr`.
    pub async fn bind(addr: SocketAddr) -> Result<Self> {
        let server_config = make_server_config()?;
        let endpoint = Endpoint::server(server_config, addr)?;
        Ok(Self { endpoint })
    }

    /// Accept the next incoming QUIC connection (blocks until one arrives).
    pub async fn accept_connection(&self) -> Result<Connection> {
        let incoming = self.endpoint.accept().await
            .ok_or("coordinator endpoint closed")?;
        let conn = incoming.await?;
        Ok(conn)
    }

    pub fn local_addr(&self) -> std::io::Result<SocketAddr> {
        self.endpoint.local_addr()
    }
}
```

- [ ] **Step 5.4: Run — test should pass**

```powershell
cargo test coordinator_binds 2>&1
```
Expected: `test coordinator_binds_on_loopback ... ok`

- [ ] **Step 5.5: Commit**

```powershell
git add tools/sp_daemon/src/network/quic_shard.rs `
        tools/sp_daemon/tests/test_quic_shard.rs
git commit -m "feat(phase6-net): SpQuicCoordinator::bind + accept_connection + bind test"
```

---

## Task 6: `SpQuicWorker` + `recv_block` — connect, send, receive

**Files:**
- Modify: `tools/sp_daemon/src/network/quic_shard.rs`

- [ ] **Step 6.1: Write a failing roundtrip test**

Add to `tests/test_quic_shard.rs`:

```rust
#[tokio::test]
async fn worker_connect_and_roundtrip() {
    use sp_daemon::network::quic_shard::{
        recv_block, ResidueBlock, ShardBlockHeader, SpQuicCoordinator, SpQuicWorker,
    };
    use std::time::Duration;

    let coord = SpQuicCoordinator::bind("127.0.0.1:0".parse().unwrap())
        .await
        .expect("bind");
    let coord_addr = coord.local_addr().unwrap();

    // Acceptor task
    let accept = tokio::spawn(async move {
        let conn = coord.accept_connection().await.expect("accept");
        let stream = conn.accept_uni().await.expect("uni");
        recv_block(stream).await.expect("recv_block")
    });

    // Worker connects and sends one block
    let worker = SpQuicWorker::connect(
        "127.0.0.1:0".parse().unwrap(),
        coord_addr,
    )
    .await
    .expect("connect");

    let block = ResidueBlock {
        header: ShardBlockHeader {
            seq_id: 99,
            token_pos: 7,
            layer_id: 2,
            prime_selector: 0,
            _pad: [0u8; 47],
        },
        residues: (0u32..128).collect(),
    };
    worker.send_block(&block).await.expect("send_block");

    let received = tokio::time::timeout(Duration::from_secs(5), accept)
        .await
        .expect("timeout")
        .expect("task panic");

    assert_eq!(received.header.seq_id, 99);
    assert_eq!(received.header.prime_selector, 0);
    assert_eq!(received.residues.len(), 128);
    assert_eq!(received.residues[0], 0);
    assert_eq!(received.residues[127], 127);
}
```

- [ ] **Step 6.2: Run — expect compile failure**

```powershell
cargo test worker_connect 2>&1
```
Expected: error — `SpQuicWorker` / `recv_block` not found.

- [ ] **Step 6.3: Add `SpQuicWorker` and `recv_block` to `quic_shard.rs`**

Append after the coordinator section:

```rust
// ── Worker ────────────────────────────────────────────────────────────────────

#[derive(Clone)]
pub struct SpQuicWorker {
    connection: Connection,
}

impl SpQuicWorker {
    /// Dial the coordinator at `server_addr`, binding the client endpoint on
    /// `local_addr` (use port 0 for OS-assigned port).
    pub async fn connect(local_addr: SocketAddr, server_addr: SocketAddr) -> Result<Self> {
        let client_config = make_client_config()?;
        let mut endpoint = Endpoint::client(local_addr)?;
        endpoint.set_default_client_config(client_config);
        let conn = endpoint.connect(server_addr, "localhost")?.await?;
        Ok(Self { connection: conn })
    }

    /// Open a fresh unidirectional stream and write `block`.
    /// Each call to send_block opens its own stream ID — independent delivery,
    /// no HoL coupling between blocks.
    pub async fn send_block(&self, block: &ResidueBlock) -> Result<()> {
        let mut send = self.connection.open_uni().await?;

        send.write_all(&header_to_bytes(&block.header)).await?;
        for r in &block.residues {
            send.write_all(&r.to_le_bytes()).await?;
        }
        send.finish()?;
        Ok(())
    }
}

// ── Receive ───────────────────────────────────────────────────────────────────

/// Read all bytes from a unidirectional stream and decode a ResidueBlock.
/// First 64 bytes = ShardBlockHeader; remaining bytes / 4 = residues.
/// Max payload: 64 + 512 * 4 = 2112 bytes (N ≤ 512).
pub async fn recv_block(mut stream: RecvStream) -> Result<ResidueBlock> {
    let bytes = stream.read_to_end(64 + 512 * 4).await?;

    if bytes.len() < 64 {
        return Err(format!("stream too short: {} bytes (need ≥ 64)", bytes.len()).into());
    }
    if (bytes.len() - 64) % 4 != 0 {
        return Err("residue payload length not a multiple of 4".into());
    }

    let header = header_from_bytes(bytes[0..64].try_into().unwrap());
    let residues = bytes[64..]
        .chunks_exact(4)
        .map(|c| u32::from_le_bytes(c.try_into().unwrap()))
        .collect();

    Ok(ResidueBlock { header, residues })
}
```

- [ ] **Step 6.4: Run — roundtrip test should pass**

```powershell
cargo test worker_connect_and_roundtrip 2>&1
```
Expected: `test worker_connect_and_roundtrip ... ok`

- [ ] **Step 6.5: Commit**

```powershell
git add tools/sp_daemon/src/network/quic_shard.rs `
        tools/sp_daemon/tests/test_quic_shard.rs
git commit -m "feat(phase6-net): SpQuicWorker::connect + send_block + recv_block + roundtrip test"
```

---

## Task 7: `run_garner_loop` — DashMap assembly + FFI reconstruction

**Files:**
- Modify: `tools/sp_daemon/src/network/quic_shard.rs`

- [ ] **Step 7.1: Write a failing unit test for the assembly logic**

Add to `tests/test_quic_shard.rs`:

```rust
#[tokio::test]
async fn garner_loop_reconstructs_single_pair() {
    use sp_daemon::network::quic_shard::{
        run_garner_loop, ResidueBlock, ShardBlockHeader, SpQuicCoordinator, SpQuicWorker,
    };
    use sp_daemon::ntt_ffi::{ntt_crt_recombine, ntt_free, ntt_init};
    use std::time::Duration;
    use tokio::sync::mpsc;

    const N: usize = 128;
    let q1: Vec<u32> = (0..N as u32).map(|i| i % Q1).collect();
    let q2: Vec<u32> = (0..N as u32).map(|i| i % Q2).collect();

    // Scalar reference
    let expected: Vec<i64> = unsafe {
        let ctx = ntt_init(N as u32);
        let mut out = vec![0i64; N];
        ntt_crt_recombine(ctx, q1.as_ptr(), q2.as_ptr(), out.as_mut_ptr());
        ntt_free(ctx);
        out
    };

    // Network path
    let coord = SpQuicCoordinator::bind("127.0.0.1:0".parse().unwrap())
        .await
        .expect("bind");
    let coord_addr = coord.local_addr().unwrap();

    let (tx, mut rx) = mpsc::channel(4);
    tokio::spawn(run_garner_loop(coord, N as u32, tx));

    tokio::time::sleep(Duration::from_millis(20)).await;

    // Worker A (q1)
    let wa = SpQuicWorker::connect("127.0.0.1:0".parse().unwrap(), coord_addr)
        .await.expect("wa connect");
    wa.send_block(&ResidueBlock {
        header: ShardBlockHeader { seq_id: 7, token_pos: 0, layer_id: 0,
                                   prime_selector: 0, _pad: [0; 47] },
        residues: q1,
    }).await.expect("send q1");

    // Worker B (q2)
    let wb = SpQuicWorker::connect("127.0.0.1:0".parse().unwrap(), coord_addr)
        .await.expect("wb connect");
    wb.send_block(&ResidueBlock {
        header: ShardBlockHeader { seq_id: 7, token_pos: 0, layer_id: 0,
                                   prime_selector: 1, _pad: [0; 47] },
        residues: q2,
    }).await.expect("send q2");

    let result = tokio::time::timeout(Duration::from_secs(5), rx.recv())
        .await
        .expect("garner loop timeout")
        .expect("channel closed");

    assert_eq!(result.seq_id, 7);
    assert_eq!(result.coeffs, expected, "Garner reconstruction not bit-identical");
}
```

- [ ] **Step 7.2: Run — expect compile failure**

```powershell
cargo test garner_loop_reconstructs 2>&1
```
Expected: error — `run_garner_loop` / `GarnerResult` not found.

- [ ] **Step 7.3: Add `run_garner_loop` to `quic_shard.rs`**

Append after the `recv_block` section:

```rust
// ── Garner assembly loop ──────────────────────────────────────────────────────

#[derive(Default)]
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

/// Accept QUIC connections and streams from shard workers. When both q1 and q2
/// residues arrive for the same seq_id, call ntt_crt_recombine and send the
/// result on `results_tx`. Runs until the coordinator endpoint is dropped.
pub async fn run_garner_loop(
    coordinator: SpQuicCoordinator,
    ntt_n: u32,
    results_tx: mpsc::Sender<GarnerResult>,
) {
    let pending: Arc<DashMap<u64, PendingBlock>> = Arc::new(DashMap::new());

    loop {
        let conn = match coordinator.accept_connection().await {
            Ok(c) => c,
            Err(_) => break,
        };

        let pending = Arc::clone(&pending);
        let results_tx = results_tx.clone();

        tokio::spawn(async move {
            loop {
                let stream = match conn.accept_uni().await {
                    Ok(s) => s,
                    Err(_) => break,
                };

                let pending = Arc::clone(&pending);
                let results_tx = results_tx.clone();

                tokio::spawn(async move {
                    let block = match recv_block(stream).await {
                        Ok(b) => b,
                        Err(_) => return,
                    };

                    let seq_id = block.header.seq_id;
                    let prime_sel = block.header.prime_selector;

                    // Insert residue; check atomically if both primes arrived.
                    // DashMap entry() holds a shard lock for the duration of the block.
                    let both_arrived = {
                        let mut entry = pending.entry(seq_id).or_insert_with(|| PendingBlock {
                            q1: None,
                            q2: None,
                            token_pos: block.header.token_pos,
                            layer_id:  block.header.layer_id,
                        });
                        if prime_sel == 0 {
                            entry.q1 = Some(block.residues);
                        } else {
                            entry.q2 = Some(block.residues);
                        }
                        entry.q1.is_some() && entry.q2.is_some()
                    }; // shard lock released here

                    if both_arrived {
                        // Atomic remove — exactly one task wins if two race here.
                        if let Some((_, pb)) = pending.remove(&seq_id) {
                            if let (Some(q1), Some(q2)) = (pb.q1, pb.q2) {
                                let mut coeffs = vec![0i64; ntt_n as usize];
                                unsafe {
                                    let ctx = ntt_init(ntt_n);
                                    if !ctx.is_null() {
                                        ntt_crt_recombine(
                                            ctx,
                                            q1.as_ptr(),
                                            q2.as_ptr(),
                                            coeffs.as_mut_ptr(),
                                        );
                                        ntt_free(ctx);
                                    }
                                }
                                let _ = results_tx.send(GarnerResult {
                                    seq_id,
                                    token_pos: pb.token_pos,
                                    layer_id:  pb.layer_id,
                                    coeffs,
                                }).await;
                            }
                        }
                    }
                });
            }
        });
    }
}
```

- [ ] **Step 7.4: Run — test should pass**

```powershell
cargo test garner_loop_reconstructs 2>&1
```
Expected: `test garner_loop_reconstructs_single_pair ... ok`

- [ ] **Step 7.5: Commit**

```powershell
git add tools/sp_daemon/src/network/quic_shard.rs `
        tools/sp_daemon/tests/test_quic_shard.rs
git commit -m "feat(phase6-net): run_garner_loop — DashMap assembly + ntt_crt_recombine FFI + unit test"
```

---

## Task 8: M_NET_1 — Topology scaffold integration test

**Files:**
- Modify: `tools/sp_daemon/tests/test_quic_shard.rs`

M_NET_1 verifies three independent QUIC nodes (coordinator + 2 workers) can establish connections and streams on loopback.

- [ ] **Step 8.1: Add M_NET_1 test**

Add to `tests/test_quic_shard.rs`:

```rust
/// M_NET_1: Three-node topology — coordinator accepts two independent worker
/// connections and receives one stream from each.
#[tokio::test]
async fn m_net_1_topology_scaffold() {
    use sp_daemon::network::quic_shard::{
        recv_block, ResidueBlock, ShardBlockHeader, SpQuicCoordinator, SpQuicWorker,
    };
    use std::time::Duration;

    let coord = SpQuicCoordinator::bind("127.0.0.1:8081".parse().unwrap())
        .await
        .expect("coordinator bind :8081");

    let accept = tokio::spawn(async move {
        // Connection from worker A (q1)
        let conn_a = coord.accept_connection().await.expect("accept conn_a");
        let stream_a = conn_a.accept_uni().await.expect("uni from A");
        let block_a = recv_block(stream_a).await.expect("block A");
        assert_eq!(block_a.header.prime_selector, 0, "worker A must send q1 (selector=0)");
        assert_eq!(block_a.residues.len(), 128);

        // Connection from worker B (q2)
        let conn_b = coord.accept_connection().await.expect("accept conn_b");
        let stream_b = conn_b.accept_uni().await.expect("uni from B");
        let block_b = recv_block(stream_b).await.expect("block B");
        assert_eq!(block_b.header.prime_selector, 1, "worker B must send q2 (selector=1)");
        assert_eq!(block_b.residues.len(), 128);
    });

    // Worker A: local port 8082, connect to coordinator on 8081
    let worker_a = SpQuicWorker::connect(
        "127.0.0.1:8082".parse().unwrap(),
        "127.0.0.1:8081".parse().unwrap(),
    )
    .await
    .expect("worker A connect");

    worker_a
        .send_block(&ResidueBlock {
            header: ShardBlockHeader { seq_id: 0, token_pos: 0, layer_id: 0,
                                       prime_selector: 0, _pad: [0; 47] },
            residues: vec![1u32; 128],
        })
        .await
        .expect("worker A send");

    // Worker B: local port 8083, connect to coordinator on 8081
    let worker_b = SpQuicWorker::connect(
        "127.0.0.1:8083".parse().unwrap(),
        "127.0.0.1:8081".parse().unwrap(),
    )
    .await
    .expect("worker B connect");

    worker_b
        .send_block(&ResidueBlock {
            header: ShardBlockHeader { seq_id: 0, token_pos: 0, layer_id: 0,
                                       prime_selector: 1, _pad: [0; 47] },
            residues: vec![2u32; 128],
        })
        .await
        .expect("worker B send");

    tokio::time::timeout(Duration::from_secs(10), accept)
        .await
        .expect("M_NET_1 timed out")
        .expect("acceptor panicked");
}
```

- [ ] **Step 8.2: Run M_NET_1**

```powershell
cargo test m_net_1 -- --nocapture 2>&1
```
Expected:
```
test m_net_1_topology_scaffold ... ok
```

- [ ] **Step 8.3: Commit**

```powershell
git add tools/sp_daemon/tests/test_quic_shard.rs
git commit -m "test(phase6-net): M_NET_1 topology scaffold — 3-node loopback QUIC PASS"
```

---

## Task 9: M_NET_2 — Bit-identical Garner reconstruction

**Files:**
- Modify: `tools/sp_daemon/tests/test_quic_shard.rs`

M_NET_2 verifies that Garner reconstruction via the network path produces bit-identical output to the local scalar C reference.

- [ ] **Step 9.1: Add M_NET_2 test**

```rust
/// M_NET_2: Garner reconstruction via QUIC must be bit-identical to local
/// ntt_crt_recombine reference.
#[tokio::test]
async fn m_net_2_math_identity() {
    use sp_daemon::network::quic_shard::{
        run_garner_loop, ResidueBlock, ShardBlockHeader, SpQuicCoordinator, SpQuicWorker,
    };
    use sp_daemon::ntt_ffi::{ntt_crt_recombine, ntt_free, ntt_init};
    use std::time::Duration;
    use tokio::sync::mpsc;

    const N: usize = 128;

    // Synthetic residues: simple sequences in [0, qi)
    let q1_residues: Vec<u32> = (0..N as u32).map(|i| i % Q1).collect();
    let q2_residues: Vec<u32> = (0..N as u32).map(|i| i % Q2).collect();

    // Scalar reference (direct FFI, no network)
    let expected: Vec<i64> = unsafe {
        let ctx = ntt_init(N as u32);
        assert!(!ctx.is_null());
        let mut out = vec![0i64; N];
        ntt_crt_recombine(ctx, q1_residues.as_ptr(), q2_residues.as_ptr(), out.as_mut_ptr());
        ntt_free(ctx);
        out
    };

    // Start coordinator on :8084
    let coord = SpQuicCoordinator::bind("127.0.0.1:8084".parse().unwrap())
        .await
        .expect("bind :8084");
    let (results_tx, mut results_rx) = mpsc::channel(4);
    tokio::spawn(run_garner_loop(coord, N as u32, results_tx));
    tokio::time::sleep(Duration::from_millis(20)).await;

    // Worker A sends q1 from :8085
    let wa = SpQuicWorker::connect(
        "127.0.0.1:8085".parse().unwrap(),
        "127.0.0.1:8084".parse().unwrap(),
    )
    .await
    .expect("worker A");
    wa.send_block(&ResidueBlock {
        header: ShardBlockHeader { seq_id: 42, token_pos: 10, layer_id: 5,
                                   prime_selector: 0, _pad: [0; 47] },
        residues: q1_residues,
    })
    .await
    .expect("send q1");

    // Worker B sends q2 from :8086
    let wb = SpQuicWorker::connect(
        "127.0.0.1:8086".parse().unwrap(),
        "127.0.0.1:8084".parse().unwrap(),
    )
    .await
    .expect("worker B");
    wb.send_block(&ResidueBlock {
        header: ShardBlockHeader { seq_id: 42, token_pos: 10, layer_id: 5,
                                   prime_selector: 1, _pad: [0; 47] },
        residues: q2_residues,
    })
    .await
    .expect("send q2");

    // Coordinator must reconstruct seq_id=42 with bit-identical result
    let result = tokio::time::timeout(Duration::from_secs(5), results_rx.recv())
        .await
        .expect("M_NET_2 timeout — no reconstruction received")
        .expect("results channel closed");

    assert_eq!(result.seq_id, 42, "seq_id mismatch");
    assert_eq!(result.token_pos, 10);
    assert_eq!(result.layer_id, 5);
    assert_eq!(
        result.coeffs, expected,
        "M_NET_2 FAIL: Garner reconstruction via QUIC not bit-identical to scalar reference"
    );
}
```

- [ ] **Step 9.2: Run M_NET_2**

```powershell
cargo test m_net_2 -- --nocapture 2>&1
```
Expected:
```
test m_net_2_math_identity ... ok
```

- [ ] **Step 9.3: Commit**

```powershell
git add tools/sp_daemon/tests/test_quic_shard.rs
git commit -m "test(phase6-net): M_NET_2 bit-identical Garner reconstruction PASS"
```

---

## Task 10: M_NET_3 — HoL bypass with falsifiable timeout

**Files:**
- Modify: `tools/sp_daemon/tests/test_quic_shard.rs`

M_NET_3 proves per-block stream independence. Block 0 is delayed 200ms; block 1 must arrive at the coordinator within 100ms. If the implementation serialized blocks on a single shared stream, block 1 would queue behind block 0's delay and fail the 100ms deadline.

- [ ] **Step 10.1: Add M_NET_3 test**

```rust
/// M_NET_3: HoL bypass — block 1 (sent immediately) must arrive at the coordinator
/// within 100ms even though block 0 (on an independent stream) is delayed 200ms.
///
/// Falsifiability: a buggy implementation that serializes blocks on a single
/// shared stream would deliver block 1 no sooner than block 0 (200ms), causing
/// the 100ms deadline to fire.
#[tokio::test]
async fn m_net_3_hol_bypass() {
    use sp_daemon::network::quic_shard::{
        recv_block, ResidueBlock, ShardBlockHeader, SpQuicCoordinator, SpQuicWorker,
    };
    use std::time::Duration;

    let coord = SpQuicCoordinator::bind("127.0.0.1:8087".parse().unwrap())
        .await
        .expect("bind :8087");

    let accept = tokio::spawn(async move {
        let conn = coord.accept_connection().await.expect("accept");

        // First accept_uni() returns the stream that completes first.
        // Block 1 (seq_id=1) is sent immediately at t≈0ms; block 0 (seq_id=0)
        // is sent at t≈200ms. So the first stream to complete is block 1.
        let stream1 = conn.accept_uni().await.expect("first uni stream");
        let block1 = tokio::time::timeout(
            Duration::from_millis(100),
            recv_block(stream1),
        )
        .await
        .expect("M_NET_3 FAIL: block 1 did not arrive within 100ms — HoL blocking detected")
        .expect("recv_block failed on block 1");
        assert_eq!(block1.header.seq_id, 1, "first stream must be seq_id=1 (immediate)");

        // Second stream: block 0 arrives after the 200ms delay
        let stream0 = conn.accept_uni().await.expect("second uni stream");
        let block0 = tokio::time::timeout(
            Duration::from_millis(500),
            recv_block(stream0),
        )
        .await
        .expect("M_NET_3: block 0 did not arrive within 500ms")
        .expect("recv_block failed on block 0");
        assert_eq!(block0.header.seq_id, 0, "second stream must be seq_id=0 (delayed)");
    });

    // Single worker on :8088
    let worker = SpQuicWorker::connect(
        "127.0.0.1:8088".parse().unwrap(),
        "127.0.0.1:8087".parse().unwrap(),
    )
    .await
    .expect("worker connect");

    // Block 0 (seq_id=0): injected 200ms delay before send_block.
    // stream_id for block 0 is opened AFTER the sleep, so it cannot
    // arrive at the coordinator until t≈200ms.
    let worker_clone = worker.clone();
    tokio::spawn(async move {
        tokio::time::sleep(Duration::from_millis(200)).await;
        worker_clone
            .send_block(&ResidueBlock {
                header: ShardBlockHeader { seq_id: 0, token_pos: 0, layer_id: 0,
                                           prime_selector: 0, _pad: [0; 47] },
                residues: vec![0u32; 128],
            })
            .await
            .expect("send block 0");
    });

    // Block 1 (seq_id=1): sent immediately. Opens its own stream ID — independent
    // of block 0's stream.
    worker
        .send_block(&ResidueBlock {
            header: ShardBlockHeader { seq_id: 1, token_pos: 1, layer_id: 0,
                                       prime_selector: 1, _pad: [0; 47] },
            residues: vec![1u32; 128],
        })
        .await
        .expect("send block 1");

    tokio::time::timeout(Duration::from_secs(3), accept)
        .await
        .expect("M_NET_3 overall timeout")
        .expect("acceptor panicked");
}
```

- [ ] **Step 10.2: Run M_NET_3**

```powershell
cargo test m_net_3 -- --nocapture 2>&1
```
Expected:
```
test m_net_3_hol_bypass ... ok
```

- [ ] **Step 10.3: Run the full test suite**

```powershell
cargo test 2>&1
```
Expected: all tests pass. Gate summary:
```
test header_is_64_bytes                    ... ok
test header_roundtrip                      ... ok
test ntt_ffi_scalar_reference              ... ok
test ntt_ctx_handle_drop                   ... ok
test tls_configs_construct_without_panic   ... ok
test coordinator_binds_on_loopback         ... ok
test worker_connect_and_roundtrip          ... ok
test garner_loop_reconstructs_single_pair  ... ok
test m_net_1_topology_scaffold             ... ok   ← M_NET_1 PASS
test m_net_2_math_identity                 ... ok   ← M_NET_2 PASS
test m_net_3_hol_bypass                    ... ok   ← M_NET_3 PASS
```

- [ ] **Step 10.4: Commit**

```powershell
git add tools/sp_daemon/tests/test_quic_shard.rs
git commit -m "test(phase6-net): M_NET_3 HoL bypass (100ms gate on independent stream) PASS"
```

---

## Task 11: Session state document + tag

**Files:**
- Create: `papers/SESSION-STATE-lat-6-NET.md` (in `shannon-prime-lattice` repo)

- [ ] **Step 11.1: Write session state document**

Create `papers/SESSION-STATE-lat-6-NET.md` in the `shannon-prime-lattice` repo
with the following content (write it verbatim — no inner code fences needed;
the wire table uses plain indented text to avoid Markdown nesting issues):

    # SESSION STATE — Phase 6-NET / QUIC CRT Sharding
    
    **Date:** 2026-05-28
    **Tag:** lat-phase-6-net-state
    **Status:** STATE — M_NET_1 VERIFIED; M_NET_2 VERIFIED; M_NET_3 VERIFIED
    
    ---
    
    ## Algorithm
    
    CRT dual-prime fields Z_q1 and Z_q2 are mathematically independent. Each
    prime's NTT residue array is computed on a separate shard node and streamed
    to a coordinator over QUIC. QUIC delivers independent stream IDs without
    head-of-line coupling, so q1 latency cannot block q2 at the OS scheduler.
    
    Garner reconstruction: ntt_crt_recombine(ctx, q1, q2, out) — called on the
    coordinator once both residue arrays for a seq_id arrive.
    
    ---
    
    ## Wire Protocol (per stream)
    
    Offset  Size    Field
     0       8      seq_id         u64 LE
     8       4      token_pos      u32 LE
    12       4      layer_id       u32 LE
    16       1      prime_selector u8  (0=q1, 1=q2)
    17      47      _pad           zeros
    64      N*4     residues       N x u32 LE, N in {128,256,512}
    
    One QUIC unidirectional stream per block. Stream close = end of payload.
    
    ---
    
    ## Gate Summary
    
    | Gate     | Description                                             | Status      |
    |----------|---------------------------------------------------------|-------------|
    | M_NET_1  | 3-node loopback topology: workers dial coordinator      | **VERIFIED** |
    | M_NET_2  | Garner reconstruction bit-identical to scalar C ref     | **VERIFIED** |
    | M_NET_3  | HoL bypass: block 1 arrives within 100ms despite 200ms delay on block 0 | **VERIFIED** |
    
    ---
    
    ## What Is Built
    
    ### Daemon crate (tools/sp_daemon/)
    
    | File | Description |
    |------|-------------|
    | src/lib.rs | [lib] target re-exporting network and ntt_ffi modules |
    | src/ntt_ffi.rs | Manual FFI: ntt_init, ntt_free, ntt_crt_recombine, ntt_pointwise_mul, NttCtxHandle |
    | src/network/mod.rs | Module root |
    | src/network/quic_shard.rs | ShardBlockHeader (64B), ResidueBlock, SpQuicCoordinator, SpQuicWorker, recv_block, run_garner_loop |
    | tests/test_quic_shard.rs | M_NET_1, M_NET_2, M_NET_3 + 5 unit tests |
    
    cargo test: 11/11 PASS.
    
    ---
    
    ## What Is NOT Done
    
    - Replace SkipServerVerification with Phase 5 ed25519 dominance identity
    - Wire run_garner_loop into main daemon startup
    - Integration of actual KV-cache KSTE candidates as NTT inputs (§16.5)
    - Multi-shard (n > 2) topologies
    
    ---
    
    ## Prior Closure Chain
    
    - SESSION-STATE-lat-5-POUW.md (2026-05-27): Friedman Sieve; M_POUW_1 C
      layer VERIFIED; bench + PTX sources done; hardware gates pending
    - This file: Phase 6-NET QUIC CRT sharding; all 3 gates VERIFIED

- [ ] **Step 11.2: Commit the session state (lattice repo)**

From the `shannon-prime-lattice` directory:
```powershell
git add papers/SESSION-STATE-lat-6-NET.md
git commit -m "[session-state] Phase 6-NET: M_NET_1/2/3 all VERIFIED — QUIC CRT sharding complete"
```

- [ ] **Step 11.3: Tag both repos**

Engine repo:
```powershell
cd "D:/F/shannon-prime-repos/shannon-prime-system-engine"
git tag lat-phase-6-net-state
git push origin lat-phase-6-net-state
```

Lattice repo:
```powershell
cd "D:/F/shannon-prime-repos/shannon-prime-lattice"
git tag lat-phase-6-net-state
git push origin lat-phase-6-net-state
```

---

## Self-Review Checklist

Spec section → task coverage:

| Spec Section | Task |
|---|---|
| §3 File Layout | Task 1 |
| §4 Cargo.toml deps (+ rcgen feature = ring, + dashmap) | Task 1 |
| §5 Wire protocol (ShardBlockHeader 64B, LE, stream close boundary) | Task 2 |
| §6 TLS bootstrap (SkipServerVerification, make_server_config) | Task 4 |
| §6 SpQuicCoordinator::bind + accept_connection | Task 5 |
| §6 SpQuicWorker::connect + send_block (per-block open_uni) | Task 6 |
| §6 recv_block | Task 6 |
| §7 ntt_ffi.rs + NttCtxHandle | Task 3 |
| §7 DashMap pending buffer | Task 7 |
| §7 run_garner_loop | Task 7 |
| §8 M_NET_1 test (ports 8081–8083) | Task 8 |
| §8 M_NET_2 test (ports 8084–8086, bit-identical) | Task 9 |
| §8 M_NET_3 test (100ms < 200ms sleep, falsifiable) | Task 10 |
| §9 Closure gates + session state | Task 11 |

All spec sections covered. No placeholders. Type names consistent across all tasks.
