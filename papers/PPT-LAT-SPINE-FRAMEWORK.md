---
type: design
title: "The Decide→Execute Spine — the unified latent-decision framework (ADR-002 §4/§8.2 realized)"
description: "The framework that turns the accumulated recall/route/judge/decline/inject workarounds into ONE compiler-enforced seam: an immutable LatentView, a priority-folded chain of Deciders (each a latent head or symbolic gate), a discrete LatentDecision, and one Executor. Realizes the ADR-002 boundary contract in the Rust type system so latent-content fusion is structurally impossible. Live in tools/sp_daemon/src/spine.rs; gated GREEN (G-SPINE-ONECONFIG: P 54/61, byte-for-byte identical to the inline baseline)."
tags: [design, spine, adr-002, latent-heads, decide-execute, framework, telepathy, recall]
timestamp: 2026-07-03T00:00:00Z
resource: shannon-prime-lattice/papers/PPT-LAT-SPINE-FRAMEWORK.md
sp_status: GREEN-LIVE
sp_gate: "G-SPINE-ONECONFIG (engine 579552d): SP_SPINE=1 reproduces P 54/61 · S 3/3 · F 2/2 · C · Q 2/2 · X = identical to inline"
sp_commit: "engine 579552d (spine.rs + routes.rs wiring)"
sp_repro: "_spine_launch.bat (run_console_faithful + SP_SPINE=1) -> python _faithful_corpus/oneconfig_run.py -> VERDICT GREEN"
---

# The Decide→Execute Spine

## 1. What this replaces (and why it was ugly)

Over the project's life, every latent decision — route to another model, recall a fact,
veto a spurious recall, decline on a missing attribute, skip recall on a statement, draft
with EAGLE — was wired **ad hoc** into the served `/v1/chat` handler as its own
env-gated `if` branch. Lesser models built each one as a standalone workaround, stacked on
the last, without a shared frame. The result was a ~1500-line ladder in `routes.rs`:
`if SP_INT2 { … } else if SP_B3_WC { … } else if SP_RECALL_JACCARD { … } else if
SP_RECALL_L5 { … nested attr-gate … } … if SP_B3_JUDGE { … }`. Adding a mechanism meant
archaeology; the mechanisms fought each other over shared mutable locals (`recalled`,
`symbolic_decline`, `syn_last`); and nothing in the type system stopped a "decider" from
reaching into the token stream — the exact fusion ADR-002 forbids.

The spine is the **thing of beauty** that ends that: one seam, two roles, a fold.

## 2. The shape

```text
   ┌─────────────┐   immutable    ┌──────────────────────────────────────────┐
   │  forward     │──── latent ───▶│  LatentView  (raw_user, l5_query, stores) │
   │  (one pass)  │   footprint    └──────────────────────────────────────────┘
   └─────────────┘                         │  fold over Deciders (priority order)
                                            ▼
        [ QOnly-aware L5Recall ] · [ AttrGate ] · [ JudgeVeto ] · [ RouteHead ] · [ Wc ] …
                                            │  each refines the decision-so-far
                                            ▼
                                    ┌──────────────────┐
                                    │  LatentDecision  │  Pass / Deliver / Decline / Route
                                    └──────────────────┘   (a DISCRETE intent — no tensor)
                                            │
                                            ▼
                                    ┌──────────────────┐
                                    │    Executor      │  drives cache + SSE; never reads a tensor
                                    └──────────────────┘
```

## 3. The three types (the whole boundary contract, in Rust)

* **`LatentView<'a>`** — an *immutable* borrow of the turn's latent footprint: the raw
  user text, the query's L5 embedding (`l5_query_embed(global_q)`), the episode stores,
  the thresholds. A decider gets `&LatentView`; it cannot mutate the cache or emit a token
  because it has no handle to either. The borrow checker is the enforcement.

* **`LatentDecision`** — the sole currency crossing Tier-1 → Tier-2. An enum of *discrete
  intents*: `Pass` (normal generation), `Deliver { episode, framing }` (recall a fact
  in-context), `Decline { message }` (zero-inference symbolic decline), `Route { target }`
  (telepathy). It carries a *selection* (which episode) and *content* (its text) — never a
  hidden tensor. A decider that wanted to fuse latent content into generation has no channel
  to: it returns this enum, and the enum has no tensor variant.

* **`Decider`** — `fn refine(&self, view: &LatentView, current: LatentDecision) ->
  LatentDecision`. Reads the view + the decision-so-far, returns the refined decision.
  `&LatentView` in, value out — nothing else. This is where every head and gate lives.

