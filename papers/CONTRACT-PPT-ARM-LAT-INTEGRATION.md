---
type: contract
title: CONTRACT-PPT-ARM-LAT-INTEGRATION — assembling XBAR · NIGHTSHIFT · KAIROS into one organism
description: The unifying contract that anchors the episodic crossbar (XBAR), live conversational memory (NIGHTSHIFT), and the temporal/agency engine (KAIROS) onto the PPT-ARM-LAT substrate as one pipeline — with an honest Built/Theory/Refuted map, the open-set router question answered (causal, not geometric), the W_c head demoted to a pre-sort, the bounded-N causal oracle enshrined as Stage-2 ARM, and the T4 weight-quant pass formally retired.
tags: [integration, ppt-arm-lat, xbar, nightshift, kairos, ring2, spinor, ablation-oracle, bounded-n]
timestamp: 2026-06-20
resource: papers/CONTRACT-PPT-ARM-LAT-INTEGRATION.md
sp_status: DESIGN
sp_gate: G-INT-1 (HOT persistence: f32 payload byte-identical + C2 sig Hamming 0) · G-INT-2 (bounded-N causal recall) — REFUTED on metal (oracle is query-independent admission gate, not a recall selector; engine 9e12225) · G-INT-3 (KAIROS ring governance) — all pre-registered below, default-off = null floor
sp_commit: (none yet — this is the pre-registration)
sp_repro: §6 per-gate commands
---

# CONTRACT-PPT-ARM-LAT-INTEGRATION

## §0 — The mandate (why this exists)

The components of the Shannon-Prime organism are GREEN **in isolation** but were never assembled into the one pipeline the PPT-ARM-LAT thesis describes. We scoped locally and mistook a beautiful blueprint for a built building. This contract is the audit-of-map-against-territory and the assembly plan, written **before** a line of C/Rust, encoding the empirical verdict the recall campaign just earned: **relevance is a causal/generative property, not a similarity-geometric one** — therefore the open-set router is a *bounded working set + a causal gate*, not a learned projection.

Substrate (unchanged, frozen): a discrete lattice over `O_K = Z[ω]`, `ω²=ω−41` (the ring of integers of `Q(√−163)`), computed in the dual-prime negacyclic ring `R_q = Z_q[x]/(x^N+1)`, `q1=1073738753`, `q2=1073732609`, `M≈2^60`.

## §1 — The honest map: BUILT / THEORY-ONLY / REFUTED

The discipline of this document is the third column. Nothing is integrated until it is BUILT-and-wired; theory-mapped is not built; refuted is kept attached.

