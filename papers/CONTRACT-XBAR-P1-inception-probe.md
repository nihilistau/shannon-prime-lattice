# CONTRACT XBAR-P1 — The Inception Probe (prove the latent crossbar, measure its geometric tolerance)

**Parent:** RFC-XBAR §5 stage P1. **Priority:** gates the entire XBAR lane — no curator training, no ring wiring, no adapter work until this runs.
**Status:** DRAFT (spec'd 2026-06-07; not yet run — no numbers exist for this contract yet).
**One line:** halt gemma-4-12B mid-decode, splice foreign state into its KV cache two ways — geometrically exact (Arm A) and geometrically naive (Arm B) — and measure both whether the model integrates the memory and *how much geometric fidelity the integration demands*. The A−B delta is the spec every future injector (Memo, modality adapters) must be trained to hit.

---

## 0. Objective

Prove (or falsify) the zero-copy latent crossbar on the proven Exec stack: **gemma-4-12B, OK_Q4B B1 artifact (the PPL-5.12 / 24-gate artifact from 06-R10), CUDA engine `k_gemv_q4b` path, RTX 2060-12GB.** Decode-only, short contexts, fits with headroom.

Three questions, each with a numeric answer:

1. **Does it work at all?** Can foreign (K,V) state placed directly in the cache steer generation, with no tokens involved?
2. **What does it cost?** Coherence (PPL) of the post-injection window vs baseline — does the memory integrate or destabilize?
3. **How exact must the injector be?** The measured gap between exact-geometry (Arm A) and naive (Arm B) injection.

## 1. Geometry constraints (the law the probe must honor — and measure)

gemma-4-12B cache geometry per position, per layer (48 layers):

| Layer class | KV shape | RoPE | V |
|---|---|---|---|
| SWA (40 layers) | 8 kv-heads × 256 | full, θ=1e4, **absolute-position phase** | real V projection |
| GLOBAL (8 layers: 5,11,…,47, period 6) | 1 kv-head × 512 | **partial 0.25** (75 % of dims unroped), θ=1e6 | **V-LESS**: V = raw K projection, weightless-RMS-normed, never roped |

Consequences baked into the design:

- **Position alignment is mandatory for Arm A.** Stored K carries RoPE phase at its minting position. The donor run is therefore *constructed* so the donor concept token sits at exactly the splice-target absolute position (pad the donor prompt). No re-roping in v0 — transplant real state at the same coordinates it was minted at.
- **Persistence prediction (measured, not assumed):** SWA layers stop seeing the injected position once the window slides past; long-range carriage is the GLOBAL layers. The probe logs resonance as a function of distance-from-injection to test this.
- **Tolerance prediction (measured, not assumed):** GLOBAL layers (75 % unroped) should tolerate imperfect injection best. Arm B per-layer-class ablation tests this.

## 2. Harness (engine work, `cuda_forward.cu` decode loop)

Four small capabilities, all on the owned arena (no framework GC in the way):

1. **HALT** — stop decode at position `p_inj` (env knob), leaving cache + stream state intact.
2. **CAPTURE** — dump the full per-layer (K,V) set for one position to disk (`payload_<concept>.bin`: 48 layers × layer-class shape, plus a header recording position, artifact sha, layer geometry).
3. **SPLICE** — `cudaMemcpy` a payload into the cache slots at `p_inj` (all layers, or a layer-class subset via mask).
4. **SNAPSHOT/RESTORE** — copy-out/copy-in of the whole cache for rewind. (v0 rewind is a raw snapshot; transactional Spinor rewind arrives with ring wiring in P3. Stated plainly so nobody mistakes this for the full mechanism.)

Per standing feedback: the harness banner **echoes every knob via getenv enumeration** (no prose-claimed config), and every gate prints **oracle-rank telemetry**, not just pass/fail.

## 3. Protocol

**Donor run (payload mint).** Prompt placing the concept token (e.g. "telephone") at absolute position `p_inj`. CAPTURE its (K,V) set → `payload_telephone.bin`. Also capture the donor's **final-layer residual** (1×3840) at the same position → `payload_telephone_resid.bin` (Arm B ammunition).

**Baseline run (B0).** Neutral prompt ("The man sat down in the quiet room and began to"), greedy decode `N=64` tokens past `p_inj`. Log: token stream, per-step logits for the concept-token set, PPL of the continuation window.

**G0 — self-transplant null control (run first, blocks everything).** CAPTURE position `p_inj` from the baseline run itself, SPLICE it back in unchanged, resume. Output must be **bit-identical** to B0 (the graph path is already proven bit-exact, so any divergence is harness corruption, not model behavior). This is the control that separates "the probe works" from "the probe broke the cache."

**Arm A — real-KV transplant.** SPLICE `payload_telephone.bin` at `p_inj` (overwriting the slot the baseline minted there), resume, decode N tokens. Repeat over ≥5 neutral prompts × ≥3 concepts (concepts chosen with distinct, low-frequency surface tokens so resonance is unambiguous).

**Arm B — raw-residual overwrite (the deliberate off-manifold arm).** Write `payload_telephone_resid.bin` content into the same slots, three sub-variants: (B-raw) truncate/tile the 3840-d residual into each slot shape as-is; (B-norm) RMS-matched to the slot's observed scale; (B-class) B-norm applied to GLOBAL layers only vs SWA layers only. Arm B is *expected* to underperform — it is run to put a number on the manifold, not to succeed.

**Rewind every arm:** RESTORE snapshot between trials; every trial starts from the identical cache.

## 4. Metrics (each gate on its own metric)

| Metric | Definition |
|---|---|
| **Resonance** | logit-rank of the concept token set at each step post-injection (oracle-rank style: print the rank, not a boolean). Headline: best rank achieved within N=64, and steps-to-rank<100. |
| **Incorporation** | does the greedy stream surface the concept lexically within N tokens (binary, logged per trial) — the qualitative "does he hear the telephone," kept subordinate to resonance. |
| **Coherence cost** | PPL of the post-injection window vs B0's same-window PPL (the gate the future curator inherits). |
| **Persistence** | resonance as a function of token-distance from `p_inj` (tests the SWA-fade / GLOBAL-carrier prediction). |
| **Geometric tolerance** | the A−B gap on all of the above — the deliverable number XBAR-C trains against. |

## 5. Gates

| Gate | Criterion | Verdict style |
|---|---|---|
| **G0_NULL** | self-transplant bit-identical to B0, all trials | blocks all other gates; failure = harness bug |
| **G1_CROSSBAR** | Arm A: concept-set rank improves by ≥2 orders of magnitude vs B0 at the same steps, in ≥⅔ of trials | the thesis gate |
| **G2_COHERENCE** | Arm A post-window PPL ≤ 1.5× B0 window PPL in trials where G1 fires | integrate-without-destabilize |
| **G3_DELTA** | Arm B measured on the same metrics; report the A−B gap per sub-variant and per layer-class | no pass/fail — a *measurement* gate; the number ships either way |
| **G4_REWIND** | post-RESTORE decode bit-identical to B0, every trial | the safety primitive the shadow-ring design rests on |

**Falsification, stated before running:** if Arm A — geometrically exact, real model-minted state at the correct coordinates — produces no resonance (G1 fails across concepts and prompts), then attention does not pick up foreign-minted cache state and the latent-crossbar thesis **as formulated** is dead at the cache level; XBAR retreats to P2 (residual-entry pseudo-token injection) as the only viable mechanism, and the RFC gets amended *formally* — no silent gate revision, no quiet retreat to a weaker claim.

## 6. Budget & risks

- **Compute:** trivial next to the PPL campaigns — decode-only, ≤80 positions/trial, ~50 trials. Hours, not days, on the 2060.
- **Risk 1 — slot-overwrite vs slot-insert.** v0 *overwrites* the position the baseline minted (keeps positions/lengths untouched — no jagged-cache surgery). An *insertion* variant (lengthening the stream) is deferred; overwrite is the minimal physics.
- **Risk 2 — quantized-cache interaction.** If the cache path quantizes KV, payload round-trips through the same codec as native entries (capture *post*-codec so Arm A stays exact by construction).
- **Risk 3 — concept choice confound.** High-frequency concepts can surface in B0 by chance; concept set must show rank>10k in B0 logits before being accepted as a probe concept.

## 7. Deliverables

1. Harness (HALT/CAPTURE/SPLICE/SNAPSHOT) behind env knobs in the engine, committed.
2. `payload_*.bin` minting tool + ≥3 concept payloads with header receipts.
3. Run log: every gate with command + numbers, the A−B tolerance table per layer-class, the persistence curve.
4. Ledger row in Position_Is_Arithmetic if (and only if) G0–G2 run green — resonance numbers are not citable without their G2 coherence number attached, same rule as tok/s without PPL.
