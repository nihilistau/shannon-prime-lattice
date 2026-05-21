# SESSION-STATE-lat-2-CPU

**Phase:** 2-CPU — engine, CPU backend (`shannon-prime-system-engine`).
**Session date:** 2026-05-21.
**Status:** **2-CPU.A done (E_CPU_1).** **2-CPU.B step 1 done (MODEL_BIND):** Qwen3 config + weight binding + dequant verified. Forward-pass computation (E_CPU_2) not started — blocked on a clean logit oracle (see below).

---

## Done this session

- **Phase-2 entry:** added `lib/shannon-prime-system` submodule (pinned at the all-tiers-green math-core HEAD). Engine root CMake builds the submodule's `sp_*` libs (tests off) and links `sp_frobenius/ntt_crt/poly_ring/kste/vht2`.
- **2-CPU.A — GGUF loader** (`include/sp_engine/gguf.h`, `src/loader/gguf.c`): GGUF v3, cross-platform mmap (Win32 `CreateFileMapping` / POSIX `mmap`), bounds-checked cursor parse of header + metadata KVs + tensor table, per-`ggml_type` block-size validation, every tensor checked in-bounds + aligned. Typed scalar/string metadata getters. **E_CPU_1 green** (`tests/test_loader.c`): parses `Qwen3-0.6B-f16.gguf` → arch=qwen3, 311 tensors, 34 kv, 28 layers, 16 heads, dim 1024; header round-trips. 15 checks, 0 fails, MSVC `/W4` clean.
- **2-CPU.B step 1 — model layer** (`include/sp_engine/model.h`, `src/forward/model.c`): `qwen3_load` reads the config from GGUF metadata and binds every weight tensor per layer; `sp_f16_to_f32` + `sp_dequant_row` (F32/F16/Q8_0). **MODEL_BIND green** (`tests/test_model.c`, 20 checks): config matches the known arch, all 28 layers bound, every tensor shape consistent, embedding dequant finite. Qwen3-0.6B config locked in code: 28 layers, n_embd 1024, n_ff 3072, **GQA 16/8, head_dim 128** (Q proj→2048, K/V→1024), **per-head QK-RMSNorm** (`attn_q_norm`/`attn_k_norm` [128]), untied `output.weight`, SwiGLU, rope_base 1e6, rms_eps 1e-6, vocab 151936, GPT2-BPE tokenizer.
- **Build-env fix:** `scripts/env/env-common.bat` + `env-cpu.bat` were broken on first real use — UTF-8 box-drawing/em-dash chars broke cmd parsing, and the `(x86)` VS path breaks parenthesised `if`-blocks. Rewrote both in ASCII with `goto`-based error handling. (Per prompt.md the pinned env scripts are fixed when they error.) `env-cuda/vulkan/hexagon.bat` likely have the same two bugs — fix them the same way when those backends come up.

## Build + run (CPU backend)

```bat
scripts\build\build-cpu.bat            REM vcvars64 (VS2019 BT) + cmake -G Ninja into build-cpu\, then build
ctest --test-dir build-cpu -R E_CPU --output-on-failure
```
Engine tests use the math-core `sp/sp_test.h` harness (via the submodule). Reference model path is a CMake cache var `SP_QWEN3_GGUF` (default `D:/Files/models/Qwen/Qwen3-0.6B-GGUF/Qwen3-0.6B-f16.gguf`).

## Prerequisites in place

