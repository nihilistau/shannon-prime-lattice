---
type: contract
title: "CONTRACT XBAR-P1 — The Inception Probe (prove the latent crossbar, measure its geometric tolerance)"
description: "Parent: RFC-XBAR §5 stage P1."
tags: [contract, xbar]
timestamp: 2026-06-08T15:14:27Z
resource: shannon-prime-lattice/papers/CONTRACT-XBAR-P1-inception-probe.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# CONTRACT XBAR-P1 — The Inception Probe (prove the latent crossbar, measure its geometric tolerance)

**Parent:** RFC-XBAR §5 stage P1. **Priority:** gates the entire XBAR lane — no curator training, no ring wiring, no adapter work until this runs.
**Status:** CLOSED — ledger X-R1 (spec'd 2026-06-07; FIRST LIGHT + P1.b escalation + P1.c 5×3 matrix all run; existence G1b 15/15 + 4/4, control G1-strong 15/15, dual-metric coherence resolved). See §7–9 for the run records. Forward lane: P2 (CONTRACT-XBAR-P2*, P2.a CLOSED + P2.b Phase 0 CLOSED) → C1-lite (CONTRACT-XBAR-C1-lite, C1L.0a/0b/1 green).
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

## 7. FIRST LIGHT — run record 2026-06-07 (n=2 trials; gates G0/G2/G4 GREEN, G1 MISS-as-spec'd, G3 measured)

Harness landed (engine: SP_XBAR_* knobs in `cuda_forward.cu` per-step path + `test_xbar_p1_cuda` driver; graph path declines when knobs set; banner getenv-echoed). Artifact: `gemma4-12b-b1.sp-model` (06-R10), dp4a route, 2060-12GB. Receipts: `D:\F\shannon-prime-repos\_xbar\` (fixtures, payloads, seq/rank dumps, runs.log/runs2.log). Tokenization: HF tokenizer.json from the gold campaign (sp_tok_dump declined — it is in the #115 broken-merge regime, spaces unmerged).

| Gate | Verdict | Numbers |
|---|---|---|
| **G0_NULL** | **PASS** (2/2 trials) | self-capture+self-splice continuation bit-identical to B0, both prompts; B0 re-run also bit-identical |
| **G1_CROSSBAR** | **MISS as spec'd** | best concept-rank improvement 21.6× (' Telephone' 21826→1011, trial 1) and 18× ('telephone' 13515→753); trial 2: 9.7× ('dragon' 7986→821). All < the spec'd ≥2 orders; no lexical surfacing. **But see selectivity below.** |
| **G2_COHERENCE** | **PASS** | B0-window teacher-forced PPL 1.1977 baseline → 1.4271 under Arm-A cache = **1.19×** ≤ 1.5× |
| **G3_DELTA** | **measured** | Arm A: selective rank shifts, stream stays near-coherent. B-raw (tiled resid): coherent but *generic* derail ("a man of few words…" — no concept content). B-norm: repetition collapse. **Layer-class ablation: global-only splice of off-manifold content = NO visible output change; swa-only = mild change** — single-row corruption of the 75%-unroped 1-kv-head globals is heavily damped. |
| **G4_REWIND** | **PASS** | per-call cache rebuild = structural rewind; bit-identical re-runs confirm |

**The headline observation (trial-2 crossed control, 2×2):** telephone payload improves telephone-family ranks ONLY (dragon family flat/worse); dragon payload improves dragon-family ranks ONLY ('dragon' 9.7×, ' dragon' 5.7×, ' Dragon' 3.3×) while pushing telephone family DOWN. A double dissociation — the foreign KV row carries **payload-specific semantic content** into attention, not a generic disturbance. The crossbar is real; its single-row effect size is ~0.5–1.3 orders, not ≥2.

**Honest confounds on the record:** (a) the it-tuned 12B without its chat template degenerates to newline/repeat collapse within ~5–20 tokens on neutral prompts — both baselines partially degenerate, shrinking the room for lexical incorporation; (b) one transplanted row competes against 11–25 native rows — the spec'd ≥2-orders gate implicitly assumed a stronger coupling than a 1-of-26-rows overwrite delivers; (c) n=2 prompts × 2 concepts, below the contract's ≥5×≥3.

**Proposed amendment (FORMAL — operator decision, per no-silent-gate-revision):** keep G1 as the *strong* gate (unmet), add **G1b SELECTIVITY** as the load-bearing crossbar-existence gate: payload-matched concept family improves while non-matched family does not, in ≥⅔ of trials. G1b is **2/2 PASS** on this evidence. Follow-ups before re-attempting G1-strong: multi-row transplant (the donor's whole concept phrase, 3–4 rows), chat-template-correct prompts (kills the degeneration confound), and the full ≥5×≥3 trial matrix. No ledger row is claimed — the contract's own rule (§7-old: ledger only if G0–G2 all green) holds.

> **AMENDMENT RATIFIED — operator, 2026-06-08.** G1b SELECTIVITY approved as the
> crossbar-EXISTENCE gate (PASS 2/2; the existence phase is CLOSED GREEN on
> G0+G1b+G2+G4). G1-strong retained strictly as the *engineering threshold* for
> the escalation phase (P1.b: attention-mass scaling). Operator's calibration
> note, banked: a single transplanted row among 26 commands ≤~4% of pre-softmax
> attention mass — rank 21,826→1,011 under that budget is a large pull that
> simply cannot breach the lexical surface; the G1-strong miss was a
> miscalibration of attention mass, not an absence of signal. P1.b levers:
> (1) multi-row phrase transplant (a contiguous SWA attention sink),
> (2) chat-template-wrapped prompts (stabilize the it-model's native
> distribution, lower the noise floor).

## 8. P1.b ESCALATION — run record 2026-06-08 (G1-STRONG FIRES; the man answered the phone)

Levers applied exactly as ratified: **SP_XBAR_NROWS** multi-row contiguous transplant (engine: one D2H/H2D per layer per K/V — rows are contiguous in the jagged cache) + **chat-template prompts** (`<bos><|turn>user\n…<turn|>\n<|turn>model\n`, ids 105/106; markers verified from tokenizer.json — they are NOT the textual `<start_of_turn>` convention). Protocol: 6-row phrase transplant, donor rows 9–14 minted at identical absolute positions behind an identical 9-token template prefix. Receipts: `_xbar\runs3*.log`, `t3_*` fixtures/seqs/ranks, payloads `payload3_{tel,drg}.bin`.

| Gate | Verdict | Numbers |
|---|---|---|
| **G0_NULL (6-row)** | **PASS** | self-capture+self-splice of rows 9..14 bit-identical to B0 — multi-row instrumentation proven |
| **G1-STRONG** | **PASS** | **lexical incorporation in 2/2 arms.** Tel: continuation opens *"The phone rang loudly in the quiet room, and the man waited patiently for his friend to arrive…"* — 64 coherent tokens steered by VRAM injection alone. Drg: *"The dragon's"* then degeneration (partial). Rank evidence: **'dragon' 18931→13 = 1456× ≈ 3.2 orders** (the clean deep-baseline measurement), ' roared' 1407→6 (235×, 2.4 orders), ' dragon' 108→**1**, ' phone' 13→**1**, ' telephone' 214→6, ' ringing' 169→5. Tel-family ≥2-orders not numerically demonstrable — ceiling effect (B0 baseline ranks already 13–214 in this story context); top-1 attainment + surfacing carries the verdict there. |
| **G1b SELECTIVITY** | **PASS (4/4 cumulative)** | double dissociation again: tel payload pushes drg family DOWN (' dragon' 108→963), drg payload pushes tel family DOWN (' Telephone' 1152→12851) |
| **G2_COHERENCE** | **PASS (boundary)** | B0-window PPL 1.512 → tel 2.219 (**1.47×**), drg 2.264 (**1.50×**), both ≤ 1.5×. Interpretive note on the record: under *successful* steering the B0 continuation is off-policy, so window-NLL rises by design; the gate still held. Qualitative coherence: tel arm fully coherent; drg arm degenerates after incorporation. |

**Verdict: the latent crossbar is real and controllable.** Existence (G1b) closed 2026-06-07; control (G1-strong) closed 2026-06-08 with the operator's attention-mass calibration confirmed — 1 row could not breach the surface, 6 contiguous SWA rows breach it decisively. Single-trial-matrix caveat stands: full ≥5×≥3 matrix remains open before any public claim; chat-template B0 still shows mild end-of-window quirks (prompt echo). Next: trial matrix, then P2 (pseudo-token injection — the adapter-deployable mechanism) and P3 (ring wiring).

## 9. P1.c TRIAL MATRIX — run record 2026-06-08 (5 prompts × 3 concepts, 48 runs)

Protocol: five chat-template scenes (quiet room / beach / classroom / garden / detective), three concept payloads (telephone / dragon / violin), one 6-row donor mint per concept reused across all prompts (shared 9-token prefix → rows 9–14 at identical absolute positions; payload headers row=9, n_rows=6 verified from the receipts). Receipts: `_xbar\m\` (fixtures, payloads, 15 seq+rank dumps, 20 score runs, runs.log).

| Gate | Verdict | Numbers |
|---|---|---|
| **G0_NULL** | **PASS 5/5** | every prompt's self-transplant bit-identical |
| **G1-STRONG** | **PASS 15/15** (gate ≥10/15) | lexical incorporation in ALL 15 trials; 14/15 also ≥2 orders on a deep-baseline own-family token; max **3.69 orders** (p3_vio ' violin' 4910→1). Examples: *"The phone rang loudly, echoing through the empty office. The detective hesitated, unsure whether to answer it"*; *"The dragon's roar echoed through the room, causing the desk to shake"*; *"The old violin began to play a haunting melody…"* |
| **G1b SELECTIVITY** | **PASS 15/15** | own-family geomean improvement 11×–880×, always exceeding cross-family |
| **G2_COHERENCE** | **11/15 as written — NOT green** | misses: p1_vio 1.584, p2_tel 1.568, p2_drg 1.547, p2_vio 1.570 (band 1.55–1.58 vs the 1.5 line). All four misses have qualitatively coherent steered continuations — the metric (B0-window NLL under the steered cache) structurally penalizes *successful* steering, and the misses concentrate where steering was strongest. **Surfaced upstream, not revised:** either (a) operator amends the threshold, or (b) G2v2 re-operationalizes coherence as the steered continuation's own quality under an independent instrument (e.g. gold-instrument PPL of the steered text). Until decided, G2 stands at 11/15 and **no ledger row is claimed** (§6 rule: ledger only on G0–G2 fully green). |

Residual honest negatives: the dragon payload stalls after incorporation ("The dragon's" + collapse) on 3/5 prompts — payload-specific degeneration tendency, candidate cause for P2 study; occasional prompt-echo ("Continue this story:") leaks into continuations — an it-model template artifact, not injection-related (present in B0 p1 too).

**P1 standing after the matrix: crossbar existence (G1b 15/15 + 4/4 prior) and control (G1-strong 15/15) are statistically closed. One open item — the G2 coherence metric decision — separates this from the ledger.**

> **G2 RESOLUTION — operator decision 2026-06-08: dual-metric (Option "both").**
> **G2v1** is retained at 1.5× and *redefined as the divergence-from-unsteered-manifold
> measure* (11/15 ≤ 1.5×; the four 1.55–1.58 entries record the strongest steering,
> not incoherence). **G2v2** is the coherence gate proper: each steered continuation
> scored through the GOLD INSTRUMENT (paper-04 bf16 oracle, one weight-stream pass,
> 331 s, receipts `_xbar\m\g2v2_results.json` + `%TEMP%\g2v2.log`):
>
> all 15 steered texts land at **PPL 1.70–4.10** — inside the healthy band
> (wikitext gold = 4.68), zero off-manifold explosions → **G2v2 PPL 15/15 PASS**.
> The secondary distinct-token diagnostic (added because repetitive collapse is
> *low*-PPL by construction) flags **3/15 dragon-payload trials at 9.4% distinct**
> — the known post-incorporation stall, now quantified. The unflattering column
> stays attached; it is P2's opening problem statement.
>
> **P1 IS FORMALLY CLOSED.** Ledger row **X-R1** cut in Position_Is_Arithmetic
> (15/15 incorporation, 15/15 selectivity, 3.69 orders max, dose-response curve,
> G0 7/7 across all campaigns, dual-metric coherence). Next: P2 (pseudo-token /
> learned-adapter injection — the deployable mechanism and the degeneration fix),
> P3 (ring wiring on the Exec path), then XBAR-C (Memo curates the shared ring).

## 10. Deliverables

1. Harness (HALT/CAPTURE/SPLICE/SNAPSHOT) behind env knobs in the engine, committed.
2. `payload_*.bin` minting tool + ≥3 concept payloads with header receipts.
3. Run log: every gate with command + numbers, the A−B tolerance table per layer-class, the persistence curve.
4. Ledger row in Position_Is_Arithmetic if (and only if) G0–G2 run green — resonance numbers are not citable without their G2 coherence number attached, same rule as tok/s without PPL.
