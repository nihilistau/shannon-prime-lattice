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

## 3. Tiering — ship the live transmit first, optimize later

- **v1 — Qwen SIDECAR (recommended, minimal-viable, ~days, ZERO engine risk).** Productionize the
  already-proven `telepathy_prefix.py` (HF Qwen, embedding-prefix inject + unfold + stream — TELE-5) as a
  small callable runner. The daemon's `LatentBridge`, on `decide_route → Telepathy`, hands the
  embedding-prefix to the sidecar (subprocess/local socket); the sidecar streams the delegate tokens back
  into the daemon's SSE. **This makes the full Gemma→Qwen transmit live end-to-end with no change to the
  Gemma engine.** It is the honest "minimal viable forward" — the forward already exists and is gated.
- **v2 — NATIVE fp16 Qwen forward in the engine (the heavy mile, only if v1 proves value).** A dedicated
  `qwen2_forward` (separate path, §2) in **fp16 cublas** — no exact-integer islands (the bridge is float;
  exactness is not required to transmit). 0.5B in fp16 ≈ 1 GB. Removes the Python dependency, gives
  in-process latency. Divergences handled explicitly per §1.
- **v3 — EXACT-INTEGER Qwen (optional, later).** Only if the *delegate's* output must be byte-exact /
  auditable like the Gemma path: re-derive the SiLU + standard-RMSNorm islands on the dual-prime CRT-NTT.
  Not needed for the capability; a sovereignty/auditability nicety.

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

## 7. Recommendation

Take **v1 (the sidecar)** first: it closes the one true-live gap end-to-end in days with **zero risk to
the byte-exact Gemma engine**, reusing the exact embedding-prefix path already proven in TELE-5. Promote
to **v2 (native fp16)** only once a live routed transmit demonstrates the value and we want to drop the
Python dependency. **v3 (exact)** stays in the drawer unless the delegate must be auditable. The whole
point of the Latent-Interceptor governance work (TELE-7) is that we can now open this gate *safely* — the
Route head decides, the bridge transfers, the sidecar unfolds, and `LOCAL` remains a strict null floor.

## 8. Open questions
- Sidecar transport: subprocess stdout vs a local socket vs a tiny persistent HTTP runner? (latency vs simplicity)
- Does the delegate stream merge into the *same* SSE response, or surface as a labelled sub-turn?
- v2 KV-cache: reuse the engine's KV ring abstraction, or a Qwen-local cache? (the ring is Gemma-shaped)
