# RFC-001: The Shannon-Prime Universal Discrete Architecture

**Status:** DRAFT for review/critique/iteration (elevating from mobile PoC + per-arch cells to a generalized, formalized framework).
**Author:** Claude (SP hat), 2026-06-02, synthesizing operator intent + a Gemini RFC draft + the empirical record.
**Disposition:** This is a *constitution + contract skeleton*, not a decree. Every §ends with OPEN QUESTIONS. The next session is expected to fix, cut, and harden it. Nothing here supersedes a frozen spec until it is itself frozen.

> Reading rule (SP discipline): claims in this doc are tagged **[PROVEN]** (silicon/oracle-confirmed), **[DESIGN]** (sound but unbuilt), or **[SPECULATIVE]** (idea, not yet load-bearing). Do not let a [DESIGN] or [SPECULATIVE] drift into a [PROVEN] without a gate. This is the anti-amnesia fence.

---

## 0. What this project actually is (the one paragraph)

Shannon-Prime / PPT-ARM-LAT is **a discrete-integer (Z_q) substrate for transformer inference and continual learning**, whose product is *the math and its primitives*, not a speedup. A model is reduced to **one canonical discrete object (the O_K object)** carried at its true information content, from which **every backend (CPU AVX-512, CUDA PTX, Vulkan, Hexagon HVX, and any future island) computes bit-identical output**. Floating point is relegated to plumbing (routers, final temperature/softmax). The system's reason to exist is **composability, lossless portability, mesh-shareable continual learning, and heterogeneous-silicon parallelism** — *not* "NTT beats fp32." Everything must live in **bounded crates/engines** with frozen seams.

---

## 1. First principles (the constitution)

These are load-bearing invariants. Violating one is a bug, not a tradeoff.

1. **The math is the product.** Primitives (Barrett, Frobenius lift Q4/Q8, NTT-CRT, KSTE, VHT2/Spinor, Garner) are the deliverable. Models, backends, and the daemon are *consumers* of the primitive set.
2. **O_K one-object, zero fidelity loss.** A weight tensor has exactly one canonical discrete representation. No backend may hold a *different* numerical truth. Dequant-to-fp32 in RAM as a *storage* form is forbidden (the **zero-copy / zero-inflation invariant**). fp is allowed only as transient per-matmul *compute scratch* that is streamed, never persisted. **[PROVEN]** in the core forwards; **[DESIGN]** as a uniform cross-backend guarantee.
3. **Bit-exact composability is the gate, not speed.** The closure test for any backend/arch is *bit-identical output vs the reference* (greedy top-1 argmax for arch cells; byte-equal logits for backend cells), never a wall-clock number. **[PROVEN]** — gemma4 (M_GEMMA4), qwen35moe (M_QWEN36), hex↔ARM (WIRE-HEX-FINISH).
4. **fp is plumbing; Z_q is truth.** The substrate's value is *structural*, not per-op throughput. Discreteness buys exactness, compression, mesh-shareability, CRT-shardability, and PoUW verifiability. It does **not** buy "NTT faster than fp32 dot" at HD ≤ 256 — that claim is **empirically false** and must never be re-asserted (see §2).
5. **Bounded crates, frozen seams.** math-core (primitives) ▸ arena (O_K container) ▸ L1 ABI (the seam) ▸ backends ▸ L3 Rust daemon (orchestration). Each crate is replaceable behind its seam. No crate reaches across a seam. Anti-contamination is binding: this is a rewrite; never fall back to legacy SP repos.
6. **Surface upstream, never silently revise a gate.** If a primitive can't meet a spec'd gate, the spec is wrong or the silicon is — say so; do not tune fixtures until a number passes.

