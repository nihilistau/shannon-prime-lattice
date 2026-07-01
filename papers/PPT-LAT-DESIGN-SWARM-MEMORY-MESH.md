---
type: design
title: "SP-SWARM — the private, content-addressed, signed memory mesh (the honest distributed layer)"
description: "The corrected distributed half of PPT-ARM-LAT. Resurrects the swarm as a private authenticated mesh over audited crypto (libp2p/X25519/AEAD), with content-addressing by byte-exact SHA over existing MEM-OKF objects, content-addressed replication, Ed25519 provenance, and C2 SimHash as a similarity OVERLAY (not the DHT routing metric). Records cross the wire, not raw latent geometry (per TELE-12 + the last-token-global-Q content-poverty finding). Replaces the rejected 'C2-Kademlia + CRT poison-pill + field-crypto DH + 3-prime fork' proposal, whose failures are banked here as honest-negatives so they do not return."
tags: [design, swarm, dht, distributed, memory, mem-okf, c2, byte-exact, provenance, crypto, honest-negative, anti-rebuild]
timestamp: 2026-07-01T00:00:00Z
resource: shannon-prime-lattice/papers/PPT-LAT-DESIGN-SWARM-MEMORY-MESH.md
sp_status: DESIGN
sp_gate: "L2-core GREEN: G-SWARM-REPLICATE-CONVERGE (content-address round-trip + have/want convergence + verify-on-arrival + tamper-reject). L0 transport (libp2p/Noise/Ed25519) + roster-auth still DESIGN."sp_gate: "none yet — blueprint; if built, gated on content-address round-trip byte-identity + roster-auth + replication convergence, never on the single-node organism"
sp_commit: TBD
sp_repro: "n/a (design). Reuses proven: byte-exact G-BYTEEXACT-FORWARD-12B (engine 69c0588); MEM-OKF verify (python tools/okf_mem.py verify --root memory-okf); receipt-ledger canonical Garner order (M.4)"
---

# SP-SWARM — the honest distributed memory layer

> **STATUS (2026-07-01): RE-ELEVATED to a PRIMARY forward axis** alongside ADR-002 (the Decide→Execute spine). The single-node faithfulness axis is now closed end-to-end, so the distributed memory mesh becomes a primary goal. Still `DESIGN` (unbuilt) — this is the blueprint; the build gates are in the frontmatter.

## Context — what this fixes

The distributed half of PPT-ARM-LAT (the swarm / DHT) was deferred to harden the single-node organism (Telepathy, local memory, byte-exact forward, agency). A proposal arrived to resurrect it as **C2-Kademlia routing + a CRT "poison-pill" payload + Diffie-Hellman over the arithmetic primes + a 3-Proth-prime fork + latent-geometry broadcast**. That proposal was pulled apart: two kernels are sound, the security core is broken, and it silently re-commits the *CRT-shards-numbers-not-experts* category error corrected in [STATE](PPT-LAT-STATE.md) §4 (line 121). This doc keeps the sound kernels, replaces every rolled primitive with audited crypto, reuses proven Shannon-Prime assets, respects our own proven negatives, and scopes the threat model honestly. The rejected mechanics are banked in §7 so they cannot creep back a second time.

**Threat model, stated up front (this is what most of the fix turns on):** a **private mesh of the operator's own nodes plus explicitly invited peers** — NOT an open public P2P network. Once membership is authenticated and closed, Sybil resistance, anonymous-crawler defense, and the entire "economic trap" apparatus fall out of scope by construction. You do not need to defend an open buffet if you never lay one out.

## 1. The reframe (the anti-rebuild insight)

A swarm of the operator's nodes sharing memory is **replication of a content-addressed store** — a solved problem (git, IPFS, Dat/Hypercore, Syncthing). And we **already have the store**: **MEM-OKF** (`tools/okf_mem.py` + `memory-okf/`), a content-addressed LUT→summary→full knowledge store with SHA addresses. So the "DHT" is not a new database to invent — it is a **replication + discovery transport over existing MEM-OKF objects.** Don't build a store; sync the one we have.

