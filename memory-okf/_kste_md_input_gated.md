# KSTE v2 (kste_md) is INPUT-GATED — do NOT wire it to the global-Q memory path

The v2 magnitude-as-depth encoder's 37.6× discrimination (G-KSTE-MD, synthetic Gaussian clusters) does NOT transfer to real vectors on the content-poor input. Verified fresh: `G-KSTE-MD-REALDATA-2026-07-01.log`.

**Test:** real gemma-4-12B captures, 61 exact-query global-Q vs 61 paraphrase-query global-Q (same facts, LN-1 data). Recall@1 (exact→its own paraphrase over 61):
- raw cosine 11.5% (7/61); KSTE-MD **1.6% = random floor**; would-dedup ratio **1.00×** (v1 1.03×).
- ROOT CAUSE = the DATA: same-fact vs diff-fact cosine gap only **0.038** (0.872 vs 0.834). The vectors barely separate, so even dense cosine is near-floor. KSTE-MD amplifies whatever separability the input HAS; last-token global-Q has ~none. Re-confirms LN-1 (input representation is the wall) with an independent method.

**Consequences (bounding where kste_md can be used):**
- **DO NOT** wire kste_md into the global-Q memory path: recall selection, episodic memory consolidation / near-dup pruning, or "semantic bloom filters" keyed on episode global-Q — ALL run at ~1.00× on real vectors. (This kills Gemini's "wire memory consolidation into facts.json ingest" idea twice over: facts.json is curated-distinct with no near-dups anyway, and the vectors don't separate.)
- kste_md's discrimination is REAL only on content-bearing vectors where cosine already separates (e.g. pooled sentence embedding, TELE-1 retrieval@1=1.000). There it's a cheap, exact-integer, Dickson-bounded discrete DEDUP KEY (its edge over cosine), NOT a magic discriminator. Using it requires the pooled-embedding capture (not wired).
- Also unbuilt / speculative-on-nothing: PoUW integration (frozen-v1 wire + no live chain), DHT bloom filters + drift detection (SP-SWARM is design-only). Park as SP-SWARM notes, not builds.

**Keep:** kste_md is a proven, gated CPU primitive (G-KSTE-MD + T_KMD 11/11). Its power is genuine but INPUT-GATED. Do not claim real-world semantic discrimination on last-token global-Q.
