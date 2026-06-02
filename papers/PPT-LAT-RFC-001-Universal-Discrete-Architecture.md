# RFC-001: PPT-ARM — the Shannon-Prime inference architecture (and the Lattice that fell out of it)

**Status:** DRAFT for review/critique/iteration. v2 — hierarchy corrected (PPT-ARM is primary; the Lattice is its natural extension).
**Author:** Claude (SP hat), 2026-06-02, synthesizing operator intent + the empirical record. Supersedes the v1 framing that wrongly centered the Lattice.
**Disposition:** A constitution + contract skeleton, not a decree. Every §ends with OPEN QUESTIONS. Nothing here is frozen until it is itself frozen.

> Tagging rule (anti-amnesia fence): **[PROVEN]** = silicon/oracle-confirmed · **[DESIGN]** = sound but unbuilt · **[TARGET]** = a number we are aiming at, not yet measured · **[SPECULATIVE]** = idea, ungated. A claim may not move toward [PROVEN] without a gate.

---

## 0. What this project actually is (corrected)

**PPT-ARM is the product.** It is a **drop-in replacement for the standard transformer's ~13-step forward pass *and* its KV/memory architecture**, which we **bolt onto existing models** by transcoding their weights into a *smaller* discrete artifact. A bolted-on model keeps its exact output but gains the PPT-ARM envelope:

1. **Inline Spinor-block KV compression (~120× [TARGET]) → effectively unlimited context.**
2. **Second-ring offload** — KV/state to disk and back, **residual + CRT bandwidth bypass**, so multiple devices (dual GPU / CPU / phone) compute on residues and recombine **without shipping full tensors**.
3. **Speed on integer silicon pipes** (vrmpy / VNNI / dp4a), **long context**, **bit-exact**, **compressed** — all at once.

The **Lattice (LAT)** — the broader Z_q discrete substrate, the mesh, the PoUW ledger, cross-backend composability — **fell out of the PPT-ARM math naturally**. It is real and beautiful, but it is the *extension*, not the center. **PPT-ARM is load-bearing and primary; LAT is what the substrate makes possible once PPT-ARM exists.**

**The bar (north-star gate).** The framework is pointless if a user can `llama.cpp` + the old SP hierarchical KV cache + a custom lmstudio build and run Qwen3.6 at **40+ tok/s**. So: **bit-exact correctness is table stakes (the precondition that the bolt-on preserves the model). The WIN is the envelope — more context per byte, faster on the same silicon, longer context than fits in RAM, and multiple devices acting as one.** A PPT-ARM result that matches llama.cpp's tokens at equal-or-slower speed with no compression/context/multi-device gain has *failed*, however bit-exact.

---

## 1. PPT — the 13-step replacement forward

Standard transformers run ~13 sequential steps per layer (embed, RMSNorm, Q/K/V proj, QK-norm, RoPE, attention, O-proj, residual, norm, FFN gate/up/down, residual). **PPT replaces each with a discrete Z_q equivalent**, so the whole forward runs in integer rings on the platform's vector pipes, bit-exact across backends, with the KV path compressed.

| Standard step | PPT replacement | Status |
|---|---|---|
| Weight storage | O_K object: Frobenius-lifted Q4/Q8 packed, **smaller than source** | [PROVEN] pack; [DESIGN] sub-Q4 |
| Q/K/V/O/FFN matmul | `mod_q` integer matmul (Barrett) on vrmpy/VNNI; dequant only logits | [PROVEN] HVX vrmpy 1.04× ARM fp32; [DESIGN] full int-end-to-end |
| RoPE | integer / φ-RoPE (Fibonacci-convergent angle approximation) | [DESIGN] |
| Attention scores | Barrett-direct dot (HD ≤ 256) or NTT-attention (HD ≳ 1024 only) | [PROVEN] direct; NTT [PROVEN]-but-not-faster at chat HD |
| **KV cache** | **Spinor-block inline compression (§2) — the headline** | [PROVEN] encode/decode; [TARGET] 120× |
| Norms | integer RMSNorm | [PROVEN] |
| Logits | the only fp dequant point | [PROVEN] |

