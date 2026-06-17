# DESIGN — VSA / Harmonic Binding as the Ring-3 holographic consolidation tier

**Status:** **IMPLEMENTED + NATIVE (2026-06-18).** The mechanism this doc specifies (HRR / circular-convolution binding for Ring-3 consolidation) is GATED GREEN end-to-end (CONTRACT-XBAR-R3 R3.1→R3.4) and, as of 2026-06-18, the deployment **binds/unbinds via the engine-native exact-integer `sp_pr_mul` (Leg A)** — the float-FFT prototype is ripped out of the live path. Two normative findings are now folded in below: (a) §2 — the bind is the native dual-prime CRT-NTT over `Z_q` (C↔engine parity 256/256 bit-identical, reduction-order-immune); (b) §2/§3 — the **carrier must stay unstructured** (random ±1): the structured split-prime Dirichlet-character carrier (Leg B) is a measured **honest negative**. **Parent:** RFC-XBAR v1.4 §Ring-3 amendment (the consolidated "neocortical/gist" tier, dual-recall, `G-R3-LOSS`); CONTRACT-XBAR-R3 (the gated contract + run-records); CONTRACT-XBAR-C1-lite (the curator); `DESIGN-diffusion-lane.md` (the consolidation-time gist instrument + the §4 recall-time-upsampling trap); CONTRACT-XBAR-P2b §3n/§3o (why VSA is NOT the curator).
**One line:** Vector-Symbolic-Architecture (HRR / circular-convolution) binding is the right primitive for **Ring-3 associative consolidation** — superposing many episodes into one fixed-size `Z_q` store, recalled by content address with graceful lossy degradation — and is the **wrong** primitive for Ring-0/1 latent steering. This doc relocates it to its native home and bakes in the corrections that killed the steering version.

---

## 0. Provenance & the steering verdict (why this lane is scoped where it is)

A 2026-06-11 design exchange proposed using harmonic binding (circular convolution = NTT point-wise multiply) to fuse the 64-token context with the 6-token span into the k=2 curator pseudo-tokens, replacing the Fork-3 ML adapter. **That proposal is condemned for STEERING and the reasons are load-bearing here:**

1. **Manifold shock.** The curator's pseudo-tokens are injected into the **frozen Gemma residual stream**, whose readable geometry is a specific learned manifold. A bind `m = s ⊛ c` lives in a random-phase frequency geometry — maximally off-manifold. Our own **1-layer-vs-6-layer injection result** is the evidence: a single-layer off-manifold injection made the Exec *narrate the glitch* ("the entire network directed its attention to it"); spreading it across 6 layers (smooth, on-manifold) grounded it ("the phone rang and the man answered"). A VSA-bound vector is further off-manifold than the raw semantic vector that already shocked the model. **KAIROS steering requires on-manifold continuous vectors; VSA emits off-manifold discrete hashes.**
2. **Storage ≠ generation.** Binding solves content-addressable *recall*; the curator needs on-manifold *steering*. Recovering `s` by unbinding does not make `s` something the frozen Exec can read — and Ring-2 already stores the exact bytes losslessly.
3. **The exact spectral inverse is unstable.** `NTT(c)_i^{-1} mod q` amplifies near-zero components catastrophically and is undefined wherever a component ≡ 0 mod q (which happens on real quantized activations). Classical HRR avoids it deliberately — see §2.
4. **sm_75 reality.** NTT butterflies on Turing are **ALU/scheduler-bound** (the `lop3`-vs-`xor` dispatch ceiling, the paired-register PTX-modmul hazard — both banked), **not** Tensor-Core-accelerated; TCs do no modular reduction. Generating binds on a hot path would hit exactly the constraints we protect. (In the Ring-3 **idle/Nightshift** loop this is fine — see §4.)

**Conclusion:** VSA is not dead; it was trespassing in Ring-1. Its native home is Ring-3, where lossy superposed associative memory is the *design intent*, not a defect.

## 1. What Ring-3 is (and why VSA fits it)

Ring-3 (RFC v1.1) is the **consolidated, gracefully-degrading, superposed long-term tier** — the neocortical gist to Ring-2's verbatim hippocampus. Its governing bound is **`G-R3-LOSS`**: consolidation may be lossy, but un-compressible episodes **stay verbatim in Ring-2** (a valid outcome, not a failure). The properties that made VSA *wrong* for steering are exactly *right* here:

| VSA property | Steering (Ring-0/1) | Consolidation (Ring-3) |
|---|---|---|
| Lossy superposition + crosstalk | fatal (manifold shock, garbage generation) | **feature** (gist memory, graceful degradation) |
| Fixed-size store, many items | irrelevant | **feature** (bounded VRAM, the neocortical compression) |
| Compute-bound, parameter-free | doesn't fix the fidelity bottleneck | **feature** (free in the KAIROS idle loop) |
| Content-addressable / completion-from-partial-cue | not needed | **the whole point** (associative recall) |

## 2. The corrected mechanism (the math fixes are normative)

Work over `Z_q`, `q` an NTT-friendly prime (the engine's existing NTT/CRT substrate). Vectors are length `d`.

**Keys are ENGINEERED near-orthogonal carriers, not raw activations.** `key_i ∈ Z_q^d` is a deterministic address — a frozen ±1 Rademacher draw (the `sp_arm_build_R` seed discipline). The **value** `value_i` is the episode gist descriptor (the curator's k=2 pseudo-tokens, or a pooled episode vector) — STORED, never injected raw.

**The carrier must stay UNSTRUCTURED — a measured law, not a preference (2026-06-18).** The earlier proposal to use a structured **Zeta-PE prime-harmonic** carrier (or any "more arithmetic structure" carrier) is **convicted as a Ring-3 carrier** by the Leg-B negative (CONTRACT-XBAR-R3 R3.x, engine d7d96fe): split-prime O_K Dirichlet-character carriers (Kronecker χ_d, the Heegner d=−67/−163 ladder) DO reduce native cross-coherence (mean@N=64: random 0.0355 > OK-67 0.0153 > OK-163 0.0086) but are **operationally INERT** — recall is *worse* (a spiky-spectrum periodic carrier degrades the unbind) and the downstream SimHash Hamming distance is unchanged. The boundary thesis: O_K's value is the *exact arithmetic of the container* (the bind, the order-immune superposition), NOT structure stamped onto the carrier. **Random ±1 is the carrier; do not re-open a structured carrier without a receipt that beats it.**

**The bind is NATIVE: the engine's exact-integer dual-prime CRT-NTT (2026-06-18).** The deployment does not bind with a host float FFT — it routes through `sp_pr_mul` / `ntt_forward∘pointwise∘inverse` over `Z_q` (the frozen primes q1=1073738753, q2=1073732609, M=1152908312643096577; `core/ntt_crt` + `core/poly_ring`, already linked into `sp_engine_cuda`, zero new linkage). C↔engine parity is **256/256 bit-identical** and the integer superposition `M` is **byte-identical across all 8 reduction permutations** (the float `M` diverges at 4.44e-15). `D=1024` is tiled as a direct sum of two deg-512 NTT blocks (CAP=32 un-regressed). This is the exact-integer realization of the "work over `Z_q`" the rest of this section specifies (CONTRACT-XBAR-R3 R3.x, engine 0019b86 / 1f0f6be).

**Bind (consolidation):**
```
m_i = INTT( NTT(key_i) ⊙ NTT(value_i) )  (mod q)
```

**Bundle (the superposition that IS the compression):**
```
S = Σ_i m_i  (mod q)        — many episodes in ONE fixed Z_q array
```

**Recall — by INVOLUTION, not exact inverse (the key correction).** To query with `key_q`, unbind with its **involution** `key_q*` (`key_q*[j] = key_q[(−j) mod d]`, i.e. circular *correlation*), **not** the spectral inverse:
```
value_est = INTT( NTT(S) ⊙ NTT(key_q*) )  (mod q)  =  value_match + crosstalk
```
The involution is what classical HRR uses precisely because (a) it is always defined (no division, no zero-component blow-up), (b) it is numerically stable (unit-magnitude in the random-carrier ideal), and (c) it **composes with bundling** — exact spectral inverse on a *sum* of binds does not isolate one item, the involution does (its crosstalk is zero-mean orthogonal noise). A **cleanup step** (nearest stored gist by cosine, or re-projection through the curator onto the Exec manifold) denoises `value_est`.

**The hard rule (manifold-shock + the diffusion-lane §4 trap).** Ring-3 returns a **gist / address**, *never* a vector injected raw into the Exec. High-fidelity content is served from **Ring-2 verbatim** (G-R3-LOSS) or re-synthesized on-manifold by the AR path. Recall-time gist→content *upsampling* is the forbidden trap (`DESIGN-diffusion-lane.md §4`); Ring-3 recall is for **addressing and partial-cue completion**, not content synthesis.

## 3. Capacity, and the gate that keeps us honest

HRR superposition capacity is bounded (~`d / (c·ln n)` clean items, Plate). The store trades fidelity for item count at fixed `d`.

**Gate `G-R3-VSA` + FALSIFICATION (pre-stated).** The holographic store must **beat the trivial baseline** — a hash-indexed Ring-2 pointer table — on the metric a hash table *cannot* serve: **(a)** capacity-per-byte at a fixed gist-fidelity floor, and **(b)** associative **completion from a partial / noisy cue** (recall the right episode from a corrupted or partial key). **LIFT** = at the target superposition count `n`, cleanup-recall accuracy holds above the `G-R3-LOSS` gist floor AND partial-cue completion works where an exact-match index returns nothing ⇒ open the lane. **KILL** = if it only equals a hash index (no graceful degradation, no partial-cue completion above the floor) ⇒ retire VSA and keep a plain content-addressable index. *We do not add NTT machinery to reimplement a dictionary.*

## 4. Hardware & scheduling (where the "compute-bound" claim is actually valid)

Binding/bundling/unbinding are `O(d log d)` NTTs over `Z_q` — the engine's existing primitive. On sm_75 this is **ALU-bound** (per the banked Turing receipts), which is **fine because Ring-3 consolidation runs in the KAIROS / Nightshift idle loop**, never on the decode hot path. It is parameter-free (0 bytes persistent VRAM beyond the one fixed `S` array) and VRAM-flat in the episode count — the genuine wins, scoped to the tier where efficiency, not steering fidelity, is the point. The earlier "Tensor Cores chew through the binds on-the-fly during Exec" framing is dropped: no hot-path binding, no TC claim.

## 5. Open friction (the honest risk register)

- **Value-side crosstalk.** Keys are engineered near-orthogonal, but the *values* are correlated LM gists (low effective rank, outlier dims). Crosstalk on recall is value-dependent; the cleanup memory must absorb it. Unproven until measured.
- **Quantization exactness.** Involution + NTT over `Z_q` is exact in the ring, but the gist *values* are quantized LM vectors; the gist-fidelity floor must be set against that quantization, not against a continuous ideal.
- **Carrier conditioning — RESOLVED (2026-06-18): plain Rademacher wins.** The prime-harmonic-vs-Rademacher question is answered: structured (Dirichlet-character) carriers lower NTT-domain coherence but recall *worse* (Leg B negative, §2). Random ±1 is the carrier. This friction is retired into the §2 unstructured-carrier law.
- **Cleanup cost.** Nearest-gist cleanup over `n` stored descriptors is itself `O(n·d)` — if `n` is large this competes with just indexing Ring-2; folds into the `G-R3-VSA` capacity-per-byte gate.

## 6. The call

**SHIPPED (2026-06-18) — this lane is no longer "banked."** What this doc proposed is gated GREEN end-to-end (CONTRACT-XBAR-R3 R3.1→R3.4) and now binds on the engine-native exact-integer CRT-NTT (`sp_pr_mul`, Leg A). The "telemetry before machinery" first step was honored — carrier coherence WAS measured first, and it produced the Leg-B negative that pinned the carrier to random ±1 (§2/§3). The original sequencing note is retained below for provenance:

> *(historical)* Banked as a **design lane**, not a build order. Sequenced **behind** the P2.b curator resolution (Fork-4 §3o → Fork-3 §3n) and the Ring-3 RFC amendment maturing; it is a KAIROS/Nightshift consolidation primitive, so it opens when K1/NIGHTSHIFT does. First cheap step when it reaches the front: **measure carrier coherence + single-bind recall fidelity** on real curator gists before building the bundle/cleanup stack — telemetry before machinery, the standing rule.
