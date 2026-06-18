---
type: contract
title: CONTRACT-XBAR-R3 — Ring-3 consolidation (the gist tier) — PRE-REGISTRATION
description: "Status: Path A CLOSED end-to-end + NATIVE-ENGINE PORT CLOSED (2026-06-18)."
tags: [contract, xbar]
timestamp: 2026-06-17T21:23:20Z
resource: shannon-prime-lattice/papers/CONTRACT-XBAR-R3-consolidation.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# CONTRACT-XBAR-R3 — Ring-3 consolidation (the gist tier) — PRE-REGISTRATION

**Status:** **Path A CLOSED end-to-end + NATIVE-ENGINE PORT CLOSED (2026-06-18).** R3.1 BIND → R3.2 LOSS → R3.3 DUALROUTE → R3.4 NIGHTSHIFT all GREEN (2026-06-17, host-numpy), and as of 2026-06-18 the deployment VSA bind/unbind is **re-carried onto the engine-native exact-integer dual-prime CRT-NTT** (`core/ntt_crt` + `core/poly_ring`, `sp_pr_mul` / `ntt_forward∘pointwise∘inverse`) — the `R3.x Z_q/NTT engine port` named below as deferred is now **DONE and removed from the deferred list** (run-records §5.1, G-R3-BIND-on-O_K + G-R3-ORGANISM-NATIVE). Path B (the learned adapter) remains deferred behind the operator's budget green. Parent: RFC-XBAR v1.4 §3.1 (the Ring-3 amendment, `G-R3-LOSS`), `DESIGN-VSA-ring3-holographic.md` (the parameter-free mechanism, now binding via native `sp_pr_mul`), `CONTRACT-XBAR-P2b-adapter.md` (the convicted learned path), `CONTRACT-XBAR-C2-memo-curator-loop.md` (the Ring-2 verbatim loop this sits above, now CLOSED incl. #222).

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

## 5.1 Run-records