**Bolting on a model = the arch cells.** gemma4, qwen35moe (Qwen3.6-35B-A3B), gemma3, qwen3, qwen2.5 each got a PPT forward proven **argmax bit-exact to llama.cpp** (M_GEMMA4, M_QWEN36, …). **[PROVEN].** This is the *foundation*, not the deliverable: it proves PPT reproduces the model exactly, which is the licence to then compress its KV, extend its context, shard it across devices, and run it on integer pipes. Bit-exact is the floor we build the envelope on.

**OPEN QUESTIONS §1:** which steps are *still* fp plumbing in the current shells (router top-k must stay f32; what else legitimately must)? Is the per-arch forward the unit of "bolting on," or do we factor a generic PPT forward + per-arch deltas so a new model is "a classifier + a delta table"?

---

## 2. ARM — the memory architecture (Spinor KV + the two rings)

This is where PPT-ARM earns its name and most of its value.

### 2.1 Spinor-block inline KV compression — the headline capability
Each cached K/V head-vector is encoded **inline** to a Spinor block (the 63-byte block / 0xA5-sentinel cache-line ABI), losslessly under the Z_q + Frobenius geometry, decoded on the fly during attention. **Target ~120× → context becomes bandwidth/disk-bound, not RAM-bound → effectively unlimited.** `sp_spinor_encode_vec`/`decode_vec` are wired in the reference attention path. **[PROVEN]** mechanism / **[TARGET]** ratio — *the compression ratio at bit-exact KV is the single most important number to measure and is not yet pinned.*

### 2.2 The two rings (corrected — Ring 2 is for PPT, not the ledger)
- **Ring 1 — active compute.** The Z_q working set: weights (O_K object) + the live Spinor-compressed KV window. Integer matmul + discrete attention happen here.
- **Ring 2 — offload / recall.** KV and state **spill to disk and are recalled**; **residuals + CRT** make the spill near-zero-bandwidth and make **multiple devices act as one**: each device holds/works a residue (mod q_i) and recombines via Garner, so you **ship residues, not full tensors** — dual GPU, CPU+GPU, or phone+host collaborate with inter-device bandwidth virtually eliminated. **This was always Ring 2's design.** The PoUW ledger and mesh-shareable memory are *tenants* of Ring 2, not its purpose.

### 2.3 Regime-adaptive memory: System-1 / System-2 + crossover oracle
The KV/memory path is **not one-size** — this is a proven prior design from old SP, re-established here.
- **System-1 (small context):** a fast, simple path. Compression + Ring-2 overhead don't pay at short ctx, so System-1 keeps latency low (closer to a plain cache).
- **System-2 (large context):** the Spinor-compressed + Ring-2-offload path — where the ~120× / unlimited-context / multi-device envelope lives.
- **A crossover oracle predicts the System-1 → System-2 switch** (by ctx length, bandwidth pressure, cache occupancy).
This is *why* the stage-gating rule below matters: System-2 measured at small ctx in isolation looks slow — it is not meant to run there. Spec'd in contract **C2**.

### 2.3.1 Stage-gating rule (do not gate a stage on system tok/s)
**The system does not work in isolation.** A stage will miss an end-system number (tok/s, context) that it only hits once the rest of the envelope is assembled (Spinor cache + Ring-2 + island sharding). **Gate each stage on its OWN correctness/metric** (bit-exact output; the kernel's own throughput; the compressor's own ratio) — **never on assembled-system tok/s.** Declaring a stage failed for missing a system number it structurally cannot hit alone is a category error. System-level numbers are *system* gates, measured only when the envelope is assembled. (See `PPT-LAT-STATE.md` §0.)

