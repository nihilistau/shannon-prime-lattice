---
type: session-handoff
title: SESSION-CLOSED-lat-2-CPU
description: "Phase: 2-CPU — engine, CPU backend (shannon-prime-system-engine)."
tags: [session-handoff, cpu]
timestamp: 2026-05-22T11:52:17Z
resource: shannon-prime-lattice/papers/SESSION-CLOSED-lat-2-CPU.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# SESSION-CLOSED-lat-2-CPU

**Phase:** 2-CPU — engine, CPU backend (`shannon-prime-system-engine`).
**Session date:** 2026-05-21, extended 2026-05-22.
**Status:** **Phase 2-CPU FULLY CLOSED 2026-05-22 — `lat-phase-2-cpu-fro4-closed`.** The six E-tests closed first (`lat-phase-2-closed`): E_CPU_1 loader, E_CPU_2 forward (distributional gate), E_CPU_3 Frobenius/Q8, E_CPU_4 AVX2, E_CPU_5 NTT-attention (meets literal T_PR_2), E_CPU_6 KSTE KV. Then the foundational-compression + load-bearing layout (E_CPU_7..10, Spinor KV, COMPOSE, math-core port), Gemma3-1B SP1 (forward), SP2 (SentencePiece tokenizer), and **SP3 / T_FRO_4** (the §8.2 closure clause). Full CPU regression **20/20 green incl. T_FRO_4 (SLOW)**. Engine commits through `3431cf8`, pushed. Remaining for full Phase 2: the other backends (2-CU/VK/HX, §8.3–8.5).

> **NEXT SESSION PICKS UP HERE → Phase 2-CU (CUDA backend, §8.3).** SP1/SP2/SP3 and T_FRO_4 are all **DONE 2026-05-22**. The CPU track is the canonical anchor; 2-CU kernels read the math-core packed formats directly (`sp_frob_packed_tensor`, `SP_FROB_ARENA_LAYOUT_VERSION=1`, per-row Frobenius; Spinor KV 63 B, `SP_SPINOR_LAYOUT_VERSION=1`). Host reality: **CUDA 13.2 + RTX 2060 sm_75** (not the old 12.4 pin); `env-cuda.bat`→13.2 (+ likely the ASCII/goto fix the CPU env scripts got). Output gate: vs CPU within 1e-3 rel.

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

## Post-close additions (2026-05-22, after the Phase 2-CPU tag)

The CPU engine now generates readable text end-to-end (Qwen3-0.6B):

- **Generation loop** `qwen3_generate` (`src/forward/generate.c`, commit 82489dc) — greedy, reuses the validated `qwen3_forward` per step (recompute-the-prefix, O(n²), correct by construction). Test **GEN_QWEN3**. A persistent-KV-cache decode (O(n)) is the optimization to add next, validated for token-identity against this.
- **Tokenizer — DECODE side** (`src/tokenizer/tokenizer.c`, `include/sp_engine/tokenizer.h`, commit 283d9e0) + GGUF `gguf_kv_str_array` helper. GPT2 byte-level inverse decode of `tokenizer.ggml.tokens`. Test **TOK_DECODE** decodes ref.bin's IDs back to the exact oracle prompt; greedy continuation reads as English.

### 2026-05-22 — Tokenizer ENCODE side closed (TOK_ENCODE)

