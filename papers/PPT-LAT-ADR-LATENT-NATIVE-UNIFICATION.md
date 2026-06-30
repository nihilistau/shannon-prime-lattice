---
type: design
title: "ADR — Latent-Native Unification: the Sovereign Latent Brain (symbolic gates as training oracles)"
description: "Architecture decision: every symbolic mechanism the project discovers is a training JIG, not a ceiling. Each graduates to a continuous latent head in the Interceptor family, trained against its symbolic oracle, on its CORRECT substrate. Triggered by the Faithfulness arc (F1->F1b.1->F2b): the win was the PROMPT + right-substrate selection, and the latent paths were undertrained/mistuned, not falsified. Tokens are the discrete sampling of the manifold; there is no separate symbolic domain."
tags: [design, adr, latent-interceptor, sovereign-latent-brain, faithfulness, telepathy, oracles, substrates]
timestamp: 2026-07-01T00:00:00Z
resource: shannon-prime-lattice/papers/PPT-LAT-ADR-LATENT-NATIVE-UNIFICATION.md
sp_status: DRAFT
sp_gate: "per-graduation gate vs its oracle (G-FAITHFUL-RECALL-JACCARD = the selection oracle)"
sp_commit: TBD
sp_repro: "oracles live + GREEN: tests/fixtures/faithful/G-FAITHFUL-RECALL-JACCARD (15/15); the latent graduations are the work this ADR plans"
---

# ADR — Latent-Native Unification (the Sovereign Latent Brain)

## Context (and the correction that forced it)

The Faithfulness arc this session (F1 in-context 100% → F1b.1 pure-KV recall 0% → F2b Jaccard+text 100%) was first read as a *boundary law*: "latent decides, symbol carries precise content." **That reading was wrong, and the operator caught it.** The corrected reading, which this ADR adopts:

- The latent paths did not *fail* — they were **undertrained / mistuned and abandoned early**, then a symbolic crutch was stood up, the crutch only limped until the **prompt** was added, and the prompt was the real lever (text-in-context 33% → 100% with the faithfulness system prompt).
- W_c did not prove "latent can't select facts" — it was **trained on high-entropy novel needles** and pointed at natural-language facts (a distribution mismatch). The same head scores 360/361 on its own corpus.
- Pure-KV delivery failed at **one attenuation** (`M_target=42`), not as a class.
- **Tokens are the discrete sampling of the continuous manifold.** There is no separate symbolic domain — only the arbitrary boundary lines we draw inside latent space.

**Therefore:** the symbolic/legacy gates are **training jigs**. They generate high-fidelity datasets + exact activation labels; a latent head trains against the jig; once it clears the jig's gate, the crutch is kicked away. This is the project's proven methodology (the causal-ablation oracle trained W_c; the deterministic verifier trains the judge). The boundary thesis is **downgraded from law to frontier**: symbolic = oracle + deployment fallback, never the ceiling.

## Decision

The long-term system is a **Sovereign Latent Brain**: one Interceptor head *family* on the continuous manifold is the unified control plane, and every successful symbolic mechanism graduates to a head trained against it. Crucially, each head graduates on its **correct substrate** (grounded, not assumed).

### Substrate map (grounded 2026-07-01 from the live code)

| substrate | dim | verb | who rides it |
|---|---|---|---|
| 12B hidden feat | 3840 | `gemma4_kv_capture_feat` | Interceptor decision heads (action/tool/route, `li_probe`) |
| EAGLE draft body | 1024 | `gemma4_draft_body` | Memory Head (`mh_probe`), bridges body→global-K |
| global K/Q | 512×n_global | `read_global_q` / `read_global_k` | **W_c recall selection** (attention-relevance) |

**Rule:** *decisions* (classify) ride `capture_feat`; *retrieval/selection* (match query↔episode) rides **global K/Q** — the model's native relevance space. Do not move retrieval onto the classifier tap.

## The three graduations (oracle → latent head, on the right substrate)

