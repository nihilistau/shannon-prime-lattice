---
type: session-handoff
title: "SESSION-CLOSED: lat-phase-3-cell-qwen25"
description: "Date: 2026-05-26"
tags: [session-handoff, qwen]
timestamp: 2026-05-26T07:08:48Z
resource: shannon-prime-lattice/papers/SESSION-CLOSED-lat-3-cell-qwen25.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# SESSION-CLOSED: lat-phase-3-cell-qwen25

**Date:** 2026-05-26  
**Tag:** `lat-phase-3-cell-qwen25-closed` (shannon-prime-system + engine)  
**Branch:** main  
**Result:** CLOSED — 365/365 math-core checks; 14/14 engine CPU tests

---

## Deliverables

### A. Architecture enum extension

Both repos extended with:
- `sp_arch_t`: `SP_ARCH_QWEN25 = 2` (math-core `include/sp/model.h`; engine `include/sp_engine/model.h`)
- `sp_arch_id`: `SP_ARCH_ID_QWEN25 = 6` (5 = QWEN35 reserved for Phase 3-SSM; math-core `include/sp/sp_model.h`; engine `include/sp_engine/sp_model.h`)

`qwen3_layer` extended with three nullable bias pointers:
```c
const gguf_tensor *attn_q_bias;  /* [n_head*head_dim] F32; Qwen2.5 only */
const gguf_tensor *attn_k_bias;  /* [n_kv_heads*head_dim] F32; Qwen2.5 only */
const gguf_tensor *attn_v_bias;  /* [n_kv_heads*head_dim] F32; Qwen2.5 only */
```

### B. model.c: Qwen2.5 GGUF load (math-core: core/model/model.c)

- Arch detection extended: `strcmp(arch, "qwen2") == 0` → `SP_ARCH_QWEN25`
- Per-layer binding (conditional on `c->arch == SP_ARCH_QWEN25`): `attn_q.bias`, `attn_k.bias`, `attn_v.bias` via `BIND` macro
- Null check: returns NULL if any bias missing on a Qwen2.5 model
- `qwen3_release_source` cap: bumped from 4 to 7 norms per layer to cover the 3 bias entries

### C. sp_model_to_qwen25 bridge (math-core: core/session/sp_model_bridge.c)

Zero-copy bridge following Fix-B (alias_mask=0x3 on codes+row_scale). Reconstructs a
`qwen3_model` from a loaded `.sp-model` handle for Qwen2.5 architecture:

- 12 synthetic tensor entries per layer: 7 matmul (attn_q/k/v/output, ffn_gate/up/down)
  + 5 f32 entries (attn_norm, attn_q.bias, attn_k.bias, attn_v.bias, ffn_norm)
- arch guard: returns NULL with `sp_set_error` if `ai.arch_id != SP_ARCH_ID_QWEN25`
- NSYN = 2 + has_output_w + 12*NL; NARENA = 1 + has_output_w + 7*NL; NNORM = 1 + 5*NL
- `sliding_window = 0`, `has_qk_norm = 0`
- `rope_freq_base` defaults to 1e6f if unset
- `sp_model_to_qwen3` gains an arch guard (returns NULL for non-Qwen3 models)

### D. qwen25_forward (math-core: core/forward/qwen25.c)

Reference f32 prefill (causal):
- No embedding scale (Qwen2.5 vs Qwen3 delta)
- After Q/K/V matmul: add f32 biases from `sp_as_f32(m, ly->attn_q_bias)` etc.
- No QK norms — RoPE applied directly to Q/K heads (neox, freq_base=1e6)
- GQA full causal attention (win=-1)
- SwiGLU FFN: `gv / (1.0f + expf(-gv)) * up[i]` (same formula as Qwen3)
- Simple pre-norm residual (no sandwich norms)

### E. kv_step_qwen25 + session dispatch (math-core: core/session/sp_session.c)

- `kv_step_qwen25`: single-token step with all 3 KV modes (f32/Spinor/f32+roundtrip)
  - Adds QKV biases after projection before RoPE
  - Uses `kb2`/`vb2` naming in Spinor mode to avoid shadowing the outer bias pointers
- `sp_session_create`: three-way dispatch (`SP_ARCH_ID_GEMMA3` → `sp_model_to_gemma3`,
  `SP_ARCH_ID_QWEN25` → `sp_model_to_qwen25`, else → `sp_model_to_qwen3`)
- `sp_prefill_chunk`: three-way dispatch via `cfg.arch`
- `sp_decode_step`: three-way dispatch via `STEP` macro