## 2. L0 — Transport & membership (audited crypto, never rolled)

- **Encrypted, authenticated transport:** libp2p **noise** (or a WireGuard mesh). Key agreement **X25519**, payloads **AEAD (ChaCha20-Poly1305)**. No bespoke finite-field cipher anywhere.
- **Membership is invite-only:** a peer joins only when an existing member signs its **Ed25519** identity into the roster. The mesh is a closed, authenticated set of nodes.
- **Why not the proposed field-crypto:** Diffie-Hellman over a 21-bit Proth prime is broken — baby-step/giant-step recovers the exponent in ~2¹⁰·⁵ ops (microseconds). **NTT primes and cryptographic groups have opposite size requirements** (small-and-register-fast vs large-enough-to-be-infeasible); you cannot serve both from one modulus. The frozen arithmetic primes stay arithmetic-only.

## 3. L1 — Content addressing (byte-exactness is the real CRT gift)

- **Object address = SHA-256 of the object's canonical byte-exact serialization.** Byte-exact inference is already GREEN (`G-BYTEEXACT-FORWARD-12B`, engine `69c0588`): cross-machine **bit-identical** bytes. So two honest nodes independently serialize the same memory to the **same bytes → the same address** — a genuine, independently *verifiable* content ID.
- **This is what CRT / Garner is actually for here:** deterministic, auditable identity and integrity — **not** a cipher. The address discipline is the existing MEM-OKF LUT key, extended across nodes.

## 4. L2 — Replication (content-addressed pull, the boring correct pattern)

- **have/want gossip:** peers exchange the sets of object **addresses** they hold; each fetches what it's missing; each **verifies by re-hashing** on arrival. (git/IPFS pattern — audited, dull, correct.)
- **Cross-node trust/audit is the ledger we already proved:** the append-only **receipt ledger + canonical Garner order** (M.4 PoUW, PROVEN-per-record — "two devices holding the same receipt set in a canonical order"). The swarm's integrity model is that ledger, not a poison pill.

## 5. L3 — Provenance & attribution (sign, don't sabotage)

- **Every object is Ed25519-signed by its originating node.** Authorship becomes cryptographically attributable — the legitimate, effective form of "attribution protection."
- **Confidentiality = encryption at rest + in transit + closed membership.** There is simply no public surface to scrape. You cannot both publish data in the open and prevent it being read; the honest move is not to publish it in the open.
- **(Optional, separate, honest):** a robust *statistical text watermark* in **generated output** for provenance is a real technique — scoped as its own project, explicitly NOT an "adversarial-gradient bomb" (see §7).

## 6. L4 — Semantic discovery (C2 done right: an overlay, not the routing metric)

- **C2 256-bit SimHash** (sign of the ±1 Rademacher projection of `global-K` — real, we own it) is a **similarity secondary index**, not the DHT routing key.
- Nodes **advertise the C2 set** they hold; a similarity query computes its own C2 and asks peers for **low-Hamming-distance** matches as a **hint**, then confirms by exact content fetch (L1).
- **Correctness caveats (why C2 is an overlay, not "Kademlia"):** Kademlia routes by **XOR distance, not Hamming** (different metric, different topology), and its routing/load-balance guarantees assume **uniformly random keys** — while C2 keys are deliberately *clustered*. So exact SHA addressing (L1) does the routing; C2 rides on top purely for "find similar," where a wrong hint costs nothing because the exact fetch verifies.

## 6.1 What crosses the wire (respecting our proven negatives)

**Curated MEM-OKF records travel — `{summary, full text, C2 signature, provenance signature, receipts}` — text + metadata, NOT raw latent geometry.** The receiving node **re-embeds the record locally** into its own latent.

Why, grounded in this project's own receipts: **TELE-12** proved fused-latent transmit = **0.000** (sequential decide-on-text won); and this session established the **last-token `global-K/Q` is content-poor**. Latent vectors are context- and model-dependent — they do not port across nodes/contexts/models. "Broadcast the geometry" re-proposes exactly the thing we falsified. Knowledge propagates as **portable curated records; latent stays local.**

