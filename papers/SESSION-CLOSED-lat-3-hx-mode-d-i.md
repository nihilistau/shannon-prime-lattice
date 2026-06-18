---
type: session-handoff
title: SESSION CLOSED — lat-3-hx-mode-d-i (Sprint I — single-layer smoke)
description: "Date: 2026-05-30"
tags: [session-handoff]
timestamp: 2026-05-29T10:53:39Z
resource: shannon-prime-lattice/papers/SESSION-CLOSED-lat-3-hx-mode-d-i.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# SESSION CLOSED — lat-3-hx-mode-d-i (Sprint I — single-layer smoke)
**Date:** 2026-05-30
**Engine commits:** `da0bd38` (parser), `e1a4407` (driver), `7d1e7a9` (verbatim output capture)
**Umbrella tag:** `lat-phase-3-hx-mode-d-i-closed`

Sprint I closes **CLEAN — all 4 gates PASS on first device run.** Real Qwen3-0.6B `W_gate` tile loads from `.sp-model`, dequantizes Q8 → i16 per-row, drives the existing Sprint G dual-VTCM Halide kernel, and produces bit-identical output against the inline scalar reference at q_bits=14 across three distinct activation patterns. 100-iter leak gate clean.

This is the first time real model weights have flown through the Hexagon bridge end-to-end. Sprint J (full multi-layer loader, KV cache, Fix B aliasing, sp_daemon integration) is now empirically unblocked.

---

## Pre-flight summary

| | Result |
|---|---|
| A. `.sp-model` location | `engine/build-cpu/tests/qwen3_rt.sp-model` (754,551,808 B, sha256 `30717fbd…f122376`) |
| B. Bridge regression | Sprint G `T_HALIDE_FFN_VTCM_*` all PASS at engine HEAD `b5a642b` (skel rebuilt + pushed to align device with source) |
| C. Sprint H tags | All 4 present |
| D. Layer + tile + q | layer 0, W_gate, 128×128, q=14, b=0; uses `sp_compute_ffn_2stage_diag_halide` (Sprint H method 9) with W2 zeroed |

The skel-state alignment step in B is worth flagging: the device's `libsp_compute_skel.so` held my unshipped Sprint H.PATCH (q_bits cast<i32>) during the pre-flight test_hvx run. Rebuilding from source HEAD and re-pushing brought the device back to Sprint H closure-state (q=16 BISECT FAIL mm-2 got=-816 as documented). Sprint I uses q=14 — well within the validated range either way — so the state nuance didn't affect Sprint I's correctness; it's recorded here for the audit trail.

---

## Gate table (verbatim from engine commit `7d1e7a9` artifact)

```
T_MODEL_HEADER_PARSE     PASS  (arch_id=2 [QWEN3], 509 tensors, data_offset=0x20000)
T_DMA_TILE_LOAD          PASS  (128×128 Q8→i16, w_tile[0..4]=[-146, 0, -395, -453])
T_LAYER_MATMUL_BITWISE
  pattern=sentinel       PASS via VTCM  pcyc=9,296,397  hidden[0..4]=[0, 520, 2149, 0]
  pattern=pseudorandom   PASS via VTCM  pcyc=9,277,391  hidden[0..4]=[1903, 0, 0, 2339]
  pattern=all-ones       PASS via VTCM  pcyc=9,278,006  hidden[0..4]=[0, 0, 0, 0]
T_LAYER_NO_HEAP_LEAK     PASS  (100 iter in 1.034 s, 10.3 ms/iter avg)
```

---

## Empirical facts uncovered by Sprint I

