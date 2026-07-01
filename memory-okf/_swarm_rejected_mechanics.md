# SP-SWARM distributed layer — rejected mechanics (do NOT resurrect)

**When the "swarm / DHT / decentralized memory" idea comes back, the design is `papers/PPT-LAT-DESIGN-SWARM-MEMORY-MESH.md` (SP-SWARM). Do NOT re-derive the broken parts below — they were pulled apart and banked.**

The sound design: private invite-only authenticated mesh (libp2p noise / X25519 / Ed25519 / ChaCha20-Poly1305), content-addressed by **byte-exact SHA over existing MEM-OKF objects**, content-addressed pull replication, Ed25519 provenance signatures, **C2 256-bit SimHash as a similarity OVERLAY (not the DHT routing metric)**, and **curated records cross the wire, NOT raw latent geometry** (re-embed locally).

## Rejected (with the killing reason)
1. **CRT "poison pill"** `R*=(R+gⁱ) mod P`: home-rolled additive stream cipher; keystream = powers of a primitive root → recoverable from 2 consecutive values (`g = N_{i+1}·N_i⁻¹`). AND encrypted data does NOT poison a training run — it's discarded/filtered; Garner-amplified `v₃·P₁·P₂` noise is max-magnitude outliers = easiest thing to filter. Deliberate sabotage payloads = legal liability pointed at US. → Replace with AEAD + closed membership + Ed25519 provenance.
2. **Diffie-Hellman over a 21-bit (Proth) prime**: broken by baby-step/giant-step in ~2^10.5 ops. NTT/arithmetic primes ≠ crypto groups (opposite size requirements). → Use X25519.
3. **"P1=structure, P2=semantic, P3=trap"**: CRT residues are residues of the SAME numbers; NOT a semantic partition. Same error as CRT-shards-numbers-not-experts (see dff07b41 + STATE line 121). → one canonical serialization, SHA-addressed.
4. **3 new 21-bit Proth primes**: forks the frozen proven q1=1073738753 / q2=1073732609 (u64-fitting, NTT-friendly, byte-exact-gated) for no arithmetic need. Arithmetic substrate ≠ crypto substrate. → keep frozen primes; crypto is separate + audited.
5. **Latent challenge-response as an AUTHENTICATOR**: gates on compute not identity (anyone with public weights passes); deterministic on public weights → replayable; forward-pass is expensive to verify too → bad PoW. → invite-only signed roster for identity.
6. **"Broadcast global-K/Q geometry" sync**: contradicts TELE-12 (fused-latent transmit = 0.000; sequential decide-on-text won) AND the last-token-global-Q-is-content-poor finding; latents don't port across context/model. → share curated MEM-OKF records, re-embed locally.

## What's genuinely reused (no new store invented)
MEM-OKF content-addressed store (exists) = object model; C2 SimHash (exists) = similarity index; byte-exact serialization (GREEN 69c0588) = deterministic content IDs; receipt ledger + canonical Garner order (M.4, PROVEN) = cross-node audit model; libp2p/X25519/Ed25519/ChaCha20-Poly1305 (off-the-shelf, audited) = transport/identity/confidentiality.
