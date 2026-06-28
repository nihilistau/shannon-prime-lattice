---
type: contract
title: "CONTRACT-CUDA-KV-FOUNDATION — add C2 Spinor compression to the (already-exact) served CUDA KV ring"
description: "CORRECTED 2026-06-28 (measured, not grep): the served 12B CUDA decode KV COMPUTE is already routed through the exact-integer O_K foundation (byteexact bx kernel + dual-prime CRT-NTT, via the kvdecode L1 ABI verb, default-on; measured: byteexact serves coherent, float Stage-A garbage). There is NO bypass. The only gap is an OPTIMIZATION: the KV STORAGE is uncompressed float (~450 MB resident ring), not the C2 Spinor compression envelope. This contract adds the lossless O_K Spinor compression to the served KV ring (~320 MB headroom), gated bit-exact (O_K Spinor is lossless) + by footprint. The earlier 'foundation bypass' framing was a static-grep error and is retracted; G-FOUNDATION-ROUTING is superseded."
tags: [contract, cuda, kv-cache, l1-abi, spinor, compression, c2, optimization, corrected]
timestamp: 2026-06-28T00:00:00Z
resource: shannon-prime-repos/shannon-prime-system-engine/src/backends/cuda/cuda_forward.cu
sp_status: DESIGN
sp_gate: G-CUDA-KV-COMPRESS
sp_commit: TBD
sp_repro: "measured served path: byteexact default coherent / raw_logits garbage => compute already foundation-routed; footprint via nvidia-smi + arch (W=2048, 48 layers, KVD=512)"
---

# CONTRACT-CUDA-KV-FOUNDATION

> Parent: [RFC-001](PPT-LAT-RFC-001-Universal-Discrete-Architecture.md) §8 (crate boundaries: backends implement the SAME primitives, bit-exact, via the L1 ABI) · [CONTRACT-C2-ARM-spinor-kv-two-ring](CONTRACT-C2-ARM-spinor-kv-two-ring.md) (the foundation KV envelope) · [ROADMAP-REBUILD-2026-06](ROADMAP-REBUILD-2026-06.md) Stage 1.
> Guardrail: `staging/foundation-routing/g_foundation_routing.py` (gate **G-FOUNDATION-ROUTING**, currently **RED**).

## 0. The measured state (corrected 2026-06-28 — there is NO bypass)

> An earlier draft of this contract claimed the served KV "bypasses the foundation (private float buffer)." That was a **static-grep inference and it is wrong** — measurement through the served L1-ABI path refutes it. Corrected below; kept visible as an honest-negative on the methodology (assert-from-grep → measure-through-the-ABI).

**MEASURED (served `/v1/chat`, L1-ABI path):**
- byte-exact default-ON → coherent ("The capital of Japan is Tokyo."); `raw_logits` float Stage-A → **garbage**. So the served **KV compute IS routed through the exact-integer O_K foundation** — the `k_attn_decode_ring_bx` kernel reads the (float-stored) K/V and runs the **dual-prime CRT-NTT** attention, dispatched via the kvdecode L1 ABI verb. The ABI is doing exactly its job: take not-natively-exact inputs, run them through the byte-exact O_K process. (`routes.rs:415` byteexact default true; `cuda_forward.cu:652` `k_attn_decode_ring_bx(const float *Kc, const float *Vc, …)`.)
- **KV STORAGE is uncompressed float** — the resident SWA ring is a plain `float` K/V buffer (`const float *Kc/Vc`). It is **not** in the C2 Spinor/two-ring **compression** envelope.
- **Footprint MEASURED/computed:** VRAM 11,973/12,288 MiB; resident KV ring ≈ **450 MB float** (40 SWA layers W=2048 ≈320 MB + 8 global layers Pmax=4096 ≈128 MB, KVD=512). Spinor ~3.5× ⇒ **~320 MB headroom** is the whole prize.

**So this is not a regression or a bypass.** The exact-integer foundation is already in the served KV path. The only real item is an **optimization**: add the C2 **Spinor compression** to the (already-exact) served KV ring — a ~320 MB VRAM-headroom win for real bit-exact CUDA codec work. The big "unlimited context" envelope (Ring-2 offload, 400–1190×) is a **separate** feature the fixed-window served path doesn't exercise. `G-FOUNDATION-ROUTING` is therefore **superseded** (there was no bypass to catch); the live gate is `G-CUDA-KV-COMPRESS` (§4).

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
