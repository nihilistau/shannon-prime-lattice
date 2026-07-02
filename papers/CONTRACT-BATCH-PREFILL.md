---
type: contract
title: "CONTRACT — batched prefill for the resident 12B decode (the launch-bound O(n) prefill fix)"
description: "Task #41. Kills the per-token launch storm on cold/large prefills (recall delivery re-prefill 71s, big-paste, qwen36) by running ONE n_tok-wide batched forward that stores K/V into the resident cache, instead of N single-token g4_kv_step launches. Recon COMPLETE (2026-07-03): the batched forward primitive already exists (gemma4_cuda_probe); the gap is a K/V-into-resident-cache sink. Specced to file/line so a fresh session executes + re-gates cleanly."
tags: [contract, batch-prefill, 12b, serve-speed, cuda, gemma4_kv]
timestamp: 2026-07-03T00:00:00Z
resource: shannon-prime-lattice/papers/CONTRACT-BATCH-PREFILL.md
sp_status: HONEST-NEGATIVE
sp_gate: "G-BATCH-PREFILL: correctness GREEN, performance honest-negative (engine 11df1f1)"
sp_commit: "engine 11df1f1 (kernel built + gated default-off)"
sp_repro: "_bp_launch.bat + curl _t_bp1.json (Apollo n=102) -> correct answer + BATCH-PREFILL log; G-BATCH-PREFILL.log"
---

> ★ **BUILT + RESOLVED 2026-07-03 (engine `11df1f1`).** The kernel is written and **CORRECT**
> — the K/V-sink-into-resident-cache design is PROVEN: a cold 102-token batched prefill gives
> the exact right answer + a clean decode-after (no corruption). But the performance is an
> **honest negative on the 12GB card**: `gemm_w_lift` dequants each packed weight to f32 →
> dequant-dominated at small n (39s@102, slower than per-token) and VRAM-thrashing at n≥~400.
> **THE REAL FIX = a batched dp4a GEMM** (weights stay int4, no f32 materialization — the
> single-column `k_gemv_q4b_dp4a_v2` generalized to N activation columns); the shipped
> correct-but-slow kernel is its validated K/V-sink harness. Default-off + precondition-gated,
> so the shipped daemon is byte-untouched. Full result: `tests/fixtures/chat_fullstack/G-BATCH-PREFILL.log`.

# CONTRACT — batched prefill

**Why.** Prefill (`gemma4_kv_prefill`, cuda_forward.cu ~4412) loops `g4_kv_step` once
per token: ~960 kernel launches × N tokens, each doing single-token GEMV work that
starves the GPU. Measured: 340 tok ≈ 12–18s, 560 tok ≈ 71s (the L5 delivery re-prefill,
G-RECALL-DEADSCAN-SKIP), 1000 tok minutes. Same cost hits cold big-paste prompts and the
qwen36 prefill-by-stepping. Batching turns N GEMVs into ONE N-wide GEMM per weight →
GPU-saturated → O(1)-ish launch count.

## Recon (DONE — the reusable primitive)
`gemma4_cuda_probe` (cuda_forward.cu ~1791) ALREADY does the full N-position batched
forward: `gemm_w_lift(..., n_tok, ...)` for every weight (Wq/Wk/Wv/Wo/Wgate/Wup/Wdown +
the tied head), `k_rmsnorm<<<n_tok>>>`, batched `k_rope`, batched attention `k_attn`
(each of n_tok positions attends causally over [0,n_tok)), and the AltUp/PLE precompute
(`k_altup_ipl`, needed — the 12B has PL>0). It is byte-validated against the CPU reference
(the G-BYTEEXACT-ISLANDS dump seam lives inside it). **The ONLY gap:** it stores per-owner
K/V into throwaway `Kst[L]`/`Vst[L]` (lines 2001-2007) and frees them; it never writes the
resident cache.

## Recon addendum (2026-07-03 — two findings that shape S1)
1. **The batched GEMM handles the packed 12B weights.** `gemm_w_lift` (cuda_forward.cu
   ~5512) already takes the OK_Q4B path: `W->bscale` ⇒ `gemm_w` (dequant-exact), else
   `k_codes_f32` dequant → cublas `gemm` → `k_scale_rows`. So the probe's n_tok-wide
   layer stack RUNS on the 12B (one big GEMM/weight/layer via an f32-scratch
   materialization — memory-heavy but launch-cheap, the whole point).
