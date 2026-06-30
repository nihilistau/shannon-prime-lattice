---
type: session-handoff
title: SESSION-CLOSED-lat-2-L1-SESSION
description: "Phase: 2-L1.SESSION (Roadmap §8.7.4) — math core (shannon-prime-system)."
tags: [session-handoff, l1]
timestamp: 2026-05-25T11:58:37Z
resource: shannon-prime-lattice/papers/SESSION-CLOSED-lat-2-L1-SESSION.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# SESSION-CLOSED-lat-2-L1-SESSION

**Phase:** 2-L1.SESSION (Roadmap §8.7.4) — math core (`shannon-prime-system`).
**Session date:** 2026-05-25.
**Status:** **CLOSED 2026-05-25 — tag `lat-phase-2-l1-session-closed`** on
`shannon-prime-system` `main`. The session + forward half of the frozen L1 ABI is
real in code; with HANDLE (§8.7.3), the full `sp_model` + `sp_session` ABI now
exists in math-core. Commits (in order):
- `cc69ebc` — series 1: `sp_model_to_qwen3` bridge + create/destroy/position + `sp_prefill_chunk` + bit-exact parity gate.
- `af24e86` — series 2: `sp_decode_step` (persistent KV) + `sp_session_clone`/`rewind` + cancel wiring + the 100-step trajectory gate.
- `c7bdb9e` — record the fixture SHA-256 in the test output.

Tier-1 (Windows MinGW gcc 15.2): full root suite **16/16 green** incl. `T_SESSION`
(6 cases / 47 checks); UBSan trap-on-error build of the session path clean. **Tier-2
(Linux gcc) AND Tier-3 (MSVC) CI both green** on the push (run `26399281466`:
`linux-gcc` 39s, `windows-msvc` 50s). Remaining CI gap is the sanitizer-instrumented
Tier-2 run only (verified locally; not wired into `ci.yml`).

> **NEXT → Phase 2-L1.FP16 (§8.7.5).** The umbrella `lat-phase-2-l1-closed` fires
> after FP16 closes. FP16 must also resolve the two frozen-format metadata gaps this
> phase surfaced (see "Frozen-spec findings"). The session ABI is now ABI-stable for
> the FP16 kernel pass to build on.

---

## Done this session

All under `core/session/` in `shannon-prime-system`; new module `session` wired into
the root `SP_MODULES` after `forward`.

- **`sp_model_to_qwen3` bridge** (`sp_model_bridge.c`). Reconstructs a runnable
  `qwen3_model` from the `const sp_model` handle — the documented adapter path
  (`sp_model.h:152`), **not** a veneer over a GGUF-loaded model (the §8.7.4 spec
  discipline). Matmul weights (token_embd tied + per-layer attn q/k/v/o + ffn
  gate/up/down) → a packed arena via `sp_arena_from_packed`, built directly from the
  `.sp-model` OK_Q8 codes + paired `<name>.scale` (per-row Frobenius max-abs → the
  per-row Q8 `sp_frob_packed_tensor` layout, dequant `code*scale/127`). Norms → owned
  f32 (`norm_src`/`norm_buf`, `released=1`); `gguf=NULL`. Freed by `qwen3_free`.
  Re-derived from PPT-LAT-SP-MODEL-v0 + Systems App. B — no engine/legacy reads.
- **`sp_session_create` / `destroy` / `position` + `sp_prefill_chunk`** (`sp_session.c`,
  series 1). Prefill re-runs `qwen3_forward` over the accumulated history and writes
  the last position's logits.
- **`sp_decode_step` + `sp_session_clone` + `sp_session_rewind`** (series 2). Decode
  owns a persistent f32 KV cache, advanced one token/call (O(1) incremental; the
  prompt KV is filled lazily from history on the first step, so prefill stays the
  bit-exact re-forward). Its per-token math is the **gate-off f32 path of
  `qwen3_generate_kv`, replicated in the session** — `qwen3_generate_kv` itself is
  left untouched (no risk to the engine's GEN_KV gate, which math-core cannot re-run
  locally). Clone deep-copies history + live KV (the spec-decode fork); rewind rolls
  position back and refills stale KV. Cancellation reads the L2-owned atomic at the
  call boundary and returns `SP_ECANCEL` before mutating state.
- **Synthetic qwen3-shaped fixture** (`qwen3_fixture.c`, TEST_SOURCES): a tiny but
  complete qwen3 (2 layers, n_embd 32, n_ff 64, GQA 4/2, head_dim 8, vocab 48, tied)
  with the full weight set as OK_Q8 + Frobenius scales / F32 norms. Deterministic,
  CI-portable; no real model artifact needed.

### Test results — `T_SESSION`, 6 cases / 47 checks / 0 fails