- **`sp_tokenizer_encode`** (`src/tokenizer/tokenizer.c`, decl in `include/sp_engine/tokenizer.h`): full Qwen2 byte-level BPE — (1) special-token pre-split (token_type CONTROL/USER_DEFINED surfaces, longest-match-first), (2) the **Qwen2 pre-tokenizer regex hand-coded** as a 7-alternative ordered-alternation splitter (incl. the `\s+(?!\S)` whitespace backtrack), (3) GPT2 byte-level encode, (4) greedy lowest-rank BPE over `tokenizer.ggml.merges`, (5) token→id. Two open-addressing hashmaps (vocab string→id, merge "A B"→rank).
- **Unicode classes** (`\p{L}`/`\p{N}`/`\s`): `src/tokenizer/unicode_ranges.h`, **generated** by `tools/oracle/gen_unicode_tables.py` from Python `unicodedata` + the `regex` module (self-derived, NOT copied from llama.cpp; 648/134/10 sorted ranges, binary-searched). Residual risk: Python's UCD/`\s` may diverge from llama.cpp's tables at exotic codepoints — documented, not yet observed.
- **Validation = byte-for-byte parity with stock llama.cpp.** Algorithm first proven in `tools/oracle/bpe_proto.py` (committed parity oracle), then ported. **TOK_ENCODE** (`tests/test_tokenizer.c`): (a) `encode(REF_PROMPT)` == ref.bin's exact **31 IDs**; (b) `decode(encode())` round-trips; (c) 4 parity cases dumped from the oracle — **ml** (CJK + accented Latin + Devanagari combining marks, 23 IDs), **digits** (Qwen2 single-digit split), **ws** (whitespace backtrack), **specials** (`<|im_start|>`…). 22 checks, 0 fails. Full CPU suite **10/10 green** (MSVC/Ninja).
- **Oracle fix:** `tools/oracle/dump_logits.cpp` now accepts `@file` to read the prompt from a UTF-8 file — Windows `argv` mangles multibyte UTF-8 into mojibake (this corrupted the first multilingual probe). New helpers: `gguf_peek.py`, `gen_encode_fixture.py` (see `tools/oracle/README.md`).

### 2026-05-22 — Foundational compression stack: Q4 weights, VHT2 KV, O(n) decode

Contract amended first (roadmap **§8.2.1**, dated block): added E_CPU_7/E_CPU_8/GEN_KV as explicit Phase-2-CPU gates (the §4.8/§4.9 "foundational" compression that the original six items only partly covered — E_CPU_3 was Q8 weights, E_CPU_6 was the *KSTE sieve* overlay, neither is Q4 nor the VHT2 KV codec). All gates default OFF (regression invariant holds). All quality measured vs the engine's **pure-f32** path (§8.6.1), on Qwen3-0.6B.

- **E_CPU_7 — Q4 inline weight compression** (`SP_ENGINE_FROB=3` inline / `=4` dequant-ref; `src/forward/forward.c` `matmul`). Symmetric 4-bit codes `[-7,7]` packed two-per-byte (`q4_pack`/`q4_unpack`), per-row scale, dequant `q·s/7`. **Mixed precision:** per-row weight-only sensitivity (rel-L2 of the Q4 round-trip) promotes high-error rows to Q8 — threshold `SP_Q4_PROMOTE` (default 0.25). **v1 calibration is weight-only; activation-based calibration is the Phase-4 refinement** (roadmap §4.4/§7.5), promotion-mask hook left in place. **Measured:** lift |Δ|max 1.37e-4 (inline==dequant), 2.9% rows promoted, Q4-vs-f32 KL mean 0.72 / argmax 17/31 (lossy by design — real quality is T_FRO_4). `qwen3_q4_stats()` reports the promotion rate. **NOTE:** the Q4 quant/pack primitive should migrate into `core/frobenius` next to Q8 so CUDA/VK/HX share it (kept engine-local this push to stay in one repo).
- **E_CPU_8 — Inline VHT2+Spinor KV compression** (`SP_KV_SPINOR=1`; `kv_spinor_roundtrip`). Each post-norm/post-RoPE K and post-proj V head vector (head_dim=128) → ⌈128/55⌉=3 frozen 63-byte Spinor blocks (balanced 43/43/42; **frozen layout untouched**), decoded back lossily before attention reads it. Gate OFF ⇒ bit-identical. **Measured:** KL mean 2.18e-2 / argmax 29/31 (much gentler than Q4). Distinct from E_CPU_6 KSTE.
- **GEN_KV — persistent-KV O(n) decode** (`qwen3_generate_kv`, `src/forward/forward.c`). Position-indexed K/V cache, stores K/V **post-RoPE**, weight matmuls run once per token (O(n)) vs `qwen3_generate`'s re-prefill (O(n²)). Honors FROB/SCALAR/KV_SPINOR. Gate = **sequence (argmax) identity** vs the O(n²) ref under `SP_CPU_SCALAR=1` (not bit-equal logits — different softmax-sum lengths hit the reassoc floor). **24/24 generated tokens identical.**