## 7. Rejected mechanics (honest-negatives — do NOT resurrect)

| Proposed mechanic | Why it's rejected | What replaces it |
|---|---|---|
| **CRT "poison pill"** `R* = (R + gⁱ) mod P` | A home-rolled additive stream cipher whose keystream is powers of a primitive root: two consecutive values give `g = Nᵢ₊₁·Nᵢ⁻¹ mod P` → the whole stream unrolls. **And even if strong, encrypted data doesn't poison training** — it decodes to nothing usable and is discarded; the Garner-amplified `v₃·P₁·P₂` term produces max-magnitude outliers, the *easiest* thing any pipeline filters. Deliberate sabotage payloads aimed at third parties are a legal liability pointed at **us**. | AEAD confidentiality + closed membership + Ed25519 provenance (§2, §5). |
| **Diffie-Hellman over a 21-bit prime** | Broken: BSGS in ~2¹⁰·⁵ ops. Arithmetic (NTT) primes ≠ cryptographic groups — opposite size requirements. | **X25519** (§2). |
| **"P₁=structure, P₂=semantic, P₃=trap"** | CRT residues are residues of the **same numbers**; there is no semantic partition across moduli. Same category error as *CRT-shards-numbers-not-experts* ([STATE](PPT-LAT-STATE.md) line 121). | One canonical serialization, addressed by SHA (§3). |
| **3 new 21-bit Proth primes** | Forks the frozen, proven q1=1073738753 / q2=1073732609 (u64-fitting, NTT-friendly, byte-exact-gated) for no arithmetic need. Arithmetic substrate ≠ crypto substrate. | Keep the frozen primes; use audited crypto separately. |
| **Latent challenge-response as an *authenticator*** | Gates on **compute, not identity** (anyone with the source-available weights passes); deterministic on public weights → replayable; a forward pass is expensive to *verify* too → a poor PoW. Also re-imports geometry-transport (killed by TELE-12). | Invite-only **signed roster** for identity (§2); proof-of-inference left as unfunded research. |
| **"Broadcast `global-K/Q` geometry" sync** | TELE-12 fused-latent = 0.000; last-token-Q content-poor; latents don't port. | Share curated records, **re-embed locally** (§6.1). |

## 8. Scope & status

- **`sp_status: DESIGN` — this is a blueprint, not a build.** Nothing here opens the C-core or a crypto/networking crate.
- If pursued, it is a **separate, self-contained project** (libp2p + X25519/Ed25519 + MEM-OKF replication), gated on **its own** correctness — content-address round-trip byte-identity, roster authentication, replication convergence — **never** on the single-node organism (per the [STATE](PPT-LAT-STATE.md) §4 gating rule: a stage is gated on its own metric, never on assembled-system numbers).
- The single-node organism remains the proven asset; SP-SWARM **composes with it, does not block it.**

## 9. Anti-rebuild ledger — what this genuinely reuses (nothing new invented)

| Asset | Status | Role in SP-SWARM |
|---|---|---|
| MEM-OKF content-addressed store (`tools/okf_mem.py` + `memory-okf/`) | exists, verify-GREEN | the swarm's object model |
| C2 256-bit SimHash (±1 Rademacher on `global-K`) | exists | the L4 similarity index |
| Byte-exact serialization | GREEN (`69c0588`) | deterministic verifiable content IDs (L1) |
| Receipt ledger + canonical Garner order (M.4) | PROVEN-per-record | the cross-node audit/trust model (L2) |
| TELE-12 + last-token-Q findings | proven negatives | why records cross the wire, not geometry (§6.1) |
| libp2p / X25519 / Ed25519 / ChaCha20-Poly1305 | off-the-shelf, audited | transport, identity, confidentiality (L0) |

**The salvage from the original proposal is small and clean: C2 as a semantic content-address survives (as an overlay); everything offensive or rolled does not.**


## 9. Build status (2026-07-01) — L1+L2 core GREEN

The replication CORE is built and gated, transport-agnostic (zero crypto, zero network yet), over the REAL MEM-OKF store. Gate **G-SWARM-REPLICATE-CONVERGE** (`tools/swarm_sync.py` + `tools/g_swarm_converge.py`, receipt `tests/fixtures/swarm/G-SWARM-REPLICATE-CONVERGE.log`):

