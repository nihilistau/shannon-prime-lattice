# SESSION-CLOSED: lat-phase-3-cell-gemma3

**Date:** 2026-05-26  
**Tag:** `lat-phase-3-cell-gemma3-closed` (shannon-prime-system + engine)  
**Branch:** main  
**Result:** CLOSED — 249/249 math-core checks; 27/27 engine CPU tests

---

## Deliverables

### A. sp_model_to_gemma3 bridge (math-core: core/session/sp_model_bridge.c)

Zero-copy bridge mirroring Fix-B (alias_mask=0x3 on codes+row_scale). Reconstructs
a `qwen3_model` from a loaded `.sp-model` handle for Gemma3 architecture:

- 13 synthetic tensors per layer: 7 matmul (attn_q/k/v/output, ffn_gate/up/down)
  + 6 f32 norms (attn_norm, attn_q_norm, attn_k_norm, post_attention_norm, ffn_norm,
  post_ffw_norm). GGUF names match exactly what the engine transcoder writes.
- arch guard: returns NULL if `ai.arch_id != SP_ARCH_ID_GEMMA3`
- tied LM head: `qm->output == qm->token_embd` (same arena entry)
- NSYN = 2 + has_output_w + 13*NL; NARENA = 1 + has_output_w + 7*NL; NNORM = 1 + 6*NL

### B. Session dispatch (math-core: core/session/sp_session.c)

- `sp_session_create`: moved `sp_model_arch` query before `sp_model_borrow_qm`; dispatches
  to `sp_model_to_gemma3` vs `sp_model_to_qwen3` on `ai.arch_id`.
- `kv_step_gemma3`: single-token step with:
  - Embedding scale: `sqrt(n_embd)` applied after `sp_embed_row` (unconditional)
  - Sandwich norms: `sp_rmsnorm(ap, post_attn_norm)` + add to residual; same for post_ffw_norm
  - GeGLU: `gelu_tanh(gg[i]) * up[i]` (vs SwiGLU in Qwen3)
  - Dual RoPE base: global layers (`L%6==5`) use `rope_freq_base` (1e6); local use 10000.0f
  - SWA via `sp_attn_head(..., win, ...)`: `win=-1` for global, `win=sliding_window` for local
  - All 3 KV modes: f32, Spinor block, f32+roundtrip
- `sp_prefill_chunk`: dispatches `gemma3_forward` vs `qwen3_forward` on `cfg.arch`
- `sp_decode_step`: dispatches `kv_step_gemma3` vs `kv_step_qwen3`

### C. gemma3_fixture.c/h (math-core: core/session/)

Tiny Gemma3-shaped `.sp-model` + `.sp-tokenizer` builder for unit tests:
- NL=2, E=32, FF=64, NH=4, NKV=2, HD=8, V=48
- arch: SP_ARCH_ID_GEMMA3, ffn_variant=1 (GeGLU), norm_variant=1 (sandwich),
  swa_window=512, tied_embeddings=1, has_qk_norm=1
- 13 tspec entries per layer (7 Q8 pairs + 6 F32 norms)

### D. Tests (math-core: core/session/session_test.c)

- **T_GEMMA3_ALIAS**: confirms alias_mask==0x3 on codes+row_scale, arch==GEMMA3
- **T_GEMMA3_DECODE_TRAJECTORY**: session argmax matches `gemma3_forward` O(n²) reference
  for 100 auto-regressive steps (100-token NPROMPT seed → NGEN steps)
- **T_PARITY_CROSS_LOAD_GEMMA3**: loads engine-transcoded Gemma3-1B
  (build-cpu/tests/gemma3_rt.sp-model); verifies n_layers=26, hidden_dim=1152,
  n_heads=4, n_kv_heads=1, head_dim=256, swa_window>0, preferred_precision=FP16;
  prefill 4 tokens → all logits finite; argmax=107

---

## Design Note: embd_prescaled Revert (Option A)

During implementation, a `embd_prescaled` flag was considered to skip the
`xt[i] *= embscale` loop in `gemma3_forward` when the transcoder pre-multiplied
`token_embd.weight.scale` by `sqrt(n_embd)`. This was reverted because:

**Tied LM head breaks logits**: Gemma3's `output == token_embd` means the same
arena entry is used for embedding lookup (correct: yields values ×√n_embd) AND
for LM head projection (`sp_matmul(output, ...)` — wrong: logits ×√n_embd instead
of ×1). All V logits are multiplied by √n_embd ≈ 33.94. Argmax is preserved
(trajectory tests pass) but softmax/PPL/T_FRO_4 would fail.

**Option A chosen**: Keep `gemma3_forward`'s unconditional `xt[i] *= embscale` loop
(O(E) per token, trivial cost). No pre-scaling. No `embd_prescaled` field. No
transcoder mutation.

---

## Commits

| Repo | Commit | Message |
|------|--------|---------|
| shannon-prime-system | `0ec01e4` | [lat-3-cell-gemma3] session: Gemma3 bridge + dispatch + tests; T_SESSION 249/249 |
| shannon-prime-system-engine | `89a5b98` | bump submodule: shannon-prime-system -> 0ec01e4 (lat-3-cell-gemma3) |

## Test Summary

```
math-core T_SESSION (16/16 module suite): 249/249 checks, 0 fails
  T_GEMMA3_ALIAS                 PASS
  T_GEMMA3_DECODE_TRAJECTORY     PASS
  T_PARITY_CROSS_LOAD_GEMMA3     PASS  [G3-cross] n_ff=6912 rms_eps=1.00e-06 swa=512 prec=2, argmax=107

engine CPU 27/27:
  GEMMA3_BIND      PASS   (26 layers fully bound incl. sandwich + QK norms)
  M_GEMMA3_CPU     PASS   (PPL gate)
  E_FMT_1..4      PASS   (Gemma3 transcode + verify)
  E_FMT_4_QWEN3   PASS
  T_FRO_4         PASS   (PPL gate, 189s)
  all others      PASS
```
