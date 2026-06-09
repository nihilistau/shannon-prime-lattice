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

**BACKLOG — Ring-3 provenance tag (the "encoding gap", banked from Ye 2606.05605, §6.1).** A consolidated Ring-3 gist is the model's *own* compressed memory, but Exec reads it as if it were raw context — the "encoding gap" (it does not know it is reading a memory). Solution, in the Shannon-Prime idiom — NOT a learned fp32 bias vector (that injects un-auditable continuous state, the exact failure mode the §6.2 doctrine forbids): a **discrete CRT/sentinel provenance lane** — a residue tag (design-rule §3-5: one CRT prime per lane) + the Spinor `0xA5` sentinel marking a block as "Ring-3 consolidated, not Ring-2 verbatim", recoverable and receipt-backed. Gate **G-R3-PROV (deferred, builds on R3):** an *agency-gain-style* test — Exec's held-out PPL on a continuation that depends on the gist, *with* the provenance tag vs *without* it; promote the tag only if `Δppl < 0` (the model uses the provenance signal). Strictly an enhancer (Ye's own ablation ranks proprioception secondary), so this is a post-R3 refinement, never bundled into P2.b's first training run.

## 3.2 Audio (M1) — the synthesis/output path (design note + verified constraints, 2026-06-09)

§3 already holds M1's **input** side: an audio encoder adapter-aligned to Exec's residual geometry deposits pseudo-token state into the ring (the `SP_XBAR_EMB` injection interface, P2.a, already built). This note scopes the **output** side (text/latent → speech) that an operator proposal raised, and records what's decided vs deferred. **Status: design exploration, NOT a committed build. No ledger row (the ledger is for green-gate results; this is a plan).**

**Direction adopted:** non-autoregressive vocoding with FiLM conditioning. AR token-by-token synthesis is O(N·D) in frames×codebook-depth; a parallel CNN vocoder is O(1) per chunk — the correct latency lever. FiLM (`γ(s)·x + β(s)`) is element-wise scale/shift, so it quantizes to fixed-point cleanly and avoids attention's dynamic-range pain — the one part of the proposal that is both correct and SP-native.

**Verified constraint — the GNA is dead for new work (do not target it).** OpenVINO discontinued the Intel GNA plugin at 2024.0 (deprecation announced 2023.1); using it requires pinning to the frozen 2023.3 LTS, and Intel redirects developers to the NPU (Core Ultra / 14th-gen+). The Beast Canyon host (11th-gen i9-11900KB) has GNA 2.0 silicon but **no NPU**. Independently, GNA is a sub-1-GOPS KWS/noise-suppression part that could never hold a HiFi-GAN-class vocoder regardless of tooling. **Decision:** always-listening VAD + mel front-end runs on plain CPU (trivial) or the 2060; the vocoder runs on the 2060 / AVX. No dead silicon in the design.

**Three honest corrections to the proposal (kept on record):**
1. **It is not "minimalist / steal one insight" — it is the full modern non-AR TTS stack:** ECAPA-class speaker encoder + FastSpeech2-style frame/variance (pitch/energy) predictors + HiFi-GAN/Vocos FiLM vocoder. Every component is a *trained* net; a GAN/diffusion vocoder is among the harder things to train stably. Scoped honestly, this is a larger program than all of XBAR to date.
2. **Category gap — semantic ≠ acoustic.** P2.b's k pseudo-tokens are proven *semantic text-recall keys*, not acoustic frames. "Exec emits an acoustic residue lane → frame predictor" hand-waves the actual hard problem (semantic → mel), which *is* TTS. The P2.b recall win does NOT transfer to acoustic conditioning for free.
3. **Adopt, don't invent — and we already have an adopted vocoder.** A real audio lane exists in the `voxtral-tts.c` satellite repo: Voxtral-4B's **300M CONV codec decoder** (4-stage upsample + ALiBi transformer) consuming LLM latents, with our **VHT2** spectral latent compression already integrated. So this is not greenfield — it is "**replace the adopted Voxtral codec with a custom non-AR FiLM vocoder**," which *raises* the bar: the custom build must beat a working baseline, not merely clone a voice. The lattice's durable contribution to audio is the **inference substrate** — `SP_XBAR_EMB` residual injection (conditioning), fixed-point/Z_q vocoder inference (the OK_Q4B/codec work, where SP quantization earns its keep and serves the Rust/no-Python goal), and eventually CRT multi-island synthesis (manifesto #1/#9) — NOT a novel TTS architecture. If we go custom, adopt a proven non-AR design; make the *inference* ours.

**Sequencing:** M1 stays downstream of the live critical path (P2.b capacity → P3 ring-on-gemma4 → C2 curator). A from-scratch TTS build now is the largest drift risk on the board — it does not exercise the lattice thesis (Z_q / Spinor / CRT / recall). Deferred behind the core.

**Falsifiable FIRST step (cheap existence probe before any Rust or training, the P2.b-Phase-0 pattern):** wire **off-the-shelf pretrained** components — Vocos/HiFi-GAN vocoder + pretrained ECAPA speaker encoder + an existing non-AR acoustic model — add FiLM conditioning, and test the single load-bearing claim: *can it clone a voice from a 3 s reference at acceptable similarity AND O(1)-per-chunk latency on the 2060?* PASS → the custom fixed-point Rust reimplementation is justified. FAIL → a day spent, not a quarter, and the architecture falsified before silicon-shaped code was built around it. **Baseline it against the existing Voxtral 300M codec** — the custom FiLM path only earns the build if it beats Voxtral on latency/footprint at equal clone quality. Gate **G-M1-CLONE (deferred):** reference-clone similarity above a pinned floor + per-chunk latency independent of sequence length, *vs the Voxtral-codec baseline*.

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
| M1 | XBAR-M | Audio lane — **input:** encoder latents → `SP_XBAR_EMB` residual injection → ring (P2.b recipe, source swap), CRT prime lane; **output (§3.2):** adopt a proven non-AR FiLM vocoder, make the *fixed-point inference* ours (NOT a novel TTS arch); GNA is dead-target (verified) → CPU/2060 only | input: Exec answers questions about injected audio never seen as text · output: **G-M1-CLONE** (off-the-shelf existence probe FIRST — 3 s ref clone similarity + O(1)/chunk latency on 2060) | pending P2.b; output deferred behind core, probe-first |
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
| No PERMISSIONS model on Ring 2/3 writes (gap named via §6.1 taxonomy audit) | OPEN/BACKLOG | who/what may propose+promote to the canonical/consolidated rings — access control is unspecified; fine while Memo is the sole writer, must be specified before multi-writer / networked curators |

## 6. Fit to the lattice

The opening doctrine: floating-point drift and unprovable identity are entropy bleeding into the hardware; the lattice makes correctness a property you *prove*. The paper series extended that from kernels to artifacts (the supply chain is part of the math). XBAR extends it one more level: **to cognition between models.** Inter-model memory becomes a thing with receipts — proposed, gated, promoted or rewound, bit-auditable end to end. A synthetic subconscious whose dreams are auditable.

## 6.1 Convergent external work (verified, 2026-06-09 — abstracts fetched, not trusted second-hand)

Two recent preprints independently arrive at the systems doctrine XBAR was built on. Cited as *convergence/validation*, not as frameworks XBAR implements — and one yields a usable methodology with a Shannon-Prime sharpening.

**AI Harness Engineering** (Zhong & Zhu, arXiv:2605.13357, 13 May 2026). Argues capability emerges from the *model–harness–environment system*, not the model alone; names 11 runtime responsibilities and a trace protocol producing an **"auditable episode package."** That is, in their vocabulary, exactly what XBAR builds at the *latent* level (they audit text-level SWE-agent runs; XBAR audits inter-model cognition — a level deeper). Mapping XBAR against their 11-item taxonomy is a genuine gap audit:

| their responsibility | XBAR analogue | status |
|---|---|---|
| context selection | ±1 Rademacher recall router (Ring 2/3) | covered |
| project memory | Ring 2 (episodic) + Ring 3 (consolidated) | covered |
| task state | `sp_session_clone`/`rewind` | covered |
| observability | `receipts.log` + getenv-echo banners | covered |
| failure attribution | the bisection-forensics doctrine (e.g. the L11 kill) | covered |
| verification | every gate (G-R3-LOSS, MTP accept, PPL gates) | covered |
| entropy auditing | Frobenius-lift bit-identity + Spinor 0xA5 sentinel | covered |
| intervention recording | per-promote/rewind receipt | covered |
| **permissions** | — | **GAP**: no access-control model on who/what may write Ring 2/3. Backlog item, surfaced honestly. |
| task specification | the per-stage contracts (out-of-band) | N/A (infra, not an agent task layer) |
| tool access | — | N/A |

So XBAR covers ~8/11 natively; "permissions" is a real, newly-named gap (banked above), and two are out of scope (XBAR is memory substrate, not an agent task framework).

**Retrospective Harness Optimization** (Pan et al., arXiv:2606.05922, 4 Jun 2026; code github.com/wbopan/retro-harness). Self-supervised improvement from **unlabeled past trajectories** — coreset of hard cases, parallel re-solve, candidate updates scored by the agent's **pairwise self-preference** (SWE-Bench Pro 59→78%, no external grader). This is the right *shape* for NIGHTSHIFT's curator-learning: Memo generates parallel n→k compression candidates over a past episode (the rollouts), and the best is kept. **Shannon-Prime sharpening (ours, claimed as an improvement, not an adoption):** RHO's self-preference is a *gameable* LLM preference judgment (self-preference bias, reward-hacking). XBAR replaces it with a **measured PPL-delta on a held-out continuation** (G-R3-LOSS) — a number with a receipt, not a preference. Same label-free trajectory-derived loop; an ungameable scorer. The exact-citation honesty: we adopt RHO's *pattern*, not its algorithm; we do not "implement RHO," and these are unrefereed preprints.

**From Prediction to Self** (Ye, arXiv:2606.05605, 4 Jun 2026; verified — abstract + body read, not taken from a summary). A minimal 192-dim GRU on sinusoidal/Lorenz signals; 40 ablations trace four ordered "developmental conditions" for self-world decomposition: (1) persistent state forming stable attractors, (2) a causal action loop, (3) proprioceptive feedback (an explicit action-trace *input channel* making implicit causal knowledge explicit), (4) **asynchronous awakening — perception must consolidate before action learning begins** — with a metric **agency gain** `A = Err_world − Err_self`, and the finding that **only forward-sampled action selection yields agency gain (gradient alternatives degenerate)**. Cited as **convergent validation, toy-model caveats stated**: it is a recurrent net on continuous noise, architecturally incompatible with our discrete attention substrate — we map *concepts*, never the GRU/EMA-trace code. Two of our existing choices are independently re-derived: condition (4) ≈ our **frozen-Exec + Memo-trained-on-top** ordering (perception consolidated before the curator acts); forward-sampled-over-gradient ≈ our §3c choice to select P2.b by **forward recall-rollout** (and the RHO forward-sampling pattern). **Two honest non-adoptions on the record:** (a) its "stable attractor" is the GRU hidden-state *dynamics* (PCA of `h_multi` recovering after perturbation), NOT our embedding-space *geometry* — equating attractor-stability with on-manifold injection (to "vindicate Arm H") is a category error; our local recall decider (n=6) **favors Arm F** (off-manifold robustly preserves span recall, 6/6 vs the noise null) with the manifold penalty kept an empirical dial — Arm H is not catastrophic (the n=1 "H recall-hostile" read was an outlier, retracted), and this paper does not bear on the F/H choice either way. (b) "proprioceptive feedback" as a *learned fp32 bias* would violate the auditable-state doctrine; the Shannon-Prime form is a **discrete CRT/sentinel provenance lane** (§3.1 backlog), and the paper itself ranks proprioception a secondary *enhancer* (agency gain survives its ablation, Table 4).

## 6.2 Threat-landscape note — why a provable latent substrate matters beyond correctness (KnackAU observation, 2026-06-09)

A forward-looking concern, recorded because the XBAR experiments make it concrete. **Deployed AI safety lives at the lexical layer; cognition happens in latent space.** RLHF refusals, input filters, output classifiers — almost the entire shipped safety stack scans *text*. But the decision is made in the residual stream. So the security question for any architecture is: *how many pathways reach latent space without passing the layer where safety is enforced?* Each is a gap, and the field's trajectory **adds** them:

- **Multimodal inputs** — an image/audio clip becomes latent vectors through a projector the text-safety training never saw (the demonstrated adversarial-image-jailbreak surface: Carlini; Bagdasaryan et al.).
- **Agentic / tool / retrieved context** — RAG docs, tool outputs, other agents' text get embedded into context without re-passing a safety filter (the bigger near-term surface — needs no special access).
- **Shared / multi-tenant KV-cache serving** — prefix-cache and shared-state optimizations are exactly where one request's latent state can bleed into another's under imperfect isolation.

The "newer architectures, bigger concern" intuition holds: unified, end-to-end, more-modalities, more-shared-state all move more cognition-bearing signal past the text checkpoint. Native-multimodal models that eliminate a separable encoder stage are the ones with *no obvious chokepoint to monitor at all*. **Calibration (concern, not panic):** direct latent writes need runtime ownership — a deployment-isolation threat, not a remote skeleton key; adversarial-input attacks need optimization access and are partially defendable. The structural worry is the *widening gap* between where safety is enforced (text) and where reasoning happens (latent), on a multi-year horizon — not an imminent break.

**Where this connects to the lattice (the part that is a contribution, not a worry).** The reason the defensive side has no good latent-layer answer is that latent state has been an un-inspectable continuous blob. XBAR's whole premise is the counter: a **discrete substrate where a block of internal state is provably well-formed (sentinel + Frobenius-lift identity), every write to memory carries a receipt, and nothing commits without passing a coherence gate** (the shadow-ring promote-on-accept). "Verifiable, gated latent state" is a research direction the defensive field genuinely lacks — and XBAR-M (the modality lane) is where it becomes a concrete defense: an incoming modality projection is a *proposal to Ring 2′*, sanitized through the same coherence/consistency gate as any Memo proposal, before it may write the canonical ring. We did not build XBAR as a security tool; but a substrate that makes latent cognition auditable is, incidentally, a small proof that the latent layer **does not have to be** the unmonitored canvas the threat model assumes. Recorded as motivation, not as a project pivot.

*The unflattering numbers, when they arrive, stay attached on purpose.*
