---
type: session-handoff
title: SESSION-CLOSED — Stage Beta Stage-0 + GPU decode (2026-06-06)
description: "Scope: open Stage Beta (RTX 2060 12GB, Turing sm_75) — verify the discrete"
tags: [session-handoff]
timestamp: 2026-06-06T05:12:58Z
resource: shannon-prime-lattice/papers/SESSION-CLOSED-stage-beta-s0.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# SESSION-CLOSED — Stage Beta Stage-0 + GPU decode (2026-06-06)

**Scope:** open Stage Beta (RTX 2060 12GB, Turing sm_75) — verify the discrete
lattice on the actual GPU, then build + gate autoregressive token generation.
Companion: PPT-LAT-Roadmap §21, PPT-LAT-STATE §5.08, CONTRACT-SPEED, memory
`project-stage-beta-rtx2060`.

## Hardware / toolchain (verified on the card, not assumed)

RTX 2060, 12288 MiB, driver 596.21. CUDA 13.2 (V13.2.51); **nvcc 13.2 still
targets compute_75** (`--list-gpu-arch` = compute_75..121) — the deprecated-
silicon risk cleared by probe. Host = VS18 BuildTools cl via vcvars64.
`-DSP_ENGINE_WITH_CUDA=ON` → build-cuda clean, 48/48 targets.

**sm_75 cache-control, MEASURED (device-attr probe):** L2 = 3.0 MB;
**MaxPersistingL2CacheSize = 0** → NO L2 set-aside/pin (Ampere sm_80+ only).
L1 has no pin API on any arch. The Turing substitute = **shared memory as
explicit non-evictable scratchpad** (64 KB/SM, 48 KB/block, 64 KB opt-in) +
PTX cache-hint bias (`ld.global.ca` hot signatures / `.cs` cold residues).
Pinned in [[reference-cuda-sm-feature-tiers]].

## Gates (all on the actual 2060)

| Gate | Result |
|---|---|
| CUDA_SMOKE | device 0 = RTX 2060 sm_75 — PASS |
| E_CU_5 NTT-attention | int64 dot == sp_pr_inner 192/192; argmax 31/31; KL 2.4e-10 — PASS |
| E_CU_6 KSTE-KV | 6944 sigs deterministic — PASS |
| M_GEMMA3_CUDA prefill | PASS |
| M_QWEN3_CUDA prefill | f32 + Q8 argmax 31/31, KL ~1e-11 PASS; **fp16 sub-gate FAILS** (precision floor) |
| **M_QWEN3_DECODE_CUDA** | GPU decode == GPU prefill teacher-forced, 5/5 — PASS |

The discrete dual-prime poly-ring attention reproduces the math-core scalar
reference to floating-point noise (KL 2.4e-10) on Turing — the substrate is
GPU-correct, not just compiling.

## What was built

`qwen3_decode_cuda` (engine `3b6831c`): the first token-GENERATION on the
card (the prior CUDA forward was stateless prefill). KV resident in VRAM
across steps; new kernels `k_rope_at` (absolute-position RoPE), `k_attn_decode`
(single-query GQA over the cached span), `k_argmax` (device reduction → writes
the winner into a VRAM-resident `dseq[]`; embed reads dseq[pos], argmax writes
dseq[pos+1] — eos=-1 has ZERO per-step host sync). Gate compares vs GPU
PREFILL (not CPU qwen3_generate_kv) to dodge the MSVC cpu_overlay LNK2005
collision (link.exe pulls both the override and the math-core member).

## Speed pass 1 (engine `1af7c9a`)

| Config | tok/s |
|---|---|
| f32 + host argmax | 6.93 |
| f32 + device argmax | 7.04 |
| **Q8 arena + device argmax** | **11.97 (1.7×, ship path)** |

**Honest bottleneck:** device-argmax barely moved f32 ⇒ the host sync was not
the wall. The wall is **kernel launch overhead** (~250 tiny kernels/token at
0.6B). Q8's 1.7× is weight-byte halving through the GEMMs. NEXT (BETA.2) =
CUDA graphs.

## Corrections banked (no spin)

- **"50% lossless" retired.** The `.sp-model` 50% is f16→OK_Q8 (quantization,
  top-1/output-lossless, NOT lossless). A 4-bit-source model has no 50% to
  take; OK_Q4 ~17% structural; sub-Q4 unproven. Beta TIES llama.cpp on weight
  size; the win is bandwidth-efficient O(1) deep-context attention.
- **int4 boundary:** STORAGE target (mandatory for 12B-in-12GB; arena does Q4),
  NOT a compute precision (int4-act MMA fails top-1; residues are exact u32,
  router is 1-bit — neither needs INT4 TC).
- **Optane stays (Stage Gamma):** dropping it makes a 0.6B toy that can't scale
  to 12B+. Gamma = cudaHostAlloc pinned bridge (consumer Turing has NO
  GPUDirect Storage).
- **fp16 sub-gate decision OWED:** re-spec bounded-divergence OR document
  fp16 non-parity on Turing. Not silently relaxed.

## Next session

BETA.2 CUDA graphs → BETA.3 fused kernels → BETA.4 discrete router on GPU →
BETA.5 llama.cpp-CUDA head-to-head → Stage Gamma pinned-mem Optane bridge.
v5 finale = do-not-relaunch. See `project-stage-beta-rtx2060` memory.