| Layer / role | Component | Status | Receipt (verify) |
|---|---|---|---|
| Substrate `O_K` / dual-prime NTT | `core/ntt_crt`, `core/poly_ring`, `core/ok_arith` | **BUILT** | reduction-order-immune, bit-exact; lattice STATE §`(1)–(3)` |
| Byte-exact forward (exact-integer 12B) | `core/exact_islands` + `SP_BYTEEXACT` | **BUILT** | `G-BYTEEXACT-FORWARD-12B` GREEN, PPL 4.6665 byte-identical, engine `69c0588` |
| 63-byte Spinor memory atom | `core/vht2` (block + `0xA5` sentinel @ byte 63) | **BUILT (math-core); NOT wired to NIGHTSHIFT** | frozen VHT2; daemon writes `ep.k`/`ep.v` files + in-mem `Vec`, NOT spinor blocks |
| Ring-2 persistent tier (Optane) | C2.1 `ReadFile` backend (`FILE_FLAG_NO_BUFFERING`+IOCP) | **BUILT (backend); NOT carrying live episodes** | C2.1 Ring-2 recall gates; live NIGHTSHIFT episodes never reach it |
| Frobenius integer episode store (Theorem-T4 storage form) | `core/frobenius`, `tools/curator/frob_episode.py` | **BUILT (host); NOT in live daemon** | `G-R2-FROB` GREEN, engine `dbe4103`/`d076797` |
| KAIROS resident daemon — O(1) cold-evict / rewind | `tools/sp_daemon/src/kairos*.rs`, SWA-ring journal | **BUILT** | `G-1b-REWIND-NULL`, `G-1b-WRAP-NULL`, `G-KAIROS-1` soak |
| KAIROS — Poncelet-orbit `nδ≡0` phase tracker | (PPT-ARM-Theory Part I) | **THEORY-ONLY** | live KAIROS = salience/event-tape policy; no orbit computation in the loop |
| NIGHTSHIFT batched capture (byte-exact provenance) | `routes.rs` B4 + `kv::capture_batched` → `gemma4_decode_cuda` | **BUILT** | live ep == curated ep **9.858 == 9.858** (BOS+`\n`); engine `3ccba61` |
| ARM routing — learned `W_c` (E+1) head | `recall.rs` `wc_score`, `routes.rs` `SP_B3_WC` | **BUILT but REFUTED as open-set router** | closed-set: 360/361 trained (`G-CHAT-B3-WC-DIV2`) but **chance/plateau unseen** (below) |
| ARM open-set router — learned dual-encoder | r∈{32,128,256,512}+MLP, raw/cosine q·K | **REFUTED (3 ways)** | raw q·K recall@20 = **23% = chance**; capacity **plateau ~50%**; scale 90→300 **worse**. `G-CHAT-B4-{HOLDOUT,CAPACITY,SCALE}` |
| Relevance gate — teacher-forced causal ablation | `SP_B3_DISPOSER` + `SP_B3_SECRET` (offline labeler) | **BUILT (offline); the ONLY open-set-correct signal** | novel −33.56 vs parametric −0.15, TAU=−8.0; `G-CHAT-B3-NEEDLE-v13-MATRIX`, engine `b6470cc` |
| Ring-3 neocortical VSA superposition | `core/ring3`, native `sp_pr_mul` bind | **BUILT (host loop); NOT live-consolidating** | `G-R3-BIND-on-O_K` 256/256, `G-XBAR-ORGANISM-FULL` `15e7051` |
| KSTE / Friedman sieve / dominance gate | `core/kste`, `core/sieve`, `core/dominance` | **BUILT (math-core); NOT in live recall path** | grep: only `sieve_capacity:0` placeholders in daemon |

**Reading of the map:** the organism's *organs* are alive; its *circulatory system* is not connected. Three big islands — (a) NIGHTSHIFT capture, (b) the spinor/Optane Ring-2 substrate, (c) the causal relevance gate — are each GREEN and mutually disjoint in the live daemon.

## §2 — The corrected unified ARM (the architecture this session earned)

The open-set router question is **answered**, not assumed. The static-K geometry carries no transferable relevance (untrained = chance; trained dual-encoder plateaus ~50% recall@20, overfits with capacity, degrades with scale). The only thing that generalizes is the **causal** gate (delete the memory, watch the structure collapse). Therefore:

```
turn ─► KAIROS (salience / recency) ─────────► bounds the working set  N ≤ W (Ring-1, flat-VRAM SWA)
   └─► NIGHTSHIFT batched capture (byte-exact, BOS+\n) ─► K/V tensors
          └─► RING-2 record = { LOSSLESS f32 K/V payload (byte-exact provenance) + EXACT 256-bit C2 sig index } ;  spinor = COLD archive tier only (G-INT-3)
   query ─► STAGE-1 PRE-SORT: C2-sig Hamming popcount over Ring-2  (pure integer, sub-µs, recall@K only)
              └─► STAGE-2 GATE: teacher-forced CAUSAL ABLATION over the bounded survivors
                    ΔLL < τ=−8  ⇒  ACCEPT (inject) ;  else  ⇒  (E+1) NULL
   consolidation ─► KAIROS phase ─► Ring-3 VSA superposition (native O_K bind)
```

**Two doctrines this fixes in stone:**
- **The `W_c` head is DEMOTED and SUBORDINATE — NOT co-equal with the LSH sig.** Stage-1 PRIMARY is the C2 LSH Hamming popcount: a pure discrete integer-ring operation, zero float compute — the hardware ideal. The `W_c` head is a **secondary pre-sort tie-breaker, invoked iff the LSH cull returns a candidate pool larger than the KAIROS latency budget `W` can afford** — it only trims an over-full pool; with a bounded pool it is not invoked at all. It is never load-bearing and never the gate; its closed-set 360/361 is a memorization-prone heuristic prior, not a verdict.
- **The bounded-N causal ablation oracle is ENSHRINED as the Stage-2 ARM.** It is the absolute gatekeeper. It is affordable because — and only because — N is bounded by KAIROS to the conversational horizon (`W≈20`), not RAG-scale. This is the reframe that makes the pipeline mathematically close: O(N) causal verification over a bounded set, no learned surrogate, no second model, no VRAM/latency wall.
- **The Ring-2 record is TWO-TIER — search decoupled from payload (the G-INT-1 grounding, operator-ratified).** **PAYLOAD (hot/recall) = lossless f32 K/V** — preserves the byte-exact provenance the causal oracle's determinism requires; a 0.7% spinor int8 perturbation of the load-bearing columns would contaminate the ablation ΔLL, so the physics forbids lossy compression on the hot path. **INDEX (routing) = the exact 256-bit C2 sig captured at ingest** (stored, NEVER recomputed from lossy data — a recompute flips razor-thin near-zero sign bits, measured 1/256, bit #229 at projection-mean −3.32e-5). **ARCHIVE (cold/eviction, N≫W) = the 63-byte spinor blocks** (3.25× shrink, near-lossless relL2 7.2e-3, storage byte-exact — proven in the G-INT-1 survey), **physically quarantined from the hot recall loop**; they belong to KAIROS eviction (G-INT-3), never the active path.

