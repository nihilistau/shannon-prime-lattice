---
type: session-handoff
title: SESSION-PLAN — lat-3-hx-mode-d-j5
description: "Sprint: Phase 4 Sprint J.5 — NDK toolchain unblock + AppState wiring"
tags: [session-handoff]
timestamp: 2026-05-29T13:13:35Z
resource: shannon-prime-lattice/papers/SESSION-PLAN-lat-3-hx-mode-d-j5.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# SESSION-PLAN — lat-3-hx-mode-d-j5

**Sprint:** Phase 4 Sprint J.5 — NDK toolchain unblock + AppState wiring
**Date filed:** 2026-05-30
**Commit prefix:** `[lat-3-hx-mode-d-j5]`
**Predecessor:** Sprint J Path A1 (`lat-phase-4-sprint-j-closed`), gate 6
(`T_APPSTATE_INTEGRATION`) deferred here.

J.5 is production-deployment infrastructure: make `sp_daemon` build for
aarch64-android, wire the Sprint J `sp_dsp_smoke` loader (`dsp_model.rs` +
`kv_cache.rs`) into the daemon's `AppState`, run the integration gate on the
S22U. **No new architectural work. No loader refactor. No manifesto scope.**

---

## 1. Pre-flight results (Stage 0)

**Sprint J state confirmed.** `git tag --list "lat-phase-4-sprint-j-*"` → 7
sub-tags including `appstate-deferred-to-j5` and the `closed` umbrella.
`tools/sp_dsp_smoke` cross-compiles clean; full Qwen3-0.6B loads on S22U
(1433.7 MB DMA in 985 ms); J gates green.

