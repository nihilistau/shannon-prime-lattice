---
type: design
title: "ADR-011 — CPU-resident layer offload: the one lever that frees real VRAM (measured curve + design)"
description: "ADR-010 proved the model (~10.9 GB) fills the 12 GB card and PCIe x8 forbids streaming weights — so the only way to free real VRAM is to move whole LAYERS to the CPU (weights resident in 40 GB/s DRAM, computed on 8 AVX2 cores, exchanging only the ~15 KB activation). This ADR measures the tradeoff on the real 12B and designs the minimal hybrid. MEASURED (SP_G4_CPU_TAIL_MEASURE): 48 layers, 7.86 GB of matmul weights, ~167.8 MB/layer — a CONTIGUOUS TAIL of K layers frees K×0.164 GB (K=8 → 1.32 GB, K=16 → 2.63 GB). Design: offload a contiguous tail so the residual stays CPU-side between them = ONE D2H + ONE H2D boundary crossing per token (not per-layer); reuse the math-core CPU gemma4 forward (core/forward/gemma4.c, sp_matmul handles OK_Q4B on CPU); the offloaded layers' KV cache also lives host-side (frees more VRAM); CRT guarantees the CPU and GPU legs are bit-identical so the split is drift-free and auditable. Analytical latency: memory-bound ~4.1 ms/layer CPU vs ~0.49 ms GPU (~8.4×) → +~3.6 ms/token/layer → K=8 ~13→9.4 tok/s, K=16 ~13→7.4 tok/s. Verdict: a VRAM-for-latency trade — free 1.3–2.6 GB at ~30–45 % slower decode; worth it to fit a bigger model, run a co-tenant, or buy headroom that stops the batch/thrash. Not a speedup; the honest rebalance the operator's instinct named."
tags: [design, adr, cpu-offload, vram, layer-placement, pcie, avx2, crt, bit-exact, hybrid, whole-machine]
timestamp: 2026-07-08T00:00:00Z
resource: shannon-prime-lattice/papers/PPT-LAT-ADR-011-CPU-LAYER-OFFLOAD.md
sp_status: "STAGE-2 REALIZED + PERF-GATED — CPU FFN offload live+coherent, ~0.96 GB freed @ K=8. Perf libs (AVX2/OpenMP) make it usable (K=4 ~6 tok/s / K=8 ~3.25 vs 23.84 baseline); curve is STEEP (per-FFN GPU↔CPU sync-bound, not compute)."
sp_gate: "G-ADR11-MEASURE + G-ADR11-HYBRID (coherent+VRAM) + G-ADR11-HYBRID-PERF (tok/s curve: K0 23.84 / K4 5.99 / K8 3.25) — engine tests/perf"
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

## 6. STAGE-2 — REALIZED (FFN-only offload; a design pivot forced by shared-KV)

Building the full-layer tail hit a real obstacle: **shared-KV**. gemma4-12b's tail layers are
mostly *sharers* whose K/V owners are the *early* layers (GPU-resident). A full-layer CPU tail
would need those GPU owners' K/V window D2H'd every step — defeating the one-crossing design. The
pivot: **offload only the FFN of the tail layers.** The FFN is ~90% of a layer's weight and
**stateless** (touches no KV), so it severs cleanly — no shared-KV coupling, one E-float D2H+H2D
per offloaded FFN.

Realized: `gemma4_ffn_block_cpu` (math-core, reuses `sp_matmul` on the OK_Q4B arena) + `g4_kv_step`
routing the last `SP_G4_CPU_TAIL` layers' FFN to the CPU + `build_weights` skipping those FFN
weight uploads. Gate **G-ADR11-HYBRID**: `SP_G4_CPU_TAIL=8` → **VRAM 11201→10221 MiB (freed
~0.96 GB)** + **coherent "Paris"** on the served 12B. Default-off = null floor.

**Honest perf caveat (as §3 warned):** the daemon links the NON-perf `build-cpu` libs (no AVX2/
OpenMP — the "0.17 rung"), so the CPU FFN is single-core scalar and slow (a 299-token prefill ×8
FFNs ran minutes; a tiny prompt 46.7 s). The VRAM lever + coherence are **proven**; the **speed
follow-on** is linking `build-cpu-perf` (AVX2/OpenMP), exactly as the qwen36 lane links
`target-wirecuda-perf`. The §3 curve (K=8 ~9.4 tok/s) assumes the perf libs.

Remaining (next): (a) link the AVX2/OpenMP CPU libs into the daemon so the offload is fast;
(b) parallelize the tail FFNs across the 8 cores; (c) a `SP_BYTEEXACT` CRT bit-parity check
(coherence is proven; bit-identity is the auditable stronger claim). The measurement instrument
`SP_G4_CPU_TAIL_MEASURE` remains for sizing K.

## 7. Perf re-gate (G-ADR11-HYBRID-PERF) — the AVX2/OpenMP libs, and the real slope

Linked the `build-cpu-perf` math-core (clang-cl `/arch:AVX2` + OpenMP; `gemma4_ffn_block_cpu`
vectorized) into the daemon via `SP_SYSTEM_BUILD_DIR=build-cpu-perf` + LLVM `libomp`, target
`target-wirecuda-perf` — the same pattern the qwen36 lane uses. Measured curve (PMAX=4096, decode
tok/s, coherent all K):

| K (tail FFNs on CPU) | tok/s | VRAM | freed |
|---|---|---|---|
| 0 (all-GPU) | **23.84** | ~11201 MiB | — |
| 4 | **5.99** | 10737 MiB | ~0.46 GB |
| 8 | **3.25** | 10221 MiB | ~0.96 GB |

**The perf-lib win is real:** K=8 went **0.5 → 3.25 tok/s (~6.5×)** vs the scalar `build-cpu` gate;
K=4 is an interactive **~6 tok/s**. **But the curve is far steeper than the §3 memory-bound ideal**
(K=8 predicted ~9.4, measured 3.25). Per-token: K0 42 ms → K4 167 ms → K8 308 ms = **~33 ms per
offloaded FFN per token**, vs the ~4 ms memory-bound compute. The extra ~29 ms is the **per-FFN
GPU↔CPU round-trip**: FFN-only offload *interleaves* with GPU attention, so each offloaded layer
forces `D2H + 2× cudaStreamSynchronize + H2D` — ~2K stream syncs/token. **The sync, not the CPU
compute, is the wall.** The honest revised verdict: a VRAM-for-latency lever with a *steep*
sync-bound slope on this interleaved architecture — usable where VRAM is the hard constraint
(K=4 frees ~0.5 GB at interactive ~6 tok/s). To flatten it: a cross-token decode pipeline (overlap
token t's CPU FFN with token t's later GPU layers) or pinned-async copies — the next real speed
project. Default-off = the 23.84 tok/s all-GPU null floor.
