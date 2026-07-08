---
type: design
title: "ADR-010 — Whole-machine balance: what fills the 12 GB, and which offloads actually pay on THIS box"
description: "The systems answer to 'stop fighting VRAM inside the 2060, use the whole NUC11.' Grounded in MEASURED hardware truth (project-perf-wholemachine) + this session's live VRAM numbers. What fills the 12 GB: model weights 8.8 GB (fixed, must stay resident) + KV caches ~2.4 GB (the ONLY movable mass) + buffers. The binding constraint is PCIe gen3 x8 at ~6.2 GB/s, which forbids per-token weight streaming and kills most naive offloads. Each of the operator's ideas tested against physics: CPU/AVX2 matmul (bounded — frees VRAM at ~8× slowdown, only the KV-attention math is a candidate, not weights), iGPU Xe-LP (0.75 TFLOPS, dp4a only — cold-tail only), Optane M10 (block ~1GB/s, NOT PMEM — cold episodes only, never weights/hot-KV), the 24 MB L3 (activation locality, not a store). The ONE lever that pays: the global-KV cache is the entire Pmax-scaling term (~128 KB/token across the 8 full-attention layers), and it is what oversubscribes — bound/spill it (the XBAR global-eviction slab, already GREEN but NOT wired into the served decode; a resident-window cap is the low-risk first step) to free the VRAM that thrashes. The split-crate design (math-core exact substrate / engine CUDA / host-CPU-perf libs / the dormant XBAR slab) is exactly the set of levers — but only the KV-offload one clears the PCIe wall."
tags: [design, adr, whole-machine, vram, offload, pcie, cpu, igpu, optane, kv-cache, xbar, balance, honest-negative]
timestamp: 2026-07-08T00:00:00Z
resource: shannon-prime-lattice/papers/PPT-LAT-ADR-010-WHOLE-MACHINE-BALANCE.md
sp_status: "ANALYSIS (measured, with an honest mid-flight correction: the MODEL fills the card, the KV is small) + auto-fit realized default-off. The real lever = CPU-resident layer offload (ADR-011 candidate)."
sp_gate: "G-PK2-AUTOFIT (measured VRAM breakdown + auto-fit behavior) — tests/perf/G-PK2-AUTOFIT.log"
sp_commit: "builds on project-perf-wholemachine (hardware truth) + ADR-009 (prefill VRAM ceiling)"
sp_repro: "nvidia-smi breakdown @ Pmax=4096 vs 20000; SP_G4_KV_GLOBAL_W cap"
---

# ADR-010 — Whole-machine balance

**Status: DESIGN + one lever realized.** The systems answer to "don't fight VRAM inside the 2060 —
balance the whole NUC11." Grounded in the MEASURED hardware truth ([[project-perf-wholemachine]])
and this session's live VRAM numbers, not architecture-diagram optimism.

## 1. What actually fills the 12 GB (measured — and the correction that matters)

Live, RTX 2060 12 GB, served 12B (`.sp-model` = 8.79 GB on disk). Measured by reading free VRAM
*inside* `gemma4_kv_open` (after weights resident, before the KV/buffer allocs) and again at idle:

| Component | VRAM | Movable? | Why |
|---|---|---|---|
| **Model RESIDENT** (OK_Q4B codes + PLE + packed embd + arena/scratch pools) | **~10.9 GB** | only by moving LAYERS off-GPU (§3) | measured: 10 937 MiB used before any KV alloc |
| **KV cache** (SHARED-KV: only a few owner layers × Pmax) | **~0.78 GB @ Pmax20000** | yes, but small | shared-KV → the global cache is ~2 owner layers, NOT 8; ~0.65 GB |
| **Working buffers** (dq/k/v, dscr, dlog[262144], dseq[Pmax]) | **~0.1 GB** | no | small |
| **Free (dedicated card)** | **~0.57 GB** @ Pmax20000 (11 719 used) | — | the thin headroom |
| **Batched-prefill scratch** (transient) | **~0.4–1 GB** | ADR-009 | O(n) f32 activations; eats the thin headroom → the batch ceiling |

