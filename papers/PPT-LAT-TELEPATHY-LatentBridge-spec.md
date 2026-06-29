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

> **Receipts-first honesty up front.** Exactly ONE Telepathy path is PROVEN today: the **same-family identity bridge** (the 4-layer EAGLE draft body → the served 12B, via `gemma4_kv_inject` / `gemma4_kv_inject_tokens`, demonstrated in RP-1's strawberry trace). Every **cross-model / cross-family** claim in this document is **SPEC / PROPOSED** and carries no number until its gate is green. Do not cite the cross-model adapters as working.

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
| **linear** | same `d_model`, related family; an orthogonal/affine map suffices | one calibration pass | SPEC |
| **learned** | different `d_model` / different family (e.g. gemma4-e2b ↔ qwen25-coder); needs a trained map | trained adapter (small MLP), calibrated on paired latents | SPEC |

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
| `G-TELEPATHY-ROUNDTRIP` | source concept transferred+injected is recoverable at `dst` ≥ threshold | (per-adapter) | identity: PROVEN (RP-1 strawberry); cross-model: PENDING |
| `G-TELEPATHY-REJECT` | foreign/out-of-domain src latent is rejected, not injected | (per-adapter; reject-hinge) | PENDING |
| `G-ADAPTER-CONFORM` | a new adapter ships all five §3.1 deliverables + green gates | `python tools/okf_validate.py <adapter-bundle>` + the three gates | PENDING |

**Proven today:** identity bridge, same-family, default-off parity + RP-1 round-trip. **Everything else: PENDING.**

---

## 8. Status & roadmap

- **Now (PROVEN):** same-family identity bridge (draft → 12B), `gemma4_kv_inject*`, RP-1/TH-1.
- **Next (SPEC → first cross-model gate):** a **learned adapter** for a real cross-family pair that is already transcoded and present — `gemma4-e2b` ↔ `qwen25-coder-0.5b-memory` — calibrated on paired latents, gated on PARITY + ROUNDTRIP + REJECT. This is the first falsifiable cross-model Telepathy claim.
- **Then:** register the adapter via `G-ADAPTER-CONFORM`; wire the LatentBridge object into `eagle_accept.rs` behind `SP_TELEPATHY` (default-off); sew references into RFC-001, the KEYSTONE map, the roadmap, and the public README.

## 9. Open questions

- What fidelity threshold makes `G-TELEPATHY-ROUNDTRIP` meaningful per task (recall vs reasoning vs tool-result)?
- Is the cross-family map linear-sufficient on RMSNorm-space, or does it need a learned MLP? (measure, don't assume.)
- Does the reject gate need a learned domain classifier or does a cosine/Hamming floor suffice?
- License-token distribution + attestation root-of-trust: where does the signing key live (it is a secret → creds file, paths-not-values)?
