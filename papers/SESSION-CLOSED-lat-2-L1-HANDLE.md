# SESSION-CLOSED-lat-2-L1-HANDLE

**Phase:** 2-L1.HANDLE (Roadmap §8.7.3) — math core (`shannon-prime-system`).
**Session date:** 2026-05-25.
**Status:** **CLOSED 2026-05-25 — tag `lat-phase-2-l1-handle-closed`** on
`shannon-prime-system` `main` @ **`df44c5e`** (`df44c5e0fdb0a59cbdc5b175ff4f13c60ce7cdb4`),
pushed to `origin/main` (`63f6488..df44c5e`). The `.sp-model` adapter surface is
landed against the **frozen** L1 ABI; the model-handle half of PPT-LAT-L1-ABI-v0
is complete. Tier-1 (Windows MinGW gcc 15.2) **15/15 root suite green incl.
T_IO_FORMAT (11 cases / 37 checks)**; UBSan trap-on-error clean. **Tier-2 (Linux
gcc) AND Tier-3 (MSVC) CI both green on the push** (run `26397311284`: `linux-gcc`
32s, `windows-msvc` 59s) — MSVC passed, so the umbrella `lat-phase-2-l1-closed`
MSVC concern is satisfied for this io_format layer. Remaining CI gap is the
*sanitizer-instrumented* Tier-2 run only (see Open/notes).

> **NEXT SESSION PICKS UP HERE → Phase 2-L1.SESSION (§8.7.4).** The loader,
> arch query, tensor lookup, and Spinor verify are all in place and frozen-ABI
> conformant. SESSION builds the *session + forward* half of the same ABI
> (`sp_session_create`/`sp_session_destroy`, `sp_prefill_chunk`/`sp_decode_step`,
> `sp_session_clone`/`rewind`/`position`, declared in `include/sp/sp_l1.h`,
> all currently **undefined**). The first parity gate is `sp_prefill_chunk` ==
> the reference forward's last-position logits (the §8.7.4 clause). See
> "SESSION handoff state" below for the exact surface you inherit.

---

## ⚠ Corrected scope — the original HANDLE handoff was stale

