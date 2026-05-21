# SESSION-STATE-lat-2-CPU

**Phase:** 2-CPU — engine, CPU backend (`shannon-prime-system-engine`).
**Session date:** 2026-05-21.
**Status:** **2-CPU.A done (E_CPU_1 green).** GGUF loader built + tested under MSVC. Forward pass (2-CPU.B) not started.

---

## Done this session

- **Phase-2 entry:** added `lib/shannon-prime-system` submodule (pinned at the all-tiers-green math-core HEAD). Engine root CMake builds the submodule's `sp_*` libs (tests off) and links `sp_frobenius/ntt_crt/poly_ring/kste/vht2`.
- **2-CPU.A — GGUF loader** (`include/sp_engine/gguf.h`, `src/loader/gguf.c`): GGUF v3, cross-platform mmap (Win32 `CreateFileMapping` / POSIX `mmap`), bounds-checked cursor parse of header + metadata KVs + tensor table, per-`ggml_type` block-size validation, every tensor checked in-bounds + aligned. Typed scalar/string metadata getters. **E_CPU_1 green** (`tests/test_loader.c`): parses `Qwen3-0.6B-f16.gguf` → arch=qwen3, 311 tensors, 34 kv, 28 layers, 16 heads, dim 1024; header round-trips. 15 checks, 0 fails, MSVC `/W4` clean.
- **Build-env fix:** `scripts/env/env-common.bat` + `env-cpu.bat` were broken on first real use — UTF-8 box-drawing/em-dash chars broke cmd parsing, and the `(x86)` VS path breaks parenthesised `if`-blocks. Rewrote both in ASCII with `goto`-based error handling. (Per prompt.md the pinned env scripts are fixed when they error.) `env-cuda/vulkan/hexagon.bat` likely have the same two bugs — fix them the same way when those backends come up.

## Build + run (CPU backend)

```bat
scripts\build\build-cpu.bat            REM vcvars64 (VS2019 BT) + cmake -G Ninja into build-cpu\, then build
ctest --test-dir build-cpu -R E_CPU --output-on-failure
```
Engine tests use the math-core `sp/sp_test.h` harness (via the submodule). Reference model path is a CMake cache var `SP_QWEN3_GGUF` (default `D:/Files/models/Qwen/Qwen3-0.6B-GGUF/Qwen3-0.6B-f16.gguf`).

## Prerequisites in place

- **Model:** `Qwen3-0.6B-f16.gguf` (1.5G) + `Qwen3-0.6B-Q8_0.gguf` (768M) from `ggml-org/Qwen3-0.6B-GGUF` (llama.cpp org) at `d:\Files\models\Qwen\Qwen3-0.6B-GGUF\`. f16 = unquantized source for the Frobenius-Q8 path + the higher-precision oracle run.
- **Oracle:** llama.cpp built at `d:\F\llama-cpp-sp\build\bin\` (`llama-perplexity.exe`, etc.) — the logit/PPL reference for E_CPU_2.
- Qwen3-0.6B arch: 28 layers, hidden 1024, 16 attention heads (GQA — check `qwen3.attention.head_count_kv`), RoPE, SwiGLU FFN, RMSNorm. Tied embedding likely (check for separate `output.weight`).

## Next session — pick up first (2-CPU.B, the big one)

1. **Forward pass on Qwen3-0.6B** → E_CPU_2: token-level logits within 1e-4 abs / 0.1% rel of llama.cpp on the first 256 tokens of a fixed prompt. Build the 13-step pass (embedding → RMSNorm → QKV (GQA) → RoPE → attention (dense fp32 first, NTT path is 2-CPU.E) → O-proj → SwiGLU FFN → residual/norm loop → final norm → LM head). Read Qwen3 specifics from the GGUF metadata (head_count, head_count_kv, rope_freq_base, rms_norm_eps, feed_forward_length, n_vocab).
   - Decode f16 weights (and Q8_0 blocks) → f32 for the reference fp32 path first; correctness before compression.
   - Generate reference logits: run `llama-perplexity`/`llama-cli` with `--logits`/eval-callback on the same prompt+model, dump, compare.
2. Then **2-CPU.C** Frobenius-Q8 inline matmul (use `sp_frob_*` on the f16 source) → E_CPU_3; **2-CPU.D** AVX2/512; **2-CPU.E** NTT-attention (sieve OFF, `sp_pr_*`) within T_PR_2 tolerance; **2-CPU.F** KSTE KV behind `SP_KSTE_KV=1`. **T_FRO_4** (Gemma3-1B PPL, `d:\Files\models\Mine\gemma-3-1b-it\gemma-3-1b-it-f16\`) runs once the forward pass exists.

## Open / notes

- The engine build also builds + registers the math-core unit tests (T_OK..T_KSTE) because `sp_add_module` always creates the test exe regardless of `SP_SYSTEM_BUILD_TESTS`. Harmless (they pass, ~2s) but bloats the engine build. Optional later: gate test creation in `sp_module.cmake` without breaking standalone module builds.
- Forward pass is large and sequential (loader → tensors → per-op → full pass); not cleanly parallel within the backend. Parallelism in Phase 2 is across backends/models, not within one bring-up.
