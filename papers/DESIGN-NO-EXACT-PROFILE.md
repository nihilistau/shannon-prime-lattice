---
type: design
title: "DESIGN — the --no-exact (standard-FP) build profile + the exact-vs-FP A/B (what byte-exactness actually buys)"
description: "Scoping for a standard floating-point sibling of the served system: NOT a fork but a cargo feature + ~10 #ifndef guards, because the FP path already exists at runtime (every byte-exact CUDA kernel is an if(sp_byteexact_attn())/else branch, default-off) and the served recall selector is already FP cosine. Maps the exact-arithmetic surface (what compiles out vs stays), the profile gating plan, and an A/B harness that can run TODAY with zero new code (flag flip) plus a separable ~1-day portability build. Records honestly where exactness is load-bearing (cross-machine determinism, auditability/content-addressing for SWARM/PoUW, integer VSA memory-at-scale) and where it is inert (faithfulness, output quality, compression)."
tags: [design, byte-exact, fp, build-profile, cargo-feature, ab-test, determinism, auditability, portability, honest-negative, anti-rebuild]
timestamp: 2026-07-04T00:00:00Z
resource: shannon-prime-lattice/papers/DESIGN-NO-EXACT-PROFILE.md
sp_status: "PARKED (operator decision 2026-07-04) — A/B answered the question (G-NOEXACT-OBEY-AB: FP ties faithfulness, 1.06x faster, equal same-box determinism) + FP-profile FOUNDATION landed (engine e58150d, default build GREEN). FP-link completion (G-NOEXACT-BUILD: quic_shard NTT-recombine gating) DEFERRED — value is portability-only, no urgency; revisit when a non-Windows/non-cl.exe target actually needs it."
sp_gate: "G-NOEXACT-OBEY-AB GREEN (flag-flip A/B, no build): exact 54/61 == FP 54/61 obey (identical misses), FP 1.06x faster, DET 6/6==6/6 same-box. Build-profile gates still pending: G-NOEXACT-PARITY (FP binary reproduces obey when exact code physically gone) + G-NOEXACT-BUILD (cl.exe, no __int128, smaller binary)."
sp_commit: "engine driver _faithful_corpus/noexact_ab.py; receipt tests/fixtures/chat_fullstack/G-NOEXACT-OBEY-AB.log"
sp_repro: "serve run_console_faithful.bat then python _faithful_corpus/noexact_ab.py (flips per-request byteexact true/false on one live daemon). Recon: SP_BYTEEXACT gating in src/backends/cuda/cuda_forward.cu (10 if/else regions), tools/sp_daemon/build.rs MODULES, recall.rs (FP cosine), __int128 usage across lib/shannon-prime-system/core/. Reuses: G-BYTEEXACT-FORWARD-12B (69c0588), G-ONECONFIG-LIVE."
---

# DESIGN — the `--no-exact` (standard-FP) build profile

## 0. The question, answered up front

*"How plausible is a standard-FP sibling that takes everything except the byte-exact ABI, and
how much does being byte-exact actually buy us?"*

**Plausibility: very high — because the FP system already exists.** Byte-exactness is not woven
through the reasoning path; it is an **opt-in ABI overlay** with a runtime flag and a physically
separable substrate. Two recon facts settle it:

1. **Every byte-exact CUDA kernel is already an `if/else` branch with an FP else, default-off.**
   In `src/backends/cuda/cuda_forward.cu` the attention decode reads
   `if (sp_byteexact_attn()) k_attn_decode_win_bx<<<…>>>  else  k_attn_decode_win<<<…>>>`, and the
   nonlinear islands (RMSNorm/GELU/RoPE/softcap) are gated the same way by `d_bx_flag`
   (set once from `SP_BYTEEXACT`). With `SP_BYTEEXACT` unset the served forward is **already pure FP**.
2. **The served faithfulness path is already FP.** The recall selector (`recall.rs`) scores L5
   **cosine** over `f32` gemma4 activations (`l5_query_embed`, `cosine_similarity` of 512-vectors).
   No integer ring is called in the hot decode. Episode recall is `replay_dir` (KV/text replay into
   the CUDA forward), not a call into the integer memory ring.

So "everything except the byte-exact ABI" describes, to first order, **what already runs when the
flag is off.** The sibling is a *build profile that makes that permanent and removes the exact code*,
not a new codebase.

