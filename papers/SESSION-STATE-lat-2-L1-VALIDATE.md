# SESSION-STATE — Phase 2-L1.VALIDATE (§8.7.2) — engine integration bump

**Phase.** PPT-LAT-Roadmap §8.7.2 — point each backend's CMake at the relocated
`shannon-prime-system` (math-core) library, delete the engine's now-redundant copies of
the files the twelve `lat-l1` increments moved, and re-run the four backends' existing
regressions consuming the math-core sources. **Gate:** every previously-green backend gate
stays green under §8.8.1 distributional discipline (argmax + top-5 + KL ≤ existing
thresholds; *no* new per-logit tolerance). **Closure tag:** `lat-phase-2-l1-validate-closed`
on engine + system. Prerequisite for §8.7.3 (HANDLE) and §8.7.4 (SESSION).

**Architecture this phase establishes (per the layering decision):** math-core OWNS the
scalar reference (relocated — bit-exact ground truth); each engine backend OWNS its perf
overlay, *not relocated*; the existing per-backend gates (E_CPU_4 and analogs) validate
overlay-vs-reference with the same KL bound. The relocations were the right cut — they moved
reference + lifecycle + model representation and deliberately left the CPU-specific AVX perf
path behind. Generalizes: CPU=AVX overlay, CU=CUDA kernels, VK=SPIR-V shaders, HX=HVX (HX.3b
qf32) — each atop the one math-core scalar reference.

**Status of this orientation:** submodule pin already moved in the engine working tree
(gitlink → `222e252c`, the §8.7.1 RELOCATE close HEAD; uncommitted — the staged opening of
the structural step). No source deletions performed; this inventory is the pre-delete plan.
**This document is the review checkpoint; the verdict follows before any delete.**

---

## Relocation inventory — the twelve `lat-l1` increments

Bisection space if a regression appears (§8.7.2 bisect clause): the twelve `lat-l1` content
increments on `shannon-prime-system`, listed below in dependency order. Consume + re-run the
regression per increment, not all at once, if the bisect signal is unclear.

Classification legend: **FULL-DELETE** (engine deletes its copy and consumes the math-core
library — pure infrastructure / reference, no perf-overlay nature). **SPLIT** (engine file
mixes a relocated symbol with a backend-specific overlay — split surgically: the relocated
content goes away, the overlay stays/migrates). **NOT-TOUCHED** (stays engine-side; only its
`#include "sp_engine/*"` lines repoint to `sp/*`).

