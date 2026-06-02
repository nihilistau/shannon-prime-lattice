# PPT-LAT — PROJECT STATE LEDGER (the proven record)

**This is the authoritative record of what is PROVEN. Read it first. Trust it. Build on it. Do NOT re-derive it.**

> To the next session/agent: this is the **20th rewrite**. Six months of validation live behind these lines. The operator remembers; you don't. **Your default is TRUST.** Each PROVEN line cites its evidence (commit / tag / gate / closure doc). If — and only if — you have a concrete reason to doubt a specific line, the reverify command is given; running it is the exception, not the warm-up. Re-proving the whole stack from scratch *is the failure mode this project has hit 20 times.* Don't.
>
> Status vocabulary: **[PROVEN]** evidence cited · **[WIRED]** built + in-tree, gated · **[DESIGN]** spec'd, unbuilt · **[TARGET]** a number to measure, not yet measured · **[SPECULATIVE]** idea. Promotion requires a gate + an entry here.
>
> Companion docs: **RFC-001** (the architecture/why) · the **C1–C6 contracts** (forward work) · per-cell **SESSION-CLOSED-*.md** (closure detail) · the **roadmap** (sequence). This ledger is the *backward* record; the contracts are the *forward* plan.

Last updated: 2026-06-02.

---

## 0. The frame (so the record is read correctly)

**PPT-ARM is the primary, load-bearing product** (the 13-step transformer-forward replacement + the Spinor KV / two-ring memory architecture). The **Lattice fell out of it.** The value is the **envelope** — inline KV compression → unlimited context, Ring-2 offload + residual/CRT bandwidth bypass → multi-device, speed on integer pipes — with **bit-exact as the invariant floor, not the headline.** See RFC-001.

**Crucial gating rule (operator, 2026-06-02):** *the system does not work in isolation.* A stage will be slow / miss a system-level number that it only hits once the rest of the envelope is in place (e.g. tok/s is not achievable until the Spinor cache + Ring-2 + island sharding are wired). **Therefore a stage is gated on ITS OWN correctness/metric (bit-exact output; the kernel's own throughput; the compressor's own ratio), NEVER on end-system tok/s.** Do not declare a stage failed because the assembled-system number isn't there yet — that number is a *system* gate, measured only when the envelope is assembled. Penalizing a stage for a system number it structurally cannot hit alone is a category error.

---

## 1. PROVEN — PPT forward (the bolt-on works on real models)

The PPT discrete forward reproduces stock models **argmax bit-exact to llama.cpp**. This is the precondition that licences compression/context/speed on top.

| Model | Evidence | Reverify | Status |
|---|---|---|---|
| Qwen3-0.6B | core E_CPU_2 / forward gates | `ctest -R E_CPU_2` | [PROVEN] |
| Qwen2.5 | qwen25_forward gates | core suite | [PROVEN] |
| Gemma3-1B | M_GEMMA3_CPU + T_FRO_4 PPL | `ctest -R T_FRO_4` | [PROVEN] |
| **Gemma4-E2B** | M_GEMMA4 PPL gate, top-1 bit-exact oracle | `ctest -R M_GEMMA4` (engine) | [PROVEN] this session |
| **Qwen3.6-35B-A3B (qwen35moe)** | M_QWEN36 top-1 bit-exact (3/3 `5444 8 198`), 218s | `ctest -R M_QWEN36` (core) | [PROVEN] this session |

qwen35moe is a **Gated DeltaNet (Qwen3-Next) + 256-expert MoE + IMRoPE hybrid**, NOT Mamba2 (the old GGUF-INVEST doc mislabeled it — superseded). Full per-block validation: GDN recurrence, MoE router/experts/shared, gated full-attn — all matched oracle fingerprints. Closure: `SESSION-CLOSED-lat-3-moe-forward.md`. Commits: core `568b678→d8e614f`.

---

## 2. PROVEN — math-core primitives (the substrate)

| Primitive | Evidence | Status |
|---|---|---|
| Barrett mod-mul (+ nvcc paired-register fix) | NTT/mod_q tests; HVX K.beta.2.5b | [PROVEN] |
| Frobenius lift Q4/Q8 + arena packed weights (zero-inflation) | E_CPU_*, arena tests | [PROVEN] |
| **Q4_K + Q6_K k-quant dequant** (ggml-exact) | weight_dtype; qwen35moe conv fingerprint matched | core `25809d8` | [PROVEN] this session |
| NTT-CRT host, dual-prime, byte-exact (negacyclic, N≤512) | ntt_crt tests | [PROVEN] |
| NTT N≤512 frozen-prime cap (2N\|q−1) + Bluestein arbitrary-N≤512 | NTT.0–5 closures | [PROVEN constraint] |
| KSTE encoder + Friedman sieve | E_CPU_6, sieve tests | [PROVEN] |
| Spinor block: KV encode/decode + 64-byte receipt ABI | vht2 / spinor tests; silicon-confirmed | [PROVEN] |
| Garner 2-prime recombination constants | ntt_crt.c | [PROVEN] |

---

