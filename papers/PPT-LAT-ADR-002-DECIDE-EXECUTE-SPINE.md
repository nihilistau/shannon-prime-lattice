---
type: design
title: "ADR-002 — The Decide→Execute Spine: the 3-tier Latent/Symbolic architecture (what lives where)"
description: "The governing architecture for the whole Shannon-Prime serving stack, derived from the 2026-06/07 evidence: DECIDE in latent (cheap heads + selectors), EXECUTE in clean symbol/text (text-in-context, delegate, tool, KV replay), NEVER fuse latent content into generation — and deciders must not execute. Maps every component (Latent Interceptor heads, Telepathy, memory/recall, EAGLE/MTP, judge, L5 selector, SSE) to Tier-1 Decider / Tier-2 Executor / Tier-3 Substrate, with a Rust typestate boundary (LatentDecision) that makes fusion structurally impossible. Supersedes the framing of ADR-LATENT-NATIVE-UNIFICATION; keeps the byte-exact O_K substrate; explicitly REJECTS the poison-pill from the swarm draft."
tags: [design, adr, architecture, decide-execute, latent-interceptor, telepathy, memory, recall, judge, eagle, mtp, sse, typestate, substrate]
timestamp: 2026-07-01T00:00:00Z
resource: shannon-prime-lattice/papers/PPT-LAT-ADR-002-DECIDE-EXECUTE-SPINE.md
sp_status: DESIGN
sp_gate: "grounded in shipped receipts: G-L5-RECALL-LIVE (86.89%), G-L5-JUDGE-PASSBLOCK, TELE-12/13, G-BYTEEXACT-FORWARD-12B"
sp_commit: "engine f7548b2 (delivery fix) + d9099cd (SP_RECALL_L5) + 5d336c7 (SP_B3_JUDGE_L5)"
sp_repro: "n/a (architecture). Component receipts cited inline."
---

# ADR-002 — The Decide→Execute Spine

## 1. Context — one pattern explained the whole session

Every win converged on a single shape; every failure violated it:

> **DECIDE in latent (cheap, fast, fail-first-then-work). EXECUTE in clean symbol/text. Never fuse latent *content* into generation. And a decider must not execute.**