Env reads factored into `read_env_knobs()` (shared by prefill + decode). Engine knobs still all default OFF. GEN_KV token count is `SP_GEN_KV_N` (default 8 to keep the O(n²) reference cheap; =24 for thorough).

**Composability — DONE (2026-05-22, Piece 3).** The all-gates-on smoke now exists: **COMPOSE** (`tests/test_compose.c`) runs `SP_ARENA=q8` + `SP_KV_SPINOR=1` + `qwen3_generate_kv` together and asserts the arena weight source and the Spinor-block KV layout are orthogonal (block KV == f32 KV with the arena active). See the Piece 2+3 dated block below.

### 2026-05-22 — Q4→core migration + load-bearing layout (Piece 1a: packed-weight arena)

User direction: do the **core load-bearing** layout before CUDA. CUDA deferred.

- **Q4 codec migrated to `core/frobenius`** (math-core commit 7907421, T_FRO_Q4; submodule bumped 562e819→7907421). `sp_frob_quant1_q4 / dequant1_q4 / q4_pack / q4_unpack / q4_row_relerr / q4_packed_bytes`, `SP_FROB_QMAX4`. Engine matmul now calls the shared primitives (engine-local q4 helpers removed); behavior byte-identical (E_CPU_7 unchanged). So all backends share one Q4 impl.
- **E_CPU_9 — packed-weight arena (Piece 1a)** (`include/sp_engine/arena.h`, `src/forward/arena.c`; engine commit 7994803). `SP_ARENA=q8|q4` (default off): at load, quantize the matmul weights once into a per-row Frobenius Q8/Q4 packed arena; `matmul` lifts inline from the codes (no per-call re-quant). **Versioned in-memory layout `SP_ARENA_LAYOUT_VERSION=1` = the byte format the GPU backends will read** (per-ROW Frobenius, NOT ggml per-32-block Q8_0). **Tight gate:** `SP_ARENA=q8` forward byte-identical to `SP_ENGINE_FROB=1`, `q4` to `=3`. Measured: Q8 arena 574.5 MB, Q4 300.7 MB (2.85% rows promoted). Scope 1a: matmul weights only (attn q/k/v/o, ffn gate/up/down, LM-head output); embedding+norms stay f32 from the still-held mapping. Full CPU regression **14/14**.

**Piece 1b DONE — F16 source release (E_CPU_10)** (engine commit dda10a0). `SP_ARENA_EMBED=1` folds the embedding into the arena; `qwen3_release_source()` copies norms→owned f32 and `gguf_release_data()` unmaps the GGUF data (keeps parsed tensor/kv structs; `gguf_tensor_data` returns NULL after). Forward then reads only arena + owned norms → peak mem ~1.5 GB f16 → ~574 MB Q8. `SP_ARENA_RELEASE=1` = do it at load. **Tokenizer owning** `sp_tokenizer_load_ex(g,1)` copies vocab+merges (survives unmap); `sp_tokenizer_load` still borrows. Gate: forward-after-release **byte-identical to held** (catches dangling ptrs) + data NULL post-release + owning tokenizer decodes. CPU regression **15/15**. **NOTE (2026-05-22):** `dda10a0` committed the E_CPU_10 callers/headers/tests but left the matching *definitions* (`arena.h` `include_embed`+`sp_arena_dequant_row` decl; `tokenizer.c` `sp_tokenizer_load_ex` def) uncommitted in the working tree, so HEAD-as-committed was internally inconsistent / non-compiling. Completed in **`6fab400`** (no behavior change; the 15/15 always lived in the working tree).

### 2026-05-22 — Piece 2 + Piece 3: persistent Spinor KV cache + composability/format-lock (engine `983a493`)

