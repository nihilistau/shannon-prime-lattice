---
type: design
title: "SP-SWARM — the private, content-addressed, signed memory mesh (the honest distributed layer)"
description: "The corrected distributed half of PPT-ARM-LAT. Resurrects the swarm as a private authenticated mesh over audited crypto (libp2p/X25519/AEAD), with content-addressing by byte-exact SHA over existing MEM-OKF objects, content-addressed replication, Ed25519 provenance, and C2 SimHash as a similarity OVERLAY (not the DHT routing metric). Records cross the wire, not raw latent geometry (per TELE-12 + the last-token-global-Q content-poverty finding). Replaces the rejected 'C2-Kademlia + CRT poison-pill + field-crypto DH + 3-prime fork' proposal, whose failures are banked here as honest-negatives so they do not return."
tags: [design, swarm, dht, distributed, memory, mem-okf, c2, byte-exact, provenance, crypto, honest-negative, anti-rebuild]
timestamp: 2026-07-01T00:00:00Z
resource: shannon-prime-lattice/papers/PPT-LAT-DESIGN-SWARM-MEMORY-MESH.md
sp_status: DESIGN
sp_gate: "none yet — blueprint; if built, gated on content-address round-trip byte-identity + roster-auth + replication convergence, never on the single-node organism"
sp_commit: TBD
sp_repro: "n/a (design). Reuses proven: byte-exact G-BYTEEXACT-FORWARD-12B (engine 69c0588); MEM-OKF verify (python tools/okf_mem.py verify --root memory-okf); receipt-ledger canonical Garner order (M.4)"
---

# SP-SWARM — the honest distributed memory layer

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
