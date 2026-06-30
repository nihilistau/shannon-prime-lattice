---
type: design
title: "Telepathy — scoping the minimal Qwen forward (the cross-family destination, the one true-live gap)"
description: "Ruthlessly-scoped plan for the last mile of Telepathy: a minimal Qwen2 forward that unfolds the injected embedding-prefix and streams the delegate response. Grounded divergence map (engine's Gemma-3-12B vs Qwen2), a v1 sidecar / v2 native-fp16 / v3 exact tiering, the inputs_embeds entry seam, gates + kill criteria, and explicit out-of-scope. Key finding: Qwen2 is architecturally SIMPLER than Gemma-3 — the integration is mostly subtraction + one addition (QKV bias)."
tags: [design, telepathy, qwen, forward, scope, cross-model, latent-bridge]
timestamp: 2026-06-30T00:00:00Z
resource: shannon-prime-lattice/papers/PPT-LAT-TELEPATHY-Qwen-forward-SCOPE.md
sp_status: DRAFT
sp_gate: "scoping doc (no code this pass); gates defined in §6"
sp_commit: TBD
sp_repro: "configs verified from HF cache: Qwen/Qwen2.5-Coder-0.5B-Instruct + google/gemma-3n-E2B-it (text_config); engine target = Gemma-3-12B (hidden 3840)"
---

# Telepathy — scoping the minimal Qwen forward

**Status:** DRAFT scope for review. **Author:** Claude (SP hat), 2026-06-30. This is the plan for the
**one true-live gap** in Telepathy: every gate that decides *whether/what* to transmit is GREEN
(TELE-1..7), but the daemon has no Qwen forward, so a fully-live Gemma→Qwen *transmit* doesn't run
in-engine yet. This doc scopes the least work that closes it without risking the byte-exact Gemma path.

> **Receipts-first.** Configs below are read from the HF cache (`config.json`), not memory. The engine's
> served model is **Gemma-3-12B** (hidden 3840 — the `feat` dim the heads probe); the bridge's *source*
> latents were gemma-3n-E2B (a different Gemma), but the **engine forward** to compare against is Gemma-3.

## 0. The headline finding (it shrinks the scope)

**Qwen2 is architecturally *simpler* than Gemma-3.** The engine's Gemma-3 forward already implements the
hard parts; Qwen2 *removes* almost all of them and *adds* exactly one thing (QKV bias). So the minimal
Qwen forward is mostly **subtraction** from what the engine can already do — not a new class of complexity.

## 1. Divergence map (engine Gemma-3-12B vs Qwen2-0.5B) — verified from configs

| feature | Gemma-3 (engine) | Qwen2.5-Coder-0.5B | for the Qwen path |
|---|---|---|---|
| attention pattern | **alternating local(SWA 1024)/global**, 2 RoPE θ (10k local / 1M global) | **uniform full attention**, single θ=1e6 (`use_sliding_window=false`) | **drop** local/global split + SWA → simpler |
| QK-norm | **yes** (RMSNorm on Q,K) | **no** | **drop** |
| RMSNorm form | **(1+weight)** offset | **standard** (weight) | use standard RMSNorm |
| norms / layer | **4** (input, post-attn, pre-FFN, post-FFN) | **2** (input, post-attn) | use 2 |
| MLP activation | **GeGLU** (gelu_pytorch_tanh) | **SwiGLU** (silu) | use SiLU |
| embedding scale | **×√hidden** | **none** | skip (and we inject embeds directly) |
| logit soft-cap | **final cap 30** | **none** | skip |
| **attention bias** | **none** | **QKV bias = true** (o_proj none) | **ADD** — the one Qwen-only piece |
| dims | 3840, head_dim 256 | hidden 896, 24 layers, 14 Q / 2 KV heads, head_dim 64, ffn 4864 | Qwen config |
| vocab / tie | tied | vocab 151936, **tied** lm_head | tied lm_head |
| attn scale | query_pre_attn_scalar | 1/√64 | standard 1/√head_dim |

Net: **8 things to drop, 1 to add (QKV bias), 2 to swap (GeLU→SiLU, (1+w)→standard RMSNorm).**

## 2. The integration decision (answers "how to handle the divergences in the Gemma backend")

**Do NOT fold Qwen into the Gemma kernels.** The Gemma forward is byte-exact and hyper-tuned; flag-
overloading it with Qwen's variants is the fast path to a Gemma regression and exactly the bloat to avoid.
Instead, a **separate Qwen2 forward path** that *reuses the primitive kernels* (cublas gemm, RMSNorm,
RoPE, softmax attention) assembled per Qwen's (simpler) config. Qwen-specific code is small and local:
the QKV-bias add, SiLU, standard RMSNorm, uniform RoPE θ=1e6. The Gemma path is **untouched** (zero
regression risk — its gates stay green by construction).

## 3. Tiering — CORRECTED (operator tip, 2026-06-30): the native forward ALREADY EXISTS

