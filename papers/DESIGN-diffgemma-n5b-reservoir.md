---
type: design
title: "DESIGN — N5b resident-weight reservoir (the structural gatekeeper of the iterative diffusion judge)"
description: "Collapse the ~3min/step disk-I/O wall of the native DiffusionGemma denoise loop. The 26B (14GB) doesn't fit in 12GB VRAM, so dg_dequant_resident_rows copies each layer's experts from the disk-backed mmap per forward; the OS evicts those pages between steps -> every denoise step re-faults from disk. Fix: a one-time resident host-RAM reservoir so per-step weight access is RAM->GPU, no disk. This is what makes the 48-step entropy-bound judge runnable."
tags: [diffusion-gemma, n5b, resident-reservoir, moe, streaming, io-bound, phase-5, diffusion-judge]
timestamp: 2026-06-21T00:00:00Z
resource: shannon-prime-lattice/papers/DESIGN-diffgemma-n5b-reservoir.md
sp_status: RED
sp_gate: "G-DG-N5b (premise REFUTED by measurement — see §RESULT)"
sp_commit: TBD
sp_repro: "forward = engine 0244800 diffusion_gemma_forward_cuda_sc; dg_dequant_resident_rows in cuda_forward.cu; mmap in lib/.../core/session/sp_model_load.c"
---

# DESIGN — N5b resident-weight reservoir

**Reframe (operator-ratified):** N5b is NOT a late-stage speed optimization — it is the **structural gatekeeper** of the iterative diffusion runtime. The math is proven (N4a sampler GREEN 5.8e-6; N3 self-cond GREEN, step-0 memcmp==0). The blocker is strictly **disk I/O during iterative generation**: ~3 min/step → a 48-step query is ~2.4 h; the 8-step cap likely under-converges (structural blur). Cut the I/O, the depth unlocks.

## Root cause (verified in the tree)
- **Dense path (12B):** packed weights upload into a resident VRAM `DevTensor` ONCE (cached by model pointer); per-forward access is on-device. Fast. (cuda_forward.cu `upload_packed` / `DevTensor`.)
- **Diffusion 26B (14GB):** does NOT fit 12GB VRAM → `dg_dequant_resident_rows` (the streaming-deadlock fix) copies each layer's OK_Q4B expert byte-ranges **from the `MapViewOfFile` view of the .sp-model** into owned heap, dequants, uploads, frees — per layer, per forward. The owned-heap copy fixed the *deadlock*, but the SOURCE is the disk-backed mmap, and the OS does NOT keep the 14GB cached under memory pressure (observed: file cache pinned ~368MB) → **every denoise step re-faults the experts from disk** (~3GB/s NVMe, dominating the ~71s-180s/step).

