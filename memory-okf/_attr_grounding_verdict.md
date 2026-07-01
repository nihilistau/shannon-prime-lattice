# Attribute-grounding mitigation: deterministic ATTR-GATE is a COMPLETE fix for the private/structured-entity regime, but over-declines paraphrase. STRICT prompt rejected.

Built two default-off levers in the L5-direct delivery (engine `recall::attr_absent_ratio` + routes.rs SP_RECALL_STRICT / SP_RECALL_ATTR_GATE) to fix the SNE confabulation (80%) + secret-leak (5%) found by the Novel-Entity Crucible.

## Results (served 12B)
| lever | SNE MATCH recall | SNE MISMATCH | paraphrase recall (fct-12) |
|---|---|---|---|
| baseline (recite) | 20/20 = 100% | confab 80% / leak 5% / decline 15% | 6/12 = 50% (subset) |
| **SP_RECALL_STRICT** (closed-book prompt) | **0/4 = 0% (over-declines even valid match!)** | decline | — (rejected) |
| **SP_RECALL_ATTR_GATE** (τ=0.5, deterministic) | **20/20 = 100%** | **decline 20/20 = 100%, confab 0%, leak 0%** | **0/12 = 0% (over-declines all paraphrase)** |
Receipts: `tests/fixtures/chat_fullstack/G-SNE-ATTRGATE-2026-07-01.log`, `G-SNE-STRICT-OVERDECLINE-2026-07-01.log`, `G-ATTRGATE-PARA-REGRESSION-2026-07-01.log`.

## Findings
1. **STRICT closed-book prompt = REJECTED.** Told to answer only from the fact, the model over-declines — it declined even valid MATCH queries where the value IS in the fact (0/4). Blunt instruction trades confabulation for total refusal. Dead lever.
2. **ATTR-GATE is a COMPLETE fix for the private/structured-entity regime.** On SNE (verbatim entity IDs + exact-attribute queries): MATCH 100% recall preserved (absent-ratio 0 → recite), MISMATCH 100% decline (absent-ratio 0.5 → forced "I do not have that information"), confabulation 80%→0%, leak 5%→0%. Surgical because it declines ONLY on lexical attribute-absence.
3. **ATTR-GATE over-declines paraphrase (0/12).** A reworded NL query ("which world orbiting our star…" vs fact "largest planet…Saturn") makes ALL salient words "absent" → force-decline. The lexical gate cannot tell reworded-same-attribute from different-attribute (that's semantic). τ can't separate them: paraphrase absent-ratio (~1.0) EXCEEDS SNE-mismatch (~0.5).

## Deploy decision
**ATTR-GATE ships default-off; recommended ON for private/structured-entity memory (config values, override codes, credentials, IDs — queried with verbatim entities + precise attributes), OFF for general paraphrased chat.** Both regimes have a working config. STRICT stays a documented dead lever. Null floor preserved (both flags unset = the proven recite path).

## The refinement that would make it GLOBALLY safe (next build, bounded)
**Shared-rare-token guard:** only force-decline when the query AND fact share a HIGH-ENTROPY verbatim token (a digit/mixed-alnum/proper-ID token — the private-entity signature) AND the attribute is absent. On paraphrase the subject is reworded → no shared rare token → gate does NOT fire → paraphrase recall preserved. On SNE the Node-ID is shared verbatim → gate fires. This turns the regime-specific tool into a globally default-on-safe one. Recommended next step; not yet built.

## Anti-rebuild
attr_absent_ratio + the two flags are DONE (engine recall.rs + routes.rs). The open item is the shared-rare-token guard (to make it paraphrase-safe), NOT re-deriving the gate. STRICT is a dead lever — do not revisit.
