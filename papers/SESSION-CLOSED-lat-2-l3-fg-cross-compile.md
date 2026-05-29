# SESSION-CLOSED — lat-2-l3-fg-cross-compile

**Sprint:** Phase 2-L3.FG-CROSS-COMPILE — math-core C ABI for aarch64-android
**Date:** 2026-05-30
**Commit prefix:** `[lat-2-l3-fg-cc]`
**Status:** **CLOSED — 5/5 gates PASS.**
**Plan:** `papers/SESSION-PLAN-lat-2-l3-fg-cross-compile.md`

The android `sp_daemon` is now feature-complete: `/v1/chat` and
`/v1/pouw/ledger` run for real on-device (the J.5 501s are gone), verified
bit-stable against the host on the S22U.

---

## Gate table

| Gate | Result | Evidence |
|------|--------|----------|
| `T_C_CROSSCOMPILE` | **PASS** | 17 `libsp_*.a` (elf64-littleaarch64) from `build-android-libs.bat`. |
| `T_DAEMON_LINK_ANDROID` | **PASS** | `sp_no_link` off; ELF **5.5 MB (J.5) → 9.5 MB** (math-core C linked); no linker errors. |
| `T_CHAT_ENDPOINT` | **PASS** (reframed) | On-device POST `/v1/chat` → 200 SSE; 12-token greedy continuation **identical to host** (`" a famous song by the band of the same name, and"`). |
| `T_LEDGER_ENDPOINT` | **PASS** | `/v1/pouw/ledger` 200 SSE; `/v1/receipts` shows **385 receipts** minted via the cross-compiled `sp_sieve`. |
| `T_NO_REGRESSION` | **PASS** | `/v1/dsp/echo` 1 MB bitwise still PASS; `model_info` 200; `mesh/peers` 200; host build compiles clean + host chat identical; J.5 android gates intact; `sp_dsp_smoke`/K untouched by this sprint. |

---

## Library inventory + cross-compile result

All 17 build.rs `MODULES` cross-compiled in **one** CMake pass via the NDK r27d
`android.toolchain.cmake` (arm64-v8a, API 21, Ninja): forward, forward_dispatch,
forward_kernels, model, arena, frobenius, poly_ring, ntt_crt, vht2, weight_dtype,
gguf, io_format, io_hash, session, sieve, kste, ok_arith. ~1 MB of archives.

**Platform deltas: zero in the math-core.** The `core/` is x86-free by design
(`forward_kernels.c:3`), so no NEON port — confirming the Stage-0 GO and the
plan's "build all 17" decision (no failure-attribution boundaries → a single
Stage-2 commit, not per-group).

**One toolchain delta (build-side, not code):** bindgen on android failed with
`stddef.h not found` — `sp_l1.h`'s `<stdint.h>` pulls the compiler-builtin
`stddef.h` from the NDK clang **resource** dir, which the host libclang doesn't
know. Fixed by adding `-isystem <NDK>/lib/clang/18/include` alongside
`--target`/`--sysroot` in `BINDGEN_EXTRA_CLANG_ARGS_aarch64-linux-android`.
(Caught by the Stage-0 bindgen spike before the re-unify — cheap.)

---

## On-device numbers (S22U R5CT22445JA)

```
arch: vocab=151936 n_layers=28 hidden=1024 ; L1 FFI OK session_position=0
tokenizer built: arch_id=2 eos_ids=[151643, 151645]
L3.FG: DSP model loaded — 28 layers, 1433 MB DMA, 1556 ms
L3.FG: KV cache — 448 MB, 311 ms ; listening on 127.0.0.1:8080
```
- **Dual-model footprint held:** CPU mmap (754 MB, chat) + DSP rpcmem (1433 MB,
  model_info/echo) ≈ 2.2 GB — no OOM/thermal trip during the run.
- The cross-compiled **L1 forward runs real inference on the S22U CPU** — this
  is the headline (`L1 FFI OK` + a coherent 12-token continuation).