### 2.4 Why this beats "llama.cpp + hier-KV @ 40 tok/s"
llama.cpp can't: (a) hold context beyond RAM at bit-exact via 120× inline compression; (b) split one model across two GPUs with **no NVLink-class bandwidth** by exchanging CRT residues; (c) recall offloaded KV from disk cheaply via residual reconstruction. PPT-ARM's reason to exist is exactly this envelope. **The gates for PPT-ARM are therefore capability + performance gates (compression ratio, tok/s at long ctx, multi-device scaling), with bit-exact as an invariant underneath — not bit-exact as the headline.**

**OPEN QUESTIONS §2:** measured Spinor KV compression ratio at bit-exact? Ring-2 residual-recall cost vs. recompute? Is the dual-GPU "ship residues" path a 2-prime CRT split of the *weights*, the *activations*, or both? What's the bandwidth model that says CRT-residue exchange < full-tensor NVLink?

---

## 3. The O_K object + the converter (REDUCES size — corrected)

**The offline converter REDUCES on-disk size; it must never inflate.** My earlier OK_Q8 transcode was backwards — 1 byte/weight is *larger* than a Q4_K source, which is exactly why it ballooned to ~35 GB and disk-blocked. That was a wrong-direction artifact, not a disk problem.

**Principle:** the `.sp-model` artifact is **≤ the source quant** — OK_Q4 at minimum, ideally **sub-Q4 via SP compression** (Frobenius lift + Spinor structure + per-row scale sharing). The disk holds the O_K object at **minimum entropy**; the **runtime loader expands into Ring 1's ALU-adapted container in cache/VTCM**, where spare bits may carry **distinct, compute-useful** info (interleaved block-scale to kill the separate scale fetch; MoE routing/stride; a *different* island's CRT residue) — **never a redundant copy of the same weight** (storing `W mod p1 | W mod p2` for one W is the same entropy twice — a non-reclamation). Any spare-bit scheme ships only if its per-element mask cost is *measured* to net-win.

**Immediate operating decision:** **lock the disk write to OK_Q4 / source-quant-or-smaller; do all entropy-dense container tricks in the runtime cache loader.** This both honors "the converter reduces size" and unblocks the qwen35moe `.sp-model` (OK_Q4 ≈ 20 GB fits; OK_Q8 ≈ 35 GB never should have been the target).

**OPEN QUESTIONS §3:** what is the true sub-Q4 SP compression ratio achievable at bit-exact (this is a headline number)? `.sp-model` v1 format = min-entropy body + runtime-expansion contract — needs a frozen spec (contract C1). Does the weight converter and the Spinor KV compressor share a codec?

---

## 4. Heterogeneous compute — Trick #1, generalized (this is Ring-2's compute face)

K **Compute Islands** (CPU-AVX, NPU, GPU, DSP, mesh peer) each compute a residue (mod q_i) of the same matmul; host **Garner-recombines**; no cross-island sync until recombination. The wall-clock win is **parallel silicon + eliminated inter-device bandwidth** (ship residues, §2.2), not per-op NTT. **[DESIGN]**; cDSP `mod_q`, NPU INT dispatch, Garner constants each **[PROVEN]** in isolation; the combined proof is Sprint TRICK-1.
- **Activation quant is part of the contract:** islands want int inputs; host quantizes fp32→int8; dequant by `weight_scale × activation_scale` after Garner (miss it → instant equivalence failure).
- **Numerical-equivalence is the critical gate** (Garner sign/scale edge cases are where CRT projects die); parallel-win may fail honestly (NPU init-dominated) without invalidating the pattern.
- **Beatty/φ stateless collision-free partition** for routing KV blocks / experts / tasks across islands without a lock table (bounded role; SP already uses φ here — we organize, not invent).

**OPEN QUESTIONS §4:** promote the ARM Garner recombination into the L1 ABI as a first-class service? 2-prime vs k-prime island scaling? mesh peer as an island via recursive CRT?

---

## 5. MTP — a system pillar (transaction protocol, not a decode hack)

