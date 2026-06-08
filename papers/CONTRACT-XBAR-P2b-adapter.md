# CONTRACT XBAR-P2b — The span-compression adapter (the scalpel, trained)

**Parent:** CONTRACT-XBAR-P2 (P2.a CLOSED + the 2026-06-09 PLE correction) · RFC-XBAR v1 §5.
**Status:** SPEC (consolidated 2026-06-09, KnackAU + Gemini + Claude). The first *trained* component of the XBAR lane.
**One line:** train a small frozen-LM adapter that maps an n-token span's embeddings to **k < n on-manifold pseudo-tokens** that steer the frozen 12B identically to the full span — learned semantic compression. This is simultaneously the deployable injector (P2's exit) and **Memo's compaction organ** (XBAR-C2's core): P2.b and the curator converge here by design.

---

## 0. What changed in consolidation (vs the first brainstorm draft)

1. **The dataset is NOT `[concept token → its minted entry vector]`** — for a real token that map is the embedding row × √E, an identity we already own. The learnable problem is mapping *non-token* sources onto the manifold. Three sources, one recipe:
   - **(S1) multi-token span → k pseudo-tokens** (THIS contract): self-supervised, unlimited data from any corpus, and exactly the ring-compaction primitive Memo needs.
   - (S2) ring/Spinor episodic state → entry vectors (Memo read-side; after P3).
   - (S3) audio latents → entry vectors (XBAR-M, voxtral source; same recipe).
2. **PLE machinery dropped** for the 12B target (PL=0 — see the P2 contract's formal correction). E-series deployments would re-add a PLE head; out of scope here.
3. **Memory honesty:** freezing the 12B avoids optimizer state for weights, but the backward pass still requires activations through 48 layers (or checkpointing). Cloud-only (RunPod/Colab A100-class; 24 GB bf16 weights + checkpointed activations fit). The 2060 is the *deployment* target, never the training target.
4. **Stall-rate is a first-class metric.** No surviving mechanistic theory for the dragon stall (PLE falsified) → adapter training/selection tracks distinct% on steered continuations, and the trained adapter must not be *worse* than raw entry injection on it.

## 1. Phase 0 — Inversion (existence proof + golden targets + manifold map)

Per-instance soft-prompt optimization on the frozen bf16 12B (cloud): for a sampled span (n=4–8 tokens) inside a context, optimize k free vectors `ê₁..ê_k` (k ∈ {1,2}) at the span's positions to minimize CE/KL against the teacher's continuation (the model's own output given the full span). Two regularization arms, A/B:

- **Arm F (free + soft-min manifold penalty):** `L_man = λ·softmin_topK(‖ê − E_v‖²)` (logsumexp over the K nearest embedding rows — the hard `min` has unstable gradients at Voronoi boundaries; normalize by the embedding-norm distribution).
- **Arm H (convex-hull parameterization):** `ê = Σ_j softmax(s)_j · E_{idx_j}` over the K nearest rows — on-manifold by construction. (The α=0.5 P2.a failure blended two *distant* tokens; local-neighborhood combinations are a different object. Whether the local patch is flat enough is exactly what this arm measures.)

Deliverables: per-span golden `ê*` sets, the achievable-steering ceiling (KL gap vs full span as f(k, n)), and the measured local manifold geometry (how far off-hull do Arm-F optima sit?). **Falsification stated up front:** if inversion cannot find ANY k=2 vector pair matching a 6-token span within tolerance, amortized compression at that ratio is dead and the contract re-scopes to k≈n alignment (S2/S3 only).

## 2. Phase 1 — The adapter (amortize the inversion)

Architecture: small (≤ ~50M params) — span-token embeddings → encoder (few transformer/MLP layers) → k output vectors, parameterized per the winning Phase-0 arm. Trained on (S1) pairs sampled from wikitext + general corpus; loss = teacher-KL on the continuation + the manifold term + a distinct%-degeneration penalty on sampled rollouts.

## 3. Phase 2 — Deployment gate (the part nobody else has)

The adapter's output IS an XBE1 payload — P2.a's `SP_XBAR_EMB` knob is the deployment interface, already built and G0E-proven. Export adapter (tiny, f32), mint payloads host-side, inject on the 2060 against the **B1 quantized artifact**.

| Gate | Criterion |
|---|---|
| **G-P2b-0 (inversion existence)** | Phase 0: ≥⅔ of sampled spans admit a k=2 inversion within the KL tolerance band (band pinned by telemetry on the first 50 spans — telemetry-then-pin) |
| **G-P2b-1 (compression fidelity)** | frozen 12B with `A(span)` at k=2 (n=6): continuation KL/PPL within the pinned band of the full-span teacher, on held-out text |
| **G-P2b-2 (content survival)** | NIAH-style: a fact inside the compressed span remains answerable downstream (the curator's recall currency) |
| **G-P2b-3 (cloud→silicon parity)** | adapter-minted XBE1 payloads on the 2060/B1 artifact reproduce cloud steering (rank telemetry + incorporation), G0E null re-run green — the artifact-quantization gap is measured, not assumed |
| **G-P2b-4 (stall regression)** | distinct% on steered continuations ≥ raw-entry-injection baseline (P2.a receipts); gold-instrument PPL of steered text stays in the healthy band (the P1 G2v2 instrument, re-used) |

## 4. Compute plan & receipts

RunPod/Colab A100-class, bf16 HF checkpoint from the proven bucket (the 4.68-gold weights — the ONLY trusted source, STATE doctrine). All cloud runs export: config echo (banner = printed env/args), dataset manifest hashes, loss curves, golden-pair archives. Receipts land in `_xbar/p2b/` + the contract run-record; ledger row only on G-P2b-1..4 green (the standing rule).

## 5. Convergence note (why this is the home stretch's keystone)

P2.b's adapter is: the deployable injector (XBAR-P exit) · Memo's compaction organ (XBAR-C2: ring consolidation = compress episodic spans to pseudo-token state under the same fidelity gates) · the modality template (XBAR-M swaps the source encoder) · NIGHTSHIFT's worker (consolidation pass = adapter applied offline under promote-on-accept). One trained component, four lanes served. The open Memo-body decision is logged in RFC v1: with the adapter as the organ, Memo v1 may be *adapter + tiny ring-block encoder* rather than the 0.5B M.0 stub.
