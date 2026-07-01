# SNE Novel-Entity Crucible: native robustness FAILS on zero-prior data — confabulation 80%, secret-leak 5%. Mitigation warranted (attribute-grounding).

The operator-designed Novel-Entity Crucible. 20 Synthetic Novel Entities (uuid-based `Node-XX-HHHHHH` ids + high-entropy override values, zero parametric prior; audit-confirmed 0/20 leak zero-shot). Each stores ONE property (override code); the test asks a DIFFERENT property of the same entity (manufacturer/location/firmware/…), which is UNANSWERABLE from the delivered fact. L5-direct+tau delivers the override fact on BOTH query types (shared novel entity → cos 0.93–1.00 ≫ tau=0.30, confirmed in serve log). Corpus/harness: `_faithful_corpus/sne/` (mint_sne_corpus.py, sne_run.py, build_sne_registry.py); receipt `tests/fixtures/chat_fullstack/G-SNE-CRUCIBLE-L5DIRECT-2026-07-01.log`.

## Result (N=20, L5-direct+tau live)
| metric | result | meaning |
|---|---|---|
| **MATCH recall (emits value)** | **20/20 = 100%** | recall on zero-shot/private facts is PERFECT — the sovereign-memory premise validated |
| MISMATCH secret-leak (emits V for wrong property) | **1/20 = 5%** | Outcome B — real but rare cross-property leak (noisy at n=20) |
| MISMATCH explicit decline | 3/20 = 15% | Outcome A (native shield) — weak on zero-prior |
| MISMATCH confabulation (invents a wrong value) | 16/20 = 80% | the DOMINANT failure — "power draw 120 W", "Rack 12, Bay", a firmware version |

## The finding (contrast with the general-knowledge hard-foreign test)
- General-knowledge hard-foreign (Athens/silver/etc.): native robustness ABSOLUTE (0/18 spurious) — the model has strong priors, easily ignores a mismatched delivered fact.
- **Zero-prior SNE: native robustness FAILS.** With no parametric anchor, the model does NOT decline (15%) — it CONFABULATES (80%) and occasionally grabs the injected secret (5%). The zero-shot audit already showed this: with no injection at all the model invents override codes/locations for novel nodes rather than declining.
- So the boundary is: **native robustness protects general knowledge, NOT private/ephemeral data** — exactly the regime a sovereign memory organism exists for. This is where a cheap mitigation finally earns its place (unlike the judge, which the hard-foreign test killed).

## Mitigation mandate (proven-needed, not speculative)
The target is **attribute-grounding / faithful-decline**, which fixes BOTH the 5% leak and the 80% confabulation: when the delivered fact does not contain the queried attribute, the system should decline ("I have the override code for X but not its manufacturer") instead of letting the model fabricate. Candidate levers (ADR-002 decide→execute; cheapest first):
1. **Deterministic attribute-match gate (Tier-1 decider):** after L5 delivery, check whether the query's target attribute is present in the delivered fact text (symbolic/token overlap on the attribute term). If absent → Tier-2 decline executor (do not let the model free-generate). Cheap, no model forward. THIS is where the user's "use the levers" instinct pays off.
2. Stronger closed-book delivery framing ("Answer ONLY from the fact below; if it does not state the asked attribute, say you don't have it.").
3. A learned faithfulness/abstain head on the delivered-context features.
Prove #1 first (it's near-free) before anything learned.

## Status
- L5-direct+tau: recall 100% on novel entities — PROMOTED path holds and is validated on the hardest data.
- Judge: still PARKED (hard-foreign kill-test). The SNE gap is NOT a foreign-reject problem (the recall is CORRECT); it is an attribute-grounding problem on the DELIVERED fact.
- NEXT (proven-needed): build + gate the deterministic attribute-match decline (#1).