1. **Qwen3-0.6B hidden_size = 1024, intermediate_size = 3072.** The phase-log entry 2026-05-30 (lattice `9b784c9`) estimated hidden_size=896; the actual `.sp-model` shows W_gate dims = [1024, 3072]. Sprint J's full-loader sizing should use these confirmed values. *No silent gate revision* — the phase log's estimate stands as the prior expectation; this closure cites the empirical correction.
2. **509 tensors** in the model file (header + table → 509 × 256 B = ~127 KB table at offset 512).
3. **W_gate.size_bytes = 3,145,728 = 1024 × 3072 × 1 B** confirms the Q8 packed arena layout described in `reference-zero-copy-invariant`. Scale companion = 3072 × 4 B (one f32 per row).
4. **Halide diag-method pcycles ~9.3M** for the 128×128 / B=4 shape. Sprint G's production-method same-shape gate measured ~7.9M. The +1.4M delta is the diag method's extra hidden_out VTCM write + memcpy at the handler's end. The production method (when used by Sprint J for non-diagnostic runs) gets the lower cost back.
5. **100 invocations in 1.034 s** = 10.3 ms/iter average. Dominated by FastRPC RTT (~9-10 ms/call, consistent with Sprint E's batched-vs-unbatched bench). No degradation across iterations.

---

## Module deliverables (cited line ranges in engine repo)

| File | Sprint I role | LOC |
|---|---|---|
| `tools/sp_dsp_smoke/src/sp_model_layer.rs` | Parser library: header + tensor table + Q8 tile dequant | 192 |
| `tools/sp_dsp_smoke/src/sp_model_layer_smoke.rs` | Driver bin: 4 gates inline, mirrors `test_hvx.rs:630-668` invoker + `674-702` scalar ref | 247 |
| `tools/sp_dsp_smoke/Cargo.toml` | `[[bin]]` entry for `sp_model_layer_smoke` | +9 |
| `tools/sp_dsp_smoke/sprint_i_run_output.txt` | Captured verbatim run output (commit `7d1e7a9`) | 57 |

Code reuse from prior sprints (no copies; same compiled crate):
- `FastRpcSession`, `DmaBuffer`, `RemoteArg`, `make_scalars` — `dsp_rpc.rs` (Sprint A/B)
- Diag-method invoker shape — `test_hvx.rs:630-668` (Sprint H method 9)
- Saturating-arithmetic scalar reference — `test_hvx.rs:674-702` (Sprint G, matches `vmpy.h:sat`)

---

## Architectural-discipline notes

- **Per-commit isolation held.** Parser landed at `da0bd38` with the tree still buildable (parser file present but unreferenced). Cargo.toml `[[bin]]` entry deferred to commit 3 (`e1a4407`) so each commit left a working build. Per `feedback-bundled-changeset-root-cause-ambiguity` discipline.
- **No production skel changes.** Sprint I uses the existing Sprint H IDL method 9 with W2 zeroed. The Halide kernel + skel handler at engine HEAD `b5a642b` are unchanged.
- **No `shannon-prime-system` changes.** The .sp-model parser is a Sprint-I local module under `tools/sp_dsp_smoke/`. Sprint J productionizes a loader in `sp_daemon`.
- **No new memory entries.** The empirical hidden_size correction is recorded here in the closure, not in memory.

---

## Open work + Sprint J unblock

Sprint J (the full Phase 4 loader) is now ready to begin. The Sprint I evidence:
- The .sp-model header + tensor table format works in Rust per `sp_model.h` v0.1.
- Q8→i16 dequantization with per-row scales is correct against the matmul kernel.
- One layer's W_gate tile flies through the existing dual-VTCM Halide pipeline at q=14 with zero divergence from the saturating scalar reference.
- The kernel handles ~9.3M pcycles per 128×128 / B=4 tile; a full Qwen3-0.6B FFN (W_gate @ 1024×3072) would be ~24 tiles × 7M pcycles ≈ 170M pcycles per FFN layer matmul-1. Real-time inference budget needs Sprint J's batching + KV reuse to amortize.

Sprint J scope (out of Sprint I, ready for plan):
- Multi-layer load (28 layers for Qwen3-0.6B; 28 × 3 matmuls = 84 FFN matmuls per token).
- KV cache allocation in either DDR or VTCM (Sprint K material — gated on Sprint J).
- Fix B aliasing: zero-copy mmap of `.sp-model` into FastRPC SMMU instead of the current `read_layer_w_gate_tile` byte-copy path.
- Full FFN composition (gate × up → SiLU → down).
- `sp_daemon` integration: move the loader out of `sp_dsp_smoke/bin/` into `sp_daemon/src/`.
- Real prefill activation tensors (replace synthetic patterns).

**Sprint H.PATCH** (q_bits >= 16 codegen divergence) remains as filed in the Sprint H closure. Sprint I avoided it by using q=14. Sprint J will need to either: (a) constrain all real-model q_bits ≤ 15, (b) apply Sprint H.PATCH (one-line `cast<int32_t>(q_bits)` change verified empirically during Sprint H), or (c) revisit if real Qwen3 quantization scales push q outside 15.

---

## Sub-tags

| Sub-tag | Engine commit |
|---|---|
| `lat-phase-3-hx-mode-d-i-parser-correct` | `da0bd38` |
| `lat-phase-3-hx-mode-d-i-bridge-bitwise` | `e1a4407` |
| `lat-phase-3-hx-mode-d-i-leak-free` | `7d1e7a9` |
| `lat-phase-3-hx-mode-d-i-closed` (umbrella) | `7d1e7a9` |

Lattice tags mirror the engine SHAs at the closure-commit head.
