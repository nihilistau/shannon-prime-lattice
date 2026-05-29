# SESSION PLAN — lat-3-hx-mode-d-j (Sprint J — full model loader + KV cache + AppState)
**Date:** 2026-05-30
**Goal:** Scale the Sprint I single-tile loader to all 28 Qwen3-0.6B layers; allocate the KV cache at ctx_max=4096; integrate model + KV into sp-daemon AppState; verify end-to-end via 6 gates on S22U.

NO inference loop (Sprint K). NO Fix B zero-copy aliasing (post-Sprint-J follow-on). NO Halide kernel changes.

---

## 0. Pre-flight (Stage 0 — verbatim results)

### A. Sprint I regression check

`adb shell '/data/local/tmp/sp_model_layer_smoke'` re-ran at engine HEAD `7d1e7a9`:

```
T_MODEL_HEADER_PARSE PASS  (arch_id=2 QWEN3, 509 tensors)
T_DMA_TILE_LOAD      PASS
T_LAYER_MATMUL_BITWISE × 3 patterns PASS via VTCM  pcyc ~9.3M
T_LAYER_NO_HEAP_LEAK PASS  (100 iter / 999 ms / 10.0 ms/iter)
```

All four Sprint I sub-tags + closed umbrella present.

### B. Memory budget from arch_struct (bytes 24..80 of qwen3_rt.sp-model)

Decoded sp_arch_info (Qwen3):

| Field | Value |
|---|---|
| `arch_id` | 2 (SP_ARCH_ID_QWEN3) |
| `vocab_size` | 151,936 |
| `hidden_size` | 1,024 |
| `n_layers` | 28 |
| `n_heads` | 16 |
| `n_kv_heads` | 8 (GQA) |
| `head_dim` | 128 |
| `context_length` | 40,960 |
| `intermediate_size` | 3,072 |
| `rope_theta` (fp32) | ~1e6 |
| `tied_embedding` (likely flag at +40) | 1 |
| `preferred_precision` | 2 (FP16) |

Weight footprint (Q8 packed; row-major):

| Tensor (per layer × 28) | Bytes |
|---|---|
| `ffn_gate.weight` | 1024 × 3072 = 3,145,728 |
| `ffn_up.weight` | 1024 × 3072 = 3,145,728 |
| `ffn_down.weight` | 3072 × 1024 = 3,145,728 |
| `attn_q.weight` | 1024 × (16×128) = 2,097,152 |
| `attn_k.weight` | 1024 × (8×128) = 1,048,576 |
| `attn_v.weight` | 1024 × (8×128) = 1,048,576 |
| `attn_output.weight` | (16×128) × 1024 = 2,097,152 |
| **per-layer Q8 subtotal** | **~15.7 MB** |
| **× 28 layers** | **~440 MB** |
| `token_embd.weight` | 151,936 × 1024 = ~149 MB |
| `output.weight` if untied | 151,936 × 1024 = ~149 MB |
| Q8 row-scale companions (fp32) | ~1.5 MB |
| RMSNorm scales (fp32 per layer × 2 + final) | ~232 KB |

**Total weight footprint:**
- Tied embedding: ~590 MB
- Untied embedding: ~740 MB

KV cache at ctx_max=4096 (Q8):
- Per layer K: `8 × 128 × 4096 = 4,194,304` bytes (~4 MB)
- Per layer V: same (~4 MB)
- × 28 layers × 2 (K+V): ~234 MB

**Grand total Sprint J budget:** ~825–975 MB.

### C. Heap 25 ceiling probe (temporary edit to test_hvx, run, reverted)

Allocated progressively larger DmaBuffers, held all concurrently:

```
alloc +16 MB OK   (cumulative held = 16 MB)
alloc +32 MB OK   (cumulative held = 48 MB)
alloc +64 MB OK   (cumulative held = 112 MB)
alloc +128 MB OK  (cumulative held = 240 MB)
alloc +256 MB OK  (cumulative held = 496 MB)
alloc +384 MB OK  (cumulative held = 880 MB)
alloc +512 MB OK  (cumulative held = 1392 MB)
alloc +640 MB OK  (cumulative held = 2032 MB)
alloc +768 MB OK  (cumulative held = 2800 MB)
ceiling probe done (cumulative reached = 2800 MB)
```

**Ceiling ≥ 2800 MB.** No `RPCMEM_HEAP_ID_SYSTEM=25` (TRY_MAP_STATIC) allocation refused. **Budget fits with ~3× margin (825 MB / 2800 MB).**

Per `feedback-no-silent-gate-revisions`: probe is verbatim, no shrinking the budget. Sprint J.1 lazy-load fallback is **NOT triggered**. Per-tensor up-front allocation is the v0 path.

### D. ADB free memory

(Confirmed device responsive; S22 Ultra has 12 GB RAM total. 2.8 GB cumulative DmaBuffer hold doesn't pressure the host.)

---

## 1. Architectural decisions

### Naming deviation from mandate

The mandate prescribes a new `SpModel<'sess>` struct. There is **already a `SpModel` struct** defined at `tools/sp_daemon/src/session.rs:17` as `pub struct SpModel(*mut ffi::sp_model);` — the math-core C FFI handle. Adding the mandate's `SpModel<'sess>` would name-collide.

**Sprint J uses `DspModel<'sess>` for the new Hexagon-bridge model type.** The math-core `SpModel` (FFI handle) is unchanged. Field names in `AppState` reflect this: `dsp_model: Option<Arc<DspModel<'static>>>`.

The `KvCache` name does not collide and is used as-spec'd.

### Lifetime + ownership

`DmaBuffer<'sess>` borrows from `FastRpcSession`. To store in `AppState` as `Arc<DspModel<'static>>`, the underlying `FastRpcSession` must be `'static`. Two design choices considered:

| Option | Pros | Cons |
|---|---|---|
| A. Box::leak NEW FastRpcSession exclusively for the loader | Simple. Single startup cost. Two skel handles on one process. | Slight duplication of the FastRPC handle. |
| B. Refactor existing `dsp_session: Option<Mutex<FastRpcSession>>` to `&'static Mutex<FastRpcSession>`; share. | One handle. | Cross-cutting refactor touching Sprint C's /v1/dsp/echo path. |

**Sprint J takes option A** (per-instance separation). The existing `dsp_session` (Sprint C, Option<Mutex<FastRpcSession>>) stays for /v1/dsp/echo. A new `dsp_loader_sess: Option<&'static FastRpcSession>` is added for the DspModel + KvCache. Both open against the same skel `libsp_compute_skel.so`; FastRPC supports multiple handles per process.

### Per-tensor vs per-layer-packed DmaBuffer

Per-tensor: ~16 tensors per layer × 28 + globals ≈ ~460 DmaBuffers (+56 KV = ~516 total). Allocation overhead bounded; Sprint I's DmaBuffer Drop chain proven for individual alloc/free cycles. Accepted for v0.

Per-layer-packed (one DmaBuffer per layer holding all tensors): Sprint J.2 follow-on if startup latency exceeds 30 sec.

### KV cache up-front allocation

`ctx_max = 4096` hardcoded (acceptable for v0). Sprint J.1 makes it configurable from `arch_struct.context_length`. Lazy per-layer growth is Sprint K material.

---

## 2. File-by-file deliverables

| File | Purpose | LOC est |
|---|---|---|
| `tools/sp_daemon/src/dsp_model.rs` | NEW. Extends Sprint I `sp_model_layer.rs` parser to full DspModel + per-tensor load loop. | 180 |
| `tools/sp_daemon/src/kv_cache.rs` | NEW. Per-layer K+V DmaBuffer allocator. | 80 |
| `tools/sp_daemon/src/state.rs` | EDIT. +`dsp_loader_sess`, +`dsp_model`, +`kv_cache` fields (all cfg(android)). | +20 |
| `tools/sp_daemon/src/daemon.rs` | EDIT. `run_inner` adds Box::leak loader session + DspModel::load + KvCache::alloc. | +60 |
| `tools/sp_daemon/src/lib.rs` | EDIT. Add `pub mod dsp_model;` `pub mod kv_cache;` cfg-gated. | +4 |
| `tools/sp_dsp_smoke/src/sp_model_layer.rs` | UNCHANGED. Sprint I parser primitives reused by Sprint J — same module, different consumer. | — |

Sprint J keeps `tools/sp_dsp_smoke/src/sp_model_layer_smoke.rs` (Sprint I's standalone smoke) as-is. Don't delete.

---

## 3. Gate table

| Gate | Definition |
|---|---|
| `T_BUDGET_FITS` | Stage 0C probe ≥ Stage 0B budget. Already PASS (2800 MB ≥ 825-975 MB) — recorded here, not re-run. |
| `T_FULL_LOAD_SUCCESS` | sp_daemon loads all 28 layers + embedding + (output_proj if untied) + norms in < 30 sec wall. Per-layer estimated ~ 15 MB / file-read + 9 alloc-and-memcpy. Target ≤ 30 sec total. |
| `T_KV_CACHE_ALLOC` | KvCache::alloc returns Ok at ctx_max=4096; 56 DmaBuffers allocated (28 K + 28 V). |
| `T_APPSTATE_INTEGRATION` | sp_daemon binary boots on S22U, `/v1/mesh/peers` and `/v1/pouw/ledger` still respond 200/with-body. Sprint C regression. |
| `T_PARTIAL_LOAD_CLEANUP` | Truncate qwen3_rt.sp-model on-device to ~80% bytes; restart sp_daemon; the partial-load error surfaces cleanly; `lsof`-equivalent (`ls /proc/<pid>/fd | wc -l`) shows no fastrpc_shell zombies; previously-allocated DmaBuffers Drop in reverse order via Rust's stack-unwind discipline. |
| `T_LAYER_N_MATMUL` | At layer N=14, run the Sprint I-style single-matmul smoke against `model.dsp_model.layers[14].w_gate` DmaBuffer. Bitwise vs scalar reference. Catches per-layer offset arithmetic bugs that layer-0 alone might mask. |

`M_J_FULL_LOAD` umbrella = all 6 gates PASS.

---

## 4. Commit plan

| # | Stage | Content | Repo |
|---|---|---|---|
| 1 | 1 | This plan | lattice |
| 2 | 2 | `dsp_model.rs` (DspModel + LayerWeights + load loop) | engine |
| 3 | 3 | `kv_cache.rs` (KvCache::alloc) | engine |
| 4 | 4 | `state.rs` + `daemon.rs` + `lib.rs` integration | engine |
| 5 | 5 | On-device verification + verbatim gate output captured as `tools/sp_daemon/sprint_j_run_output.txt` | engine |
| 6 | 6 | Closure | lattice |

Per `feedback-bundled-changeset-root-cause-ambiguity`: parser, KV, AppState in three separate commits. If gate 6 fails, attribution is at-most-one-commit per cause.

---

## 5. Sub-tag taxonomy

- `lat-phase-4-sprint-j-budget-fits` — engine commit at Stage 2 (the load loop pulls the budget; bound by probe at Stage 0).
- `lat-phase-4-sprint-j-full-load` — engine commit at Stage 4 (AppState bound).
- `lat-phase-4-sprint-j-kv-cache` — engine commit at Stage 3.
- `lat-phase-4-sprint-j-appstate` — engine commit at Stage 4.
- `lat-phase-4-sprint-j-partial-cleanup` — engine commit at Stage 5 (verified at on-device test).
- `lat-phase-4-sprint-j-layer-n-bitwise` — engine commit at Stage 5 (layer-14 smoke).
- `lat-phase-4-sprint-j-closed` — umbrella, both repos.

---

## 6. Out of scope (explicit)

- **Forward pass / decode loop** → Sprint K.
- **Fix B zero-copy aliasing** of `.sp-model` mmap into FastRPC SMMU → Sprint J.1 or Phase 4+ follow-on. v0 reads bytes into DmaBuffer (copy), matching Sprint I.
- **Lazy load pattern** → Sprint J.1 if a later sprint needs it. Sprint J Stage 0 probe shows it's NOT needed for v0.
- **Per-layer packed DmaBuffer** → Sprint J.2 if startup latency overshoots 30 sec.
- **CRT split (Trick #1 of manifesto)** → Sprint K.
- **KV cache compression** (VHT2 + Möbius) → Sprint J.3 after baseline established.
- **`ctx_max` configurability** → Sprint J.1. Hardcoded 4096 for v0.
- **Real prefill / activation tensors** → Sprint K.

---

## 7. Risks + responses

**R1: Tensor naming mismatch.** Sprint I confirmed `blk.0.ffn_gate.weight` + scale companion. For layers 1..27 and the other 8 weight types (ffn_up, ffn_down, attn_q/k/v/o), names are inferred from the GGUF convention but not yet probed. **Mitigation:** Stage 2 load loop dumps the first failing tensor name and the first 8 entries of the table so any mismatch is immediately diagnosable. No silent fallback.

**R2: tied_embedding flag misread.** I decoded the flag at offset +40 of arch_struct as 1 (tied). If `output.weight` actually exists as a separate tensor, load it and account for the extra 149 MB. **Mitigation:** load loop checks for `output.weight`; if present, allocate; if absent, treat as tied (alias to embedding for inference but Sprint K's concern, not Sprint J's).

**R3: Stage 0C ceiling probe overshooting practical limit.** The 2800 MB number is "cumulative held during one session"; Sprint J actually loads ~975 MB and keeps it for the daemon's life. Different access pattern. **Mitigation:** if T_FULL_LOAD_SUCCESS fails despite probe success, this is a meaningful finding — surface as Sprint J.1 (lazy load) rather than silent fallback. Probe demonstrates *capacity*, not necessarily *load-time success* under file I/O concurrency.

**R4: Box::leak'd FastRpcSession not Send/Sync.** If FastRpcSession needs a Mutex even at static lifetime, the loader path needs `&'static Mutex<FastRpcSession>` instead. **Mitigation:** Stage 4 compile catches this immediately; design pivot to leaked Mutex is one-line.

**R5: Layer-14 W_gate offset arithmetic bug.** Sprint I tested only layer 0. **Mitigation:** T_LAYER_N_MATMUL specifically validates a mid-model layer. If layer-14 diverges but layer-0 passes, the bug is in `dsp_model.rs`'s offset computation, not the kernel.

**R6: Mid-load FastRPC handle leak.** If T_PARTIAL_LOAD_CLEANUP shows leftover fastrpc_shell zombies, Rust's Drop chain isn't unwinding cleanly. **Mitigation:** explicit `Drop` on `DspModel` that drops layers in reverse; `LayerWeights::Drop` drops individual DmaBuffers in declared order. Sprint B's DmaBuffer Drop discipline is the foundation.

---

## 8. What this sprint does NOT prove

- That the loaded weights are *semantically correct* — only that they bit-match against the same dequantization path used by the scalar reference. End-to-end semantic correctness is Sprint K (decode loop matches L1 reference forward).
- That ctx_max=4096 is the right operational window — it's a v0 hardcode; Sprint J.1 makes it tunable.
- That the model survives a *running* daemon's full duty cycle. T_APPSTATE_INTEGRATION proves boot + basic endpoints; a soak test is Sprint J's bonus, not a gate.
- That per-tensor DmaBuffer is the right perf shape. The 30 sec target is the loose envelope; if startup times come in well below (e.g., 5 sec), per-layer packing optimization is unwarranted. If 25–30 sec, Sprint J.2 is justified.
