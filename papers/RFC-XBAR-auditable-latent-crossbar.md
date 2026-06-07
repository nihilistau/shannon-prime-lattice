# RFC-XBAR — The Auditable Latent Crossbar (Exec + Memo sharing Ring 2)

**Status:** DRAFT v0 (brainstorm formalized 2026-06-07, KnackAU + Gemini + Claude).
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
        │   ┌─ Ring 1 ─┐  ┌── Ring 2 (canonical) ──┐  ┌─ Ring 2′ (shadow) ─┐       │
        │   │ working  │  │ Spinor blocks, 0xA5,   │◄─│ Memo's proposals   │       │
        │   │ KV       │  │ receipt per block      │  │ promote-on-accept  │       │
        │   └──────────┘  └────────────────────────┘  └────────────────────┘       │
        │                          ▲                                               │
        │              modality lanes (CRT prime per modality):                    │
        │              audio adapter (voxtral), video, ...                         │
        └──────────────────────────────────────────────────────────────────────────┘
   Gate on every promotion: coherence/PPL delta on post-injection window → accept or REWIND.
```

Design rules (settled in the 2026-06-07 brainstorm):

1. **Memo is small.** It sorts latents, it does not speak. A few layers / low-rank operator / 0.5B-class body co-resides permanently with Exec inside 12 GB — no weight-swap latency. (Two 12Bs on a 2060 is a non-starter; it's also unnecessary.)
2. **"Backwards" = non-causal.** Exec is causal (past→future). Memo runs bidirectionally over the whole stored episode and rewrites it globally. That is the architectural form of consolidation ("sleep/replay"), not a vague autoencoder.
3. **Shadow ring, promote-on-accept.** Memo never writes the canonical Ring 2 directly. Proposals land in Ring 2′; a cheap downstream coherence gate (PPL delta over the post-injection window) accepts → promote with receipt, or rejects → rewind. The canonical episode stays clean and every promotion is auditable.
4. **Geometry is the law.** A ring entry is a per-layer, per-head (K,V) at a position — roped, normed, V-less where the architecture says so (gemma4 globals: V = raw K projection, weightless-RMS-normed, never roped). Nothing enters the ring that does not honor the coordinates. XBAR-P1 exists to *measure* how strict this law is.
5. **One CRT prime per modality lane.** Audio/text/video blocks are residue-separable in the same unified ring; Exec attends to one memory, provenance stays recoverable, lanes can never alias. (Manifesto tricks #4 + #9, applied to modality instead of hardware channel.)

## 4. The honest negative (stated up front)

"Injected memory as sudden realization" and "confident hallucination from off-manifold state" are the **same event** described twice. The discrete substrate detects *invalid* blocks (sentinel, lift identity); it cannot detect *semantically-wrong-but-valid* ones. Therefore the coherence gate is load-bearing, not decorative: no promotion without a measured downstream delta, accept-or-rewind, every time. This is the kernel-gating doctrine pointed at inter-model state.

Second honest negative: RoPE phase ties keys to absolute position; SWA layers fade injected state beyond their window (the GLOBAL period-6 layers are the long-range carrier); partial-rotary-0.25 globals are the most transplant-tolerant. The probe must quantify all three, not assume them.

## 5. Roadmap (lanes and order)

| Stage | Lane | What | Gate / exit | Status |
|---|---|---|---|---|
| **P1** | XBAR-P | **Inception Probe** — A/B latent injection on gemma-4-12B CUDA path: Arm A real-KV transplant vs Arm B raw-residual overwrite, with self-transplant null control and snapshot/restore rewind | see `CONTRACT-XBAR-P1-inception-probe.md` (G0–G4) | **SPEC'D** |
| P2 | XBAR-P | Pseudo-token injection — inject at the *residual entry* (embedding-level), let the real forward mint the KV; this is the mechanism a trained adapter would actually use | concept resonance ≥ Arm A's within measured tolerance | pending P1 |
| P3 | XBAR-P | Ring wiring on the Exec path — bring two-ring (today: qwen3 CPU math-core) to the gemma4 CUDA decode loop; KV slots become Spinor-block ring entries with receipts | T_ARM gates green on gemma4-CUDA; bit-exact null path | pending |
| C1 | XBAR-C | Memo v0 = handwritten curator — no training; CUDA/C heuristics (select/merge/evict blocks) driving the full propose→gate→promote/rewind loop on Ring 2′ | loop closes; ≥1 promotion improves post-window PPL vs no-curation baseline | pending P1/P3 |
| C2 | XBAR-C | Memo v1 = learned curator — small model trained self-supervised: **fixed ring budget, maximize Exec's recall over the episode** (QA-over-episode / reconstruction, supervised by Exec's own behavior; no text labels) | recall@budget beats Memo v0 heuristics on held-out episodes | pending C1 |
| M1 | XBAR-M | Audio lane — voxtral encoder + learned projection adapter into Exec's residual geometry; deposit as pseudo-tokens on a dedicated CRT prime lane | Exec answers questions about injected audio it never saw as text | pending P2 |
| N1 | XBAR-N | **NIGHTSHIFT** — consolidation as idle-time PoUW (manifesto trick #7): Memo replays and compacts the day's ring while the operator is away; every promotion receipt-logged | unattended run produces net-positive gated promotions, zero canonical corruption | pending C1 |

Order discipline: **P1 before any training.** You cannot optimize a loss toward a target whose physics is unproven; P1's Arm-A/Arm-B delta *is* the spec the curator trains against.

## 6. Fit to the lattice

The opening doctrine: floating-point drift and unprovable identity are entropy bleeding into the hardware; the lattice makes correctness a property you *prove*. The paper series extended that from kernels to artifacts (the supply chain is part of the math). XBAR extends it one more level: **to cognition between models.** Inter-model memory becomes a thing with receipts — proposed, gated, promoted or rewound, bit-auditable end to end. A synthetic subconscious whose dreams are auditable.

*The unflattering numbers, when they arrive, stay attached on purpose.*
