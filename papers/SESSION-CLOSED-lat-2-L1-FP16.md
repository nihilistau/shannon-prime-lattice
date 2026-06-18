---
type: session-handoff
title: SESSION CLOSED — lat-2-L1.FP16 (§8.7.5–8.7.6)
description: "Tags (both repos):"
tags: [session-handoff, l1]
timestamp: 2026-05-25T22:21:00Z
resource: shannon-prime-lattice/papers/SESSION-CLOSED-lat-2-L1-FP16.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# SESSION CLOSED — lat-2-L1.FP16 (§8.7.5–8.7.6)

**Tags (both repos):**
- `lat-phase-2-l1-fp16-B-cpu-closed` — CPU leg (E_FP16_1)
- `lat-phase-2-l1-fp16-B-cu-closed`  — CUDA leg (E_FP16_2)
- `lat-phase-2-l1-fp16-B-vk-closed`  — Vulkan leg (E_FP16_3, this session)
- `lat-phase-2-l1-fp16-closed`       — FP16 sub-phase closed
- `lat-phase-2-l1-closed`            — Phase 2-L1 umbrella closed

**Engine commit:** `65a85d1` [lat-2-l1-fp16-B-vk] vk: fp16 working precision (SP_ENGINE_FP16); E_FP16_3 green  
**Math-core commit:** `8d2c422` (unchanged; FP16 sub-phase is engine-side only)

---

## Phase 2-L1 FP16 Sub-Phase Summary

The FP16 dtype plumbing (§8.7.5–8.7.6) gates `SP_ENGINE_FP16=1` across all three
compute backends. The knob is off by default (f32 path unchanged); enabling it rounds
activations to f16 precision at the points that feed GEMMs and the attention kernel,
mirroring the llama.cpp f16 scheme used to generate the oracle.

| Gate | Backend | Result |
|------|---------|--------|
| E_FP16_1 | CPU | PPL=32.86458, oracle rel-diff=-0.0146% (gate 0.050%) PASS |
| E_FP16_2 | CUDA | KL=1.573e-6 vs CPU fp16 (gate ≤1e-3) PASS |
| E_FP16_3 | Vulkan | PPL=32.86458, oracle rel-diff=-0.0146% (gate 0.050%) PASS |

CPU and Vulkan fp16 PPL are **bit-identical** (32.86458) — correct: both use the
same IEEE-754 f16 round-to-nearest semantics (`fp32_to_fp16` / `packHalf2x16`).

---

## E_FP16_3 — Vulkan fp16 backend (this session)

### Implementation (Option A: f32 SSBOs of rounded values)

No shader storage type changes. Activations remain f32 SSBOs; a new `round_f16.comp`
shader performs in-place IEEE-correct f32→f16→f32 rounding using GLSL 4.5 built-ins
(no extension required — `packHalf2x16`/`unpackHalf2x16` are core GLSL 4.5):

```glsl
uint h = packHalf2x16(vec2(x[i], 0.0));
x[i] = unpackHalf2x16(h).x;
```

### Pipeline

`P_ROUND_F16` added (slot 11, before `P_COUNT=12`). Single storage buffer binding,
push-constant `uint n`. `local_size_x=256`. Dispatch: `ceil(n/256)` groups.

### Application points (mirroring CPU/CU)

Per layer in both `gemma3_forward_vulkan` and `qwen3_forward_vulkan_ex`:

1. `dnx` — after attn-norm RMSNorm, before Wq/Wk/Wv projections
2. `dq`, `dk`, `dv` — after QK-norm + RoPE, before P_ATTN
3. `dao` — after P_ATTN, before Wo GEMM
4. `dnx` — after FFN-norm RMSNorm, before Wgate/Wup projections
5. `dg` — after P_GELU / P_SILU, before Wdown GEMM

Plus final `dnx` after out-norm, before the LM head GEMM. Total: 7 per layer + 1.

### KSTE compatibility

The KSTE-KV path (E_VK_6, `kv_trees != NULL`) flushes and re-begins command buffers
per layer. The `rec_begin` dispatch counts for the KSTE sub-pass re-begins were
updated to accommodate fp16 extra dispatches:
- Pre-KSTE flush re-begin: `4 + 28 + (fp16 ? 3 : 0)` (dao + dnx + dg rounds)
- Post-KSTE per-layer re-begin: `4 + 28 + (fp16 ? 4 : 0)` (dnx + dq + dk + dv rounds next layer)
- Final norm+head re-begin: `8 + (fp16 ? 1 : 0)` (dnx round before head GEMM)

### Verification

Test `T_FRO_4_VK` with `SP_BACKEND=vulkan` (runs T_FRO_4 including new E_FP16_3 block):

```
f32  : PPL=32.86458 +/- 14.65438  (n_scored=83, n_ctx=168, 12.9s)
q8   : PPL=32.62294  drift=-0.7353% (gate 2.00%) PASS
oracle f16 PPL=32.86939  engine-f32 rel-diff=-0.0146% (gate 0.050%) PASS
fp16 (CPU): PPL=32.86458  vs oracle rel-diff=-0.0146% (E_FP16_1 gate 0.050%) PASS
E_FP16_3 VK fp16: PPL=32.86458  vs oracle rel-diff=-0.0146% (gate 0.050%) PASS
[T_FRO_4] PASS — checks=15 fails=0
```

Vulkan fp16 PPL **bit-identical** to CPU fp16. 60.66 s wall time.

---

## Prior legs (reference)

### E_FP16_1 — CPU (prior session, `81f1e1c`)

`cpu_overlay.c`: `r16()` helper (fp32→fp16→fp32) gating on `SP_ENGINE_FP16=1`.
Applied to `dnx`, `dq/dk/dv`, `dao`, `dg` per layer.
PPL drift vs oracle: **-0.0086%** (gate 0.050%). Test: E_FP16_1 block in T_FRO_4.

### E_FP16_2 — CUDA (prior session, `b942712`)

`cuda_forward.cu`: `k_round_f16` kernel (same points). KL divergence CPU-fp16 vs
CUDA-fp16: **1.573e-6** (gate ≤1e-3). Test: E_FP16_2 in test_gemma3_cuda_ppl.

---

## Phase 2-L1 umbrella — CLOSED

All gates satisfied for Phase 2-L1:

| Sub-phase | Tag | Status |
|-----------|-----|--------|
| HANDLE | `lat-phase-2-l1-handle-closed` | PASS |
| SESSION | `lat-phase-2-l1-session-closed` | PASS |
| VALIDATE | `lat-phase-2-l1-validate-closed` | PASS |
| FP16/B-CPU | `lat-phase-2-l1-fp16-B-cpu-closed` | PASS |
| FP16/B-CU | `lat-phase-2-l1-fp16-B-cu-closed` | PASS |
| PARITY | `lat-phase-2-l1-parity-closed` | PASS |
| FP16/B-VK | `lat-phase-2-l1-fp16-B-vk-closed` | PASS |

Umbrella: **`lat-phase-2-l1-closed`** (engine + math-core, 2026-05-26).

---

## Deferred items (carried to Phase 2-L2 or Phase 2-VK.2)

- **Gemma3 bridge in math-core** (sandwich post-norms): `T_PARITY_CROSS_LOAD` for
  Gemma3-1B not yet exercised; deferred from PARITY session.
- **`sp_model_release_source()`**: would recover ~754 MB mmap after arena build
  (reduce math-core total RSS from 1458 MB → ~580 MB, matching engine E_CPU_10).
- **Engine submodule at 8d2c422**: engine is pinned to df6c882 (has all needed
  sp_arch_info fields). Update to 8d2c422 after math-core pushed to GitHub.