| Case | What it gates | Result |
|---|---|---|
| `T_SESSION_BRIDGE` | `sp_model_to_qwen3` reconstructs a runnable model; cfg fields (incl. n_ff derived from ffn_gate); `qwen3_forward` over it gives finite logits | PASS |
| `T_SESSION_PREFILL_PARITY` | **`sp_prefill_chunk` last-position logits BIT-EXACT vs `qwen3_forward`** (the §8.7.4 first-parity gate; also the bridge's correctness gate) | PASS |
| `T_SESSION_GUARDS` | null/capacity/n_tokens=0 arg guards → `SP_EBADARG`; NULL cfg → defaults | PASS |
| `T_SESSION_DECODE_TRAJECTORY` | **session greedy argmax trajectory == `qwen3_generate_kv` EXACTLY over a 100-step decode** (the §8.7.4 full gate) | PASS |
| `T_SESSION_CLONE_REWIND` | clone is independent + its decode logits BIT-EXACT vs the original; rewind rolls position back; rewind > pos → `SP_EBADARG` | PASS |
| `T_SESSION_CANCEL` | tripped cancel flag → `SP_ECANCEL` (prefill + decode) with position unchanged; clears cleanly | PASS |

**Fixture `.sp-model` SHA-256** (deterministic, 88640 bytes):
`b6379383e70066c16dc92206bd8e5306531fb0ecbd40936a6812b0e5a2e0ff30`
(printed to stderr by `T_SESSION_BRIDGE`; regenerate by re-running the test).

## Frozen-ABI divergences (roadmap prose vs frozen `sp_l1.h` — frozen header wins)

- §8.7.4 prose lists `sp_session_arch`; it is **not** in the frozen `sp_l1.h`. Skipped
  — it would be a veneer over the already-shipped `sp_model_arch` (HANDLE). Consumers
  query arch via `sp_model_arch(model, ...)`.
- The prose omits `sp_session_position`, which **is** frozen — implemented.
- The full-gate prose names `gemma3_generate_kv`; **it does not exist in math-core**
  (only `qwen3_generate_kv`). Per the agreed disposition the full trajectory gate is
  **qwen3-only**. Note the session is **qwen3-only end-to-end as shipped**:
  `sp_prefill_chunk` dispatches `qwen3_forward` and `kv_step` replicates qwen3's
  per-token math (no sandwich norms, no dual RoPE). A gemma3 `.sp-model` would compute
  the wrong thing — gemma3 needs an arch-conditional dispatch in prefill + a parallel
  `kv_step` variant (and `gemma3_generate_kv` for its gate). Out of scope for §8.7.4.

## Frozen-spec findings (carry into FP16 / format-v1)

- **`sp_arch_info` carries neither `n_ff` nor `rms_eps`.** The bridge derives `n_ff`
  from the `ffn_gate` out-dimension and **defaults `rms_eps` to 1e-6**. The parity
  gate is bit-exact regardless (both sides use the same reconstruction), but a *real*
  transcoded model needs `rms_eps` carried in the format — an `sp_arch_info` field
  (ABI bump + `.sp-model` arch_struct rev) or a separate metadata slot. Decide
  alongside the `preferred_precision` question from the HANDLE offload (also still a
  format/ABI gap, for fp8). **Do not extend `sp_arch_info` unilaterally** — it is an
  L1 ABI change.
- **HANDLE-offload correction (owned):** SESSION-CLOSED-lat-2-L1-HANDLE classified
  `sp_model_to_qwen3` as "the L2/engine adapter… out of scope for SESSION." On the
  §8.7.4 read that was wrong — SESSION cannot run inference without it, and the spec's
  "no veneer" rule forbids a *public* `sp_session_create(qwen3_model*)` entry point,
  not the session internally holding a reconstructed model. It now lives in math-core
  (`core/session/sp_model_bridge.c`). `sp_model.h:152` documented this path all along.

## Build + run (Tier-1, this host)

```bash
cmake -S shannon-prime-system -B build -G Ninja -DCMAKE_C_COMPILER=gcc
cmake --build build && ctest --test-dir build -R T_SESSION --output-on-failure
# UBSan (trap-on-error on MinGW): -DSP_UBSAN=ON, target test_session.
```
The `session` module has a wide dependency fan-in (io_format + forward + model +
arena + frobenius); build it from the ROOT tree (which CI uses), not standalone.

## SESSION handoff state — the surface now complete

Frozen, implemented, tested in math-core (`sp/sp_l1.h` + `sp/sp_model.h`):
`sp_model_load`/`unload`/`arch`/`find_tensor`/accessors/`verify_spinors` (HANDLE) +
`sp_session_create`/`destroy`/`position`/`prefill_chunk`/`decode_step`/`clone`/`rewind`
+ the atomic cancel flag (SESSION). The model-handle and session halves of
PPT-LAT-L1-ABI-v0 are both real.

## Open / notes

- **Bridge scope = tied embeddings + qwen3 weight set only (fails loud otherwise).**
  `sp_model_to_qwen3` rejects an untied model with a clear error (`return NULL` +
  `sp_last_error`) — a real transcoded Qwen3 is **untied** (`output.weight` separate;
  cf. the CPU offload), so wiring a real model needs the untied branch: pack
  `output.weight` as its own arena entry + synth slot. It also omits gemma3's
  `post_attention_norm`/`post_ffw_norm` from the NORM list. The synthetic fixture is
  tied + qwen3-shaped so the gates pass cleanly; **the engine-integration / FP16 agent
  must extend the bridge before loading a real or gemma3 model.**
- **Decode is the f32 reference path.** The session implements the gate-off f32 KV
  decode. The production Spinor-block KV overlay (`SP_KV_SPINOR`) and the NTT/KSTE
  attention overlays are engine/backend concerns, not the L1 session reference — out
  of scope here (and for FP16, which is about working precision, not the KV codec).
- **Re-forward prefill is O(n²) across multiple prefills** (each re-runs the full
  forward over the accumulated history). Single-shot prefill is fine; the persistent
  KV makes decode O(n). A KV-populating prefill (so multi-chunk prefill is also O(n))
  is a clean follow-up but was not needed for either gate and would break the bit-exact
  parity (a KV-path prefill is only argmax-equal to `qwen3_forward`, not bit-equal).
- **Tier-2 sanitizer gate** unchanged from HANDLE: `ci.yml`'s `linux-gcc` job builds
  without `-DSP_UBSAN=ON`/ASan; the instrumented run is verified locally (trap-on-error)
  but not in CI. One-line CI edit when wanted.
- **Anti-contamination held**: bridge + decode re-derived from the spec papers + the
  in-repo `qwen3_model`/forward; the legacy `shannon-prime/` and `shannon-prime-engine/`
  trees were not read.