The handoff prompt for this sub-phase was written against the **v0 draft** as if
nothing had been built, and contradicted the already-frozen, already-implemented
L1 ABI in load-bearing ways. It was reconciled (user verdict: *"the frozen
contract is sacred"*, Option 1) **before** any code was written. For the record,
so the SESSION agent does not re-derive the wrong contract:

| Stale handoff asked for | Frozen reality (PPT-LAT-L1-ABI-v0 / Systems App. A / shipped code) |
|---|---|
| `sp_model_query`, `sp_model_release`, 2-arg `sp_model_load` | `sp_model_arch`, `sp_model_unload`, **3-arg** `sp_model_load(model, tokenizer, **out)` |
| `sp_model_get_tensor` | `sp_model_find_tensor` |
| new `SP_EFORMAT_MAGIC/VERSION/LAYOUT/TOKENIZER_MISMATCH/SPINOR_SENTINEL` | the frozen enum: `SP_EBADFORMAT` (−10), `SP_ETOKENIZER_HASH` (−12), `SP_EVOCAB` (−13), `SP_ESPINOR_BADBLOCK` (−20) — "must not be renumbered" |
| separate `sp_tokenizer.{h,c}`, tests `T_MODEL_1..6` | tokenizer folded into the format module; test name `T_IO_FORMAT` |
| branch `lat-l1`, push `origin/lat-l1` | `lat-l1` already merged to `main`; no such branch/remote |
| "depends on `core/hash`" | the hash primitives live in **`core/io_hash`** (module `sp_io_hash`) |

The loader/format layer itself was already landed by RELOCATE (`.sp-model
format/loader` = `cced325`, hash primitives = `c795845`) and integrated +
validated by VALIDATE (`lat-phase-2-l1-validate-closed`). HANDLE therefore did
**only the three genuinely-missing math-core gaps**, using the real names/codes.

---

## Done this session (commit `df44c5e`)

All under `core/io_format/` in `shannon-prime-system`; one coherent commit.

- **A — `sp_model_arch`** (`sp_model_arch.c`, new). Implements the
  declared-but-undefined L1 arch query (`include/sp/sp_l1.h:78`,
  `sp_status sp_model_arch(const sp_model*, sp_arch_info*)`). Projects the header
  `arch_struct` — the memcpy-direct `sp_arch_info` payload (PPT-LAT-SP-MODEL-v0
  §3) — into the caller-stack-allocated out-param via the **public** header
  accessor `sp_model_get_header` (does not reach into the opaque `sp_model`).
  `SP_EBADARG` on null handle/out; zero-fills any tail the producer didn't write.
- **B — Spinor `0xA5` sentinel sweep** (`sp_model_load.c`). PPT-LAT-SP-MODEL-v0
  §6: byte `block_size-1` (== 63 for the frozen 64-byte block) of every
  `SP_DT_SPINOR63` tensor block holds `0xA5`. The default `sp_model_load` path
  samples the **first + last** block of each Spinor tensor (cheap page-tear/
  partial-write integrity, no O(N) sweep); a mismatch returns the frozen
  **`SP_ESPINOR_BADBLOCK`** (−20), un-bounds-checkable geometry returns
  `SP_EBADFORMAT`. The full per-block sweep is exposed as the **non-ABI** helper
  `sp_model_verify_spinors(const sp_model*, int full_sweep)` (declared in
  `sp/sp_model.h`, internal-helpers section) for the SESSION `SP_VERIFY_TENSORS`
  path. No new error code was invented; the spec's `SP_VERIFY_TENSORS` full scan
  remains the opt-in heavy check, this is the always-on cheap layer beneath it.
- **C — Runtime loader tests** (`io_format_test.c`, `T_IO_FORMAT`) over a
  **synthetic, spec-conformant** `.sp-model`+`.sp-tokenizer` built in-process
  (`sp_model_fixture.{h,c}`, compiled via `TEST_SOURCES`). Deterministic and
  dependency-free — no multi-GB real-model artifact, green on every tier incl.
  Tier-2 Linux CI. The fixture is a Gemma3-shaped (arch_id=GEMMA3) model with one
  F32 tensor + one 4-block SPINOR63 tensor and a paired SentencePiece tokenizer;
  hashes (header CRC-32, tokenizer SHA-256, name `xxh64`) are real so it passes
  the loader's default-load checks. Negative cases mutate a copy of the buffers.

### Test results — `T_IO_FORMAT`, 11 cases / 37 checks / 0 fails

| Case | Scenario | Result |
|---|---|---|
| `HEADER_LAYOUT` | packed-struct sizes/offsets (512/256/128; @280/@360/@208/@176) | PASS |
| `T_IO_FORMAT_LOAD_OK` | valid synthetic model+tokenizer → load+count+release | PASS (`SP_OK`) |
| `T_IO_FORMAT_BAD_MAGIC` | clobber `SPMD` magic | PASS (`SP_EBADFORMAT`) |
| `T_IO_FORMAT_BAD_VER` | `version_major` → 1 | PASS (`SP_EBADFORMAT`) |
| `T_IO_FORMAT_BAD_CRC` | corrupt `created_unix_seconds` (CRC-covered, [0,360)) | PASS (`SP_EBADFORMAT`) |
| `T_IO_FORMAT_TOK_HASH` | corrupt `.sp-tokenizer` body → SHA-256 drift | PASS (`SP_ETOKENIZER_HASH`) |
| `T_IO_FORMAT_FIND` | `sp_model_find_tensor` hit (f32 + spinor) + miss | PASS (O(log N) hit/NULL miss) |
| `T_IO_FORMAT_SPINOR_OK` | all sentinels `0xA5` | PASS (`SP_OK`) |
| `T_IO_FORMAT_SPINOR_BAD` | clobber **last** block sentinel | PASS (`SP_ESPINOR_BADBLOCK`, caught by default sample) |
| `T_IO_FORMAT_ARCH` | `sp_model_arch` byte-identity vs embedded `sp_arch_info`; null-handle/null-out guards | PASS (`SP_OK` / `SP_EBADARG`) |
| `T_IO_FORMAT_SPINOR_FULL` | clobber **middle** block: default load passes, `verify(full=0)` misses, `verify(full=1)` catches | PASS (proves both flag states) |

**Fixture `.sp-model` SHA-256** (deterministic, `FX_BLOCKS=4`, 65920 bytes):
`96e3757fecb6f24cb359f43f38b3cc39e1e0c73d5a2cd2cba5cd81a1eaeb9c2f`
(printed to stderr by `T_IO_FORMAT_LOAD_OK`; regenerate by re-running the test).

**Open question answered — `sp_arch_info` vs `preferred_precision`.** They are
**NOT the same struct today.** `preferred_precision` is **not** a field of the
frozen `sp_arch_info` (PPT-LAT-L1-ABI-v0 §2 / Systems App. A / `sp/sp_l1.h:59`).
The term appears **only** in `PPT-LAT-Roadmap.md:1541`, as a forward-looking hook
for "a later fp8 sub-phase." **Action for Phase 2-L1.FP16:** fp16-vs-fp32 gating
is *not yet expressible* through `sp_arch_info`. Choose one and treat it as its
own contract event: (a) bump `sp_arch_info` (which is an **L1 ABI change** + a
Roadmap entry to update the frozen contract + a `.sp-model` `arch_struct` rev),
or (b) add a `precision_mode` field to `sp_session_config` (session-time, no
model-format change — likely the cleaner cut since precision is a run knob, not a
model property). **Do not extend `sp_arch_info` unilaterally.**

## Build + run (Tier-1, this host)

```bash
# Whole math core (mirrors CI):
cmake -S shannon-prime-system -B build -G Ninja -DCMAKE_C_COMPILER=gcc
cmake --build build
ctest --test-dir build -R T_IO_FORMAT --output-on-failure
# Standalone module + UBSan (trap-on-error on MinGW; no libubsan):
cmake -S shannon-prime-system/core/io_format -B bh -G Ninja -DCMAKE_C_COMPILER=gcc -DSP_UBSAN=ON
cmake --build bh && ctest --test-dir bh -R T_IO_FORMAT --output-on-failure
```
Toolchain: CMake 4.2.1, MinGW-Builds gcc 15.2.0, Ninja 1.13. No model file or
network needed (the fixture is synthetic).

## SESSION handoff state — the surface you inherit (all in `sp/sp_model.h` / `sp/sp_l1.h`)

Frozen, implemented, tested — **ready to consume**:
- `sp_model_load(model_path, tokenizer_path, **out)` / `sp_model_unload` — mmap
  load + full header/CRC/tokenizer-SHA/vocab/Spinor validation.
- `sp_model_arch(m, *out)` — size your logits buffer from `out->vocab_size`.
- `sp_model_get_header` / `sp_model_tensor_count` / `sp_model_tensor_at` /
  `sp_model_find_tensor(name)` (O(log N) `xxh64` + collision-safe name verify) /
  `sp_model_tensor_data(m, e)` / `sp_model_tokenizer_blob(m, *size)`.
- `sp_model_verify_spinors(m, full_sweep)` — non-ABI; your `SP_VERIFY_TENSORS`
  hook (`sp_session_config.flags`) can call it with `full_sweep=1` at create.

**NOT done (yours):** everything session/forward in `sp/sp_l1.h` is declared but
**undefined** — `sp_session_create/destroy`, `sp_prefill_chunk`, `sp_decode_step`,
`sp_session_clone/rewind/position`, `sp_session_config`. fp16 working precision is
the FP16 sub-phase after you (see the `preferred_precision` finding above).

## Open / notes

- **Tier-2 UBSan/ASan gate.** The §3.7 gate calls for `T_MODEL_1`(≈`LOAD_OK`)
  under UBSan **+ ASan** on Linux CI. `.github/workflows/ci.yml`'s `linux-gcc`
  job does **not** currently pass `-DSP_UBSAN=ON` (nor `-fsanitize=address`).
  `cmake/sp_module.cmake` already supports `SP_UBSAN` (real libubsan on Linux
  gcc; trap-on-error fallback on MinGW — verified clean locally). Honoring the
  letter of the gate needs a one-line CI edit (a sanitized job or flag) — left
  **un-touched** this session because CI is shared scaffold across all modules;
  flagged here for a deliberate decision rather than a silent edit.
- **Real-model end-to-end deferred.** The original `T_MODEL_6` (load a real
  transcoded Gemma3-1B `.sp-model`) cannot run: **no `.sp-model` artifact exists
  on this host** (no `sp-transcode` output found in any non-contaminated repo).
  The synthetic fixture exercises the identical loader/arch/find/sentinel paths.
  When a transcoded model lands, add a presence-gated case (skip if absent),
  mirroring the HX/S22U physical-presence pattern.
- **Anti-contamination held.** Everything re-derived from PPT-LAT-L1-ABI-v0 /
  PPT-LAT-SP-MODEL-v0 / PPT-LAT-Systems App. A+B; the legacy `shannon-prime/` and
  `shannon-prime-engine/` trees were not read.
- **`sp_io_format` still declares `sp_model_to_qwen3`** (the runtime-model
  adapter, `sp/sp_model.h`) as an inert prototype; its definition remains
  engine-side and is out of scope for both HANDLE and SESSION (it is the L2/engine
  adapter, not the L1 handle).