Evidence (all this repo's receipts):
- **TELE-12/13**: fused latent+text transmit = 0.000; sequential decide→execute = the win → cemented as the native primitive.
- **Faithfulness recall**: latent *selects* (L5-cosine query-key), text-in-context *delivers* → **86.89% live** (G-L5-RECALL-LIVE). The latent-KV-replay *content* injection (W_c α-sweep) had no operating point.
- **Pass→block reject**: L5 shortlists (decide) + judge picks/NULLs (decide) → foreign spurious-delivery 90%→17% (G-L5-JUDGE-PASSBLOCK). When the *judge itself tried to deliver* ("recite natively") it produced `<image|>` garbage; and even after the garbage was fixed, **the judge-block delivery lost context-authority** (picked the right fact but the model answered parametric) — a fine-grain proof that **a decider that also executes loses authority.**
- **Interceptor heads** (action/tool/route/memory): tiny latent *deciders*, symbolic *execution*; near-miss-hardened, false-fire 0.000.
- **Byte-exact forward**: the exact-integer container underneath all of it.

This ADR makes that pattern the governing architecture.

## 2. The Law (and its corollary)

- **L1 — Decide/Execute separation.** Latent computes DECISIONS (route, select, gate, reject, draft). Clean symbol/text computes CONTENT (deliver, answer, call, replay). 
- **L2 — Never fuse.** Do not inject latent *content* into the generation stream (KV-content-inject, tag-conditioned "recite", cross-model latent fusion). Latent content does not survive generation — it collapses (echo-hijack) or degenerates (garbage/parametric-washout).
- **L3 — Deciders don't execute (corollary, proven 2026-07-01).** A component that makes a decision must hand a *discrete intent* to a separate executor; if the decider also runs the delivery, it drags its own cache/prompt state in and the execution loses authority. (The judge-delivers experiment: right pick, wrong answer.)

## 3. The three tiers — what lives where

### Tier 1 — DECIDERS (latent, cheap, on `capture_feat` / global-K/Q)
| component | decision | status |
|---|---|---|
| **L5-cosine recall selector** | WHICH memory (query-key cosine, global layer 5) | **GREEN-LIVE 86.89%** (G-L5-RECALL-LIVE) |
| **Judge (SP_B3_JUDGE + SP_B3_JUDGE_L5)** | does the candidate answer? PICK / **[NULL]** (the reject) | validated (85.7% recall@1; reject G-L5-JUDGE-PASSBLOCK) |
| **Interceptor heads** (action / tool / memory) | WHAT to do (near-miss-hardened) | proven, false-fire 0.000 |
| **Route head** | LOCAL vs TELEPATHY delegate | proven (TELE-7) |
| **EAGLE / MTP draft** | next-K token proposals (then verified) | wired; scale corpus pending (#40) |
Deciders take an **immutable** view of the neural state and return a discrete intent. They never mutate the KV cache or emit tokens.

### Tier 2 — EXECUTORS (clean, symbolic)
| component | executes | status |
|---|---|---|
| **Text-in-context delivery** (SP_RECALL_L5 format) | deliver a recalled fact (system faithfulness prompt + "Context (authoritative): …") | **the authoritative delivery** — 86.89%; also the fix for the judge (f7548b2) |
| **Telepathy delegate** | clean text → Qwen, stream back | GREEN-LIVE (TELE-CHAT) |
| **Tool / MCP / E2B** | run the action | THL closed loop |
| **KV replay / inject_tokens** | restore an episode's cache | wired |
| **SSE stream** | deliver to the user (delegate markers, injected context) | the OUTPUT seam (see §5) |
Executors take a `LatentDecision` and mutate the generation stream. They never inspect a tensor.

### Tier 3 — SUBSTRATE (exact-integer O_K, isolated)
Byte-exact forward + dual-prime CRT-NTT (auditability / cross-machine determinism), C2 / Ring-3 VSA (content addressing), MEM-OKF (the content-addressed store), the M.4 receipt ledger + canonical Garner order (the honest audit/provenance layer). The **Friedman sieve / KSTE / kste_md** live here as dedup/eviction primitives — **parked** (magnitude-shape, off the recall path). 
**Tier 3 is exact-arithmetic + auditability ONLY. The "poison-pill / commercial-hostile payload" from the swarm draft is REJECTED (banked honest-negative: home-rolled weak crypto, does not poison training, liability inverts). It is NOT part of the substrate. Provenance = Ed25519 signatures + closed membership (SP-SWARM), not sabotage.**

## 4. The boundary contract (make fusion structurally impossible)

The only value that crosses Tier-1 → Tier-2 is a discrete intent — no tensors, no logits:

```rust
/// The sole boundary between the latent manifold (Tier 1) and the symbolic
/// engine (Tier 2). Tensors go IN to a decider; a discrete intent comes OUT.
pub enum LatentDecision {
    Pass,                                   // continue normal autoregressive generation
    RecallFact  { episode_id: u32 },        // L5 select + judge PICK -> Tier-2 delivers the TEXT
    RouteToModel{ target: ModelId },        // Telepathy route head
    CallTool    { tool: ToolId, args_id: u32 },
    Reject      { reason: RejectReason },    // judge [NULL] -> suppress spurious recall
}

pub trait Tier1Decider {   // immutable view; cannot mutate cache or emit tokens
    fn evaluate(&self, latent: &LatentView) -> LatentDecision;
}
pub trait Tier2Executor {  // takes intent; cannot inspect a tensor
    fn execute(&self, d: LatentDecision, stream: &mut GenerationStream);
}
```

This is the refactor target (heads are currently wired ad-hoc inside `routes.rs`). Encoding it in the type system is what prevents a future change from re-fusing them — the compiler forbids a decider from touching the stream and an executor from touching a tensor. (Adapted from the Gemini draft; the poison-pill Tier-3 framing is dropped.)

## 5. The dispatch loop (the SSE inject pathway)

The served `/v1/chat` loop becomes the spine made literal — and the SSE stream is where Tier-2 executions splice into the user's output:

```
forward → capture L5/feat → Tier-1 deciders → LatentDecision
  Pass         → normal generation
  RecallFact   → Tier-2 text-in-context delivery (authoritative) → SSE
  RouteToModel → Tier-2 delegate (clean text → Qwen)             → SSE (⟦delegate⟧ marker)
  Reject       → suppress recall, normal generation              → SSE
```

## 6. The unified recall/reject path (derived from §2-L3)

Correct wiring, replacing "judge delivers":
1. **L5 selects** the top-1 memory (86.89% correct).
2. **Judge vetoes** that top-1: does it answer? PASS or **[NULL]** (reject foreign). Judge is a pure gate — it does not deliver.
3. **L5-direct executor delivers** the chosen fact via the authoritative text-in-context path.

This preserves the 86.89% recall (L5-direct owns delivery) AND adds the reject (judge NULL), without the authority loss seen when the judge delivered. `SP_B3_JUDGE_L5` already does step 1+2's selection; the remaining build is the **reorder** so the judge is a veto *before* L5-direct commits, not a separate delivering branch.

## 7. Status reconciliation (proven / promoted / parked)

- **CHANGED**: recall/reject is now **L5-select → judge-veto → L5-deliver**. Supersedes W_c-pure-KV-replay and raw-global-Q approaches (W_c demoted to a fallback pre-filter). L5 is the graduated recall selector (updates ADR-LATENT-NATIVE-UNIFICATION).
- **UNCHANGED / compose**: Telepathy, Interceptor heads, EAGLE/MTP, byte-exact substrate, C2/Ring-3/MEM-OKF.
- **PARKED (no change)**: Friedman sieve / KSTE / kste_md (dedup primitives; kste_md is input-gated, directional-blind — see its receipts). CRT multi-device (resolved-negative). Poison-pill / field-crypto (rejected).

## 8. Consequences — the next builds (in order)
1. **Unified path reorder** (§6): judge as veto before L5-direct delivery; gate para-obey (~86%) + foreign-reject in ONE served path; default-off → promote to default-on when green.
2. **Refactor to the typestate boundary** (§4): extract the ad-hoc `routes.rs` decider/executor branches into `Tier1Decider`/`Tier2Executor` + `LatentDecision`. This is the "clean/hardened" the operator asked for — one seam, compiler-enforced.
3. **Cleanup/harden**: consolidate the ~dozen `_*` gate harnesses into one recall/reject runner; prune the dead naive-binary-judge; every flag default-off with a byte-exact null floor; re-run G-CLEAN-BUILD + G-OKF-CONFORM; refresh STATE/KEYSTONE.
4. **Scale-confirm** the recall+reject numbers beyond n=61/12.
5. Standing: special-token ban in the sampler (belt-and-suspenders vs any future degeneration).
