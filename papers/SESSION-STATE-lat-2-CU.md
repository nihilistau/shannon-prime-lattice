# SESSION-STATE-lat-2-CU

**Phase:** 2-CU — engine, CUDA backend (`shannon-prime-system-engine`).
**Session date:** 2026-05-22.
**Status:** **CLOSED 2026-05-23 — `lat-phase-2-cu-fro4-closed`.** T_FRO_4 split
gate GREEN on CUDA (Gemma3-1B): gate (a) cuda-f32 −0.0146% vs f16 oracle; gate (b)
per-row Q8 arena drift −0.7354%. Tags pushed: engine @ `9de1fb9`, system @
`eca1bdc`. Dispatch verified actually firing on CUDA (probe, then removed).
Backend: CUDA 13.2 + sm_75 (RTX 2060) + VS2019 BT + Ninja.

**Follow-up notes (not blocking the close):**
- **Q4 device path compiled but UNEXERCISED.** `k_dequant_arena`'s `row_prec!=8`
  (Q4 nibble) branch is correct-by-construction but T_FRO_4 only uses Q8. A future
  **E_CU_7** should add a `SP_ARENA=q4` scenario to M_GEMMA3_CUDA.
- **`.gitignore` fix is forward-only:** the CPU close tag `lat-phase-2-cpu-fro4-closed`
  (engine `3431cf8`) predates the fix, so a fresh clone at that tag has NO build
  scripts (they were ignored). `lat-phase-2-cu-fro4-closed` onward is buildable.
- **This SESSION-STATE lives in the read-only lattice repo** (per the 2-CU brief,
  lattice is read-only for the CU agent). It is written to disk but NOT committed by
  this session — the user/orchestrator commits lattice (the CPU agent's
  SESSION-CLOSED-lat-2-CPU.md is committed there, so likely they want this too).
- **E_CU_1..6 / GEN_CU on Qwen3-0.6B** (the full §8.3 contract) are NOT done — only
  the T_FRO_4 (Gemma3-1B) exit the brief specified. The same CUDA kernels would
  serve Qwen3 (untied head + per-head QK-norm already handled), but that arch hasn't
  been wired to `gemma3_forward_cuda`/a `qwen3_forward_cuda` yet.

Parallels `SESSION-CLOSED-lat-2-CPU.md` (the canonical CPU anchor). The CPU
track closed T_FRO_4 at f32 −0.0146% vs the f16 oracle and per-row Q8 −0.74%.

---

## Ground truth established this session (host probe, not the brief)

- **GPU: NVIDIA GeForce RTX 2060 → sm_75 (Turing).** NOT sm_86/sm_89. The Phase
  2-CU brief's "sm_86/sm_89" premise is factually wrong for this host.
- **CUDA toolkits installed:** 12.1, 12.4, 13.0, 13.1, 13.2. PATH `nvcc` = 13.2,
  driver = 13.2. **User directive: use 13.2.** Matches roadmap §8.3 (already
  amended to "CUDA 13.2 + sm_75") and `reference_cuda_build_recipe` (sm_75 default).
  `prompt.md`'s build table still says "CUDA 12.4 / sm_86/sm_89" — STALE; overridden.
- **VS: 2019 BuildTools only** (no full VS). Matches the pin.
- **Toolchain probe GREEN:** `nvcc 13.2 -arch=sm_75` compiles a `.cu` with the
  VS2019 host `cl.exe` and the exe runs on the RTX 2060 (`devices=1 sm=7.5`).
  The highest-risk gate (13.2 ↔ VS2019 host-compiler compat) passes.
- **`--use-local-env` is required** in `CMAKE_CUDA_FLAGS` on this box: with only
  VS2019 BuildTools (no registry full-VS install), nvcc's internal vcvars lookup
  fails ("Could not set up the environment for Microsoft Visual Studio") unless
  nvcc inherits the parent vcvars64 shell env. (From `reference_cuda_build_recipe`,
  which is from the OLD contaminated engine repo — toolchain knowledge only, NO code.)

## Scope decision (recorded so the next agent doesn't re-litigate)

- **The L1 ABI surface (`sp_session` / `sp_prefill_chunk` / `sp_decode_step` /
  `sp_status` / `SP_ECUDA` / `sp_last_error`) is implemented NOWHERE in the engine.**
  Those strings appear only in `.bat`/`docs`. The CPU agent hit T_FRO_4 entirely
  through `gemma3_forward` + `sp_perplexity` with env-knob gating; it never built
  the ABI. The brief's "implement sp_prefill_chunk/sp_decode_step CUDA dispatch"
  language is aspirational — there is no CPU reference to be parity-tested against.
- **Decision: mirror the CPU.** CUDA dispatch hooks at the `gemma3_forward` /
  `matmul` level (a CUDA `forward_fn` selected when `SP_BACKEND=cuda`), validated
  by the same T_FRO_4 split gate. Building the full L1 ABI CUDA-only would be
  asymmetric (CPU lacks it) and is properly a Phase-2-driver task, not backend
  bring-up. The frozen ABI's `SP_ECUDA`/`sp_last_error` error contract IS honored
  inside the CUDA layer (every `cudaError_t`/`cublasStatus_t` wraps to a status +
  thread-local detail string), so the ABI lands cleanly when the driver is built.
