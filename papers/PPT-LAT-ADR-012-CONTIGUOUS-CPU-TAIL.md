---
type: design
title: "ADR-012 — Contiguous full-layer CPU tail: killing the sync-bound slope of CPU offload"
description: "ADR-011 realized CPU FFN offload but measured a STEEP sync-bound slope (K=4 -> 5.99 tok/s), because FFN-only offload is intrinsically INTERLEAVED with GPU attention: every offloaded FFN forces a D2H + 2x cudaStreamSynchronize + H2D, ~2K syncs/token, and the receipt proved ~80% of the added latency is that round-trip, not the CPU matmul. This ADR removes the interleave by offloading a CONTIGUOUS tail of WHOLE layers (attention+FFN+AltUp) to the CPU with ONE boundary crossing per token. The enabler is shared-KV: every tail layer is a SHARER that reads a FIXED owner cache (global src=kvfs-1, SWA src=kvfs-2, independent of L), so the whole tail's attention needs only TWO owner K/V caches mirrored to host (~8 KB/token incremental, or a bounded window). The GPU runs layers [0,NL-K), hands over the residual + those two owner caches in ONE batched async D2H + ONE cudaStreamSynchronize, the CPU runs EVERY tail layer with zero GPU interaction (weights already host-resident in the OK_Q4B arena; sp_matmul reads them), and hands the residual back ONCE for the GPU head. Per-token crossings collapse from ~2K to ~2, so the slope approaches the memory-bound floor (~4 ms/layer) instead of ~33 ms/layer. CRT keeps the CPU legs bit-identical to the GPU. Default-off = the all-GPU 23.84 tok/s null floor. New knob SP_G4_CPU_TAIL_FULL=K supersedes the FFN-only SP_G4_CPU_TAIL."
tags: [design, adr, cpu-offload, vram, layer-placement, shared-kv, sync-bound, contiguous-tail, crt, bit-exact, hybrid, whole-machine]
timestamp: 2026-07-08T00:00:00Z
resource: shannon-prime-lattice/papers/PPT-LAT-ADR-012-CONTIGUOUS-CPU-TAIL.md
sp_status: "IMPLEMENTED — pending G-ADR12 gate (byte-exact coherence + VRAM freed + tok/s curve vs ADR-011's K=4 5.99). Builds on ADR-011's honest sync-bound diagnosis."
sp_gate: "G-ADR12 (pending): coherent all K + VRAM freed ~0.16 GB/tail-layer + tok/s curve — target the memory-bound curve (~13-17 tok/s @ K=4) vs FFN-only 5.99"
sp_commit: "engine cuda_forward.cu (SP_G4_CPU_TAIL_FULL boundary) + math-core gemma4.c gemma4_tail_cpu + sp/model.h"
sp_repro: "SP_G4_CPU_TAIL_FULL=4 on the perf daemon (build-cpu-perf + libomp, target-wirecuda-perf); decode tok/s vs SP_G4_CPU_TAIL_FULL unset"
---

# ADR-012 — Contiguous full-layer CPU tail (the sync-killer)

**Status: IMPLEMENTED, gate pending.** Follows ADR-011's honest verdict: FFN-only offload works and
frees VRAM, but its slope is **sync-bound, not compute-bound** — the receipt measured ~33 ms per
offloaded FFN per token, of which only ~4 ms is the memory-bound CPU matmul; the other ~29 ms is the
per-FFN GPU↔CPU round-trip. This ADR attacks that ~29 ms directly.

## 1. Why FFN-only is intrinsically sync-bound

A transformer layer is `attention → FFN`, and layers are sequential. Offloading only the FFN leaves
it **interleaved**: GPU does layer L's attention, the FFN of L goes to the CPU, GPU does layer L+1's
attention, the FFN of L+1 goes to the CPU, … Each offloaded FFN therefore forces a full pipeline
drain — `cudaStreamSynchronize` + `D2H` the residual + (CPU compute) + `H2D` the residual — because
the next GPU op depends on the CPU result and vice-versa. K offloaded FFNs ⇒ ~2K stream syncs/token.
You cannot batch these copies: the interleave is structural. ADR-011 §7 named this and stopped there.

## 2. The fix — offload a CONTIGUOUS tail of WHOLE layers

Run the last **K whole layers** (attention **and** FFN and AltUp) on the CPU as one uninterrupted
block. Then the boundary is crossed exactly **twice per token**: once to hand the residual (and the
KV the tail needs) to the host, once to hand the post-tail residual back for the GPU head. No
per-layer interleave ⇒ no per-layer sync ⇒ the slope is set by CPU compute (~4 ms/layer, memory-
bound over the 40 GB/s DDR4 on 8 AVX2 cores), not by the copy/sync.