**NDK present — do NOT stop.** `D:\Files\Android\android-ndk-r27d`
(r27d), `toolchains\llvm\prebuilt\windows-x86_64\bin\` carries
`aarch64-linux-android{21..35}-clang[.cmd]` + `clang++[.cmd]`, `llvm-ar.exe`,
and a populated `sysroot\`. `rustup target list --installed` includes
`aarch64-linux-android`.

**Continuity citation.** The cross-compile blocker was first surfaced in
Sprint C (`papers/SESSION-CLOSED-lat-3-hx-mode-d-axum.md`) and restated in the
Sprint J closure (`SESSION-CLOSED-lat-3-hx-mode-d-j.md` §14, §96-102), which
attributed it to `ring`/`esaxx-rs` cc-rs deps + a presumed bindgen-on-`sp_l1.h`
need, and hypothesised "setting `CC_aarch64_linux_android` alone is
insufficient — each cc-rs dep looks up `aarch64-linux-android-clang` in PATH."

### Empirical findings (spike — three load-bearing corrections)

A throwaway `[env]` block was added to `tools/sp_daemon/.cargo/config.toml` and
`cargo build --target aarch64-linux-android --release --bin sp-daemon` was run
**from within `tools/sp_daemon/`** (config reverted after). Results:

1. **The toolchain fix is `[env]` CC/CXX/AR + correct CWD — not PATH.** Built
   from the engine root with `--manifest-path`, cargo never reads
   `tools/sp_daemon/.cargo/config.toml` (config discovery walks **up from
   CWD**, and the config sits in a *child* dir). Built from *within*
   `tools/sp_daemon/`, the `[env]` block was honoured and `ring` + `esaxx-rs`
   compiled cleanly. The Sprint J "CC alone is insufficient, needs PATH"
   hypothesis was wrong — the real causes were config-discovery CWD + needing
   `CXX_*`/`AR_*` alongside `CC_*`. *(Synthesis-respecting reframe: the J
   author correctly identified the blocker family — cc-rs deps — and the
   needed env vars; only the "PATH lookup" mechanism and the CWD subtlety
   were off.)*

2. **bindgen-on-`sp_l1.h` is NOT a blocker.** `tools/sp_daemon/build.rs`
   already early-returns `cargo:rustc-cfg=sp_no_link` on
   `CARGO_CFG_TARGET_OS == "android"` *before* the bindgen call. No
   `BINDGEN_EXTRA_CLANG_ARGS=--sysroot=…` is required. *(The Sprint C/J note
   predates this build.rs android skip.)*

3. **The daemon's own crate has never compiled for android — second wall.**
   With the toolchain fixed, the build advanced past every dep and died in the
   daemon's own source:
   ```
   error: couldn't read .../out/sp_bindings.rs: The system cannot find the file
     --> src\ffi.rs:10:1  include!(concat!(env!("OUT_DIR"), "/sp_bindings.rs"));
   ```
   `ffi.rs` unconditionally `include!`s bindings that build.rs never generates
   on android; `session.rs`, `daemon.rs::run_inner`, `state.rs`, `sieve_ffi.rs`
   and `mining.rs` all reference C-ABI symbols that `sp_no_link` leaves
   unlinked. build.rs comments confirm: *"type-check passes; link is Phase
   2-L3.FG scope."* The mandate's "~50-line config + 3 Option fields" budget
   did not anticipate that the daemon's whole L1/sieve C path must be
   host-gated for the android binary to compile or link.

---

## 2. Toolchain plumbing decisions

**`tools/sp_daemon/.cargo/config.toml`** — add an `[env]` table alongside the
existing `[target.aarch64-linux-android]` linker/ar:

```toml
[env]
CC_aarch64_linux_android  = "D:\\Files\\Android\\android-ndk-r27d\\…\\bin\\aarch64-linux-android21-clang.cmd"
CXX_aarch64_linux_android = "D:\\Files\\Android\\android-ndk-r27d\\…\\bin\\aarch64-linux-android21-clang++.cmd"
AR_aarch64_linux_android  = "D:\\Files\\Android\\android-ndk-r27d\\…\\bin\\llvm-ar.exe"
```

- `CC_*` satisfies `ring`; `CXX_*` satisfies `esaxx-rs` (via `tokenizers`);
  `AR_*` provides the archiver. `.cmd` wrappers are invoked directly (no PATH
  reliance).
- **bindgen:** none — build.rs skips it on android. No sysroot arg needed.
- **No feature-gating of `ring`/`esaxx`** is required; the `[env]` fix makes
  them build as-is.

**`tools/sp_daemon/build-android.bat`** (Windows host helper) — its load-bearing
job is to run cargo with `tools/sp_daemon` as CWD so the `.cargo/config.toml`
is discovered, then invoke
`cargo build --target aarch64-linux-android --release --bin sp-daemon`.
Belt-and-suspenders: also export the three env vars before the call so a
build launched from a different CWD still works.

**`build.rs`** — no change needed for the toolchain (already android-aware).

---

## 3. AppState wiring scope — host-gate the C path (operator-approved Option A)

The android daemon **host-gates** the unlinkable C-ABI path rather than
cross-compiling the math-core C (that is the separately-filed Phase 2-L3.FG
work, §6). Per-file:

- **`state.rs`** — split `AppState` by cfg:
  - `#[cfg(not(target_os="android"))]` keeps the existing C-backed fields
    (`model: SpModel`, `session`, `draft_*`, `vocab_size`, `tokenizer`, the
    mining `receipt_store`/`node_signing_key` stay shared).
  - `#[cfg(target_os="android")]` adds:
    `dsp_model: Option<Arc<DspModel<'static>>>`,
    `kv_cache: Option<Arc<Mutex<KvCache<'static>>>>`,
    reusing the existing `#[cfg(android)] dsp_session` field.
  - **Note the literal field type differs from the mandate's
    `Option<Arc<SpModel>>`:** the loader yields `DspModel<'sess>` /
    `KvCache<'sess>` (all ~1.4 GB of weights live in `DmaBuffer<'sess>` that
    borrow the `FastRpcSession`). Storing session + model + kv in one struct
    is self-referential. Resolution that touches **zero** loader code:
    `Box::leak` the `FastRpcSession` to `&'static` at startup (it lives for the
    whole process — freed at exit anyway), giving `DspModel<'static>` /
    `KvCache<'static>` as owned, storable values.
  - **Thread-safety note:** the `Mutex<FastRpcSession>` existed because
    FastRPC per-handle calls are single-thread. Leaking to `&'static`
    *relocates*, does not remove, that constraint. J.5 does **zero** FastRPC
    invokes (load-and-hold only; `model_info` reads `header`/`total_dma_bytes`
    + `kv_cache.total_bytes()`). Per-invoke serialization is **Sprint K's** to
    add, recorded here so K does not inherit a silent data race.

- **`daemon.rs`** — split `run_inner`:
  - `#[cfg(not(target_os="android"))]` retains today's host path (SpModel::load
    → session → tokenizer → mining → QUIC).
  - `#[cfg(target_os="android")]` `run_inner` variant:
    `FastRpcSession::new(SKEL_URI)` → `Box::leak` → `DspModel::load` →
    `KvCache::alloc(ctx_max=4096)` → build the android `AppState` → serve a
    router with `/v1/mesh/peers` (pure-Rust quinn), `/v1/dsp/echo`,
    `/v1/dsp/model_info`; the C-backed routes return 501. Graceful degrade: if
    `FastRpcSession::new` fails, all three model fields stay `None` and
    `model_info` returns 501 (no panic).

- **`ffi.rs` / `session.rs` / `sieve_ffi.rs` / `mining.rs`** — `#[cfg(not(
  target_os="android"))]` the modules (and their `mod` decls in `main.rs` /
  `lib.rs`) so the `include!(sp_bindings.rs)` and unlinked C symbols leave the
  android build entirely.

