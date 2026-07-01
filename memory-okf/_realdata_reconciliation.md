# Reconciliation: the L5 finding HALF-overturns the earlier "input is the wall" realdata conclusion

Earlier (G-KSTE-MD-REALDATA, memory c90d457): "on real last-token global-Q, cosine gap same-vs-diff = 0.038, recall 11.5%, kste_md 1.6% → the input is content-poor, the input is the wall, the unlock is a NEW pooled-embedding capture." The L5 finding (G-REP-LAYER-L5, aee79cba) forces a correction.

## What was WRONG (too pessimistic) — the earlier realdata number was measured on the LAYER-AVERAGED vector
- The 0.038 gap / 11.5% recall was on the ALL-8-global-layer representation (flat65536 / mean-over-heads-and-layers). **Averaging the 8 global layers DESTROYED the signal.**
- On **global layer 5 ALONE**: cosine gap **+0.086**, exact→paraphrase recall **85.2%**; L5 query-key recall = **100% exact / 88.5% paraphrase**. The content was PRESENT, layer-localized.
- So "the input is the wall / content-poor" was an ARTIFACT of the representation, NOT intrinsic. And "the unlock needs a new pooled-embedding capture" is WRONG — the unlock is **layer SELECTION (index L5)**, already in the existing `read_global_q` capture. No new capture needed for the query side.
- The through-line "every method hits the 0.038 ceiling / nothing content-bearing is captured" is superseded: cosine on L5 hits 85%.

## What STANDS (sharpened) — the kste_md verdict survives, for a BETTER reason
- kste_md still does NOT go on the global-Q recall/consolidation path — but the reason UPGRADES from "input content-poor" to **"wrong geometry."** On the L5 rep that cosine aces at 85%, **kste_md is still 3.3%** (G-REP-LAYER-L5 confirm). The L5 fact signal is **directional/angular** (cosine reads it); kste_md reads **magnitude-profile shape** — orthogonal geometry, so kste_md is blind to it REGARDLESS of input quality.
- "kste_md amplifies input separability" → refined to **"magnitude-shape separability"**; it cannot amplify directional/angular separability.
- Consequence for kste_md's "home": NARROWER than earlier claimed. Earlier I said "pooled sentence embedding (TELE-1)". But TELE-1 retrieval@1=1.0 is a COSINE (directional) result — kste_md may be blind there too. kste_md's genuine home is data whose DISCRIMINATIVE axis is magnitude/sign-profile, not angle. Do not assume it helps on any cosine-separable embedding.

## Net
- The REAL live win is **L5 + cosine** (query-to-query), now being wired (SP_RECALL_L5, branch feat/l5-recall). It is a cosine/directional win, NOT a kste_md win.
- kste_md remains a proven, banked, gated magnitude-shape primitive with a narrower home than first thought.
- Corrects the pessimism in c90d457 (the "need a new pooled capture" claim); the actual fix was already-captured layer selection.