| # | Relocated content / key symbols | math-core source (post-reloc) | engine file (pre-reloc) | Class |
|---|---|---|---|---|
| 1 | reference primitives `sp_dot_f32` / `sp_rmsnorm` / `sp_rmsnorm_head` / `sp_rope_neox` / `sp_attn_head` | `core/forward_kernels/forward_kernels.c`, `include/sp/forward_kernels.h` | `src/forward/kernels.c` (reference half) | **SPLIT** (see K) |
| 2 | `.sp-model` hash primitives (CRC-32 / SHA-256 / XXH64 / BLAKE3-stub) | `core/io_hash/sp_hash.c`, `include/sp/sp_hash.h` | `src/io/sp_hash.c` | FULL-DELETE |
| 3 | `.sp-model` mmap loader half + thread-local `sp_last_error`/`sp_set_error` | `core/io_format/{sp_model_load.c, sp_error.c}`, `include/sp/{sp_model.h, sp_status.h}` | `src/io/sp_model_load.c`, `src/common/sp_error.c` | FULL-DELETE *(verify: io_format's `sp_error.c` exposes the internal `sp_set_error` the backends extern-call)* |
| 4 | weight-dtype dequant `sp_f16_to_f32` / `sp_f32_to_f16` / `sp_dequant_row` | `core/weight_dtype/weight_dtype.c`, `include/sp/weight_dtype.h` | head of `src/forward/model.c` + dtype decls in `include/sp_engine/model.h` | FULL-DELETE (of that content) |
| 5 | GGUF v3 parser (`gguf_open`/`gguf_find_tensor`/typed getters/`gguf_tensor_data`) | `core/gguf/gguf.c`, `include/sp/gguf.h` | `src/loader/gguf.c`, `include/sp_engine/gguf.h` | FULL-DELETE |
| 6 | model-representation header (`qwen3_config`/`qwen3_layer`/`qwen3_model` + forward/lifecycle prototypes) | `include/sp/model.h` | `include/sp_engine/model.h` | header repoint (folded into 4/7) |
| 7 | packed-weight arena (`sp_arena_build`/`from_packed`/`find`/`dequant_row`) | `core/arena/arena.c`, `include/sp/arena.h` | `src/forward/arena.c`, `include/sp_engine/arena.h` | FULL-DELETE |
| 8 | GGUF load/free/release lifecycle (`qwen3_load`/`qwen3_release_source`/`qwen3_free`) | `core/model/model.c` | binding portion of `src/forward/model.c` | **SPLIT** (see M) |
| 9 | model-coupled weight-lift kernels `sp_matmul` / `sp_embed_row` / `sp_as_f32` / env-knob state | `core/forward_dispatch/forward_dispatch.c`, `include/sp/forward_dispatch.h` | weight-lift half of `src/forward/kernels.c` | **SPLIT** (see K) |
| 10 | Qwen3 forward orchestration `qwen3_forward` / `qwen3_forward_ex` + KV-decode `qwen3_generate_kv` | `core/forward/forward.c` (the reference twin) | `src/forward/forward.c` | **REORGANIZE → CPU backend** `src/backends/cpu/cpu_forward.c` (see Backend-overlay symmetry) |
| 11 | Gemma3 reference forward `gemma3_forward` | `core/forward/gemma3.c` (the reference twin) | `src/forward/gemma3.c` | **REORGANIZE → CPU backend** `src/backends/cpu/cpu_gemma3.c` |
| 12 | greedy O(n²) `qwen3_generate` | `core/forward/generate.c` (the reference twin) | `src/forward/generate.c` | **REORGANIZE → CPU backend** `src/backends/cpu/cpu_generate.c` |

The engine already links the Phase-1 math-core libs (`sp_frobenius sp_ntt_crt sp_poly_ring
sp_kste sp_vht2`); the bump adds the new ones the FULL-DELETE/SPLIT rows demand:
`sp_gguf sp_weight_dtype sp_io_hash sp_io_format sp_model sp_arena sp_forward_kernels
sp_forward_dispatch sp_forward`.

---

## SPLIT detail (the blind-delete-protected files)

**K — `src/forward/kernels.c`** (rows 1 + 9). The canonical split.
- *Going (consumed from math-core):* the scalar reference primitives → `sp_forward_kernels`;
  the weight-lift `matmul`/`matmul_arena`/`embed_row`/`as_f32` + the `g_*` env-knob state →
  `sp_forward_dispatch` (math-core ABI names `sp_matmul`/`sp_embed_row`/`sp_as_f32`/
  `sp_kernels_read_env`).
- *Staying (the CPU perf overlay):* the AVX/AVX-512 `dot_f32` (`#if defined(SP_ENGINE_AVX2)`
  branch + its scalar tail), migrating to a clearly-named **`src/backends/cpu/cpu_overlay.c`**
  so the layering is explicit in the directory tree. E_CPU_4 stays the gate that compares the
  CPU AVX path against the math-core scalar reference (the SP_CPU_SCALAR=1 path is now the
  consumed reference); KL bound unchanged (E_CPU_4 closure: argmax 31/31, |Δ| 1.7e-4 reassoc).

**M — `src/forward/model.c`** (rows 4 + 8). A second mixed file.
- *Going:* the dtype helpers (row 4) and the GGUF binding lifecycle (row 8) — consumed from
  `sp_weight_dtype` + `sp_model`.
- *Staying (a backend-lifecycle overlay):* the engine's `qwen3_free` invoked the device-memory
  release hooks under `#ifdef SP_ENGINE_WITH_{CUDA,VULKAN,HEXAGON}` (`sp_cuda/vulkan/hexagon_
  _model_release`). The math-core `qwen3_free` deliberately dropped these (engine/L2 concern).
  So consuming the math-core lifecycle *removes the device-release call site* — those hook
  invocations must be re-homed into the engine's own backend/session teardown (a CU/VK/HX-leg
  task; the CPU leg is unaffected — no device memory).

