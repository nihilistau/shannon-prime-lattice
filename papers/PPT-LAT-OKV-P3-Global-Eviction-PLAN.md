---
type: design
title: "O(1) KV P3 — global-layer eviction for unbounded context (build plan, ready to execute)"
description: "Execute-ready plan to break the ~16-20K GPU-resident ceiling on the 12GB 2060 by evicting the 8 GLOBAL KV layers (the only O(n) growth) out of VRAM. KEY ANTI-REBUILD FINDING: the eviction substrate already exists (SP_ARM_SLAB compact global slab + host-RAM store, SP_ARM_LSH learned router, gemma4_kv_replay bring-back; G-P3-SHARED/PPL already GREEN). P3 = wire the existing ARM slab/LSH into the live daemon kvdecode path + gate end-to-end; NOT a from-scratch build."
tags: [design, okv, p3, eviction, global-layers, arm-slab, lsh, unbounded-context, gemma4, plan]
timestamp: 2026-06-30T00:00:00Z
resource: shannon-prime-lattice/papers/PPT-LAT-OKV-P3-Global-Eviction-PLAN.md
sp_status: DRAFT
sp_gate: "plan only (no code this pass); the gate G-OKV-P3-EVICT is defined in §4"
sp_commit: TBD
sp_repro: "grounded from engine src: cuda_forward.cu (sp_g4_kv, gemma4_kv_open/step, gemma4_kv_replay, §3q SP_ARM_SLAB/SP_ARM_LSH); daemon routes.rs run_kvdecode_chat; prior gates G-P3-SHARED/PPL, NIAH cond A/B/C (_run_niah_cc.bat)"
---

# O(1) KV — P3: global-layer eviction for unbounded context (build plan)

## 0. Why (the binding fact from P2)
On the 12 GB RTX 2060 the 12B weights + CUDA workspace consume **~11.4 GB**, leaving only ~0.5–0.9 GB for KV → a **~16–20 K-token resident ceiling** (measured: Pmax 24 K barely allocs + thrashes, 32 K OOMs). Under the SWA ring the 40 SWA layers are already O(1); the **8 GLOBAL layers are the sole O(n) growth** (32 KB/token, full-cache to Pmax). To exceed ~20 K, the globals must leave VRAM. P1 (persist) + P2 (ring at the shipped 20 K) are done; P3 is the only piece that lifts the ceiling.

## 1. KEY FINDING — the eviction substrate already exists (do NOT rebuild)
Grounded in `src/backends/cuda/cuda_forward.cu`:

- **`gemma4_kv_replay(s, epdir, npos, zero)`** — injects stored owner-K/V back into the resident cache at `[dpos, dpos+npos)` (the bring-back primitive; journaled; #222 GREEN).
- **`SP_ARM_SLAB` (§3q C-b.2 "COMPACT GLOBAL SLAB")** — caps the 8 global `dKc/dVc` at `B+sink+margin` slots (NOT Pmax). The **full global history lives in a host-RAM store (`arm_ramK/V`)**; the slab is paged from RAM into compact slots `[0,m)` and the attention gather reads compact-slot indices. **This is exactly the global-eviction mechanism.**
- **`SP_ARM_LSH` / `SP_ARM_LSH_R`** — the learned LSH router (`R·Rᵀ` / `R [hd*r]`) that **scores and selects which global history to page into the slab**.
- **Already-GREEN gates:** `G-P3-SHARED`, `G-P3-SHARED_E2B`, `G-P3-PPL` (`_p33_ep*`, `_p34_gate`); the **NIAH cond C** (`_run_niah_cc.bat C` = slab + LSH r=32, "learned router selects the needle into the slab → HIT") is the retrieval gate.

So the math, the store, the router, the bring-back, and offline gates exist. The unbuilt part is integration.

## 2. The gap (what P3 actually has to do)
The ARM slab / LSH path was developed + gated in the **§3q CUDA test-bin path** (`test_gemma4_cuda.exe`, `SP_G4_NIAH`/`SP_ARM_*`). It is **NOT wired into the live daemon serving path** (`routes.rs::run_kvdecode_chat` → `gemma4_kv_open/prefill/decode` → `gemma4_kv_decode_logits`), which today opens the plain `sp_g4_kv` ring (globals full-cache to Pmax). **P3 = wire the existing ARM slab + LSH router into the daemon's resident-cache path, and gate it end-to-end on the live 12B chat** (with persist-KV from P1).

Two eviction tiers — keep them distinct:
- **Tier 1 (this P3): ARM slab → HOST RAM**, verbatim global K/V, LSH-paged. Bounds resident VRAM; extends context to host-RAM-bounded (effectively unbounded for chat).
- **Tier 2 (separate, the latent-mem/MeMo + XBAR Ring-2→Optane store): semantic consolidated episodes** (NIGHTSHIFT, C2/Frobenius). The long-term memory; not required for P3.

## 3. Build steps (P3.x)
1. **P3.0 — verify the wiring point.** Confirm whether `gemma4_kv_step` (the daemon decode path) already branches on `SP_ARM_SLAB/SP_ARM_LSH`, or whether the slab path is only reachable from the test bin. Map the exact entry (likely `gemma4_kv_open` must alloc `arm_ramK/V` + the slab, and `g4_kv_step`'s global gather must read slab indices).
2. **P3.1 — daemon knobs.** Add `SP_DAEMON_KVDECODE_SLAB` (+ `_LSH`, `_LSH_R` paths) → set `SP_ARM_SLAB/SP_ARM_LSH*` at open, exactly like the existing `SP_DAEMON_KVDECODE_RING_W` surfacing in `daemon.rs`. Default-off = today's full-global null floor.
3. **P3.2 — open-time alloc.** In `gemma4_kv_open`: when slab on, cap the 8 global `dKc/dVc` to `B+sink+margin`, allocate the host-RAM `arm_ramK/V` global store; SWA stays on the ring. This makes resident global VRAM **fixed** (≈ 8×4 KB×slab_slots, e.g. ~96 MB at 3 K slots) instead of 8×4 KB×Pmax.
4. **P3.3 — per-step paging.** In `g4_kv_step`: append each new global K/V to the host store; the LSH router selects the slab residents for the current query; gather attention over the slab. (This is the §3q logic; the work is making it run under the daemon's persistent decode + the P1 persist append, not the one-shot test bin.)
5. **P3.4 — persist-KV interaction.** `KV_COMMITTED` still tracks the token sequence; the slab is a resident *projection* of the host-RAM global history. Ensure suffix-append (P1) coexists with the slab (the global store grows append-only; the slab re-pages per turn). Bit-exact-when-off.

## 4. Gate — G-OKV-P3-EVICT (the kill-test)
- **(a) Byte-exact when the needle is resident:** with the slab large enough to hold the whole context, the live-chat output is byte-identical to full-global (== the P1/P2 null floor). *Kill: any divergence ⇒ slab/gather corrupts global K/V.*
- **(b) Retrieval past the slab (the real win):** NIAH cond C on the **live daemon** — needle beyond the slab capacity, LSH pages it back → **HIT**, matching full-cache. Characterize vs depth (honest: gemma's 8 global layers cap what's *retrievable*; a deep MISS is the model, not the paging — separate "router paged the right block" from "model attended").
- **(c) VRAM bound:** a 40–64 K-token context runs **without OOM** because resident globals are capped to the slab (the P2 ceiling is lifted). Report peak VRAM flat vs context length.

## 5. Effort + sequencing (honest)
Medium-large **engine** build (CUDA `gemma4_kv` path + `daemon.rs` knobs + gates), GPU-heavy to gate, and it touches the resident-cache hot path that P1/P2 + byte-exact ride on — so it wants a **fresh, focused session**, not a tail-end bolt-on. Lead with **P3.0** (the wiring-point audit) before any code: if `SP_ARM_SLAB` already reaches `g4_kv_step`, P3 collapses to daemon knobs + gates (small); if not, P3.2–P3.3 are the real work. Reuse the existing `_run_niah_cc.bat` cond C as the retrieval gate (port it to drive the daemon, as the P1 harness did) rather than the standalone `niah.c` (which errored on `qwen3_generate_kv`).

**Bottom line:** P3 is integration + gating of an already-built eviction substrate (ARM slab + LSH + replay, partial G-P3 green), not a new memory system. Start at P3.0.