- **L1 content-address round-trip** — every content-addressed object re-hashes to its address; two "nodes" (store dirs) seeded divergently converge to the byte-identical union (113/113 byte-identical).
- **L2 have/want convergence** — bidirectional `manifest → want → verified pull`; both nodes reach the union; **idempotent** (re-sync pulls 0).
- **Verify-on-arrival + tamper-reject** — a tampered content object is REJECTED on pull (integrity-fail), never written → corruption/forgery cannot propagate.
- **GROUNDED FINDING (two address classes):** MEM-OKF holds **content-addressed** objects (agent facts, addr = sha256(norm(body))[:16] — strong, tamper-evident by re-hash) AND **C2-addressed** episodes (XBAR/NIGHTSHIFT, addr = the 256-bit C2 SimHash passed via `--addr` — body does NOT re-hash; integrity = self-consistency now, Ed25519 provenance at L3). A correct replicator MUST handle both (87 content + 26 c2 in the current store). This is why L1 verify is two-class.

**Transport seam:** `manifest / have / want / pull / sync` are transport-agnostic; the local two-dir `pull` (byte copy) is the loopback impl. **L0 (libp2p noise / X25519 / Ed25519 roster / ChaCha20-Poly1305) layers UNDER this seam** — it carries the have/want address sets + object bytes without touching the proven reconciliation logic. **L3 — Ed25519 provenance GREEN (2026-07-01).** `tools/swarm_provenance.py` (audited **libsodium/PyNaCl**, never a rolled signer): sign-on-write over `(addr || body)`, signature in the object frontmatter (`mem_signer`/`mem_sig`, address-preserving); `pull` verifies against an invite-only roster BEFORE commit. Gate **G-SWARM-PROVENANCE-ED25519** (receipt `tests/fixtures/swarm/G-SWARM-PROVENANCE-ED25519.log`): signed content + signed C2 episode commit; **tampered episode → sig-invalid** (the hole L1 left open, now closed), stripped → unsigned, forged → sig-invalid, unrostered-key → untrusted-signer, tampered-content → integrity-fail — ALL rejected before write. **C2-addressed episodes are now cryptographically tamper-evident cross-node.**

**Rust port (L0 prep) — GREEN (2026-07-01).** Standalone crate **`tools/sp_swarm`** in the engine workspace (decoupled; an *optional* `swarm`-feature dep of `sp-daemon`, so the heavy `rust-libp2p`/`tokio` tree never enters the lean byte-exact/CUDA build). Ported the proven L1/L2/L3 core to Rust (`sha2` addressing, `ed25519-dalek` provenance, `parse_fm`/`classify`/`pull`), byte-for-byte interoperable with the Python prototype. Gate **G-SWARM-RUST-PARITY** (`tests/parity.rs` vs a pynacl-signed fixture; receipt `tests/fixtures/swarm/G-SWARM-RUST-PARITY.log`, 6/6): Rust `sha2` reproduces every Python address (89 content re-hash), Rust `signing_payload` == the exact bytes Python signed, **`ed25519-dalek` verifies the libsodium/pynacl signature** (cross-lang crypto parity), tamper fails, roster rejects (unsigned/untrusted/forged). **CROSS-PLATFORM INTEROP FINDING (the gate caught it):** Python-on-Windows writes MEM-OKF files as **CRLF** but computes the address over the **LF**-normalized body (its text-mode read translates CRLF→LF); a Rust node's `read_to_string` keeps CRLF, so `parse_fm` must **normalize line endings on read** or every cross-node address mismatches. Fixed in `parse_fm` (normalize first).

