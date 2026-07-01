---
type: reference
title: "SP-SWARM Mesh API — the private, content-addressed, signed memory mesh (call surface + protocol)"
description: "The how-do-I-call-it reference for the SP-SWARM distributed memory mesh: the `sp_swarm` Rust crate (L1 content addressing, L2 have/want replication, L3 Ed25519 provenance, L4 C2-SimHash discovery), its public API, the QUIC wire protocol + Ed25519 roster handshake, every env flag, the daemon `swarm` feature + the standalone `sp-swarm-node` binary, the gate index, and turnkey config. Pairs with the design doc PPT-LAT-DESIGN-SWARM-MEMORY-MESH.md (the why) and the FINDINGS-LEDGER (the measured recall)."
tags: [reference, api, swarm, mesh, dht, sp_swarm, quic, ed25519, c2, replication, discovery, decide-execute]
timestamp: 2026-07-01T00:00:00Z
resource: shannon-prime-system-engine/tools/sp_swarm
sp_status: GREEN
sp_gate: "G-SWARM-REPLICATE-CONVERGE, G-SWARM-PROVENANCE-ED25519, G-SWARM-RUST-PARITY, G-SWARM-TRANSPORT-QUIC, G-SWARM-NODE, G-SWARM-DAEMON-WIRE, G-SWARM-C2-INDEX, G-SWARM-C2-SEMANTIC, G-SWARM-GOSSIP-DISCOVERY"
sp_commit: "engine 7daf2fa (L0-L4 complete + daemon-integrated)"
sp_repro: "cargo test -p sp-swarm --features transport (from tools/sp_swarm); python tools/sp_swarm/g_c2_semantic.py <corpus>"
---

# SP-SWARM Mesh API