**★ THE CORRECTION (honest):** my first pass assumed the globals were ~2.5 GB (8 full-attention
layers × Pmax). Wrong — gemma4-12b uses **shared-KV**, so only a handful of owner layers hold a
cache; the KV is **~0.78 GB, not 2.5 GB**. The dominant term is the **MODEL itself at ~10.9 GB
resident** — the 12B *fills the 12 GB card by design*, leaving ~0.57 GB free. Two consequences:
(a) the **original "stall" was co-resident LM Studio** (~6.4 GB) → model+LMStudio = ~15 GB ≫ 12 GB
oversubscription, NOT the KV; (b) the **ADR-009 batch thrash** was the transient batch scratch
(~0.4–1 GB) eating the thin ~0.57 GB headroom. The KV cache was never the movable mass — **the
model is.**

## 2. The binding constraint (why most offloads don't pay)

**PCIe gen3 x8 ≈ 6.2 GB/s real** (measured `_pcie_bw.cu`; NOT x16, NOT Gen5). To run a layer
somewhere other than the 2060 you must move either its **weights** or its **activations** across
that bus every token. Weights: the 8.8 GB model at 6.2 GB/s = **~1.4 s/token** just to stream —
catastrophic. So **weights must stay resident**; no CPU/iGPU/Optane weight offload pays. Only data
that is (a) small per token, or (b) accessed with locality / infrequently is a candidate: the KV
cache and cold episodes. Everything below follows from this one number.

## 3. The operator's ideas, each against the physics (re-judged on the corrected breakdown)