- **`.sp-model` (Appendix B) is DEFERRED to Phase 2-FMT** (user directive
  2026-05-22; roadmap §10 @ lattice 7d817f3). 2-FMT is a backend-agnostic
  parallel sub-phase (separate agent) that builds `sp_model_load` (mmap zero-copy
  parser), `sp-transcode` (GGUF→.sp-model), and the §12.3 round-trip gate ONCE.
  **2-CU runs entirely on the GGUF + in-RAM Frobenius arena path.** When
  `lat-phase-2-cu-fro4-closed` is tagged, DO NOT read it as "Appendix B
  implemented" — the on-disk `.sp-model` format is NOT built by this phase. The
  in-RAM `sp_frob_packed_tensor` arena the CUDA kernels read is the runtime
  equivalent of the on-disk `OK_Q8`/`OK_Q4` dtypes, but no `.sp-model` file is
  read or written. (Roadmap §8.3/§8.4-§9/§20 are currently missing from a partial
  restore at 7fbf153; last-good §8.3 at 623b26e — restoration is another session.)
- **Memory-entry discrepancy:** the brief named memory entries at
  `~/.claude/projects/.../memory/` (empty dir). The real binding feedback entries
  live under `AppData/Roaming/Claude/local-agent-mode-sessions/.../memory/`
  (`feedback_engine_is_the_path`, `feedback_stop_blocking`,
  `feedback_no_cross_contamination`, `feedback_user_is_collaborator_not_pitcher`,
  `reference_cuda_build_recipe`, etc.) — read those.

## Plan (dependency-ordered; tracked in TaskCreate CU.0..CU.3)

1. **CU.0** — env-cuda.bat (ASCII/goto, 13.2, sm_75, --use-local-env) + build-cuda.bat;
   CMake wires `src/backends/cuda/` behind `SP_ENGINE_WITH_CUDA`; CUDA_SMOKE test.
2. **CU.1** — `gemma3_forward_cuda` f32: cuBLAS SGEMM (8 matmuls) + custom kernels
   (rmsnorm, rmsnorm_head, rope_neox, GQA windowed softmax, gelu_tanh, embed scale).
   Gate `M_GEMMA3_CUDA`: per-logit KL + top5 + argmax vs CPU f32, ≤1e-3 rel (§8.3).
3. **CU.2** — Q8 arena: upload `sp_frob_packed_tensor`, dequant kernel → f32 scratch
   → cuBLAS SGEMM (== CPU `SP_ENGINE_FROB=2` dequant-reference).
4. **CU.3** — T_FRO_4-CU split gate: (a) cuda-f32 vs cpu-f32/oracle ≤0.05%
   deterministic single stream; (b) per-row Q8 ≤2%. Tag both repos; closure entry.

## Progress log

### 2026-05-22 — CU.0 closed (toolchain + scaffold)
- `env-common.bat` CUDA pin 12.4→13.2; `env-cuda.bat` rewritten ASCII/goto, sm_75;
  `build-cuda.bat` adds `--use-local-env` (required: VS2019-BT-only nvcc VS lookup)
  + explicit `CMAKE_CUDA_COMPILER`.
- `src/CMakeLists.txt`: separate `sp_engine_cuda` STATIC lib (keeps engine /W4 +
  /arch:AVX2 off nvcc); `find_package(CUDAToolkit)`, links CUDA::cudart/cublas +
  sp_frobenius/sp_vht2; sp_engine PUBLIC-links it + defines `SP_ENGINE_WITH_CUDA`.
- New: `sp_status.h` (frozen ABI enum, Appendix A §7), `common/sp_error.c`
  (thread-local `sp_last_error` shared by all backends), `cuda_backend.h`,
  `backends/cuda/cuda_backend.cu` (device query + cudaError→SP_ECUDA wrap).
- Math-core C++ fix (submodule): `_Static_assert`→`#ifdef __cplusplus static_assert`
  guards in `kste.h`/`ntt_crt.h`/`spinor_block.h` so the C++ CUDA backend can
  include the C math core. Behavior-identical in C mode.
- **Toolchain probe GREEN; CUDA_SMOKE green** (device visible, sm_75). **CPU fast
  regression 19/19 still green** (regression invariant holds).
- **Repo fix:** `.gitignore` `build/` (unanchored) was matching `scripts/build/`,
  so the build scripts (build-cpu/cuda/vulkan/hexagon.bat) were NEVER tracked.
  Anchored to `/build/` etc.; `scripts/build/` now committed for the first time.