- **Loader import path — `#[path]` include, no smoke `[lib]` target.**
  `sp_dsp_smoke` is bin-only (no `[lib]`), so `use sp_dsp_smoke::dsp_model` is
  impossible without adding a lib target to the smoke crate. Chosen instead
  (anti-pattern-compliant — loader files untouched, smoke manifest untouched):
  ```rust
  #[cfg(target_os="android")] #[path="../../sp_dsp_smoke/src/dsp_model.rs"] mod dsp_model;
  #[cfg(target_os="android")] #[path="../../sp_dsp_smoke/src/kv_cache.rs"]  mod kv_cache;
  ```
  Inside those files `use crate::dsp_rpc::{…}` resolves to the **daemon's own**
  `dsp_rpc.rs` (signatures verified identical: `FastRpcSession::new`,
  `alloc_dma`, `DmaBuffer<'sess>`, `SpErr`), so no duplicate `FastRpcSession`
  type and no second crate. Tech-debt noted: the cross-tree `#[path]` is a
  marker for the loader's eventual real home (a shared crate), out of J.5 scope.

---

## 4. Test gates (operator-amended taxonomy)

| Gate | Scope | Pass criterion |
|------|-------|----------------|
| `T_NDK_CROSS_COMPILE` | host build cmd | `sp_daemon` Rust-only path cross-compiles to aarch64-linux-android clean (zero errors; warnings OK). |
| `T_APPSTATE_INTEGRATION` | S22U | daemon starts via the cfg-gated android startup; loads model via the Sprint J `sp_dsp_smoke` loader; `model_info` surfaces `n_layers` + total DmaBuffer footprint. |
| `T_ENDPOINT_REGRESSION_ANDROID` | S22U | `/v1/mesh/peers` + `/v1/dsp/echo` + `/v1/dsp/model_info` respond correctly. `/v1/pouw/ledger` + `/v1/chat` → 501 (C ABI not yet cross-compiled). |
| `T_ENDPOINT_REGRESSION_HOST` | Windows host | host build still passes all 5 endpoints **including** the C-backed `/v1/pouw/ledger` + `/v1/chat` — no host regression from the cfg gating. |
| `T_J5_GRACEFUL_DEGRADE` | host + android | cfg fences clean; no panic on missing C symbols; android `model_info` returns 501 when the loader is unavailable. |

---

## 5. Sub-tag taxonomy

- `lat-phase-4-sprint-j5-ndk-unblock` — `[env]` config + build-android.bat.
- `lat-phase-4-sprint-j5-c-path-host-gated` — cfg-split of ffi/session/sieve/
  mining + android `AppState`/`run_inner` (architectural decision, auditable).
- `lat-phase-4-sprint-j5-appstate-wire` — loader `#[path]` import + model/kv
  fields + `model_info` endpoint.
- `lat-phase-4-sprint-j5-endpoint-regression` — on-device + host gate runs.
- `lat-phase-4-sprint-j5-closed` — umbrella (after ≥3 substantive tags).

---

## 6. Out of scope

- **Loader refactor.** `dsp_model.rs` / `kv_cache.rs` stay in `sp_dsp_smoke`,
  imported by `#[path]`, never edited.
- **Forward pass / decode loop / tokenizer / sampler** — Sprint K + later
  Phase 4 follow-ons.
- **Manifesto Trick #1 CRT split** — Sprint K, runs in parallel, does not
  touch J.5.

### Filed follow-on — Phase 2-L3.FG-CROSS-COMPILE (2026-05-30)

- **Scope:** cross-compile the `shannon-prime-system` math-core + sieve C ABI
  (~17 static libs) for aarch64-linux-android; flip build.rs from `sp_no_link`
  to real linking on android.
- **Unblocks:** `/v1/chat` + `/v1/pouw/ledger` on the android binary (removes
  their 501s).
- **Prerequisites:** J.5 closed (NDK toolchain known-good for Rust deps; the C
  path follows a similar plumbing pattern but with hexagon-clang-vs-
  aarch64-android-clang reconciliation, and possible `sp_forward.c` divergence
  points for the android target).
- **Estimated:** 4-6 h (toolchain reconciliation + on-device verify of chat +
  ledger).
- **Anti-pattern:** do NOT bundle into J.5 or any K-series sprint. Standalone
  audit surface (per `feedback-bundled-changeset-root-cause-ambiguity`).

---

## Execution order (commit isolation — distinct failure modes)

1. **Stage 2** (engine) `feat(j5-ndk)`: `.cargo/config.toml` `[env]` +
   `build-android.bat`. Verify Rust-only deps cross-compile (build advances to
   the daemon-source wall).
2. **Stage 3a** (engine) `feat(j5-host-gate)`: cfg-split ffi/session/sieve/
   mining + module decls → daemon's android build compiles.
3. **Stage 3b** (engine) `feat(j5-appstate)`: `#[path]` loader import + android
   `run_inner` + `AppState` model/kv fields + `model_info` route.
4. **Stage 4** (engine) `test(j5)`: ADB on-device verification + host
   regression.
5. **Stage 5** (lattice) closure note + sub-tags.

**Plan pushed BEFORE any Stage 2 code.** No new memory entries this sprint
(NDK-on-Windows patterns, if worth capturing, file as a separate follow-on
commit after closure).