## 3. PROVEN-PER-RECORD — Hexagon / backend / daemon track

*(Reported via the operator's session logs + memory; in sibling repos — `engine`, `sp_compute_skel`, `sp_daemon`. Trust the tags/closures; do not re-run unless touching that code.)*

| Item | Evidence | Status |
|---|---|---|
| Hexagon HVX: Barrett, mod_q matmul, NTT.0–5c, Bluestein | tags lat-phase-2-... ; closures | [PROVEN-per-record] |
| **HX.3b: vrmpy int8 forward = 1.04× faster than ARM fp32, byte-equal** | tag `lat-phase-2-hx-3b-hvx-vectorized`; CLOSURE-HX-3b.md | [PROVEN-per-record] — *the integer-substrate-matches-fp32 proof point* |
| Cross-backend determinism (ARM ↔ cDSP scalar) | WIRE-HEX-FINISH | [PROVEN-per-record] |
| QNN HTP NPU dispatch in Unsigned PD (1.329 ms execute, 64/64 byte-exact) | K.2-spike closure | [PROVEN-per-record] |
| Mode-D FastRPC bridge (S22U), concurrent dispatch (Arc<FastRpcSession>) | Sprint K closures | [PROVEN-per-record] |
| L3 daemon: chat + dialogue + ledger + QUIC peer wire | daemon closures | [PROVEN-per-record] |
| M.4 PoUW ledger + mesh canonical Garner order | M.4 closure | [PROVEN-per-record] |
| Trick #1 substrate (dual HVX vector contexts 1.935×) | Sprint K v0.alpha | [PROVEN-per-record] |

**Honest negatives also proven (do not re-litigate):**
- NTT-attention is **slower** than fp32 dot at HD ≤ 256 (~0.15–0.72×). The substrate win is over HD (poly length), not ctx. Speed comes from compression + bandwidth-bypass + integer pipes + multi-device, NOT from NTT. [PROVEN-per-record: NTT.6]
- HX.3b chat-shape inner loop is **memory-bandwidth-bound**, not ALU-bound → v2 wsum-precompute only got 1.065× (gate was 1.20×, FAILED honestly). Attack bandwidth (prefetch/VTCM/2-row), not ALU. [PROVEN-per-record]

---

## 4. The ARM memory architecture — regime split (System-1 / System-2)

**Prior proven design (old SP, to be re-established here):** the KV/memory path is **regime-adaptive**, not one-size:
- **System-1 (small context):** a fast simple path — keep latency low where compression overhead wouldn't pay. *(Old SP ran small-ctx differently to hold speed.)*
- **System-2 (large context):** the Spinor-compressed + Ring-2-offload path — where the 120× and unlimited-context envelope lives.
- **A crossover oracle predicts when to switch** System-1 → System-2 (by ctx length / bandwidth pressure / cache occupancy).

[DESIGN here / PROVEN-pattern in old SP]. This is *why* §0's gating rule matters: System-2 looks slow at small ctx in isolation — it's not meant to run there. Belongs in contract **C2** (ARM memory) with the oracle spec'd explicitly.

---

## 5. TARGET — the envelope (the value; measure, don't assume)

These justify the project and are **not yet measured here**. They are the point. Measuring them is the next phase's job (contracts C1/C2).

| Target | Where measured | Status |
|---|---|---|
| Spinor inline KV compression ratio (~120×) at bit-exact | C2 | [TARGET] |
| `.sp-model` converter REDUCTION ratio (≤ source; sub-Q4) | C1 | [TARGET] |
| tok/s vs the bar: **beat llama.cpp + old SP hier-KV @ 40 tok/s, Qwen3.6** | system gate (envelope assembled) | [TARGET] |
| Ring-2 disk offload + residual recall cost | C2/C3 | [TARGET] |
| Dual-GPU / multi-device residue-sharing (ship residues, not tensors) | C3 + Trick #1 | [TARGET] |
| int-end-to-end (no per-matmul fp dequant; only logits) | WIRE-* + C2 | [DESIGN] |

---

## 6. Open blockers (honest)

- **WIRE gap:** CPU/CUDA/Vulkan forward shells still call scalar f32 (Hexagon done via HX.3b). The envelope isn't realized until shells call the integer + Spinor-KV primitives.
- **qwen35moe `.sp-model`:** needs the *reducing* OK_Q4 artifact (OK_Q8 was backwards → 35 GB) + `sp_model_to_qwen36` bridge + arena-aware expert path. Forward already gated GGUF-direct (M_QWEN36).
- **engine↔core fork tax:** duplicated forwards / dequant / row_bytes / arch-id enums. "One object" presupposes de-duplication.

---

## 7. Discipline that is working (keep it)

Clean rewrite · bounded crates + frozen seams · contract system (RFC + C1–C6) · per-cell closure docs · oracle-fingerprint validation · honest PROVEN/TARGET tagging · surface-upstream-never-silently-revise-a-gate · separate worktrees for parallel agents · this STATE ledger updated every session. **This is the structure that finally works. Maintain it. Update this file at the end of every session.**