* **`Executor`** — one `match` over `LatentDecision` that drives the cache/stream: `Deliver`
  rebuilds the augmented prompt + prefills it; `Decline` streams a fixed string with **no
  forward** (leak impossible); `Pass` runs normal generation. Its input is the discrete
  enum; it never sees a tensor. It lives in the same module so the whole spine is one place.

## 4. The dispatch is a fold (the elegant part)

The deciders form a **priority pipeline**. Priority == order in the list. Each refines:

```rust
let mut decision = LatentDecision::Pass;
for d in deciders {
    if decision.is_terminal() { break; }   // Decline / Route are terminal
    decision = d.refine(view, decision);
}
```

A selector turns `Pass → Deliver`. The attribute-gate turns `Deliver → Decline` when the
fact does not state the queried attribute (the SNE shield). A judge veto turns
`Deliver → Pass` (reject a spurious recall). QONLY makes a selector abstain on statements.
That single fold *is* the whole recall/reject/decline logic that used to sprawl across
1500 lines. Reading it, the architecture is self-evident.

## 5. Heads are Deciders (the multi-head design, finally paying off)

The project's **multi-head design** — a bank of tiny latent classifiers (route head, W_c
recall head, judge, EAGLE/MTP draft) — is unique and powerful because each head is a *cheap
read on a forward pass you are already computing*: it rides the captured global-Q/K or
`capture_feat`, so N heads cost N little matmuls, not N forwards. A monolithic runtime must
*generate* to decide; these heads *decide from the latent* before a token is emitted.

The spine is the home that makes them worth it: **a head is a `Decider`.** This is now
BUILT (G-SPINE-HEADS GREEN): the `LatentHead` trait (`score(view, ep) -> f32` +
`reject_floor`) captures "a trainable head that scores an episode from the latent," and the
`HeadSelector<H>` adapter turns ANY `LatentHead` into a selecting `Decider` in one line
(argmax over the reject floor). The learned **W_c recall head** is ported as the exemplar
(`WcRecallHead`): it reads `view.global_q` against each episode's stored `ep.gk`, scores via
logsumexp-mean, and its `s0` is the NULL slot. `build_pipeline` runs a fired head first, then
the cosine selector, then the veto — and re-gating with the head added (W_c off in the
one-config) reproduced P 54/61 byte-for-byte: the abstraction is behavior-preserving. Adding a
head is now: `impl LatentHead` + drop into the pipeline; the compiler guarantees it cannot
fuse or execute. This realizes ADR-LATENT-NATIVE-UNIFICATION: every symbolic gate graduates to
a latent head, and they *all compose in one typed seam*.

The payoff this unlocks: a committee of heads on every turn — route + recall + reject +
tool-detect + safety + self-draft — each cheap, each independently trainable against its own
oracle, adjudicated deterministically by the fold. A committee of latent classifiers over
the residual stream, arbitrated by a compiler-enforced spine. That is a genuinely novel
shape, and it is now the living architecture, not a pile of workarounds.

## 6. Status (what is live, what plugs in next)

* **LIVE + GATED GREEN.** `L5Recall` (cosine select) + `AttrGate` (zero-inference decline),
  QONLY-aware, run the served one-config stack through the spine: `G-SPINE-ONECONFIG` =
  **P 54/61 · S 3/3 · F 2/2 · C · Q 2/2 · X byte-identical** — identical to the inline
  baseline. Behavior-preserving. `SP_SPINE=1`; unset ⇒ the inline path byte-untouched.
* **Scaffolded extension points (next ports, mechanical not archaeological):** `Route` (the
  telepathy head → executor), `JudgeVeto` (the generative judge as a `Deliver → Pass`
  refiner), the `W_c` / `Jaccard` / `INT2` selectors (each a `Pass → Deliver` decider),
  `Forget` and operator `Replay`. Each is a named place in the fold with a typed signature.
* **The vision:** a `HeadDecider` adapter (latent head weights → `Decider`) so porting a
  head is loading a `.bin` and dropping it into the pipeline.

## 7. Files

`tools/sp_daemon/src/spine.rs` (the framework: types, traits, deciders, executor, fold),
wired at the `/v1/chat` recall seam in `tools/sp_daemon/src/routes.rs` behind `SP_SPINE=1`.
Governing law: `papers/PPT-LAT-ADR-002-DECIDE-EXECUTE-SPINE.md` (§4 boundary contract, §8.2
typestate refactor — now BUILT for the live stack). Receipt:
`tests/fixtures/chat_fullstack/G-SPINE-ONECONFIG.log`.
