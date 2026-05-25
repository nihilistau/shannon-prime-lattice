# SESSION-STATE-lat-2-L1-FP16-A

**Phase:** 2-L1.FP16 (Roadmap §8.7.5) — **PART A ONLY (the math-core ABI extension).**
**Session date:** 2026-05-25.
**Status:** **STATE, NOT CLOSED.** Part A (the `sp_arch_info` growth + session
precision resolution) is shipped + Tier-1 green. **Part B (fp16 working precision
across CPU/CU/VK in the engine) is NOT done** — it is GPU/real-model gated and is the
bulk of §8.7.5. **No tags fired.** `lat-phase-2-l1-fp16-closed` and the umbrella
`lat-phase-2-l1-closed` fire only after the canonical `E_FP16_1..5` gates pass — see
the Part B plan.

shannon-prime-system `main` @ **`35cb5df`** (`[lat-2-l1-fp16-A]`), pushed
(`0f5b29f..35cb5df`). Tier-1 (Windows MinGW gcc 15.2): full root suite **16/16**;
`T_SESSION` 9 cases / **73 checks**; UBSan trap-on-error clean. **Tier-2 (Linux gcc)
AND Tier-3 (MSVC) CI both green** (run `26401194997`: `linux-gcc` 33s, `windows-msvc`
48s) — confirms the grown `sp_arch_info` + `_Static_assert(sizeof<=256)` compile under
gcc and MSVC, and `sp_l1.h`'s C++ inclusion (Vulkan) is unaffected.

---

## ⚠ Handoff corrections (verified against sp_l1.h + Roadmap §8.7.5 on disk)

The FP16 handoff drifted from ground truth (third handoff this round to do so — see
[[feedback-frozen-contract-sacred]]). Verified discrepancies:

1. **Cited memory entries do not exist.** The handoff repeatedly says "re-read
   `reference-fp16-working-precision`" (per-backend table) and
   `reference-hx-activation-correctness` (V69 gotcha #7). Neither exists in this
   project's memory (only `reference-cuda-13.2-build-recipe` + this feedback entry).
   **The content is recoverable from Roadmap §8.7.5 itself**: the per-backend
   precision table is lines ~1495-1505 (CPU = fp16 activations + fp16 KV + **f32
   matmul accumulator**; HX = qf32, "V69 Q6_Vsf_* IEEE-fp16 broken, gotcha #7"); the
   Frobenius-lift cross-backend-identity rationale is lines ~1483-1489.
2. **The handoff's `E_FP16_*` gate definitions are wrong.** Canonical §8.7.5:
   - `E_FP16_1` = CPU fp16 forward, PPL vs f16 oracle ≤ 0.05%.
   - `E_FP16_2` = cross-backend fp16 identity (CPU vs CU vs VK), zero/ULP KL by the Frobenius-lift identity.
   - `E_FP16_3` = **HX qf32 precision-floor** (NOT a T_FRO_4 PPL gate; HX stays qf32, bounded comparison).
   - `E_FP16_4` = **memory ceiling** at production context (+ the deferred desktop-GPU legs).
   - `E_FP16_5` = **fp8 forward-compat** via `sp_arch_info.preferred_precision` exposing fp16/qf32/f32.
   The handoff's "E_FP16_4 = T_ARCH_GROWTH / E_FP16_5 = T_SESSION_PRECISION_PRECEDENCE"
   are reasonable *mechanism* tests for Part A but are **not** the §8.7.5 gates. The
   Part A tests below are named as themselves, not as `E_FP16_*`.
3. **`sp_arch_info` lives in `sp_l1.h`**, not `sp_model.h` (handoff hedged). 
4. **A5 transcoder does not exist** in either repo (`sp-transcode`/`gguf-to-sp` —
   only comments match). It is spec'd engine-side (PPT-LAT-SP-MODEL-v0 §9) and was
   never built. So A5 (write the new fields from the transcoder) has nothing to update
   — it is a Part B prerequisite (E_FP16_1's PPL gate needs a transcoded `.sp-model`).
5. Engine backend paths are `src/backends/{cpu,cuda,vulkan,hexagon}/` (real, committed),
   not `src/{cpu,cuda,vulkan}/`.

## Done this session — Part A (commit `35cb5df`, shannon-prime-system only)

- **`sp_arch_info` grown** (`sp_l1.h`): appended `uint32_t n_ff`, `float rms_eps`,
  `uint32_t preferred_precision` in the reserved arch_struct tail. **`sizeof`
  44 → 56 bytes** (≤ 256, `_Static_assert` in `sp_model_arch.c`, a C TU — `sp_l1.h`
  is also included by the C++ Vulkan backend, where `_Static_assert` is invalid).
  Growth is backward-compatible via the size-limited memcpy `sp_model_arch.c` already
  performs — **not** an ABI version bump.
- **`enum sp_precision`** {UNSPECIFIED=0, F32=1, FP16=2, QF32=3, (FP8=4 reserved)}.
- **`sp_session_config.precision_override`** + **`sp_session_precision()`** accessor.
  Precedence (fixed at create): `override > arch_info.preferred_precision > F32`.
  Backend dispatch (Part B) reads it; the math-core f32 reference ignores it.
- **Bridge** (`sp_model_bridge.c`): `n_ff` from arch_struct if set else derive from
  `ffn_gate`; `rms_eps` from arch_struct if set else default 1e-6 + a one-line stderr
  warning (the bridge has the handle, not the file path, so the warning names neither;
  acceptable — flagged).
- **Tests** (`T_SESSION`, +3): `T_ARCH_GROWTH_OLD` (arch_struct_size = offsetof(n_ff):
  appended fields truncated → read 0 → bridge defaults → session F32; loads, no
  `SP_EBADFORMAT`), `T_ARCH_GROWTH_NEW` (full size: fields populated + read by arch
  query and bridge), `T_SESSION_PRECISION_PRECEDENCE` (override QF32 beats arch FP16;
  arch FP16 beats default; unspecified → F32). All green; UBSan clean.

**Math-core reference forward UNCHANGED** (f32, the bit-exact anchor). HX untouched.

## NOT done — Part B (engine fp16; closes the phase)

Part B lands fp16 working precision in `shannon-prime-system-engine` and runs the
canonical gates. It is **resource-gated** (GPU + real model + oracle) and was not
attempted this session.

### Part B execution plan

Re-derive per Roadmap §8.7.5 (lines ~1495-1505 table + the per-backend notes);
confirm the CU/VK rows there before coding. Backends read `sp_session_precision`
(now available) to select the fp16 path; f32 stays the fallback (no regression).

- **B-CPU** (`src/backends/cpu/`, no GPU needed — do first, locally): activations +
  KV cache + norms/RoPE/attention in fp16 (`_Float16` on gcc; AVX-512-FP16 / F16C on
  MSVC); **matmul accumulator stays f32** (widen per dot). Gate `E_FP16_1`: engine-cpu
  -fp16 PPL vs f16 oracle ≤ 0.05% — **blocked on a transcoded Gemma3-1B `.sp-model`**
  (transcoder doesn't exist; build it first, or use the engine's GGUF path + oracle).
- **B-CU** (`src/backends/cuda/`, needs RTX 2060 + CUDA 13.2, see
  [[reference-cuda-13.2-build-recipe]]): cuBLAS HGEMM in the hot matmul, `__half`
  activations + KV, f32 compute type; sm_75 target.
- **B-VK** (`src/backends/vulkan/`, needs RTX 2060 + Vulkan SDK): enable
  `VK_KHR_shader_float16_int8` (runtime feature-gated; f32 fallback), `float16_t`
  activations + KV in the `.comp` shaders, f32 accumulator; `glslc` rebuild.
- **E_FP16_2** cross-backend identity: CPU-fp16 vs CU-fp16 vs VK-fp16 bit-identical at
  fp16 on the Q4 arena — zero KL by the Frobenius-lift identity; nonzero ⇒ a backend
  dispatch bug, not a math bug. **HX is explicitly NOT in this bit-equality gate.**
- **E_FP16_3** HX qf32 precision-floor: HX-qf32 vs CPU-fp16 KL bounded by the
  qf32-vs-fp16 representation floor (argmax + top-5 agreement). HX backend code stays
  qf32 — do NOT try to give V69 an IEEE-fp16 path (Q6_Vsf_* broken, gotcha #7).
- **E_FP16_4** memory ceiling; **E_FP16_5** fp8 forward-compat — Part A already landed
  the `preferred_precision` enum E_FP16_5 leans on; the gate itself is a Part B
  validation that the fp16 path doesn't preclude fp8.
- **Transcoder prerequisite**: `E_FP16_1`/`E_FP16_3` need a real transcoded `.sp-model`
  (Gemma3-1B / Qwen3-0.6B). None exists on host. Build `sp-transcode` (engine-side per
  §9), OR run the gates via the engine's existing GGUF forward path + the llama.cpp
  oracle at `shannon-prime-lattice-llama`.

### Closure (deferred to Part B)
Tag `lat-phase-2-l1-fp16-closed` then the umbrella `lat-phase-2-l1-closed` (both repos)
**only after all five `E_FP16_1..5` pass for real** + the §8.2 T_FRO_4-fp16 amendment.
Until then this is shipped mechanism, not a closed phase.

## Notes
- Fixture `.sp-model` SHA-256 changed (arch_struct_size 44→56): the SESSION offload's
  `b6379383…` and HANDLE's `96e3757…` are superseded — both were observability prints,
  not asserted, so no gate moved.
- Anti-contamination held: no reads of legacy `shannon-prime/` or `shannon-prime-engine/`.
