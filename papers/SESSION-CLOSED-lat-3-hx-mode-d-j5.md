---
type: session-handoff
title: SESSION-CLOSED — lat-3-hx-mode-d-j5
description: "Sprint: Phase 4 Sprint J.5 — NDK toolchain unblock + AppState wiring"
tags: [session-handoff]
timestamp: 2026-05-29T13:47:51Z
resource: shannon-prime-lattice/papers/SESSION-CLOSED-lat-3-hx-mode-d-j5.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# SESSION-CLOSED — lat-3-hx-mode-d-j5

**Sprint:** Phase 4 Sprint J.5 — NDK toolchain unblock + AppState wiring
**Date:** 2026-05-30
**Commit prefix:** `[lat-3-hx-mode-d-j5]`
**Status:** **CLOSED — 5/5 gates PASS** (4 substantive + graceful-degrade).
**Plan:** `papers/SESSION-PLAN-lat-3-hx-mode-d-j5.md`

J.5 closes the 6th Sprint-J gate (`T_APPSTATE_INTEGRATION`, deferred under
`lat-phase-4-sprint-j-appstate-deferred-to-j5`). `sp_daemon` now cross-compiles
to aarch64-android, loads the Qwen3-0.6B model into cDSP rpcmem at startup, and
surfaces it over HTTP on the S22U — verified end-to-end.

---

## Gate table

| Gate | Result | Evidence |
|------|--------|----------|
| `T_NDK_CROSS_COMPILE` | **PASS** | `cargo build --target aarch64-linux-android --release --bin sp-daemon` links a 5.5 MB aarch64 PIE ELF (NDK r27d, Android 21). |
| `T_APPSTATE_INTEGRATION` | **PASS** | On-device `GET /v1/dsp/model_info` → 200 `{n_layers:28, hidden_size:1024, total_dma_bytes:1503367168, kv_cache_bytes:469762048, load_wall_ms:734}`. |
| `T_ENDPOINT_REGRESSION_ANDROID` | **PASS** | `/v1/mesh/peers` 200; `/v1/dsp/echo` 200 + 1 MB bitwise round-trip (SHA256 in==out); `/v1/dsp/model_info` 200; `/v1/chat` 501; `/v1/pouw/ledger` 501 (all 501 not 404). |
| `T_ENDPOINT_REGRESSION_HOST` | **PASS** | Host daemon starts, loads model via L1 C ABI; `/v1/metrics` 200, `/v1/mesh/peers` 200, `/v1/dsp/echo` 501, `/v1/dsp/model_info` 501. No regression from cfg gating. |
| `T_J5_GRACEFUL_DEGRADE` | **PASS** | cfg fences clean on both targets; no panic on missing C symbols; host `/v1/dsp/*` returns 501 not 404. |

---

## On-device timing (S22U R5CT22445JA)

```
sp-daemon (android) inner starting
§3-HX Sprint C: cDSP echo session open
J.5: model loaded — 28 layers, 1433 MB DMA, 734 ms
J.5: KV cache — 448 MB, 70 ms
listening on 127.0.0.1:8080
```

- Model load 734 ms (Sprint J measured 985 ms; faster here — warm page cache;
  same loader, same 1433.7 MB → 1503367168 B DMA).
- KV cache (ctx=4096) 448 MB in 70 ms.
- **Both cDSP sessions admitted concurrently** (echo skel + compute skel, two
  distinct handles) — the two-session design holds on the unsigned-PD path; the
  pre-deploy concern about same-skel double-open did not materialise (distinct
  skels sidestep it).

---

## Three load-bearing corrections to the mandate framing (spike-established)

The Stage-0 spike (throwaway `[env]`, reverted; full build to first genuine
error) corrected the Sprint C/J blocker framing:

1. **The toolchain blocker was `[env]` CC/CXX/AR + CWD, not PATH.** cargo
   discovers `.cargo/config.toml` by walking **up from the CWD**; building from
   the engine root with `--manifest-path` bypassed `tools/sp_daemon/.cargo/
   config.toml`. Built from within `tools/sp_daemon`, the `[env]` block was
   honoured and `ring` + `esaxx-rs` compiled. The Sprint J "CC alone is
   insufficient — needs PATH" hypothesis was wrong.
2. **bindgen-on-`sp_l1.h` is not a blocker.** `build.rs` early-returns
   `sp_no_link` on android before the bindgen call; no NDK sysroot arg needed.
   The Sprint C closure's "build.rs::bindgen needs NDK sysroot" note is stale
   (predates the build.rs android skip).
3. **The real wall was the daemon's own crate.** `ffi.rs` unconditionally
   `include!`s `sp_bindings.rs` (never generated on android), and `session`/
   `forward`/`sieve`/`mining` reference unlinked C symbols; the QUIC garner
   loop additionally link-pulled `ntt_crt_*`. The mandate's "~50-line config +
   3 Option fields" budget did not anticipate host-gating the whole L1/sieve
   path. Operator-approved **Option A** (host-gate the C path) resolved it.

---

## NDK config diff summary (`feat(j5-ndk)`, engine `92f1a59`)

`tools/sp_daemon/.cargo/config.toml` gains an `[env]` table:
`CC_aarch64_linux_android` / `CXX_aarch64_linux_android` (NDK r27d
clang/clang++ `.cmd`) + `AR_aarch64_linux_android` (`llvm-ar.exe`). New
`tools/sp_daemon/build-android.bat` runs cargo with `tools/sp_daemon` as CWD
(so the config is discovered) and re-exports the vars belt-and-suspenders.
`Cargo.lock` gains `libloading` (android-only dep).

## Host-gate + AppState wiring diff summary