**The honest value-proposition list** (what the substrate IS load-bearing for — replaces the discredited "NTT is fast" story):
(a) **Composability** — bit-exact across CPU/CUDA/Vulkan/Hexagon and mesh peers. **[PROVEN]**
(b) **Compression** — Q4/Q8 + Frobenius lift, weights never inflated. **[PROVEN]**
(c) **Mesh-shareable continual learning** — Spinor receipts + canonical Garner order. **[PROVEN]** (receipt ABI) / **[DESIGN]** (load-time fusion).
(d) **Heterogeneous-SoC parallelism** — CRT-shard a matmul across K islands, Garner-recombine, no mid-compute sync (Trick #1). **[DESIGN]**, dispatch primitives **[PROVEN]**.
(e) **PoUW verification** — KSTE / Friedman-sieve integer fingerprints as proof-of-useful-work. **[PROVEN]** (encoder + ledger).

**OPEN QUESTIONS §1:** Is (d) a *first-class* pillar or an optimization? (Operator: load-bearing.) Should "bit-exact" relax to "bit-exact under fixed sampling+backend" as the formal definition (cf. lattice-decode-determinism preconditions)?

---

## 2. The substrate: Z_q and the cyclotomic ring R_q

**The container of all compute is the negacyclic polynomial ring** R_q = Z_q[X]/(X^N + 1). This is the *Universal Topography*: pin every op to this ring and an H100, an M4, and a Hexagon DSP produce the same bits. This framing (Gemini §1) is **correct** — and Gemini's own correction is correct too: **stop selling NTT as a faster matmul.**

Honest constraints that the framing MUST carry (these are [PROVEN] and have bitten us):
- **N ≤ 512 with the frozen primes.** Negacyclic NTT needs 2N | (q−1); both frozen primes have v₂(q−1)=10 → max N=512. N=1024+ is *mathematically impossible* without a Phase-5 prime change (cascades through every Garner constant + bit-identity gate). Long context ⇒ tiled N=512, or Bluestein for non-power-of-2 ≤ 512. Mixed-radix/Good-Thomas are invalid for the frozen primes. (ref: NTT frozen-prime cap.)
- **The NTT win is over HD (polynomial length), not ctx (attention count).** At HD ≤ 256, NTT-attention is *slower* than fp32 dot (~6× per dot at HD=64; measured 0.15–0.72× of fp32). The O(N log N) crossover doesn't arrive until HD ≳ 1024. For HD with odd factors (96/288/384), direct Barrett integer dot is the boring-correct answer. **Do not put NTT on the single-island latency path expecting a win.** (ref: ntt-substrate-win-is-over-HD-not-ctx.)
- **Where the ring earns its keep:** cross-backend *exactness* (the same NTT/Barrett gives the same bits everywhere), CRT-shardability, and *future* HD≥1024 / heavy-poly regimes — not today's chat-shape latency.

**OPEN QUESTIONS §2:** The cyclotomic-ring story deserves its own short paper (operator flagged the current treatment as thin). What is the *precise* boundary where ring-NTT beats Barrett-direct on each backend (it differs: HVX vrmpy vs AVX-512 VNNI vs CUDA dp4a)? Should N>512 be unblocked via a third prime now (Phase-5) or stay deferred?

---

## 3. The entropy-dense container (the O_K object) — operator's killer insight, SP-corrected

**The problem:** packing a 4.5-bit Q4_K weight into an 8-bit container pads it with zeros — a Shannon-bound violation. You pay 8 bits of storage/bandwidth for 4.5 bits of entropy.

**The resolution (and a correction to the RFC draft):**

- **On disk: keep the weight at its true entropy.** Q4_K stays Q4_K (~19 GB for the 35B). Do not expand to OK_Q8 on disk — that is *literally* the padding waste, and it is *also* what just disk-blocked the qwen35moe `.sp-model` (35 GB > free space). **[PROVEN constraint, this session.]**
- **In RAM/cache/VTCM: the container is an ALU adaptation, and spare bits carry DISTINCT, compute-useful information — never a redundant copy.** This is the entropy-reclamation principle.

**Correction to Gemini's "RNS split" (§3.1 of the draft):** storing `W mod p₁ | W mod p₂` for the *same* W in 8 bits is **not** entropy reclamation — it is the same 4.5 bits encoded twice in two bases (redundant, by CRT). RNS/CRT residue *packing of a single weight* buys nothing for storage. CRT is for (i) **widening the accumulator/intermediate modulus** during compute, or (ii) **sharding *different* data across islands** (§4) — not for duplicating one weight. The honest "fill the spare bits with useful SP math" options are those that carry **independent** information:
  - **(A) Interleaved scale [DESIGN, high value].** `low nibble = discrete weight`, `high nibble = local Z_q/Frobenius scale exponent`. One byte load yields weight *and* its block scale → halves the matmul's memory fetches (no separate scale-block fetch). This is real entropy use — the scale is distinct information.
  - **(B) Routing/topology metadata [DESIGN, MoE-specific].** For 256-expert MoE, pack expert-stride / sparsity bits so the DMA engine knows the next token's stride without a branch. Distinct info, real.
  - **(C) CRT-shard residue for a *different* island [DESIGN].** Only meaningful across Trick #1 — the byte carries this island's residue of *its* shard, not a copy.
  - **(D) Zeckendorf-sparse weight code [SPECULATIVE].** "No two consecutive 1s ⇒ fewer HVX ops" is weak — encode/decode cost likely dominates; needs a gate before it's load-bearing.

**The O_K object is defined as:** the canonical discrete weight + its provenance, stored at true entropy, with a documented *runtime expansion contract* per backend (how spare-bit metadata is injected in cache and masked before the ALU op). The mask cost MUST be measured — if masking eats the fetch savings, the scheme fails its gate.

**Immediate operating decision (affirming Gemini, corrected):** **lock the disk write to the source quant (Q4_K / OK_Q4), and move all entropy-dense container tricks into the runtime loader / cache-staging path** where we can actually exploit the spare bits without paying disk for them. The disk holds truth at min-entropy; the cache holds the ALU-adapted O_K object.

**OPEN QUESTIONS §3:** Does interleaved-scale (A) actually net-win after the per-element mask op on each backend (HVX `lop3`/`and`, AVX `vpand`, CUDA)? What is the `.sp-model` on-disk format for "min-entropy + runtime-expansion contract" (this needs a v1 format spec)? Is OK_Q4 (vs OK_Q8) the right default disk form for all archs now?

---

## 4. Generalized heterogeneous compute (Trick #1, off the phone)

Abstract the S22 into **K Compute Islands** (CPU-AVX, NPU, GPU, DSP, FPGA, mesh peer). The orchestrator detects islands and shards by **co-prime moduli** q₁…q_k; each island computes its residue in isolation; ARM/host **Garner-recombines**; no cross-island sync until recombination. Wall-clock win = **parallel silicon utilization**, not per-op NTT (§2). **[DESIGN]**; the cDSP `mod_q` matmul + NPU INT dispatch + Garner constants are each **[PROVEN]** in isolation; the *combination* is the unbuilt proof (Sprint TRICK-1).

- **Stateless collision-free partition via Beatty/φ [DESIGN, bounded].** A φ-driven Beatty partition (`⌊nφ⌋`, `⌊nφ²⌋`) cleaves an integer address/task space into two sequences that *provably never collide* (Rayleigh), with zero lookup state. Legitimate use: KV-block / expert / task routing across islands without a lock table. **Boundary:** CRT already gives collision-free *residue* split; Beatty is for *address/task* partition — a different layer. Don't conflate them. (ref: sp-uses-phi-extensively — SP already uses φ in Fibonacci-Prime DHT, KV sub-sampling, RoPE-φ, Halton; this generalizes those, it does not invent them.)
- **Activation quantization is part of the contract** (Gemini's tweak #1, correct): both DSP and NPU want integer inputs; the host dynamically quantizes fp32 activations → int8, and the Garner-recombined integer is dequantized by `weight_scale × activation_scale`. Missing the combined scale ⇒ instant numerical-equivalence failure.
- **Numerical-equivalence is the critical gate**, not parallel-win. Trick #1 must match the fp32 reference within Q8 rounding; a deviation means a Garner/sign/scale bug. Parallel-win can fail honestly (NPU init-dominated) without invalidating the pattern.

**OPEN QUESTIONS §4:** Should the "ARM Garner library" be promoted into the L1 ABI as a first-class recombination service backends compose against? Is 2-prime the ceiling, or do we want k-prime island scaling (q₁ DSP, q₂ NPU, q₃ GPU)? How does the mesh (remote peer as an "island") fold into the same Garner formula (the recursive-CRT-mesh trick)?

---

## 5. MTP as a system pillar (not a bolt-on) — SP-corrected

**Reality anchor:** qwen35moe carries a NextN/MTP decoder block (loaded-not-run in the base forward); the `-Draft` GGUF is the speculative pairing. **[PROVEN]** (this session: the MTP block tensors + the spec exist).

**Correction to Gemini's "parallel roots of a polynomial" framing:** that is poetic but not how MTP works. MTP = **draft-then-verify speculative decode**, made *exact* by the discrete substrate. The SP-specific integration (this is the real, defensible framing):
- **Draft head** = the NextN block (or the smaller Draft model), proposing K future tokens cheaply.
- **Target verify** = one batched forward over the drafted block (the cost MTP amortizes).
- **Deterministic, byte-exact accept/reject** — because draft and target both live in Z_q, acceptance is *exact token-id equality*, not a probability ratio. No sampling-temperature ambiguity on the accept path.
- **Transactional rewind via Spinor blocks** — a rejected speculation rolls back the KV/state to the last committed Spinor receipt, byte-exactly. This is where MTP *needs* the substrate: the rewind is lossless and verifiable. **[DESIGN]**, Spinor ABI **[PROVEN]**.
- **System placement:** MTP is not a decode-loop hack; it is a **transaction protocol** in the L3 daemon (propose → verify → commit/rollback) with the Spinor ledger as the journal. Phase 4-MTP.

**OPEN QUESTIONS §5:** Does the accept gate stay byte-exact under temperature>0 (probably needs a discretized-sampling contract)? Is the draft a separate model or the in-model NextN head as the default? How does MTP compose with Trick #1 (draft on island A while target verifies on islands B/C)?

---

## 6. MeMo as a system pillar — memory + continual learning, SP-corrected

Operator intent: **MeMo is core, "memo as memory is important," and with MTP, Phase-4-SPEC is redundant.** **[PROVEN intent]**, elevated to core in the roadmap.

Two layers, both first-class:
- **(i) Memory (retrieval + portable profiles).** A user's memory is a localized set of facts/context + **a set of discrete Z_q additive offsets** ("Spinor receipts") that are *algebraically fused at Frobenius-lift load time*. Because additive deltas in Z_q **commute and associate**, a memory profile is order-independent and **peer-shareable byte-exactly** (mesh-portable). This is the elegant, defensible core. **[DESIGN]** (load-time fusion) / **[PROVEN]** (receipt ABI, canonical Garner order, mesh determinism).
- **(ii) Continual learning without gradient drift.** Traditional LoRA/SFT is continuous gradient drift — it destroys bit-exactness. MeMo replaces it with **append-only algebraic receipts**: the base frozen Z_q weights never change; learning = accumulating commutative integer deltas + a PoUW ledger entry for provenance. **[DESIGN]**, ledger **[PROVEN]** (M.4).

**Honest caveat:** "learning = matrix addition in Z_q" is clean *only if* the update genuinely decomposes into an additive low-rank Z_q delta. Whether a useful continual-learning signal can be captured purely as commutative additive receipts (vs. needing a non-commutative composition) is an **open research question** — flag as [SPECULATIVE] until a gate shows a real task improving via fused receipts with bit-exact reproducibility.

**OPEN QUESTIONS §6:** What is the receipt format (delta-rank, scale, provenance hash) as a frozen contract? Does fusion happen at load (Frobenius stage) or as a runtime overlay (cf. the KSTE-KV overlay)? How does MeMo relate to the two-tier working-memory/ledger pattern (CLAUDE.md + memory/ dir) at the *agent* level vs the *model* level — are they the same mechanism or analogues?

---

## 7. The φ / Wythoff / Beatty / Zeckendorf / Stern-Brocot machinery — precise roles

Operator intuition is right that this bridges rationals↔irrationals inside an integer-only engine. SP-hat discipline: **assign each tool a bounded, gated role; fence against "a solution looking for a problem"** (operator's own earlier instinct). Anchor: SP *already* uses φ extensively (Fibonacci-Prime DHT, KV sub-sampling `⌊k·φ·N⌋`, RoPE-φ, Halton/Sobol). This section *organizes* that, it does not invent it.

| Tool | Role in the lattice | Status |
|---|---|---|
| **Stern-Brocot / Fibonacci convergents of φ** | Integer-only approximation of irrational scale constants on islands with no fp (cDSP). Use `F_{n+1}/F_n` instead of a float. | [DESIGN] real |
| **Beatty / Rayleigh partition (φ, φ²)** | Stateless, collision-free address/task/expert sharding across islands & KV blocks (§4). | [DESIGN] real |
| **Zeckendorf (base-φ integer rep)** | Sparse weight/index encoding (no consecutive 1s). | [SPECULATIVE] — needs a gate; encode/decode cost may dominate |
| **Continued-fraction of φ = [1;1,1,…]** | Why φ is the *maximally irrational* hub ⇒ best worst-case equidistribution for QMC sampling / sub-sampling. | [DESIGN] (already in Halton/Sobol upgrade) |

**Rule:** any φ-construct entering a hot path must show a *measured* win vs the boring integer alternative, or it stays a [SPECULATIVE] note. The golden ratio is a beautiful hub; it is not a free lunch.

**OPEN QUESTIONS §7:** Which of these is load-bearing *now* (Beatty-sharding for Trick #1 routing is the strongest candidate) vs. parked research? Does the Fibonacci-Prime DHT already subsume the "Beatty routing" need, or are they distinct?

---

## 8. Crate / engine boundaries (the bounded-engine contract)

```
┌ math-core (C) ── PRIMITIVES: Barrett, Frobenius lift Q4/Q8, NTT-CRT (N≤512),
│                  KSTE, VHT2/Spinor, Garner. The reference forward = validation oracle.
│                  Property: bit-exact, no backend/arena coupling. THE product.
├ arena (C) ───── the O_K object: packed Q4/Q8 + Frobenius scales; the runtime
│                  entropy-dense container (§3); zero-inflation invariant.
├ .sp-model (fmt) ─ on-disk min-entropy form + runtime-expansion contract + arch_struct
│                  (sp_arch_info, 256-byte reserved tail, grows w/o format bump).
├ L1 ABI (frozen) ─ the seam: sp_model_load/unload, sp_session_*, the forward entrypoint,
│                  arch-query, and (PROPOSED) the Garner recombination service (§4).
├ backends ─────── CPU AVX-512 (VNNI), CUDA (dp4a/PTX), Vulkan, Hexagon (vrmpy/HVX).
│                  CONTRACT: same primitive set, same packed weights, BIT-EXACT output.
│                  Current gap: per-backend forward *shells* call scalar f32, not the
│                  silicon-confirmed integer primitives (the WIRE-* sprints close this).
└ L3 daemon (Rust) ─ orchestration ONLY: parse .sp-model, island detection + Beatty
                   dispatch, MTP transaction protocol, MeMo ledger, mesh/QUIC peering,
                   Garner recombination. Safety + layout + scheduling. No math truth here.
```

**The single most important current gap (cross-track, [PROVEN diagnosis]):** *the primitives exist; the per-platform forward shells don't call them.* `sp_hex_forward` (and the CPU/CUDA/Vulkan analogues) are scalar-f32 placeholders. The `WIRE-*` sprints replace those calls with the silicon-confirmed integer kernels. HX.3b already did this for Hexagon (vrmpy) and flipped 3.63× slower → 1.04× faster than ARM fp32 — **the project-central proof that the integer substrate matches/beats fp32 on real silicon.** **[PROVEN, reported]**. The same template applies to AVX-512 (VNNI), CUDA, Vulkan.

**OPEN QUESTIONS §8:** Should `sp_model_to_<arch>` bridges + the arena-expert path be unified so a new arch is "add a forward + a transcode classifier" with everything else generic? Is the Garner service in-ABI or a Rust-only orchestration concern?

---

## 9. Honest scorecard (no spin)

**Proven (oracle / silicon):**
- Core reference forwards bit-exact to llama.cpp: Qwen3, Qwen2.5, Gemma3, **Gemma4** (M_GEMMA4), **qwen35moe / Qwen3.6-35B-A3B** (M_QWEN36 top-1) — this session.
- NTT-CRT host dual-prime byte-exact; Frobenius Q4/Q8 + arena; KSTE + Friedman sieve; Spinor receipt ABI (silicon-confirmed); M.4 PoUW ledger + mesh canonical order; L3 daemon (chat/dialogue/ledger/QUIC).
- Hexagon HVX: Barrett, mod_q matmul, NTT.0–5c, Bluestein; **HX.3b vrmpy 1.04× faster than ARM fp32, byte-equal** (reported).
- Cross-backend determinism (ARM ↔ cDSP scalar) bit-exact.

**Real gaps / blockers (honest):**
- **The WIRE gap:** CPU/CUDA/Vulkan forward shells still call scalar f32, not the primitives (HX.3b done for Hexagon; AVX/CUDA/Vulkan pending).
- **Integer-end-to-end:** arena still dequantizes Q4/Q8→fp32 before matmul on most paths; the true Z_q `mod_q`-all-the-way path (only logits dequant) is v2.
- **qwen35moe `.sp-model`:** OK_Q8 transcode disk-blocked (35 GB > free); the bridge + arena-expert path + OK_Q4 are the remainder (forward correctness already gated GGUF-direct).
- **NTT N≤512** frozen-prime cap; **NTT-not-faster-than-fp32 at HD≤256** (structural, not a bug).
- **Trick #1, MTP, MeMo continual-learning, entropy-container** are all [DESIGN]/[SPECULATIVE] — sound, unbuilt, ungated.

---

## 10. Where this design breaks (the part Gemini's RFC under-weighted)

1. **Entropy-container mask cost.** If injecting interleaved-scale/routing into spare bits costs an ALU mask per element, it can erase the fetch savings. Gate it per backend or it's theater.
2. **MeMo additive-only assumption.** If useful continual learning is *not* expressible as commutative Z_q additive receipts, the elegant load-time-fusion story collapses to needing ordered/non-commutative composition. Unproven.
3. **Trick #1 init-cost & precision.** NPU per-process init (~130 ms) can dominate; INT accum overflow before Barrett at large K; P-core pinning may be unavailable. Numerical-equivalence (Garner sign/scale edge cases) is where CRT projects usually die.
4. **N≤512 ceiling** blocks any design assuming arbitrary-length cyclotomic NTT; a third prime is a Phase-5 cascade, not a config flag.
5. **The fork tax.** math-core ↔ engine still carry duplicated forwards / dequant / row_bytes / arch-id enums. Generalization presupposes de-duplication, or the "one object" becomes two.
6. **"Bit-exact" is conditional** — holds under greedy + fixed K + same checkpoint + same backend; temperature/adaptive-K/cross-backend can break it. The formal guarantee must state its preconditions.

---

## 11. What to hand the next session

Spawn these as **separate frozen contracts** (this RFC is their parent):
- **C1 — `.sp-model` v1 + O_K container:** min-entropy disk form + runtime-expansion contract + spare-bit metadata schema (§3). Decide OK_Q4 default.
- **C2 — L1 ABI v2:** add the Garner recombination service + the island-dispatch surface (§4, §8).
- **C3 — MTP transaction protocol:** propose/verify/commit/rollback over the Spinor journal (§5).
- **C4 — MeMo receipt format + fusion contract:** additive Z_q deltas, provenance, load-time vs overlay fusion (§6).
- **C5 — Cyclotomic-ring paper:** the proper treatment operator asked for — ring structure, N≤512, where NTT wins vs Barrett-direct per backend (§2).
- **C6 — φ-machinery role doc:** Beatty-sharding + Fibonacci-scale promoted to [DESIGN] with gates; Zeckendorf parked (§7).

**Prime directive for whoever edits this:** keep the [PROVEN]/[DESIGN]/[SPECULATIVE] tags honest. The failure mode of this whole project is a beautiful idea drifting into the "done" column without a gate. This document's only real job is to make that drift impossible.
