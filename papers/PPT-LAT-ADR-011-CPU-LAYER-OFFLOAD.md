---
type: design
title: "ADR-011 — CPU-resident layer offload: the one lever that frees real VRAM (measured curve + design)"
description: "ADR-010 proved the model (~10.9 GB) fills the 12 GB card and PCIe x8 forbids streaming weights — so the only way to free real VRAM is to move whole LAYERS to the CPU (weights resident in 40 GB/s DRAM, computed on 8 AVX2 cores, exchanging only the ~15 KB activation). This ADR measures the tradeoff on the real 12B and designs the minimal hybrid. MEASURED (SP_G4_CPU_TAIL_MEASURE): 48 layers, 7.86 GB of matmul weights, ~167.8 MB/layer — a CONTIGUOUS TAIL of K layers frees K×0.164 GB (K=8 → 1.32 GB, K=16 → 2.63 GB). Design: offload a contiguous tail so the residual stays CPU-side between them = ONE D2H + ONE H2D boundary crossing per token (not per-layer); reuse the math-core CPU gemma4 forward (core/forward/gemma4.c, sp_matmul handles OK_Q4B on CPU); the offloaded layers' KV cache also lives host-side (frees more VRAM); CRT guarantees the CPU and GPU legs are bit-identical so the split is drift-free and auditable. Analytical latency: memory-bound ~4.1 ms/layer CPU vs ~0.49 ms GPU (~8.4×) → +~3.6 ms/token/layer → K=8 ~13→9.4 tok/s, K=16 ~13→7.4 tok/s. Verdict: a VRAM-for-latency trade — free 1.3–2.6 GB at ~30–45 % slower decode; worth it to fit a bigger model, run a co-tenant, or buy headroom that stops the batch/thrash. Not a speedup; the honest rebalance the operator's instinct named."
tags: [design, adr, cpu-offload, vram, layer-placement, pcie, avx2, crt, bit-exact, hybrid, whole-machine]
timestamp: 2026-07-08T00:00:00Z
resource: shannon-prime-lattice/papers/PPT-LAT-ADR-011-CPU-LAYER-OFFLOAD.md
sp_status: "MEASURED + DESIGNED (VRAM curve real; latency analytical). Hybrid forward = the committed next brick (STAGE-2)."
sp_gate: "G-ADR11-MEASURE (the VRAM curve) — engine tests/perf; STAGE-2 gate = coherence + VRAM-freed + tok/s"
sp_commit: "builds on ADR-010 (the model fills the card) + core/forward/gemma4.c (CPU forward, reused)"
sp_repro: "SP_G4_CPU_TAIL_MEASURE=1 in gemma4_kv_open → the per-layer + tail curve in the daemon log"
---

# ADR-011 — CPU-resident layer offload

**Status: MEASURED + DESIGNED.** The VRAM curve is real (this session); the latency is analytical
(the hybrid forward, STAGE-2, measures it live). Follows ADR-010's verdict: *the model fills the
card, so you free VRAM by moving weights, and PCIe x8 forbids streaming them — the layer must
compute where its weights live.*

## 1. The measured VRAM curve (real 12B, `SP_G4_CPU_TAIL_MEASURE=1`)

```
48 layers, matmul weights 7.86 GB resident, ~167.8 MB/layer avg
  tail K= 4 -> free 0.66 GB      tail K=16 -> free 2.63 GB
  tail K= 8 -> free 1.32 GB      tail K=24 -> free 3.93 GB
  tail K=12 -> free 1.97 GB      tail K=32 -> free 5.25 GB
```

Per layer: Wq/Wo (~7.9 M weights each) + Wk/Wv (owners) + FFN Wgate/Wup/Wdown (the bulk) at OK_Q4B
(~0.56 B/weight incl. per-32-block f16 scales + row_off) ≈ **167.8 MB**. The matmul weights are
7.86 GB of the 8.8 GB model (the rest = packed embd + PLE table + norms — those stay on GPU).

## 2. The design — contiguous-tail hybrid (one boundary crossing/token)

Offload a **contiguous tail** of layers `[NL−K, NL)`:
- **GPU** runs layers `0 .. NL−K−1` as today, then **D2H the residual** (E=3840 floats ≈ 15 KB —
  one small copy).
