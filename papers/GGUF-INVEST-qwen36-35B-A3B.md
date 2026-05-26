# GGUF Investigation: Qwen3.6-35B-A3B (Phase 3-MoE scope)

**Date:** 2026-05-26  
**File:** `D:\Files\Models\lmstudio-community\Qwen3.6-35B-A3B-GGUF\Qwen3.6-35B-A3B-Q4_K_M.gguf`  
**Verdict:** Phase 3-SSM + Phase 3-MoE **combined** — both sub-phases required simultaneously. Cannot be built as an incremental delta from any existing bridge.

---

## Metadata

| Field | Value |
|-------|-------|
| `general.architecture` | `qwen35moe` |
| `general.name` | `Qwen_Qwen3.6 35B A3B` |
| `general.size_label` | `35B-A3B` |
| `block_count` | 40 |
| `context_length` | 262144 |
| `embedding_length` | 2048 |
| `attention.head_count` | 16 |
| `attention.head_count_kv` | 2 |
| `attention.key_length` | 256 (= head_dim for full-attn layers) |
| `expert_count` | 256 |
| `expert_used_count` | 8 (top-8 routing per token) |
| `expert_feed_forward_length` | 512 (per-expert FFN dim) |
| `expert_shared_feed_forward_length` | 512 (shared expert FFN dim) |
| `ssm.conv_kernel` | 4 |
| `ssm.state_size` | 128 |
| `ssm.group_count` | 16 |
| `ssm.time_step_rank` | 32 |
| `ssm.inner_size` | 4096 |
| `full_attention_interval` | 4 |
| `rope.freq_base` | 10,000,000 (1e7) |
| `rope.dimension_count` | 64 |
| `attention.layer_norm_rms_epsilon` | 1e-6 |
| `tokenizer.ggml.model` | gpt2 (BPE) |
| `tokenizer.ggml.pre` | qwen35 |
| Vocab size (token_embd cols) | 248,320 |
| Tensor count | 733 |
| KV metadata count | 41 |
| Tied embeddings | yes (`token_embd.weight` = `output.weight` columns at same count) |

**GGUF arch detection:** `strcmp(arch, "qwen35moe") == 0` — not caught by any existing `qwen3`/`qwen2` guard.

---

## Layer Type Distribution

- **Total layers:** 40  
- **Full-attention layers (10):** `L % 4 == 3` → indices 3, 7, 11, 15, 19, 23, 27, 31, 35, 39  
- **SSM layers (30):** all other indices → 0,1,2, 4,5,6, 8,9,10, 12,13,14, …  

Pattern: three consecutive SSM blocks followed by one full-attention block, repeating 10 times.

**MoE FFN: present on ALL 40 layers** (both SSM and full-attn).

---

## Tensor Layout

### Global tensors (3)

| Name | Dtype | Shape |
|------|-------|-------|
| `token_embd.weight` | Q4_K | [2048, 248320] |
| `output_norm.weight` | F32 | [2048] |
| `output.weight` | Q6_K | [2048, 248320] |

### Per-layer: SSM block (blk.0 representative, 30 layers)

| Tensor | Dtype | Shape | Note |
|--------|-------|-------|------|
| `attn_norm.weight` | F32 | [2048] | pre-block RMSNorm |
| `attn_qkv.weight` | Q6_K | [2048, 8192] | fused QKV input for SSM expansion |
| `attn_gate.weight` | Q4_K | [2048, 4096] | SSM output gate [n_embd → ssm_inner] |
| `post_attention_norm.weight` | F32 | [2048] | post-block norm |
| `ssm_a` | F32 | [32] | log-dt bias (A param, per time_step_rank) |
| `ssm_alpha.weight` | Q4_K | [2048, 32] | input→state gate [n_embd, time_step_rank] |
| `ssm_beta.weight` | Q4_K | [2048, 32] | state→output gate [n_embd, time_step_rank] |
| `ssm_conv1d.weight` | F32 | [4, 8192] | causal conv [conv_kernel, ssm_inner_size] |
| `ssm_dt.bias` | F32 | [32] | time-step bias [time_step_rank] |
| `ssm_norm.weight` | F32 | [128] | SSM state norm [state_size] |
| `ssm_out.weight` | Q4_K | [4096, 2048] | SSM→hidden project [ssm_inner, n_embd] |
| `ffn_gate_inp.weight` | F32 | [2048, 256] | MoE router [n_embd, n_experts] |
| `ffn_gate_inp_shexp.weight` | F32 | [2048] | shared-expert gate bias [n_embd] |
| `ffn_gate_exps.weight` | Q4_K | [2048, 512, 256] | gate proj, 256 experts |
| `ffn_up_exps.weight` | Q4_K | [2048, 512, 256] | up proj, 256 experts |
| `ffn_down_exps.weight` | Q6_K | [512, 2048, 256] | down proj, 256 experts |
| `ffn_gate_shexp.weight` | Q4_K | [2048, 512] | shared expert gate |
| `ffn_up_shexp.weight` | Q4_K | [2048, 512] | shared expert up |
| `ffn_down_shexp.weight` | Q6_K | [512, 2048] | shared expert down |