2. **Skip the head — it is the only 12B blocker.** The probe's FULL head (probe ~2077)
   needs `g_w.embd` (f32 embedding), which the 12B does NOT keep resident (packed codes
   only ⇒ the probe self-disables FULL mode: "use the decode path"). Prefill does NOT
   need per-position logits — only the LAST position's, which the caller already gets
   from the PACKED `decode_step(last)`. So the batched prefill runs embed→AltUp→layers
   (K/V sink)→set dpos, and STOPS before the head. The f32-embd blocker is sidestepped.

## The build (S1 — the K/V-sink batched prefill)
New `extern "C" int gemma4_kv_prefill_batched(sp_g4_kv *s, const int32_t *toks, int n)`:
mirror the probe's full-forward layer loop but at the K/V-store point (probe 2001-2007)
write into **`s->dKc[L]`/`s->dVc[L]` at [0, n)** instead of Kst/Vst (for a full-cache
owner the slot == pos, so dKc[L]'s first n slots ARE the layout k_kv_store writes
per-token). Set `s->dpos_host = n`. Leave the last position's post-head logits reachable
(or require the caller to `decode_step(last)` exactly as the per-token path does — the
K/V for [0,n) is already resident, so decode_step(n-1) recomputes only that row's logits).
Prefer refactoring the probe's layer body into a shared `g4_forward_batched(kv_sink)`
helper over copy-paste, to avoid arithmetic drift between the two.

## Gating (S1 constraints — why it is SAFE and default-off)
- **FLOAT, not byte-exact.** The probe's `k_attn` is float + batched accumulation ⇒ K/V
  differ from the bx per-token path (and from float per-token, by reduction order). So
  this is a CHAT SPEED MODE, not the auditable mode. Justified: G-BX-OBEY-AB proved obey
  is byte-exact-NEUTRAL (61/61 identical answers on==off). Gate `SP_KV_PREFILL_BATCH=1`,
  default-off = the exact current per-token path (null floor).
- **Cold + full-cache + ring-off only.** Fire ONLY when `dpos_host==0` (no persist prefix
  to preserve) AND `ring_W==0` (SWA-ring's slot=pos%W store is not a contiguous [0,n)
  block — batched store would need ring-aware indexing; defer). AND no inject/capture seam.
  Any other state ⇒ fall through to per-token (byte-identical). The daily-driver chat
  launcher can drop `SP_DAEMON_KVDECODE_RING_W` at Pmax=4096 (full cache fits) to enable it.
- The L5 delivery re-prefill (reset_cold → dpos==0 → cold) is the prime beneficiary.

## S2 — daemon wiring
routes.rs kvdecode path: when `SP_KV_PREFILL_BATCH=1` AND the turn is cold (post-reset,
no persist reuse, `head.len()` large) AND ring-off, call `gemma4_kv_prefill_batched(head)`
instead of the per-token `kv::prefill(head)`. Small heads (< ~64 tok) stay per-token (batch
launch overhead not worth it). The L5 recite delivery (routes ~1795) is the same swap.

## S3 — G-BATCH-PREFILL gate
1. COHERENT: cold 300/600/1000-tok prompt → coherent reply (vs per-token: same meaning).
2. NO CORRUPTION: after batched prefill, decode 32 tokens → coherent (proves resident K/V
   is correct across the whole window, not just position 0).
3. SPEED: prefill tok/s ladder — target ≥5× the per-token prefill at 600 tok (71s → <15s).
4. FLOAT-PARITY DISCLAIMER in the receipt: NOT byte-identical to bx per-token (by design);
   coherence + obey are the gate, not bit-parity. Re-run G-ONECONFIG-LIVE with the batch
   flag on to confirm obey unchanged (expected: neutral).
5. Default-off proof: unset ⇒ per-token path byte-identical (the null floor).

## Risk register (why this was NOT rushed at session end 2026-07-03)
Writing into the live K/V cache with a wrong slot/layout silently corrupts decode — the
exact failure class the byte-exact work exists to prevent. It needs 2-3 build/test
iterations + a full obey re-gate. Recon is done and the approach de-risked (reuse the
validated probe forward); the kernel + re-gate is a focused half-day, not a tail-of-session
commit. Bank: MEM-OKF "gemma4_cuda_probe IS the batched forward — reuse it, don't rebuild".
