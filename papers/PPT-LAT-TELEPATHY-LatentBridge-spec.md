---
type: design
title: "Telepathy — the LatentBridge framework for tokenizer-free latent→latent transfer between models"
description: "Canonical spec for Telepathy: a named API/framework that moves information between two models on the latent manifold (no detokenize→retokenize round-trip), via a registry of pluggable adapters. PROVEN today only for the same-family draft→12B case; everything cross-model is SPEC. Separately licensed (proprietary) component layered on the MIT substrate."
tags: [design, telepathy, latent-bridge, latent-interceptor, adapters, ip]
timestamp: 2026-06-30T00:00:00Z
resource: shannon-prime-lattice/papers/PPT-LAT-TELEPATHY-LatentBridge-spec.md
sp_status: DRAFT
sp_gate: G-TELEPATHY-PARITY (off=null floor) | G-TELEPATHY-ROUNDTRIP | G-TELEPATHY-REJECT | G-ADAPTER-CONFORM
sp_commit: TBD
sp_repro: "see §7 Gates — each gate names its reproducing command; same-family identity path proven via RP-1 (gemma4_kv_inject, strawberry demo)"
---

# Telepathy — the LatentBridge framework

**Status:** DRAFT for review/iteration. **Author:** Claude (SP hat), 2026-06-30, synthesizing operator intent + the empirical record (Latent Interceptor RP-1/TH-1, the served gemma4-12b-b1). **Disposition:** a constitution + adapter contract skeleton, not a decree. Nothing here is frozen until it is itself frozen.

> **Receipts-first honesty up front.** PROVEN today: (1) the **same-family identity bridge** (EAGLE draft body → served 12B, `gemma4_kv_inject*`, RP-1 strawberry trace); (2) **TELE-1** — the cross-FAMILY affine adapter (gemma-3n-E2B ↔ qwen2.5-coder-0.5b) at the representation level (retrieval@1 1.000, round-trip 0.891, reject AUC 0.999); (3) **TELE-2** — the injected mapped latent causally **steers** Qwen (dLL_self +0.414, steer-accuracy 1.000 vs matched control). **Honest scope:** TELE-2 is *activation steering* — the matching latent measurably raises the matching text's likelihood and beats a control, with fluency preserved; it does NOT *force verbatim* output (a single mean-pooled vector can't, and we don't claim it). The license/attestation fail-closed mechanisms (§6) are SPEC. Don't overclaim beyond these gated numbers.

---

## 1. What Telepathy is (and is not)

**Telepathy** is the named capability of transferring information from one model's latent space into another model's latent space **without going through text** — no detokenize on the source, no retokenize on the destination. The unit of transfer is a latent vector (or a small set of them), not a token string.

The carrier object is a **`LatentBridge`**: a typed, licensed channel `src → adapter → dst` plus the injection transport that lands the adapted latent into `dst`'s residual/KV state.