### T_CHAT_ENDPOINT reframe — outcome

The mandate's "bitwise-equal to host" was reframed (plan §6) to **top-1
greedy-argmax token-sequence equality**, per `reference-ecpu2-qknorm-precision-
gate` (host x86 libm vs android aarch64 libm diverge in transcendental ULPs).
Outcome: the 12-token sequence was **byte-identical** host↔android — the libm
ULP differences never flipped an argmax decision, exactly the reframe's
expectation. (Bitwise *logit* equality was not asserted and is not required;
the discrete top-1 invariant the Lattice depends on holds.)

---

## ⚠ Commit-isolation collision with the parallel K-beta agent

L3.FG and Sprint K v0.beta ran against the **same engine working tree**
(not separate worktrees). The K-beta agent's `git add` swept my **uncommitted
Stage-3 files** into its commit:

> `41963ac [lat-3-hx-mode-k-beta] Stage 2.5a scalar Barrett primitives`

That commit contains **both** lanes. File-level attribution:
- **L3.FG Stage 3 (mine):** `.cargo/config.toml`, `build.rs`, `src/{main,state,
  daemon,routes,server}.rs`.
- **K v0.beta (theirs):** `sp_compute_skel/*`, `sp_dsp_smoke/{Cargo.toml,
  src/sp_barrett_oracle*.rs, sprint_k_beta_2_5a_run_output.txt}`.

`41963ac` is already on `origin/main`, so it was **not** rewritten (no
force-push of shared history; unbundling would also touch K-beta's lane, which
this sprint must not). The code is correct and live; only the commit boundary
is impure.

**Provenance (tested ≡ committed):** the device binary was built from the
working tree; no edits were made between that build and the commit attempt;
K-beta's `git add` snapshots files into history without mutating the working
tree; `git diff` for my 7 files was then empty (working tree == HEAD ==
`41963ac`). So **tested binary ≡ working tree ≡ committed source**. The
empirical clincher: the daemon behaved exactly as the re-unify designed (CPU
chat coherent, DSP fields populated) — impossible if K-beta had also edited
those files. Post-closure `git status` confirms nothing of L3.FG's is left
uncommitted in the engine tree. **Recommendation for future parallel cohorts: give each agent its
own git worktree** so concurrent `git add` cannot cross-contaminate. L3.FG
Stage 2 (`c01662b`) and this closure are cleanly isolated.

---

## Sub-tags

- `lat-phase-2-l3-fg-cross-compile-libs` — 17 libs cross-compile (engine `c01662b`).
- `lat-phase-2-l3-fg-cross-compile-link` — sp_no_link flip + bindgen sysroot (in `41963ac`, see collision).
- `lat-phase-2-l3-fg-cross-compile-chat` — chat live on android, top-1 == host.
- `lat-phase-2-l3-fg-cross-compile-ledger` — 385 receipts via cross-compiled sieve.
- `lat-phase-2-l3-fg-cross-compile-no-regression` — echo bitwise + host clean.
- `lat-phase-2-l3-fg-cross-compile-closed` — umbrella.

---

## Notes

- **No new memory entries.** The NDK-config-per-crate quirk's "second occurrence"
  did **not** trigger here — L3.FG added a *CMake toolchain invocation* +
  `BINDGEN_EXTRA_CLANG_ARGS` to the **same** `sp_daemon` crate, not a new
  per-crate `.cargo/config.toml`. The capture trigger still awaits a genuinely
  new android-targeting crate.
- **Stage 4 had no engine code delta** (all wiring landed in Stage 3); the
  on-device evidence is recorded here rather than as a separate engine artifact
  commit — deliberately, to avoid another shared-working-tree collision.
- **What this unlocks:** android daemon is production-feature-complete (chat +
  ledger + mesh + DSP). Combined with K v0.beta's Barrett payload, the next
  checkpoint is the two-node on-phone integration smoke.