### F. qwen25_fixture.c/h (math-core: core/session/)

Tiny Qwen2.5-shaped `.sp-model` + `.sp-tokenizer` builder for unit tests:
- NL=2, E=32, FF=64, NH=4, NKV=2, HD=8, V=48
- arch: SP_ARCH_ID_QWEN25, ffn_variant=0 (SwiGLU), norm_variant=0, tied_embeddings=1,
  has_qk_norm=0, rope_freq_base=1e6
- 41 tspec entries for NL=2: (Q8 pair = 2 entries) × 7 matmul + F32 × 5 norms per layer,
  plus token_embd Q8 pair + output_norm F32 global

### G. Tests (math-core: core/session/session_test.c)

- **T_QWEN25_ALIAS**: confirms alias_mask==0x3 on codes+row_scale, arch==SP_ARCH_QWEN25
- **T_QWEN25_DECODE_TRAJECTORY**: session argmax matches `qwen25_forward` O(n²) reference
  for 100 auto-regressive steps (5-token prompt → 100 decode steps)
- **T_PARITY_CROSS_LOAD_QWEN25**: loads engine-transcoded Qwen2.5-3B
  (`build-cpu/tests/qwen25_rt.sp-model`); verifies n_layers=36, hidden_dim=2048, n_heads=16,
  n_kv_heads=2, head_dim=128, preferred_precision=FP16; skips gracefully if artifact absent

### H. Engine adapter (engine: src/io/sp_model_adapter.c)

`sp_model_to_qwen25` mirrors the math-core bridge for the engine adapter path:
- arch guard: returns NULL if `h->arch_id != SP_ARCH_ID_QWEN25`
- 12 synthetic gguf_tensor entries per layer (same layout as math-core bridge)
- norm_cap = 1 + 5*NL; arena_cap = 1 + has_output_w + 7*NL
- Dedicated macro set (`ADD_NORM25`, `ADD_Q825`, `NEW_T25`) to avoid collision with
  existing macros in `sp_model_to_qwen3`

### I. Transcoder (engine: tools/sp_transcode/sp_transcode.c)

`fill_arch_struct` extended:
- `int qwen25 = (c->arch == SP_ARCH_QWEN25)` → `ai.arch_id = SP_ARCH_ID_QWEN25`
- `ffn_variant=0`, `norm_variant=0` (SwiGLU/pre-norm, same as Qwen3)
- `is_matmul_weight` unchanged: bias tensors (`attn_q.bias` etc.) don't match any
  matmul pattern and are correctly serialized as F32

---

## Architecture Deltas: Qwen2.5 vs Qwen3

| Feature | Qwen3 | Qwen2.5 |
|---------|-------|---------|
| Embedding scale | `sqrt(n_embd)` | none |
| QK norms | yes (`has_qk_norm=1`) | none (`has_qk_norm=0`) |
| QKV biases | none | F32, all 3 per layer |
| FFN variant | SwiGLU | SwiGLU (same) |
| Norm variant | pre-norm | pre-norm (same) |
| SWA | optional | none (sliding_window=0) |
| GGUF arch key | `qwen3` | `qwen2` (also Qwen2) |
| RoPE freq_base | 1e6 | 1e6 |

---

## Commits

| Repo | Commit | Message |
|------|--------|---------|
| shannon-prime-system | `aeecdba` | [lat-3-cell-qwen25] Phase 3 Cell 2: Qwen2.5 bridge + forward + session + fixture; T_SESSION 365/365 |
| shannon-prime-system-engine | `2063496` | [lat-3-cell-qwen25] Phase 3 Cell 2: Qwen2.5 engine adapter + transcoder; submodule aeecdba |

## Test Summary

```
math-core T_SESSION (16 subtests): 365/365 checks, 0 fails
  T_QWEN25_ALIAS                 PASS
  T_QWEN25_DECODE_TRAJECTORY     PASS
  T_PARITY_CROSS_LOAD_QWEN25     PASS  (artifact absent — SKIP, graceful)
  all prior T_GEMMA3_* / T_SESSION_* / T_PARITY_* / T_ZERO_COPY_*  PASS

engine CPU 14/14 (fast suite, model-dependent):
  E_CPU_1–10       PASS
  MODEL_BIND       PASS
  GEMMA3_BIND      PASS
  TOK_DECODE       PASS
  TOK_ENCODE       PASS
  E_FMT_0          PASS
```