- **"Run the matmul on the CPU (24 MB SVM) / system RAM."** ★ **This is the relevant lever —
  because the MODEL, not the KV, fills the card.** The i9-11900KB has **24 MB L3** (that's the
  "SVM"), 8 cores, ~40 GB/s DDR4. To free real VRAM you must evict *weights*, and the only weights
  that can move are whole LAYERS: keep a subset of layers' OK_Q4B weights in **host RAM** (31.5 GB
  free) and **compute those layers on the CPU** (AVX2/OpenMP — the `build-cpu-perf` libs already
  ship, the qwen36 lane uses them), exchanging only the E-sized activation (~15 KB/token/layer)
  over PCIe. Cost: those layers run ~8–10× slower (40 GB/s DRAM vs the 2060's ~336 GB/s), but each
  offloaded layer frees ~0.2 GB VRAM. **Verdict: a genuine VRAM-for-latency trade** — offload k
  layers → free ~0.2k GB → slower by ~(k/48)×8×. Worth it to (a) create headroom that stops the
  batch/co-tenant thrash, or (b) fit a *second* small model / longer everything. NOT a speedup;
  a rebalance. The `_int8` weight streaming path (per-token weight fetch over PCIe) stays refuted
  (~1.4 s/token) — the layer must COMPUTE where its weights live (CPU), not stream them to the GPU.
- **"Offload the ring to RAM / Optane."** Re-judged: the KV is only **~0.78 GB**, so this frees
  little. The XBAR host-spill + LSH slab (GREEN, un-wired) is still architecturally right for
  *very long contexts* (where even shared-KV grows), but it is NOT the VRAM lever on today's
  persona-sized chats — the model is. Deferred to when context length, not the model, is the term.
- **"Offload weights to Optane."** Optane M10 = **block NVMe ~1 GB/s, NOT PMEM** — slower than the
  PCIe it feeds. Refuted for weights. Right role = the **cold XBAR episode store**. (Note: for the
  CPU-layer-offload above, the offloaded weights live in **DRAM**, not Optane.)
- **"Shard experts across devices via CRT."** CRT splits *numbers*; a GEMM runs in FULL in each
  prime channel → every device needs ALL weights → per-device cut = zero. Refuted as a sharding
  mechanism. CRT's gift = *bit-exactness across devices* (the enabler of a clean split), not the split.
- **"iGPU (Xe-LP)."** 32 EU, no XMX, ~0.75 TFLOPS, dp4a only — 10–25× weaker; feeding it costs the
  same activation exchange as the CPU but with less RAM and no AVX2 maturity. The CPU is the better
  offload target on this box. iGPU = cold-tail only.

## 4. The verdict, ranked (corrected)

1. **CPU-resident layer offload** (weights in DRAM, compute on CPU AVX2, exchange only activations).
   The one lever that frees *real* VRAM, because the model is what fills the card. VRAM-for-latency;
   the `build-cpu-perf` machinery exists. The big-but-correct project.
2. **Auto-fit the KV to free VRAM** (`SP_G4_KV_AUTOFIT`, realized §5) — the co-tenant safety clamp:
   size Pmax to what's actually free so a shared card (the original LM-Studio stall) never
   oversubscribes. Small VRAM effect (KV is small) but directly fixes the *original stall's cause*.
3. **Chunked batch scratch** (ADR-009 follow-on) — cap the transient O(n) f32 scratch so the batch
   win fires without eating the thin headroom.
4. **XBAR host-spill KV slab** — for *long-context* regimes (deferred; not today's term).
5. **Optane = cold episodes, iGPU = cold-tail, CRT = exactness** — already in role.

## 5. The realized first step — auto-fit the KV to free VRAM (G-PK2-AUTOFIT)

`SP_G4_KV_AUTOFIT=1` (default-off = the passed Pmax verbatim = **null floor**): at
`gemma4_kv_open`, read free VRAM (weights already resident) and clamp Pmax so the KV cache + a
margin fit — so a **shared card never oversubscribes** (the original stall = co-resident LM Studio;
autofit would have clamped Pmax to fit the remaining VRAM instead of thrashing). Small effect on a
dedicated card (the 12B already fits at Pmax=20000 with ~0.57 GB free), decisive on a shared one.
Honest limitation found in the gate: on a nearly-full card the free-read at open under-estimates
(the arena/scratch pools allocate lazily), so the clamp is conservative — margin-tunable via
`SP_G4_KV_AUTOFIT_MARGIN_MB`. It never RAISES Pmax and never breaks the dedicated-card path.

## 6. The real conclusion (the operator's thesis, confirmed — and it points at the CPU)

The split multi-crate design **is** the set of levers. But the corrected measurement flips which
one matters: **the 12B model at ~10.9 GB resident fills the 12 GB card — the KV cache is a rounding
error (~0.78 GB), and the ~0.57 GB headroom is the whole game.** So the physics verdict is:
- **You cannot free meaningful VRAM by moving DATA (KV/episodes) — there isn't much.** You free it
  by moving **WEIGHTS**, and PCIe x8 forbids streaming them per token — so the weights must
  **compute where they live**. That is the **CPU-resident layer offload**: a few layers' weights in
  40 GB/s DRAM, computed on 8 AVX2 cores, exchanging only the tiny activation. The operator's
  instinct ("run the matmul on the CPU… balance of the entire system") is **correct** — it is the
  one lever that rebalances the dominant mass, at a bounded latency cost.
- The split design enables it cleanly: the math-core forward is already CPU-capable (the reference
  path), the `build-cpu-perf` AVX2/OpenMP libs exist, and CRT guarantees the CPU and GPU legs stay
  **bit-identical** — so a hybrid CPU+GPU forward is drift-free and auditable, which is exactly the
  property that makes a split trustworthy. That is the next real project (ADR-011 candidate):
  a per-layer placement policy (GPU for the hot majority, CPU-resident for the cold tail that buys
  back headroom), gated on end-to-end tok/s and VRAM freed.