qwen35moe carries a NextN/MTP block (loaded-not-run) + a `-Draft` pairing **[PROVEN]**. MTP = **draft → verify → commit/rollback**, made exact by the discrete substrate: draft head proposes K tokens; one batched target forward verifies; **acceptance is byte-exact token-id equality (not a probability ratio)**; rejection **rolls back KV/state to the last committed Spinor block, losslessly** (Ring-1/Ring-2 transactional rewind). It belongs in the L3 daemon as a **transaction protocol with the Spinor journal**, composing with Trick #1 (draft on island A, verify on B/C). **[DESIGN]**, Spinor ABI **[PROVEN]**.

**OPEN QUESTIONS §5:** byte-exact accept under temperature>0 (needs a discretized-sampling contract)? in-model NextN head vs separate draft as default?

---

## 6. MeMo — a system pillar (memory + continual learning on Ring 2)

Operator: MeMo is core; "memo as memory"; with MTP, the old Phase-4-SPEC is redundant. Two first-class layers:
- **Portable memory profiles:** a user's memory = facts/context + a set of **commutative Z_q additive Spinor receipts** fused at Frobenius-lift load. Additive deltas commute+associate ⇒ order-independent, **peer-shareable byte-exactly** over the mesh (a Ring-2 tenant). **[DESIGN]** fusion / **[PROVEN]** receipt ABI + canonical Garner order + mesh determinism.
- **Continual learning without gradient drift:** base frozen Z_q weights never change; learning = appended algebraic receipts + a PoUW ledger entry. **[DESIGN]**, ledger **[PROVEN]**.

**Honest caveat [SPECULATIVE]:** "learning = matrix addition in Z_q" is clean *only if* the useful update decomposes into a commutative additive low-rank delta. Whether a real continual-learning signal survives that constraint is unproven — gate it.

**OPEN QUESTIONS §6:** receipt format (rank, scale, provenance) as a frozen contract; load-time fusion vs runtime overlay (cf. KSTE-KV overlay); model-level MeMo vs agent-level two-tier memory — same mechanism or analogue?

---

## 7. The φ / Wythoff / Beatty / Zeckendorf machinery — bounded roles

SP already uses φ extensively (Fibonacci-Prime DHT, KV sub-sampling `⌊k·φ·N⌋`, RoPE-φ, Halton/Sobol) — this section *organizes* it. Each tool gets a gated role; fence against "a solution looking for a problem."

| Tool | Role | Status |
|---|---|---|
| Stern-Brocot / Fibonacci convergents of φ | integer-only approximation of irrational scales/angles on fp-less islands | [DESIGN] |
| Beatty/Rayleigh (φ, φ²) partition | stateless collision-free KV/expert/task sharding across islands (Ring 2) | [DESIGN] |
| Continued-fraction φ=[1;1,1,…] | maximal irrationality ⇒ best worst-case equidistribution for QMC sub-sampling | [DESIGN] (in Halton upgrade) |
| Zeckendorf base-φ rep | sparse weight/index encoding | [SPECULATIVE] — encode/decode cost likely dominates; gate first |

**Rule:** any φ-construct on a hot path must beat the boring integer alternative *measured*, or it stays a note.

---

## 8. Crate boundaries (bounded engines)

```
math-core (C)  — PRIMITIVES: Barrett, Frobenius lift, NTT-CRT (N<=512), KSTE, Spinor (KV + receipt),
                 Garner. Reference forward = validation oracle. THE substrate of PPT.
arena (C)      — O_K object: packed, <= source size; runtime entropy-dense container.
.sp-model fmt  — min-entropy disk body + runtime-expansion contract + arch_struct.
L1 ABI (frozen)— seam: load/unload, session, forward entry, arch-query, (PROPOSED) Garner service,
                 (PROPOSED) Ring-2 offload/recall + Spinor-KV API.
backends       — CPU AVX-512(VNNI), CUDA(dp4a/PTX), Vulkan, Hexagon(vrmpy). SAME primitives, BIT-EXACT.
L3 daemon(Rust)— orchestration: island detect + Beatty dispatch, MTP transactions, MeMo ledger,
                 Ring-2 disk/mesh offload, Garner recombine. No math truth here.
```