**Per-backend overlay locations** (where each backend's optimized equivalent of the relocated
reference/weight-lift lives — the "atop the reference" perf paths the legs validate):
- CPU — AVX `dot_f32` → **`src/backends/cpu/cpu_overlay.c`** (new home, extracted from kernels.c).
- CUDA — `src/backends/cuda/cuda_forward.cu` (+ `cuda_backend.cu`); links `sp_frobenius sp_vht2`.
- Vulkan — `src/backends/vulkan/shaders/*.comp` (gemm/rmsnorm/rope/attn/…) + `vulkan_forward.cpp`; links `sp_frobenius sp_vht2 sp_kste`.
- Hexagon — `src/backends/hexagon/dsp/sp_hex_imp.c` (HVX qf32 dot) + host `sp_hex_host.c`.

---

## NOT-TOUCHED (stays engine-side; only `sp_engine/*` includes repoint to `sp/*`)

- `src/forward/ppl.c` — the perplexity / T_FRO_4 (SP3) evaluation harness, not the inference path.
- `src/tokenizer/tokenizer.c` — tokenizer; never relocated (Phase-3 / `.sp-tokenizer` territory).
- `src/io/sp_model_adapter.c` — the `sp_model_to_qwen3` adapter; explicitly §8.7.3 HANDLE work.
  Must keep compiling under the bump (repoint its includes; its ~5 references to relocated
  symbols resolve against the new `sp/*` headers + ABI names).
- `src/backends/{cuda,vulkan,hexagon}/*` — the device perf forwards/dispatch (the overlays
  themselves). Their host/dispatch C/C++ references the renamed kernels/relocated headers
  (counts: CUDA ~5, VK ~4, HX-host ~5, HX-dsp ~1) — repoint to `sp/*` + the ABI names when the
  respective leg is built.
- `include/sp_engine/*.h` mirror headers — repointed/retired in favor of the math-core `sp/*`
  equivalents, except a slim residual carrying the surviving CPU-overlay surface (the AVX
  `dot_f32` declaration). *(Verify-at-execution: the exact engine `sp_engine/` header set —
  a directory-listing glob false-negatived this orientation pass.)*

---

## Backend-overlay symmetry (the Option-C resolution — authorized)

The relocation accidentally created an asymmetry: pre-relocation the engine *was* the CPU
backend — its forward.c/kernels.c served as both the reference and the AVX perf path, toggled
at runtime by `SP_CPU_SCALAR`. Moving that forward into math-core made math-core the reference
and left the CPU "backend" with no backend-side forward, while CUDA (`cuda_forward.cu`), Vulkan
(`vulkan_forward`), and Hexagon (`sp_hex_imp.c` / `gemma3_forward_hexagon`) each retain their own
optimized forward validated against the reference. Option C restores symmetry: **the CPU backend
gets its own forward in `src/backends/cpu/` — the AVX-overlay sibling of `cuda_forward.cu` — and
math-core's scalar forward is the parallel reference oracle every backend validates against**
(the same pattern the cross-backend KL gates E_CPU_2 / E_CU_2 / E_VK_2 already use).

