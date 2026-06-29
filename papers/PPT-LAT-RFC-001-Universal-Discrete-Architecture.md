---
type: design
title: "RFC-001: PPT-ARM — the Shannon-Prime inference architecture (and the Lattice that fell out of it)"
description: "Status: DRAFT for review/critique/iteration."
tags: [design]
timestamp: 2026-06-18T05:55:03Z
resource: shannon-prime-lattice/papers/PPT-LAT-RFC-001-Universal-Discrete-Architecture.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# RFC-001: PPT-ARM — the Shannon-Prime inference architecture (and the Lattice that fell out of it)

**Status:** DRAFT for review/critique/iteration. v2 — hierarchy corrected (PPT-ARM is primary; the Lattice is its natural extension). **Amended 2026-06-03:** the C2.1 memory envelope is now measured (recall router solved, two-ring wired live — §9/§11); public front door live at [Position Is Arithmetic](https://github.com/nihilistau/Position_Is_Arithmetic) (site https://nihilistau.github.io/Position_Is_Arithmetic/); all repos relicensed to MIT.
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

> **Status upgrade (2026-06-18) — the FORWARD PATH is now BYTE-EXACT on a real gemma-4-12B; the auditable discrete substrate is realized end-to-end (table rows unchanged in intent, status moved).** The float surfaces that were still `[DESIGN]` in the engine as built — the matmul row's **"[DESIGN] full int-end-to-end"**, the **RoPE** row's `[DESIGN]`, and the attention dot/softmax — now run **exact-integer** behind a default-off `SP_BYTEEXACT` flag, on the same dual-prime CRT-NTT as the memory ring. So the *Universal Discrete Architecture's forward path is byte-exact on a 12B*: **G-BYTEEXACT-FORWARD-12B GREEN** — OFF = PPL 4.6665 byte-identical null floor / ON = 4.6569 parity / run-to-run bit-identical (logits bit-identical across reduction-order and machine). "Byte-exact" here = **EXACT ARITHMETIC / cross-machine determinism = AUDITABILITY**, which is the one property §0's bar called table stakes and the whole RFC-001 thesis rests on — now realized for the *complete* forward, not just the linear cells. NOT a compression result (that axis is separate, and convicted). The new piece was the four nonlinear islands (`sp_islands_q_ref.rs` + math-core `core/exact_islands/`); the byte-exact linear algebra was already in the universal crate `tools/sp_dsp_smoke`. Record: `CONTRACT-BYTEEXACT-forward.md`; L1-ABI §6b (the new persistent-KV decode verb the daemon drives the 12B through). Only the external 2-physical-GPU bit-identical check remains.

**OPEN QUESTIONS §1:** which steps are *still* fp plumbing in the current shells (router top-k must stay f32; what else legitimately must)? *Largely ANSWERED by the byte-exact forward (2026-06-18): RMSNorm / softmax / GELU / RoPE / attention all converted to exact-integer behind `SP_BYTEEXACT`; the residual fp surfaces are the logit dequant (by design — the only fp point) and the MoE router top-k (f32 by the top-k cliff). A from-scratch successor would choose Mersenne hidden dims to close RMSNorm/RoPE division by exact bit-shift — out of scope for the retrofit, see `CONTRACT-BYTEEXACT-forward.md` §6.* Is the per-arch forward the unit of "bolting on," or do we factor a generic PPT forward + per-arch deltas so a new model is "a classifier + a delta table"?

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

**[PROVEN since 2026-06-03 (C2.1)]:** the **two-ring memory recall envelope** — ±1 recall router + Optane Ring-2 (7.57 µs/read) + (sink+W) window shrink (910× @32k) + needle off physical NVMe + 8×@+0.69% PPL + fusion, bit-exact when off; the **reducing loader** (GGUF → ~50%-smaller `.sp-model`, bit-faithful, paper 02 green); **WIRE-CPU** 0.84 → 39.52 tok/s (47×, ~1.34× behind llama.cpp Q8_0).

**[TARGET]/[DESIGN] — still the open value:** the Spinor *per-vector codec* ratio *at bit-exact* (the ~120× question — the codec is lossy 29/31 today, distinct from the recall envelope); sub-Q4 converter ratio; the **40-tok/s north-star on 35B-A3B** (the 0.6B WIRE gap is closed to ~1.34×); Ring-2 **multi-device** residual recall + dual-GPU residue-sharing (single-device offload now [PROVEN]); Trick #1 combined; MTP transaction loop; MeMo fusion; int-end-to-end (no per-matmul fp dequant).

**Blockers:** WIRE gap (CPU/CUDA/Vulkan shells scalar-f32); qwen35moe `.sp-model` needs the OK_Q4 (reducing) artifact + bridge + arena-expert; NTT N≤512 + not-faster-at-HD≤256 (structural); engine↔core fork tax (duplicated forwards/dequant/enums).

---

## 10. Where this design breaks

1. **The *remaining* headline numbers are unmeasured.** The *memory* envelope is now measured (C2.1: 910× resident @32k, off-NVMe retrieval @7.57 µs/read, 8×@+0.69% PPL). Still [TARGET]: the Spinor *per-vector codec* ratio at bit-exact (the 120× — lossy 29/31 today) and "beats 40 tok/s" on the 35B-A3B (the 0.6B WIRE gap is down to ~1.34×). If that codec ratio is only ~3× at bit-exact, or the MoE is slower than the hier-KV baseline after wiring, the value thesis is still partly open. **Measure before believing.**
2. **Ring-2 residual recall** may cost more than recompute; **dual-GPU residue exchange** only wins if CRT-residue bandwidth < full-tensor transfer — unproven bandwidth model.
3. **Entropy-container mask cost** can erase the fetch savings; **MeMo additive-only** may not capture real learning; **Trick #1** init-cost/precision/Garner-sign edges.
4. **N≤512** caps cyclotomic NTT; a third prime is a Phase-5 cascade.
5. **Bit-exact is conditional** (greedy + fixed-K + same checkpoint/backend); state its preconditions.
6. **Fork tax:** "one object" presupposes de-duplicating engine↔core.

---

## 11. Child contracts to spawn (this RFC is their parent)

### FORWARD PRIORITY — re-ordered 2026-06-02 (differentiators ahead of context work)

The C2 measurement phase is **done** and it re-ranked the work: the per-vector KV codec is ~3.5× (lossy, 29/31 real-model) and the Ring-2 context multiplier, while large (~hundreds×), is largely disk-tiering. **The unmeasured, load-bearing differentiators are SPEED, MULTI-DEVICE, and MTP — not more context work.** So the forward order is now:

1. **P1 — SPEED / the WIRE gap → real tok/s (the north-star).** Wire the integer pipes (CPU AVX-512+VNNI first; the dev host has it) into the forward *shell* (today they're scalar f32 off-Hexagon) and measure tok/s vs llama.cpp on a proven small model. This is the literal reason-to-exist gate and the biggest unmeasured risk (HX.3b's 1.04× bandwidth-bound result is the warning). Lives partly in C3 (backend wiring) + a new measurement gate. **[IN PROGRESS 2026-06-03]:** WIRE-CPU took Qwen3-0.6B decode **0.84 → 39.52 tok/s (47×)** (Q8 pack + threaded matmul + AVX2 int8×f32 dot), now **~1.34× behind llama.cpp Q8_0**; VNNI tested + falsified → the gap is **memory layout, not ALU**. Next step filed: `PLAN-SPEED-WIRE-CPU-V3-memory-layout.md` (Stage-0 profile gates a block-Q8 layout). The 0.6B dense dot is "match the tuned ceiling"; the real speed win is the **35B-A3B MoE system gate**, not this kernel.
2. **P2 — C4 MTP transaction protocol** (Theorem T8): exact O(1) ring-pointer rollback + batched-draft bit-identity; a speed differentiator that composes with P1.
3. **P3 — C3 multi-device CRT residues + Garner recombination service** (ship residues not tensors): the most differentiated capability; bigger build. A 2-node CRT-shard byte-exact vertical slice is the proof.
4. **P4 — remaining C2** (DEMOTED to context axis): fp16 swivel, wire Spinor-KV into `qwen36_forward`, a real *directional* recall router (KSTE ruled out — C2.0.4.1). Secondary; matters most for long-ctx on small models, not the weight-dominated flagship MoE.
5. **P5 — C5 eMeMo, C6 cyclotomic paper** as before.

### Contract index

- **C1 — `.sp-model` v1 + O_K container (REDUCING):** min-entropy disk body ≤ source + runtime-expansion + spare-bit schema; OK_Q4 default. **[DONE 2026-06-02 — ~17% reduction, output-lossless top-1.]**
- **C2 — ARM memory contract:** Spinor-KV inline-compression + two-ring offload/recall + recall router. **[MEASUREMENT PHASE DONE 2026-06-02; C2.1 RESOLVED + WIRED LIVE 2026-06-03.]** The recall router is **solved** — a ±1 Rademacher projection (KSTE was falsified, C2.0.4.1) — and the two-ring memory is wired into the live decode path and **measured**: 910× resident KV shrink @32k, needle retrieved off physical Optane @7.57 µs/read, 8× sparsification @ +0.69% PPL, O(N) quickselect, compact-and-spill fusion (verified 512 + timed 8k; 32k R9 in flight). Engine `f8ea920`/`7896bc4`; CONTRACT-C2 §C2.1. The Spinor *per-vector codec* ratio at bit-exact (the ~120× question) remains [TARGET]; the *recall envelope* is now [PROVEN].
- **C3 — L1 ABI v2:** Garner recombination service + island dispatch + Ring-2 hooks. **[P3]**
- **C4 — MTP transaction protocol** over the Spinor journal. **[P2]**
- **C5 — MeMo receipt format + fusion contract.** **[P5]**
- **C6 — Cyclotomic-ring paper** (N≤512, NTT-vs-Barrett crossover per backend). **[P5]**
- **(new) SPEED gate — WIRE the integer pipes → tok/s vs llama.cpp.** **[P1 — the north-star; spawn as its own contract/sprint.]**

**Prime directive:** PPT-ARM is primary; the Lattice is its extension. The win is the **envelope** (compression · unlimited context · bandwidth bypass · multi-device · speed), with **bit-exact as the invariant floor, not the headline**. Keep the [PROVEN]/[TARGET]/[DESIGN]/[SPECULATIVE] tags honest — the project's failure mode is a [TARGET] drifting into the "done" column without a measured gate.

---

## KEYSTONE addendum (2026-06-25)

> This addendum is additive — the body above stands as the original architecture record. It registers what the KEYSTONE milestone (keystone-1) changed about the *shape* of the architecture, and points at the current-state source of truth. **The current state of the system is [PPT-LAT-KEYSTONE.md](PPT-LAT-KEYSTONE.md), not this RFC's body.** Read it first; use this RFC for the design rationale behind the substrate.

**The architecture is now FIVE repositories — `shannon-prime-harness` is the 5th.** The original crate-boundary map (§8) named the math core, the engine, and the L3 daemon. KEYSTONE adds **`shannon-prime-harness`** (Python) as a first-class repo of the architecture: the agent harness (CosySim's runtime re-hosted on sp-daemon, lmstudio stripped) that carries ephemeral tool calling, the tiered conversation memory, and the agency loop. The full repo set is now: **shannon-prime-lattice** (umbrella/papers), **shannon-prime-system** (math core), **shannon-prime-system-engine** (engine + daemon + memory agency), **shannon-prime-harness** (agent harness), **Position_Is_Arithmetic** (public face). See [PPT-LAT-KEYSTONE.md §2](PPT-LAT-KEYSTONE.md).

**Pillars that were PROPOSED in this RFC are now REALIZED [PROVEN-LIVE].** The following moved from `[DESIGN]`/`[SPECULATIVE]` to built-and-gated parts of the architecture (the realization is host-side in the daemon + harness; no frozen-ABI or `.sp-model` change):

- **Memory agency — forget / decide / merge.** §6 (MeMo) framed memory + continual learning as a Ring-2 tenant; KEYSTONE realizes the *agency* over that memory: the model forgets on intent (FORGET), supersedes a changed fact (DECIDE), and consolidates two complementary facts into one synthesized truth (MERGE). Gates G-FORGET, G-DECIDE, G-MERGE; default-off = null floor.
- **Ephemeral tool calling.** Not in the original RFC; KEYSTONE adds a text-protocol ReAct loop (`<tool name="X">{json}</tool>` parsed/executed/fed-back) over the daemon `/v1/chat` seam — no native tool channel needed. Gates G-HARNESS-DAEMON-E2E, G-HARNESS-TOOLCALL-E2E.
- **The tiered MEM-OKF conversation memory.** §6's "portable memory profiles" + the model-vs-agent two-tier question is answered concretely: a content-addressed three-tier store (LUT→summary→full, sha256/C2-sig addressed) serves SHORT (live convo) → MID (extracted facts) → LONG (full+summary), one scheme linking them. Spec: [MEMORY-OKF-PROFILE.md](MEMORY-OKF-PROFILE.md); gates G-HARNESS-CONVMEM-E2E, G-MEM-OKF-CONFORM.
- **The autonomous agency loop (KAIROS realized).** The KAIROS resident-kernel axis (closed earlier) now drives a *model-driven* between-turn loop: on a heartbeat tick the organism consolidates the written conversation and runs a memory-maintenance round — the "auto rounds where the organism does things between turns." Gates G-HARNESS-AGENCY-E2E, G-HARNESS-KAIROS-TICK-E2E, G-HARNESS-HOOK-E2E.

**The byte-exact-forward status upgrade** (the 2026-06-18 box in §1) stands and is the floor KEYSTONE builds on: the §0 "table stakes" property — exact arithmetic / cross-machine determinism / auditability — is realized for the complete forward (G-BYTEEXACT-FORWARD-12B GREEN). The one remaining external item is the 2-physical-GPU bit-identical check.

**The boundary thesis holds, sharpened.** O_K wins on the *container* (exact arithmetic); every structure-on-content compression lever is a measured-inert honest negative. The KEYSTONE additions are all about the *organism around* the container (memory, agency, tools, tiers), not new compression claims.

**Open edges (the forward work):** see [PPT-LAT-KEYSTONE.md §12](PPT-LAT-KEYSTONE.md) — (1) persistent O(1) conversation KV; (2) the 2-physical-GPU byte-exact check; (3) deeper faithfulness via reliable tiered recall; (4) native-C XBAR port + T4 Frobenius of the model weights.

**Post-KEYSTONE — the Latent Interceptor + Telepathy [PROVEN + licensing SPEC].** The finetuned EAGLE draft body (the MTP draft) is repurposed as a **latent-native router**: a shared 1024-d body + tiny action/memory/tool heads that decide/route on the manifold without a tokenizer round-trip. The heads are **near-miss-hardened** (isolated cross-distribution OOD: tool 1.000, action 0.979, **false-fire 0.000** — never fires on idle chatter; KEEP recall 0.429→1.000). **Telepathy** generalizes the same-family latent injection (RP-1, `gemma4_kv_inject*`) into a named framework — a `LatentBridge` (`src→adapter→dst`) + an adapter registry with a conformance contract (`G-ADAPTER-CONFORM`). The first **cross-FAMILY** bridge is proven: gemma-3n-E2B ↔ qwen2.5-coder-0.5b via a *ridge affine* adapter — representation alignment (retrieval@1 1.000, round-trip 0.891), foreign reject (AUC 0.999), and generation **steering** (injected mapped latent raises matching-text LL, steer-accuracy 1.000 vs a matched control; the clean injection seam is the late residual at gentle scale). **Honest scope:** activation steering + geometry alignment + foreign rejection are PROVEN; **verbatim text-forcing is NOT claimed** (a single pooled latent can't force exact output). **Licensing (SPEC, prominent by design):** Telepathy is a *separately-licensed proprietary component layered on the MIT substrate* — the base stays MIT; the LatentBridge framework + cross-model adapters are restricted, enforced by **fail-closed license-key + cryptographic attestation** (the bridge refuses to run / runs inert without a valid license, and the protections only ever disable the bridge's own operation — never any host-external effect; that destructive line is explicitly out of scope). Spec: [PPT-LAT-TELEPATHY-LatentBridge-spec.md](PPT-LAT-TELEPATHY-LatentBridge-spec.md).
