---
type: session-handoff
title: SESSION-PLAN — Phase 3-G4 Stage 2 (Gemma4 decode + oracle validation)
description: "Filed: 2026-06-02 (overnight autonomous handoff)."
tags: [session-handoff]
timestamp: 2026-06-01T21:07:03Z
resource: shannon-prime-lattice/papers/SESSION-PLAN-lat-3-g4-stage2.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# SESSION-PLAN — Phase 3-G4 Stage 2 (Gemma4 decode + oracle validation)

**Filed:** 2026-06-02 (overnight autonomous handoff). **Owner:** dispatched agent.
**Entry state:** Stage 1 math-core GREEN — system `51e4c5c`, lattice `978545a`,
engine `0a600f3`. Full math-core suite **19/19**. Gemma4 forward + bridge +
fixture + prefill-parity all green and pushed.

This plan is the single source of truth. Read it + roadmap §3-G4 (Stage 0/1
entries near the phase-log tail) before doing anything.

## Confirmed-from-source (do NOT re-litigate)

- **rope_freqs semantics:** `theta_i = (pos · base^(-2i/d)) / ff[i]` — verified
  against ggml `rope_cache_init` (`D:\F\llama.cpp\src\...\ops.cpp:5708-5719`:
  `ff = freq_factors[i0/2]`, `rope_yarn(theta/ff,...)`, `theta *= theta_scale`).
  `core/forward_kernels/forward_kernels.c::sp_rope_neox_freqs` already implements
  this exactly (ext_factor=0, freq_scale=1, mscale=1 for gemma4 → plain cos/sin).
- **AltUp scales:** `1/sqrt(n_embd)` (proj), `1/sqrt(2)` (input), `sqrt(PL)` (token
  embd) — read from `gemma4.cpp::project_per_layer_inputs`. Implemented in gemma4.c.
- **Weightless V-norm:** `ggml_rms_norm` no weight — read from gemma4.cpp graph.
  Implemented as `g4_rmsnorm_noweight`.
- **Per-layer geometry:** SWA 256/8/2, global 512/4/1, QD=2048 KVD=512 constant;
  global layer when `L % swa_period == swa_period-1`. Shared-KV: owners
  `[0, n_kv_from_start)`; shared SWA reuse owner `kvfs-2`, shared global `kvfs-1`.

## Discipline (BINDING — these are the rules the operator enforces)

1. **Never fake or relax a gate.** If gemma4_forward diverges from the oracle,
   that is a real finding — debug the forward, or surface UPSTREAM in the closure
   doc. Do NOT widen tolerances, tune fixtures, or retreat to a weaker check to
   make a number pass. (memory: feedback-no-silent-gate-revisions)
2. **Keep the tree green at every commit.** Build (`cmake --build`) + `ctest`
   must pass before each commit. Land WIP behind a flag if it can't stay green.