> **⚠ §2 KEYSTONE REFUTED ON THE METAL (G-INT-2 Step 3, engine `9e12225`, receipt `G-INT-2.log`).** The enshrinement of the bounded-N causal ablation oracle as the live **query-conditioned Stage-2 ARM is FALSIFIED.** Live result over the bounded curated working set: **novel-recall 0/10, foreign-reject 0/10** — every query (matched AND foreign) ACCEPTed the SAME globally-steepest-self-collapse episode (ep_n_div_034, ΔLL −49 even for "capital of France?"). ROOT CAUSE: the teacher-forced ablation is a **query-INDEPENDENT self-dependency oracle** — each candidate teacher-forces its OWN secret + ablates its OWN rows, so every novel needle self-collapses regardless of the query; `argmin ΔLL` carries no query signal. The clean diagonal (B3-v13, −33.56) needed the **answer key** to teacher-force — available OFFLINE, NOT live (the answer is what recall seeks; teacher-forcing it is circular). The only key-free query-conditioned variant (multi-token Δ-continuation) reached 2/3 but FAILED the absolute open-world gate (foreign false-fires). **CORRECTED DOCTRINE:** the causal ablation oracle is a query-INDEPENDENT **ADMISSION gate** ("is this a real non-parametric memory?") — its proven, durable role as the corpus labeler — NOT a recall selector. The live query-conditioned recall selector remains the W_c head (closed-set, ~50% recall@20 unseen). **Open-set autonomous recall of a NOVEL live fact has NO clean mechanism — refuted from every side: similarity=chance/closed-set, causal-self=query-independent, causal-Δcont=fails-absolute-gate, causal-answer-key=not-live.** This is the campaign's deepest boundary-thesis terminus.

## §3 — Officially RETIRED: T4 Frobenius weight-quantization pass

`T4-WEIGHT-QUANT` (per-row Frobenius `π^k` sensitivity pass on the 9.4 GB weights) is **RETIRED as convicted-redundant.** Receipts:
- Weight compression frontier is **closed**: `OK_Q4B` is gold at PPL **4.6665**; the only lever is bit-width; entropy-coding the codes is dead (`G-R2-FROB-ENTROPY` 1.02×, engine `e6d17bb`).
- The exact-arithmetic Frobenius thesis is **already realized on the 12B** by the byte-exact forward (`G-BYTEEXACT`, 4.6665, run-to-run bit-identical).
- The validated T4 (`G-R2-FROB`) is the **episode store**, not the weights; `T2`-Möbius-on-weights was refuted (`G-T2-WEIGHTS`, recon cos 0.032 ≈ random, engine `ac76c8e`).
A weight-Frobenius pass buys neither new compression nor a new arithmetic property. It is an artifact of an older roadmap, convicted by newer receipts. Do not run it.

## §4 — Pre-registered integration gates (falsifiable; default-off = null floor)