**R3.1 — G-R3-BIND GREEN (2026-06-17, engine 23539b7; Path A, parameter-free, offline).** The VSA/HRR superposition math holds on the real Ring-2 episode tensors. `tools/ring3/g_r3_bind.py`: store `M = Σ_i (addr_i ⊛ id_i)` (circular convolution = the engine's NTT-over-Z_q algebra), `addr_i` = a carrier **seeded by episode i's real C2 256-bit signature** (content-derived from `ep.k` global keys, so a live cue regenerates it — ties Ring-3 to the proven C2 resolver), `id_i` = a clean ±1 label (the surfaced "episode signature", a pointer back to the Ring-2 verbatim episode for the exact #222 verify — never a reconstructed span, §1 trap stays shut). Recall: `id_est = M ⊛ addr_j†` → cleanup argmax over the id codebook.

| metric | result |
|---|---|
| **N=2 (ep_toy + ep_wiki, the operator's ask)** | recall@1 = 1.0; margins **+0.586 / +0.568** (correct id strictly above crosstalk), ±1 substrate carrier |
| capacity (±1 carrier, D=1024) | recall@5 ≥ 0.90 to **N=64**; graceful degrade past ~D (N=128 → 0.87, N=256 → 0.45) |
| substrate cost | ±1 Rademacher carrier tracks the ideal unitary carrier closely (recall curves ≈ identical) |

**Caught + fixed a metric bug, not a math failure:** the first cut defined `SNR = cos(correct)/max cos(wrong)`, which at N=2 divides by a ~0/negative wrong-id cosine (near-orthogonal random ids) → a sign-flipped artifact (`−91`) despite recall@1 being perfect. Replaced with the cleanup-standard **margin** (`correct − max wrong > 0`) + **z-score**; recall was always correct. Receipt `engine tests/fixtures/xbar_r3/G-R3-BIND.log`. Domain note: proved in the real domain via FFT circular conv (= the NTT algebra); the **deployment binds over Z_q via the engine NTT/CRT** (exact integer, no float drift) — that engine port is R3.x. NEXT = R3.2 `G-R3-LOSS` (consolidation loss + fact-survival, pin the promotion budget) → R3.3 dual-route (RETRIEVE shortlist → the closed #222 VERIFY) → R3.4 NIGHTSHIFT idle loop. All Path-A steps remain **no-budget**.

**R3.2 — G-R3-LOSS GREEN (2026-06-17, engine aae3131; 12B-b1).** Architecture correction made before running: in the locked retrieve-and-verify design Ring-3 stores a content-addressable **pointer**, not a lossy gist — a correct recall fetches the **verbatim** Ring-2 tensor, so **hit fidelity is 0 by construction.** The directive's "gist-PPL vs verbatim-PPL" delta would read ~0 (trivial/misleading) or require the convicted lossy-gist Path B. So `G-R3-LOSS` decomposes into three real axes, all measured:

| axis | result |
|---|---|
| **(1) hit fidelity** (correct id → verbatim ep_wiki, NPOS=16) | PPL 4.6665 == baseline → **+0.000% — lossless verify** |
| **(2) capacity miss** (wrong id → foreign ep_toy, NPOS=16) | PPL 5.0417 → **+8.04%**, i.e. **>> the 2% gate ⇒ flagged + O(1)-rewound, never silent corruption**. Recoverable-info loss is BINARY: 0 on hit / total on miss, governed by `recall@1(N)`. |
| **(3) promotion budget** (from the G-R3-BIND curve @ D=1024) | recall@1 = 1.0 to **N=32** → **consolidate ≤ 32 episodes per Ring-3 vector for lossless recall**; beyond, misses are gate-caught (degrade-safe) |
| **(4) latency shear** | unbind+cleanup **71 µs** (negligible) + one Optane ReadFile (existing Ring-2 backend); inject/score unchanged |

The thermodynamic answer: a correct unbind costs **zero** fidelity (the verify re-injects exact bytes); a wrong unbind (capacity overflow) loses the fact but is **caught by the deflection gate** — the loss is degrade-safe, not corrupting. Receipt `engine tests/fixtures/xbar_r3/G-R3-LOSS.log`. NEXT = R3.3 `G-R3-DUALROUTE` (wire the live RETRIEVE shortlist → the closed #222 VERIFY end-to-end on 12B+E2B). No-budget.

**R3.3 — G-R3-DUALROUTE GREEN (2026-06-17, engine 69638cf).** The continuous retrieve-and-verify pipe, composed from individually-metal-proven stages (`tools/ring3/g_r3_dualroute.py`): **RETRIEVE** = VSA unbind (R3.1) → top-K shortlist → **VERIFY** = the #222 / R3.2 gate (correct → +0.000% ACCEPT / foreign → +8.04% REJECT, 12B metal) → **LAND/UNDO** = `gemma4_kv_replay` + `gemma4_kv_rewind` O(1) (#222). Three pipes:

| pipe | trace | verdict |
|---|---|---|
| **(a) clean hit** | cue → shortlist top-1 = correct → verify +0.000% → ACCEPT | scan_len=1, PASS |
| **(b) decoy scan** | adversarial shortlist [foreign, correct] → rank-1 +8.04% REJECT+rewind → rank-2 +0.000% ACCEPT | scan_len=2, PASS — the top-K (P2.b top-5) door: survives a wrong candidate, still lands the fact |
| **(c) null parity** | empty Ring-3 → empty shortlist → NULL → no inject → baseline byte-exact (== no module) | PASS, scan O(1) |

The pipe takes a raw cue, survives the VSA unbind, executes the shortlist scan (rejecting + O(1)-rewinding foreign candidates), and lands the correct verbatim memory in the resident cache — degrade-safe throughout. Receipt `engine tests/fixtures/xbar_r3/G-R3-DUALROUTE.log`. NEXT = R3.4 NIGHTSHIFT idle loop (Ring-2 → bind → Ring-2′ shadow → G-R3-LOSS gate → Ring-3, pre-eviction; saturate-and-seal at ≤32 episodes/vector). No-budget.

**R3.4 — G-R3-NIGHTSHIFT GREEN (2026-06-17, engine a64a916). Ring-3 Path A CLOSED end-to-end.** The idle-loop consolidation state machine (`tools/ring3/g_r3_nightshift.py`): SELECT a resident Ring-2 episode → BIND (addr⊛id into the active vector, in a shadow copy) → SHADOW-GATE (re-verify **every** bound episode still recalls@1 above margin — crosstalk-safe, not just the new one) → PROMOTE + EVICT (free the resident slot; the verbatim ep.k **stays on Optane**, a tier-demotion not a delete) → SATURATE & SEAL (gate-driven; CAP=32 = the R3.2 budget as a safety cap) → fresh vector.

| run | result |
|---|---|
| **(A) D=1024, CAP=32 (production)** | 40 episodes → vector#1 seals at the cap (32), vector#2 carries 8; all recall@1 GREEN; resident pool 40→0; **349.8 MB resident KV demoted to Optane, Ring-3 resident index 16.3 KB** |
| **(B) D=128 (small)** | the shadow-gate fires **before** the cap — seals `[10,6,15,8,1]` (max 15 < 32), proving the seal is the capacity **math**, not a hardcoded 32; all recall@1 GREEN |

The thermodynamic GC works: episodes move from the expensive resident pool into the dense superposed index (O(1)-per-vector resident footprint) before capacity runs out, the eviction is degrade-safe (gate guards reachability before the slot is freed; verbatim survives on Optane), and the seal is the math. Receipt `engine tests/fixtures/xbar_r3/G-R3-NIGHTSHIFT.log`.

**⇒ Ring-3 Path A is CLOSED end-to-end, parameter-free, zero training budget: R3.1 BIND → R3.2 LOSS → R3.3 DUALROUTE → R3.4 NIGHTSHIFT, all GREEN.** Remaining (deferred): the R3.x **provenance tag** (G-R3-PROV); and **Path B** (the P2.b adapter) — only if a future need shows the parameter-free shortlist insufficient, and only behind the operator's budget green. **The R3.x Z_q/NTT engine port is now DONE (2026-06-18) — no longer deferred** (next run-records).

**R3.x — G-R3-BIND-on-O_K Leg A GREEN (2026-06-18, engine 0019b86; `tools/ring3/g_r3_bind_ok.py`). The native-engine port — the deferred R3.x Z_q/NTT bind, now CLOSED.** The host-numpy float-FFT VSA bind/unbind (R3.1) is re-carried onto the **engine-native exact-integer dual-prime NEGACYCLIC CRT-NTT** already linked into `sp_engine_cuda` (`core/ntt_crt` + `core/poly_ring`; frozen primes q1=1073738753, q2=1073732609, M=1152908312643096577). Three axes, all measured:

| axis | result |
|---|---|
| **C↔engine parity** (numpy-int reference vs native `sp_pr_mul` / `ntt_forward∘pointwise∘inverse` / `sp_pr_inner` / `sp_pr_score_kstore`-encode) | **256/256 bit-identical** — the `arm.h`-style EXACTNESS CONTRACT holds for the bind algebra |
| **margin parity** (±1 carrier, integer vs float recall) | int == float recall — the ±1 encode is **lossless**; recall@1 = 1.0 to N=16, recall@5 = 1.0 to N=32 @ deg-512 |
| **reduction-order immunity** | the integer superposition `M` is **byte-identical across all 8 reduction permutations**; the float `M` diverges at 4.44e-15 — the same order-immunity that motivated the C2 discrete resolver, now in the Ring-3 carrier |

Seam note (no new linkage): the `gemma4_kv_*` cache is pure f32 (the INT8/dp4a path is the *weight* GEMV, NOT the cache), and `poly_ring`/`ntt_crt` are reachable with **zero new linkage** — the bind runs over the existing math-core substrate. Receipt `engine tests/fixtures/xbar_r3/G-R3-BIND-on-O_K.log`.

**R3.x — Leg B HONEST NEGATIVE (2026-06-18, engine d7d96fe). Structure-on-the-carrier is measured-inert.** Tested replacing the random ±1 carrier with **split-prime O_K Dirichlet-character carriers** (Kronecker χ_d; the Heegner ladder d=−67 streak-16 vs d=−163 streak-40, deg N=512). The characters *do* Heegner-order native coherence (mean@N=64: random 0.0355 > OK-67 0.0153 > OK-163 0.0086 — more arithmetic structure ⇒ lower cross-talk) **but are OPERATIONALLY INERT**: recall is *worse*, because a spiky-spectrum periodic carrier degrades the unbind, and the downstream SimHash Hamming distance is unchanged. **Verdict: random ±1 stays the carrier** — the carrier must remain unstructured (this is the Leg-B negative that DESIGN-VSA-ring3 §2 now records). Receipt `engine tests/fixtures/xbar_r3/G-R3-BIND-OK-charcarrier.log`.

**R3.x — G-R3-ORGANISM-NATIVE GREEN (2026-06-18, engine 1f0f6be; `tools/ring3/ok_bind.py`). Float FFT ripped out of the live R3 deployment.** `ok_bind.py` routes bind/unbind through native `sp_pr_mul` (ctypes), with **D=1024 tiled as a direct sum of two 512-blocks** (the two NTT blocks the deg-512 substrate supports) — CAP=32 is **not** regressed by the tiling. `g_r3_dualroute` + `g_r3_nightshift` re-ran GREEN on the native bind (the R3.3/R3.4 pipes now use the integer carrier end-to-end, not numpy FFT). Receipt `engine tests/fixtures/xbar_r3/G-R3-ORGANISM-NATIVE.log`.

**R3.x — G-R3-MOBIUS NEGATIVE (2026-06-18, engine 1e70763). Möbius square-free filtering on the dense superposition fails.** Tested Möbius / square-free sparsification on the bundled store `M`: `M` is **99.6% dense**, so the filter sheds memories (recall 1.000→0.969 @ N=32) for no capacity gain — another measured-inert structure-on-content lever. Kept on the board as the honest negative; the bundle stays dense. Receipt `engine tests/fixtures/xbar_r3/G-R3-MOBIUS.log`.

## 6. Scope fence

- Ring-3 is **Ring-2-verbatim's gist companion**, not a replacement. The verbatim store and its O(1) evict/rewind/replay (C2 + #222, CLOSED) remain the source of truth; Ring-3 only *shortlists* into it.
- **No training is opened without the operator's explicit budget green** (Path B / R3-B only). Path A (R3.0–R3.4) + the native-engine port (R3.x) are compute-only and need no budget.
- Recall-time gist upsampling stays FORBIDDEN (§1). The provenance tag (G-R3-PROV) is deferred.
- **The carrier stays unstructured (the Leg-B boundary thesis).** O_K's value here is the *exact arithmetic* of the container (the bind / order-immunity / the integer superposition), NOT structure imposed on the content: split-prime Dirichlet-character carriers (Leg B) and Möbius square-free filtering (G-R3-MOBIUS) are both measured-inert. Random ±1 remains the carrier; do not re-open a structured carrier without a receipt that beats it.
