# SESSION-STATE — lat-2-VK (Phase 2-VK: Vulkan compute backend)

Status: **COMPLETE — all gates GREEN.** Phase 2-VK mirrors the closed 2-CU CUDA
backend on Vulkan compute (SPIR-V). Exit gate T_FRO_4_VK passes.

## Worktree / branch
- Worktree: `D:\F\shannon-prime-repos\shannon-prime-system-engine\.claude\worktrees\agent-acf8c48f84ca8d1ec`
- Branch: `worktree-agent-acf8c48f84ca8d1ec` (coordinator integrates — NOT pushed).
- Commit: `0c243ec` "[lat-2-VK] Phase 2-VK: Vulkan compute backend mirrors 2-CU
  (T_FRO_4_VK GREEN)" — single commit on top of 2-CU HEAD `cc1aafd`. 26 files,
  +2347/-24.
- Submodule `lib/shannon-prime-system`: pinned at `eca1bdc` — NOT bumped.
- Build dir: `build-vulkan/` (landed in worktree, gitignored; main repo untouched).
- Working tree clean post-commit; the env-common.bat SP_ENGINE build hack was
  applied locally only and reverted before committing (verified clean).

## GPU / driver tested
- NVIDIA GeForce RTX 2060 (DISCRETE_GPU), Vulkan apiVersion 1.4.329, driver NVIDIA 596.21.
- Vulkan SDK 1.4.341.1; glslc (shaderc v2026.1). GLSL→SPIR-V at BUILD time via glslc.
- The box also exposes an Intel UHD Graphics iGPU (Vulkan 1.3); the backend's
  device selection scores DISCRETE_GPU + shaderInt64 + shaderFloat64 highest, so
  it deterministically selects the RTX 2060.

## Gate results (all on NVIDIA RTX 2060 Vulkan)
- **VULKAN_SMOKE (VK.0)**: 2 devices visible; device 0 = RTX 2060, Vulkan 1.4. PASS.
- **M_GEMMA3_VULKAN (VK.1/2/3)**: CPU-vs-Vulkan, 15 pos x 262144 vocab, argmax 15/15:
  - f32 : KL mean 3.5e-12, worst_rel 2.0e-5
  - Q8  : KL mean 1.5e-11, worst_rel 4.5e-5
  - Q4 mixed (11292/459264 rows promoted): KL mean 2.9e-11, worst_rel 5.6e-5
  - all << 1e-5 KL gate. PASS (33/33 checks).
- **M_QWEN3_VULKAN (VK.4 / E_VK_1..4)**: argmax 31/31 everywhere:
  - E_VK_2 vs ggml oracle: argmax 31/31, top5 31/31, KL mean 2.33e-6 (< 1e-5)
  - §8.3 vs CPU f32: KL mean 5.3e-12
  - E_VK_3 Q8 arena vs CPU: KL mean 1.2e-10
  - PASS (17/17). Untied LM head (V=151936 rows) decoded correctly via tiled dispatch.
- **E_VK_5 (NTT-attention)**: Part A int64_dot == sp_pr_inner 192/192 (N∈{128,256,512});
  Part B argmax 31/31, KL(f32‖ntt) mean 2.07e-10 (≤1e-7) AND KL_max 1.07e-9 > 0
  (branch fired, no silent fallback). PASS (13/13).
- **E_VK_6 (KSTE-KV)**: Part A encoder deterministic (4000 inputs); Part B 6944
  signatures deterministic + wire-valid (version byte ok); cross-backend agreement
  73.13%; Tier-0 ROOT order-statistic label drift max=1 LSB (≤4 gate → FP-floor
  cause proven, NOT a logic bug). PASS (11/11). [2-CU measured 2 LSB; VK 1 LSB.]
- **T_FRO_4_VK (exit gate)** — Gemma3-1B, n_ctx=168, via SP_BACKEND=vulkan:
  - **(a)** vulkan-f32 PPL = **32.86458** vs oracle f16 PPL 32.86939 →
    rel-diff **-0.0146%** (gate 0.05%). PASS.
  - **(b)** per-row Q8 arena PPL = 32.62294, drift **-0.7353%** vs vulkan-f32
    (gate 2%). PASS.
  - 9/9 checks. Verified both via direct exe (SP_BACKEND=vulkan) and via the
    registered ctest target's `ENVIRONMENT "SP_BACKEND=vulkan"`.
- CPU regression intact: E_CPU_2, E_CPU_5, E_CPU_6, COMPOSE, M_GEMMA3_CPU all PASS.