**The current cross-track gap [PROVEN diagnosis]:** the primitives exist; the per-backend forward *shells* still call scalar f32 (HX.3b fixed Hexagon → vrmpy → 1.04× over ARM fp32; AVX/CUDA/Vulkan pending — the `WIRE-*` sprints). **Until the shells call the integer + Spinor-KV primitives, none of the PPT-ARM envelope (compression/speed/context) is realized — only correctness is.**

---

## 9. Honest scorecard

**[PROVEN]:** PPT forward bit-exact to llama.cpp for qwen3/qwen2.5/gemma3/gemma4/qwen35moe (the bolt-on works); NTT-CRT dual-prime byte-exact; Frobenius Q4/Q8 + arena; KSTE + sieve; Spinor encode/decode + receipt ABI (silicon-confirmed); M.4 PoUW ledger + mesh canonical order; L3 daemon (chat/ledger/QUIC); Hexagon HVX Barrett/mod_q/NTT/Bluestein; **HX.3b vrmpy 1.04× > ARM fp32, byte-equal** (reported); cross-backend determinism.

**[TARGET]/[DESIGN] — the actual value, not yet measured/built:** Spinor KV compression ratio (the 120×); sub-Q4 converter ratio; tok/s at long ctx vs the 40-tok/s baseline; Ring-2 disk offload + residual recall; dual-GPU residue-sharing; Trick #1 combined; MTP transaction loop; MeMo fusion; int-end-to-end (no per-matmul fp dequant).

**Blockers:** WIRE gap (CPU/CUDA/Vulkan shells scalar-f32); qwen35moe `.sp-model` needs the OK_Q4 (reducing) artifact + bridge + arena-expert; NTT N≤512 + not-faster-at-HD≤256 (structural); engine↔core fork tax (duplicated forwards/dequant/enums).

---

## 10. Where this design breaks

1. **The headline numbers are unmeasured.** 120× KV and "beats 40 tok/s" are [TARGET]. If the measured Spinor ratio is 10×, or PPT-ARM is slower than the hier-KV baseline after all wiring, the value thesis is in question. **Measure these before believing them.**
2. **Ring-2 residual recall** may cost more than recompute; **dual-GPU residue exchange** only wins if CRT-residue bandwidth < full-tensor transfer — unproven bandwidth model.
3. **Entropy-container mask cost** can erase the fetch savings; **MeMo additive-only** may not capture real learning; **Trick #1** init-cost/precision/Garner-sign edges.
4. **N≤512** caps cyclotomic NTT; a third prime is a Phase-5 cascade.
5. **Bit-exact is conditional** (greedy + fixed-K + same checkpoint/backend); state its preconditions.
6. **Fork tax:** "one object" presupposes de-duplicating engine↔core.

---

## 11. Child contracts to spawn (this RFC is their parent)

- **C1 — `.sp-model` v1 + O_K container (REDUCING):** min-entropy disk body ≤ source + runtime-expansion + spare-bit schema; OK_Q4 default. *(Unblocks qwen35moe + nails the "converter reduces" principle.)*
- **C2 — ARM memory contract:** Spinor-KV inline-compression API + the two-ring offload/recall + residual reconstruction. *(The headline capability — measure the ratio.)*
- **C3 — L1 ABI v2:** Garner recombination service + island dispatch + Ring-2 hooks.
- **C4 — MTP transaction protocol** over the Spinor journal.
- **C5 — MeMo receipt format + fusion contract.**
- **C6 — Cyclotomic-ring paper** (N≤512, NTT-vs-Barrett crossover per backend).

**Prime directive:** PPT-ARM is primary; the Lattice is its extension. The win is the **envelope** (compression · unlimited context · bandwidth bypass · multi-device · speed), with **bit-exact as the invariant floor, not the headline**. Keep the [PROVEN]/[TARGET]/[DESIGN]/[SPECULATIVE] tags honest — the project's failure mode is a [TARGET] drifting into the "done" column without a measured gate.