### 1. Selection — Jaccard → Natural Recall Head  *(graduate on global K/Q; do NOT fold into the draft-body suite)*
- **Oracle:** `recall::token_overlap` (Jaccard) — `G-FAITHFUL-RECALL-JACCARD` 15/15, the right natural-language episode every time.
- **Latent move:** retrain/specialize the **W_c-family** retrieval head on the **natural-fact distribution**, labels = the Jaccard hits, substrate = global K/Q. W_c is not structurally incapable; it was optimized for the needle haystack. (The Memory Head's body→global-K bridge is available if a 1024-d entry is wanted, but the direct global-K retrain is the proven, simplest path.)
- **Gate:** match the Jaccard oracle's selection on the fact-conflict set (target 15/15), then on a larger held-out natural-fact corpus.

### 2. Faithfulness — `T_CONSOLE` prompt → Faithfulness Head  *(steering delta on the residual)*
- **Oracle:** the faithfulness system prompt ("use facts you were given faithfully…") — drives obedience 33% → 100% on the text path.
- **Latent move:** capture the **activation/steering delta** of the model running under that system prompt vs without; map it to a continuous head that injects the same geometric bias into the residual stream (the **TELE-2** steering mechanism, already 1.000 steer-acc), instead of spending sequence length + attention bandwidth on the token string.
- **Gate:** latent-steer obedience == the text-sys-prompt 100%, with coherence held.

### 3. Delivery — text-in-context → ordered latent prefix  *(the research leg)*
- **Oracle:** text-in-context synthesis (clean tokens to prefill) = 100%.
- **Latent move:** NOT uniform `kv::replay` (structurally flat, position-blind — 0%). Follow **TELE-5 readable-prefix**: map the retrieved fact to an *ordered, positionally-encoded multi-vector* injected at early layers, matching how the model natively reads token embeddings (TELE-5 already showed ordered latent bandwidth, +1.45 nats corr−shuf).
- **Gate:** latent-prefix delivery obedience == text-in-context 100% on a held-out set. **Honest tag: unproven; the 100% text run is the oracle to train + grade against.**

(Telepathy carries the same way: decide-route in latent [proven]; the precise task currently executes clean-text [oracle] → graduate the transmit toward latent as fidelity allows, same jig→head pattern.)

## Near-term execution — F3 Data Capture (the immediate task; engine untouched until data is in hand)

Keep `SP_RECALL_JACCARD` text-in-context **live** as the stable deployment fallback AND the data-generation oracle. During its 100%-obedient fact-conflict resolutions, log, per turn:
1. **Query global-Q** (`read_global_q`, last prompt token) — selector input.
2. **Selected episode global-K** (`ep.k` / `read_global_k`) + the **Jaccard label** (which episode, overlap) — selector target.
3. **Hidden residual** (`capture_feat`) of the answer turn **with** the faithfulness system prompt vs **without** — the **faithfulness steering delta** (head-2 target).
4. (delivery) the in-context fact's embedding-space prefix vs the model's read of it — head-3 target.

Reuse the existing dump rails (`SP_ARM_DUMP` QRKP global-K/Q dump, the `SP_B3_QDUMP` query-dump) + add the with/without-sys-prompt residual capture. Output = three training sets, one per graduation. No new heads trained until the capture is verified.

## Sequencing (the fork, decided)

**Selector first** (highest confidence: W_c-family retrain on the right distribution, oracle is GREEN), then the **Faithfulness steering head** (TELE-2 mechanism proven), then **Delivery** as the research leg. Rationale: graduate the high-confidence, oracle-GREEN gate first so the methodology is re-confirmed before the open research leg. The selector graduates **in place on global K/Q**; the trigger/ground/route **decisions** extend the Interceptor classifier suite on `capture_feat`.

## Consolidation payoff

Retire the parallel *deciders* (standalone q·K, C2 centroid-sig Hamming, ad-hoc thresholds) into the one head family. Keep the symbolic gates as oracles + fallbacks. One latent control plane; each capability graduated symbolic→latent only when a trained head matches the oracle's gate.

## Open questions
- Does the faithfulness steering delta generalize across prompts/topics, or is it fact-specific?
- Delivery: can an ordered multi-vector latent prefix actually override a strong prior (the unproven leg)? Oracle = the 100% text run.
- Selector: retrain W_c vs a fresh head — and does one head cover both natural facts AND novel needles, or do we keep two regimes?