The load-bearing layout is now **solid** — full CPU regression **16/16 green** (adds COMPOSE; GEN_KV also runs GEN_KV_SPINOR), MSVC `/W4` clean.

- **Piece 2 — persistent Spinor KV cache (the §4.9 production KV layout).** `qwen3_generate_kv` with `SP_KV_SPINOR=1` stores the cache as `sp_spinor_block_t[]` (NBLK = ceil(head_dim/55) = 3 for Qwen3) and decodes on read into a per-LAYER f32 scratch — resident KV = packed blocks + one layer of scratch, not the full f32 cache. `decode(encode(x))` equals the in-place round-trip, so the block cache is **sequence-identical** to the f32 round-trip parity reference, now selectable via **`SP_KV_SPINOR_REF=1`** (the §4.9 "fp32 cache for parity tests only"). Gate off ⇒ unchanged f32 path (regression invariant). **Measured drop: 2.71×** (block 2.96 MB vs f32 8.03 MB, P=44) — honest figure for the **frozen** 63-byte/55-anchor block at head_dim=128 (512 B → 189 B/head). The roadmap's "~6×" was aspirational; a larger ratio needs a block change ⇒ `SP_SPINOR_LAYOUT_VERSION` bump. **Gate `GEN_KV_SPINOR`** (`tests/test_gen_kv.c`) asserts block == f32-round-trip sequence identity.
- **Piece 3 — composability + format-lock.** **`COMPOSE`** (`tests/test_compose.c`): with the arena active (`SP_ARENA=q8`), block KV still == f32 KV ⇒ weight source and KV layout are orthogonal, all three gates compose. **Format-lock** = file-scope `_Static_assert`s freezing the cross-backend byte contract. Silent layout drift is now a compile error.

### 2026-05-22 — Piece 4: ported the load-bearing primitives into the math core (math-core `9a4e0ea`, engine `b00fbf1`)

User direction: *"did you build the load-bearing stuff into math core or the engine? it needs to be ported to mathcore… we need more loadbearing stuff in mathcore before we start cu-2."* The arena format + KV head split were engine-local (`src/forward/{arena,forward}.c`) — but they are **cross-backend byte contracts** (every backend reads the same bytes), so they belong in `shannon-prime-system` where CUDA/VK/HX share one impl. Ported, behavior **byte-identical**, CPU regression **16/16** unchanged.