**Gist.** A private, invite-only mesh that replicates the operator's MEM-OKF store across authenticated, encrypted, cryptographically-verified nodes — and lets a node *discover* relevant memories on its peers. It is **replication + discovery over a content-addressed store**, not a new database: don't build a store, sync the one we have. Five layers, all gated, all reusing proven assets (byte-exact SHA addressing, the engine's QUIC stack, the C2 SimHash). Default-off in the daemon (`SP_SWARM` unset = no-op). The design rationale + rejected mechanics are in [PPT-LAT-DESIGN-SWARM-MEMORY-MESH.md](PPT-LAT-DESIGN-SWARM-MEMORY-MESH.md); the measured recall numbers are in [PPT-LAT-FINDINGS-LEDGER.md](PPT-LAT-FINDINGS-LEDGER.md).

## Keyword LUT (jump table)
`crate` `sp_swarm` `modules` → §2. `addr` `norm` `classify` `two-address-classes` → §3. `have/want` `pull` `accept` `sync` → §4. `Ed25519` `roster` `provenance` `verify_provenance` → §5. `QUIC` `handshake` `SIM/GET/LIST` `wire` → §6. `C2` `find_similar` `discover_similar` `shortlist` → §7. `SP_SWARM_*` `flags` `env` → §8. `sp-swarm-node` `daemon` `swarm-feature` `run_node` → §9. `gates` `G-SWARM-*` → §10. `config` `roster.txt` `run` → §11.

---

## 1. Layer stack (what runs where)

```
  L4  discovery      SIM gossip -> C2 shortlist -> exact-fetch verify   (similarity.rs + transport.rs)
  L3  provenance     Ed25519 sign-on-write / verify-on-pull (roster)    (transport.rs verify_provenance)
  L2  replication    have/want -> verified pull -> converge             (lib.rs pull/accept, transport.rs)
  L1  addressing     addr = sha256(norm(body))[:16]  OR  C2-sig(episode)(lib.rs norm/addr_of/classify)
  L0  transport      QUIC (quinn/rustls TLS1.3) + Ed25519 mutual auth   (transport.rs)  [feature `transport`]
  ---------------------------------------------------------------------------------------------
  substrate          MEM-OKF store (full/<addr>.md + sum/ + LUT.md)     (tools/okf_mem.py)
```

Governing law (ADR-002): decide in latent, execute in clean text, **never fuse** — the mesh moves *curated records*, never raw latent geometry (TELE-12: fused latent = 0.000; latents don't port across nodes). Each node re-embeds locally.

## 2. The Rust crate — `tools/sp_swarm` (engine repo)

Standalone crate, an *optional* `swarm`-feature dep of `sp-daemon` (keeps `rust-libp2p`/`tokio` out of the lean byte-exact/CUDA build). Cross-language byte-compatible with the Python prototype (`shannon-prime-lattice/tools/swarm_sync.py` + `swarm_provenance.py`).

| module | role | key items |
|---|---|---|
| `lib.rs` (always) | L1+L2 core, pure std | `norm`, `addr_of`, `parse_fm`, `classify`→`Class{Content,C2,Bad}`, `verify_provenance`, `accept`, `have`, `pull` |
| `similarity.rs` (always) | L4 index, pure std | `Sig=[u64;4]`, `hamming`, `agree`, `C2Index{insert,find_similar}`, `sig_{to,from}_hex`, `index_store` |
| `transport.rs` (feature `transport`) | L0 QUIC + L3 auth + orchestration | `Identity`, `Roster`, `bind`, `serve`, `pull_from`, `discover_similar`, `run_node`, `NodeConfig`, `load_or_create_identity`, `load_roster` |
| `bin/sp_swarm_node.rs` (feature `transport`) | deployable headless node | env-configured `run_node` |

Build/test: `cargo test -p sp-swarm --features transport` (from `tools/sp_swarm`).

## 3. L1 — Content addressing (two classes)

- `norm(body) = body.replace("\r\n","\n").trim() + "\n"` — canonical (Python-parity; **normalize line endings on read** or cross-platform addresses mismatch, `G-SWARM-RUST-PARITY`).
- `addr_of(body) = sha256(norm(body))[..16]` (16 hex).
- **Two address classes** (`classify`): **Content** (agent facts, `addr == addr_of(body)` — tamper-evident by re-hash) and **C2** (XBAR/NIGHTSHIFT episodes, `addr == 256-bit C2 SimHash` via `--addr`, self-consistent frontmatter; tamper-evidence deferred to L3). A correct replicator MUST handle both.

## 4. L2 — Replication (have/want)

- `have(root) -> HashSet<addr>`; `pull(remote, local, addrs, roster) -> (pulled, rejected)` — verifies each object **on arrival** via `accept` (L1 class + optional L3 provenance) **before writing**; a tampered/forged/unrostered object is rejected, never committed.
- Convergence: bidirectional pull → both nodes hold the union, byte-identical, idempotent (`G-SWARM-REPLICATE-CONVERGE`).

## 5. L3 — Provenance (Ed25519, audited: ed25519-dalek / libsodium-pynacl parity)

- Sign-on-write over `signing_payload(addr, body) = "{addr}\n" ++ norm(body)`; signature in frontmatter (`mem_signer`, `mem_sig`), **address-preserving**.
- `verify_provenance(addr, fm, body, roster) -> Ok | Err(Reject)` — `Reject∈{Unsigned, UntrustedSigner, SigInvalid, IntegrityFail}`. Makes C2 episodes tamper-evident cross-node (`G-SWARM-PROVENANCE-ED25519`).
- `Roster = HashMap<node_id, VerifyingKey>` (invite-only). Identity is Ed25519; `load_or_create_identity` persists a 32-byte seed (the daemon's own node key is ephemeral — do not use it for the roster).

## 6. L0 — Transport (QUIC + Ed25519 mutual roster handshake)

QUIC (quinn 0.11 + rustls 0.23/ring, reused from `sp_daemon::network::quic_shard`) = TLS 1.3 encrypted channel (X25519 / ChaCha20-Poly1305 / AES-GCM). **Not rust-libp2p** — the engine already owns this transport; libp2p DHT/gossipsub are overkill for a closed invite-list (design §2 allows "libp2p noise OR a WireGuard mesh").

Wire protocol — length-prefixed (`u32 LE len ++ payload`) messages on one authenticated QUIC bi-stream:
1. **Ed25519 mutual auth** — each side signs the other's 32-byte nonce; an unrostered `node_id` or bad signature is dropped before any object moves.
2. Commands: `LIST` → have-set; `GET:<addr>` → object bytes (or `MISS`); `SIM:<c2_hex>:<k>` → top-k C2 candidates (`addr hamming`/line); `DONE`.

Client entry points: `pull_from(server, me, roster, local)` (L2 sync), `discover_similar(server, me, roster, query_sig, k, local)` (L4). Server: `serve(endpoint, me, roster, root)`.

## 7. L4 — Discovery (C2-SimHash overlay — a HINT, not a judge)

- `C2Index::find_similar(sig, k)` ranks stored `mem_c2` sigs by 256-bit Hamming (`== recall::agree`).
- `discover_similar` ships a query sig, gets the peer's top-k shortlist, then **exact-fetches + verifies** (L1+L2+L3) any missing addrs — a wrong hint costs only bandwidth (`G-SWARM-GOSSIP-DISCOVERY`).
- **Honest scope (measured, `G-SWARM-C2-SEMANTIC`):** C2-256 is a **shortlist**, not a top-1 oracle — recall@1 0.607 vs L5-cosine 0.885, but **recall@5 0.885** = cosine's top-1. Use **k≥5** and let the exact-fetch confirm. Bit-count is the lever (2048-bit ≈ cosine) if top-1 discovery is ever needed; 256 is the default.

## 8. Environment flags (daemon + node)

| flag | default | meaning |
|---|---|---|
| `SP_SWARM` | unset | `=1` spawns the mesh (daemon). Unset = no-op null floor. |
| `SP_SWARM_PORT` | `7777` | QUIC listen port (its OWN port, separate from the garner `--quic-port`). |
| `SP_SWARM_KEY` | `swarm.key` | persistent Ed25519 seed file (created on first run). |
| `SP_SWARM_ROSTER` | `roster.txt` | invite-only roster: `node_id <ed25519_pubkey_hex>` per line (`#` comments). |
| `SP_SWARM_NODE_ID` | `node` | this node's roster key. |
| `SP_SWARM_PEERS` | (empty) | comma-separated peer addrs to pull from (`host2:7777,host3:7777`). |
| `SP_SWARM_ROOT` | ← `SP_OKF_ROOT` → `memory-okf` | MEM-OKF store dir to replicate. |
| `SP_SWARM_INTERVAL_S` | `30` | pull cadence (seconds). |

## 9. Deployment shapes

- **In the daemon** (`--features swarm`): `SP_SWARM=1` → `sp_daemon::swarm::spawn_if_enabled()` runs `run_node` alongside the served 12B (`G-SWARM-DAEMON-WIRE`). Default-off.
- **Standalone** headless replication peer (no 12B): `sp-swarm-node` binary (same env flags).
- **Orchestration** `run_node(id, roster, NodeConfig{listen, peers, root, interval})` = serve + periodic verified pull (`G-SWARM-NODE`).

## 10. Gate index

| gate | proves |
|---|---|
| `G-SWARM-REPLICATE-CONVERGE` | L1 addr round-trip + L2 have/want convergence + verify-on-arrival + idempotence + tamper-reject |
| `G-SWARM-PROVENANCE-ED25519` | L3 sign/verify vs roster; tampered/stripped/forged/unrostered all rejected; C2 episodes tamper-evident |
| `G-SWARM-RUST-PARITY` | Rust ↔ Python byte-parity (sha2==addr, ed25519-dalek verifies pynacl sig); CRLF interop fix |
| `G-SWARM-TRANSPORT-QUIC` | L0 QUIC + Ed25519 roster: bidirectional convergence, tamper-reject, off-roster reject |
| `G-SWARM-NODE` / `G-SWARM-DAEMON-WIRE` | run_node autonomous sync converges; sp-daemon builds+links with `--features swarm` |
| `G-SWARM-C2-INDEX` / `G-SWARM-C2-SEMANTIC` | index top-k Hamming mechanics; C2 recall (shortlist 0.885 / top-1 0.607) |
| `G-SWARM-GOSSIP-DISCOVERY` | C2 shortlist gossip → exact-fetch verify → converge; off-roster rejected |

Receipts: `shannon-prime-system-engine/tests/fixtures/swarm/*.log`.

## 11. Turnkey config

`roster.txt`:
```
# invite-only roster: node_id <ed25519 pubkey hex>
laptop   3a107bff3ce10be...   # (printed by sp-swarm-node / the daemon log on first run)
desktop  9f2c...
```
Run (daemon): `SP_SWARM=1 SP_SWARM_NODE_ID=laptop SP_SWARM_PORT=7777 SP_SWARM_KEY=swarm.key SP_SWARM_ROSTER=roster.txt SP_SWARM_PEERS=desktop.local:7777 SP_OKF_ROOT=memory-okf sp-daemon start ...` (built `--features wire_cuda_backend,swarm`).
Run (standalone): same env, `sp-swarm-node`.

## 12. Status & what's left

**L0–L4 complete + daemon-integrated + gated, default-off.** The one remaining item is **deployment, not invention**: multi-HOST bring-up (real NICs / NAT / firewall) — everything localhost can prove is GREEN. Optional future: L4 semantic quality at wider bit-counts; peer discovery only if the mesh outgrows a static invite-list.

## Cross-links
- Design + rejected mechanics: [PPT-LAT-DESIGN-SWARM-MEMORY-MESH.md](PPT-LAT-DESIGN-SWARM-MEMORY-MESH.md)
- Measured recall/levers: [PPT-LAT-FINDINGS-LEDGER.md](PPT-LAT-FINDINGS-LEDGER.md)
- Governing law: [PPT-LAT-ADR-002-DECIDE-EXECUTE-SPINE.md](PPT-LAT-ADR-002-DECIDE-EXECUTE-SPINE.md)
- Verified status: [VERIFIED-SCOREBOARD.md](VERIFIED-SCOREBOARD.md)
- Store spec: [MEMORY-OKF-PROFILE.md](MEMORY-OKF-PROFILE.md)