> **Correction.** The original v1/v2 below assumed the engine had no Qwen forward and reached for an HF
> sidecar. That was wrong (asserted without grepping the C core). **The engine already runs Qwen
> natively** — verified: `qwen3_forward_cuda` / `qwen3_forward_cuda_ex` (`include/sp_engine/cuda_backend.h`),
> `qwen3_generate_kv` (the shared decode, `core/forward/decode.c`), the **embedding-sequence inject**
> `gemma4_kv_inject_seq(s, embs, n_frames, ph)` ("the GENERIC residual-frame channel, already in the
> engine"), and **`qwen25-coder-0.5b-memory.sp-model` is transcoded and already loaded/run in the MeMo
> path** (`sp_memo_m1_smoke`). `qwen3_model` is the *unified* model type (Gemma + Qwen). So the native
> path is the v1.

- **v1 — NATIVE in-engine transmit (no sidecar, no new forward).** Assemble existing verbs: load
  `qwen25-coder-0.5b-memory.sp-model` → `qwen3_model`; `gemma4_kv_open` on it; the `LatentBridge` maps the
  Gemma latent → Qwen embedding space (the `W_emb` adapter, saved `telepathy_adapter_g2q_emb.npz`);
  inject the mapped prefix via **`gemma4_kv_inject_seq`**; decode with `qwen3_generate_kv` / the
  `gemma4_kv_decode*` verbs; stream back. **Pure glue over proven engine primitives — no HF, no new
  kernel, Gemma path untouched.** Footprint: the 0.5B sp-model (~0.5 GB Q-packed). This is the real
  minimal-viable forward; the §1 divergences are already handled by the engine's qwen3 path.
- **v0 — HF sidecar (`telepathy_sidecar.py`): DEMOTED to optional prototype/fallback.** Kept for
  cross-checking the native forward against HF (a parity oracle), not for production. Superseded by v1.
- **v2 — exactness (optional, later).** The native decode is the engine's standard path; if the delegate
  must be byte-exact/auditable like the Gemma forward, that is the engine's existing exact-integer
  machinery applied to the qwen3 path — a sovereignty nicety, not required to transmit.

## 4. Minimal-viable forward spec (v1 sidecar, and the v2 contract)

- **Entry seam = `inputs_embeds`**, not token ids: the bridge produces Qwen-embedding-space soft tokens
  (the `W_emb` readable-prefix), so the forward consumes the prefix embeddings directly (skip
  `embed_tokens` for the prefix), optionally followed by a short task prompt's embeddings.
- forward: prefix → Qwen2 decoder stack → tied lm_head → logits → sample → stream.
- decode: naive autoregressive + a basic KV cache; greedy or temperature sample; SSE stream back to the
  daemon. No batching.
- **Out of scope (explicitly):** Qwen as a general served chat endpoint; batching; the full sampler
  suite; quantization; exact-integer islands (v3); reverse qwen→gemma; speculative decode. v1 is *only*
  the delegate-forward for a routed Telepathy transmit.

## 5. Data flow (live, v1)

```
served Gemma-3-12B turn → draft-body latent → Route head (decide_route)
   ├─ LOCAL  → normal Gemma decode (unchanged, the default/null floor)
   └─ TELEPATHY → LatentBridge.transfer (gemma→qwen embedding space, W_emb)
                 → Qwen sidecar: inputs_embeds = mapped prefix → decode → stream tokens
                 → daemon merges the delegate stream into the response
```

## 6. Gates + kill criteria

- `G-QWEN-FWD-PARITY` — the engine/sidecar Qwen forward matches HF Qwen logits on a fixed prompt
  (v1: trivially true, same HF model; v2: fp16 forward vs HF within tol). *Kill: v2 logits diverge beyond
  fp16 tol from HF.*
- `G-TELEPATHY-LIVE` — end-to-end: a routed `TELEPATHY` turn produces a coherent delegate continuation
  from the **injected embedding-prefix** (not a re-tokenized prompt), streamed back. *Kill: the delegate
  output ignores the prefix (no better than an empty prefix) — would mean the live inject path is broken.*
- `G-TELEPATHY-NULLFLOOR` (already the law) — `SP_TELEPATHY` off / `route=LOCAL` ⇒ the served Gemma path
  is byte-identical to today. *Kill: any Gemma-path diff.*
- Route safety is already gated (TELE-7: false-fire 0.000) — the gate won't fire spuriously.

## 7. Recommendation (CORRECTED)

Take **v1 — the NATIVE in-engine transmit** (§3 corrected): it reuses the engine's *existing* qwen3
forward (`qwen3_forward_cuda` / `qwen3_generate_kv`), the *existing* embedding-sequence inject
(`gemma4_kv_inject_seq`), the *already-transcoded* `qwen25-coder-0.5b-memory.sp-model`, and the
`LatentBridge` + `W_emb` adapter we already built — pure glue, no HF, no new kernel, Gemma path
untouched. The HF sidecar is kept only as a parity oracle. The governance work (TELE-7, false-fire
0.000) is what lets us open this gate *safely*: the Route head decides, the bridge transfers, the engine's
qwen3 decode unfolds the prefix, and `LOCAL` remains a strict null floor.

**Lesson banked:** check the C core before declaring an engine capability missing — the native Qwen
forward was already there; the operator caught the over-scope.

## 8. Open questions
- Sidecar transport: subprocess stdout vs a local socket vs a tiny persistent HTTP runner? (latency vs simplicity)
- Does the delegate stream merge into the *same* SSE response, or surface as a labelled sub-turn?
- v2 KV-cache: reuse the engine's KV ring abstraction, or a Qwen-local cache? (the ring is Gemma-shaped)
