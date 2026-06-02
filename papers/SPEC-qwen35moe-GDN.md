# SPEC: qwen35moe (Qwen3.6-35B-A3B) — Phase 3-MoE+GDN ground truth

**Date:** 2026-06-02
**Oracle:** llama.cpp `5dcb711`, `src/models/qwen35moe.cpp` + `delta-net-base.cpp` (read, not guessed).
**Model:** `D:\Files\Models\lmstudio-community\Qwen3.6-35B-A3B-GGUF\Qwen3.6-35B-A3B-Q4_K_M.gguf` (19.7 GB, 733 tensors, 41 KV).
**Supersedes the architecture claim in `GGUF-INVEST-qwen36-35B-A3B.md`** (which mislabeled the linear layers as "Mamba2 SSM" from metadata-key inspection without reading the compute graph).

---

## HEADLINE CORRECTION — it is NOT Mamba2 SSM

The 30 non-attention layers are **Gated DeltaNet (GDN) linear attention** — the **Qwen3-Next family** (same `llm_build_delta_net_base` / `ggml_gated_delta_net` op shared with `qwen3next.cpp` and `kimi-linear.cpp`). The `ssm.*` GGUF keys are *reused* to carry GDN params; the computation is a **gated delta-rule recurrence**, not a Mamba selective scan. Building a Mamba2 kernel would be wrong.

---

## Verified hparams (from oracle metadata dump)

| field | value |
|---|---|
| `general.architecture` | `qwen35moe` |
| block_count | 40 (+1 NextN/MTP block loaded-not-run) |
| embedding_length | 2048 |
| attention.head_count / kv | 16 / 2 |
| attention.key_length / value_length | 256 / 256 (full-attn head_dim) |
| rope.dimension_count | 64 |
| rope.freq_base | 1e7 |
| rope.dimension_sections (IMRoPE) | [11, 11, 10, 0] (sum 32 = n_rot/2) |
| full_attention_interval | 4 → full-attn iff `(i+1) % 4 == 0` (i=3,7,…,39); else GDN |
| expert_count / used | 256 / 8 |
| expert_feed_forward_length | 512 (per-expert n_ff) |
| expert_shared_feed_forward_length | 512 (shared expert n_ff) |
| ssm.conv_kernel | 4 |
| ssm.state_size | 128 (= GDN head_dim S) |
| ssm.group_count | 16 (= n_k_heads H_k) |
| ssm.time_step_rank | 32 (= n_v_heads H_v / dt_rank) |
| ssm.inner_size | 4096 (= d_inner = H_v·head_v_dim) |
| rms_eps | 1e-6 |
| tokenizer | gpt2 BPE, pre=`qwen35`, vocab 248320, tied embeddings |
| gating func | SOFTMAX, norm_topk=true |

Oracle top-1 baseline (fixed prompt `785 3974 13876 38835 35308 916`, greedy):
**`5444, 8, 198, 785, 3974, 13876, 38835, 35308`** (settles into echoing the prompt — deterministic target).

---

## Layer forward (trunk, per layer `il` in [0,40))

```
inpSA = inpL
cur   = RMSNorm(inpL, attn_norm)                      # pre-norm
if is_recurrent(il):   cur = GDN_block(cur, il)       # 30 layers
else:                  cur = full_attn_block(cur, il) # 10 layers, (il+1)%4==0
cur          = cur + inpSA                            # attn residual
ffn_residual = cur
cur = RMSNorm(cur, attn_post_norm)                    # POST-attn norm feeds FFN
cur = MoE_FFN(cur, il)                                # routed + shared expert
cur = cur + ffn_residual                              # FFN residual
inpL = cur
# after all layers: RMSNorm(output_norm) -> LM head (tied). No logit softcap.
```

### GDN block (the hard, novel kernel)

```
qkv_mixed = wqkv · x                 # [n_embd -> key_dim*2 + value_dim]; key_dim=H_k*S=16*128, value_dim=H_v*128=4096
z         = wqkv_gate · x            # [n_embd -> value_dim]
beta  = sigmoid(ssm_beta · x)                         # [H_v] per token
alpha = ssm_alpha · x                                 # [H_v]
gate  = ssm_a * softplus(alpha + ssm_dt)              # [H_v]  (g; = -exp(A_log)*softplus, negative)
# causal depthwise conv over the qkv channel mix, kernel=4, then SiLU:
conv  = SiLU( ssm_conv(concat(conv_state, qkv_mixed), ssm_conv1d) )   # conv_channels = d_inner + 2*H_k*S
q,k,v = split(conv)                  # q,k: [S=128, H_k=16]; v: [S=128, H_v=32]
q = L2norm(q); k = L2norm(k)         # ggml_l2_norm (NOT RMS), eps=1e-6
o = gated_delta_net(q,k,v, g=gate, b=beta, state)     # recurrence below
out = RMSNorm(o, ssm_norm) * SiLU(z)                  # gated output norm (build_norm_gated)
cur = ssm_out · out                  # [value_dim -> n_embd]
```