**L0 — network transport GREEN (2026-07-01).** `tools/sp_swarm/src/transport.rs`, behind the `transport` feature. **Anti-rebuild deviation (justified):** built on the engine's PROVEN QUIC stack (`quinn` 0.11 + `rustls` 0.23/ring, reused verbatim from `tools/sp_daemon/src/network/quic_shard.rs`) **instead of rust-libp2p** — QUIC's TLS 1.3 IS the encrypted-authenticated channel §2 requires (X25519 / ChaCha20-Poly1305 / AES-GCM), it is already a dependency (no new tree), and libp2p's DHT/gossipsub are overkill for a *closed invite-only* mesh with known peer addresses (§2 explicitly allows "libp2p noise **or** a WireGuard mesh" — QUIC is the same class). Invite-only IDENTITY is an app-level **Ed25519 mutual challenge-response** over the encrypted stream (each peer signs the other's nonce; an unrostered `node_id` or bad signature is dropped before any object moves). have/want pull runs `accept` (L1+L2+L3) on every object BEFORE write. Gate **G-SWARM-TRANSPORT-QUIC** (2-node localhost, receipt `tests/fixtures/swarm/G-SWARM-TRANSPORT-QUIC.log`): A←B converge (pulled 3, tampered rejected on arrival), B←A converge (pulled 2, reverse direction), off-roster peer C rejected (connection dropped, 0 objects). Roster-auth + encrypted round-trip + bidirectional convergence + verify-on-arrival + invite-only reject — all GREEN.

**NEXT (mesh is now traffic-capable; remaining is integration + scale, none blocking the organism):** (1) wire `sp-swarm` into `sp-daemon` behind a `swarm` feature (reuse the existing `--quic-port` mesh hook + `SP_SWARM_ROSTER`); (2) multi-HOST test beyond loopback (real NICs, NAT); (3) peer discovery IF the mesh grows past a static invite-list (libp2p/gossipsub becomes worth it only then); (4) L4 C2-SimHash similarity overlay (advertise C2 sets, low-Hamming hints, exact-fetch confirm).**NEXT:** **L0 libp2p transport** — `rust-libp2p` noise / X25519 / ChaCha20-Poly1305 + the invite-only Ed25519 roster over the wire (request-response or gossipsub), behind the `transport` feature, carrying the have/want address sets + object bytes under the existing `manifest/have/want/pull/sync` seam. Gated on its own transport metrics (roster auth, encrypted round-trip, multi-node convergence), never on the single-node organism.**NEXT:** (1) **L0 libp2p transport** (noise / X25519 / ChaCha20-Poly1305) + the invite-only signed roster over the wire, under the existing `manifest/have/want/pull/sync` seam; (2) port the reconciliation + provenance to Rust (ed25519-dalek) for the daemon.**NEXT:** (1) L3 Ed25519 provenance signature over each object (makes C2 episodes tamper-evident cross-node); (2) L0 libp2p transport + invite-only signed roster; (3) port the reconciliation to Rust for the daemon.


## 10. Integration — wired into sp-daemon (2026-07-01) GREEN

The mesh is now integrated into the served daemon, default-off.