The obstacle ADR-011 hit — "full-layer tail needs the early GPU owners' KV every step" — turns out to
be **cheap**, because of how gemma4-12b's shared-KV actually works.

## 3. The enabler — shared-KV makes the host-KV mirror tiny

Only the first `kvfs` layers OWN K/V; every later layer is a **sharer**. Reading the forward
(`gemma4.c` / `cuda_forward.cu`), a sharer's source is **fixed**:

```
src = kvfs - (global ? 1 : 2)      // independent of the layer index L
```

So *every* global tail layer reads owner `kvfs-1`, and *every* SWA tail layer reads owner `kvfs-2`.
The entire tail's attention needs exactly **two** owner K/V caches — and both are produced by early
(GPU-resident) layers that run every token anyway. To run the tail attention on the CPU we mirror
just those two caches to host:

- **global owner** (`kvfs-1`): full-cache, `head_dim=512 × nkv=1` = 512 floats/pos.
- **SWA owner** (`kvfs-2`): sliding-window, `head_dim=256 × nkv=2` = 512 floats/pos.

That is **~4 KB per position per cache**. Per decode token the owners append one new position each —
so the incremental mirror is **~8 KB/token**, foldable into the single residual D2H under one
`cudaStreamSynchronize`. (The tail layers are all sharers, so the CPU side never stores K/V — no
ring/journal logic host-side; it only *reads*.)

## 4. The boundary (one crossing/token)

Per decode step, in `g4_kv_step`, when the loop reaches `L == NL − K`:

1. `cudaMemcpyAsync` D2H: the residual `dx` (E floats), the AltUp per-layer inputs `dipl` (NL·PL),
   and the two owner caches' `[0..pos]` K/V (global contiguous; SWA contiguous when the ring is
   unwrapped, else unrolled by `slot = p % ring_W`).
2. **ONE** `cudaStreamSynchronize` — the only sync of the tail.
3. `gemma4_tail_cpu(m, NL−K, pos, x, ipl, Kg,Vg,ng, Ks,Vs,ns)` runs **every** tail layer on the CPU:
   attn_norm → Wq → q-norm+RoPE → attention over the host owner KV (windowed for SWA) → Wo →
   post_attn → FFN (the ADR-011 `gemma4_ffn_block_cpu`) → AltUp → out_scale. Weights come from the
   host OK_Q4B arena via `sp_matmul` (always host-resident; the GPU copy is what we skip to free VRAM).
4. `cudaMemcpyAsync` H2D the residual back, `break` the GPU loop → the GPU runs `out_norm` + the tied
   LM head as usual.

`build_weights` skips uploading the whole tail layer's matmul weights (Wq/Wo/Wgate/Wup/Wdown/PLE),
freeing the full **~0.164 GB/layer** (vs FFN-only's ~0.15 GB) — and, being contiguous, at no
extra sync cost.

## 5. Why it stays byte-exact (CRT)

`gemma4_tail_cpu` is the same arithmetic as `gemma4_forward_impl`'s per-layer body for one token; the
owner K/V mirrored to host is the exact post-norm/post-RoPE K/V the GPU stored. Under `SP_BYTEEXACT`
the CPU `sp_matmul` and the GPU dp4a agree bit-for-bit (the O_K/CRT gift), so the split is drift-free
and auditable — the whole reason this offload belongs on THIS stack. In float chat mode the legs
agree to coherence (same argmax).

## 6. Expected curve (memory-bound) — the gate target

With the per-FFN sync gone, per offloaded layer ≈ the CPU compute floor (~4 ms) + a negligible share
of the single ~8 KB + E-float crossing. So:

| K | VRAM freed | est. added/tok | est. tok/s |
|---|---|---|---|
| 4  | ~0.66 GB | ~16 ms | **~13–17** |
| 8  | ~1.31 GB | ~32 ms | **~10–13** |

vs ADR-011 FFN-only measured **5.99 @ K=4 / 3.25 @ K=8**. The gate `G-ADR12` measures the real curve
on the perf daemon (`SP_G4_CPU_TAIL_FULL`), checks coherence at every K, and confirms the VRAM freed.
Default-off (`SP_G4_CPU_TAIL_FULL=0`) = the all-GPU **23.84 tok/s** null floor, byte-untouched.

## 7. Gate (G-ADR12) — pending

(measured curve + coherence + VRAM to be recorded here after the gate runs.)