> ⚠ One nuance that cuts in favour of doing this: the served chat path currently defaults
> `byteexact` **ON** (`routes.rs:483`, `req.byteexact.unwrap_or(true)`), and backlog **#47** records
> that default-on byteexact *echoes on some short prompts where float is the correct answer*. That is
> the cleanest existing evidence that exactness is not buying output quality — in places it costs it.

## 1. The exact-arithmetic surface (what a FP profile removes vs keeps)

Recon: `lib/shannon-prime-system/core/` C modules, `tools/sp_daemon/build.rs` `MODULES`,
`src/backends/cuda/cuda_forward.cu`, and `__int128` usage.

### 1a. Removed by `--no-exact` (the exact substrate)

| Unit | Where | LOC | Role | In the served hot path? |
|---|---|---|---|---|
| Byte-exact islands (RMSNorm/GELU/RoPE/softcap) | `cuda_forward.cu` `#…_bx` kernels + `d_bx_flag` | ~10 gated regions | exact-integer nonlinear islands | **No** — `else` FP branch runs by default |
| Byte-exact attention (dual-prime CRT-NTT on device) | `cuda_forward.cu` `k_attn_decode_win_bx`, `sp_byteexact_attn()` | (same regions) | exact-integer attention | **No** — FP `k_attn_decode_win` default |
| `exact_islands` (host/CPU ref) | `core/exact_islands/` | 223 | CPU exact-island reference (`__int128`) | No |
| `ntt_crt` | `core/ntt_crt/` | 803 | dual-prime CRT-NTT | Linked, **dormant** at serve |
| `poly_ring` | `core/poly_ring/` | 1917 | negacyclic ring / Bluestein | Linked, **dormant** at serve |
| `ok_arith` | `core/ok_arith/` | 544 | O_K lattice arithmetic | Linked, **dormant** at serve |
| `frobenius` | `core/frobenius/` | 671 | Frobenius π^k episode store | Linked, **dormant** at serve |
| `ntt_ffi.rs` / `ntt_hex_dispatch.rs` | `tools/sp_daemon/src/` | — | Rust FFI to the ring (smoke tests) | **Dormant** in routes |

The four ring modules (`ntt_crt`+`poly_ring`+`ok_arith`+`frobenius` ≈ **3935 C-lines**) are compiled
and **linked** into the served daemon via `build.rs MODULES`, but `routes.rs`/`recall.rs` do **not
call them per turn** — they are the substrate for the **offline** memory organism (XBAR/Ring-3/
Frobenius: `G-R3-BIND`, `G-XBAR-ORGANISM`), not the daily driver. Dropping them removes dead weight
from the served binary and only removes capability from the *offline organism research track*.

### 1b. The `__int128` / toolchain payload

`__int128` (which forces **clang-cl**, not `cl.exe` — a recurring clean-build-RED per
`BUILD-ENV-TOOLCHAIN.md`) appears only in the exact substrate: `exact_islands.c`,
`ntt_crt/*` (ref/test/fixture + `ntt_ref_int128.c`), `poly_ring_test.c`, and the byte-exact regions
of `cuda_forward.cu`. **Compiling the exact code out is what lets the FP profile build with plain
`cl.exe`** — removing the single most persistent from-clean build hazard in the project.

### 1c. Kept (identical in both profiles)

The whole FP forward — `forward`/`forward_dispatch`/`forward_kernels`/`model`/`arena`/`gguf`/
`io_format`/`io_hash`/`weight_dtype`/`session`/tokenizer — plus the served spine, L5 **FP** cosine
recall, attr-gate, decline, telemetry, personality, and the CUDA FP kernels
(`k_attn_decode_win`, the q4b GEMV lanes). None of this touches the exact substrate.

## 2. The profile (cargo feature + `#ifndef`, NOT a fork)

A single default-on cargo feature `exact` (or its inverse `--no-exact`), threaded to C/CUDA via a
compile define `SP_NO_EXACT`:

1. **`build.rs`** — under `--no-exact`, drop `ntt_crt`/`poly_ring`/`ok_arith`/`frobenius` from
   `MODULES`; exclude `ntt_ffi.rs`/`ntt_hex_dispatch.rs` from the crate (`#[cfg(feature = "exact")]`);
   pass `-DSP_NO_EXACT` to the `nvcc`/cc invocations.
