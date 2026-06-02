# SESSION CLOSED — Phase 3-MoE: qwen35moe reference forward bit-exact (2026-06-02)

**Model:** Qwen3.6-35B-A3B (`qwen35moe`), `D:\Files\Models\lmstudio-community\Qwen3.6-35B-A3B-GGUF\Qwen3.6-35B-A3B-Q4_K_M.gguf` (19.7 GB, Q4_K_M).
**Oracle:** llama.cpp `5dcb711` — `g35moe_oracle.exe` (greedy) + `g35moe_oracle_dbg.exe` (cb_eval per-layer fingerprints).
**Result:** the full `qwen36_forward` (core/forward/qwen36.c) is **argmax bit-exact** to real Qwen3.6 — 3/3 non-trivial greedy tokens match (`5444 8 198`; the rest of the oracle sequence is prompt echo), and per-layer fingerprints match through every block.

## Architecture (corrected — see SPEC-qwen35moe-GDN.md)

NOT Mamba2. A **Gated DeltaNet (Qwen3-Next family) + MoE hybrid**. 40 layers: full-attn iff `(L+1)%4==0` (10 layers), else GDN (30). MoE FFN on every layer. No NextN/MTP block in this GGUF (tensor count `30*19 + 10*16 + 3 = 733` confirms nextn=0; the MTP head is the separate `-Draft` GGUF, a Phase 4-MTP hook).

Verified hparams: n_embd 2048, head 16/kv 2, head_dim 256, 256 experts/8 used, n_ff_exp/shexp 512, GDN conv_k 4 / state 128 / H_k 16 / H_v 32 / inner 4096, IMRoPE dim 64 base 1e7 sections [11,11,10,0], rms_eps 1e-6, tied=0 (has output.weight), vocab 248320, gpt2 BPE.

## Blocks implemented + validated

- **GDN (the novel kernel):** `qkv = wqkv·x`, `z = wqkv_gate·x`; `beta = sigmoid(ssm_beta·x)`; `gate = ssm_a·softplus(ssm_alpha·x + ssm_dt)`; causal depthwise conv1d (k=4) + SiLU; **L2-norm** (not RMS) on q,k; per-token gated delta-rule recurrence per v-head (kq head = `h % Hk`): `q*=1/√128; g=exp(gate); S⊙=g; sk=Σ_i S[i,j]k[i]; d=beta(v−sk); S[i,j]+=k[i]d[j]; o[j]=Σ_i S[i,j]q[i]`; gated output `RMSNorm(o,ssm_norm)·SiLU(z)`; `ssm_out·`. Validated: `conv_output_silu-0` and `linear_attn_out-0` match oracle within Q4-vs-f32 noise. **Bug found + fixed via fingerprints: beta was missing its sigmoid.**
- **MoE FFN:** f32 softmax over 256 → top-8 → renorm → `×expert_weights_scale` (router stays f32 — top-k is a discrete cliff, never quantized); rank-3 expert slices via `expert_mm` (row `(e*out+o)` of `[in,out,n_expert]`, f32 dequant dot) → SwiGLU, weighted accumulate; sigmoid-gated shared expert. Validated: `ffn_out-0` absum 8.022 vs 8.065, `l_out-0` 27.851 vs 27.797.
- **Gated full-attn + IMRoPE:** `wq→[query|gate]` (stride 2·HD); Q/K RMSNorm over HD=256; RoPE NEOX on first n_rot=64 dims (**IMRoPE reduces to NEOX for a text model** — all mrope position components equal the token position); GQA causal attn (16q/2kv, kq_scale 1/√256); `out *= sigmoid(gate)`; `wo·`. Validated: `l_out-3` absum 44.19 vs 44.49; end-to-end top-1.

## Math-core prereq added (Stage 1.5): k-quant dequant

`sp_dequant_row` + `row_bytes` only handled F32/F16/Q8_0. Added **Q4_K** (144 B/256) and **Q6_K** (210 B/256), transcribed bit-exactly from ggml (`get_scale_min_k4`; Q6_K ql/qh/scales − 32 bias). This leaf is REQUIRED by three consumers: the reference matmul, the **frobenius** arena packer (the discrete Z_q production path), and the **loader/transcoder** (GGUF→.sp-model). `SP_WDT_Q4_K=12`, `SP_WDT_Q6_K=14`.

## Validation methodology (per Knack's correction — important)

Expanding Q4→f32 and diffing against a Q4-native oracle is **NOT a bit-exactness proof** — the two run different numerical paths, so the residual is precision slop. The fingerprint comparison is a **wiring check** only: a wrong formula diverges O(10%), precision noise is O(0.01%), so it cleanly separates right-architecture from wrong (it earned its keep catching the beta bug). The **bit-exact gate is top-1 argmax** vs the oracle. Bit-exactness itself comes from the discrete Z_q substrate by construction; **production is the discrete path, never f32 expansion** (zero-copy invariant).

## Commits

core: `568b678` (model.h) → `83aa2e9` (load/bind, STAGE1_OK) → `25809d8` (k-quant) → `25913fa` (GDN) → `0257810` (MoE) → `a9e7150` (full-attn) → `d8e614f` (validated).
lattice: `00bdbde` (SPEC) + `b3e77f7` (oracle fingerprints fixture).

## Artifacts (permanent, for reuse)

- `papers/SPEC-qwen35moe-GDN.md` — the ground-truth architecture spec from llama's graph.
- `papers/qwen35moe-oracle-fingerprints.txt` — per-layer oracle block fingerprints (localization targets).
- `llama.cpp/g35moe_oracle{,_dbg}.{cpp,exe}` — greedy oracle + cb_eval fingerprint dumper.
- `shannon-prime-system/tests/qwen36_load_probe.c` (Stage 1) + `qwen36_fwd_probe.c` (greedy top-1).
- `core/forward/qwen36.c` — the reference forward (`SP_Q36_DBG=1` dumps fingerprints).

## Remaining (Stage 3 — production path)

1. Engine `sp_transcode`: Q4_K/Q6_K source `row_bytes` + **rank-3 expert tensor** packing (per-expert 2D Frobenius blocks).
2. Bridge `sp_model_to_qwen36` (const sp_model* → qwen3_model with the q36 layout).
3. End-to-end transcode → `sp_model_load` → forward; top-1 bit-exact.
4. Discrete **arena** (Z_q) path on Q4_K_M (SP_ARENA / FROB) — the production compute.
5. Formal `M_QWEN36` ctest (top-1 gate; PPL hits the f32-vs-Q4 smoke floor cf. M_GEMMA4).