### 2026-05-22 — CU.1 closed (gemma3_forward_cuda f32 + M_GEMMA3_CUDA)
- `backends/cuda/cuda_gemma3.cu`: full Gemma3 f32 forward. cuBLAS SGEMM
  (OP_T/OP_N, lda=ldb=in, ldc=out — row-major y=X·Wᵀ) for the 8 matmuls; kernels
  `k_embed_scale`, `k_rmsnorm` (f64 accum, matches CPU), `k_rmsnorm_head`, `k_rope`
  (NEOX), `k_attn` (GQA causal/windowed softmax, dyn-shared scores, scalar f32 acc),
  `k_gelu_mul`, `k_add`. Single stream + CUBLAS_DEFAULT_MATH (sm_75 = true f32) ⇒
  deterministic. Weights dequant host-side (GGUF f16→f32) + uploaded once, cached by
  model pointer; `sp_cuda_model_release` hooked into `qwen3_free` (invalidates on
  pointer reuse). `ppl.c` routes gemma3 fwd to CUDA when `SP_BACKEND=cuda`.
- **M_GEMMA3_CUDA GREEN** (15-tok prompt, CPU-vs-CUDA): **argmax 15/15**,
  worst_rel **2.6e-5**, worst_abs 3.7e-5, **KL(cpu‖cuda) mean 4.35e-12 / max 1.5e-11**
  — far inside §8.3's 1e-3 (the QK-norm amplifier doesn't bite CPU-vs-CUDA: both
  honest f32). nvcc /W4-equivalent clean.
- Engine f32 forward path proven on CUDA. NEXT: CU.2 Q8 arena (upload
  `sp_frob_packed_tensor` + on-device dequant → SGEMM), then CU.3 T_FRO_4.

### 2026-05-23 — CU.2 closed (Q8/Q4 arena decode-on-demand on CUDA)
- `k_dequant_arena` device kernel decodes the per-row Frobenius packed format
  (`sp_frob_packed_tensor`: codes/row_off/row_scale/row_prec) to f32 — Q8 row
  `code*scale/127`, Q4 row two-per-byte sign-extended nibble `code*scale/7` —
  byte-equivalent to the CPU `matmul_arena` lift. `DevTensor` is f32-or-packed;
  packed weights decode into a reused scratch (max packed elem = E*FF) right
  before SGEMM (decode-on-demand, §4.8). Per-tensor dispatch: the 7 layer
  matmuls are Q8-packed (arena), the tied head/embedding + norms stay f32 (the
  arena doesn't pack a tied head in Phase 1a). `gemma3_forward_cuda` arena guard
  removed.
- **M_GEMMA3_CUDA q8 scenario GREEN** (CUDA device-decode vs CPU matmul_arena,
  same codes): argmax 15/15, worst_rel **4.6e-5**, KL(cpu‖cuda) mean **1.6e-11**.

### 2026-05-23 — CU.3 CLOSED: T_FRO_4 split gate GREEN on CUDA
`T_FRO_4_CU` ctest = `test_ppl` with `ENVIRONMENT SP_BACKEND=cuda` (auto-routes
the gemma3 forward through the CUDA backend via the ppl.c dispatch). Gemma3-1B,
wiki.tiny, single 168-tok window. Run inside the env-cuda shell (CUDA DLLs on PATH):
```
call scripts\env\env-cuda.bat && ctest --test-dir build-cuda -R T_FRO_4_CU
```
- **Gate (a) — forward correctness:** cuda-f32 PPL **32.86459** vs the stock
  llama.cpp f16 oracle **32.86939** → **−0.0146%** (gate ≤0.05%). Identical to the
  CPU-f32 rel-diff (the CUDA f32 forward matches CPU f32 to 5 sig figs;
  M_GEMMA3_CUDA KL(cpu‖cuda)=4.35e-12 corroborates). So cuda-f32 vs cpu-f32 drift
  ≈ 0% « 0.05%.
- **Gate (b) — per-row Q8 arena quality:** cuda-q8 PPL **32.62290** → drift
  **−0.7354%** vs cuda-f32 (gate ≤2%). Matches the CPU-q8 −0.74% — device decode
  is faithful.
- **Deterministic single stream + CUBLAS_DEFAULT_MATH (sm_75 = true f32).**

**PHASE 2-CU EXIT MET.** Tag `lat-phase-2-cu-fro4-closed` on engine + system.
NOTE: `.sp-model` (Appendix B) is NOT implemented by this phase — deferred to
Phase 2-FMT (see scope decision above). This close means the CUDA forward (f32 +
Q8/Q4 arena) hits T_FRO_4 on the GGUF + in-RAM Frobenius arena path, nothing more.

## Forward-pass reference (from gemma3.c — what CU.1 mirrors on GPU)

embed ×√n_embd → per layer { rmsnorm(attn_norm) → q/k/v matmul → per-head
QK-rmsnorm (over head_dim, before RoPE) → NEOX RoPE (global base 1e6 on L%6==5,
else local base 1e4, sliding window 512) → GQA causal/windowed softmax (scale
1/√head_dim) → o matmul → post_attn_norm → residual → rmsnorm(ffn_norm) → GeGLU
(gelu_tanh(gate·x)*(up·x)) → ffn_down → post_ffw_norm → residual } → rmsnorm
(output_norm) → tied LM head. ggml weight `[ne0=in, ne1=out]`, y[j]=Σ W[i+j*in]·x[i].
Gemma3-1B: 26 layers, n_embd 1152, n_ff 6912, head_dim 256, n_head 4, n_kv 1,
vocab 262144, rms_eps per GGUF.
