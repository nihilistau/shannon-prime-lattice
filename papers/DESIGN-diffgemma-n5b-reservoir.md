---
type: design
title: "DESIGN — N5b resident-weight reservoir (the structural gatekeeper of the iterative diffusion judge)"
description: "Collapse the ~3min/step disk-I/O wall of the native DiffusionGemma denoise loop. The 26B (14GB) doesn't fit in 12GB VRAM, so dg_dequant_resident_rows copies each layer's experts from the disk-backed mmap per forward; the OS evicts those pages between steps -> every denoise step re-faults from disk. Fix: a one-time resident host-RAM reservoir so per-step weight access is RAM->GPU, no disk. This is what makes the 48-step entropy-bound judge runnable."
tags: [diffusion-gemma, n5b, resident-reservoir, moe, streaming, io-bound, phase-5, diffusion-judge]
timestamp: 2026-06-21T00:00:00Z
resource: shannon-prime-lattice/papers/DESIGN-diffgemma-n5b-reservoir.md
sp_status: DESIGN
sp_gate: "G-DG-N5b (pre-registered below)"
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
