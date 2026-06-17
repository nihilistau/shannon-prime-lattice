# CONTRACT-XBAR-R3 — Ring-3 consolidation (the gist tier) — PRE-REGISTRATION

**Status:** STAGED (2026-06-17). Contract + pre-registered gates locked **before any resource is allocated**, per the scope-fence discipline. **Not opened.** Opening requires the operator's explicit go (and, for the training path only, a budget green). Parent: RFC-XBAR v1.1 §3.1 (the Ring-3 amendment, `G-R3-LOSS`), `DESIGN-VSA-ring3-holographic.md` (the parameter-free mechanism), `CONTRACT-XBAR-P2b-adapter.md` (the convicted learned path), `CONTRACT-XBAR-C2-memo-curator-loop.md` (the Ring-2 verbatim loop this sits above, now CLOSED incl. #222).

**One line:** Ring-2 (now closed) is the verbatim hippocampus — bit-exact recall, O(1) evict/rewind. Ring-3 is the neocortical gist: superpose many episodes into one bounded store, recall by content address with **graceful, bounded, pre-registered loss**. The crossbar's first *lossy* tier — so it is the first one whose gate is irreversible.

---

## 1. The non-negotiable boundary (the §4 trap)

Consolidation is **consolidation-time only.** A Ring-3 gist is written during the idle/NIGHTSHIFT loop and read back as native context. **Recall-time gist *upsampling* is FORBIDDEN** (`DESIGN-diffusion-lane.md` §4): the model must never hallucinate detail back out of a gist at read time — that manufactures confident false history. Ring-3 returns either (a) the gist as-is (shortlist/address), or (b) a pointer that triggers a Ring-2 verbatim retrieve. It never reconstructs the raw span generatively at recall.

## 2. Architecture — retrieve-and-verify, NOT generate-fill (the P2.b verdict, honored)

