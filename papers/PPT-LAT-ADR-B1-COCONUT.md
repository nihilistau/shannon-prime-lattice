---
type: design
title: "ADR-B1 — Coconut continuous-thought latent decode channel (SP_COCONUT)"
description: "Design for a byte-exact, ADR-002-native latent 'thinking' channel on the served 12B: after prefill, run N continuous thoughts (feed the last position's post-final-norm hidden state back as the next input residual, advancing the KV by one slot per thought) BEFORE decoding the answer — Coconut (arXiv 2412.06769). Recon verdict: pure Rust glue over existing FFI verbs (kv::capture_feat_arm reads h_t=post-output_norm d_model=3840 f32; kv::inject_frames feeds it back + advances KV; kv::decode_step resumes). No new CUDA. Splits into G-COCONUT-ENGINE (mechanism: null-floor + determinism + ρ<1 stability + no-crash, gateable now) and G-COCONUT-LIFT (accuracy beats n=0, needs a curriculum finetune). Respects TELE-12 (thoughts are a SEPARATE span, answer decoded cleanly after — sequential, never fused)."
tags: [design, adr, coconut, latent-reasoning, continuous-thought, decode, kv, byte-exact, sp-coconut, b1, okf]
timestamp: 2026-07-08T00:00:00Z
resource: shannon-prime-lattice/papers/PPT-LAT-ADR-B1-COCONUT.md
sp_status: DESIGN
sp_gate: "G-COCONUT-ENGINE (mechanism, this session) + G-COCONUT-LIFT (accuracy, finetune sprint)"
sp_commit: TBD
sp_repro: "engine: SP_COCONUT=N on the served daemon; gate harness per §6"
---

# ADR-B1 — Coconut continuous-thought latent decode channel

Implements item **B1** of [CONTRACT-EXTERNAL-ADOPTION](CONTRACT-EXTERNAL-ADOPTION.md), from [the comparison design](PPT-LAT-COMPARE-EXTERNAL-SYSTEMS-2026-07.md) §4/B1. Source: **Coconut** (Hao et al., arXiv 2412.06769).

## 1. Decision

Add a flag-gated latent "thinking" channel to the served decode path: with `SP_COCONUT=N` (N>0), after the prompt is prefilled and **before** the first answer token is decoded, run **N continuous thoughts** — each thought reads the last position's **post-final-norm hidden state** `h_t` (d_model=3840 f32) and feeds it back as the **next input residual** (advancing the resident KV cache by one position), instead of decoding a token. After N thoughts, resume normal byte-exact token decode for the answer. `SP_COCONUT=0` (default) is a byte-identical no-op.

This is the **sequential** Coconut shape — the thoughts occupy their own span; the answer is decoded cleanly afterward from the advanced KV. It therefore **honors TELE-12** (`a2b4dc7ab58afcfd`: *fused* latent+text = 0.000; sequential decide/think → execute is the win) and ADR-002 (think in latent, execute in clean text).

## 2. Why this is bounded (recon verdict: pure Rust glue)

Both halves already exist and are FFI-wrapped (verified against the engine on the Windows disk):

| Piece | Verb (C) | Rust wrapper | Notes |
|---|---|---|---|
| Read `h_t` (post-output_norm hidden, E=3840 f32) | `gemma4_kv_capture_feat` (`cuda_forward.cu:5321`) | `kv::capture_feat_arm(h, &mut buf)` (`cuda_kvdecode_dispatch.rs:710`) | one-shot arm-then-step; already used by EAGLE/MTP (`eagle_accept.rs`) |
| Feed `h_t` back as next residual + advance KV by 1 | `gemma4_kv_inject_seq(s, embs, n, ph)` (`cuda_forward.cu:5679`) | `kv::inject_frames(h, &frames, n, ph)` (`dispatch.rs:487`) | `embs` = raw `[n][3840]` f32; runs a full forward, mints K/V natively, dpos += n |
| Resume normal token decode | `gemma4_kv_decode_logits` (`cuda_forward.cu:5097`) | `kv::decode_step(h, tok, &mut logits)` (`dispatch.rs:91`) | logits only; sampler argmaxes |
| The loop | — | new Rust logic in `run_kvdecode_chat` (`routes.rs:1239`, decode loop `:3447`) | all three calls already in scope here |

No new CUDA export. d_model E=3840, NL=48; hidden states are f32 end-to-end; the step is deterministic per fixed build/GPU (the EAGLE feature recurrence already depends on this).

## 3. The one modeling decision — capture-vs-inject scale

`capture_feat` yields the **post-output_norm** hidden `RMSNorm(x)·out_norm`; `inject_seq` feeds a vector in as the **layer-0-input residual** (the token path normally injects `embd·√E`, √E≈61.97). These are different points/magnitudes in the network — the same mismatch the KAI-2 codec note flags (`cuda_forward.cu:5650`). Options, in order of ambition:
- **(a) raw** — inject `h_t` verbatim (`SP_KAI2_INJSCALE=1.0`). Under-scaled vs a real residual; the engine test tolerates it (we measure stability, not accuracy).
- **(b) scalar rescale** — `SP_COCONUT_SCALE` (or reuse `SP_KAI2_INJSCALE`) to roughly match residual magnitude (√E is the natural first guess).
- **(c) learned projection** — a small `W: R^3840→R^3840` mapping post-norm hidden → input residual, trained in the curriculum (the Coconut-faithful choice; this is what makes the thoughts *useful*).

**Engine phase** uses (a)/(b) as a knob and reports the **B3 stability profile** (`‖h_t‖` across the N thoughts) at each scale. **Lift phase** trains (c).

## 4. Honest split of the gate (no silent revision)