- **Model:** `Qwen3-0.6B-f16.gguf` (1.5G) + `Qwen3-0.6B-Q8_0.gguf` (768M) from `ggml-org/Qwen3-0.6B-GGUF` (llama.cpp org) at `d:\Files\models\Qwen\Qwen3-0.6B-GGUF\`. f16 = unquantized source for the Frobenius-Q8 path + the higher-precision oracle run.
- **Oracle (BLOCKER for E_CPU_2):** the local llama.cpp checkouts — `d:\F\llama-cpp-sp`, `…\shannon-prime-repos\llama-cpp-sp-cleanroom`, `…\llama-cpp-b8861-test` — are **all contaminated** (each links `shannon_prime_core/cuda/engine` libs; "cleanroom" is misnamed). They are NOT valid stock references and are in the anti-contamination zone — do not use them. E_CPU_2 needs a **clean** logit oracle: either (a) a fresh upstream `llama.cpp` build (then `llama-perplexity --kl-divergence-base ref.bin` dumps logits, or a ~60-line tool against stock `libllama` + ggml libs), or (b) HF `transformers` running `Qwen/Qwen3-0.6B` (authoritative; needs torch). Build it out-of-tree, away from the contaminated checkouts.
- Qwen3-0.6B arch (now locked in `model.c`): 28 layers, n_embd 1024, n_ff 3072, **GQA 16/8, head_dim 128** (Q→2048, K/V→1024), **per-head QK-RMSNorm**, **untied** `output.weight`, SwiGLU, RoPE base 1e6, rms_eps 1e-6, vocab 151936, GPT2-BPE.

## Next session — pick up first (2-CPU.B forward pass)

Model layer (`qwen3_load` + dequant) is in place and MODEL_BIND-green. Two tracks:

1. **Clean logit oracle first** — the E_CPU_2 gate depends on it and all local llama.cpp are contaminated (see Prerequisites). Build upstream llama.cpp out-of-tree, or stand up HF `transformers` for `Qwen/Qwen3-0.6B`. Produce reference logits for a fixed token-ID sequence (skip our tokenizer; feed the same IDs both sides). Dump to a file the engine test reads.
2. **Forward pass (f32 reference path)** producing logits for a token-ID sequence:
   embed → per layer { RMSNorm(attn_norm) → Q/K/V proj → **per-head QK-RMSNorm** (over head_dim, BEFORE RoPE) → RoPE (base 1e6) → GQA attention (16 q-heads / 8 kv-heads, group 2; causal; fp32 softmax) → O proj → residual → RMSNorm(ffn_norm) → SwiGLU(gate,up)→down → residual } → RMSNorm(output_norm) → LM head (`output.weight`).
   - ggml weight layout: tensor `[ne0=in, ne1=out]`, element (out_j,in_i) at `in_i + out_j*ne0` ⇒ `y[j]=Σ_i W[i+j*in]·x[i]`. Dequant via `sp_dequant_row`; f32 path first.
   - **Bug hotspots only the oracle catches:** RoPE convention (NEOX vs GPT-J interleave), QK-norm placement, GQA q→kv head mapping, causal masking, the weight layout above.
   - E_CPU_2 acceptance: max-token logit diff ≤ 1e-4 abs / ≤ 0.1% rel on the first 256 tokens.
3. Then **2-CPU.C** Frobenius-Q8 matmul (`sp_frob_*`) → E_CPU_3; **2-CPU.D** AVX2/512; **2-CPU.E** NTT-attention (sieve OFF, `sp_pr_*`) within T_PR_2; **2-CPU.F** KSTE KV behind `SP_KSTE_KV=1`. **T_FRO_4** (Gemma3-1B PPL, `d:\Files\models\Mine\gemma-3-1b-it\gemma-3-1b-it-f16\`) once the forward pass exists.
   - Qwen GPT2-BPE **tokenizer** (vocab+merges in the GGUF `tokenizer.ggml.*` arrays) needed for real prompts/PPL; build when generation/PPL is required (E_CPU_2 can use raw token IDs).

## Open / notes

- The engine build also builds + registers the math-core unit tests (T_OK..T_KSTE) because `sp_add_module` always creates the test exe regardless of `SP_SYSTEM_BUILD_TESTS`. Harmless (they pass, ~2s) but bloats the engine build. Optional later: gate test creation in `sp_module.cmake` without breaking standalone module builds.
- Forward pass is large and sequential (loader → tensors → per-op → full pass); not cleanly parallel within the backend. Parallelism in Phase 2 is across backends/models, not within one bring-up.
