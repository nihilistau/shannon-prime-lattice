---
type: design
title: "ADR-009 — Prefill speed on a 12 GB card: batched-under-ring is a bounded win, batching is not the general lever"
description: "The empirical verdict on cold-prefill acceleration for the served 12B on an RTX 2060. Batched prefill was previously blocked under the SWA ring (declined → per-token fallback), so the PRODUCTION ring config never used it. This ADR lifts that block (ring-layout sink + retained shared-owner K/V) and MEASURES it: at PMAX=4096 a persona-sized cold prompt (n≈837) prefills in 6.6s coherent vs ~46s per-token (~7×). But the batched path materializes O(n) f32 activation scratch (~1 GB at n≈1765), which oversubscribes the 12 GB card at large n and/or the production PMAX=20000 — the exact WDDM-thrash signature of the original stall. A VRAM guard now DECLINES the batched path cleanly (→ per-token null floor) when the scratch won't fit, making batching a safe opt-in accelerant for moderate cold prompts, never a footgun. Conclusion: batching is a bounded win, not the general prefill lever; the general lever is the per-token path (wave-1 fix) + a smaller PMAX or a chunked/streamed batch (future)."
tags: [design, adr, prefill, speed, batched, ring, vram, honest-negative, dp4a, cublas]
timestamp: 2026-07-08T00:00:00Z
resource: shannon-prime-lattice/papers/PPT-LAT-ADR-009-PREFILL-SPEED.md
sp_status: "REALIZED + GATED — G-PK2-BATCHRING 3/3 live: n=837 batch 6.7s (~7×), n=1765 graceful per-token fallback 99s, both coherent; VRAM guard + persist guard"
sp_gate: "G-PK2-BATCHRING 3/3 (tests/perf/G-PK2-BATCHRING.log)"
sp_commit: "engine (wave 6); builds on G-PK2-PREFILL (wave 1 per-token fix) + G-PK2-PREFILL-DP4A (wave 2 honest-negative)"
sp_repro: "_pk2_batchring_daemon.bat (ring+batch @PMAX=4096) + tests/perf/_pk2_dp4a_probe.py"
---

# ADR-009 — Prefill speed on a 12 GB card

**Status: REALIZED, with a bounded win and an honest ceiling.** The third and final data point on
cold-prefill acceleration (after wave-1 per-token fix G-PK2-PREFILL and wave-2 dp4a honest-negative
G-PK2-PREFILL-DP4A).

## 1. What was blocked, and lifting it

`gemma4_kv_prefill_batched` (one n-wide cublas forward, ~7 matmuls × 48 layers instead of n×
per-token GEMVs) declined whenever `ring_W != 0`. Since the PRODUCTION config (`run_console.bat`)
runs the SWA ring, the batched path was **never taken in production** — every cold prompt paid the
per-token tax. Wave 6 lifts the precondition: under the ring, attention reads the CONTIGUOUS
per-token scratch (correct regardless of the resident layout), sharer layers read retained
contiguous copies of the two shared owners, and each SWA owner's K/V is sunk into the resident
ring layout (`k_ring_sink`, position p → slot p%W) so the subsequent DECODE reads a correct
windowed cache. `commit_pos` is anchored at n (a cold batch writes no undo-journal).

## 2. The measurement (RTX 2060, 12 GB)

- **Win:** at **PMAX=4096**, a persona-sized cold prompt **n≈837 prefills in 6.6s, coherent**
  ("Paris" through the full 48-layer forward + a correct ring-cache decode) vs **~46s** on the
  per-token path — **~7×**. This is exactly the gateway's persona+tools turn size (the original
  stall doc noted "persona-sized ~840-tok chats"), so it is the case that matters most.
- **Ceiling:** the batched path materializes **O(n) f32 activation scratch** (~15 n-sized E/FF/QD
  buffers + the ring retained copies) — ~1 GB at n≈1765. On the 12 GB card this oversubscribes
  VRAM for **large n** (n≈1765 fails at PMAX=4096) and for the **production PMAX=20000** even at
  n≈837 (96% VRAM, GPU util collapses to 12% — the WDDM paging thrash that IS the original stall).

## 3. The safety guard (the null floor made robust)

A **VRAM guard** now runs before any allocation: it estimates the batched scratch
(`per_tok · n · 4B`), reads free VRAM (`cudaMemGetInfo`), and **declines cleanly** (returns -1 →
the caller falls back to the per-token path, the G-PK2-PREFILL null floor) when the estimate
exceeds free VRAM minus a margin (`SP_KV_BATCH_VRAM_MARGIN_MB`, default 512). So the batched path
is a **graceful opt-in accelerant** — it fires only when it fits, and degrades to the working
per-token path otherwise. It never poisons the CUDA context by half-allocating. Default-off in
production (`run_console.bat` does not set `SP_KV_PREFILL_BATCH`); the whole feature is opt-in.

## 4. Conclusion — batching is a bounded win, not the general lever

Across three waves the verdict is consistent: **on a 12 GB card, batching the prefill is a
memory-bound trade, not a free speedup.** It wins decisively for moderate cold prompts at moderate
PMAX (the common persona-turn case, ~7×), and it is the wrong tool for large prompts or the
20k-context config (the f32 activation scratch doesn't fit). The dp4a GEMM (wave 2) was arithmetic-
correct but occupancy-bound; a cublasGemmEx-int8 variant would ride the SAME O(n) f32 activation
scratch and hit the SAME VRAM ceiling — so it is NOT pursued (the matmul is not the bottleneck;
the batched activation storage is). The durable levers: the per-token path (wave-1 chunked-sync
fix, the production default) + `SP_PERSIST_KV` warm-turn reuse; and, for a future session, a
**chunked/streamed batch** (process the n tokens in VRAM-bounded tiles) that keeps the batched
GEMM efficiency without the full-n scratch footprint.

## 5. The gate (G-PK2-BATCHRING 3/3, measured)

Ring-on `SP_G4_KV_RING_W=1024`, PMAX=4096, `SP_KV_PREFILL_BATCH=1`, `SP_PERSIST_KV=0`,
`SP_KV_BATCH_VRAM_MARGIN_MB=96`:
- **turn1 cold n≈837 → 6.7s, coherent "Paris"** (batch fires; ~7× vs ~39s per-token)
- **turn2 cold n≈837 → 6.7s, coherent** (each turn cold under non-persist; batch fires again)
- **turn3 cold n≈1765 → 99s, coherent** (the VRAM guard DECLINES the larger batch → graceful
  per-token fallback; correct, just not accelerated) — the null floor, live-proven.

Two guards make it safe: the **VRAM guard** (declines when the batched scratch + margin exceeds
free VRAM → per-token) and the **persist guard** (declines when `SP_PERSIST_KV=1`, because a
batched-ring cache is valid for a fresh decode but not as a base for persist continuation — a
second reusing turn returned empty pre-guard; now it never takes the batched path).

## 6. Honest scope

Enable `SP_KV_PREFILL_BATCH=1` (with `SP_PERSIST_KV=0`) for moderate-PMAX single-shot cold prefills
— e.g. the gateway's fresh-context agent turns — to get the ~7× on persona-sized prompts. Leave it
off (default) for the 20k-context config and for persist-reuse multi-turn chat. `SP_KV_BATCH_VRAM_
MARGIN_MB` (default 512; the gate used 96) tunes the decline threshold — the batched scratch is
~360 MB at n≈834, so a small margin is right on a card with ~1 GB headroom. Future work: a
persist-continuation-compatible batch (initialize the undo-journal/commit state the way per-token
does incrementally) would let the production ring+persist config use batching too.
