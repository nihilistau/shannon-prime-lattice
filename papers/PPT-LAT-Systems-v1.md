---
type: design
title: PPT-LAT-Systems — v1
description: "Shannon-Prime: PPT-ARM Systems Architecture."
tags: [design]
timestamp: 2026-06-18T05:54:36Z
resource: shannon-prime-lattice/papers/PPT-LAT-Systems-v1.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# PPT-LAT-Systems — v1

**Shannon-Prime: PPT-ARM Systems Architecture.**

*The single canonical systems narrative. This is the rewrite of the May‑22/23 v0 corpus (PPT-LAT-Systems + the standalone PPT-LAT-L1-ABI-v0 and PPT-LAT-SP-MODEL-v0), folded into one document and re-homed against what is now PROVEN. It corrects the v0 hierarchy (PPT-ARM is the product; the Lattice fell out of it), carries forward only what the empirical record supports, and promotes four things the v0 corpus did not treat as first-class: **eMeMo**, **MTP = Theorem T8**, **System‑1/System‑2 + crossover oracle**, and the **φ / Wythoff / Beatty / Zeckendorf** machinery.*

---

> **Document set (read in this order).**
> 1. **`PPT-LAT-Theory.md`** — the canonical math (the 13‑step PPT substitution, O_K = Q(√−163), the frozen CRT primes, the frozen Spinor + KSTE formats, theorems T1–T8, production status). **Read it first.** Skipping it has caused real drift.
> 2. **`PPT-LAT-RFC-001`** — the short north‑star preamble / constitution (PPT-ARM primary; the envelope is the value; bit‑exact is the floor).
> 3. **This document (Systems v1)** — the canonical systems narrative built on (1) and (2).
> 4. **`PPT-LAT-STATE.md`** — the backward proven ledger (every PROVEN line cites a commit/tag/gate). **Trust it; do not re‑derive it.**
> 5. **`CONTRACT-C1 … C6`** — the forward work items.
>
> **Status vocabulary (the anti‑amnesia fence).** **[PROVEN]** silicon/oracle‑confirmed, evidence cited · **[PROVEN‑per‑record]** proven in a sibling repo, trust the tag · **[WIRED]** built + in‑tree, gated · **[DESIGN]** spec'd, unbuilt · **[TARGET]** a number to measure, not yet measured · **[SPECULATIVE]** idea. A claim may not move toward [PROVEN] without a gate + a STATE entry. This is the 20th rewrite; the failure mode is a [TARGET] drifting into the "done" column without a measured gate.
>
> **Supersession.** This v1 supersedes the v0 `PPT-LAT-Systems.md` and the standalone `PPT-LAT-L1-ABI-v0.md` / `PPT-LAT-SP-MODEL-v0.md`. Those are kept for provenance and carry a SUPERSEDED banner; their content lives here, corrected, in §3, §4, §5, and Appendices A/B. Last updated 2026‑06‑03.
>
> **Public front door.** The receipts-first paper series + live landing site live at **`Position_Is_Arithmetic`** (https://github.com/nihilistau/Position_Is_Arithmetic, site https://nihilistau.github.io/Position_Is_Arithmetic/) — every public claim reproduces from a command. This document is the internal canonical narrative; Position is what a newcomer reads first.

---

## 0. The frame — what this project actually is

**PPT-ARM is the product.** It is a drop‑in replacement for the standard transformer's ~13‑step forward pass **and** its KV/memory architecture, which we **bolt onto existing models** by transcoding their weights into a *smaller* discrete artifact. A bolted‑on model keeps its exact output but gains the PPT-ARM envelope:

1. **Inline Spinor‑block KV compression → effectively unlimited context.**
2. **Second‑ring offload** — KV/state to disk and back, with **residual + CRT bandwidth bypass** so multiple devices (dual GPU / CPU / phone) compute on residues and recombine via Garner **without shipping full tensors**.
3. **Speed on integer silicon pipes** (vrmpy / VNNI / dp4a), at **long context**, **bit‑exact**, **compressed** — all at once.

**The Lattice (LAT)** — the broader Z_q discrete substrate, the mesh, the PoUW ledger, cross‑backend composability — **fell out of the PPT-ARM math naturally.** It is real, and §11–§13 specify it, but it is the *extension*, not the center. The v0 corpus inverted this; v1 corrects it.

**The value is the envelope; bit‑exact is the floor.** Bit‑exact forward (M_GEMMA4, M_QWEN36, …) is **table stakes** — the precondition that the bolt‑on preserves the model — **not the headline.** A PPT-ARM result that matches llama.cpp's tokens at equal‑or‑slower speed with no compression / context / multi‑device gain has **failed**, however bit‑exact.

**North‑star gate.** The framework is pointless if a user can run `llama.cpp` + the old SP hierarchical KV cache + a custom lmstudio build and get Qwen3.6 at **40+ tok/s**. PPT-ARM must beat that — by holding context beyond RAM at bit‑exact via inline compression, by splitting one model across devices without NVLink‑class bandwidth via CRT residues, and by running on integer pipes. The gates are therefore **capability + performance** gates (compression ratio, tok/s at long context, multi‑device scaling), with bit‑exact as an invariant underneath.

**Stage‑gating rule (binding, operator 2026‑06‑02).** *The system does not work in isolation.* A stage will be slow / miss a system‑level number that it only reaches once the rest of the envelope is assembled (tok/s is not achievable until the Spinor cache + Ring‑2 + island sharding are wired). **Therefore a stage is gated on ITS OWN correctness/metric** (bit‑exact output; the kernel's own throughput; the compressor's own ratio), **never on assembled‑system tok/s.** Penalizing a stage for a system number it structurally cannot hit alone is a category error.

**Regression invariant (binding).** Every Lattice‑only feature (§11) is off‑by‑default, and with every gate off the engine output is **bit‑identical** to a plain inference path. Tested every release with a four‑backend parity sweep.

---

## 1. The one math object, six layers

There is one mathematical object — a discrete lattice over the ring of integers O_K of the imaginary quadratic field **K = Q(√−163)** (class number 1, hence a PID/UFD, with j‑invariant −640320³), realized computationally in the negacyclic cyclotomic ring **R_q = Z_q[x]/(xᴺ+1)** under a **dual‑prime CRT** decomposition with an **NTT diagonalization** that turns convolution into a pointwise product. The same object reappears as one walks from silicon to network:

- **Silicon.** Vector width and integer precision. The two CRT primes are sized so a pointwise product fits the ALU: 32‑bit on CPU, 30‑bit halves on Hexagon HVX.
- **Kernel.** The matmul: weight tiles in packed integer storage, an inline Frobenius‑scale dequant before accumulation. *(Speed comes from this integer pipe, not from NTT — see §2.)*
- **Cache.** The KV representation: K/V projected onto lattice anchors, stored as small integer blocks, decoded on read (§4).
- **Model.** Attention: queries and keys live in the same ring, so dot products are polynomial products and transforms can be cached.
- **Sieve.** The dominance partial order ⪯_d: cached cells form a poset; the engine keeps the dominance‑incomparable frontier (§11).
- **Network.** The routing key space: peers hash into prime‑factored slabs; shards flow over a DHT whose addresses are residues of the same primes that ground the NTT (§12).

The claim is not metaphysical identity; it is that exploiting the lattice structure consistently makes a careful implementation at one layer compose with the layers above and below.

**The frozen constants (canonical, do not change).** CRT primes **q₁ = 1073738753, q₂ = 1073732609** (both Proth, both with v₂(q−1)=10), reconstructed modulus ≈ 2⁶⁰. **[PROVEN]** Garner 2‑prime recombination constants in `ntt_crt.c`.

**The honest NTT cap.** Negacyclic NTT requires 2N | (q−1); both frozen primes have v₂(q−1)=10, so **max N = 512**. `ntt_crt.c` enforces N ∈ {128, 256, 512}. N ≥ 1024 is mathematically impossible with these primes; long context uses tiled N=512 NTTs, and **Bluestein** extends admissible lengths to all powers of two ≤ 512 (covers HD=64). Non‑power‑of‑two HD with odd factors (96, 288, 384) cannot be wrapped — the boring‑but‑correct answer there is a direct Barrett integer dot. Mixed‑radix / Good‑Thomas are **mathematically invalid** for the frozen primes (odd_part(q−1) not divisible by 3); a third prime is a Phase‑5 cascade. **[PROVEN constraint]** (NTT.0–5 closures).

---

## 2. PPT — the 13‑step replacement forward (the bolt‑on)

A standard transformer runs ~13 sequential steps per layer. PPT replaces each with a discrete Z_q equivalent so the whole forward runs in integer rings on the platform's vector pipes, bit‑exact across backends, with the KV path compressed.

| Standard step | PPT replacement | Status |
|---|---|---|
| Weight storage | O_K object: Frobenius‑lifted Q4/Q8 packed, **smaller than source** (§4, §5) | [PROVEN] pack; [DESIGN] sub‑Q4 |
| Q/K/V/O/FFN matmul | `mod_q` integer matmul (Barrett) on vrmpy/VNNI; dequant only at logits | [PROVEN] HVX vrmpy 1.04× ARM fp32; [DESIGN] full int‑end‑to‑end |
| QK‑norm / RMSNorm | integer RMSNorm | [PROVEN] |
| RoPE | integer / φ‑RoPE; relative phase as polynomial index shift mod N (§2.2) | [PROVEN] poly‑shift cache; [DESIGN] φ‑RoPE schedule swap |
| Attention scores | Barrett‑direct dot (HD ≤ 256) or NTT‑attention (HD ≳ 1024 only) | [PROVEN] direct; NTT [PROVEN] but not faster at chat HD |
| **KV cache** | **Spinor‑block / KSTE inline compression — the headline (§4, §6)** | [PROVEN] encode/decode; [TARGET] ratio at bit‑exact |
| Residuals / norms | integer adds + integer RMSNorm | [PROVEN] |
| Logits | the only fp dequant point | [PROVEN] |

> **Status upgrade (2026‑06‑18) — "full int‑end‑to‑end" is now REALIZED + 12B‑gated (the table rows above carry no proof change).** The remaining float surfaces in the *engine as built* — the four nonlinear "islands" (RMSNorm / softmax / GELU‑tanh / RoPE) and the **attention** (Q·K / p·V dot + softmax), which had stayed fp32 on the gemma‑4 CUDA path — now convert to **exact‑integer** behind a default‑off `SP_BYTEEXACT` flag, on the same dual‑prime CRT‑NTT (T6) as the memory ring. So the **"[DESIGN] full int‑end‑to‑end"** entry on the matmul row, the attention‑scores row, and the RoPE row are upgraded to **[PROVEN] byte‑exact on the real gemma‑4‑12B**: **G‑BYTEEXACT‑FORWARD‑12B GREEN** — OFF = PPL 4.6665 byte‑identical null floor / ON = 4.6569 parity / run‑to‑run bit‑identical (logits bit‑identical across reduction‑order and machine). This is *cross‑machine‑determinism / auditability*, NOT a compression result. The byte‑exact linear algebra was already in the universal crate `tools/sp_dsp_smoke`; the new piece was the four nonlinear islands (`sp_islands_q_ref.rs` + math‑core `core/exact_islands/`). The daemon drives the 12B prefill + token‑by‑token decode through the new L1 verb `sp_session_register_kvdecode_backend` (G‑WIRE‑CUDA‑DECODE‑GEMMA4 32/32 == oracle). Record: `CONTRACT-BYTEEXACT-forward.md` §5.2/§7/§8; L1‑ABI §6b; receipts engine `tests/fixtures/xbar_r3/G-BYTEEXACT-FORWARD-12B.log`. Only the external 2‑physical‑GPU check remains.

### 2.1 The bolt‑on is proven on real models

Each arch "cell" is a PPT forward proven **argmax bit‑exact to llama.cpp**:

| Model | Evidence | Status |
|---|---|---|
| Qwen3‑0.6B | core E_CPU_2 / forward gates | [PROVEN] |
| Qwen2.5 / Qwen2.5‑Coder‑0.5B | qwen25_forward gates | [PROVEN] |
| Gemma3‑1B | M_GEMMA3_CPU + T_FRO_4 PPL | [PROVEN] |
| **Gemma4‑E2B** | M_GEMMA4 PPL gate + top‑1 bit‑exact oracle | [PROVEN] (this session) |
| **Qwen3.6‑35B‑A3B (qwen35moe)** | M_QWEN36 top‑1 bit‑exact (3/3 `5444 8 198`), 218 s | [PROVEN] (this session) |

**qwen35moe is a Gated DeltaNet (Qwen3‑Next family) + 256‑expert top‑8 MoE + IMRoPE hybrid**, NOT Mamba2 — 30/40 layers are `ggml_gated_delta_net` linear attention, MoE on all layers, 10 full‑attn IMRoPE layers (full iff (L+1)%4==0), router stays f32 (top‑k cliff). The old GGUF‑INVEST doc mislabeled it Mamba2 and is SUPERSEDED. Full per‑block validation matched the oracle fingerprints (GDN recurrence, MoE router/experts/shared, gated full‑attn). Spec: `SPEC-qwen35moe-GDN.md`; closure `SESSION-CLOSED-lat-3-moe-forward.md`; commits core `568b678→d8e614f`.

This is the **foundation**, not the deliverable: it licences compressing the KV, extending the context, sharding across devices, and running on integer pipes.

### 2.2 Polynomial‑shift relative attention (the RoPE cache)

Inside R_q, multiplication by the RoPE phase eⁱᐧᐧΔᐧθ_d is a **polynomial index shift mod N** — a discrete permutation of the coefficient vector. The continuous trig rotation is replaced by exact arithmetic on residue indices, so the rotation cache stores **one int32 shift offset per token** instead of D fp32 values per token. For D=128, ctx=4096: 16 KB vs 2 MB — **~128× cache reduction, lossless on stock geometric‑RoPE models.** This is structural to the cyclotomic ring, not to the frequency schedule: no φ‑RoPE precondition, no Three‑Gap dependency. Coupled to `SP_ENGINE_NTT_ATTN=1`; when NTT‑attention is off, the engine uses the standard fp32 cos/sin table. **[PROVEN]** lossless by construction once E_CPU_5 measures KL < 10⁻⁷ (we have ≈2.7×10⁻¹⁰ on Qwen3‑0.6B).

*Correction from v0:* an earlier draft claimed a ~43× collapse from the Three‑Gap Theorem (T7) — but that requires *linear‑in‑φ* RoPE frequencies, and stock RoPE is *geometric*. The Phase 2‑CPU agent flagged this 2026‑05‑22. The ring representation gives ~128× on every stock model with no retraining; the φ‑RoPE schedule swap is kept as a research item (§9, Roadmap §20).

### 2.3 The honest negative: NTT‑attention is not the speed win

NTT‑attention is **slower** than a direct fp32/Barrett dot at HD ≤ 256 (measured ~0.15–0.72×). The substrate win is over **HD (polynomial length)**, not over context. **Speed comes from compression + bandwidth‑bypass + integer pipes + multi‑device, NOT from NTT.** [PROVEN‑per‑record: NTT.6]. NTT‑attention earns its place only at HD ≳ 1024, which chat‑shape models do not reach.

**OPEN QUESTIONS §2.** Which steps are *still* fp plumbing in the current shells (router top‑k must stay f32 — what else legitimately must)? Is the per‑arch forward the unit of "bolting on," or do we factor a generic PPT forward + per‑arch delta tables so a new model is "a classifier + a delta"?

---

## 3. Engine backends

The same forward runs on four backends behind a thin function‑pointer dispatcher (no scattered `if (backend==…)` in model code). Each implements the same kernel surface: packed‑weight matmul, fused softmax/attention, SwiGLU FFN, positional op, and the NTT primitive.

**The WIRE gap [PROVEN diagnosis], the single most important backend fact.** The primitives exist and are validated, but the per‑backend forward **shells still call scalar f32** on CPU/CUDA/Vulkan. Hexagon is the exception (HX.3b, below). **Until the shells call the integer + Spinor‑KV primitives, none of the PPT-ARM envelope — compression, speed, context — is realized; only correctness is.** The `WIRE-*` sprints close this.

### 3.1 CPU
Reference implementation and commodity‑desktop production target. Builds on Windows (MinGW gcc 15.2 is the pinned working toolchain; the v0 "MSVC VS2019 BT" line does not build the current tree — see STATE P0.1) and Linux (gcc 11+/clang 14+). Paths: scalar (correctness baseline + CRT alternate‑residue forgery check), AVX2 (8‑wide), AVX‑512 + VNNI (`vpdpbusd` for INT8 dot; manual `vpmaddubsw`+`vpaddw` fallback). Q8 dequant is inline (packed byte → sign‑extend int16 → × broadcast fp32 row scale → accumulate); no decode arena. SwiGLU fused. **[PROVEN]** forward correctness. **[PROVEN/measured]** integer‑pipe wiring (WIRE‑CPU): Q8 packing + OpenMP‑threaded matmul + AVX2 int8×f32 dot took Qwen3‑0.6B decode **0.84 → 39.52 tok/s (47×)**, now **~1.34× behind llama.cpp Q8_0** — and the remaining gap is **memory layout, not ALU** (VNNI tested + falsified). See `CONTRACT-SPEED` + `PLAN-SPEED-WIRE-CPU-V3`. **The two‑ring memory envelope (PPT‑ARM recall + Optane Ring‑2) is realized and measured on this backend** (§6.2) — the CPU is no longer correctness‑only.

### 3.2 CUDA
RTX 3000/4000 (sm_86 Ampere, sm_89 Ada). Warp‑cooperative 16×16 matmul tiles. **Hardware‑tier reality (do not spec across it):** sm_75 Turing has Tensor Cores + INT8/INT4 `mma.sync` but **no** cp.async / ldmatrix / mbarrier; sm_80 Ampere adds them; sm_90 Hopper adds TMA. INT8‑TC : fp16‑HGEMM peak ratio is ~2.8× on sm_75, silicon‑fixed. Turing has **one** 32‑bit ALU dispatch port shared between `lop3` and `xor` → lop3's theoretical 3× is capped at ~1.1× on sm_75 (separated on sm_80+). PTX inline asm **must not** use `mul.wide`/`mad.wide` (nvcc paired‑register allocator bug) — decompose to `mul.lo`+`mul.hi`+`shf`/`add.cc`. **[PROVEN‑per‑record]** PTX Barrett/NTT/mma‑tile sprints; **[DESIGN]** forward wiring (WIRE‑CU).

### 3.3 Vulkan
AMD / Intel / mobile via SPIR‑V (glslc). Only Vulkan‑1.2‑core subgroup intrinsics (ballot/shuffle) are used, forcing some reductions onto shared memory. Lower priority than CUDA (no validated AMD production results at Llama‑3 scale). **Open blocker:** wire‑vulkan OOM on main is quarantined (STATE P2). **[DESIGN]/[WIRED‑partial]**.

### 3.4 Hexagon (the phone path) — one accelerator backend among four
Snapdragon 8 Gen 1 V69, FastRPC from the ARM cores. Build env Hexagon SDK on a Windows host. Three logical layers used in combination:

- **Halide‑compiled HVX kernels** — matmul, Q8/Q4 dequant, NTT, attention. 128‑byte vectors, INT8/INT16 lanes, 32 output channels per HVX vector. **HX.3b: vrmpy int8 forward = 1.04× faster than ARM fp32 and byte‑equal** — *the integer‑substrate‑matches‑fp32 proof point.* [PROVEN‑per‑record, tag `lat-phase-2-hx-3b-hvx-vectorized`].
- **QNN HTP backend** — NPU dispatch via runtime‑built graphs. **Confirmed working in Unsigned PD on the S22U: 1.329 ms execute, 64/64 byte‑exact** (K.2‑spike). Skel pathing gotcha: push `libQnnHtpV69Skel.so` + set `ADSP_LIBRARY_PATH`; tensor `clientBuf` NULL at create, set at execute; per‑process init ~130 ms (amortize via persistent daemon).
- **Mode‑D bridge** — see Appendix C. FastRPC marshalling + admission patterns nailed down on the S22U (Path B Unsigned PD, `remote_handle64`, DmaBuffer heap 25). [PROVEN‑per‑record].

**Concurrent dispatch (Trick #1 substrate).** Wrap `FastRpcSession` in `Arc`, **not** `Mutex`. Multiple ARM threads calling `sess.invoke(&self,…)` on one `Arc<FastRpcSession>` are parallelized by the cDSP scheduler via V69 SSR:XA={4,5} dual vector‑context attachment. **Empirically: 1.935× (matmul, compute‑bound) down to 1.006× (Barrett primitive, data‑bound)** — the speedup is shape‑dependent (compute‑bound shapes overlap; data‑bound shapes are marshalling‑limited). Parallelism is measured by **wall‑clock overlap**, not pcycle ratio. [PROVEN‑per‑record, Sprint K]. This substrate is kernel‑agnostic and generalizes to cross‑model (§7, §10).

**Honest bandwidth negative.** The HX.3b chat‑shape inner loop is **memory‑bandwidth‑bound**, not ALU‑bound: a v2 wsum‑precompute got only 1.065× against a 1.20× gate and **FAILED honestly**. Attack bandwidth (prefetch / VTCM staging / 2‑row), not ALU. [PROVEN‑per‑record].

Thermal: V69 HTP throttles ~40% after 30–60 s sustained load on passive cooling; the scheduler inserts 1–2 ms micro‑pauses (`sp_session_config.thermal_pause_us`). Memory: S22U (~8 GB user) fits Qwen3‑3B Q4 with the full cache; the 1B–7B class is the well‑positioned consumer band.

---

## 4. Inline weight + KV compression

Compression is foundational, not an option; the unpacked path exists only for validation.

### 4.1 Q8 / Q4 weight storage with per‑row Frobenius scale
Each weight row is normalized, scaled into int8 (Q8, 1 byte/elem) or packed int4 nibbles (Q4, 16 bytes/32 elems), with **one fp32 Frobenius scale per row** in a sibling `<weight>.scale` tensor. Dequant is inlined into matmul; **no intermediate decode arena.** Q8 is 4× vs fp16 / 8× vs fp32 (Gemma3‑1B: 10.4 GB → 1.3 GB) at PPL within ~0.6% of fp16. Q4 needs **per‑row** scales with a clipping‑percentile calibration (a single per‑tensor scale collapsed Gemma3‑1B PPL by nine orders of magnitude — v0's documented failure). Mixed precision per arch: for qwen35moe, expert weights aggressively Q4, router stays f32 (router miscalibration tanks routing).

**[PROVEN] the zero‑inflation invariant.** Frobenius lift + arena packed weights never inflate quantized weights to fp16 in RAM (Q4→fp16 is 4× bandwidth for zero new information). **Q4_K + Q6_K k‑quant dequant is ggml‑exact** (`weight_dtype`, core `25809d8`; qwen35moe conv fingerprint matched).

### 4.2 The two KV‑compression overlays (corrected against canonical Theory)
**There are two distinct overlays, and they trade fidelity for ratio. The ~130× headline is the lossy KSTE signature, NOT the faithful per‑vector codec.** (An earlier C2 step measured the faithful codec and wrongly reported "~3×, not 120×" as the headline.)

- **(a) KSTE 64‑byte signature** — `core/kste/kste_encode.c`, E_CPU_6 / `SP_KSTE_KV`. Maps Rᵈ → **64 bytes regardless of d** (a T_{60,3} tree: 8 anchors + 55 residuals = top coefficients of the VHT2/Möbius transform). This is the **~130× headline**, and it is **LOSSY, valid only up to ⪯_d‑equivalence** — a dominance / dedup signature, not a reversible codec. **Production, 21/21 KSTE gate** (Theory §10). Caller must fold token IDs > 32 k to i16 before encoding (`label_of` clamps int32→int16; XOR‑low/XOR‑high fold — KSTE quantize gotcha, M.5).
- **(b) `sp_spinor_encode_vec`** — `vht2/spinor_block.c`, E_CPU_8 / `SP_KV_SPINOR`. Dimension‑preserving multi‑block int8, NBLK = ⌈HD/55⌉, **~3.5×/f32 asymptotic (~1.0–1.7×/f16)** at per‑vector cosine ≥ 0.99996, deterministic CRC‑checked decode. **But measured LOSSY end‑to‑end:** live E_CPU_8 on Qwen3‑0.6B gives **argmax 29/31, KL mean 0.023** — Spinor‑KV flips ~6.5% of top‑1 tokens accumulated over the layers. It is a *bounded‑divergence* overlay, **not bit‑exact** — the bit‑exact floor (§0) is the weight path + gate‑OFF, not this overlay.

**C2 must decide which the KV path uses** (lossy‑130× signature vs faithful‑3× codec) per the accuracy the application needs, and whether attention‑on‑signatures at ⪯_d granularity is acceptable, then measure end‑to‑end. The **frozen on‑wire KV record** is the **63‑byte Spinor block** (7‑byte VHT2 header + 55 int8 Möbius‑reordered anchor coeffs + CRC‑8, padded to 64 on disk with a `0xA5` sentinel — Appendix B §6). Decoding happens on read inside the attention kernel; the anchor table is small and shared (L1 / shared memory). [PROVEN] encode/decode + receipt ABI (silicon‑confirmed); [TARGET] the ratio at bit‑exact KV.

### 4.3 Fibonacci sub‑sampling for KV eviction
When context exceeds memory bounds, evict by retaining tokens at positions ⌊k·φ·N⌋ mod N (φ = (√5−1)/2) instead of FIFO/LRU. By Three‑Gap (T7) this maximally and uniformly covers temporal context with bounded discrepancy, mirroring the frequency‑axis equidistribution of E9.1. Distinct from the periodic‑refresh scheme (recompress tokens older than K with a larger block every K=512 tokens, keeping drift < 1% to 32 K). Both engaged via flags, default OFF until the long‑context PPL‑drift sweep validates parity. See §9 for the φ machinery and `SP_ECONTEXT_FULL` (Appendix A §7), which signals L2 to trigger this eviction and retry. [DESIGN / PROVEN‑math].

---

## 5. The `.sp-model` object + the swivel loader (REDUCES — corrected)

**The offline converter REDUCES on‑disk size; it must never inflate.** This is the largest single correction to the v0 corpus: v0 SP‑MODEL §1 listed "compression on disk" as a *non‑goal* ("PPT weights are already compressed; zstd buys little"). The real finding is the opposite — earlier SP models (gemma4/gemma3/qwen0.5b) used **OK_Q8 per‑row Frobenius = lossless and *smaller* than their F16/Q8 sources**, using part of the 13‑step PPT as a lossless weight codec. The OK_Q8‑on‑a‑Q4‑source transcode that ballooned qwen35moe to 35 GB was a **wrong‑direction artifact**, not a disk problem.

**Principle.** The `.sp-model` body is **≤ the source quant** — OK_Q4 for Q4‑class sources, OK_Q8 for Q8/F16 sources, ideally **sub‑Q4** via SP compression (Frobenius lift + Spinor structure + per‑row scale sharing). The disk holds the O_K object at **minimum entropy**; the **runtime loader (the "swivel") expands into Ring‑1's ALU‑adapted container** in cache/VTCM, where spare bits may carry **distinct, compute‑useful** info (interleaved block‑scale to kill the separate scale fetch; MoE routing/stride; a *different* island's CRT residue) — **never a redundant copy of the same weight** (`W mod p₁ | W mod p₂` for one W is the same entropy twice). Any spare‑bit scheme ships only if its per‑element mask cost is *measured* to net‑win.

### 5.1 C1 — PROVEN, the first real envelope number
**qwen35moe `.sp-model` reducing + output‑lossless production path.** transcode OK_Q4 → `sp_model_load` → `sp_model_to_qwen36` (the loader = swivel) → `qwen36_forward`. Rank‑3 experts packed via arena (`build_packed_q4` rank‑3 fix: rows = dims[1]·dims[2]); f32 router via `sp_as_f32`; arena‑aware `expert_mm` (`sp_frob_packed_dequant_row`). **Measured: 16.33 GB vs 19.7 GB Q4_K_M source (~17% reduction); round‑trip top‑1 = 5444 == oracle (OUTPUT‑LOSSLESS).** Even though OK_Q4 is a 4‑bit requant of a Q4_K source, the top‑1 held — "we were surprised." Mixed per‑tensor codec (Q4‑src→OK_Q4, Q6‑src→OK_Q8, matching Q4_K_M) is an optional fidelity refinement, not needed for the gate. **[PROVEN]** (core `66ccab9`; gate `qwen36_spmodel_top1`, `E_PARITY_2`).

### 5.2 The fp16 swivel
The loader can expand to an **fp16 runtime container** (arch_struct `preferred_precision = FP16` + `sp_matmul` `g_f16_act` path), halving activation/working RAM and matching native fp16 compute. **Orthogonal** to the on‑disk reducing codec — the disk stays min‑entropy; the swivel chooses the runtime container. **[PROVEN viable]; C2 task:** expose the explicit swivel flag, measure the RAM delta, confirm top‑1 unchanged.

**OPEN QUESTIONS §5.** The true sub‑Q4 SP compression ratio at bit‑exact (a headline number). Does the weight converter and the Spinor‑KV compressor share a codec? Disk‑sharding for very large models (`.sp-shards`). Direct DMA from `.sp-model` into GPU memory (GDS; the 64 KB data‑region alignment is already compatible).

---

## 6. ARM — the memory architecture (Spinor KV + the two rings + System‑1/2)

This is where PPT-ARM earns its name and most of its value.

### 6.1 Spinor‑block inline KV compression — the headline capability
Each cached K/V head‑vector is encoded **inline** to a Spinor block (the 63‑byte / 0xA5‑sentinel cache‑line ABI), decoded on the fly during attention. **Target: context becomes bandwidth/disk‑bound, not RAM‑bound → effectively unlimited.** `sp_spinor_encode_vec`/`decode_vec` are wired in the reference attention path (gemma3/qwen3; E_CPU_8). **C2 task:** wire it into `qwen36_forward`'s GDN + full‑attn KV (currently plain f32 KV) and report round‑trip determinism + ratio. The compression ratio at bit‑exact KV is the single most important number still to pin (see §4.2 for the two‑overlay choice). [PROVEN] mechanism / [TARGET] ratio.

### 6.2 The two rings (Ring 2 is for PPT, not the ledger)
- **Ring 1 — active compute.** The Z_q working set: the O_K weight object + the live Spinor‑compressed KV window. Integer matmul + discrete attention happen here.
- **Ring 2 — offload / recall.** KV and state **spill to disk and are recalled**; **residuals + CRT** make the spill near‑zero‑bandwidth and make **multiple devices act as one** — each device holds/works a residue (mod q_i) and recombines via Garner, so you **ship residues, not full tensors** (dual GPU, CPU+GPU, phone+host with inter‑device bandwidth virtually eliminated). This was always Ring‑2's design. The PoUW ledger (§13) and mesh‑shareable memory (§7) are *tenants* of Ring 2, not its purpose. **Storage tier (Knack's host):** Intel Optane E:/F: (16/32 GB) is reserved for Ring‑2 KV spill — byte‑addressable, near‑RAM latency = the tier that keeps "context beyond RAM" *fast*; a C2/C3 design input, not just storage. **[PROVEN] (C2.1) — the single‑device disk offload + recall is shipped and measured:** real Optane Ring‑2 (Windows `FILE_FLAG_NO_BUFFERING` + IOCP async, **7.57 µs/read**), a ±1 Rademacher recall router + Möbius attention‑sink window, **910× resident KV shrink @32k** (8.3 MB vs 7.5 GB), the needle **retrieved off the physical drive** under a poison‑gated (NaN‑filled) evicted cache, **8× sparsification at +0.69% PPL** (N=2k), O(N) quickselect, and a compact‑and‑spill **fusion** (exact prefill + window‑sized decode RAM; verified N=512, timed N=8192, 32k headline R9 in flight). Engine `f8ea920` / `7896bc4`; record in CONTRACT‑C2 §C2.1 + STATE §5.05/§5.055. **[DESIGN]** remains for the *multi‑device* residual + CRT residue‑exchange face (ship‑residues‑not‑tensors) — that bandwidth model is still unmeasured. **[PROVEN] AUTONOMOUS RECALL on the Exec (2026‑06‑20):** the recall *policy* on top of this two‑ring substrate — *which* stored episode the Exec pulls for a query, and how it refuses when none fits — is now a learned content head live on the served gemma‑4‑12B chat (B3‑WC). After proving every hand‑designed relevance signal fails open‑world (honest negatives), a teacher‑forced ablation knockout on NOVEL needles labeled a curator‑minted diverse corpus to train a **W_c** head (HD=512→r=32, **logsumexp‑over‑positions‑then‑mean‑over‑heads**, InfoNCE over [episodes + NULL/s0]); corpus diversity was the binding constraint (instance top‑1 34%→100%). G‑CHAT‑B3‑WC‑DIV2: 360/361 recall + 50/50 foreign reject, int16‑exact, s0=+0.102 (`87044d8`); G‑CHAT‑B3‑WC‑DEPLOY LIVE (`routes.rs SP_B3_WC`, (E+1)‑NULL‑argmax → replay winner @M=42 or clean prompt, `edc8079`). Record `CONTRACT-CHAT-FULLSTACK.md`.

### 6.3 Regime‑adaptive memory: System‑1 / System‑2 + crossover oracle *(first‑class)*
The KV/memory path is **not one‑size** — a proven prior design from old SP, re‑established here.
- **System‑1 (small context):** a fast, simple path. Compression + Ring‑2 overhead don't pay at short ctx, so System‑1 keeps latency low (closer to a plain cache).
- **System‑2 (large context):** the Spinor‑compressed + Ring‑2‑offload path — where the unlimited‑context / multi‑device envelope lives.
- **A crossover oracle predicts the System‑1 → System‑2 switch**, by context length, bandwidth pressure, and cache occupancy.

This is *why* the stage‑gating rule (§0) matters: System‑2 measured at small ctx in isolation looks slow — it is not meant to run there. [DESIGN here / PROVEN‑pattern in old SP]. Spec'd in contract **C2**, oracle explicit.

### 6.4 ARM aggregation (the HRR bank)
ARM (Algebraic Resonance Memory) is an HRR‑style associative memory in R_q. Each bound (k,v) pair is a single bound ring element; bindings accumulate by **ring addition** (commutes + associates → no consensus to merge); recall on query q gives a noisy value with noise ~1/√K. Local‑only by default; multi‑node ARM gossips slab deltas (§11.2). Capacity degrades with K, mitigated by periodic rebinding (default 1 h). **Golden‑ratio key generation:** the k‑th binding key has phase 2πkφ mod 2π (rest derived from a fixed seed), giving near‑orthogonality structurally by Three‑Gap (T7) with no Gram‑Schmidt cost; empirical capacity 0.83→0.15 cosine recall over K=1…64, expected to extend toward K=128 under φ‑spacing (Phase‑9 sweep). ARM writes are **journaled per‑token** so `sp_session_rewind` is precise (this is what makes MTP rollback exact — §8). [PROVEN] receipt ABI / [DESIGN] multi‑node fusion.

**OPEN QUESTIONS §6.** Measured Spinor‑KV ratio at bit‑exact? Ring‑2 residual‑recall cost vs recompute? Is the dual‑GPU "ship residues" path a 2‑prime CRT split of the *weights*, the *activations*, or both? The bandwidth model that says CRT‑residue exchange < full‑tensor NVLink.

---

## 7. eMeMo — episodic memory + continual learning on Ring 2 *(first‑class)*

Operator: **MeMo is core**; "memo as memory"; with MTP (§8), the old Phase‑4‑SPEC is redundant and deprecated. eMeMo is the *episodic* layer of MeMo — a dual‑model dialogue that mints an auditable, mesh‑shareable, order‑independent memory.

### 7.1 The dual‑model substrate (Executive + Memory)
Two models run as one system: an **Executive** (e.g. Qwen3‑0.6B) and a **Memory** model (trained differently — SFT on a factual corpus — not necessarily smaller). **M.0 PROVEN (stub):** a different‑checkpoint Memory `.sp-model` (Qwen2.5‑Coder‑0.5B, 24L×896H) loads, forwards, and produces **6/6 divergent logit positions** from the Executive (Qwen3, 28L×1024H) on identical tokens — `T_MEMO_M0_{EXISTS,LOADS,FORWARDS,DISTINCT}` all PASS (`lat-phase-4-memo-m0-stub`). **M.0‑real** (SFT on a factual corpus, same arch as Executive) is the follow‑on that unblocks M.3 (Frobenius‑lifted TIES merge needs matching tensor shapes). The dual‑model forward composes on the **same `Arc<FastRpcSession>` cDSP scheduler as Trick #1** — the scheduler is **kernel‑ and model‑agnostic** (cross‑PRIME 1.935× → cross‑MODEL 1.796× Exec+Memo concurrent forward, M.1). [PROVEN‑per‑record].

### 7.2 The SpinorReceipt ledger (the audit envelope)
Every dialogue turn mints a **64‑byte SpinorReceipt** (one cache line, distinct from the 63‑byte KV block): `turn_index@0, model_id@1, wall_us@4 (u32 LE), input_hash@8 [24 B trunc‑SHA‑256], output_hash@32 [24 B], n_input_tokens@56 (u32), n_output_tokens@60, _reserved@61, sentinel=0xA5@63`. Hashes cover the **actual DmaBuffer bytes** the model saw/produced (not token IDs) so any byte‑level divergence is caught. It is the **Trick #9 inter‑island integrity ABI**: the `0xA5` sentinel lets a receive‑side island detect cross‑marshalling corruption and re‑request. Wire format for the M.4 PoUW ledger, mesh broadcast, and cross‑island Garner verification. **[PROVEN]** (M.2 hexdump‑confirmed; M.4 ledger + mesh canonical Garner order PROVEN‑per‑record).

### 7.3 Portable memory profiles (the additive‑receipt thesis)
A user's memory = facts/context + a set of **commutative Z_q additive Spinor receipts**, fused at Frobenius‑lift load. Because additive deltas commute and associate, fusion is **order‑independent** and the profile is **peer‑shareable byte‑exactly** over the mesh (a Ring‑2 tenant) — the same canonical Garner order + decode determinism that makes ledger replay exact (`reference-lattice-decode-determinism`). [DESIGN] fusion / [PROVEN] receipt ABI + canonical order + mesh determinism.

### 7.4 Continual learning without gradient drift
Base frozen Z_q weights never change; "learning" = **appended algebraic receipts** + a PoUW ledger entry. No backprop, no catastrophic forgetting, no gradient drift. **Honest caveat [SPECULATIVE]:** "learning = matrix addition in Z_q" is clean *only if* the useful update decomposes into a commutative additive low‑rank delta. Whether a real continual‑learning signal survives that constraint is unproven — gate it before believing it.

**OPEN QUESTIONS §7.** The receipt fusion format (rank, scale, provenance) as a frozen contract (C5). Load‑time fusion vs runtime overlay (cf. the KSTE‑KV overlay). Is model‑level eMeMo the same mechanism as the agent‑level two‑tier working memory, or an analogue? Does M.0‑real survive as a faithful additive delta against the Executive?

---

## 8. MTP = Theorem T8 — a transaction protocol, not a decode hack *(first‑class)*

qwen35moe carries a NextN/MTP block (loaded‑not‑run) + a `-Draft` pairing **[PROVEN present]**. MTP is the explicit construction of the next K positions of the **Step‑10 Poncelet orbit in R_q** (Theory §11.5, T8). It is a **draft → verify → commit/rollback transaction**, made exact by the discrete substrate.

### 8.1 The protocol
1. The draft head (in‑model NextN, or a separate `-Draft` model — cf. eMeMo Memory‑as‑draft, §7) proposes **K candidate tokens** in one forward pass.
2. One **batched** target forward verifies them — batched K‑draft is **bit‑identical** to K sequential decodes in Z_q (T8 corollary).
3. **Acceptance is byte‑exact token‑id equality** (NOT a probability ratio) — the discrete substrate makes greedy accept/reject deterministic.
4. The Spinor blocks at the K speculative positions are written **uncommitted**. On accepting the first j ≤ K, those blocks flip to committed and the write index advances to t+j. The remaining K−j are dropped by `sp_session_rewind`, which **decrements the ring write index from t+K to t+j in O(1)** — no free, no payload scrub. T8.1 guarantees no fp residual is left because the Z_q algebra is exact.

### 8.2 What it consumes and what it costs
The L1 ABI primitives are **already frozen** and need no new surface: `sp_session_clone` (speculative fork), `sp_session_rewind(sess, n_rejected)` (rollback), the atomic cancel flag (abort mid‑verify). **VRAM (T8.2):** the compressed‑cache speculative state is ~130× smaller than the fp16 equivalent — Gemma3‑1B at ctx=4096, K=4 → ~8 MB speculative KV vs ~1 GB fp16. This makes MTP **affordable on hardware where fp16 makes it prohibitive** (S22U via Hexagon; RTX 2060 under fp16).

### 8.3 Where it lives, and the invariant
MTP belongs in the **L3 daemon as a transaction protocol over the Spinor journal**, composing with Trick #1 (draft on island A, verify on B/C — §10) and with eMeMo (Memory‑as‑draft, Executive‑as‑verify — one orchestrator commit away per the M.0 closure). **Absolute regression invariant:** with `SP_MTP_DRAFTER=0`, decode output is **bit‑identical** to the baseline single‑token path — MTP is a *speedup overlay*, not a quality trade. Gate `M_MTP_1`: bit‑identity **and** > 1.5× tok/s on code‑heavy prompts, against the Gemma3‑1B / Qwen3‑0.6B baselines. Loading a model without MTP heads with the gate on returns `SP_EUNSUPPORTED`; `sp_arch_info.mtp_variant` reports the draft‑head family. **[DESIGN]; Spinor ABI [PROVEN].** This deprecates the separate Phase‑4‑SPEC framing (folded into MTP + eMeMo).

**OPEN QUESTIONS §8.** Byte‑exact acceptance under temperature > 0 (needs a discretized‑sampling contract). In‑model NextN head vs separate draft as the default. Does Memory‑as‑draft (eMeMo) beat a dedicated small draft on acceptance rate?

---

## 9. The φ / Wythoff / Beatty / Zeckendorf machinery *(first‑class)*

SP already uses φ extensively — this section **organizes** it and fences against "a solution looking for a problem." (Caught 2026‑05‑30: a φ proposal was dismissed as redundant under low‑context amnesia precisely because the existing roadmap usage wasn't recalled. SP **already does** Fibonacci‑Prime DHT, Fibonacci KV sub‑sampling ⌊k·φ·N⌋, RoPE‑φ, Halton/Sobol QMC.)

| Tool | Role | Status |
|---|---|---|
| Three‑Gap (T7) equidistribution | the theorem under Fibonacci KV eviction (§4.3), ARM φ‑keys (§6.4), Fibonacci‑hash DHT load axis (§12), φ‑validator rotation (§13) | [PROVEN math] |
| Fibonacci KV sub‑sampling ⌊k·φ·N⌋ mod N | uniform temporal coverage on eviction | [DESIGN], `SP_KV_FIB` |
| Stern‑Brocot / Fibonacci convergents of φ | integer‑only approximation of irrational scales/angles on fp‑less islands | [DESIGN] |
| **Beatty/Rayleigh (φ, φ²) partition** | **stateless, collision‑free** KV/expert/task sharding across islands (Ring 2) with no lock table | [DESIGN] |
| Continued‑fraction φ = [1;1,1,…] | maximal irrationality → best worst‑case equidistribution for QMC sub‑sampling (Halton upgrade) | [DESIGN] |
| RoPE‑φ schedule | the research φ‑RoPE swap (vs the structural poly‑shift cache, §2.2) | [DESIGN] |
| Zeckendorf base‑φ rep | sparse weight/index encoding | [SPECULATIVE] — encode/decode cost likely dominates; gate first |

**The k‑way correction (operator).** Beatty/Rayleigh partitions the integers into exactly **two** complementary sequences (the φ, φ² Beatty pair). For **k‑way** island/expert partition, the correct primitive is **CRT residue classes** (mod the island count), not a "k‑way Beatty" — Beatty does not generalize to k > 2 as a clean complementary partition. Use Beatty for the 2‑way split, CRT residues for k‑way.

**Rule.** Any φ‑construct on a hot path must beat the boring integer alternative *measured*, or it stays a note.

---

## 10. Heterogeneous compute — Trick #1, the CRT compute islands (Ring‑2's compute face)

K **Compute Islands** (CPU‑AVX, NPU, GPU, DSP, mesh peer) each compute a **residue (mod q_i)** of the same matmul; the host **Garner‑recombines**; there is **no cross‑island sync until recombination**. The wall‑clock win is **parallel silicon + eliminated inter‑device bandwidth** (ship residues, §6.2), not per‑op NTT.

**The contract details that make or break it:**
- **Activation quant is part of the contract.** Islands want int inputs; the host quantizes fp32→int8 and dequants by `weight_scale × activation_scale` *after* Garner. Miss it → instant equivalence failure.
- **Numerical equivalence is the critical gate.** Garner sign/scale edge cases are where CRT projects die. The parallel‑win may fail honestly (e.g. NPU init‑dominated) without invalidating the pattern — gate the two separately.
- **Beatty/φ stateless partition** routes KV blocks / experts / tasks across islands without a lock table (2‑way Beatty; k‑way = CRT residues, §9).

**PROVEN substrate, [DESIGN] combination.** cDSP `mod_q`, NPU INT dispatch, and the Garner constants are each [PROVEN] in isolation. **Trick #1 silicon‑confirmed** via the `Arc<FastRpcSession>` dual‑vector‑context scheduler: cross‑PRIME 1.935× / 0.9699 overlap (K v0.alpha), 1.724× (K.beta.2.5c), and cross‑MODEL 1.796× (M.1 Exec+Memo). The scheduler is kernel‑ and model‑agnostic (§3.4, §7.1). The combined end‑to‑end forward across islands is Sprint TRICK‑1. The full ten‑trick manifesto (`reference-heterogeneous-soc-crt-tricks`) is the canonical heterogeneous‑SoC compute model — the discrete CRT substrate *is* the heterogeneous compute paradigm, replacing statistical‑fp partitioning.

**OPEN QUESTIONS §10.** Promote the Garner recombination into the L1 ABI as a first‑class service (C3)? 2‑prime vs k‑prime island scaling? A mesh peer as an island via recursive CRT (the endgame: the same Garner formula from L1 cache to QUIC packet)?

---

## 11. Lattice features — gated (the extension, not the center)

Everything above is a fast, compressed, portable inference engine + its memory architecture. The features here turn a node into part of a federated fabric. **All are gated, off by default, bypassed in the baseline path.** The regression invariant (§0) is binding: gates off ⇒ bit‑identical to plain inference, tested every release across four backends.

### 11.1 KSTE‑encoded KV cache + Friedman sieve (`SP_LATTICE_SIEVE`)
KSTE emits the 64‑byte tree (§4.2a): root = coarse fingerprint, internal nodes = residuals, leaves = the Spinor block. Two purposes: (1) dominance comparison is cheap (compare fingerprints without decoding leaves); (2) the **Friedman sieve** keeps only dominance‑incomparable trees, dropping cells strictly dominated by one already cached. The sieve runs on cache write, O(frontier) per insert. Gate off → writes go straight to the standard encoder; the standard decoder never consults the KSTE structure, so bit‑identicality holds. [PROVEN] encoder + sieve (E_CPU_6).

### 11.2 ARM gossip (`SP_LATTICE_ARM`)
Multi‑node ARM (§6.4): slabs are gossiped; a receiving node ring‑adds the delta to its bank. Ring sum commutes/associates → merge needs delivery, not consensus. Periodic rebinding bounds capacity; short‑term gossip is the primary value, not long‑term memory (that's eMeMo, §7). [DESIGN] multi‑node / [PROVEN] local bank.

### 11.3 CRT‑sharded inference (`SP_LATTICE_CRT_SHARD`)
One inference across two nodes by splitting the NTT across q₁/q₂; outputs CRT‑reconstructed at the end. Bandwidth is small (~30 bits/scalar in residue domain); **latency is the binding constraint** — synchronizing twice per layer puts the inter‑node round‑trip on the per‑token critical path (5 ms LAN → +320 ms/token; 100 ms WAN → non‑starter). LAN/batch‑bound today; relaxing to per‑block sync (every ~4 layers) at some accuracy cost is the open WAN path. This is the *network* face of Trick #1 (§10); the *local* face (islands inside one SoC) has no latency tax. [DESIGN].

### 11.4 DHT participation (`SP_LATTICE_DHT`)
A **2‑Axis Fibonacci‑Prime Address Space.** **Axis 1 (semantic):** prime factorization of lattice slab indices routes by semantic adjacency (related content at nearby prime indices, by KSTE construction). **Axis 2 (load):** node addresses within a slab are `frac(node_id · φ)` — Knuth Fibonacci hashing, which by Three‑Gap (T7) maximally distributes load regardless of ID distribution. The two axes are mathematically independent, so traffic skew on one does not propagate to the other. Carries sieve deltas, ARM slab updates, block propagation, and shard recruitment. [DESIGN].

### 11.5 Token‑economy tracking (`SP_LATTICE_TOKENS`)
Local ledgers: a **work‑token** ledger (verified compute served) and a **discovery‑token** ledger (dominance‑incomparable KSTE trees contributed). Settled at block boundaries with Merkle proofs. Off by default because chain participation is opt‑in consent, not because tracking is expensive (a few hundred bytes/layer/token). Feeds §13.

---

## 12. Network and protocol

The carrier for §11 once data crosses between nodes. libp2p‑compatible swarm, long‑lived Ed25519 identity, TCP + optional Noise (QUIC on the roadmap; the L3 daemon already speaks a QUIC peer wire [PROVEN‑per‑record]). The 2‑axis routing (§11.4) is layered on Kademlia: k‑buckets partitioned by semantic axis, sorted within by Fibonacci‑hash distance; lookups walk the semantic axis, break ties on load.

**Wire formats.** (1) **KSTE trees** — 64 bytes/node, pre‑order, index‑relative, little‑endian; median tree ~500 bytes. (2) **ARM updates** — one R_q element (N=256, dual‑prime 60‑bit) = 2 KB/slab delta (ring sum is the delta; delta‑encoding is a future optimization). (3) **CRT residue blobs** — per‑layer activations at ~30 bits/scalar (Llama‑3‑8B d=4096 → ~15 KB/layer/token → ~48 MB/s at 100 tok/s; gigabit‑LAN‑bound, hence §11.3's LAN constraint). **Gossip:** 8‑peer fanout biased by semantic slab; dedup by content hash (recently‑seen set, 5‑min TTL); blocks propagate aggressively (fanout 32) and validate‑on‑receive.

---

## 13. Blockchain / PoUW — scaffolding, not specification

*This section is explicitly scaffolding (the most revisable part of the design); parameters are starting points. The mathematical core is fixed; the chain constants are a snapshot.*

**Two‑token economy.** A **Work token (W)** for verifiable inference contributions and a **Discovery token (D)** for dominance‑incomparable KSTE‑tree contributions, fungible via a constant‑product AMM, logarithmic emission. **Proof‑of‑Useful‑Work** = **dominance verification**: minting D requires a Merkle proof that a submitted tree is incomparable against the on‑chain frontier; minting W requires a requester‑countersigned work attestation. The useful‑work caveat is honest: useful‑work proofs are harder to make adversary‑resistant than wasted‑work (a colluding requester/server pair can mint W against fake sessions — mitigated by rate‑limiting + reputation + slashing). **Consensus:** BFT 2/3 stake quorum; **proposer chosen by Golden‑Ratio rotation** — `r_b = frac(b·φ)` indexes a stake‑weighted arc partition, which by Three‑Gap (T7) gives optimal stake‑weighted fairness with **no random beacon** and independent verifiability. **Frozen for the chain's life:** the NTT/CRT primes (changing them invalidates every prior dominance proof), the dominance comparison itself, and the two‑ledger structure. Everything else is validator‑votable with a six‑month cooldown. **M.4 PoUW ledger + mesh canonical Garner order [PROVEN‑per‑record].**

---

## 14. Failure modes and mitigations

**Sybil** — stake‑weighting nullifies consensus weight; 2‑axis routing + Fibonacci‑load axis bound DHT damage to local. **Cache poisoning** — dominance‑at‑write means content matters, not just tree shape; limits to genuinely‑novel‑by‑content submissions (doesn't stop semantic poisoning). **Eclipse** — 2‑axis routing partitions the table by slab, raising the bar; diverse bootstrap peers (ASN/geo). **Free riders** — incentive alignment (no gossip → no W; no discovery → no D); pure consumers tolerated at the margin, can't scale. **ARM overflow** — periodic rebinding bounds the working set; long‑term memory is eMeMo's job (§7), out of the gossiped slab. **Network partition** — BFT quorum means a <2/3 sub‑net can't produce blocks; longer‑chain rule on heal. **Collusion** — standard BFT bound (>1/3 stalls, >2/3 controls); defense is decentralized stake distribution, no cryptographic guarantee beyond it.

---

## 15. Comparison to prior work

**Hivemind / Petals** — volunteer‑GPU LLM inference; we differ by phone‑class compression + an on‑chain accounting layer Petals avoided. **Bittensor** — closest analogue to the work‑token; we measure contribution by dominance‑frontier expansion, not peer ranking. **DiLoCo** — relaxed gradient‑sync frequency informs our relaxed‑sync CRT‑shard question (§11.3). **Filecoin/Storj** — the precedent for verifiable‑useful‑work accounting (proof‑of‑replication ↔ our proof‑of‑useful‑work). **YaCy** — P2P search that failed for lack of an incentive layer; the discovery‑token is the response. **Render** — compute‑for‑tokens at scale, simpler (no useful‑work proof). **Bitcoin/Ethereum** — validator‑rotation primitive + BFT‑quorum + settlement‑record + slashing playbook borrowed; no general VM (chain logic fixed at protocol level).

---

## 16. Open questions (the bounded unknowns)

Carried from RFC‑001 §10, the v0 corpus, and the STATE blockers:

1. **The remaining headline numbers are unmeasured.** The *memory* envelope is now measured (C2.1: 910× resident @32k, off‑NVMe retrieval @7.57 µs/read, 8×@+0.69% PPL). Still [TARGET]: the Spinor *per‑vector codec* ratio *at bit‑exact* (the codec is lossy 29/31 today) and "beats 40 tok/s" on the **35B‑A3B** (the 0.6B WIRE gap is down to ~1.34×). If that codec ratio is only ~3× at bit‑exact, or the 35B MoE is slower than the hier‑KV baseline after wiring, the value thesis is still partly open. **Measure before believing.**
2. **Ring‑2 residual recall** may cost more than recompute; **dual‑GPU residue exchange** wins only if CRT‑residue bandwidth < full‑tensor transfer — unproven bandwidth model.
3. **Entropy‑container spare‑bit mask cost** can erase the fetch savings; ship only if measured net‑win.
4. **eMeMo additive‑only** may not capture real continual learning (§7.4 [SPECULATIVE]).
5. **Trick #1** init‑cost / precision / Garner‑sign edges; shape‑dependent parallelism (compute‑ vs data‑bound).
6. **N ≤ 512** caps cyclotomic NTT; a third prime is a Phase‑5 cascade.
7. **Bit‑exact is conditional** — greedy + fixed spec‑decode K + same checkpoint/backend; state the precondition that changed rather than widening tolerance.
8. **Fork tax** — "one object" presupposes de‑duplicating the engine↔core forwards/dequant/enums.
9. CRT‑shard real‑time vs batch (WAN sync relaxation); validator hardware diversity; shared‑KV privacy.

---

## 17. Crate boundaries (bounded engines)

```
math-core (C)  — PRIMITIVES: Barrett, Frobenius lift, NTT-CRT (N<=512), KSTE, Spinor (KV + receipt),
                 Garner. Reference forward = the validation oracle. THE substrate of PPT.
arena (C)      — the O_K object: packed weights, <= source size; runtime entropy-dense container.
.sp-model fmt  — min-entropy disk body + runtime-expansion contract + arch_struct (Appendix B).
L1 ABI (frozen)— the seam: load/unload, session, forward entry, arch-query; (PROPOSED) Garner service,
                 (PROPOSED) Ring-2 offload/recall + Spinor-KV API (Appendix A).
backends       — CPU AVX-512(VNNI), CUDA(dp4a/PTX), Vulkan, Hexagon(vrmpy). SAME primitives, BIT-EXACT.
L3 daemon(Rust)— orchestration: island detect + Beatty dispatch, MTP transactions, eMeMo ledger,
                 Ring-2 disk/mesh offload, Garner recombine. No math truth here.
```

**The cross‑track gap [PROVEN diagnosis]:** the primitives exist; the per‑backend forward shells still call scalar f32 (HX.3b fixed Hexagon → vrmpy 1.04×; AVX/CUDA/Vulkan pending — the `WIRE-*` sprints). Until the shells call the integer + Spinor‑KV primitives, none of the envelope is realized — only correctness. **Fork tax:** engine and core duplicate forwards / dequant / row_bytes / arch‑id enums; "one object" presupposes de‑duplication.

---

## 18. Honest scorecard + where this breaks

**[PROVEN].** PPT forward bit‑exact to llama.cpp for qwen3 / qwen2.5 / gemma3 / gemma4 / qwen35moe (the bolt‑on works); NTT‑CRT dual‑prime byte‑exact (N≤512) + Bluestein; Frobenius Q4/Q8 + arena (zero‑inflation); Q4_K + Q6_K k‑quant dequant; KSTE + Friedman sieve; Spinor encode/decode + 64‑byte receipt ABI (silicon‑confirmed); **C1 — reducing `.sp-model` (~17%) + output‑lossless** (the first real envelope number); M.0 dual‑model distinct (stub); M.4 PoUW ledger + mesh canonical order; L3 daemon (chat/dialogue/ledger/QUIC); Hexagon HVX Barrett/mod_q/NTT/Bluestein; **HX.3b vrmpy 1.04× > ARM fp32, byte‑equal**; QNN HTP NPU 64/64 byte‑exact in Unsigned PD; cross‑backend determinism; Trick #1 dual‑context 1.935× / cross‑model 1.796×; **C2.1 two‑ring memory envelope — ±1 recall router + Optane Ring‑2 (7.57 µs/read) + (sink+W) window shrink + compact‑and‑spill fusion: 910× resident KV @32k, needle retrieved off physical NVMe (poison‑gated), 8× sparsification @ +0.69% PPL, bit‑exact when off** (engine `f8ea920`/`7896bc4`); **reducing loader — GGUF → ~50%‑smaller `.sp-model`, bit‑faithful forward on gemma‑3 + qwen3** (6/6 E_FMT gates, Position paper 02); **WIRE‑CPU integer pipe 0.84 → 39.52 tok/s (47×), ~1.34× behind llama.cpp Q8_0.**

**[TARGET]/[DESIGN] — the actual value, not yet measured/built.** Spinor‑KV per‑vector codec ratio *at bit‑exact* (distinct from the recall envelope — the codec is still lossy 29/31); sub‑Q4 converter ratio; the **40‑tok/s north‑star on the 35B‑A3B** (the 0.6B WIRE gap is closed to ~1.34×; the MoE system gate is the open one); Ring‑2 **multi‑device** residual recall + dual‑GPU residue‑sharing (single‑device offload now [PROVEN], C2.1); Trick #1 combined end‑to‑end; the MTP transaction loop; eMeMo fusion; System‑1/2 crossover oracle; int‑end‑to‑end (no per‑matmul fp dequant).

**Where it breaks (read this before celebrating).** (1) The *memory* envelope is now measured (C2.1: 910×, off‑NVMe retrieval, 8×@+0.69%), but the *speed* north‑star (40 tok/s on 35B‑A3B) and the *Spinor per‑vector codec ratio at bit‑exact* are still unmeasured — if that codec ratio is only ~3× at bit‑exact, or the 35B MoE is slower than the hier‑KV baseline after wiring, the value thesis is still partly open. (2) Ring‑2 recall may cost more than recompute. (3) Entropy‑container mask cost may erase savings. (4) eMeMo additive‑only may not capture real learning. (5) N≤512 is a hard cap. (6) Bit‑exact is conditional on greedy + fixed‑K + same checkpoint/backend. (7) The fork tax must be paid for "one object" to be true.

---

## Appendix A — L1 ABI (the math‑core C boundary)

*Updated from `PPT-LAT-L1-ABI-v0`. v0's three tear‑down axes (caller‑allocates, Send‑but‑not‑Sync session, named discrete‑algebra error surface) are PROVEN: the ABI shipped through Phase 2‑L1 (`lat-phase-2-l1-closed`, math‑core canonical inference path under the frozen L1 ABI; Qwen3‑0.6B end‑to‑end real). Deltas from v0 marked **[Δv0]**.*

**Object lifetimes.** Two opaque types: `sp_model` (read‑only after load, many sessions per model) and `sp_session` (single‑thread state: KV + ARM + sieve + arch scratch). Constructors are L1's; destruction is the caller's via the matched destroyer. `sp_model_load / sp_model_unload / sp_session_create / sp_session_destroy`. The `cancel_flag` is an L2‑owned `volatile _Atomic bool*` that must outlive the session (held inside an `Arc<AtomicBool>` so the address never dangles — the UAF‑proof inversion).

**Memory ownership — caller‑allocates on the hot path.** Every per‑step buffer is caller‑allocated; L1 never `malloc`s anything L2 frees. Sizing comes from `sp_model_arch(model, *out sp_arch_info)` once at load. **[Δv0] `sp_arch_info` has grown** beyond the v0 fields (`vocab_size, hidden_dim, n_layers, n_heads, n_kv_heads, head_dim, rope_base_microcents, swa_window, ffn_variant, norm_variant, tied_embeddings, arch_id`): it now also carries `preferred_precision` (the fp16‑swivel selector, §5.2), `mtp_variant` (§8), and per‑arch tails (e.g. q36 GDN/MoE config). Growth is via the reserved arch_struct tail (Appendix B) — the struct may grow **without** a format/ABI version bump; zero is the "unspecified" sentinel. *(Known historical gap, STATE: engine wrote `qwen3_config` while math‑core expected `sp_arch_info` per the frozen spec — the arch_struct divergence; reconcile before any new arch. Read the frozen `sp_status.h` / arch headers before drafting a handoff — the L1 ABI codes "must not be renumbered.")*

**Forward — two functions.** `sp_prefill_chunk(sess, tokens, n, *out logits_last, cap)` and `sp_decode_step(sess, token, *out logits, cap)`. Asymmetric cost shape (compute‑ vs bandwidth‑bound); `cap < vocab_size` → `SP_EBADARG`.

**Session manipulation — speculative‑decode‑shaped from day one (this is what MTP, §8, consumes).** `sp_session_clone` (deep‑copy KV+ARM+sieve = the spec‑fork), `sp_session_rewind(sess, n_tokens)` (the O(1) ring‑pointer reject; ARM writes journaled per‑token so rewind is precise), `sp_session_position`. **No new surface needed for MTP** — already frozen at `lat-phase2-contract-frozen`.

**[Δv0] arch_id enum** — v0 stopped at `DEEPSEEK_V4=4`. Current: `LLAMA3=1, QWEN3=2, GEMMA3=3, DEEPSEEK_V4=4, …, QWEN25, GEMMA4, QWEN36=8` (`SP_ARCH_ID_QWEN36=8`, with the engine shadow enum kept in sync — part of the fork‑tax reconciliation).

**[Δv0] dtype for the reducing codec** — `SP_DT_OK_Q4=11` (O_K‑lifted int4, nibble‑packed, block_size 32) is the C1 reducing codec; `SP_DT_OK_Q8=10` for Q8/F16 sources; `SP_DT_FROBENIUS_SCALE_FP32=12` is the per‑row scale sibling. (v0 listed these as planned; OK_Q4 is now PROVEN/WIRED, gate `E_PARITY_2`.)

**Determinism.** `sp_session_config { max_context, deterministic, arm_bank_kb, sieve_capacity, flags }`, immutable for the session. `deterministic=true` is the bit‑exact (T_FRO_4 / top‑1) gate; production runs ULP‑tolerant. Reduction order is baked into kernel selection at create, so it can't toggle mid‑session.

**Error surface (names the discrete‑algebra failure modes).** `SP_OK=0`; generic −1..−6; load/arch −10..−13 (`SP_EBADFORMAT, SP_EBADARCH, SP_ETOKENIZER_HASH, SP_EVOCAB`); **discrete‑algebra −20..−26** (`SP_ESPINOR_BADBLOCK, SP_EVHT2_DOMAIN, SP_EMOBIUS_PERM, SP_EOK_NORM, SP_EFROBENIUS_QUANT, SP_ENTT_OVERFLOW, SP_ERING_DEGREE`) — every T1..T7/E9/E10 invariant maps to one; lattice −30..−33 (`SP_ESIEVE_FULL, SP_EARM_BANK_FULL, SP_EDOMINANCE_CYCLE`, **`SP_ECONTEXT_FULL`** = position hit max_context → L2 triggers Fibonacci sub‑sampling eviction (§4.3) and retries, structurally distinct from `SP_ENOMEM`); backend −40..−43. `sp_last_error()` returns the thread‑local detail.

**Threading.** `Model: Send+Sync` (immutable after load); `Session: Send` but **not Sync** (`&mut self` on every step method); `Cancel(Arc<AtomicBool>): Send+Sync` automatically — cancellation is a single relaxed atomic store, no FFI crossing, no UAF window.

**Out of scope for v1 ABI (deliberate):** streaming‑logits callbacks, L1‑side multi‑session batching, in‑process sampler, tokenization (L2 owns the blob; L1 verifies the hash). **[Δv0] PROPOSED additions** (C3): a Garner‑recombination service (§10) and Ring‑2 offload/recall + Spinor‑KV hooks (§6).

---

## Appendix B — `.sp-model` byte layout (the reducing artifact)

*Updated from `PPT-LAT-SP-MODEL-v0`. **The single biggest correction:** v0 §1 listed "compression on disk" as a **non‑goal**; v1's C1 finding is the opposite — the converter **REDUCES** (the body is ≤ source quant; §5). `sp_model_load` stays pure mmap + pointer setup (no malloc of tensor data, no memcpy of tensor data — the file IS the layout). Deltas marked **[Δv0]**.*

**Header (fixed 512 B at offset 0).** `magic "SPMD"`, `version_major/minor`, `header_size=512`, `arch_id` (Appendix A enum — **[Δv0]** now through QWEN36=8), `arch_struct_size`, `arch_struct_capacity=256`, **`arch_struct[256]`** (memcpy‑direct `sp_arch_info`, zero‑filled tail; **[Δv0]** grows via this reserved tail without a version bump — see Appendix A), `tokenizer_hash[32]` (SHA‑256 of the paired `.sp-tokenizer`), `vocab_size`, `tensor_count`, `tensor_table_offset` (=512), `tensor_data_offset` (multiple of 65536 — Windows `MapViewOfFile` granularity, also GDS‑compatible), `file_size`, `created_unix_seconds`, `transcoded_from`, `header_crc32`, reserved tail. Forward‑compat: v0 readers refuse `version_major≠0`; new fields land in the reserved tail before the header grows.

**Tensor table (256‑B fixed entries, sorted by `name_hash` for O(log N) binary search + one strcmp).** `name[80]`, `dtype_id`, `n_dims`, `dims[8]` (u64 elements, unused=0), `offset_in_data` (64‑aligned), `size_bytes`, `block_size`, `block_count`, `blake3[32]` (opt‑in verify via `SP_VERIFY_TENSORS`), `name_hash` (xxh3_64), reserved[40].

**dtype_id.** Continuous 1‑3 (F32/F16/BF16); **PPT‑native quant 10‑12** (`OK_Q8`, **[Δv0] `OK_Q4` — the C1 reducing codec, PROVEN**, `FROBENIUS_SCALE_FP32`); discrete‑algebra 20‑31 (`SPINOR63` = 63 logical + 1 pad byte, `RING_RESIDUE_CRT_30_30`, `OK_INTEGER`). `block_size × block_count == size_bytes` is the loader sanity invariant.

**The Spinor 63→64 padding decision (unchanged, [PROVEN]).** On‑disk padding to 64 B/block, byte 63 = sentinel `0xA5`. Three structural reasons: (1) the caller‑allocates ABI forbids a scatter‑at‑load arena (would double RAM + add an O(N) copy, breaking "the file IS the load"); (2) 64‑B SIMD loads (`vmovdqu64` / NEON) read past byte 63 — on‑disk padding makes that well‑defined; (3) the `0xA5` sentinel (0b10100101, distinct from 0x00 and 0xFF) is cheap integrity, scanned by the opt‑in verifier → `SP_ESPINOR_BADBLOCK`. This is the same sentinel as the 64‑byte SpinorReceipt (§7.2) — the Trick #9 integrity ABI — but the two structures serve different roles (on‑wire KV record vs per‑turn audit envelope); do not conflate.

**Transcoder (`sp-transcode`, engine repo, offline one‑shot).** Per‑tensor: unquantized (norms/biases/RoPE inv‑freq) copied bit‑for‑bit; **[Δv0] quantized → codec‑by‑source** (Q4‑class source → `OK_Q4` + Frobenius scale sibling; Q8/F16 source → `OK_Q8`) — the reducing principle. Rank‑3 expert weights pack with `rows = dims[1]·dims[2]` (the C1 fix). Arch detection pulls `general.architecture`, maps to `arch_id`, fills `arch_struct`. **Spatial‑locality constraint:** `<weight>.scale` must be physically adjacent to `<weight>` in the data region so the OS prefetcher pulls both in one readahead (cold‑load 10 µs vs 150 µs/layer). `--verify` warns on non‑adjacency and checks the round‑trip (transcode → load → forward → **top‑1 == oracle**, the C1 gate).

**Load procedure (`sp_model_load`, ~200 lines).** open + stat → single mmap → memcpy 512‑B header → verify magic/CRC/file_size/version → memcpy arch_struct → set tensor table + data pointers → verify alignments (table %64, data %65536) → SHA‑256 the tokenizer, match `tokenizer_hash` (else `SP_ETOKENIZER_HASH`) → mmap tokenizer separately → return. No malloc in the hot path; pages fault in lazily. **The swivel** (`sp_model_to_<arch>`, §5) runs after load to expand the min‑entropy body into Ring‑1's runtime container.

---

## Appendix C — Mode D (heterogeneous Hexagon: HVX / HTP / ISP)

*From v0 Systems Appendix C + the proven Sprint A–K / M Mode‑D discoveries. The three modes: **Mode C** (QNN HTP matmul + HVX everything‑else) is the production target; **Mode D** (ISP‑as‑spectral‑reconstructor, Spectra 680 doing skeleton+residual band fusion at 18‑bit fixed point in parallel with HTP matmul) is research — pieces validated, not yet strung together.*

**Signed PD developer path (corrected — the "needs vendor cooperation" framing is overstated for dev‑account holders).** Signing tools ship with the Hexagon SDK (`hl_signnow` inline; `hl_signsav`+`hl_signuse` split‑build); `testsig` on device authorizes dev‑signed binaries to the Signed PD (VTCM + real‑time priority + low‑latency drivers unlocked). **Anti‑flag:** never set `vendor.fastrpc.process.attrs=0x8` (forces the unsigned sandbox). Knack's host has the full Qualcomm SDK inventory + a developer account (read‑only reference catalog; anti‑contamination still applies to code).

**Mode‑D bridge marshalling (PROVEN‑per‑record, S22U, Path B Unsigned PD).** `DSPRPC_CONTROL_UNSIGNED_MODULE` before `remote_handle_open`. IDL must inherit `remote_handle64` (not the u32 `remote_handle`); host calls `remote_handle64_{open,invoke,close}`. URI `file:///lib<name>_skel.so?<iface>_skel_invoke&_modver=1.0&_dom=cdsp`. Skel link needs the SDK `hexagon_toolchain.cmake` PIC_SHARED template + `rtld_init.a` whole‑archive + SigVerify_* stubs (Unsigned PD; a security vuln to remove on a future Signed‑PD migration). DmaBuffer: heap 25 + `RPCMEM_TRY_MAP_STATIC`; **exact‑size match with the IDL Len at invoke** (off‑by‑one = silent `AEE_EUNSUPPORTED` — the recurring footgun).

**V69 HVX expert practices.** SSR:XA per‑thread vector‑context attachment (V69: SSR:XA={4,5,6,7}→ctx 0..3; 4 scalar threads / 2 vector contexts → 2 HVX + 2 scalar‑only parallel). `.tmp` loads skip VRF writeback for VLIW density; `.cur` writes VRF. VTCM 8 MB — pin Frobenius scales + KSTE LUTs via `qurt_mem_l2cache_lock`; **per‑stage twiddle arrays land 4‑byte‑aligned, not 128‑byte** → aligned `vmem` from stage 2+ reads wrong data; use `vmemu` or pad each stage to 128 B (the NTT VTCM misalignment gotcha). 32×32→64 widening = `Q6_W_vmpye_VwVuh` + `Q6_W_vmpyoacc_WVwVh` (2‑instruction, per HVX PRM §151) for Barrett/NTT. Halide schedule: tile 128×4 + unroll 4 + prefetch 2‑iters + 128‑B alignment; `q_bits ≤ 14` (32‑bit saturation in Halide vs wrap in the scalar ref); 128‑multiple shapes via tail‑loop predication.

**Hyper‑V / WAITPKG caveat (Beast Canyon dev host).** CPUID.7.0.ECX[5]=0 because the Hyper‑V root partition masks WAITPKG (VBS=2); VMCS bit 26 also clear → UMONITOR #UD even ignoring CPUID — silicon‑enforced, distinct from the *structurally‑bypassable* 2 MB‑large‑page channel‑select identity mapping (TS offline‑map bypass: run the channel oracle once on bare‑metal Windows, cache `.bin`, restore Hyper‑V; 2 MB `MEM_LARGE_PAGES` bits 0‑20 identity‑map to physical at runtime).

---

## Appendix D — Theorems (reference; canonical statements live in `PPT-LAT-Theory.md`)

| # | Statement (informal) | Used by |
|---|---|---|
| T1–T6 | The 13‑step PPT substitution is exact in Z_q / O_K; Frobenius lift identity; negacyclic ring arithmetic exactness | §2 forward, §4 weights |
| **T7 (Three‑Gap)** | Stepping by φ gives bounded‑discrepancy equidistribution regardless of N | §4.3 KV eviction, §6.4 ARM keys, §9, §12 DHT load axis, §13 validator rotation |
| **T8 (Step‑10 Poncelet orbit)** | The next K positions are constructible in R_q; batched K‑draft is bit‑identical to K sequential; rejection is O(1) ring‑pointer rewind; **T8.1** no fp residual after rewind; **T8.2** compressed speculative state ~130× < fp16 | §8 MTP |
| E9.1 | Frequency‑axis equidistribution (the analogue mirrored by T7's temporal‑axis coverage) | §2.2, §4.3 |
| E10 | (canonical — see Theory) | error surface (Appendix A) |

*Production status (Theory §10): KSTE 21/21 production; Q4 mixed‑precision under calibration → now C1‑PROVEN reducing for the gate; ARM math‑validated, integration pending (eMeMo, §7). Frozen + shared (anti‑contamination §12 of Theory): the Spinor format, the CRT primes, the KSTE algorithm.*

---

*End of PPT-LAT-Systems v1. The forward plan lives in C1–C6; the proven record in PPT-LAT-STATE.md; the math in PPT-LAT-Theory.md; the north star in RFC‑001.*