3. **Anti-contamination.** Never copy code from `D:\F\shannon-prime-repos\
   shannon-prime\` or `...\shannon-prime-engine\`. `D:\F\llama.cpp` is
   REFERENCE-READ ONLY (read the graph; re-derive, never paste).
4. **Tricks are proven spine — implement, don't defer.** (memory:
   feedback-tricks-are-proven-spine)
5. Commit per green increment, `[lat-3-g4]` prefix, push to origin/main. Write
   `SESSION-CLOSED-lat-3-g4-stage2.md` at the end with HONEST pass/fail per gate.

## Build / test / oracle

- gcc build dir: `D:\F\shannon-prime-repos\shannon-prime-system\build` (MinGW
  gcc 15.2 + Ninja). Prepend `C:\ProgramData\mingw64\mingw64\bin` to PATH.
  `cmake --build <build>` then `ctest --test-dir <build> --output-on-failure`.
- Oracle: `%SP_LLAMA_ORACLE_DIR%` = `D:\F\llama.cpp\build\bin`
  (`llama-cli.exe`, `llama-perplexity.exe`, gemma4 support, commit 5dcb711).
- Models: E4B = `D:\Files\Models\lmstudio-community\gemma-4-E4B-it-GGUF\
  gemma-4-E4B-it-Q6_K.gguf` (Q6_K — NOT dequantable by math-core, oracle-only).
  **E2B Q8_0** = `D:\Files\Models\New folder\gemma-4-E2B-it-uncensored-Q8_0.gguf`
  (Q8_0 — math-core `sp_dequant_row` supports it; USE THIS for the loader gate).
- GGUF inspector: scratch `g4_inspect.py` pattern; `python -c "import gguf; ..."`.

## File map

- Forward: `core/forward/gemma4.c` (`gemma4_forward`, `gemma4_forward_ex2`).
- Bridge: `core/session/sp_model_bridge.c` (`sp_model_to_gemma4`).
- Fixture: `core/session/gemma4_fixture.{c,h}` (NL=6, period=3, kvfs=3).
- Session dispatch: `core/session/sp_session.c` — create bridge dispatch (~line
  84), prefill forward dispatch (~line 187), `kv_step_gemma3` (~line 353), decode
  dispatch (~line 549). Mirror these for gemma4.
- Tests + runner: `core/session/session_test.c` (`T_GEMMA4_*`, `SP_RUN` block).
- Config/struct: `include/sp/model.h` (qwen3_config g4_* / qwen3_layer /
  qwen3_model fields), `include/sp/sp_l1.h` (sp_arch_info g4_* tail).
- Row dequant: `core/forward_dispatch/forward_dispatch.c::sp_weight_row`.

## TASKS (priority order)

### TASK A (PRIMARY, low-risk, green-verifiable now) — kv_step_gemma4 decode
Mirror `kv_step_gemma3` (sp_session.c) adding the gemma4 deltas already in
`gemma4_forward`: per-layer geometry dispatch, weightless V-norm, rope_freqs on
global layers, attention scale 1.0, AltUp per-layer-input injection, per-layer
out_scale, logit softcap, and shared-KV reuse against the persistent KV cache.
Persistent KV: the session caches K/V per OWNER layer; shared layers (≥ kvfs)
read the owner's cached K/V (SWA→kvfs-2, global→kvfs-1) and skip their own K/V.
Wire `kv_step_gemma4` into the decode dispatch (the `_arch == ...` ternary near
sp_session.c:549). Add `T_GEMMA4_DECODE_TRAJECTORY` to session_test.c mirroring
`T_GEMMA4_PREFILL_PARITY` + `T_GEMMA3_DECODE_TRAJECTORY`: session greedy decode
trajectory (prefill TOKS then decode_step) == `gemma4_forward` O(n²) re-prefill
reference, bit-exact over the available steps. Register in the SP_RUN block.
Build + full ctest green. Commit + push. **This completes the L1 session ABI
(prefill+decode) for gemma4.**

### TASK B (SECONDARY) — gemma4 GGUF loader + oracle top-1 validation
Goal: prove `gemma4_forward` is bit-faithful to REAL Gemma4, not just
self-consistent. Build a loader that reconstructs a `qwen3_model` from the
**E2B-Q8_0** GGUF (gguf-backed: `qm->gguf` set, no arena, `released=0`; bind the
gemma4 tensors by GGUF name; sp_matmul will dequant Q8_0 from the mapping).
Derive config: `nh_swa=head_count`, `hd_swa=key_length_swa`, `nkv_swa=head_count_kv`,
`hd_global=key_length`, `nh_global=(nh_swa*hd_swa)/hd_global`,
`nkv_global=(nkv_swa*hd_swa)/hd_global`, `swa_period` from the sliding_window_pattern
array (confirm it is periodic; else store the full per-layer bool array — may need
a config extension), `n_kv_from_start=n_layer-shared_kv_layers`, softcap from
`final_logit_softcapping`, rope bases from `rope.freq_base`(+`_swa`), `n_embd_per_layer`
from `embedding_length_per_layer_input`. Then a harness (engine `tools/` or a
math-core test bin) that greedy-generates ~16 tokens from a fixed prompt and
compares the argmax token sequence to the oracle (`llama-cli --temp 0 -no-cnv`
on the same E2B-Q8_0 model, same prompt). Tokenization must match — either use
the GGUF's tokenizer via the math-core tokenizer, or extract llama-cli's token
IDs (`-v`/verbose prints them) and feed the same IDs to both. **Top-1 match over
16 tokens = forward validated.** If it diverges: debug (suspects in order:
per-layer geometry derivation, AltUp injection wiring, shared-KV map, the
sliding_window_pattern periodicity assumption). Record the result honestly —
a divergence is a finding, not a failure to hide.

### TASK C (IF TIME) — engine sp-transcode gemma4 + M_GEMMA4 engine gate
Add gemma4 to the engine's `sp-transcode` (real GGUF → `.sp-model` with the
gemma4 tensor set + `g4_*` arch_struct), so the production path
(transcode → sp_model_load → sp_model_to_gemma4 → gemma4_forward) works, and
wire the engine `M_GEMMA4` distributional PPL gate (§8.6.1) vs the oracle. Larger;
only if A+B are done and green.

## Closure
Write `SESSION-CLOSED-lat-3-g4-stage2.md`: per-task PASS/FAIL/PARTIAL with the
actual numbers, what was committed (hashes), what remains, and any UPSTREAM
surfaces. Update the roadmap phase log. Push all touched repos.