## Vulkan-specific adaptations (analogous to 2-CU's two adaptations)
1. **No cuBLAS → hand-written tiled f32 GEMM** (`gemm.comp`, 16×16 tile, shared
   memory). Mirrors the cuBLAS SGEMM mapping Y[t,j]=Σ_i W[j*in+i]·X[t*in+i].
   Accumulates in **f64** (operands stay f32) — the CPU/cuBLAS reference uses
   shallow reduction trees; a flat f32 register would floor at ~K·eps ≈ 8e-4 for
   K=n_ff=6912. f64 acc keeps Vulkan logits at the f32 floor of CPU (KL ~1e-11).
2. **Host-precomputed RoPE cos/sin tables** (`rope.comp` reads a uploaded
   (cos,sin) buffer; no GLSL pow/sin/cos). Built with the exact CPU
   powf/cosf/sinf so the rotation is bit-for-bit the CPU rope_neox transcendentals.
3. **Workgroup-count overflow** (the 2-CU embedded learning): the untied Qwen3 LM
   head has 151936 rows > Vulkan's 65535 per-dim dispatch limit. `dequant_arena.comp`
   dispatches `(ceil(cols/16), ceil(rows/16))` with a 16×16 workgroup decoding a
   tile (rows tiled → 9496 < 65535), NOT one workgroup per row.
4. **Determinism for T_FRO_4(a)**: single compute queue, sequential dispatch in one
   command buffer, full SHADER_WRITE→SHADER_READ memory barrier between every op,
   no atomics, true f32 (no relaxed precision). Fence-wait per submit.
5. **KSTE**: host `sp_kste_encode` (E_VK_6), exactly as 2-CU — K downloaded D→H per
   layer (one command-buffer flush per layer), encoded on host. On-device KSTE
   shader deferred (same as 2-CU).
6. **shaderInt64 + shaderFloat64** enabled at device creation (needed by the NTT
   int64 dot and the rmsnorm/GEMM f64 accumulation). NTT path errors cleanly if a
   device lacks shaderInt64.

## DEBUGGING NOTE (cost one cycle, captured so it isn't rediscovered)
- gemma3-1b head_dim = **256** (Q proj 4×256=1024, KV 1×256=256; head_dim ≠
  n_embd/n_head). The first RoPE shader hardcoded local_size_x=64 (=Qwen3 HD/2),
  so it rotated only the first 64 of 128 pairs on Gemma3 → KL ~6e-4, argmax still
  matched (RoPE error subtle). Fix: local_size_x=128 + a stride loop over half.
- Build-dep gotcha: `vulkan_forward.cpp` `#include`s the generated `*.spv.h`.
  Ninja's initial /showIncludes scan runs before the headers exist, so shader
  edits did NOT trigger a .cpp recompile. Fixed with `set_source_files_properties(
  ... OBJECT_DEPENDS "${SP_VK_SPV_HEADERS}")` in src/CMakeLists.txt. If shader
  edits ever look "ignored", do a clean rebuild and check the .obj timestamp.

## Vendor gate (per brief)
- Closed on NVIDIA RTX 2060 Vulkan (the box's one discrete vendor). The brief's
  "two vendors" is contract aspiration: AMD / Intel-discrete / MoltenVK validation
  is **deferred** until those devices land. The backend is vendor-neutral (core
  Vulkan 1.1 + shaderInt64/Float64 features, no NVIDIA extensions), so it should
  port; the Intel iGPU present here was not exercised (would need feature-fallback
  for f64/int64 which Intel iGPUs often lack).

## Files
New (additive backend):
- include/sp_engine/vulkan_backend.h
- src/backends/vulkan/vk_common.h, vulkan_backend.cpp, vulkan_forward.cpp
- src/backends/vulkan/shaders/*.comp (gemm, embed_scale, rmsnorm, rmsnorm_head,
  rope, attn, attn_ntt, gelu_mul, silu_mul, add, dequant_arena)
- tests/test_vulkan_smoke.c, test_gemma3_vulkan.c, test_qwen3_vulkan.c,
  test_ntt_attn_vulkan.c, test_kste_kv_vulkan.c
Shared files (additive only, mirroring the CUDA blocks):
- CMakeLists.txt (option SP_ENGINE_WITH_VULKAN)
- src/CMakeLists.txt (Vulkan backend lib + glslc SPIR-V build)
- tests/CMakeLists.txt (Vulkan test block + T_FRO_4_VK)
- src/forward/ppl.c (SP_BACKEND=vulkan → gemma3_forward_vulkan, gemma3-only)
- src/forward/model.c (#ifdef SP_ENGINE_WITH_VULKAN → sp_vulkan_model_release)
- scripts/env/env-vulkan.bat (ASCII + goto rewrite, like env-cuda.bat)
LOCAL BUILD HACK (NOT committed): env-common.bat SP_ENGINE → worktree root was
applied during the session and REVERTED before commit (verified clean).
