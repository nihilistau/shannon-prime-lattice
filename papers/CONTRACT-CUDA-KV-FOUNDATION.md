---
type: contract
title: "CONTRACT-CUDA-KV-FOUNDATION — route the served CUDA decode KV through the L1 ABI foundation codec"
description: "Root-caused regression: the live 12B CUDA decode (cuda_forward.cu) stores K/V as a private raw-float32 buffer and never honors the L1 ABI KV codec (SP_KV_SPINOR / sp/spinor_block.h), which is realized only on the CPU/math-core path. The served chat therefore bypasses the entire C2 foundation KV envelope (Spinor compression, ARM two-ring, Ring-2). This contract wires the CUDA backend to the ABI KV contract — exact KV as the default auditable mode, SP_KV_SPINOR as a selectable compressed mode — gated correctly (bit-exact for exact mode; top-1/KL for the lossy compressed mode), with a standing guardrail (G-FOUNDATION-ROUTING) so the drift cannot recur."
tags: [contract, cuda, kv-cache, l1-abi, spinor, foundation-routing, regression, c2, anti-drift]
timestamp: 2026-06-28T00:00:00Z
resource: shannon-prime-repos/shannon-prime-system-engine/src/backends/cuda/cuda_forward.cu
sp_status: DESIGN
sp_gate: G-FOUNDATION-ROUTING
sp_commit: TBD
sp_repro: "python shannon-prime-lattice/staging/foundation-routing/g_foundation_routing.py"
---

# CONTRACT-CUDA-KV-FOUNDATION

> Parent: [RFC-001](PPT-LAT-RFC-001-Universal-Discrete-Architecture.md) §8 (crate boundaries: backends implement the SAME primitives, bit-exact, via the L1 ABI) · [CONTRACT-C2-ARM-spinor-kv-two-ring](CONTRACT-C2-ARM-spinor-kv-two-ring.md) (the foundation KV envelope) · [ROADMAP-REBUILD-2026-06](ROADMAP-REBUILD-2026-06.md) Stage 1.
> Guardrail: `staging/foundation-routing/g_foundation_routing.py` (gate **G-FOUNDATION-ROUTING**, currently **RED**).

## 0. The regression (root-caused, receipts)

The served Gemma-4-12B chat runs its forward on the exact-integer foundation (byte-exact islands + dual-prime CRT-NTT attention, default-on — `routes.rs:411-415`), **but its KV cache is a private CUDA float32 buffer**:

- `src/backends/cuda/cuda_forward.cu:1918-1919` — `cudaMalloc(&Kst[L], n_tok*kvd*sizeof(float))`, `Vst[L]` float. Raw fp32 K/V.
- No `SP_KV_SPINOR` / `spinor_block` / `kv_flags` anywhere in the CUDA decode or `cuda_kvdecode_dispatch.rs` (the only CUDA "spinor" is `ptx_bench.cu`, a throughput bench, and `dialogue_runner.rs` `SpinorReceipt`, the memo receipt — neither is the KV path).
- The L1 ABI **defines** the foundation KV codec — `sp_l1.h:156 SP_KV_SPINOR` ("persistent COMPRESSED KV: VHT2+Möbius 63-byte Spinor blocks, decoded inline"), `sp/spinor_block.h` — and it is honored on the **CPU/math-core** forward (where C2 was measured), but the **CUDA backend was built with its own KV and ignores the ABI flag.**

Consequence: the served path bypasses the **entire C2 foundation KV envelope** — Spinor compression (~3.5×), ARM two-ring, Ring-2 offload (400–1190× effective context). The reason PPT-ARM exists is absent from the live chat. This is "built in isolation," exactly.

## 1. The spec'd Spinor KV IS byte-exact (corrected 2026-06-28)

An earlier draft of this contract cited a **stale, wrong-path** number — the `C2_KV_DECODE_DETERMINISM` ~6.5% argmax flips (2026-06-02). Those were the **generic float-carrier** Spinor codec (`sp_spinor_encode_vec`, int8 + per-block scale), **not the spec'd path**. The 2026-06-18 work re-carried the memory stack onto the **native integer O_K dual-prime CRT-NTT carriers**, where it is byte-exact (CONTRACT-XBAR-R3-consolidation, **G-R3-BIND**):

- numpy-int reference vs native `sp_pr_mul` / `ntt` / `sp_pr_inner` / `sp_pr_score_kstore` = **256/256 bit-identical** (the arm.h EXACTNESS CONTRACT holds for the bind algebra);
- the **±1 carrier is int == float — lossless**;
- the integer superposition is **byte-identical across all 8 reduction permutations** (the float diverges at 4.44e-15);
- **lossless verify**: hit fidelity PPL 4.6665 == baseline (**+0.000%**).

So, run as specced on the O_K carriers, the Spinor/Ring KV **is byte-exact** — the number theory (NTT-over-Z_q, ±1 carriers, dual-prime CRT) gives exact reconstruction. **Principle (operator): "as byte-exact as possible."** The ABI's job is precisely to take not-natively-exact inputs and run them through the byte-exact O_K processes (the byte-exact-ification seam). ~90% of non-exacts are eliminated; any residual non-exact carrier (e.g. the old float-carrier Spinor) is flagged for the exactness backlog and revisited later — it is **not** a blocker. **The foundation KV target is therefore byte-exact AND compressed — not a tradeoff.**

