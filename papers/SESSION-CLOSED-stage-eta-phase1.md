---
type: session-handoff
title: "SESSION-CLOSED — Stage Eta Phase 1: the Gemma4 CUDA engine (2026-06-06)"
description: "Scope: port the full Gemma 4 (MatFormer E-series) architecture — per-layer"
tags: [session-handoff]
timestamp: 2026-06-06T10:10:43Z
resource: shannon-prime-lattice/papers/SESSION-CLOSED-stage-eta-phase1.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# SESSION-CLOSED — Stage Eta Phase 1: the Gemma4 CUDA engine (2026-06-06)

**Scope:** port the full Gemma 4 (MatFormer E-series) architecture — per-layer
variable geometry, shared-KV, proportional RoPE, AltUp, softcap — to the RTX
2060, forward AND autoregressive decode, gated bit-faithful against the CPU
oracle `core/forward/gemma4.c` on the `gemma4-e2b` `.sp-model`. Branch
`stage-eta-gemma4-cuda`, merged to main at `559435c`. Companion: PPT-LAT-STATE
§5.10, Roadmap §19, engine README §5.2.1b, memory `project-stage-eta-gemma4-cuda`.

## The headline

**The full 35-layer variable-geometry forward matches the oracle at
`max KL = 2.663e-10` (argmax 12/12), and the autoregressive decode generates
token streams the oracle teacher-forced-predicts exactly — both on the FIRST
attempt of their live runs.** Cumulative suite: **38/38 checks.** Zero debugging
sessions on the composed system. The bisection discipline (lock every mechanism
in isolation, telemetry-then-pin every gate) made the monolith land pre-verified.

## The gates (chronological, all green)

| gate | what it locked | receipt |
|---|---|---|
| E_G4_CU_W (8/8) | weight ingest: per-layer GLOBAL/SWA Q-KV widths, shared-KV owner-only uploads, elastic FFN, AltUp tensor set, per-tensor precision. **The cross-seam link**: CORE lane (`sp_model_load → sp_model_to_gemma4`) + `sp_engine_cuda` in ONE binary — every engine-named symbol cross-resolves from the core libs; ONE shim (`as_f32 → sp_as_f32`). The fork-tax wall was one function name. | E2B geometry: L=35, period=5, kvfs=15, ff=[6144..12288], PL=256 |
| L0 staged parity | the math mechanics: ascale=1.0, QK-norm, WEIGHTLESS V-norm, window attention. **Finding 1 — oracle arithmetic = the inline Frobenius lift**: raw integer codes accumulated exactly + ONE row-scale at the end; per-weight dequant injects an extra f32 rounding per term (measured 2.8e-3). `gemm_w_lift` enforces it on cuBLAS. **Finding 2 — norm amplification**: every pre-norm stage at the f32 floor (nx BIT-EXACT, q 8.6e-6, ao 3.2e-5, ap 6.3e-5 abs); post_attn_norm divides by rms≈0.04 → ×25 into the residual. Gate currency = staged ABS floors; raw rel-err is never gated at norm outputs. | nx bit-exact; floors pinned ~3× |
| L4 staged parity | **the geometry shift**: hd 256→512, qd 2048→4096, `rope_freqs` proportional handoff (`base^(-2i/d)/ff[i]`), SWA→full-causal mask switch, dynamic launch dims. q at 1.15e-5 abs THROUGH the handoff. **Depth stability**: 4 layers of norm-amplified inflow re-condenses at the next attn_norm (1.1e-4) — the architecture is numerically self-healing. | no OOB, no crash, floors |
| L15-sharer parity | **the shared-KV seam**: the first sharer (SWA→owner L13) attends over the owner's STORED device K/V at **ao 1.11e-5 abs** — an off-by-one owner index would read L14's GLOBAL K/V through the SWA stride → garbage. Address/fetch/attend = exact. Sharer attention is the CLEANEST reading of all probes (inherited normalized states + softmax squashing). | cross-layer VRAM exact |
| **E_G4_CU_FULL** | the full 35-layer `gemma4_forward_cuda`: everything + AltUp (precompute ONCE pre-layer-0, persistent `dipl`; injection = its own sandwich block AFTER the FFN residual — NOT folded into GeGLU; per-layer scalar `out_scale`) + tied head + `k_softcap`. | **argmax 12/12, KL 2.663e-10, |dlogit| 1.84e-4 — FIRST TRY** |
| **E_G4_CU_DEC** | `gemma4_decode_cuda`: autoregressive greedy over the **JAGGED shared-KV cache** (per-owner [P×kvd_L]; global 512-wide, SWA 256-wide, sharers allocate NOTHING), per-step AltUp (PLE row host-gathered per token — the 5a correctness tax), `k_attn_decode_win` (s0=max(0,pos-win+1)), `k_rope_freqs_at`, head+softcap+argmax. | **oracle teacher-forced match ALL 12 generated tokens — FIRST TRY** |

## Oracle-truth corrections made along the way (read the silicon, not the sketch)

1. Gemma4 has **NO attention-score softcap** (that was Gemma2) — final-logit cap only; attention runs uncapped at scale 1.0.
2. The AltUp injection is **its own sandwich block after the FFN residual**, not folded into the GeGLU.
3. The E2B artifact's real geometry: **period=5** (not the comment's 6), **kvfs=15** (15 owners / 20 sharers, not 20/15) — cfg/tensor dims are the truth, comments are aspirations.
4. The first sharer is **L15** (layers [0,15) own), reading **L13** (kvfs-2, SWA) / L14 (kvfs-1, global).

## New CUDA surface (engine, merged at 559435c)

Kernels: `k_rmsnorm_head_noweight`, `k_rope_freqs`, `k_rope_freqs_at`, `k_softcap`,
`k_codes_f32` + `k_scale_rows` (the lift pair), `k_altup_ipl`, `k_altup_gate`,
`k_scale_by_dev`, `k_attn_decode_win`. Host: `build_weights` gemma4 path,
`gemm_w_lift`, `gemma4_cuda_probe` (the permanent truncated bisection harness,
6 stages), `gemma4_forward_cuda`, `gemma4_decode_cuda`,
`gemma4_cuda_weights_probe`. Test: `tests/test_gemma4_cuda.c` (E_G4_CU_W +
truncated_parity harness + FULL + DEC; links sp_session + sp_engine_cuda).

## What remains — ETA.5b, the velocity pass (everything left is physics)

Gated **top-1** (like Beta), not byte-match: (1) device-side PLE gather (packed
PLE table → VRAM + gather kernel) to sever the per-step host sync; (2)
CUDA-graph capture of the jagged topology (position-indirect, the BETA.2
machinery); (3) Q4-dp4a routing via `gemv_w_packed` (the proven ~7× byte diet)
for the giant 12B projections; (4) `sp-transcode` the 6.6 GB Gemma-4-12B-Q4_K_M
→ `.sp-model`, VRAM-fit, load; (5) **tok/s vs llama.cpp on the same card** —
the shootout where the whole campaign converges.

## The discipline that did this (keep it)

Reference-first (the oracle read line-by-line before any kernel) · bisection
bulkheads before composition · telemetry-then-pin gates · ABS floors at norm
boundaries · oracle arithmetic enforced (`gemm_w_lift`) · correctness lane (5a,
host-sync + lift) split from velocity lane (5b, top-1) · every claim with a
receipt. **The monolith lit first-try because no part of it was written blind.**