Each is additive and env-gated; with the flag unset, the live B-stack chat is **byte-identical** (the project's null-floor law).

- **G-INT-1 — HOT persistence (the first wire; spinor archive deferred to G-INT-3).** A NIGHTSHIFT-captured episode's **lossless f32 K/V** plus its **exact 256-bit C2 sig** (computed once at ingest from full-precision K) are written to the Ring-2 backend (`sp_arm_ring2_backend` — Optane NO_BUFFERING+IOCP store / stdio reference twin) and reloaded. PASS iff: **(a) PAYLOAD 100% byte-identical** — the f32 K/V read back == written (memcmp == 0 over the whole episode); **(b) C2 sig Hamming == 0** — the stored exact sig round-trips identically (and, f32 being lossless, a recompute from the round-tripped K also matches at 0). Default-off (no `SP_RING2`) = the current `ep.k` f32-file path, byte-identical null floor.
- **G-INT-2 — Bounded-N causal recall as Stage-2 ARM. [REFUTED — engine `9e12225`; see §2 keystone-refuted block. The causal oracle is query-INDEPENDENT (admission gate), not a live recall selector; novel 0/10, foreign 0/10.]** On the served 12B chat, with KAIROS bounding the working set to `W` live episodes: Stage-1 = C2-sig Hamming cull (+ optional `W_c` pre-sort) → ≤K survivors; Stage-2 = teacher-forced ablation over the survivors; ACCEPT iff ΔLL<τ=−8 else NULL. PASS iff: a matched **novel** stated fact ACCEPTs and is recalled, AND a foreign query → NULL → clean answer, on a held-out live set of ≥10 novel facts + ≥10 foreigns, with the `W_c` head used ONLY as pre-sort. Pre-registered thresholds: **novel-recall ≥ 80%** (honest: the Stage-1 cull leaks, so end-to-end recall is capped — a librarian may fail to find a book), **foreign-reject = 100%** (NON-NEGOTIABLE: the Stage-2 ablation oracle is deterministic with ~220× ΔLL separation, so a false positive is physically precluded — a librarian must NEVER confidently hand the user a hallucinated book), per-turn added latency ≤ (K × single-candidate-ablation), K≤W. Default-off = current `SP_B3_WC` head path.
- **G-INT-3 — KAIROS ring governance.** KAIROS bounds N (salience/recency eviction into Ring-2), drives Ring-1→Ring-2 paging on overflow, and triggers the Ring-3 consolidation phase between turns; O(1) bit-exact rewind preserved across the flow. **G-INT-3 also owns the COLD ARCHIVE tier**: evicted episodes (N≫W) are compressed to 63-byte VHT2 spinor blocks (3.25× shrink, near-lossless relL2 7.2e-3, storage byte-exact per the G-INT-1 survey) in a Ring-2 cold region, quarantined from the hot f32 recall payload; re-promotion on recall re-materialises lossless-enough K for the cull, with the exact f32 re-fetched only when a candidate reaches the Stage-2 oracle. PASS iff: VRAM stays flat as live N grows (episodes page to Ring-2 spinor/Optane, not VRAM), AND a recalled paged episode is byte-identical to its pre-page form, AND G-INT-2 still holds after paging. Default-off = unbounded in-mem `Vec` (current).

## §5 — Execution sequence (locked order; one green tile at a time)

1. **G-INT-1 first** — NIGHTSHIFT → VHT2 spinor → Optane Ring-2 (C2-sig indexed). Connect the two biggest disjoint islands. This is the substrate everything else rides on.
2. **G-INT-2** — wire the bounded-N two-stage recall (C2/`W_c` pre-sort → causal ablation gate) as the live ARM, demoting `W_c`.
3. **G-INT-3** — KAIROS bounds N + pages Ring-1↔Ring-2 + fires Ring-3 consolidation; prove flat VRAM + byte-exact paged recall.
4. (Frontier, out of this contract) Ring-3 live consolidation semantics + the KSTE/Friedman-sieve eviction policy on Ring-2 — promote from math-core into the live path only with their own pre-registered gates.

## §6 — Honest scope + open frontiers

- This contract assembles **proven** islands; it introduces **no new math**. Every primitive is already GREEN (§1). The risk is plumbing + ABI seams, not theory.
- The bounded-N causal oracle's cost is real: a per-candidate teacher-forced forward is ≈1–2 s on the 12B, so `W` (the KAIROS horizon) is latency-bounded to ~10–20. This is a **feature** (conversational memory is bounded), not a bug — but it caps the design at session-scale memory, NOT RAG-scale (explicitly out of scope; that is a different product needing a cross-encoder / external retrieval).
- The Poncelet-orbit KAIROS framing stays THEORY until a gate operationalizes it; the live KAIROS is the salience/event-tape daemon, and this contract treats it as such.
- Repro commands per gate to be filled at build time; each gate carries its own `G-INT-*.log` receipt under `tests/fixtures/`.

**The container is indestructible; the organs are alive. This contract is the circulatory system.**
