---
type: session-handoff
title: SESSION CLOSED — lat-3-hx-mode-d-j (Sprint J — Path A1 sp_dsp_smoke-resident)
description: "Date: 2026-05-30"
tags: [session-handoff]
timestamp: 2026-05-29T12:06:10Z
resource: shannon-prime-lattice/papers/SESSION-CLOSED-lat-3-hx-mode-d-j.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# SESSION CLOSED — lat-3-hx-mode-d-j (Sprint J — Path A1 sp_dsp_smoke-resident)
**Date:** 2026-05-30
**Engine commits:** `5b446e9` (SpErr::Other), `3ede795` (dsp_model.rs), `f429f5f` (kv_cache.rs), `78fd394` (bin), `8896ea7` (verbatim output)
**Umbrella tag:** `lat-phase-4-sprint-j-closed`

Sprint J ships **5 of 6 gates PASS** on the Samsung S22 Ultra (R5CT22445JA). All 28 Qwen3-0.6B layers + globals load through the dual-VTCM bridge into per-tensor DmaBuffers; the KV cache allocates at ctx_max=4096; partial-load cleanup is clean; layer-14 W_gate is bitwise-correct against the saturating scalar reference at q=14.

The 6th gate (`T_APPSTATE_INTEGRATION`) is explicitly deferred to **Sprint J.5** (filed below) under the operator-approved Path A1 reframe. Sprint K (manifesto Trick #1, internal CRT split) is unblocked — it consumes the FastRpcSession-resident DmaBuffers Sprint J ships, not sp_daemon's AppState.

---

## Path A1 reframe rationale

The mandate's Stage 4 (AppState integration in `tools/sp_daemon`) hit a pre-existing cross-compile blocker: `sp_daemon`'s mandatory deps (`ring` via rustls/quinn, `esaxx-rs` via tokenizers, plus the pre-existing bindgen-on-sp_l1.h blocker noted in Sprint C closure) need full NDK toolchain plumbing that's out of scope for a "~7 commit" sprint. Setting `CC_aarch64_linux_android` alone is insufficient — each cc-rs-using dep does its own lookup of `aarch64-linux-android-clang` / `clang++` in PATH.

Operator approved pivot:
- Loader code lands in `tools/sp_dsp_smoke/` (which cross-compiles cleanly, per Sprint A–I lineage).
- 5 of 6 substantive gates achievable.
- `T_APPSTATE_INTEGRATION` filed as Sprint J.5 with the cross-compile blocker explicitly cited.
- Sprint K does NOT gate on J.5 — it needs the model in cDSP-coherent DmaBuffers (which Sprint J ships), not in daemon AppState.

Per `feedback-no-silent-gate-revisions`: the deferral is explicit, recorded both in the lat-phase-4-sprint-j-appstate-deferred-to-j5 tag and in this closure body.

---

## Stage 0 pre-flight (verbatim from plan)

| | Result |
|---|---|
| A. Sprint I regression | `sp_model_layer_smoke` 4/4 gates PASS at engine HEAD `7d1e7a9`. No regression. |
| B. Memory budget | Plan estimate 825–975 MB (tied embedding case); **actual 1433.7 MB** (untied embedding + Q8→i16 dequant ×2). |
| C. rpcmem heap 25 cumulative ceiling | **2800 MB** (verbatim progression 16→48→112→240→496→880→1392→2032→2800; no allocation refused). Headroom ~50%. |
| D. ADB to S22U | OK (no host memory pressure). |

---

## Gate table (verbatim)

```
T_BUDGET_FITS         PASS  (pre-recorded; 2800 MB ≥ 1433.7 MB)
T_FULL_LOAD_SUCCESS   PASS  28 layers + globals; 1433.7 MB DMA;
                              wall time 985 ms (target was < 30 sec)
T_KV_CACHE_ALLOC      PASS  56 DmaBuffers (28 K + 28 V);
                              per-layer 8 MB; total 448 MB; 52 ms
T_LAYER_N_MATMUL      PASS  layer 14 W_gate 128×128 via VTCM at q=14;
                              kernel pcyc=9,305,133; hidden[0..4]=[0,0,0,651]
T_PARTIAL_LOAD_CLEANUP PASS nonexistent-file: clean SpErr::Other-wrapped
                              std::io::Error; re-load + drop 1433.7 MB
                              clean, session still usable
T_APPSTATE_INTEGRATION DEFERRED → Sprint J.5
```

---

## Empirical findings (will feed Sprint K planning)

### Untied embedding

The arch_struct +40-offset flag I read as `tied_embedding=1` in the Sprint J plan was a **misinterpretation**. The .sp-model file contains both `token_embd.weight` AND `output.weight` as separate Q8 tensors. The flag at that offset has a different meaning (precision hint, possibly).

Real-world impact: +149 MB to the loader budget vs the tied-case estimate. Still well under the 2.8 GB heap ceiling.

### Q8 → i16 dequant doubles weight footprint

Sprint J loaded ~745 MB of on-disk Q8 data and emitted 1433.7 MB of i16-packed DmaBuffers. The 2× expansion is by-construction (Q8 is 1 byte per element; i16 is 2 bytes; dequantization happens on host). Sprint J.3 could on-DSP-dequant for a 2× heap savings; Sprint J ships the simpler host-side variant.

### Load throughput

985 ms for 1.43 GB = **~1.46 GB/s effective throughput** (file read + Q8 dequant + DmaBuffer alloc + memcpy combined). This is **30× under** the 30-sec budget. Sprint J.2 (per-layer-packed DmaBuffer optimization) is **NOT warranted** at this latency — Sprint J ships the per-tensor pattern.

Possible explanation: the `.sp-model` file was already in page cache from the Sprint J pre-flight + Sprint I runs. A cold-cache run would be slower (file size 754 MB × cold-read = ~3–6 seconds depending on flash speed). For v0 the warm-cache number is the operational reality.

### Layer-14 matmul correctness

`hidden[0..4] = [0, 0, 0, 651]` differs from Sprint I's layer-0 `[0, 520, 2149, 0]` — confirms the per-layer offset arithmetic in `dsp_model.rs::load_q8_weight` is reading the right block at non-zero layers. Bitwise vs the saturating scalar reference; the kernel works on **real intermediate-layer weights**, not just layer 0.

---

## Architectural-discipline notes

- **5 commits in engine + 1 in lattice, ordered per per-commit isolation:**
  - `5b446e9` — `SpErr::Other(String)` in sp_daemon dsp_rpc.rs (one-line; useful regardless of A1 pivot)
  - `3ede795` — `dsp_model.rs` in sp_dsp_smoke (loader module + parser primitives)
  - `f429f5f` — `kv_cache.rs` in sp_dsp_smoke (KvCache::alloc)
  - `78fd394` — `sp_full_load_smoke` bin (consumer; 5 gates inline)
  - `8896ea7` — verbatim on-device output artifact (`sprint_j_run_output.txt`)
- **No production skel changes.** Sprint J reuses the Sprint G compute skel + Sprint H diag method 9 (`sp_compute_ffn_2stage_diag_halide`).
- **No `shannon-prime-system` changes.** Loader is engine-tree only.
- **No new memory entries.** Empirical findings (untied embedding, 2× dequant expansion, 1.46 GB/s throughput) recorded in this closure rather than in memory.
- **Pre-existing standalone bins preserved.** Sprint I's `sp_model_layer_smoke` continues to exist for single-tile debugging; Sprint J's `sp_full_load_smoke` is the new full-model bin.

---

## Sprint J.5 — explicit follow-on filing

**Scope:** unblock `sp_daemon` aarch64-android cross-compile, wire `dsp_model.rs` + `kv_cache.rs` from `sp_dsp_smoke` into `sp_daemon`'s `AppState`, run T_APPSTATE_INTEGRATION on the daemon process.

**Prerequisites:**
- Address the NDK toolchain plumbing for `cc-rs`-using deps (`ring`, `esaxx-rs`, plus any bindgen-needs-sysroot path for `sp_l1.h`).
  - Likely needs `AR_aarch64_linux_android` + `CC_aarch64_linux_android` + `CXX_aarch64_linux_android` + `BINDGEN_EXTRA_CLANG_ARGS=--sysroot=…` set BEFORE `cargo build`.
  - Pre-existing reference: Sprint C closure (lattice `papers/SESSION-CLOSED-lat-3-hx-mode-d-axum.md` — Sprint C surfaced this blocker the first time).
- Estimated: 2-4 hours of NDK env setup + 30 min of `AppState` wiring + 30 min on-device verify.

**Anti-pattern callout:** do NOT bundle J.5 into another sprint. The NDK toolchain work is its own audit surface; bundling makes failure attribution impossible (per `feedback-bundled-changeset-root-cause-ambiguity`).

**Dependency status:**
- Sprint K (manifesto Trick #1, internal CRT split) does NOT block on J.5. Sprint K consumes `DspModel<'sess>` + `KvCache<'sess>` from `sp_dsp_smoke` directly; daemon residence is irrelevant for the manifesto's architectural unlock.
- J.5 is required for production deployment (daemon-resident model + endpoint orchestration). Cohorts running Sprint K can proceed in parallel.

The Sprint J.5 tag set (when that sprint runs):
- `lat-phase-4-sprint-j5-ndk-toolchain` (env-var plumbing)
- `lat-phase-4-sprint-j5-appstate-wired` (AppState fields + run_inner)
- `lat-phase-4-sprint-j5-on-device` (T_APPSTATE_INTEGRATION)
- `lat-phase-4-sprint-j5-closed`

---

## Sub-tags (this sprint)

| Sub-tag | Engine commit | Status |
|---|---|---|
| `lat-phase-4-sprint-j-budget-fits` | `8896ea7` | PASS (2800 MB ceiling ≥ 1433.7 MB load) |
| `lat-phase-4-sprint-j-full-load` | `8896ea7` | PASS (985 ms / 1.43 GB / 28 layers) |
| `lat-phase-4-sprint-j-kv-cache` | `8896ea7` | PASS (56 DmaBuffers / 448 MB / 52 ms) |
| `lat-phase-4-sprint-j-partial-cleanup` | `8896ea7` | PASS (clean Err + re-load cycle) |
| `lat-phase-4-sprint-j-layer-n-bitwise` | `8896ea7` | PASS (layer 14 bitwise via VTCM) |
| `lat-phase-4-sprint-j-appstate-deferred-to-j5` | `8896ea7` | DEFERRED (explicit; J.5 filed above) |
| `lat-phase-4-sprint-j-closed` | `8896ea7` | UMBRELLA (5 substantive gates PASS) |

Lattice tags mirror the engine SHAs at the closure-commit head.

---

## What this sprint does NOT prove

- **End-to-end forward pass correctness.** Sprint J proves the *load + storage* substrate. The decode loop (Sprint K) is the next correctness gate.
- **Cold-cache load time.** The 985 ms figure benefits from page-cache residence after Sprint I + pre-flight runs. A first-time-after-reboot load is unmeasured.
- **Sustained operation under inference load.** Sprint J's 100-iter style leak test was inherited from Sprint I; Sprint J doesn't add a separate soak gate. KV cache + model held simultaneously across the run is the main soak data point.
- **Daemon-resident model lifecycle.** That's exactly what J.5 will verify.
