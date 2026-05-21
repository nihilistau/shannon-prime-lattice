# SESSION-STATE-lat-2-CPU

**Phase:** 2-CPU — engine, CPU backend (`shannon-prime-system-engine`).
**Session date:** 2026-05-21, extended 2026-05-22.
**Status:** **Phase 2-CPU CLOSED 2026-05-22 — all six E-tests green (engine ctest 7/7 incl. MODEL_BIND).** E_CPU_1 loader, E_CPU_2 forward (distributional gate), E_CPU_3 Frobenius/Q8, E_CPU_4 AVX2, E_CPU_5 NTT-attention (meets literal T_PR_2), E_CPU_6 KSTE KV. Per §8.6 this is the canonical-anchor close → tag `lat-phase-2-closed`. Remaining for full Phase 2: T_FRO_4 (Gemma3-1B PPL) and the other backends (2-CU/VK/HX).

---

## Done this session

- **Phase-2 entry:** added `lib/shannon-prime-system` submodule (pinned at the all-tiers-green math-core HEAD). Engine root CMake builds the submodule's `sp_*` libs (tests off) and links `sp_frobenius/ntt_crt/poly_ring/kste/vht2`.
- **2-CPU.A — GGUF loader** (`include/sp_engine/gguf.h`, `src/loader/gguf.c`): GGUF v3, cross-platform mmap (Win32 `CreateFileMapping` / POSIX `mmap`), bounds-checked cursor parse of header + metadata KVs + tensor table, per-`ggml_type` block-size validation, every tensor checked in-bounds + aligned. Typed scalar/string metadata getters. **E_CPU_1 green** (`tests/test_loader.c`): parses `Qwen3-0.6B-f16.gguf` → arch=qwen3, 311 tensors, 34 kv, 28 layers, 16 heads, dim 1024; header round-trips. 15 checks, 0 fails, MSVC `/W4` clean.
- **2-CPU.B step 1 — model layer** (`include/sp_engine/model.h`, `src/forward/model.c`): `qwen3_load` reads the config from GGUF metadata and binds every weight tensor per layer; `sp_f16_to_f32` + `sp_dequant_row` (F32/F16/Q8_0). **MODEL_BIND green** (`tests/test_model.c`, 20 checks): config matches the known arch, all 28 layers bound, every tensor shape consistent, embedding dequant finite. Qwen3-0.6B config locked in code: 28 layers, n_embd 1024, n_ff 3072, **GQA 16/8, head_dim 128** (Q proj→2048, K/V→1024), **per-head QK-RMSNorm** (`attn_q_norm`/`attn_k_norm` [128]), untied `output.weight`, SwiGLU, rope_base 1e6, rms_eps 1e-6, vocab 151936, GPT2-BPE tokenizer.
- **Build-env fix:** `scripts/env/env-common.bat` + `env-cpu.bat` were broken on first real use — UTF-8 box-drawing/em-dash chars broke cmd parsing, and the `(x86)` VS path breaks parenthesised `if`-blocks. Rewrote both in ASCII with `goto`-based error handling. (Per prompt.md the pinned env scripts are fixed when they error.) `env-cuda/vulkan/hexagon.bat` likely have the same two bugs — fix them the same way when those backends come up.

### 2026-05-22 — 2-CPU.B forward pass + E_CPU_2 closed