**Autoregressive gated delta-rule recurrence** (per token; the math-core reference — `build_delta_net_autoregressive`). State `S` is `[S_v, S_v, H_v]` = `[128,128,32]` per seq. Scalar decay `g` per head, scalar `beta` per head:

```
q *= 1/sqrt(S_k)            # S_k = 128
g  = exp(g)                 # decay in (0,1)
S  = S ⊙ g                  # decay state (broadcast scalar-per-head)
sk = sum_rows(S ⊙ k)        # S^T k          -> [1, S_v, H_v]
d  = beta * (v - sk^T)      # delta          -> [S_v, 1, H_v]
S  = S + (k ⊗ d^T)          # rank-1 update  (k repeated over S_v)
o  = sum_rows(S ⊙ q)        # S^T q  readout -> [S_v, H_v]
```
Grouping: H_v=32 v-heads, H_k=16 k/q-heads → each k/q head serves H_v/H_k = 2 v-heads (GQA-style broadcast). Chunked (`build_delta_net_chunking`) and fused (`ggml_gated_delta_net`) forms are math-equivalent prefill optimizations; the reference uses the per-token AR form for correctness, validated against the chunked oracle.

### Full-attention block (10 layers; mostly Qwen3 + a gate)

```
Qfull = wq · x                       # outputs [query | gate] interleaved, 2*head per head
Q     = view(query half);  gate = view(gate half)
Q = RMSNorm(Q, attn_q_norm)          # over head_dim=256
K = RMSNorm(reshape(wk·x), attn_k_norm); V = wv·x
Q,K = IMRoPE(Q,K, sections=[11,11,10,0], dim=64, base=1e7)   # ggml_rope_multi
attn = build_attn(Q,K,V, kq_scale = 1/sqrt(256))             # GQA 16 q / 2 kv
attn = attn * sigmoid(gate)          # output gate (Qwen3-Next)
cur  = wo · attn
```

### MoE FFN (all 40 layers) — f32 router, Z_q experts

```
# ROUTER — stays f32 (discrete top-k cliff; do NOT quantize):
logits = ffn_gate_inp · x            # [256]
p      = softmax(logits)             # SOFTMAX gating
idx, w = top8(p)                     # 8 expert indices + weights
w      = w / sum(w)                  # norm_topk = true
w     *= expert_weights_scale        # (read from GGUF/hparams; default 1.0)
# ROUTED experts (weights in Z_q / Frobenius):
moe = sum_{j in idx}  w_j * down_j( SiLU(gate_j·x) * (up_j·x) )   # SwiGLU, n_ff_exp=512
# SHARED expert (always on), sigmoid-gated:
sh  = down_sh( SiLU(gate_sh·x) * (up_sh·x) )                       # n_ff=512
sh *= sigmoid(ffn_gate_inp_shexp · x)                             # scalar gate per token
ffn = moe + sh
```

---

## NextN / MTP block

One extra block (`nextn_predict_layers`) is appended: a full-attn + MoE decoder block with `nextn.{eh_proj,enorm,hnorm,embed_tokens,shared_head_*}`. **Loaded but NOT executed** in the main forward (`n_transformer_layers = n_layer - nextn_predict_layers`). It is the self-draft head for **Phase 4-MTP** — wire later; ignore for the base forward gate. The `Qwen3.6-35B-A3B-Draft` GGUF is the speculative-decode pairing.

---

## Corrections applied to the Gemini "MoE pull-back" proposal

1. **Right:** math-core reference first as the byte-exact oracle target; per-expert 2D Frobenius packing of the rank-3 expert tensors.
2. **Wrong — architecture:** it's GDN linear attention, not Mamba2 SSM. (Above.)
3. **Wrong — router quantization:** the router/gates are f32 plumbing (softmax→top8→renorm→scale; sigmoid gates). Quantizing to Z_q flips the top-8 selection (a discrete cliff, like the gemma4 softcap lesson) and diverges from the oracle. Only the **expert weight matmuls** are Z_q/Frobenius.
4. **Incomplete:** Gemini omitted the GDN path (30/40 layers), gated full-attn + IMRoPE, and the shared-expert sigmoid gate — without these there is no runnable forward to validate.
5. **Framing:** there is no Hexagon MoE to "pull back"; math-core is where this starts by design. DSP is a later backend.
6. **Sequencing:** `sp_packer_3d` is the easy, late piece — pack AFTER the forward spec is locked, not first (the gemma4 "don't lay out blind" lesson).

## Staging

- Stage 0 (this doc + oracle + cb_eval fingerprints).
- Stage 1: arch enum + `qwen35moe` detection + bifurcated model struct.
- Stage 2a: GDN forward (validate vs `attn_output`/`linear_attn_out` per layer).
- Stage 2b: gated full-attn + IMRoPE (vs `attn_output` on full-attn layers).
- Stage 2c: MoE FFN router + experts + shared (vs `ffn_moe_out`/`ffn_out`).
- Stage 3: rank-3 expert transcode + `.sp-model` load → top-1 bit-exact → `M_QWEN36` PPL gate (Q4-only → f32-vs-Q4 smoke floor, cf. M_GEMMA4).