Coconut's accuracy benefit REQUIRES training at the exploited depth (the paper's curriculum; also 2604.07822/2502.17416). On the frozen 12B, raw thoughts are mechanically valid but semantically ~noise. So the pre-registered G-COCONUT is split:

- **G-COCONUT-ENGINE** (this session, on the perf daemon): (i) **null-floor** — `SP_COCONUT=0` ⇒ `/v1/chat` byte-identical to current (SHA); (ii) **determinism** — the N thought hidden-states are bit-identical run-to-run under fixed clocks; (iii) **stability** — `‖h_t‖` across the thoughts is B3-STABLE (or, if DIVERGENT, that is a recorded finding pointing at the scale/Prelude-Norm fix); (iv) **no-crash / coherence** — the answer after the thought span still decodes without NaN and remains coherent at small N. This proves the mechanism + is the substrate for the lift.
- **G-COCONUT-LIFT** (finetune sprint, likely Colab/RunPod — local 2060 is full with the 12B): `SP_COCONUT=n (n>0)` beats `n=0` by a pre-registered margin on a held-out multi-hop set (GSM8K-style / ProsQA-style / multi-hop-over-memory), after the curriculum finetune of the channel (staged replacement of k text steps with k·c continuous thoughts, masking the latents; train the (c) projection + optionally a LoRA on the first/last block; base 12B frozen + byte-exact).

## 5. Mechanism (engine phase, precise)

In `run_kvdecode_chat`, after prefill of the prompt and immediately before the `'decode` loop (`routes.rs:3447`):

```
let n_thoughts: usize = env "SP_COCONUT" (0 = off);
let inj_scale: f32   = env "SP_COCONUT_SCALE" (default 1.0);
if n_thoughts > 0 {
    // seed: capture the last prompt position's post-final-norm hidden
    let mut h = vec![0f32; E];                 // E = 3840
    kv::capture_feat_arm(handle, &mut h);      // fires on the next step
    // (the prefill's last step already produced dnx; if not separately captured,
    //  do one non-emitting decode_step of the last committed token to arm+read)
    let mut norms = Vec::new();
    for _ in 0..n_thoughts {
        for v in h.iter_mut() { *v *= inj_scale; }
        let mut h_next = vec![0f32; E];
        kv::capture_feat_arm(handle, &mut h_next);       // arm read of the injected position's hidden
        kv::inject_frames(handle, &h, 1, ph_token);      // inject h as 1 new residual position; KV += 1; tap fires
        norms.push(l2(&h_next));
        h = h_next;                                       // continuous thought: next input = this hidden
    }
    // emit the thought-norm trace for the B3 monitor (SP_COCONUT_DUMP)
}
// then the normal 'decode loop runs from the advanced KV position (clean answer decode)
```

Stream output is suppressed for the thought positions (they emit no token). The `ph_token` placeholder is the same one `inject_seq` already uses. Thought-norms are dumped (behind `SP_COCONUT_DUMP`) and fed to `tools/loop_stability.py` (B3).

**Zero-CUDA engine variant (this session).** `inject_frames` advances the KV but does not copy out logits, and reading the last thought's logits to sample the first answer token would need a new `read_logits` D2H export (and an nvcc rebuild of `cuda_forward.cu`). To keep the engine phase to a fast Rust relink, the thoughts are injected as **latent KV context** — the N thought positions are appended to the resident cache, and the normal `'decode` loop resumes and samples the first answer token from its current `logits`; every answer token then attends to the thought positions via the KV. The **faithful** Coconut refinement (sample the first answer token from the *last thought's* logits) needs the `read_logits` export and is folded into the **lift** phase, where the CUDA rebuild is already on the table for the learned projection. The engine gate (null-floor/determinism/stability/coherence) is fully exercised by the zero-CUDA variant.

## 6. Gate harness

- **Null-floor**: 6-turn `/v1/chat` transcript, `SP_COCONUT=0` vs pre-change binary → SHA-identical (reuse the persist-KV parity harness).
- **Determinism**: run `SP_COCONUT=8` twice (locked clocks), assert the dumped 8×3840 thought tensors are bit-identical.
- **Stability**: `python tools/loop_stability.py` over the dumped `‖h_t‖` → STABLE, at `SP_COCONUT_SCALE ∈ {1.0, √E}`. Record ρ̂.
- **Coherence smoke**: `SP_COCONUT ∈ {2,4,8}` on a factual prompt → answer still coherent (no NaN/garbage) — report verbatim.
- **(Lift, deferred)** multi-hop accuracy n>0 vs n=0 after finetune.

## 7. Null-floor & risk

Default `SP_COCONUT=0` → the whole block is skipped → byte-identical. The change is additive Rust in one function; no CUDA, no math-core, no effect on the byte-exact forward when off. Risk is contained: worst case the thoughts are noise (caught as DIVERGENT by B3 or as incoherent by the smoke) — which is a *finding*, not a regression, since it's off by default. Respect: do NOT fuse (thoughts are a pre-answer span; TELE-12); cap N (overthinking, 2604.07822); watch ‖h‖ (Parcae/B3).

## 8. Pre-flight (anti-rebuild)

`capture_feat`/`inject_frames`/`decode_step` all exist and are used by EAGLE/MTP — B1 REUSES them, adds no verb. `okf_mem lookup` inject_seq/capture_feat/eagle confirmed the recurrence primitive is `c68b2f15dc30e641` (gemma4_kv_inject_seq is the generic residual-frame inject). New flags `SP_COCONUT`, `SP_COCONUT_SCALE`, `SP_COCONUT_DUMP` (register in KEYSTONE §7). B3 monitor (`tools/loop_stability.py`) already built.