Why this and not the alternatives: a math-core dot-dispatch *seam* (the cleaner long-term answer)
re-opens the just-relocated hot path and the determinism-at-create contract — that belongs to the
§8.7.4 SESSION phase where the L1 config knobs already plumb through, not to a *validation* phase
(it would turn VALIDATE into a redesign the per-increment bisect can't cleanly recover). And the
literal "consume the math-core scalar forward as the CPU path" neuters E_CPU_4 — a whole-forward,
runtime-toggled (`SP_CPU_SCALAR={1,0}`) AVX-vs-scalar comparison: with only a scalar forward, both
legs are identical, the gate trivially "passes" but exercises nothing (verified from `test_avx.c`).

Consequence — duplication accepted, by design. The CPU backend's forward is structurally parallel
to the four device backends' forwards; future edits to the forward orchestration logic touch all
five sites (math-core scalar reference + the four backend overlays) — the same cost the existing
CU/VK/HX backends already pay. The CPU backend's forward is **not redundant code**; it is the
AVX-overlay sibling.

One file-level clarification to the kernels.c SPLIT, resolved by this principle: the CPU backend's
overlay is not *only* the AVX `dot_f32`. To be a real AVX-accelerated forward whose `SP_CPU_SCALAR`
toggle is meaningful, the CPU backend keeps its full kernel surface — the weight-lift matmul/embed
and the reference primitives that compose the forward — calling its own AVX-toggled `dot_f32`
(in `cpu_overlay.c`, `SP_ENGINE_AVX2`-guarded; its scalar branch may delegate to math-core's
`sp_dot_f32` for consistency). What the CPU backend *consumes* from math-core is the shared
infrastructure that has no perf-overlay nature: model representation, the packed-weight arena,
the GGUF parser, weight-dtype dequant, IO/hash, and the error surface. The math-core
forward/forward_dispatch/forward_kernels libraries stand as the reference twin.

## Structural step (executed only after the verdict checkpoint)

1. Submodule pin → `222e252c` (gitlink already moved in the working tree; commit it with the bump).
2. Engine CMake (`src/CMakeLists.txt`): drop the FULL-DELETE/SPLIT sources from `sp_engine`'s
   source list, add `src/backends/cpu/cpu_overlay.c`, and add the new math-core `sp_*` libs to
   `target_link_libraries(sp_engine PUBLIC …)`. Repoint backend CMakes likewise per leg.
3. Apply the FULL-DELETE rows (delete the engine files), apply the two SPLITs surgically
   (extract `cpu_overlay.c`; re-home the device-release hooks for the device legs).
4. Repoint surviving `#include "sp_engine/*"` → `sp/*` across NOT-TOUCHED consumers.
5. Rebuild + run the regression — per leg, CPU first.

## Four-leg validation plan & local executability

- **CPU (the §8.6 canonical anchor — mine, local MSVC + ctest):** target the full suite incl.
  the slow `T_FRO_4`. Known closure numbers to re-measure: forward correctness −0.0146% (gate
  ≤0.05%, the §8.6.1 floor) and per-row-Q8 arena quality −0.74% (gate ≤2%). Expect CPU 20/20.
- **CU (mine, same host — RTX 2060 + `env-cuda.bat`):** if a clean-`main` checkout exposes a
  broken env script (the 2-CU agent's worktree-local hacks were reverted pre-commit — cf. the
  CPU env script's ASCII/goto breakage), **fix the script at the root, do not work around it.**
  Target CU 6/6 (CUDA_SMOKE / M_GEMMA3_CUDA / M_QWEN3_CUDA / E_CU_5 / E_CU_6 / T_FRO_4_CU).
- **VK (mine, same host — RTX 2060 Vulkan compute + `env-vulkan.bat`):** same fix-at-root rule.
- **HX (physical-presence-gated):** requires the S22U on USB with adb; the software toolchain
  (Hexagon SDK 5.5.6.0 + qaic + hexagon-clang v8.7.06 + NDK r25c + `env-hexagon.bat`) is on the
  host. If the phone is not attached when HX gates run: stash the diff, tag the HX gate
  **"pending S22U attach"**, and close the other three legs — VALIDATE closure must not block on
  a physical-presence dependency. Target HX.0–HX.3b.

§8.8.1 discipline applies to every leg: argmax + top-5 + KL ≤ the existing thresholds; no new
per-logit tolerance may be required.

## Cross-platform math-core contract (new build environments the bump introduces)

Math-core was Phase-1-tested on Win + Linux in isolation. The bump exposes it to nvcc (CUDA),
glslc + Vulkan headers, and the NDK aarch64 + hexagon-clang toolchains. **Math-core's contract
is: it compiles under all four backend toolchains and exposes the symbols the backends consume.**
Any relocated math-core file that fails to compile under one of those is a *math-core* bug to fix
in `shannon-prime-system` — not worked around in the engine. (Precedent: the pre-relocation
`[lat-2-CU]` "C++-safe `_Static_assert` for CUDA/VK/HX backends" header fix.) The relocated
headers/sources must hold the same line.

## Verify-at-execution flags (honest uncertainties to confirm during the structural step)

- io_format's relocated `sp_error.c` must expose the internal `sp_set_error` the engine backends
  extern-declare and call (the engine's `common/sp_error.c` documents that contract).
- The exact engine `include/sp_engine/` header set and which mirror headers retire vs. slim down.
- The precise content boundary inside `kernels.c` separating the AVX `dot_f32` overlay from the
  relocated reference + weight-lift (the `#if defined(SP_ENGINE_AVX2)` region and `dot_f32`).

*(Verify-at-execution outcome: the build proved them — the kernels.c content moved whole into the CPU
backend as `cpu_overlay.c` per the symmetry resolution; `sp_set_error`'s exposure and the engine's
`sp_engine/*` declaration headers resolved cleanly against the linked math-core libs; no header-set
retirement was needed — the engine's includes are root-rooted and move-transparent.)*

## VALIDATE leg results (running)

**CPU — the §8.6 canonical anchor — CLOSED (2026-05-24).** Engine `main` carries Commit A (pin-only →
math-core `63f6488` = the §8.7.1 RELOCATE HEAD plus the `sp_set_error` public-API promotion and the
`sp_add_module` test-exe gating fix) and Commit B (the Option-C structural cutover); both pushed
(engine HEAD `8795c1f`). Build green — the cutover compiles and links, and the relocated math-core
modules cross-compile under MSVC. Regression **27/27 green, and behavior-PRESERVING** — the gate
measurements match the pre-relocation close: `T_FRO_4` forward-correctness rel-diff **−0.0146%** (gate
0.050%) and Q8-arena drift **−0.7353%** (gate 2.00%); arena / Frobenius inline-lift `bit_exact=YES`
(L2-drift 0.000000%); `M_GEMMA3_CPU` argmax 31/31, mean KL 2.3e-6 (gate 1e-5); the Qwen distributional
path within the 1e-5 floor. The integration also surfaced and fixed-at-root a latent math-core build
bug (the test-exe target-name collision; now gated on `SP_SYSTEM_BUILD_TESTS`) — the kind of latent
issue VALIDATE exists to catch.

**CU — CLOSED (2026-05-24).** Build green (CUDA backend consumes the cutover; math-core nvcc/C++-safe);
regression 31/33, M_QWEN3_CUDA full f32/Q8/Q4 green, CUDA_SMOKE green. Load-bearing gate: per-row Q4
mixed-precision cross-backend identity (cuda-vs-cpu) on the production arena — KL(cpu‖cuda) ~1e-11 —
proving the relocated math-core ≡ engine-local copies. M_GEMMA3_CUDA scoped to that Q4 path (VRAM
hygiene). T_FRO_4_CU gate (a) f32-vs-oracle deferred → §8.7.5 Phase 2-L1.FP16 (f32 working precision
retiring for fp16; reproducing it isn't load-bearing); gate (b) Q4 cross-backend identity = the close.
Engine 3fe16a8.

**VK — CLOSED.** Build green (3rd cross-toolchain: glslc). Q4 cross-backend identity vk-vs-cpu pristine where run (q8 KL 1.2e-10, argmax 31/31); M_GEMMA3_VULKAN Q4-scoped. Host-RAM saturation OOMd full-suite reproduction (VkResult-2/host-OOM, VRAM free) -> deferred to 2-L1.FP16 (the fp16 envelope fix). **HX — Q8-only anchored (2-HX, closed).** TAG lat-phase-2-l1-validate-closed: engine aff54c6 / system. **VK/HX(orig) — n/a.** Each builds its own device-backend overlay (consuming the same relocated
infrastructure) and re-runs its existing regression, with a results entry added here. Disposition:
VK runs the identical Q4 cross-backend identity gate; HX is Q8-only anchored already (2-HX). The `model.c`
device-release `#ifdef` hooks — dropped with the deleted engine `model.c` — are re-homed into the
engine's backend teardown as those legs build (CPU-inert, so it did not block the CPU leg). Device env
scripts are fixed-at-root if a clean checkout exposes breakage; the HX leg is live (S22U on USB). The
closure tag `lat-phase-2-l1-validate-closed` lands once all four legs are green.