- **Forward pass** (`src/forward/forward.c`): embed → per layer { RMSNorm → Q/K/V matmul → per-head QK-RMSNorm → NEOX RoPE → GQA causal fp32-softmax attention → O proj → residual → RMSNorm → SwiGLU → residual } → final RMSNorm → LM head. Dequant-on-demand (F32/F16/Q8_0). `SP_ENGINE_F16_ACT=1` = optional ggml-faithful precision mode (rounds matmul activations to F16).
- **The 1e-4/0.1% per-logit gate was wrong** — a scalar f32 pass can't bit-match ggml because **per-head QK-RMSNorm amplifies the ~1e-6 F16-matmul-precision floor 39×(Q)/477×(K)**, compounding over 28 layers to ~1–2% worst-case per-logit (argmax still exact). Full evidence chain in roadmap **§8.6.1** and memory `reference-ecpu2-qknorm-precision-gate`. Proven via isolation harnesses (below), and via f32-acc≈f64-acc (~1e-4) while both differ from ggml ~100× more.
- **New gate (§8.2/§8.6.1):** argmax + top-5 cross + mean `KL(ggml‖engine) < 1e-5` nats on the **pure-f32** path. Measured KL mean **2.347e-6**, argmax 31/31, top5 31/31. `tests/test_forward.c` rewritten (top5/kl_div helpers; `SP_KL_MAX` override). E_CPU_2 reads `ref.bin` (committed fixture, regenerate via oracle).
- **Oracle harness suite** (`tools/oracle/`, all link the clean llama.cpp at [[reference-llama-oracle]]): `dump_logits` (logits, now takes optional n_threads arg), `dump_layers` (per-tensor checkpoints via sched eval callback: attn_norm/ffn_inp/l_out/Qcur/Kcur/Vcur/Qcur_normed/Kcur_normed/kqv/result_norm), `rope_check` (RoPE vs `ggml_rope_ext`), `attn_check` (runs engine's GQA core on ggml's Q/K/V vs ggml's kqv). Oracle uses **f32 KV cache + flash-attn disabled** for apples-to-apples.
- **Decisive findings:** matmul projection F16-exact (Vcur 1.3e-6); RoPE ≤2e-6 (linear); attention core 1e-6 on ggml's Q/K/V; QK-norm is the sole amplifier (post-norm == post-rope residual confirms RoPE adds nothing). **No logic bug.**

## Build + run (CPU backend)

```bat
scripts\build\build-cpu.bat            REM vcvars64 (VS2019 BT) + cmake -G Ninja into build-cpu\, then build
ctest --test-dir build-cpu -R E_CPU --output-on-failure
```
Engine tests use the math-core `sp/sp_test.h` harness (via the submodule). Reference model path is a CMake cache var `SP_QWEN3_GGUF` (default `D:/Files/models/Qwen/Qwen3-0.6B-GGUF/Qwen3-0.6B-f16.gguf`).

## Prerequisites in place

- **Model:** `Qwen3-0.6B-f16.gguf` (1.5G) + `Qwen3-0.6B-Q8_0.gguf` (768M) from `ggml-org/Qwen3-0.6B-GGUF` (llama.cpp org) at `d:\Files\models\Qwen\Qwen3-0.6B-GGUF\`. f16 = unquantized source for the Frobenius-Q8 path + the higher-precision oracle run.
- **Oracle (DONE):** clean stock llama.cpp cloned + built at `D:\F\shannon-prime-repos\shannon-prime-lattice-llama` (CPU-only, gcc/Ninja; its own git repo, not committed into ours). Oracle tool `shannon-prime-system-engine/tools/oracle/dump_logits.{cpp,sh}` (self-contained MinGW exe) tokenizes a prompt with the stock tokenizer and dumps token IDs + per-position logits — verified on Qwen3-0.6B-f16 (5 tok × 151936). File format in `tools/oracle/README.md`. (The local `llama-cpp-*` checkouts — incl. the misnamed "cleanroom" — are all contaminated with `shannon_prime_*` libs and must NOT be used.)
- Qwen3-0.6B arch (now locked in `model.c`): 28 layers, n_embd 1024, n_ff 3072, **GQA 16/8, head_dim 128** (Q→2048, K/V→1024), **per-head QK-RMSNorm**, **untied** `output.weight`, SwiGLU, RoPE base 1e6, rms_eps 1e-6, vocab 151936, GPT2-BPE.

## Next session — pick up first (2-CPU.C Frobenius/Q8)

E_CPU_1, MODEL_BIND, E_CPU_2 are green. Remaining subphases:

**2-CPU.C–F all closed 2026-05-22** (commits 3e6ebee/1d033b4/9c65af7 + E_CPU_6):

- **E_CPU_3** Frobenius/Q8 (`SP_ENGINE_FROB`): inline-lift==dequant-ref (1e-4); Q8-vs-f32 KL ~2e-2 (per-row Q8 lossy by design, argmax reported not gated).
- **E_CPU_4** AVX2 (`dot_f32`, `/arch:AVX2`; `SP_CPU_SCALAR=1` forces scalar): argmax 31/31, |Δ| 1.7e-4 (reassoc floor, not 1e-6 — §8.6.1).
- **E_CPU_5** NTT-attention (`SP_ENGINE_NTT_ATTN`, exact `sp_pr_inner`, int32 scale 2^16): KL 2.7e-10 ≤ 1e-7 (literal T_PR_2).
- **E_CPU_6** KSTE KV (`qwen3_forward_ex` + `kv_trees`, gate `SP_KSTE_KV=1`): 6944 signatures deterministic + wire-valid.

Engine env knobs all default OFF (pure-f32 reference): `SP_ENGINE_F16_ACT`, `SP_ENGINE_FROB={1,2}`, `SP_CPU_SCALAR`, `SP_ENGINE_NTT_ATTN`, plus build-time `SP_ENGINE_WITH_AVX2/AVX512`.

**Truly next (not blocking the CPU close):** **T_FRO_4** (Gemma3-1B PPL, `d:\Files\models\Mine\gemma-3-1b-it\gemma-3-1b-it-f16\`) — needs a real tokenizer (Qwen/Gemma GPT2-BPE: vocab+merges in GGUF `tokenizer.ggml.*`; the E-tests use raw token IDs from `ref.bin`, no tokenizer). Then other backends **2-CU/VK/HX** (§8.3–8.5) mirror the CPU set, output vs CPU within 1e-3 rel.

### Forward-pass reference

embed → per layer { RMSNorm(attn_norm) → Q/K/V proj → per-head QK-RMSNorm (over head_dim, BEFORE RoPE) → NEOX RoPE (base 1e6) → GQA attention (16 q / 8 kv, group 2; causal; fp32 softmax; scale 1/√128) → O proj → residual → RMSNorm(ffn_norm) → SwiGLU → residual } → RMSNorm(output_norm) → LM head. ggml weight layout `[ne0=in, ne1=out]`, `y[j]=Σ_i W[i+j*in]·x[i]`, dequant via `sp_dequant_row`. Oracle harness: `tools/oracle/{dump_logits,dump_layers,rope_check,attn_check}` (link clean llama.cpp, f32 KV + flash-attn off).

## Open / notes

- The engine build also builds + registers the math-core unit tests (T_OK..T_KSTE) because `sp_add_module` always creates the test exe regardless of `SP_SYSTEM_BUILD_TESTS`. Harmless (they pass, ~2s) but bloats the engine build. Optional later: gate test creation in `sp_module.cmake` without breaking standalone module builds.
- Forward pass is large and sequential (loader → tensors → per-op → full pass); not cleanly parallel within the backend. Parallelism in Phase 2 is across backends/models, not within one bring-up.