2. **`cuda_forward.cu`** — wrap the ~10 byte-exact regions (the `_bx` kernels, `sp_byteexact_attn`,
   the `d_bx_flag` island routing, and `gemma4_kv_byteexact_set`) in `#ifndef SP_NO_EXACT`. When
   defined: `sp_byteexact_attn()` becomes a constant `return 0;` and `gemma4_kv_byteexact_set()` a
   no-op returning success. The FP `else` branches — already present — become the only path. This
   also removes the on-device `__int128`.
3. **`routes.rs`** — under `--no-exact`, the `byteexact` request field is accepted-and-ignored
   (always false) so the served API is unchanged; the daily-driver default (#47) is moot because FP
   is the only path.
4. **Memory organism** — `--no-exact` builds **without** the integer VSA ring. The served recall is
   unaffected (already FP cosine); only the offline XBAR/Ring-3/Frobenius organism is unavailable in
   this profile. This is the **one genuine fork-forcing choice**, and it is a clean drop, not a port.

Net surface: **one cargo feature, ~10 `#ifndef` guards, a `build.rs` `cfg`, two dropped `.rs`
files.** No behavioural change to the daily driver, which already defaults FP.

## 3. What byte-exactness actually buys (honest ledger)

| Axis | Exact | FP | Verdict |
|---|---|---|---|
| **Cross-machine determinism / reproducibility** | bit-identical, run-to-run + machine-to-machine | non-associative; cuBLAS/atomics/GPU-model → divergence (the whole N2 campaign) | **exact wins — the real prize** |
| **Auditability + content-addressing (SWARM / PoUW)** | stable bytes → hashable, signable, replicable, third-party-verifiable | same input → different bytes → content-addressing breaks | **exact wins — FP structurally cannot** |
| **Integer VSA memory-at-scale** | Ring-3 bind reduction-order-immune (M byte-identical vs float 4.44e-15 drift); retention **1.000 @ N=32** | drift accumulates; retention **0.969 @ N=32** (~3% shed) | **exact wins — offline organism only** |
| **Faithfulness / obedience** | — | — | **tie — 0 benefit measured** (hard-foreign kill-test; selector is FP regardless) |
| **Output quality** | 4.6665 PPL | 4.6569 PPL | **tie** — the #47 short-prompt "echo" was RE-INVESTIGATED (`G-ECHO-HUNT-47`, 2026-07-04) and is **not** a byteexact artifact: exact and FP echo the *system prompt* on contentless prompts about equally. FP does not fix it; #47's "float is correct" premise is refuted. |
| **Compression** | none (explicitly) | none | **n/a** |
| **Forward speed** | CRT-NTT overhead on islands+attn | standard FP kernels | **FP wins** |
| **Portability / build** | clang-cl + `__int128` | plain `cl.exe`, smaller binary | **FP wins** |

Byte-exactness buys **determinism, auditability, and integer memory fidelity** — the audit/swarm
column. It does **not** buy faithfulness, quality, or compression. That argues byte-exact should be
an explicit opt-in **"audit / swarm mode"**, not the daily driver — which is exactly where #47 points.

## 4. The A/B — most of it runs TODAY with zero new code

**Behavioural A/B needs no profile build** (byteexact is already a runtime flag): serve the *same
binary* with `byteexact:true` vs `byteexact:false` and diff:

- **Faithfulness parity** — `G-ONECONFIG-LIVE` (61-para obey) both ways. Expect ~tie (docs: 0 benefit). Gate name: `G-NOEXACT-OBEY-AB`.
- **Speed ladder** — tok/s exact vs FP decode (reuse the speed probe). Expect FP faster; quantify.
- **Determinism cross-run** — same prompt ×2 per mode, diff the token stream. Exact = bit-identical; FP = measure the first-divergence position / divergence rate. **This is the axis exact wins**; make the FP cost legible.
- **Short-prompt echo** — count echoes exact-on vs FP over a short-prompt set (the #47 signal). Expect FP better on some.

**Portability A/B needs the profile built** (the ~1-day piece): binary size, from-clean build time,
toolchain (`cl.exe` vs clang-cl), and — the real point — **`G-NOEXACT-PARITY`**: the FP-profile
binary reproduces `G-ONECONFIG-LIVE` obey within noise, proving parity holds when the exact code is
*physically gone*, not merely flag-off. Plus **`G-NOEXACT-BUILD`**: compiles with `cl.exe`, no
`__int128`, smaller binary.

**Memory-at-scale** is documented, not re-run: served recall is FP already (no change); the organism
retention `1.000 → 0.969 @ N=32` is the recorded cost of the FP profile *dropping* the integer ring.

## 4a. MEASURED — the flag-flip A/B on metal (2026-07-04, `G-NOEXACT-OBEY-AB`)

Ran the behavioural A/B with **zero new build**: one live daemon under `run_console_faithful.bat`,
per-request `byteexact` flipped `true` (exact) vs `false` (FP), on the RTX 2060.
Receipt: `shannon-prime-system-engine/tests/fixtures/chat_fullstack/G-NOEXACT-OBEY-AB.log`.

| Axis | Exact | FP | Read |
|---|---|---|---|
| **Faithfulness** (61 paraphrase obey) | **54/61** | **54/61** | **exact tie** — identical obey *and* identical 7 misses (`france_capital`, `telephone_inv`, `italy_capital`, `canada_capital`, `longest_river`, `statue_liberty`, `taj_mahal` — the known parametric-prior selection cross-picks). FP costs **nothing** on faithfulness. |
| **Speed** (amortized tok/s, prefill+recall bound) | 1.10 | 1.16 | **FP 1.06× faster** end-to-end. This workload is prefill/recall-bound with short answers, so 6% is a conservative floor on the decode-only delta. |
| **Determinism** (same prompt ×2, same box) | 6/6 identical | 6/6 identical | **equal on one pinned box** — `CUBLAS_WORKSPACE_CONFIG=:16:8` already makes FP run-to-run deterministic here. Exact's determinism win is **cross-MACHINE**, which this single-box run does not exercise. |
| **Short-prompt echo** (#47 signal) | 0/12 | 0/12 | **did not reproduce** on this 12-prompt set; both clean, and replies were byte-identical on 10/12. Honest null — this run does not confirm FP *fixes* #47, only that echo was not a differentiator here. |

**Interpretation.** The A/B confirms the thesis empirically: on the served daily-driver path,
byte-exact and FP are behaviourally indistinguishable on quality (identical 54/61, identical misses),
FP is marginally faster, and they are equally deterministic on a single pinned machine. Every
measured advantage of byte-exact lives in the **cross-machine / auditability** column that this
single-box test cannot show — exactly the SWARM/PoUW use case, not the daily driver. Nothing here
argues for byte-exact as the default; it argues for FP-default + byte-exact-as-audit-mode.

**#47 follow-up (`G-ECHO-HUNT-47`, 2026-07-04).** A dedicated hunt on the *plain chat* launcher
(`run_console_chat.bat`, recall OFF — the daily-driver path where #47 was reported), 30
short/adversarial prompts × both modes: the "echo" IS real but is **system-prompt recital on
contentless prompts** (`Sure.`→"You are Shannon-Prime…", `Continue.`→ same, `What?`→ FP echoes), and
it occurs in **exact AND FP about equally** (exact ~3, FP ~3; on `What?` FP is the one that echoes).
**byteexact is exonerated as the cause; #47's "float is correct" premise is refuted.** The real fix
is a prompting/decoding change for contentless turns, orthogonal to exact-vs-FP. Consequence: there
is **no "quality fix" argument** for the FP profile — it stands on portability + speed alone.

## 4b. RECON CORRECTION (2026-07-04) — the CUDA #ifndef work is low-value; the win is host-side

A closer read of `cuda_forward.cu` + `build.rs` + the `__int128` map revises §1–§2:

- **The byte-exact CUDA code uses NO `__int128`.** It uses `__umul64hi` for wide products (the
  dual-prime primes fit u64), per the kernel comments. So gating out the CUDA exact path removes **no
  toolchain dependency**, and the branches are ~15 scattered `if (d_bx_flag) {...}` one-liners inside
  many kernels (RMSNorm/RoPE/GELU/attention) — `#ifndef`-ing them cleanly is invasive and
  breakage-prone, for ~zero benefit (they are already zero-cost at runtime when `d_bx_flag==0`).
- **The `__int128` / clang-cl requirement comes ONLY from `core/exact_islands/exact_islands.c`**,
  which is compiled by the **CPU/math-core build (`build-cpu`)**, and is **NOT in the daemon's
  `build.rs` MODULES**. The four ring modules the daemon actually links
  (`ntt_crt.c`/`poly_ring.c`/`ok_arith.c`/`frobenius.c`/`resdot.c`) contain **zero `__int128`**
  (verified by grep). So the daemon's clang-cl dependency is `exact_islands.c` in the CPU-core step,
  not the ring or the CUDA.

**Revised profile = host-side only, two clean moves, no CUDA surgery:**
1. A cargo feature that drops the 4 **dormant** ring modules (`ntt_crt`/`poly_ring`/`ok_arith`/
   `frobenius`) + the 2 FFI files (`ntt_ffi.rs`/`ntt_hex_dispatch.rs`) from the daemon build →
   footprint win; requires a link check (nothing in the served path calls them, but the organism
   research does).
2. Remove `exact_islands.c` from the `build-cpu` step under the feature → that step compiles with
   `cl.exe` (no `__int128`) → removes the recurring clang-cl clean-build hazard.

The CUDA byte-exact kernels **stay in place** (default-off `d_bx_flag=0` = the FP path, zero runtime
cost) — there is no reason to cut them. This is a smaller, safer profile than §2 implied, and it
captures the entire measured portability value without touching `cuda_forward.cu`.

## 4c. BUILD STATUS (2026-07-04) — foundation landed, one cluster remaining

Lean host-side profile scaffolded (engine, this commit); the **default build stays GREEN** (verified
`cargo build --release --features wire_cuda_backend` = Finished, exact-on = daily driver unchanged):

- **`Cargo.toml`**: `exact` feature, **default-on**. FP profile = `--no-default-features --features wire_cuda_backend`.
- **`build.rs`**: under `!exact`, the 4 ring archives (`ntt_crt`/`poly_ring`/`ok_arith`/`frobenius`) are
  skipped from the link (footprint win).
- **`lib.rs`**: `pub mod ntt_ffi` gated `#[cfg(feature = "exact")]`.

**One cluster remains to make the FP profile LINK-GREEN (G-NOEXACT-BUILD):** `network/quic_shard.rs`
(the QUIC garner NTT mesh) references `ntt_ffi::{ntt_crt_recombine,ntt_free,ntt_init}` at 3 sites
inside recombine functions. These are genuinely ring-dependent (integer NTT recombination over the
wire), so under `--no-exact` they must be cfg-gated (the mesh recombine path is unavailable in the FP
profile — consistent, since the whole integer ring is gone). That is a contained `network`-module
edit + a `--no-default-features` build to confirm the link. The `exact_islands.c`→`cl.exe` half of
the CPU-core build is a separate `build-cpu`/CMake edit (independent of the daemon cargo build).

Deliberately **not** grinding the `quic_shard` gating + FP-build-debug loop in-session at turn-end
(RED risk against a portability-hygiene payoff); the foundation is safe and the daily driver is
untouched. The remaining step is small, well-scoped, and compiler-enumerable.

## 5. Recommendation

Do **not** spin up a sister repo. Build it as the `--no-exact` cargo feature. Sequence:

1. **Run the behavioural A/B now** (flag flip, no build) — `G-NOEXACT-OBEY-AB` + determinism +
   speed + short-prompt echo. This answers "what does exactness cost/buy per turn" this week and
   likely resolves #47 (make FP the daily-driver default; keep byteexact as opt-in audit mode).
2. **If the numbers justify portability** (they likely will — FP faster, `cl.exe`-clean, smaller),
   land the `--no-exact` feature (~1 day) and gate `G-NOEXACT-PARITY` + `G-NOEXACT-BUILD`.
3. Keep byte-exact as the **audit/swarm profile** — it remains the substrate the SWARM/PoUW design
   (`PPT-LAT-DESIGN-SWARM-MEMORY-MESH.md`) and the offline memory organism genuinely require.

The sibling is a **profile, not a project.** The only thing that resists being a compile switch is
the integer memory organism, and in the served daily driver that is already dormant.