**Telepathy IS:**
- a transport for decisions/memory/tool-results that already live on the manifold (the Latent Interceptor's heads produce latents; Telepathy moves them);
- a registry of **adapters**, each mapping one source latent geometry to one destination latent geometry, with a conformance contract and gates;
- the proven same-family fast path (identity adapter) generalized into a pluggable framework.

**Telepathy is NOT:**
- a compression codec (that is the 63-byte Spinor / KV-cache codec — separate);
- the memory address (that is the C2 256-bit signature — separate);
- a claim that arbitrary models share a latent space. They do not. Cross-family transfer **requires a learned adapter** and is unproven until gated.

---

## 2. The `LatentBridge` object / API

```
LatentBridge {
  src:      ModelRef      # source model + tap point (which layer / which stream)
  dst:      ModelRef      # destination model + inject point
  adapter:  AdapterRef    # the registered map src-geometry -> dst-geometry (see §3)
  dim_in:   u32           # source latent width  (e.g. draft HID = 1024)
  dim_out:  u32           # destination inject width (e.g. 12B d_model)
  scale:    f32           # injection gain (dx <- scale * dinj); default 1.0
  basis:    BasisRef      # frozen basis/normalization the adapter assumes (id, RMSNorm-space, ...)
  flags:    BridgeFlags   # see below
  license:  LicenseToken  # REQUIRED; bridge refuses to build without a valid token (§6)
}

BridgeFlags = {
  DEFAULT_OFF       # bit0: when unset, transfer() is a null op -> byte-exact destination (parity floor)
  REQUIRE_ATTEST    # bit1: validate cryptographic build/runtime attestation before any transfer
  REJECT_FOREIGN    # bit2: run the reject gate; drop transfers whose src signature is out-of-domain
  ONE_SHOT          # bit3: single residual injection vs persistent KV write
}
```

API surface (all fallible; all no-op to a byte-exact destination when `DEFAULT_OFF` and the license/attestation check fails-closed):

- `LatentBridge::build(src, dst, adapter, license) -> Result<Bridge>` — validates dims, basis compatibility, license/attestation; **fails closed** (returns an inert bridge) on any violation.
- `bridge.transfer(latent_in[dim_in]) -> Result<latent_out[dim_out]>` — applies the adapter.
- `bridge.inject(latent_out[dim_out])` — the transport (§4): `gemma4_kv_inject` (one residual) or `gemma4_kv_inject_tokens` (into the KV ring).
- `bridge.validate() -> GateReport` — runs the conformance gates (§7) and returns the receipts.

**Default-off / null-floor law (inherited from the engine):** a bridge with `DEFAULT_OFF` set and no valid license/attestation MUST leave the destination byte-identical to no-bridge. This is the parity floor (`G-TELEPATHY-PARITY`) and is the safe default.

---

## 3. Adapter taxonomy + the registration contract

An **adapter** is the only model-pair-specific piece. Three tiers:

| tier | when | cost | status |
|---|---|---|---|
| **identity** | `src` and `dst` are the same model or same family/tokenizer/`d_model` (e.g. EAGLE draft → its 12B target) | free (no learning) | **PROVEN** (RP-1) |
| **linear** | affine map (z-scored ridge), works **even across different `d_model` / family** via a rectangular map | one calibration pass | **PROVEN** (TELE-1: gemma-3n-E2B 2048-d ↔ qwen2.5-coder-0.5b 896-d — retrieval@1 1.000, round-trip cos 0.891, reject AUC 0.999) |
| **learned** | shallow MLP, only if linear underfits the gates | trained adapter, calibrated on paired latents | SPEC — **not needed for gemma↔qwen** (linear cleared all gates) |

### 3.1 Adapter registration contract (`G-ADAPTER-CONFORM`)

To add a new adapter to the registry, a contributor MUST provide, as a single SP-OKF bundle:

1. **Identity** — `name`, `src` ModelRef, `dst` ModelRef, `dim_in`, `dim_out`, `basis` it assumes.
2. **The map** — the transfer function (weights + a pure `transfer()` impl) OR a declaration of `identity`.
3. **Calibration provenance** — what paired-latent data trained/derived it, how many pairs, the held-out split (receipts-first; no number without its command).
4. **Gate receipts** — green logs for:
   - `G-TELEPATHY-PARITY` — with the bridge off, `dst` is byte-identical to no-bridge (the null floor).
   - `G-TELEPATHY-ROUNDTRIP` — a known source concept, transferred and injected, is recoverable at `dst` above a stated fidelity threshold (and the threshold is stated, not implied).
   - `G-TELEPATHY-REJECT` — a foreign / out-of-domain source latent is **rejected** (does not silently inject garbage); reuse the Latent-Interceptor reject-hinge discipline.
5. **License compatibility** — declaration that the adapter ships under (or compatibly with) the Telepathy license (§6), and that it contains no host-external effects (§6 boundary).

An adapter that does not carry all five is **not registered** and `build()` refuses it. No silent gate revision — a failing gate is surfaced, not relaxed.

---

## 4. Transport (the injection mechanism)

Telepathy reuses the engine's existing, proven injection verbs — it does **not** invent a new transport:

- **`gemma4_kv_inject(s, emb[E])`** — one residual injection (`dx ← scale·dinj`). Used for `ONE_SHOT`.
- **`gemma4_kv_inject_tokens(s, toks, n)`** — writes token-embeddings into the KV ring with no prompt re-feed. Used for persistent landing (this is the RP-1 return path).

The read/tap side on `src` is the Latent Interceptor's draft-body latent (`gemma4_draft_body` → 1024-d) or any declared tap point. The same-family identity bridge is exactly `src.latent → (identity) → dst.inject` and is the proven path.

---

## 5. Relationship to the Latent Interceptor

Telepathy is the **transport layer** under the Latent Interceptor's heads. The heads (action / memory / tool — now hardened, false-fire 0.000) decide *what* to move; Telepathy moves it:
- tool-result latent → `LatentBridge(tool_sandbox → 12B)` → inject (RP-1/TH-1 today is the same-process identity case);
- memory recall latent → inject into the resident cache;
- (future) a *different* model's reasoning latent → adapter → the 12B.

The safety property is inherited: a bridge only fires when a hardened head selects it, and the bridge itself fails closed.

---

## 6. IP & licensing (baked in from day one)

The Shannon-Prime **substrate** repos are MIT (RFC-001). Telepathy is therefore specified as a **separately-licensed, proprietary component layered on top of the MIT core** — the base stays open; the LatentBridge framework and its cross-model adapters are licensed restrictively. This is standard dual-component licensing and needs no relicensing of the substrate.

**Protection model (legitimate, fail-closed — the "bricks itself" design):**
- **Restrictive license** — proprietary / non-commercial-by-default; commercial use only under explicit grant. Copyright held under a chosen (pseudonymous) name; pseudonymous authorship is fine.
- **License-key gating** — `build()` requires a valid `LicenseToken`; **without it the bridge is inert** (returns a null-floor bridge that performs no transfer). This is ordinary commercial licensing (cf. FlexLM, dongles, trial gating).
- **Cryptographic attestation** — `REQUIRE_ATTEST` validates a signed build/runtime attestation before any transfer; tampered or unauthorized builds **refuse to run**.
- **Tamper-evidence + watermarking / canary tokens** — adapters carry detectable provenance markers so unauthorized copies are identifiable; tampering is detectable and trips fail-closed.

**The boundary (non-negotiable, written into the spec so adapters stay on the right side):**
> Telepathy's protection mechanisms may only **disable the bridge's own operation** (refuse to build, refuse to transfer, run inert). They may **never** reach outside the bridge to damage, delete, exfiltrate, or attack the host's other data or systems. Fail-closed self-disabling is legitimate IP enforcement; anything host-external is malware and is out of scope (and would expose the author to computer-misuse/CFAA liability rather than protect them).

This achieves the objective — unauthorized commercial deployment is **commercially unviable** because the software simply won't run — without crossing into destructive territory. Effective, and safe for the author.

---

## 7. Gates

| gate | asserts | repro | status |
|---|---|---|---|
| `G-TELEPATHY-PARITY` | bridge off / no license ⇒ `dst` byte-identical to no-bridge | (per-bridge harness; null-floor diff) | identity path: inherited from RP-1 default-off |
| `G-TELEPATHY-ROUNDTRIP` | source concept transferred+injected is recoverable at `dst` ≥ threshold | `fit_adapter.py` (cos / retrieval@k) | identity: PROVEN (RP-1); **gemma↔qwen: GREEN** (round-trip 0.891, retrieval@1 1.000, chance 0.016) |
| `G-TELEPATHY-REJECT` | foreign/out-of-domain src latent is rejected, not injected | `fit_adapter.py` (nn-dist AUC) | **gemma↔qwen: GREEN** (AUC 0.999, in-domain 0.325 vs foreign 0.648) |
| `G-TELEPATHY-GEN-TRIGGER` | the *injected* mapped latent causally steers `dst`'s output (raises matching-text LL; beats a matched control) | `telepathy_steer.py` (ΔLL + steer-accuracy) | **gemma→qwen: GREEN** (L=20 α=0.25: dLL_self +0.414, dLL_cross −0.496, steer-acc 1.000) |
| `G-TELEPATHY-READABLE-PREFIX` | a multi-vector prefix in `dst`-embedding space is read **positionally** (order matters beyond aggregate mass) | `telepathy_prefix.py` (permutation gap) | **gemma→qwen: GREEN** (ORDER_gain corr−shuf = +1.45 nats, corr>shuf 100%; aggregate-mass gain −0.39 ⇒ no uniform-bias artifact; rev≈shuf) |
| `G-TELEPATHY-WIRE` | the LatentBridge is cemented in the daemon: adapter-load + in-engine transfer == Python + fail-closed license + routing primitive; `SP_TELEPATHY` default-off null floor | `sp-daemon SP_TELEPATHY=1` (`telepathy.rs`) | **GREEN** (in-engine transfer vs Python max\|Δ\|=6.7e-6 relL2=3.3e-7; license unset⇒inert; route→Local) |
| `G-ROUTE-WIRE` | the routing primitive is governed by a **near-miss-hardened Route head** (LOCAL vs TELEPATHY); in-engine decision == Python | `sp-daemon SP_TELEPATHY=1 + SP_ROUTE_HEAD` | **GREEN** (Route head isolated-OOD 1.000, false-fire 0.000; in-engine `decide_route` matches Python on both fixture classes; headless ⇒ Local null floor) |
| `G-TELEPATHY-TWOSTAGE` | the **two-stage primitive** is cemented: `decide_route`(latent) → `delegate_execute`(CLEAN TEXT); the never-fuse contract is enforced; null floor on LOCAL | `sp-daemon SP_TELEPATHY=1` (`telepathy.rs`) | **GREEN** (route→Telepathy → delegate_execute invoked w/ clean-text task; native L1 coder-exec wired in TELE-14) |
| `G-TELEPATHY-NATIVE` | **standalone SOVEREIGN native delegate (Path A, no Python):** the coder runs fully in-engine — load qwen2.5-coder in its own L1 session → encode clean-text task → `prefill_chunk`→`decode_step` argmax loop → detok | `sp-daemon SP_TELEPATHY_NATIVE=1` (`eagle_accept::run_telepathy_native`, engine `2f57520`) | **GREEN** (coherent in-engine python answer, 24 toks ~0.8 tok/s CPU; HF parity inherited from top-1-lossless transcode gate). **Notes:** CUDA `qwen3_decode_cuda`/`qwen3_forward_cuda` are `SP_ARCH_QWEN3`-only (reject the QWEN25 coder); `qwen3_generate_kv` on the wire_cuda session segfaults; CPU L1 = zero `g_w`/CUDA contention ⇒ also the clean **co-residency** route (Path B without the risky `g_w` refactor). |
| `G-ADAPTER-CONFORM` | a new adapter ships all five §3.1 deliverables + green gates | `python tools/okf_validate.py <adapter-bundle>` + the gates | gemma↔qwen adapter meets representation + generation-trigger + readable-prefix gates |

**The decisive boundary (TELE-11/11b/12) — what the bridge is FOR:**
- **Gist/intent/routing channel — PROVEN.** Domain, structure, format, on-task steering, faithful reconstruction all transmit strongly (TELE-1..10b).
- **NOT a precise-symbolic channel.** Exact operands don't survive: latent-only answering on arithmetic is near-chance, and the *same* Qwen does 0.806 from text — so the loss is the channel's symbolic precision, not the delegate (the delegate is capable).
- **Fusing latent+text FAILS (TELE-12):** a fused [latent-prefix + text-operands] prompt = 0.000 vs 0.348 for text-operands alone — the soft prefix corrupts downstream text. ⇒ **architecture is strictly two-stage: decide via latent, execute via clean text. Never fuse.** This is exactly the existing Latent-Interceptor design (heads decide on latent; harness executes via text/tools).
- **Native cross-family execution needs NO `inputs_embeds` entry** (fusing is dead): run the qwen coder **token-in** (`qwen3_generate_kv`, exists) on the clean-text task, loaded via L1 (MeMo two-model pattern, avoids the `g_w` global). The L1 coder-load is the one remaining wiring; `delegate_execute` is the cemented seam.

**Proven today:** (1) identity bridge, same-family, default-off parity + RP-1 round-trip; (2) **TELE-1 — the first cross-FAMILY adapter (gemma-3n-E2B ↔ qwen2.5-coder-0.5b), a ridge affine map: round-trip cos 0.891, retrieval@1 = 1.000 (chance 0.016), foreign-reject AUC 0.999, at the representation level (mean-pooled sentence latents).** (3) **TELE-2 generation-trigger** — the injected mapped latent causally steers Qwen (steer-acc 1.000 vs control); (4) **TELE-4 multi-vector mapping** via char-span alignment (per-token `W_tok`: within-sentence retrieval@1 0.967); (5) **TELE-5 readable-prefix** — a multi-vector prefix in Qwen's embedding space is read **positionally** (ORDER_gain +1.45 nats corr−shuf, 100% win-rate; aggregate-mass control −0.39 ⇒ not a uniform-bias artifact). **PENDING:** wiring the bridge into the engine (`SP_TELEPATHY` default-off) + reverse direction + the license/attestation enforcement (SPEC). Tools: `tools/telepathy/{gen_pairs,extract_latents,fit_adapter,telepathy_steer,telepathy_multivec,telepathy_prefix}.py`; adapters `telepathy_adapter_g2q.npz` (pooled), `telepathy_adapter_g2q_tok.npz` (per-token).

---

## 8. Status & roadmap

- **Now (PROVEN):** (1) same-family identity bridge (draft → 12B), `gemma4_kv_inject*`, RP-1/TH-1; (2) **TELE-1 cross-FAMILY affine adapter gemma-3n-E2B ↔ qwen2.5-coder-0.5b** — representation alignment GREEN (round-trip 0.891, retrieval@1 1.000, reject AUC 0.999); ridge affine sufficed across `d_model` 2048→896, no MLP; (3) **TELE-2 generation-trigger GREEN** — the *injected* mapped latent causally steers Qwen (dLL_self +0.414, steer-accuracy 1.000 vs matched control), fluency preserved. **The clean injection seam = the late residual (layers ~16–22, near where the aligned final-hidden vector lives) at gentle scale α≈0.1–0.5; early layers or large α disrupt.** (4) **TELE-4 multi-vector mapping** — per-token (not pooled) transfer via **character-span token alignment** (the two tokenizers split differently, so align by char offsets, not index). A refit per-token `W_tok` reaches cos 0.936 and **within-sentence retrieval@1 0.967** (vs the pooled-W applied per-token: 0.796 / 0.799) — i.e. the channel carries real per-position bandwidth, not just a global nudge. The pooled-fit W *partially* holds per-token (cos 0.796, does not collapse) but must be refit for high-fidelity multi-vector. Adapter: `telepathy_adapter_g2q_tok.npz`.
- (5) **TELE-5 readable-prefix GREEN** — the mapped per-token sequence injected as a soft prefix in Qwen's **embedding space** is read **positionally**: permutation gate ORDER_gain (corr−shuf) = **+1.45 nats**, corr>shuf on **100%** of held-out texts, while the aggregate-mass control gives **−0.39** (so it is NOT a uniform bias from the vectors' mass; reversed ≈ shuffled). The bridge carries true *ordered* bandwidth, not just a nudge. Adapter `telepathy_adapter_g2q_tok.npz` → Qwen-embedding via `telepathy_prefix.py`.
- (6) **TELE-6 engine wiring GREEN** — the **LatentBridge is cemented in the daemon** (`tools/sp_daemon/src/telepathy.rs`, `mod telepathy`, `SP_TELEPATHY` default-off): the bridge object + adapter-load + pure-Rust affine transfer + the **routing primitive** (`RouteDecision{Local, Telepathy(id)}`, default `Local` = null floor) + the **fail-closed license** gate. Gate `G-TELEPATHY-WIRE` GREEN: in-engine transfer == Python adapter (max\|Δ\|=6.7e-6, relL2=3.3e-7), license unset⇒inert, route→Local. The same-family inject is RP-1 (live); the cross-family destination forward stays PENDING. Build: Rust daemon only (no CUDA recompile).
- **Routing (decided + DONE):** Telepathy gets its **own primitive**, NOT an overload of the Tool/Action heads (those decide local effects; transport is orthogonal and must carry *which bridge*). **TELE-7: the Route head is trained + hardened** (LOCAL vs TELEPATHY; anti-laziness = local-doable code + tool tasks + model-mentions all labelled LOCAL; isolated-OOD **1.000, false-fire 0.000**) and now **GOVERNS `decide_route` in-engine** (`G-ROUTE-WIRE` GREEN — in-engine route == Python; headless ⇒ Local null floor). The decision suite (Tool / Action / Memory / Route) is complete and uniformly non-hallucinating.
- (7) **TELE-8 SCOPED** — the **cross-family destination FORWARD** (the one true-live gap) is scoped in [PPT-LAT-TELEPATHY-Qwen-forward-SCOPE.md](PPT-LAT-TELEPATHY-Qwen-forward-SCOPE.md). Key finding: **Qwen2 is architecturally simpler than Gemma-3** (uniform attention, standard RMSNorm, 2 norms, SiLU, no QK-norm/soft-cap/embed-scale) and adds only **QKV bias** — so the integration is mostly subtraction. Decision: **do NOT fold Qwen into the Gemma kernels** (regression risk); a separate path. Tiering: **v1 sidecar** (HF Qwen, the proven TELE-5 embedding-prefix path, zero engine risk) → **v2 native fp16** → **v3 exact** (optional).
- **Next (build) — CORRECTED:** the cross-family forward is **NOT a new build** — the engine already has `qwen3_forward_cuda` + `qwen3_generate_kv` + the `gemma4_kv_inject_seq` embedding-inject, and `qwen25-coder-0.5b` is transcoded + run in MeMo (operator tip). So **v1 = NATIVE in-engine transmit** (load qwen sp-model → `LatentBridge` map via `W_emb` → `gemma4_kv_inject_seq` → `qwen3_generate_kv` → stream); pure glue over proven primitives. The HF sidecar (`telepathy_sidecar.py`) is demoted to a parity oracle. Then: harden REJECT (in-domain-but-wrong negatives); reverse (qwen→gemma); realize license/attestation (SPEC).

## 9. Open questions

- What fidelity threshold makes `G-TELEPATHY-ROUNDTRIP` meaningful per task (recall vs reasoning vs tool-result)?
- ~~Is the cross-family map linear-sufficient, or does it need a learned MLP?~~ **RESOLVED (TELE-1): a z-scored ridge affine map is sufficient for gemma-3n↔qwen2.5 at the representation level (retrieval@1 1.000) — no MLP needed.** (Open: whether the generation-trigger claim needs nonlinearity.)
- Does the reject gate need a learned domain classifier or does a cosine/Hamming floor suffice?
- License-token distribution + attestation root-of-trust: where does the signing key live (it is a secret → creds file, paths-not-values)?