- **`core/frobenius` (math-core `9a4e0ea`):** `sp_frob_packed_tensor` (mixed-precision per-row Q8/Q4 — the §4.8 arena layout) + `sp_frob_pack_tensor(rows,cols,prec,promote,get_row_cb,ctx,out,*promoted)` (a **row-reader callback** keeps GGUF dequant engine-side, no full-tensor f32 spike) + `sp_frob_packed_dequant_row` + `sp_frob_packed_free` + `sp_frob_packed_tensor_bytes` + **`SP_FROB_ARENA_LAYOUT_VERSION`** (single source of truth; the engine's duplicate `SP_ARENA_LAYOUT_VERSION` was deleted). Gate **`T_FRO_5`**.
- **`core/vht2` (same commit):** `sp_spinor_blocks_for` (ceil(k/55)) + `sp_spinor_encode_vec` / `sp_spinor_decode_vec` (the frozen 43/43/42 head split). Gate **`T_VHT_7`** — encode_vec/decode_vec are byte-identical to an explicit per-chunk encode/decode of the split. Math-core regression **6/6**, `-Wsign-conversion` clean.
- **Engine (`b00fbf1`):** submodule bump `7907421→9a4e0ea`; `sp_arena_tensor` = `{ name, sp_frob_packed_tensor }`; `build_tensor` is a thin GGUF-row callback over `sp_frob_pack_tensor`; `forward.c` KV codec calls the math-core `sp_spinor_*_vec`; `matmul_arena` reads through `at->pt`. Net −75 LOC (duplicate code removed). The format-lock `_Static_assert`s now reference `SP_FROB_ARENA_LAYOUT_VERSION`.

### 2026-05-22 — SP1→SP3 + T_FRO_4 closed; roadmap §8 truncation repaired

- **Gemma3-1B SP1 (forward).** 2nd architecture: loader + `GEMMA3_BIND`, `gemma3_forward` (embed ×√1152, plain RMSNorm — the `(1+w)` is baked into the GGUF, do NOT add 1 — QK-norm before RoPE, dual RoPE global 1e6 / local 10000 with global on `L%6==5`, sandwich residuals, GeGLU gelu-tanh, tied head), `kernels_attn_head` windowed GQA. **`M_GEMMA3_CPU`** distributionally matches the oracle (argmax 6/6, top5 6/6, KL 1.65e-6). Engine `8aba0e2`→`0aedcb9`+`8cacfce`.
- **SP2 — SentencePiece tokenizer** (`SPM_ENCODE`, engine `41c5e19`). SPM "llama" path added to `tokenizer.c` (model-type aware; the GPT2-BPE path stays byte-identical/untouched): greedy bigram-merge by unigram score via max-heap, byte-fallback `<0xXX>`, whitespace→U+2581, `add_space_prefix=0`, BOS auto-prepend. Parity vs stock llama.cpp on 5 fixtures (`tests/fixtures/spm/`).
- **SP3 — PPL loop + T_FRO_4** (engine `3431cf8`). `sp_perplexity` follows perplexity.cpp (non-overlapping n_ctx chunks, per-chunk BOS, score `[n_ctx/2, n_ctx-1)`, PPL=exp(mean NLL)). **T_FRO_4 split gate** (`tests/test_ppl.c`): **(a)** engine-f32 PPL vs the f16 oracle **−0.0146%** (≤0.05% — the real forward-correctness check); **(b)** per-row Q8 arena drift vs engine-f32 **−0.74%** (≤2%; per-row Q8 is ~1% lossy by design, so the old single 0.1% target was never right for it). Q8 pass via `SP_ARENA=q8` (byte-identical to `SP_ENGINE_FROB=1`, quantised once at load); f32 pass clears matmul knobs first. Oracle: `dump_logits` + `ppl_from_logits.py` on `wiki.tiny.raw` (168 tok, n_ctx=168 single window); 176 MB `.ref.bin` gitignored. **20/20 green incl. T_FRO_4.**
- **Roadmap repair.** The Three-Gap-integration commit (lattice `6fba9e2`) had truncated `PPT-LAT-Roadmap.md` §8.2 body → §9 + Phase log (1278→914 lines). Restored §8.2–§9 + Phase log from `623b26e`, kept the polynomial-shift reframe (§8.1, §20), added the T_FRO_4 split-gate closure clause to §8.2 + a §8.6.1 back-ref, and repointed the stale §6 T4 / §7.5 "0.1%" wording at it.

**Load-bearing plan (remaining, dependency-ordered):**

1. **T_FRO_4 — DONE 2026-05-22** (SP3 `3431cf8`; split gate, see above). Model at `D:\Files\Models\Mine\gemma-3-1b-it\gemma-3-1b-it-f16\gemma-3-1b-it-f16.gguf` (`gemma-3-1b-it-f16` is a *subdir* holding the f16 GGUF); quantized variants are sibling subdirs; the **SentencePiece** `tokenizer.model` + configs live at the `gemma-3-1b-it\` root. The arena is the production layout this validated.
2. **2-CU** (§8.3) — now unblocked (load-bearing layout solid, and the primitives that realize it are in the math core for all backends to share). Host reality: **CUDA 13.2 + RTX 2060 sm_75** (not the old 12.4 pin); `env-cuda.bat`→13.2 (+ likely the ASCII/goto fix). The CUDA kernels read the math-core packed formats directly: the arena (`sp_frob_packed_tensor`, `SP_FROB_ARENA_LAYOUT_VERSION=1`, per-row Frobenius) and the Spinor KV block (63 B, `SP_SPINOR_LAYOUT_VERSION=1`; head split via `sp_spinor_blocks_for`).

## Closed subphases — 2-CPU.C–F (2026-05-22; commits 3e6ebee/1d033b4/9c65af7 + E_CPU_6)

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