P2.b is closed-as-convicted: span→k=2 **generation** is dead (6 forks); **recognition** is real-but-sub-usable (Fork-6 top-1 0.462 < 0.50, but **top-5 = 0.77** — a shortlister, not a sniper). That verdict is load-bearing here: Ring-3 is a **two-stage retrieve-and-verify**, exactly the door P2.b's top-5 opened —
1. **RETRIEVE (Ring-3, lossy):** content-address the gist store with the live cue → a **shortlist** of candidate episode-ids (not a single answer, not a reconstructed span).
2. **VERIFY (Ring-2, exact):** the C2 curator resolves each shortlisted id to its verbatim episode and gates it with the already-closed machinery — `SP_REPLAY` inject (#222) → `SP_G4_SCORE` deflection < 2% → promote, else discard/rewind O(1).

Ring-3 never has to be *right*; it has to be *not-wrong-enough to shortlist*, and Ring-2's exact verify carries the fidelity. This is the only framing consistent with the measured P2.b numbers.

## 3. Two candidate mechanisms — and a budget fork the operator should see

| | **Path A — VSA / HRR binding** (`DESIGN-VSA-ring3-holographic.md`) | **Path B — P2.b learned adapter** (n→k gist) |
|---|---|---|
| Mechanism | `m_i = INTT(NTT(key_i) ⊙ NTT(value_i))` superpose; recall by unbind w/ engineered near-orthogonal carriers | trained adapter compresses n raw tokens → k pseudo-token gist |
| Training | **NONE — parameter-free, on the existing NTT/CRT substrate** | **cloud bake (RunPod), cost-capped — research-risk arm** |
| Budget | **~zero** (compute-only, idle-loop) | **requires operator budget green** |
| Shannon-Prime fit | discrete `Z_q`, exact bind, lossy-by-design superposition; auditable | adapter = continuous fp; convicted for generation, only shortlist-grade for recognition |
| Risk | crosstalk/capacity at high load (the gist quality question) | known hard negatives; needs the retrieve-and-verify framing to be usable at all |

**Recommendation:** open Ring-3 on **Path A first** — it is parameter-free, native to the substrate, and **needs no training budget**, so it tests the *whole Ring-3 thesis* (superpose → content-address → shortlist → verify) for the cost of compute. Path B (the adapter) only earns its training budget if Path A's shortlist recall is measured insufficient. This sequencing means the operator's budget decision is **deferred until there is evidence it is needed** — not spent up front.

## 4. Pre-registered gates (locked now; thresholds pinned BEFORE any run)

- **G-R3-NULL (substrate floor).** Ring-3 wired but empty / disabled ⇒ the C2 loop + decode are byte-identical to the closed C2 baseline (the bit-exact-when-off discipline, as every prior tier). *Falsify:* any drift.
- **G-R3-BIND (Path A mechanism, offline).** Bind K planted (key,value) episode descriptors into one `Z_q` store; unbind each by its carrier; the recovered descriptor's nearest-neighbour over the planted set is the correct id at **recall@shortlist-k ≥ a pinned floor** (pre-registered from a capacity sweep: bind {8,16,32,64,128} episodes, report recall@1 and recall@5 vs the superposition-load crosstalk curve). *Falsify:* recall@5 collapses to chance before the target capacity.
- **G-R3-LOSS (the irreversible consolidation gate — RFC §3.1, load-bearing).** For each candidate consolidation: measure the **recoverable-information delta** — PPL of a held-out continuation that *depended on the raw span* under {Ring-2 verbatim} vs {Ring-3 gist}, **plus** a NIAH-style fact-survival probe on facts inside the compressed span. Promote **only if loss ≤ a pinned budget**; otherwise the span **stays verbatim in Ring-2** (a valid, logged outcome — not a failure). The gate runs **BEFORE source eviction**, and the eviction is part of the same receipt or does not happen (a bad Ring-3 promotion cannot be rewound — the raw source is gone). *Falsify:* loss exceeds budget and the source is evicted anyway.
- **G-R3-DUALROUTE.** Dual-store recall (Ring-2 verbatim + Ring-3 gist): empty-Ring-3 parity (== Ring-2-only) + the measured scan-cost of adding the Ring-3 lookup. *Falsify:* dual-route changes the answer when Ring-3 is empty, or the scan cost is not O(1) in episode count.
- **(deferred) G-R3-PROV.** The CRT/sentinel provenance tag (the "encoding gap", RFC §3.1) — agency-gain test: held-out PPL with vs without the provenance tag; adopt only if `Δppl < 0`. Post-R3 refinement, never bundled into the first run.

## 5. Build order (smallest falsifiable steps)

1. **R3.0** — `G-R3-NULL`: wire the dual-route scaffold over the closed C2 loop, disabled ⇒ byte-exact floor. (no budget)
2. **R3.1 (Path A)** — `G-R3-BIND`: offline VSA bind/unbind capacity sweep on planted episode descriptors; pin recall@5 vs load. (no budget)
3. **R3.2** — `G-R3-LOSS`: on planted episodes with raw-span-dependent continuations, measure the consolidation loss + fact-survival; pin the promotion budget. (no budget)
4. **R3.3** — `G-R3-DUALROUTE`: wire RETRIEVE(Ring-3 shortlist) → VERIFY(Ring-2 + the closed #222 inject/score/rewind); the full two-stage loop on 12B + E2B. (no budget)
5. **R3.4 (NIGHTSHIFT)** — the idle-loop driver: Ring-2 → (bind) → Ring-2′ shadow → (G-R3-LOSS) → Ring-3, pre-eviction-gated. (no budget for Path A)
6. **R3-B (only if R3.1 shortlist is insufficient)** — open Path B: the P2.b adapter training campaign, **gated on operator budget green**, retrieve-and-verify framing, cost-capped RunPod bake.

## 6. Scope fence

- Ring-3 is **Ring-2-verbatim's gist companion**, not a replacement. The verbatim store and its O(1) evict/rewind/replay (C2 + #222, CLOSED) remain the source of truth; Ring-3 only *shortlists* into it.
- **No training is opened without the operator's explicit budget green** (Path B / R3-B only). Path A (R3.0–R3.4) is compute-only and needs no budget.
- Recall-time gist upsampling stays FORBIDDEN (§1). The provenance tag (G-R3-PROV) is deferred.