`feat(j5-host-gate)` (engine `15bfdd8`):
- `main.rs`: `ffi`, `session`, `sieve_ffi`, `mining`, `spec`, `tokenizer` are
  `cfg(not(target_os="android"))` mods.
- `state.rs`: host `AppState` unchanged (byte-identical → protects host gate);
  new minimal android `AppState` (`started_at`, `events_tx`, `peer_map`,
  `dsp_session`).
- `routes.rs`: host-only handlers gated; android same-name 501 stubs for
  `chat` + `pouw_ledger`; shared `events`/`mesh_peers`/`dsp_echo` compile
  against both.
- `server.rs`: cfg-split `build_router` (host full; android DSP+mesh surface).
- `daemon.rs`: cfg-split `run_inner`; android variant skips the L1 path and the
  NTT-CRT QUIC garner loop (mesh/peers serves an empty peer_map on a single
  on-device node).

`feat(j5-appstate)` (engine `841160c`):
- `main.rs`: `#[path]`-include `dsp_model.rs` + `kv_cache.rs` from
  `sp_dsp_smoke` (import, not move — loader files + smoke manifest untouched);
  `use crate::dsp_rpc::…` binds the daemon's own `dsp_rpc` (signatures
  identical → no duplicate `FastRpcSession`, no smoke `[lib]` target).
- `state.rs`: `ModelHandle`/`KvCacheHandle` newtypes, `unsafe impl Send+Sync`
  — sound because the model is load-and-read-only in J.5 (DmaBuffer raw rpcmem
  pointers never dereferenced/invoked across threads; `model_info` reads
  metadata only). android `AppState` gains `dsp_model: Option<Arc<ModelHandle>>`
  + `kv_cache: Option<Arc<Mutex<KvCacheHandle>>>`.
- `daemon.rs`: android `run_inner` loads `DspModel` + `KvCache(ctx=4096)` via a
  **separate** `FastRpcSession` leaked to `&'static` (so the ~1.4 GB
  `DmaBuffer<'sess>` borrows live process-long without a self-referential
  struct). The Sprint-C echo `Mutex<FastRpcSession>` path is untouched.

`test(j5)` (engine `cf7837d`): model session uses `libsp_compute_skel.so`
(Sprint J's proven path); host `v1_dsp_model_info` → 501 (uniform `/v1/dsp`
surface).

---

## Per-endpoint regression confirmation

| Endpoint | android | host |
|----------|---------|------|
| `/v1/dsp/model_info` | 200 (real metadata) | 501 (no DSP model) |
| `/v1/dsp/echo` | 200 (1 MB bitwise) | 501 (FFI gated) |
| `/v1/mesh/peers` | 200 (empty peer_map) | 200 |
| `/v1/metrics` | n/a (host-only) | 200 |
| `/v1/chat` | 501 | 200 (SSE stream) |
| `/v1/pouw/ledger` | 501 | 200 (SSE) |

---

## Type-design note (Send/Sync soundness)

`DmaBuffer` wraps a raw rpcmem `*mut u8` → `!Send + !Sync`; `DspModel`/
`KvCache` inherit it. axum `State<Arc<AppState>>` requires `Send + Sync`. The
`unsafe impl` on the daemon-side `ModelHandle`/`KvCacheHandle` newtypes is
**sound for J.5 only** because the model is load-and-read-only. **Sprint K**
(which drives concurrent FastRPC invokes — see engine `6bd01fe`
`sp_dual_dispatch`, `Arc<FastRpcSession>` concurrent invoke) owns the
per-invoke serialization (`Mutex`) that the read-only J.5 surface defers.
`FastRpcSession` itself is auto-`Send+Sync` (raw `extern "C" fn` ptrs + `u64`
handle + `libloading::Library`), so the echo `Mutex<FastRpcSession>` field
needed no wrapper.

---

## Sub-tags

- `lat-phase-4-sprint-j5-ndk-unblock` — `[env]` config + build-android.bat.
- `lat-phase-4-sprint-j5-c-path-host-gated` — cfg-split of the L1/sieve C path
  (the operator-approved architectural decision).
- `lat-phase-4-sprint-j5-appstate-wire` — loader `#[path]` import + model/kv
  fields + Send/Sync handles + `model_info`.
- `lat-phase-4-sprint-j5-endpoint-regression` — on-device + host verification.
- `lat-phase-4-sprint-j5-closed` — umbrella.

---

## Filed follow-on — Phase 2-L3.FG-CROSS-COMPILE (2026-05-30)

Cross-compile the `shannon-prime-system` math-core + sieve C ABI (~17 static
libs) for aarch64-android; flip `build.rs` from `sp_no_link` to real linking on
android. **Unblocks** `/v1/chat` + `/v1/pouw/ledger` on the android binary
(removes their 501s). **Prereq:** J.5 closed. **Est:** 4-6 h (hexagon-clang vs
aarch64-android-clang reconciliation + on-device verify). **Anti-pattern:** do
NOT bundle into J.5 or any K-series sprint — standalone audit surface.

---

## Scope discipline

- Loader (`dsp_model.rs` / `kv_cache.rs`) **not modified** — imported via
  `#[path]`. `sp_dsp_smoke` manifest untouched (no `[lib]` target added).
- Toolchain (Stage 2) and wiring (Stage 3) committed separately per their
  distinct failure modes; host-gate (3a) and appstate (3b) split further so
  "make android compile" and "wire the loader" attribute independently.
- No inference/decode endpoint introduced (Sprint K).
- **No new memory entries.** NDK-on-Windows config-discovery + `[env]` pattern
  is worth capturing; if so, file as a separate follow-on commit after closure
  (not bundled here).