## 2. The architectural call (made, not asked)

The CUDA backend MUST implement the **L1 ABI KV contract** — KV is never again a private backend buffer. KV is carried on the **O_K Spinor / Ring carrier via the ABI**, which is **byte-exact AND compressed in one path** (§1): the C2 envelope (Spinor compression, ARM two-ring, Ring-2) *and* the exactness, together, because the number theory delivers both. The ABI is the **byte-exact-ification seam** — float K/V out of the projection are carried into the exact-integer O_K domain (dual-prime CRT-NTT, ±1 carriers) and stored/decoded exactly.

- **Gate:** `G-WIRE-CUDA-DECODE-GEMMA4` (bit-exact) — the spec'd O_K Spinor KV **passes it** (lossless, §1). Plus `G-CUDA-KV-RATIO` for the compression / effective-context the envelope now buys in the served path.
- **"As byte-exact as possible":** if a *specific* carrier turns out residually non-exact (the old float-carrier Spinor is the known example), it is gated top-1-safe / KL-bounded **and flagged on the exactness backlog** — never made the silent default.

The point of "route through the foundation" is that **the foundation defines the KV contract and the CUDA backend implements it** (RFC §8: backends implement the same primitives, bit-exact, via the ABI) — never a rogue buffer.

## 3. The surgery (hooks)

1. **ABI seam** — thread `kv_flags` (incl. `SP_KV_SPINOR`) onto the kvdecode handle: `cuda_kvdecode_dispatch.rs` (the `sp_kvdecode_dispatch_fn` table / `sp_g4_kv` handle) + the C glue, so the served session selects the KV codec via the ABI rather than the backend hardcoding float.
2. **Storage** — `cuda_forward.cu:1918` K/V alloc: behind `kv_flags`, store either exact-foundation K/V (default) or Spinor 63-byte blocks (`sp/spinor_block.h`), replacing the unconditional `sizeof(float)` buffer.
3. **Read** — the decode attention (`g4_kv` read / `k_attn_decode_*`) decodes the foundation KV block inline before the dp4a / byte-exact-CRT-NTT attention.
4. **Nightshift migration** — `routes.rs` / the nightshift curator read/write the dense **63-byte Spinors via the ABI**, not raw float logits (the memory arc on the foundation).
5. **Default config** — the serve launcher selects EXACT-foundation KV by default; `SP_KV_SPINOR` is the explicit compressed-mode opt-in.

## 4. Gates

| Gate | What | Mode |
|---|---|---|
| **G-FOUNDATION-ROUTING** | the guardrail: CUDA decode routes KV via the ABI codec, not a private float buffer (`g_foundation_routing.py`) | RED now → GREEN when wired; runs in Stage-0 battery + pre-commit |
| G-WIRE-CUDA-DECODE-GEMMA4 | O_K Spinor KV decode == math-core oracle (**bit-exact** — the spec'd Spinor passes, §1) | foundation KV |
| G-CUDA-KV-RATIO | measured served KV compression + effective-context (the C2 envelope, now live in the served path) | foundation KV |
| G-CUDA-KV-RESIDUAL | top-1-safe + KL-bounded fallback **only** for a carrier proven residually non-exact (e.g. old float Spinor); flag on the exactness backlog | residual non-exact |

## 5. Anti-drift (so this cannot recur)

- **G-FOUNDATION-ROUTING is now a standing invariant gate** — added to `run_stage0_battery.sh` (here-tier) and pre-commit. Any backend that ships a private KV/forward/recall buffer bypassing the ABI trips it RED.
- **Banked**: `okf_mem` fact "CUDA decode KV is private float, bypasses SP_KV_SPINOR — fix per this contract".
- **Invariant stated** (RFC §8 made executable): *a backend never owns a primitive the foundation defines; it implements the ABI contract.* The gate enforces it for KV; extend the same gate pattern to forward/recall.

## 6. Build & honest scope

This is a **CUDA-kernel build** (nvcc) + Rust ABI plumbing + `cargo build --release --features wire_cuda_backend`, gated on the dev box — not a flag flip (the CUDA decode has no Spinor path today). Sequence: (1) thread `kv_flags` / `SP_KV_SPINOR` through the ABI (Rust + C glue) — buildable, no kernel change; (2) implement the **O_K Spinor KV carrier** storage + inline decode in `cuda_forward.cu` via the ABI — byte-exact **and** compressed (§1) — gate `G-WIRE-CUDA-DECODE-GEMMA4` (bit-exact, passes) + `G-CUDA-KV-RATIO` (the envelope). **G-FOUNDATION-ROUTING flips GREEN at step 2.** No separate "lossy mode" is required for the spec'd carrier; `G-CUDA-KV-RESIDUAL` exists only if a specific carrier is later proven non-exact.
