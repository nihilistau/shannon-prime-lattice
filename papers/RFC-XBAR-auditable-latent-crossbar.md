# RFC-XBAR — The Auditable Latent Crossbar (Exec + Memo sharing Ring 2)

**Status:** **v1.1** (Ring 3 consolidated tier added 2026-06-09, §3.1); **v1** (consolidated 2026-06-09 on P1/P2.a POC data; v0 brainstorm formalized 2026-06-07, KnackAU + Gemini + Claude). v1 deltas: §5 roadmap rewritten on measured physics (P1 CLOSED ledger X-R1; P2.a CLOSED; PLE-stall theory formally corrected in CONTRACT-XBAR-P2); P2.b reframed as the span-compression adapter (CONTRACT-XBAR-P2b) — **the convergence point where the injector, the curator's compaction organ, the modality template and NIGHTSHIFT's worker become one trained component**; C1 split into C1-lite (qwen3 CPU ring, exists today) and C1-full (post-P3); §7 NIGHTSHIFT/Optane persistence design added; §8 endgame risk register added.
**Parents:** RFC-001 (discrete substrate doctrine) · CONTRACT-C2 (ARM Spinor-KV two-ring) · Phase 4-MeMo (M.0 stub / M.1 dual-load / M.2 zero-copy dialogue loop) · Heterogeneous-SoC manifesto (tricks #1, #4, #7, #9).
**One line:** two models — the Executive (Exec, $M_{gen}$) and the Memory curator (Memo, $M_{manage}$) — share Ring 2 of the cyclotomic memory and communicate through **latent state, not tokens**, with every write receipt-backed, gated, and rewindable. The industry strings agents together through the tokenizer; we hand them the same VRAM.

---

## 0. The name

**XBAR** — the Auditable Latent Crossbar. "Crossbar" because it is a switching fabric between models' latent states; "auditable" because that is the one word no floating-point agent stack can claim, and it is the entire reason this belongs in the lattice rather than in a PyTorch script. Lanes are XBAR-P (probe / physics), XBAR-C (curator), XBAR-M (modality lanes), XBAR-N (NIGHTSHIFT — idle-time consolidation).

## 1. The thesis

Multi-agent systems today communicate by detokenizing model A's state into text and retokenizing it for model B. The boundary is lossy, slow, and discards everything the residual stream knew that the argmax threw away. XBAR bypasses the boundary: Exec writes its episodic state into Ring 2 as it generates; Memo — a small, differently-trained curator — reads the ring **non-causally** (it is offline; it sees the whole episode at once), consolidates it, and writes back. Exec's next attention sweep picks up the curated state as native memory. No prompt, no tokens, no copy.

The same mechanism is the multimodal door: any encoder whose output is adapter-aligned to Exec's residual geometry (we already hold the audio path — voxtral-tts.c / VHT2 / Voxtral-4B) can deposit pseudo-token state into the ring. Not one-shot prompt multimodality — **persistent, curated, episodic multimodal memory.**

## 2. Why this is ours to build (the primitives already exist)

| Primitive | Status | Role in XBAR |
|---|---|---|
| Exec + Memo concurrent forward | **PROVEN** — M.1 dual-model cDSP, 1.796×, one `Arc<FastRpcSession>`; scheduler is model-agnostic | the two models already run together sharing the *scheduler*; XBAR's delta is sharing *state* |
| Memo artifact | **EXISTS** — M.0 stub (`qwen25-coder-0.5b-memory.sp-model`, sha-pinned) | starting body for the curator; XBAR-C retrains/replaces it |
| Two-ring cyclotomic memory | **IN MATH-CORE** — core/arm wired into `qwen3_generate_kv`, T_ARM_GENKV green | Ring 2 is the shared medium (NOTE: wired on the qwen3 CPU path; gemma4-CUDA ring wiring is XBAR-P3, not P1) |
| Spinor block ABI | **EXISTS** — 63 B + 0xA5 sentinel = 1 cache line; Frobenius-lift bit-identity as integrity receipt | the inter-model message format; a written block is *provably* well-formed |
| Transactional rewind | **EXISTS** — `sp_session_clone`/`rewind` (MTP work) | Memo operates on a clone; bad consolidation rolls back; canonical episode never corrupted |
| Accept/reject machinery | **EXISTS** — MTP draft→verify→byte-exact accept | repointed: gate whether an injected/consolidated memory is *promoted* into the canonical ring |
| ~120× Spinor KV compression | **MEASURED** (C2) | the cost structure: Memo re-reads a few hundred blocks, not 32k tokens — the curator is affordable |
| Owned VRAM arena (no GC) | **SHIPPED** — engine CUDA arena, OK_Q4B kernels | the zero-copy pointer handoff is real, not aspirational |
| CRT residue lanes | **DOCTRINE** — manifesto tricks #4/#9 | one prime lane per modality: audio and text blocks CRT-separable, never alias, provenance recoverable |

## 3. Architecture

```
        ┌─────────────────────────── VRAM (owned arena) ───────────────────────────┐
        │                                                                          │
        │   Exec (gemma-4-12B, OK_Q4B)          Memo (small curator, frozen-small) │
        │   causal forward, generates           non-causal pass over the episode   │
        │        │            ▲                        │             ▲             │
        │        ▼ write      │ attend                 ▼ propose     │ read        │
        │   ┌─ Ring 1 ─┐  ┌── Ring 2 (hippocampus) ┐  ┌─ Ring 2′ (shadow) ─┐       │
        │   │ working  │  │ verbatim Spinor KV,    │◄─│ Memo's proposals   │       │
        │   │ KV       │  │ recent + bounded       │  │ promote-on-accept  │       │
        │   └──────────┘  └────────────────────────┘  └─────────┬──────────┘       │
        │        ▲ recall from BOTH                              │ promote (gated)  │
        │        │                ┌── Ring 3 (neocortex) ───┐◄───┘                  │
        │        └────────────────│ adapter pseudo-tokens,  │   G-R3-LOSS bounded   │
        │                         │ consolidated long-term  │   (irreversible)      │
        │                         └─────────────────────────┘                       │
        │              modality lanes (CRT prime per modality):                      │
        │              audio adapter (voxtral), video, ...                           │
        └──────────────────────────────────────────────────────────────────────────┘
   Ring 2′ promotions: coherence/PPL delta → accept or REWIND (transient, reversible).
   Ring 3 promotions: G-R3-LOSS bounded BEFORE source eviction (permanent, irreversible).
```

Design rules (settled in the 2026-06-07 brainstorm):

1. **Memo is small.** It sorts latents, it does not speak. A few layers / low-rank operator / 0.5B-class body co-resides permanently with Exec inside 12 GB — no weight-swap latency. (Two 12Bs on a 2060 is a non-starter; it's also unnecessary.)
2. **"Backwards" = non-causal.** Exec is causal (past→future). Memo runs bidirectionally over the whole stored episode and rewrites it globally. That is the architectural form of consolidation ("sleep/replay"), not a vague autoencoder.
3. **Shadow ring, promote-on-accept.** Memo never writes the canonical Ring 2 directly. Proposals land in Ring 2′; a cheap downstream coherence gate (PPL delta over the post-injection window) accepts → promote with receipt, or rejects → rewind. The canonical episode stays clean and every promotion is auditable.
4. **Geometry is the law.** A ring entry is a per-layer, per-head (K,V) at a position — roped, normed, V-less where the architecture says so (gemma4 globals: V = raw K projection, weightless-RMS-normed, never roped). Nothing enters the ring that does not honor the coordinates. XBAR-P1 exists to *measure* how strict this law is.
5. **One CRT prime per modality lane.** Audio/text/video blocks are residue-separable in the same unified ring; Exec attends to one memory, provenance stays recoverable, lanes can never alias. (Manifesto tricks #4 + #9, applied to modality instead of hardware channel.)

## 3.1 The memory hierarchy — Ring 3, the consolidated tier (v1.1 amendment, 2026-06-09)

v1 carried two rings + a shadow. P2.b's reframing (the adapter as Memo's compaction organ) and the C2.4 finding (raw recall degrades past ~16× selection budget) together force a distinction we had been conflating: **a transient staging buffer and a permanent consolidated store are different objects.** Naming them separately yields a four-tier hierarchy that maps cleanly onto the brain's memory consolidation:

| Tier | Substrate | Representation | Lifetime | Biological analogue |
|---|---|---|---|---|
| **Ring 1** | RAM working window | verbatim KV, full attention | the live turn | sensory / working memory |
| **Ring 2** | Optane raw episodic store | verbatim Spinor KV blocks | recent episode (bounded) | **hippocampus** — recent, detailed, lossless |
| **Ring 2′** (shadow) | transient staging copy of Ring 2/3 | proposals awaiting the gate | one consolidation pass | (no analogue — it's the *audit* mechanism) |
| **Ring 3** | Optane consolidated store | **P2.b-adapter pseudo-tokens** (n→k gist) | long-term | **neocortex** — old, dense, semantic |

**The transfer-and-transform rule (what NIGHTSHIFT actually does).** Sleep does not just tidy the hippocampus; it *replays raw episodes and writes compressed semantic traces to neocortex.* NIGHTSHIFT does the same: it reads aging Ring 2 episodes, runs the P2.b adapter to compress n verbatim positions into k pseudo-tokens, proposes those to Ring 2′, and on gate-accept **promotes them to Ring 3** (and may then evict the now-redundant raw Ring 2 positions under the same receipt). Ring 3 is therefore populated *exclusively* by the adapter — it is the curator's compaction organ writing to its long-term destination.

**Recall-from-both (the Executive's new query path).** Exec no longer recalls from a single growing list. Per step it queries **Ring 2 for verbatim recent detail** and **Ring 3 for dense long-ago grounding**, and attends over the union. This is why Ring 3 *resolves* the C2.4 ceiling rather than re-hitting it: raw Ring 2 stays **bounded and recent** (where the selection budget is favorable — the NIAH ladder was clean through ~8k), and the long tail lives in Ring 3 as compact gist whose effective selection budget is k-per-episode, not n-per-token. You stop asking the raw router to do 64× selection over 32k verbatim positions — the regime where it broke.

**Honest negatives (operator-specified, on the board permanently):**

1. **Double-recall cost.** The router must now score candidates across *both* Ring 2 and Ring 3 every step — two stores, two index scans, a merged top-k. The ±1 projection sidecar already supports an arbitrary candidate set, so the mechanism composes; the *cost* is ~2× the routing scan plus a fetch from two physical stores (the C2.2 split-device `read_batch2` overlap pattern applies directly). Gate **G-R3-DUALROUTE**: dual-store recall reproduces single-store recall when Ring 3 is empty (parity null), and the added scan cost is measured, not assumed.

2. **The consolidation-loss gate (irreversible).** Compressing n raw tokens into k pseudo-tokens *discards detail by construction* — and unlike eviction (which the operator can refuse), a promoted Ring 3 block has thrown its source away. So the loss must be **quantified and bounded before promotion, permanently.** Gate **G-R3-LOSS**: for each candidate consolidation, measure the recoverable-information delta — PPL of a held-out continuation that *depended on the raw span* under {raw Ring 2} vs {Ring 3 gist}, plus a NIAH-style fact-survival probe on facts inside the compressed span. Promote only if the loss is within a pinned budget; otherwise the span stays verbatim in Ring 2 (some episodes are not compressible without unacceptable loss — that is a valid, logged outcome, not a failure). This gate is **load-bearing and irreversible-aware**: a bad Ring 3 promotion cannot be rewound the way a Ring 2′ proposal can, because the raw source is gone — so the gate runs *before* the source is evicted, and the eviction is part of the same receipt or does not happen.

3. **Ring 3 is the §4 risk surface, doubled.** Ring 3 blocks are adapter-*generated*, not model-*minted* — they are exactly the "semantically-wrong-but-valid" objects §4 warns about, now made permanent. The discrete substrate proves a Ring 3 block is *well-formed* (sentinel, lift identity); only G-R3-LOSS proves it is *faithful*. The coherence gate is therefore not optional on the Ring 3 path — it is the only thing standing between "consolidated memory" and "confidently fabricated history."

**Lane ownership:** Ring 2 verbatim store + cold-evict = **C1-lite** (heuristic, today, no adapter). Ring 3 consolidation = **C2** (the P2.b adapter) under G-R3-LOSS. NIGHTSHIFT = the offline loop that drives Ring 2 → (adapter) → Ring 2′ → (gate) → Ring 3. The C1-lite persistence format (episode = {K store, V store, manifest}) is the substrate both Ring 2 and Ring 3 serialize into; Ring 3 just carries pseudo-token blocks instead of verbatim KV.

## 4. The honest negative (stated up front)

"Injected memory as sudden realization" and "confident hallucination from off-manifold state" are the **same event** described twice. The discrete substrate detects *invalid* blocks (sentinel, lift identity); it cannot detect *semantically-wrong-but-valid* ones. Therefore the coherence gate is load-bearing, not decorative: no promotion without a measured downstream delta, accept-or-rewind, every time. This is the kernel-gating doctrine pointed at inter-model state.

Second honest negative: RoPE phase ties keys to absolute position; SWA layers fade injected state beyond their window (the GLOBAL period-6 layers are the long-range carrier); partial-rotary-0.25 globals are the most transplant-tolerant. The probe must quantify all three, not assume them.

## 5. Roadmap v1 (consolidated 2026-06-09 — rewritten on measured POC physics)

| Stage | Lane | What | Gate / exit | Status |
|---|---|---|---|---|
| **P1** | XBAR-P | Inception Probe — KV transplant A/B + escalation + 5×3 matrix | CONTRACT-XBAR-P1 G0–G4 + G1b + dual-metric G2 | **CLOSED — ledger X-R1 citable** (15/15 incorporation, 15/15 selectivity, 3.69 orders, dose-response curve) |
| **P2.a** | XBAR-P | Residual-entry pseudo-token mechanism probe | CONTRACT-XBAR-P2 G0E–G3E | **CLOSED** (ghost prompt ≥ KV transplant; blends fall off manifold; stall theory corrected — PLE falsified, PL=0 on the 12B) |
| **P2.b** | XBAR-P/C | **The span-compression adapter** (cloud-trained, frozen 12B): n-token span → k on-manifold pseudo-tokens; inversion Phase 0 → adapter Phase 1 → on-silicon deployment gate. *The keystone: injector + Memo's compaction organ + modality template + NIGHTSHIFT worker in one component.* | CONTRACT-XBAR-P2b G-P2b-0..4 | **SPEC'D** — next build |
| **C1-lite** | XBAR-C | Memo v0 heuristic curator on the **existing qwen3 CPU two-ring** (no new infra): select/merge/evict driven by router scores + the LRU access telemetry; full propose→gate→promote/rewind loop on Ring 2′ | loop closes; ≥1 promotion improves post-window PPL/NIAH vs no-curation; rewind receipts complete | **UNBLOCKED TODAY** — can run before P3 |
| P3 | XBAR-P | Ring wiring on the Exec path — two-ring to the gemma4 CUDA decode loop; KV slots become Spinor-block ring entries with receipts | T_ARM gates green on gemma4-CUDA; bit-exact null path | pending |
| C1-full | XBAR-C | C1-lite's loop re-run on Exec (gemma4-CUDA ring) | same gates, Exec path | pending P3 |
| C2 | XBAR-C | Memo v1 = the P2.b adapter applied to ring state: **fixed ring budget, maximize Exec's recall over the episode** (the adapter compacts; promote-on-accept gates). Open decision logged: Memo body may be *adapter + tiny ring-block encoder*, not the 0.5B M.0 stub | recall@budget beats C1 heuristics on held-out episodes | pending P2.b + C1 |
| **R3** | XBAR-C | **Ring 3 consolidated tier** (§3.1) — dual-store recall (Ring 2 verbatim + Ring 3 gist); NIGHTSHIFT writes adapter pseudo-tokens to Ring 3 under the irreversible loss gate | G-R3-DUALROUTE (empty-Ring3 parity null + measured scan cost) + G-R3-LOSS (n→k loss bounded, fact-survival, pre-eviction) | pending P2.b + C1-lite |
| M1 | XBAR-M | Audio lane — voxtral latents through the P2.b recipe (source swap), CRT prime lane | Exec answers questions about injected audio never seen as text | pending P2.b |
| N1 | XBAR-N | **NIGHTSHIFT** (§7) — episode persistence on Optane + offline Ring 2→Ring 3 consolidation under promote-on-accept, schtasks-owned | unattended run: net-positive gated promotions, zero canonical corruption, full receipt log | v0 (heuristic, Ring 2 evict) pending C1-lite; v1 (adapter, Ring 3) pending P2.b + R3 |

Order discipline, updated: P1's physics is banked — **training is now licensed**, and P2.b leads because four lanes converge on it. C1-lite runs in parallel on existing infrastructure (the curator's *control flow* needs no training and no CUDA port). Compute split: training = cloud (RunPod/Colab A100-class, bf16 bucket weights); deployment + every gate that touches receipts = the 2060/B1 artifact via the P2.a harness.

## 7. NIGHTSHIFT — the Optane subconscious (v1 design, operator synthesis 2026-06-09)

C2 already proved the substrate this rests on: byte-exact Ring-2 spill/recall on physical Optane (7.57 µs/read floor), 16.3 h unattended saturation with zero leaks (the honest-MISS finale's infrastructure half), receipts end to end. NIGHTSHIFT adds three things, none of them new physics:

1. **Episode persistence.** The Ring-2 store + router sidecar + a manifest (artifact sha, geometry, block receipts) become a named *episode* file set on E:/F: that survives sessions. Exec's recall router pulls from a reloaded episode exactly as it pulls from a live one — the recall machinery is already store-agnostic (RAM mock / Optane / QUIC peer, all proven).
2. **The consolidation pass.** Offline (idle-time, manifesto trick #7), Memo walks the episode non-causally: select/merge/evict in v0 (heuristics), span-compression via the P2.b adapter in v1 — proposals to a shadow episode, **promote-on-accept** (PPL/recall delta on probe queries), rewind on reject, every promotion receipt-logged. **The association-strength signal already exists:** the LRU temporal-locality telemetry (measured 67% hit-rates, absorption-vs-depth curves) is a live record of which blocks attention keeps returning to — "strengthen frequent associations, cull dead ones" is driven by data we already collect, not by a new estimator.
3. **Operational discipline inherited:** NIGHTSHIFT runs are schtasks-owned (the C2.4 lesson — bakes belong to the OS, not the agent tree); the runner banner echoes `getenv` (the config-regression lesson); no agent poll-watching.

Honest constraint carried forward: the NIAH budget ladder broke at 16×–32× selection (4k miss-by-a-digit, 16k clean miss) — **v0 NIGHTSHIFT bounds episodes ≤8k tokens** or runs two-stage re-rank; B∝N scaling is an open item on the risk register, not a buried assumption.

## 8. Endgame risk register (kept current; each item has an owner-gate)

| Risk | Status | Where it's held |
|---|---|---|
| Dragon-stall cause unknown (PLE theory falsified — PL=0 on the 12B) | OPEN; two hypotheses (context contradiction / baseline-attractor amplification) | P2 contract correction; P2.b G-P2b-4 stall-rate gate |
| Inter-token manifold is thin (α-blend degeneration) | MEASURED | P2.b Phase-0 arm A/B (soft-min penalty vs convex-hull parameterization) |
| Cloud-bf16 ↔ local-B1-quantized behavior gap | NAMED GATE | P2.b G-P2b-3 (on-silicon parity through the P2.a harness) |
| Recall budget scaling B∝N (16×+ selection breaks) | OPEN (C2.4 ladder) | NIGHTSHIFT v0 episode bound ≤8k; two-stage re-rank as the design fallback |
| gemma4 tokenizer dispatch (#115) blocks 12B text-in (daemon/interactive Exec) | SPEC'D, unbuilt | SPEC-gemma4-tokenizer-dispatch; required before any interactive XBAR demo (fixtures carry everything until then) |
| Semantically-wrong-but-valid blocks undetectable by the substrate | DOCTRINE (§4) | the coherence gate is load-bearing on every promotion, forever |
| Ring 3 consolidation is IRREVERSIBLE (raw source evicted) — a bad gist can't be rewound | DESIGN (§3.1) | G-R3-LOSS runs BEFORE eviction; loss bounded + fact-survival probe; un-compressible episodes stay verbatim in Ring 2 (valid outcome) |
| Dual-store recall doubles routing scan + adds a second fetch | DESIGN (§3.1) | G-R3-DUALROUTE: empty-Ring3 parity null + measured cost; reuse C2.2 split-device `read_batch2` overlap |
| Host memory wedge after big bakes (32 GB box, driver-pinned pages) | KNOWN | budget a reboot into post-bake plans; stream big models per-layer |

## 6. Fit to the lattice

The opening doctrine: floating-point drift and unprovable identity are entropy bleeding into the hardware; the lattice makes correctness a property you *prove*. The paper series extended that from kernels to artifacts (the supply chain is part of the math). XBAR extends it one more level: **to cognition between models.** Inter-model memory becomes a thing with receipts — proposed, gated, promoted or rewound, bit-auditable end to end. A synthetic subconscious whose dreams are auditable.

*The unflattering numbers, when they arrive, stay attached on purpose.*