- **CPU** runs layers `NL−K .. NL−1` — RMSNorm, Wq/Wk/Wv, q/k-norm, RoPE, attention, Wo, FFN
  (GeGLU), AltUp/PLE — entirely in host RAM, reusing **`core/forward/gemma4.c`** (its per-layer
  body already uses `sp_matmul`, which reads the OK_Q4B arena weights on CPU). The residual stays
  CPU-side *between* the tail layers, so there is **no per-layer PCIe traffic** — just the one
  hand-off and one return.
- **H2D the pre-head hidden**, GPU runs `out_norm` + the tied head (or run the head on CPU too).
- The offloaded layers' **KV cache lives host-side** (their attention reads it on CPU) — this
  frees *additional* VRAM beyond the weights and keeps the boundary at one crossing.

Because the tail is contiguous, the activation exchange is **2 × 15 KB/token total**, negligible
over even PCIe x8 — the whole point of moving *layers* not *weights*.

## 3. The latency (analytical; STAGE-2 measures it)

CPU layer is memory-bound: 167.8 MB / 40 GB/s DDR4 ≈ **4.1 ms/layer** (8 AVX2 cores saturate the
bus). GPU layer: 167.8 MB / 336 GB/s ≈ **0.49 ms** → **~8.4×**. Net per token per offloaded layer
≈ **+3.6 ms**. At the ~13 tok/s (~77 ms/token) baseline:

| K (tail on CPU) | VRAM freed | est. decode | est. tok/s |
|---|---|---|---|
| 8  | 1.32 GB | ~106 ms/tok | ~9.4 |
| 16 | 2.63 GB | ~135 ms/tok | ~7.4 |
| 24 | 3.93 GB | ~163 ms/tok | ~6.1 |

**Prefill** pays K× per prompt token, so offload favors decode-heavy / short-prompt use. The
numbers are memory-bound estimates; the STAGE-2 hybrid measures the real AVX2 dp4a throughput.

## 4. Why the split design makes this clean (CRT = the enabler)

The math-core forward is already CPU-capable (the reference path) and the `build-cpu-perf`
AVX2/OpenMP libs ship. The crucial property: **CRT / the exact-integer O_K substrate makes the CPU
and GPU legs bit-identical** (the byte-exact forward, `SP_BYTEEXACT`). So a hybrid CPU+GPU forward
is **drift-free and auditable** — the residual handed across the boundary is the same bytes either
device would have produced. That is the one property that makes a split trustworthy, and it is why
this project belongs on THIS stack and not a generic llama.cpp offload.

## 5. Verdict — a VRAM-for-latency rebalance, worth it when the model doesn't otherwise fit

CPU layer offload is **not a speedup** — it trades ~30–45 % decode latency to free 1.3–2.6 GB. It
pays when VRAM is the *hard binding constraint*:
- **fit a bigger model** (a 12B that's tight, or a would-be-OOM larger quant) by parking its tail
  on the CPU;
- **run a co-tenant** (another model / app) in the freed VRAM;
- **buy headroom** so the batch-prefill scratch (ADR-009) or a longer KV never thrashes.
For plain chat on a dedicated card the 12B already fits — offload is off (default). The operator's
instinct — "run the matmul on the CPU, balance the whole system" — is the correct lever, now
measured and bounded.

## 6. STAGE-2 (the committed next brick)

Realize the hybrid: (a) extract a `gemma4_forward_layers(m, x, ipl, a, b, host_kv)` from
`core/forward/gemma4.c` that runs layers `[a,b)` on a residual with a persistent host KV cache;
(b) wire the boundary in `g4_kv_step` behind `SP_G4_CPU_TAIL=K` (D2H residual → CPU tail → H2D);
(c) gate on **coherence** (byte-exact vs full-GPU under `SP_BYTEEXACT`, the CRT parity) + **VRAM
freed** (nvidia-smi) + **tok/s** (the real curve). Default-off = the null floor. The measurement
instrument (`SP_G4_CPU_TAIL_MEASURE`) shipped this session is its scaffolding.