- **Reusable orchestration** `sp_swarm::transport::run_node` (serve + periodic pull + persistent identity + roster-file) — gate **G-SWARM-NODE** (`tests/fixtures/swarm/G-SWARM-NODE.log`): two nodes with divergent stores, autonomous periodic sync over QUIC, **converge 5/5 both directions**; persistent identity stable across reloads; roster file parsed.
- **Deployable node** `tools/sp_swarm/src/bin/sp_swarm_node.rs` (`sp-swarm-node`) — headless replication node (no 12B), env-configured, the standalone form of the integration.
- **Daemon wiring** — `sp-daemon` gains an optional `swarm` feature (`sp-swarm{transport}` dep) + `sp_daemon::swarm::spawn_if_enabled()` called in `run_inner` before the HTTP server. Gate **G-SWARM-DAEMON-WIRE**: `cargo build --features wire_cuda_backend,swarm` builds+links clean (19.33s). **Default-off:** `SP_SWARM` unset ⇒ no-op (null floor; daemon byte-identical to before). Runs on its OWN `SP_SWARM_PORT` (separate from the garner `--quic-port`), a PERSISTENT `SP_SWARM_KEY` identity (not the daemon's ephemeral node key), `SP_SWARM_ROSTER` invite list, replicating `SP_OKF_ROOT`.

**Config:** `SP_SWARM=1 SP_SWARM_PORT=7777 SP_SWARM_KEY=swarm.key SP_SWARM_ROSTER=roster.txt SP_SWARM_PEERS=host2:7777,host3:7777 SP_SWARM_INTERVAL_S=30` (roster line: `node_id <ed25519_pubkey_hex>`).

**Remaining (scale/discovery, none blocking):** multi-HOST test beyond loopback (real NICs/NAT); peer discovery only if the mesh grows past a static invite-list; L4 C2-SimHash similarity overlay.


## 11. L4 — C2-SimHash similarity overlay (2026-07-01): index GREEN, semantic = HINT-only

`sp_swarm::similarity` (pure std): a `C2Index` (addr→256-bit sig) + `find_similar(sig,k)` ranked by 256-bit Hamming (== `recall::agree`), built from `mem_c2` frontmatter; the engine computes the sigs via the proven `recall::Projection`. **Mechanics gate G-SWARM-C2-INDEX** GREEN (`tests/similarity.rs`): near ranks above far, exact match = Hamming 0, top-k monotone, hex round-trip.

**Semantic gate G-SWARM-C2-SEMANTIC** (`g_c2_semantic.py`, receipt `tests/fixtures/swarm/G-SWARM-C2-SEMANTIC.log`) — the honest measurement of whether C2-Hamming discovery tracks the proven L5-cosine signal, on the faithful corpus (61 paraphrase queries → nearest episode):

| index | recall@1 | recall@5 |
|---|---|---|
| L5-cosine (ground truth) | **0.885** | 0.984 |
| **C2 SimHash-256 (the overlay)** | **0.607** | **0.885** |
| SimHash-512 / 1024 / 2048 | 0.721 / 0.820 / 0.869 | 0.951 / 0.967 / 0.967 |

**Verdict (honest):** C2-256 is a **weak top-1 retriever** (retains only 69% of cosine recall@1) but an **excellent shortlist/hint** — its recall@5 (0.885) equals cosine's recall@1. This is *exactly* the role §6 scopes C2 for ("a wrong hint costs nothing because the exact fetch verifies"). So:
- **Expose `find_similar` as a top-k candidate SHORTLIST (default k≥5) that feeds L1/L2 exact-fetch confirmation — NOT as a standalone answer.** In that role the overlay is GREEN.
- **Do NOT** use C2-256 as a top-1 discovery oracle (honest-negative, retention 0.69).
- **Bit-count is the lever:** if top-1-grade discovery is ever needed, wider sigs recover it (2048-bit ≈ cosine). 256-bit stays the default (it's the frozen C2 width; the shortlist role doesn't need more).

**Network gossip discovery — GREEN (2026-07-01).** `sp_swarm::transport`: a `SIM:<c2_hex>:<k>` command on the authed QUIC stream returns the peer's top-k local C2 candidates ("addr hamming"); `discover_similar` ships a query sig, receives the shortlist, and **exact-fetches + verifies (`accept`, L1+L2+L3)** any addresses it lacks — a wrong hint costs only bandwidth. Gate **G-SWARM-GOSSIP-DISCOVERY** (`tests/gossip.rs`, receipt `tests/fixtures/swarm/G-SWARM-GOSSIP-DISCOVERY.log`): Node A discovers a memory held ONLY by Node B via the C2 shortlist, exact-fetches + verifies it, and converges — while decoys A already holds are NOT re-fetched, and an off-roster peer's discovery is rejected (connection dropped, 0 objects). Calibrated to the k≥5 shortlist regime the semantic gate justified.

**NEXT (deployment-only): multi-host bring-up** — the mesh is semantically complete (sync + provenance + discovery all gated on localhost); the one thing localhost can't prove is real-NIC/NAT/firewall topography. That's an operational exercise, not new invention.**NEXT:** wire the network `find_similar` gossip (advertise C2 sets, ask peers for low-Hamming candidates, exact-fetch confirm) over the have/want seam — calibrated to k≥5 shortlist semantics, gated on the shortlist recall above. Then multi-host bring-up.