## The fix — N5b: one-time resident host-RAM reservoir
Read the model's packed data region into an **owned, committed host buffer ONCE** (at model load or the first diffusion forward), then point the per-layer dequant at THAT resident buffer instead of the mmap view. The single disk read (~14GB / ~5-7s at 3GB/s) amortizes over all steps; every subsequent step's weight access is RAM->GPU (memory-bus + PCIe, sub-second/layer), not disk.
- **Minimal change:** a global `dg_resident_base` (malloc/VirtualAlloc 14GB + `ReadFile` the .sp-model data region once; or `VirtualLock` the existing mmap view if working-set limits allow — measure). In `dg_dequant_resident_rows`, source = `dg_resident_base + (mmap_src - mmap_base)` instead of `mmap_src`. Free at session end / `sp_cuda_model_release`.
- **Byte-identical:** same bytes, resident source — the dequant arithmetic + the forward are UNCHANGED (the existing G_DG_N1B 256/256 + the N3 memcmp==0 must still hold). Additive, diffusion-path only; dense+12B untouched.
- **Memory:** 14GB committed host + ~3GB SC embed cache (`g_dg_sc_embed`) + GPU staging + working set ≈ 18-20GB. The box's commit limit was ~47GB (N0 era) → fits, but the N0 OOM warns: watch commit; the `--stream`-style bounded path stays the fallback if a smaller box ever needs it. (Owned 14GB is a HARD commit vs the mmap's lazy virtual — verify headroom before locking it in.)
- **Optional escalation (only if RAM-resident isn't enough):** (a) keep the attention/norm backbone + the token-embed resident in VRAM (small) and only the experts in the host reservoir; (b) a VRAM LRU hot-expert cache (128 experts, ~8 active/token but most activate across 256 positions×30 layers → modest hit rate; RAM-resident is the bigger, simpler win). Start with the host reservoir.

## GATE G-DG-N5b
1. **Speed:** per denoise step time drops from ~3min to seconds (target: a full diffusion forward in << the prior ~71-180s; the one-time 14GB read is amortized). Report ms/step + the one-time load.
2. **Correctness (byte-identical):** with the reservoir on, G_DG_N1B still 256/256 finite + the canvas argmax bit-identical to the pre-N5b forward (`8309d90`/`0244800`); N3 step-0 memcmp==0 still holds. Same bytes, resident source.
3. **Depth unlock:** re-run G-DIFFJUDGE-NATIVE-full at the FULL step budget (up to 48, adaptive stop) on the subset — now affordable — and report whether the recall climbs from the single-forward ~14% toward the oracle 95.6% (the real proof the iterative judge works once depth is affordable).
Receipt `tests/fixtures/chat_fullstack/G-DG-N5b.log`.

## Sequencing
N5b (this) → re-run G-DIFFJUDGE-NATIVE-full at full depth (the real judge gate) → if GREEN, N6 (wire the native diffusion judge into routes.rs, replacing the AR judge) → N7 (drafter). All behind SP_DIFFUSION, default-off = null floor; receipts-first.

## Honesty
The byte-exact-vs-Q4_K_M-oracle confound persists (different quants) — the gate stays SELECTION fidelity, not logit byte-exactness. N5b is the I/O fix; if the full-depth judge STILL under-recovers after the depth is affordable, the remaining levers are the 0.005 confidence threshold, the SC feedback magnitude, and the step count — all tunable without touching the proven sampler/recurrence kernels.

## RESULT (2026-06-22) — PREMISE REFUTED: reservoir engages but is INSUFFICIENT

Built the host-RAM reservoir as a **per-tensor resident clone cache** (`dg_resident_pt`/`dg_reservoir_free` in `cuda_forward.cu`, gated `SP_DG_RESERVOIR`, default-off = byte-identical null floor). Builds GREEN. Clone telemetry **confirms it engages** — 143 `[N5b]` clone lines on one run (embed 369 MB, big layer tensors 253 MB ×2, …), i.e. the weight SOURCE is genuinely made resident in host RAM.

**But it gives ~no speedup.** With the reservoir ON, per-query time was FLAT across queries: q1=785s, q2=+743s, q3=+747s … ≈186s/step. The warm query (q2 — cache hit, no clone, no disk) ≈ the cold query (q1 — includes the clone). So the per-forward cost is unchanged by the reservoir.

**Root cause — the I/O premise was wrong.** The one-time clone (~14 GB read) costs only ~7s; the ~186s/**step** is the per-forward **dequant (14 GB OK_Q4B → 28 GB f32 on CPU) + cudaMalloc + cudaMemcpy H2D (28 GB f32 over PCIe)** done for every weight every forward in `dg_upload_arena_w`/`dg_upload_arena_rows`. The reservoir removes the disk read from the dequant *source* but leaves the dequant+upload — the actual wall — untouched. **The diffusion judge is dequant+upload-bound (compute/PCIe), not disk-I/O-bound.**

**Real lever (N5c, the actual fix):** stop re-dequanting+re-uploading per forward — either (a) upload the PACKED OK_Q4B (14 GB) to VRAM once + dequant in a GPU kernel per forward (cuts the 28 GB f32 H2D; 14 GB packed > 12 GB VRAM ⇒ needs partial-resident + LRU), or (b) a VRAM hot-expert LRU cache (escalation (b) above) keeping the most-used dequanted experts on GPU. The host-RAM reservoir is kept as a building block (default-off, byte-identical) but is not the speed fix alone.

**Harness note:** `test_diffjudge_denoise` ignores `SP_DJ_LIMIT`/`SP_DJ_FLIMIT` (ran the full 90+50 corpus both times → two runaway multi-hour bakes were killed). A tight N5b/N5c A/B needs a real per-query limit or a single-forward micro-harness with per-step `cudaEvent` timing. The `cuda_forward.cu` reservoir change builds GREEN + is byte-identical but is left **UNCOMMITTED** pending the N5c redirect. Receipts: `_n5b_diag.log` (143 clones), `_n5b_gate.log` (flat ~745s/query ON). Banked: MEM-OKF `6f5d228dc1990c87` (RED).