**19 tensors per SSM layer.**

### Per-layer: Full-attention block (blk.3 representative, 10 layers)

| Tensor | Dtype | Shape | Note |
|--------|-------|-------|------|
| `attn_norm.weight` | F32 | [2048] | pre-block RMSNorm |
| `attn_q.weight` | Q4_K | [2048, 8192] | Q proj [n_embd, n_heads*head_dim] |
| `attn_k.weight` | Q4_K | [2048, 512] | K proj [n_embd, n_kv*head_dim] |
| `attn_v.weight` | Q6_K | [2048, 512] | V proj [n_embd, n_kv*head_dim] |
| `attn_output.weight` | Q4_K | [4096, 2048] | out proj [n_heads*head_dim, n_embd] |
| `attn_q_norm.weight` | F32 | [256] | QK norm [head_dim] |
| `attn_k_norm.weight` | F32 | [256] | QK norm [head_dim] |
| `post_attention_norm.weight` | F32 | [2048] | post-block norm |
| (same 8 MoE FFN tensors as SSM layer) | … | … | |

**16 tensors per full-attention layer** (8 attn + 8 MoE FFN).

---

## Key Architectural Surprises

### 1. SSM is the dominant block type (75% of layers)
30 of 40 layers are Mamba2-style SSM blocks. Full attention is the minority (10 layers). The `full_attention_interval=4` means one full-attention per 4-layer group.

### 2. SSM layers use fused QKV input
SSM layers have `attn_qkv.weight` [2048, 8192] feeding the Mamba2 expansion — **not** a standard attention QKV split. The `attn_gate.weight` is the output gate for the SSM block, not an attention projection.

### 3. MoE FFN on every layer — no dense FFN exists
Every layer (SSM and full-attn alike) uses the 8-tensor MoE FFN. This is a Mixture-of-Experts across the entire depth of the model.

Expert sharding: `ffn_{gate,up,down}_exps.weight` are 3D tensors [in, out, 256]. The transcoder and adapter must handle 3D quant tensors, which no existing bridge code does.

### 4. Full-attention layers are nearly identical to Qwen3
Full-attn layers (L%4==3) use separate Q/K/V + QK norms (same pattern as Qwen3-0.6B), with no biases. RoPE applied with freq_base=1e7. The only new element is the MoE FFN replacing the dense SwiGLU.

### 5. GGUF arch string is novel
`general.architecture = "qwen35moe"` — not caught by any existing `strcmp` guard in `model.c` or `sp_transcode.c`.

---

## Implementation Scope (Phase 3-SSM+MoE combined)

This is a two-sub-phase problem that cannot be decomposed:

| Component | New work |
|-----------|----------|
| Arch enum | `SP_ARCH_QWEN36` (or `SP_ARCH_QWEN35MOE`), `SP_ARCH_ID_QWEN36` |
| GGUF detection | `strcmp(arch, "qwen35moe") == 0` in `model.c` |
| Model struct | `qwen36_layer`: bifurcated SSM vs full-attn per layer, plus MoE FFN fields for all |
| SSM forward | Mamba2 state-space computation: conv1d → ssm_a/alpha/beta/norm/out; completely new code path |
| MoE router | top-8 gating over 256 experts + 1 shared expert; SwiGLU per-expert |
| Adapter | `sp_model_to_qwen36`: must handle 3D quant tensors (rank-3 `gguf_tensor`) |
| Transcoder | 3D expert tensors serialized as F32 or custom 3D Q-format |
| Tests | `qwen36_fixture`: synthetic MoE+SSM model; decode trajectory test |

**Estimated delta:** 4–6× the complexity of the Qwen2.5 cell.  
**Phase:** Phase 3-SSM + Phase 3-MoE combined → label `Phase 3-MoE+SSM` or `Phase 3-qwen36`.

---

## Verdict

Qwen3.6-35B-A3B cannot be implemented as an incremental delta from any existing bridge. The two deferred sub-phases (3-SSM and 3-MoE) are tightly coupled in this architecture and must be addressed together. The Gemma4 and Qwen3.6 deferrals both stand; the correct sequencing is:

1. Phase 3-attn: **CLOSED** (`lat-phase-3-attn-closed`) — Gemma3 + Qwen2.5
2. Phase 3-G4: Gemma4 (dual head_dim + per-layer embedding)
3. Phase 3-MoE+SSM: Qwen3.6 (this model)
4. Phase 3-FP8: FP8 quantization path
