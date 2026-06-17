# Shannon-Prime — Current State of the Project

**As of 2026-06-18 (the XBAR memory architecture UNIFIED onto the exact-integer O_K substrate — Q(√−163), the algebra the project is built on; ten receipts, all GREEN or honest-negative; engine `0019b86→d2d7ceb`).** On top of the already-closed XBAR stack (Ring-2 verbatim, Ring-3 gist, EAR→Ring-2 bridge — proven end-to-end as of 2026-06-17), the memory tier was moved off the generic float carriers it had been running on and re-carried onto the engine-native dual-prime negacyclic CRT-NTT. The headline finding is a **boundary thesis** (§9): the substrate's value is exact arithmetic — the indestructible algebraic *container* — while every attempt to impose number-theoretic *structure* onto the high-entropy *content* was measured-inert. This is the human-readable map of where the project stands: what we built, the numbers that matter, the tests we used to prove each claim, *why* those tests are the right ones, and why the results can be trusted. It is written to be read top-to-bottom by a person, and to orient an agent in one pass. Detailed, citable records live in the contracts and `PPT-LAT-STATE.md`; this document is the synthesis, not the ledger.

---

## 0. What Shannon-Prime is, in one paragraph

Shannon-Prime is an attempt to build a **memory and agency substrate for a frozen large language model that is auditable at the bit level**. Mainstream inference treats the KV cache as an opaque, ever-growing scratchpad and treats agent state as text passed between models. We treat the cache as a **first-class, addressable, evictable, rewindable memory**, and we hold every operation on it to one of two standards: it is either *bit-exact* (byte-for-byte identical to the untouched baseline) or it passes a *pre-registered bounded-degradation gate* (a degradation threshold written down before the code, not tuned after). Everything runs on a single **RTX 2060 with 12 GB of VRAM**, driving **Gemma-3-12B** (quantized to ~4-bit), which is the load-bearing proof that this is an edge-deployable architecture and not a datacenter trick.

The last two weeks unified three axes on that one card:

- **Space** — the cache can be made *O(1) in context length* (flat VRAM from 8k to 16k tokens) with a learned sparse router, and a needle planted in a 16k haystack still survives the compaction.
- **Time** — the cache can be *rewound* by an O(1) memory-coordinate operation that is byte-exact, so a background process can "think" on a tick and then perfectly un-think it.
- **Cognition** — a resident 12B daemon holds disciplined silence on idle ticks, acts coherently only on salient events, and reverts cleanly — running the time and space machinery underneath it.

---

## 1. The XBAR — an auditable latent crossbar (the *space* axis)

### 1.1 What it is
XBAR ("auditable latent crossbar") is the memory fabric. The idea: a frozen transformer's behaviour can be steered by writing directly into its KV cache — model-to-model communication through *latent state* rather than text — and **every such write is well-formed, receipted, gated, and reversible**. Built in phases P1 → P3, then a compaction phase (C-b/C-c).

### 1.2 P1 — latent write works, and it is selective
We mint donor KV at RoPE-phase-exact absolute positions and splice it into a running 12B's cache.

- **Headline:** 15/15 lexical incorporation and 15/15 selectivity (a 2×2 double dissociation), with a single-token rank pull of up to **3.69 orders of magnitude**, while the steered text stays coherent (perplexity in the model's healthy band, not garbage).
- **The test that matters — and why:** a *self-transplant null* (write the cache's own contents back onto itself) came out **7/7 byte-identical**. This is the load-bearing control: it proves the instrumentation itself changes nothing, so any effect we then measure is the *payload*, not an artifact of the splice machinery. Without that null, every downstream number would be suspect.

### 1.3 P3 — the cache lives on a ring, spills to disk, and pages back
We made the cache a real memory hierarchy instead of one flat VRAM block.

- The sliding-window (SWA) layers — the dominant 40 of 48 layers — were moved onto a **W-slot ring buffer** (write slot = position mod W). That alone makes the big cache term O(1) in space.
- Per-step K/V is **spilled to a Ring-2 backend** (host RAM / disk) and **paged back** on demand. We proved the closed loop bit-exact by *poisoning* the live cache (overwriting it with zeros/NaNs) so that a correct read could *only* have come from disk.
- **Why poison is the right test:** it removes the possibility of "it looked right because the live cache happened to still hold it." If the decode stays token-identical after the live source is destroyed, the data provably came off the spill. That is a much stronger claim than a plain equality check.

### 1.4 C-b.2 — O(1) VRAM, measured
The 8 *global* (full-attention) layers can't use a sliding window, so we gave them a **compact slab**: keep the full K/V in host RAM (Ring-2), and per step page in only the union of the selected keys into a small fixed-size device slab.

- **Headline:** context length 8,192 vs 16,384 — **VRAM flat within ~50 MiB** (a full O(N) cache would add ~5.4 GiB across that doubling). The KV term is O(1) in context.
- **Honest scope (stated on the record):** the ~11.4 GiB absolute floor in that harness is the *resident 9.4 GiB model* plus rings — the test harness keeps the whole model in VRAM and bypasses the streaming path, so the *absolute* number is a harness artifact. The thing XBAR controls — the **KV term** — is what's O(1), and that is what we claim. We deliberately did **not** publish "12B @ 16k on 12GB" because the resident-model harness would over-state it.

### 1.5 The learned router — the part that's actually hard
Selecting *which* global keys to keep is the whole game. We measured it honestly, in order:

1. A **frozen ±1 geometric router** gave +4.17% perplexity at 8× compression on the full validation set — RED (over our <2% bar).
2. An **oracle** (exact top-B by true attention score) gave −0.08% — proving 8× is *information-achievable*, the router just wasn't good enough. (This flipped an earlier wrong call to "concede 4×"; see methodology.)
3. A **learned 512×32 LSH projection** router (trained by distilling the true attention distribution) gave **+0.47% at 8×** — GREEN, at the same per-step cost as the frozen router (the projection is a one-time matrix, no new hot-path kernels).

- **Why the progression matters:** measuring the oracle ceiling *before* training told us the target was reachable, so the training cycle was worth running. Skipping that step would have meant either training blind or wrongly conceding the compression ratio.

### 1.6 C-c NIAH — the needle survives
The retention proof: plant a secret "needle" deep in a 16k-token haystack, force it outside the sliding window so it can *only* be retrieved through the global crossbar, then free-decode and check the model recovers it.

- **Headline:** with the learned router the needle is recovered at depths 10%, 50%, and 90%. With a **frozen router (negative control)** it MISSES.
- **Why the negative control is essential:** a HIT alone could be leakage (the needle sitting in some live buffer). The frozen-router MISS at the same depth proves the retrieval is *the learned router doing its job*, not an artifact — the router selected the needle into the compact slab, and only the good router can. A full-attention baseline at 16k is physically impossible on the 2060 (the context-sized softmax blows the shared-memory budget), which is exactly the motivation.

### 1.7 P3.3 — the replay-write seam (CLOSED GREEN)
The read/compaction path proved XBAR can *read* a compacted cache; P3.3 closes the inverse — *writing* a stored episode back in. `SP_REPLAY` injects an episode's owner-K/V over the prefill rows `[0, NPOS)` at the CUDA cache-store boundary, before attention.

- **Headline (`G-P3-SHARED`, 3-leg PASS on BOTH 12B and E2B):** on the 12B (`gemma4-12b-b1`, 48 owners) and on E2B (`gemma4-e2b`, 15 owners / 20 sharers = owner-indirection exercised), an *intact* replayed episode is **bit-identical to baseline (diffs = 0)**, a *zeroed* episode **diverges 12/12** (collapse to a degenerate loop), and `SP_REPLAY` unset is the floor. Intact-equals-baseline proves the seam is well-formed; zeroed-diverges proves the payload is *load-bearing*, not inert.
- The inject is placed at **both** prefill stores in `gemma4_decode_cuda` (graph-capture and velocity paths) — the velocity path is the one the gate actually runs (`use_graph` false under recall). Receipts `tests/fixtures/xbar_p3_replay/G-P3-SHARED_{12B,E2B}_GREEN.log`; harness `SP_G4_REPLAY_GATE`.

### 1.8 P3.4 — recall quality (CLOSED GREEN)
The last gate: replaying a foreign episode must not *break the model's perplexity*. The PPL scorer **is** `gemma4_decode_cuda` in `SP_G4_SCORE` mode, so `SP_REPLAY` composed with it with **zero new engine code**.

- **Headline (`G-P3-PPL`):** wiki.tiny `n_ctx=84`, recall-OFF baseline SP PPL **4.6665** → recall-ON (proven episode, `NPOS=4`) **4.7311** = **+1.38% deflection, under the <2.0% gate → PASS**. A foreign episode over the 4 earliest of 84 positions, and the model holds focus. This complements the §1.5 sparse-recall deflection (learned-LSH 8× = +0.47%).
- **Honest caveat (on the record):** `n_scored = 42`, a single chunk. The number is *deterministic* (replay, not router sampling — so not a noise-flippable illusion like the small-N read-deflection was), but a **larger-N multi-chunk run is the hardening lever before any public headline.** Receipt `tests/fixtures/xbar_p3_replay/G-P3-PPL_run.log`; runner `_run_p34_ppl.bat`.

---

## 2. The Rewind — O(1) eviction at the metal (the *time* axis, KAI-1b)

### 2.1 What it is
For a resident daemon, "forgetting" an idle thought must be cheap. The naive way (re-prefill the surviving context) costs more every time the history grows. We built a **persistent-KV ABI** (`gemma4_kv_open / prefill / decode / rewind / commit / pos / snapshot / close`) where eviction is a single memory-coordinate operation: `rewind(Δ)` logically decrements the decode position by Δ. Because each cache slot maps to exactly one position, the sheared slots are never read again — so the rewind is a **perfect inverse**.

### 2.2 The tests and why they're right
- **G-1b-REWIND-NULL (bit-exact):** snapshot the cache, run an idle tick (prefill a frame + decode), rewind, snapshot again. The two snapshots are **byte-identical across all 48 owner layers (16.5 MB, diffs = 0)**. Plus EQUIV: re-running the idle tick after the rewind reproduces the *same* tokens — the rewound cache is a perfect re-entry point, "as if the tick never happened."
- **The O(actions)→O(1) telemetry:** we swept the number of retained actions A ∈ {1,2,4,8,16} and timed an idle tick under each. The host "prefix-grow" hack rises at **0.924 seconds per action** (linear recompute tax); the metal rewind is flat at **0.0073 s/action — a 127× shallower slope**, and 16.7× faster at A=16. That measured flatline *is* the O(1) claim; it's not asserted, it's the slope of a real curve.
- **Why bit-exact, not "close":** for a memory operation that will run tens of thousands of times unattended, any non-zero drift compounds. A bit-exact gate is the only one that can't silently rot over a long run.

### 2.3 The null floor
The one-shot production decode path (`gemma4_decode_cuda`) is left **byte-untouched**. The persistent-KV ABI is a separate twin. This means every previously-closed gate (the 26.1 tok/s @ PPL 5.12 paper-06 result, the NIAH retention, the XBAR results) is still valid — we didn't perturb the thing they were measured on. This "null floor" discipline is what lets the whole tower of results stay standing as we add to it.

---

## 3. KAI-1c — uniting O(1)-time with O(1)-space (the wrap-aware ring)

### 3.1 The hazard, named honestly
KAI-1b's rewind is exact on a *full* cache (slot == position). On the *space-optimized ring* it is not: an idle tick's writes wrap around and **alias onto slots that still hold live-window positions**. A naive `rewind` would then leave those slots holding *future* data — corruption.

### 3.2 The fix and its proof
We added an **undo-journal**: before the ring overwrites a slot, it saves the slot's old contents; `rewind` replays the journal in reverse to restore them; `commit` (on a retained action) clears the journal and sets a new baseline. The journal is bounded by min(k, W) per layer per tick — **constant**, independent of how many actions are retained, so it preserves O(1) in both time and space.

- **G-1b-WRAP-NULL (bit-exact + non-vacuous):** we forced a wrap-crossing idle tick and confirmed it **clobbered live-window slots in all 40 SWA layers** (so the test isn't trivially passing), then showed the post-rewind ring is **byte-identical (diffs = 0)** and reproduces identical tokens. The "clobbered = 40" line is the non-vacuity proof: it demonstrates the journal was actually exercised, not bypassed.

### 3.3 The O(1) endurance telemetry (and a hardware lesson)
We re-ran the latency-vs-A sweep through the journal path: ring slope **0.00365 s/action ≈ full-cache 0.00371** — both flat, ~270× under the prefix-grow tax. The journal adds **no asymptotic cost**.

- **The honest caveat we banked:** the *fine-grained* per-tick journal overhead (~1-3% of a tick) turned out to be **below the wall-clock noise floor on this card** — because the RTX 2060 **cannot lock its memory clock** (`nvidia-smi`: "not supported"), and memory-bandwidth-bound decode jitters ±~12%, which swamps the small delta and even produced physically-impossible *negative* taxes. The within-leg slope (the O(1) claim) survives because it's measured inside one leg; the exact tax needs CUDA-event instrumentation (filed). **The lesson — never difference two sequential wall-clock series for sub-10% deltas on this card — is now a standing rule.** This is a good example of the project catching the limits of its own instrument and writing them down rather than reporting a number it can't defend.

---

## 4. KAIROS — the resident cognitive loop (the *agency* axis, KAI-1 / KAI-1c)

### 4.1 What it is
A background kernel daemon that wakes each tick, reads one environment event, and replies with exactly `NO_OP` (stay silent) or `<ACTION>…</ACTION>` (intervene), governed by a salience policy. The whole point is **disciplined silence**: a useful resident agent must do nothing, correctly, almost all the time.

### 4.2 The crucible, on the metal
`run_kairos_metal` wires the decision loop onto the journaled-ring ABI: prefill the system contract, commit (anchor); per tick prefill the event frame and decode; **NO_OP → rewind** to the anchor (cold-evict the tick), **ACTION → commit** (retain it, advance the anchor).

- **Headline (24-event tape, 12B, ring active):** `noop_ok=21, action_ok=3, false_action=0, missed=0, malformed=0, pos_violations=0` — perfect. The three salient ticks produced coherent, context-correct imperatives ("start" for a finished build, "clean" for a full disk, "renew" for an expiring TTL), each committed; every post-action idle tick reverted cleanly to NO_OP.
- **The negative control that proves it's capacity, not plumbing:** the identical harness collapses a 0.6B model into a deterministic corruption attractor (it starts emitting garbage like `NO_克作` and false-fires after a retained action). The 12B holds. So the discipline is a property of model capacity exercised through correct machinery — both halves proven.
- **Why "pos-discipline" is a gate, not just a log line:** by asserting that idle ticks return the position exactly to the anchor and action ticks advance it, the test fails loudly if the rewind/commit math is off by even one — so the semantic pass and the metal correctness are checked simultaneously.

### 4.3 The endurance soak (6h GREEN; the formal ≥24h gate un-pursued by choice)
`run_kairos_soak` loops the deterministic tape with a per-loop re-anchor (bounded state), streams two-tier flushed telemetry, and arms in-process tripwires: CUDA error, any false-action/missed, pos-violation, 3-consecutive malformed, latency (5-consecutive spikes — *consecutive* precisely to tolerate the unlockable memory clock's jitter), VRAM leak, and thermal.

**6h soak GREEN (2026-06-16, hard receipt).** `_run_kairos_soak.bat 6` on the **dedicated local RTX 2060** ran to a clean verdict: `SOAK_EXIT=0`; **351 loops / ~8,400 ticks / 6h01m; 0 false-action, 0 missed, 0 malformed, 0 pos-violation** — salient ticks → ACTION and idle → NO_OP throughout, GPU clocks reset on exit. The journaled-ring metal ran a multi-hour reflex loop **unattended on consumer silicon with zero drift and zero leak** — the strongest endurance receipt to date. The fix that got the uninterrupted run was a **dedicated GPU**: the prior best (6.5h) was *contention*-aborted on the shared desktop's global-free tripwire — a harness/contention issue, not a substrate failure. The **formal ≥24h endurance gate remains un-pursued by operator choice (NOT failed)**: the discipline/arithmetic/crucible legs of G-KAIROS-1 were already functionally passed, and the clean 6h unattended run is the endurance evidence on the record.

### 4.4 KAI-2 — the latent interrupt (CLOSED, BOUNDED)
A resident daemon should be *interruptible*: an event deliverable mid-idle as a compact latent packet rather than a verbose text frame. KAI-2 promotes the X-R1 latent-write into a delivery path, and phase 2 trained a codec to *compress* the event so the injected packet pivots the model in ≈1 step instead of the **44 text-delivery steps** measured in §6.2.

**KAI-2 CLOSED (engine `c5628e4`; lattice contract §6.6 `2675c79`).** Two findings, both kept on the record:

- **Phase-1 latent delivery seam = GREEN / frozen verified asset.** `gemma4_kv_inject` (the residual-entry seam) was proven on the 12B OK_Q4B / RTX 2060: the **EMB control passed 2/2** — a real-token embedding *sequence* pivots a salient event → `<ACTION>` and an idle event → `NO_OP`. This seam is now a frozen, load-bearing asset (it is the same seam KAI-3 and the GNA "EAR" line build on).
- **Phase-2 learned compressed single-event codec `KAI2Codec` = BOUNDED.** The maximally-constrained `t10` packet (k=16, on-manifold cos 0.9913, sharp τ=0.2, held-out `val_KL` plateau 0.9157) **MISSED** the salient pivot (PACKET 1/2). The wall is **sequence-positional**: a fixed-width *static* packet compresses out the per-position directional variance attention routes on. It is **NOT** manifold-distance and **NOT** capacity. No more codec-compression cycles.

The lesson — that a single static packet cannot carry what a per-position *sequence* carries — is exactly what motivated KAI-3 (§4.5).

### 4.5 KAI-3 — the audio-port frame projector (CLOSED GREEN; the bridge into the GNA "EAR" line)
KAI-3 is the **inverse of KAI-2** and the bridge into a *separate-but-related* program: the GNA "EAR" line, which gives the frozen model a real-world audio sense through the Intel NUC "Beast Canyon" GNA 2.0 always-on hardware. KAI-3 is filed under that line — it shares KAI-2's frozen `gemma4_kv_inject` seam, but it is **not** a replacement for KAIROS latent memory (the XBAR axis). The audio-port/GNA work is a deliberate **near-term pivot**; the project will **pivot back to XBAR (KAIROS latent memory)** afterward.

**KAI-3 CLOSED GREEN (engine `e35a227`; lattice contract §7.3 `e826950`).** Instead of compressing an event into one static packet (the KAI-2 wall), KAI-3 injects a **SEQUENCE of N projected frames, 1:1 with positions, no compression** — so the per-position directional variance survives.

- **New engine ABI `gemma4_kv_inject_seq`** — a strict loop over the frozen inject+prefill primitives; **G-KAIROS-3-NULL passed 2/2 byte-identical** to the inline EMB loop (the seam is provably the same primitive, just sequenced).
- **The projector** (`tools/audio_port/{gen_synth_frames,frame_projector,emit_corpus}.py`) is a per-position MLP `640→V_sub` plus an on-manifold binder `softmax(logits/τ)·W_sub` (with `W_sub` = the real embed rows × √H). It is trained with **DENSE PER-POSITION cross-entropy** — the fix for the KAI-2 `t10` sparse-gradient plateau; the pivot is a *consequence*, never the train signal.
- **Done LOCAL / NO CLOUD.** The engine now owns the gemma tokenizer (new `SP_G4_TOK_DUMP` mode), so a cloud G4 for a tiny MLP would be over-provisioning.
- **Numbers.** Synthetic ladder `noise_rel=0.1` (2.5× noise:signal) → held-out per-position top-1 **1.000**, manifold cos **0.9998** (the binder is noise-independent). Real-token train `V_sub=60` → top-1 **0.931**, cos **0.9937**.
- **G-KAIROS-3 metal gate** (`SP_G4_KAI3` manifest) on the resident 12B: **8/8 SEMANTIC pivots** — salient → an event-specific `<ACTION>` ("Restart the build process", "Check disk status and run SMART"), idle → `NO_OP`; `KAI3_GATE_EXIT=0`. Receipts: `_xbar/p2b/kai3_gate.log`, `tools/audio_port/KAI3-LADDER-RESULTS.md` (engine repo).

### 4.6 GNA "EAR" — CLOSED end-to-end ON PHYSICAL SILICON (the real audio sense lands)
The GNA "EAR" line — replacing the synthetic anchor with a real audio front-end and lowering it onto the Intel GNA hardware — is now **CLOSED end-to-end on the physical silicon**, the strongest receipt in the audio program.

- **Real speech → 12B pivot, 7/8 (2026-06-17).** Real TTS speech → log-mel → a GNA-conservative Conv1d encoder + CTC head → `gemma4_kv_inject_seq` → the resident 12B pivots **7/8** (up from 3/7 on the first run). Held-out CTC token recovery climbed **0.44 → 0.868** under a multi-voice bake (924 samples, 2 voices, 400 ep) — the 3/7 ceiling was data-starvation, not architecture, exactly as predicted. All 4 NO_OPs correct; 3/4 ACTIONs correct and coherent; the 1 miss was a conservative ACTION→NO_OP.
- **The quant ladder (OpenVINO 2023.3, GNA 2.0).** ONNX→OV-IR FP32 is **bit-exact** (CPU 0.877 == torch 0.877). GNA default i16 *naive* PTQ **shears** recovery 0.877→0.667 (−0.211, scale-invariant ⇒ real int16 quant loss = the predicted CTC-head shear). NNCF calibrated INT8 on CPU recovers the head (0.860) but its FakeQuantize won't compile on GNA. **POT DefaultQuantization, GNA-native i16 = 0.877 FULL RECOVERY** (== FP32). Two GNA conv constraints fixed at zero cost: padding `1→0` (GNA = VALID only) and the CTC head `33→36` out-channels (GNA needs filters a multiple of 4; the dummy channels are sliced off).
- **GNA_HW on the physical accelerator = 0.877.** Run on the real Intel **GNA 2.0** in the NUC "Beast Canyon" (i9-11900KB, driver `gna_03.05.00.2116`, BIOS-enabled), the front-end scores **0.877 == GNA_SW_EXACT emulation == FP32**. The EAR front-end is **PHYSICALLY REALIZED**. (Native-Windows OpenVINO 2023.3 — WSL2 has no GNA MMIO passthrough.)
- **Receipts/contract.** `CONTRACT-KAIROS-K0-K1.md` §7.4/7.5/7.6; `_xbar/p2b/kai3/G-KAIROS-3-{AUDIO_7of8,GNA-i16_quant_gate,GNA-HW}.log`; engine tooling `tools/audio_port/{ov_gna_score,ov_score_ir,pot_gna_quantize}.py` + `run_gna_hw.bat` + `GNA_HW_BRINGUP.md`.

With the EAR landed on silicon, the audio/GNA near-term pivot is **DONE** and the project **pivots back to XBAR (KAIROS latent memory)** — see §7.

---

## 5. The Memo curator — autonomous Ring-2 recall (the orchestration tier)

### 5.1 What it is
C2 is the **policy that drives the crossbar**. P3 built the substrate (read / write / compress / replay / recall-quality-bounded); C2 is the resident loop that, on each tick, decides whether to search memory, which episode to pull, and hands that episode to the proven `SP_REPLAY` inject seam — all under the same bit-exact-when-off + bounded-deflection discipline.

### 5.2 The episode index — a 256-bit content-address
Episodes are registered in a flat, append-only `registry.jsonl`. Each entry carries a `sig_bits` — a **256-bit LSH hash** of the mean projected global-owner key (`R@K` centroid over the episode). Matching a live cue to an episode is an **integer XOR+popcount against TAU_BITS=168** — reduction-order-immune and hardware-independent (a float cosine near a threshold can flip across reduction orders; an integer popcount cannot).

**Why 256 bits, not 32?** An r-sweep over sign-binarized centroids proved that at r=32, sign binarization **collapses** the ep_wiki separation (bit-gap −1; a noise vector beats the target — the thin margin lives in magnitude, which sign discards). The gap recovers at r≥128, ships at r=256 (bit-gap +19). The claim "dot product IS Hamming distance" is **false as built** (holds only for ±1 vectors, not real-valued projection centroids) — verified by measurement, not accepted from the operator's reframe.

### 5.3 The round-trip loop
Per tick: extract a live query key → hash → Hamming match against registry → if match ≥ TAU_BITS, PROPOSE the episode via `SP_REPLAY` → GATE via `SP_G4_SCORE` deflection < 2% → ACCEPT (promote, keep cache) or REJECT (discard, rerun). The "rerun" is O(context) on the Option A one-shot path; the O(1) bit-exact alternative is #222.

- **G-MEMO-NULL (engine `3ea0587`):** curator off ⇒ PPL **4.6665 bit-identical** to the uncurated baseline (shadow observer fired; empty-registry → NULL → inert). The whole loop is a provable no-op when off.
- **G-MEMO-LOOP (engine `627dfad`):** ACCEPT matched recall **+0.000%** → PROMOTE (the right memory at zero fidelity cost); REJECT zeroed recall **+40,106.6%** → FLAG + DISCARD (the safety valve fires on garbage, not just borderline cases). Both branches proven.

### 5.4 #222 — O(1) bit-exact rewind in the persistent KV ABI
`gemma4_kv_replay` (engine `b4b037a`) injects a stored episode into the **resident** cache at `[dpos, dpos+npos)`. The curator can SPECULATE a recall; on reject, `gemma4_kv_rewind(npos)` undoes it **byte-exactly in O(1)** (full-cache slot==pos inverse). The SWA-ring variant (engine `24071bc`) journal-checkpoints each clobbered ring slot before overwrite; G-222-WRAP GREEN (journal-backed rewind diffs=0). **The local KV substrate is airtight in both regimes.**

---

## 6. Ring-3 — the gist tier (parameter-free neocortex, Path A CLOSED)

### 6.1 What it is
Ring-2 (now closed with C2) is the verbatim hippocampus — bit-exact recall, O(1) evict/rewind. Ring-3 is the **neocortical gist**: superpose many episodes into one bounded store, recall by content address with graceful, bounded, pre-registered loss. The crossbar's first *lossy* tier, and the only one whose gate is irreversible (source eviction happens after promotion).

### 6.2 Architecture — VSA/HRR, parameter-free (Path A)
Store `M = Σ_i (addr_i ⊛ id_i)` (circular convolution = the engine's NTT-over-Z_q algebra). Each `addr_i` is a carrier **seeded by the episode's real C2 256-bit signature** (so a live cue regenerates it without a model call). Recall: unbind with the carrier → cleanup argmax over the id codebook → Ring-2 verbatim verify via #222 (the retrieve-and-verify framing: Ring-3 only shortlists, Ring-2 carries the fidelity).

**Why parameter-free works:** the signed (±1 Rademacher) carrier tracks the ideal unitary carrier closely (recall curves ≈ identical), so the math of large-number superposition holds without training. Path B (the P2.b learned adapter) is deferred unless a future measured need shows the shortlist insufficient.

### 6.3 The four gates
- **R3.1 G-R3-BIND** (engine `23539b7`): N=2 recall@1=1.0 (margins +0.586/+0.568); capacity recall@5≥0.90 to N=64 @ D=1024, graceful degrade past ~D. Caught+fixed: metric bug SNR→margin/z-score at N=2.
- **R3.2 G-R3-LOSS** (engine `aae3131`): consolidation loss is a **step function** — hit +0.000% (verbatim verify is lossless), capacity miss +8.04% (>> 2% gate → caught + O(1)-rewind, never silent corruption). Promotion budget: ≤32 episodes/vector @ D=1024. Latency: 71µs unbind + one Optane ReadFile.
- **R3.3 G-R3-DUALROUTE** (engine `69638cf`): cue→VSA unbind→top-K shortlist→#222 verify scan→land. Three pipes proven: clean hit, decoy scan (rank-1 foreign REJECT+rewind → rank-2 correct ACCEPT), null parity (empty Ring-3 → baseline byte-exact).
- **R3.4 G-R3-NIGHTSHIFT** (engine `a64a916`): idle-loop state machine: SELECT→BIND(shadow copy)→SHADOW-GATE(re-verify every bound ep, crosstalk-safe)→PROMOTE+EVICT(verbatim stays on Optane, tier-demotion not delete)→SEAL. **D=1024/CAP=32 production run:** 40 episodes → **349.8 MB resident KV demoted to Optane, Ring-3 resident index 16.3 KB**. D=128 gate-driven seal proves the seal is the **math** (gate fires before the cap at [10,6,15,8,1] max 15 < 32).

Remaining deferred: the Z_q/NTT engine port of the host-numpy VSA bind/unbind (deployment, exact integer); the G-R3-PROV provenance tag.

---

## 6.1 The organism — EAR→Ring-2 integration (step 1 GREEN)

The **G-XBAR-ORGANISM** integration bridges the audio/GNA "EAR" line into the XBAR memory stack. Step 1 (engine `6600cf4`): a real audio packet (KAI-3 inject_seq path) flows through the conditioned cache (npos=114) and is serialized as an episode in the canonical uniform-512 format [48,114,512] — the same format as ep_wiki, with the clamp fix (12B SWA cache is jagged global 512 / SWA 2048; the episode clamps to global 512). Episode signature separates (self 211/256, margin +79, distinct from ep_wiki and ep_toy). SP_REPLAY=ep_audio loads and injects clean (RT_EXIT=0); the **+1989% deflection is foreign-by-design** (audio KV injected into a wiki context; ~0% is matched-context only — this is a scope-honest figure, not a failure).

The **full organism loop** (driving a raw audio cue → Ring-3 shortlist → #222 verify scan → autonomously land ep_audio in the resident cache) is the next trajectory, gated behind the period-6 rebase correctness tidy-up.

**Period-8 vs period-6 caveat:** the C2/Ring-3 sig pipeline uses PERIOD=8 (L%8==7) as the content-hash layer subset; the 12B's true SWA period is **6** (L%6==5). Separation is robust to the choice — all prior C2/R3 gates stand — and the rebase is a named correctness tidy-up, not a result fix.

---

---

## 7. Latent-space steering (the P2b adapter line)

Parallel to the substrate work, we investigated whether the latent write of §1.2 can be made *general* — learning an adapter that fills cache slots to order rather than transplanting them.

- **Recognition is real but sub-usable so far:** a contrastive-addressing probe reached top-1 0.462 (vs 0.031 chance — ~15× over chance) and top-5 0.77. That says the addressing signal exists and is a *shortlister, not yet a sniper*, which points the design toward a two-stage retrieve-and-verify loop rather than more training epochs.
- **Generation at high compression is dead at k=2** (six forks all convicted) — an honest negative kept on the record. The verdict: the substrate stands regardless of the learned-fill outcome; learned-fill is a policy layer on top, not a foundation.

---

## 6. Why the results can be trusted (the methodology)

This section is the actual moat. The numbers above are only as good as the discipline that produced them.

1. **Bit-exact-when-off / null floor.** The production decode path is never touched. Every "on" result is therefore a controlled delta against a byte-identical baseline, not a comparison between two moving targets.
2. **Pre-registered bounded gates.** When a stage crosses from exact to lossy (sparse, compressed), bit-exactness is impossible by definition — so we *write down the degradation threshold before the code* (e.g. PPL < 2%) and never move it to make a result pass. The 8× router's +0.47% is green against a bar set in advance.
3. **Negative controls and poison.** Retention is proven by *destroying* the live source (poison) and by showing a *worse router misses* (control), not by a bare equality that leakage could fake.
4. **Honest negatives, published.** A faster-but-wrong 34.2 tok/s headline was retired by our own perplexity rule; a 32k needle MISS stayed on the public front page; a small-N "improvement" was caught as a noise illusion when measured on a real corpus. The discipline self-corrects in the open.
5. **Measurement hygiene.** GPU clocks pinned for timing; and when the 2060 turned out unable to pin its *memory* clock, we changed how we read sub-10% deltas rather than trusting the wall clock. We don't difference two sequential noisy series.

A claim in this project comes with the command that produced it and the scope it's valid in. That is what "auditable" means here, and it is the one property a floating-point, text-bus agent stack cannot offer.

---

## 9. The unification — XBAR onto the exact-integer O_K substrate (2026-06-18)

### 9.1 What happened
The XBAR memory tier had been *correct* but running on **generic float carriers** — host numpy FFT for the Ring-3 bind, a float centroid for the C2 signature, a float32 episode store for Ring-2. This session moved it onto the **exact-integer O_K substrate** the rest of the project is built on: Q(√−163), the dual-prime negacyclic CRT-NTT (`core/ntt_crt` + `core/poly_ring`), with frozen primes q1=1073738753, q2=1073732609, M=1152908312643096577. That substrate was **already linked into the engine** — the bind needed **zero new linkage**, because the `gemma4_kv_*` resident cache is pure f32 (the only int8 path is the *weight* gemv, not the cache), so the memory tier was float-decoupled by construction.

### 9.2 The container — what the integer substrate *won*
- **Bind on O_K (Leg A, engine `0019b86`).** The Ring-3 circular-convolution bind, re-carried onto native `sp_pr_mul` / NTT-forward∘pointwise∘inverse: **256/256 bit-identical** to the integer reference (the header exactness contract); ±1 carrier recall **lossless** vs float (recall@1=1.0 to N=16, recall@5=1.0 to N=32 @ deg-512); and — the property only an integer substrate can offer — the superposition vector M is **byte-identical across 8 summation permutations**, where the float M diverges 4.44e-15 (non-associative). Reduction-order immunity is a *correctness* guarantee, not a speed trick.
- **Frobenius integer Ring-2 store (G-R2-FROB, engine `dbe4103`/`d076797`).** Episodes stored as Frobenius-scaled **integer** coords (Theorem-T4 storage form) with a rank-2 error-feedback lattice (coarse a + residual b, real scales). Fidelity: 24-bit reaches relL2 1.2e-7 (sub-ULP, 18% byte-exact) at 0.76× the float store; 16-bit is effectively lossless (relL2 3e-5) at half the bytes. The compression lever is **bit-width** (12b 2.86× / 16b 2.0× / 24b 1.36× vs float32). **Honest scope on the record:** "lossless" here is established by *reconstruction fidelity*, not by the n=42 wiki.tiny PPL gate, which is blind below ~1% (small-N tie-flip) — we explicitly did **not** manufacture a fake +0.000% from it; only the float-exact replay reads a clean baseline-equal PPL.
- **The full organism, native (G-XBAR-ORGANISM-FULL, engine `15e7051`; native bind `1f0f6be`).** Host FFT ripped out of the live loop; D=1024 tiled as a direct sum of two 512-blocks so the CAP=32 capacity gate held. The end-to-end loop ran on **real episodes** (audio EAR + text decoys): C2 256-bit signature separation (audio self 256, decoys 147/129 ≪ TAU_BITS 168) → Ring-3 native integer bind shadow-gate → dualroute audio cue → ep_audio top-1, Hamming verify **accepts audio / rejects text** → Frobenius integer store decoded sub-ULP → SP_REPLAY into the 12B resident cache, checks=5 fails=0. **Continuous audio → discrete integer memory → continuous KV back out, autonomous.** (The cross-modal verify is by *signature*, not text-PPL — audio is foreign to any text scoring context, so the +88.89 PPL is foreign-by-design, on the record.)
- **Period-6 rebase CLOSED (G-PERIOD6-REBASE, engine `d2d7ceb`).** The prior session's named correctness tidy-up is done: the C2/Ring-3 content-hash subset moved from PERIOD=8 (which hashed mostly *non-global* layers) to the true gemma4 SWA period 6 (globals {5,11,17,23,29,35,41,47}). Re-gated GREEN, separation cleaner (decoy 154→129) — and, as predicted, every prior gate stood.

### 9.3 The boundary — what number-theoretic *structure* did **not** win (four honest negatives)
The keystone of the session is that the substrate's value is the *container*, not the *content*. Four attempts to extract structure from the high-entropy payload were each measured-inert and kept on the record:
- **Dirichlet-character carriers (Leg B, engine `d7d96fe`).** Split-prime χ_d carriers *do* lower native mutual coherence and Heegner-order it (random 0.0355 > OK(−67) 0.0153 > OK(−163) 0.0086, the Weil bound) — but recall got **worse** (spiky small-period spectrum = poor self-unbind) and the C2 SimHash was unchanged (random projection washes the coherence out). **Random ±1 stays the carrier.**
- **Möbius-on-M (G-R3-MOBIUS, engine `1e70763`).** Square-free compression of the Ring-3 superposition fails — M is 99.6% dense, divisor-reconstruction error is 1.35× the signal, masking sheds memories. The 6/π² density is real but doesn't transfer to a holographic vector.
- **Entropy-on-codes (G-R2-FROB-ENTROPY, engine `e6d17bb`).** lzma/zlib on the Frobenius residual is dead weight (1.02×) — the int8 residual is incompressible high-entropy. (The earlier "2.56× on dense M" was a leading-zero-byte red-herring.)
- **T2-Möbius-on-weights (G-T2-WEIGHTS, engine `ac76c8e`).** Tested on T2's own object — real gemma-4-12b `embed_tokens` — Möbius puts 43.6% energy on non-square-free (claim ~0%) and reconstructs composite rows *worse than random*. Trained embeddings have no multiplicative index structure (token IDs are BPE merge ranks). For the record: T2 (Möbius) was a *design proposal* in the theory paper, never empirically validated — unlike T4 (Frobenius), validated 6-sig-fig on Gemma3-1B and now operational here.

**The thesis, stated plainly:** unstructured chaos bound inside rigid algebraic order. The integer substrate is an indestructible container (exact bind, exact integer store, reduction-order immunity); the content it carries is high-entropy and resists every number-theoretic structure we tried to impose on it. Wins on the container, never on the content.

### 9.4 NEXT
The host-numpy VSA → native Z_q/NTT port (the long-deferred Ring-3 follow-on) is now **DONE**. The named open frontier is **T4 Frobenius π^k quantization of the 9.4 GB model weights** — the *validated* lever (Frobenius cancellation, per-tensor scale is free), applied to embedding/FFN/attention weights, untouched this session. **Not** Möbius, which failed its own object (§9.3). Then KAIROS post-organism state.

---

## 8. The state of the board

| Axis | Status | Headline receipt |
|---|---|---|
| XBAR latent write (P1) | CLOSED | 15/15 incorporation + 15/15 selectivity; self-null 7/7 bit-identical |
| XBAR ring + spill + page (P3) | CLOSED | bit-exact paged decode under a poisoned live cache |
| O(1) VRAM (C-b.2) | CLOSED | 8k↔16k flat within ~50 MiB |
| Learned router (8×) | CLOSED | +0.47% PPL (oracle −0.08%; frozen +4.17%) |
| NIAH retention (C-c) | CLOSED | needle survives at 10/50/90% depth; frozen-router control MISSES |
| XBAR replay-write (P3.3) | CLOSED GREEN | `SP_REPLAY` `G-P3-SHARED` 3-leg PASS on 12B + E2B: intact bit-identical, zeroed diverges 12/12 |
| XBAR recall quality (P3.4) | CLOSED GREEN | `G-P3-PPL` +1.38% deflection < 2% gate (4.6665→4.7311); n=42 single-chunk caveat |
| O(1) rewind (KAI-1b) | CLOSED | byte-identical 48 layers; 0.0073 vs 0.924 s/action |
| Wrap-aware ring (KAI-1c) | CLOSED | byte-identical across a forced wrap (40 layers clobbered, diffs=0) |
| Journaled-ring O(1) telemetry | CLOSED | ring slope 0.00365 ≈ full 0.00371 s/action |
| Semantic crucible (KAIROS) | CLOSED | 24 ticks perfect: 0 false / 0 missed / 0 drift |
| 6h endurance soak (G-KAIROS-1) | **GREEN** | 351 loops / ~8,400 ticks / 6h01m unattended, 0 false / 0 missed / 0 malformed / 0 pos-violation (≥24h gate un-pursued by choice, not failed) |
| KAI-2 latent interrupt | **CLOSED (BOUNDED)** | Phase-1 seam `gemma4_kv_inject` GREEN (EMB 2/2); Phase-2 static `KAI2Codec` MISSED (sequence-positional wall, not capacity). Engine `c5628e4` |
| KAI-3 audio-port (GNA "EAR" bridge) | **CLOSED GREEN** | `gemma4_kv_inject_seq` (N-frame sequence, no compression); G-KAIROS-3 8/8 semantic pivots on 12B. Engine `e35a227` |
| GNA "EAR" on physical silicon | **CLOSED** | real speech → 12B pivot 7/8 (CTC 0.44→0.868); POT GNA-native i16 = 0.877 full recovery; GNA_HW on Intel GNA 2.0 = 0.877 == emu == FP32 |
| C2 Memo curator (Steps 1–3.1) | **CLOSED GREEN** | G-MEMO-NULL bit-identical; G-MEMO-LOOP ACCEPT +0.000% → PROMOTE / REJECT +40106.6% → DISCARD. Engine `627dfad` |
| C2 resolver discrete bit-collision | **CLOSED GREEN** | 256-bit LSH hash, TAU_BITS=168; r=256 bit-gap +19 (r=32 collapses); reduction-order-immune address. Engine `6dd87b9` |
| #222 O(1) rewind in kv ABI | **CLOSED GREEN** | `gemma4_kv_replay` + `gemma4_kv_rewind` byte-exact E2B+12B (diffs=0); G-222-WRAP GREEN (SWA-ring journal-backed). Engine `24071bc` |
| Ring-3 Path A BIND (R3.1) | **CLOSED GREEN** | recall@1=1.0 to N=32 @ D=1024, margins +0.586/+0.568; ±1 carrier ≈ ideal. Engine `23539b7` |
| Ring-3 consolidation loss (R3.2) | **CLOSED GREEN** | hit +0.000% / miss +8.04% gate-caught; budget ≤32 ep/vector; 71µs unbind. Engine `aae3131` |
| Ring-3 dual-route recall (R3.3) | **CLOSED GREEN** | clean hit + decoy scan + null parity; degrade-safe. Engine `69638cf` |
| Ring-3 NIGHTSHIFT idle loop (R3.4) | **CLOSED GREEN** | 40 ep → 349.8 MB KV demoted to Optane, Ring-3 index 16.3 KB; D=128 gate-driven seal proves seal is the math. Engine `a64a916` |
| G-XBAR-ORGANISM step 1 | **GREEN** | EAR→Ring-2 write seam: ep_audio [48,114,512] uniform-512, sig self 211/256 margin +79, SP_REPLAY loads+injects clean. Engine `6600cf4` |
| Ring-3 bind on O_K (Leg A) | **CLOSED GREEN** | native CRT-NTT bind 256/256 bit-identical; ±1 carrier lossless (recall@1=1.0 to N=16); M byte-identical across 8 summation orders (float diverges 4.44e-15). Engine `0019b86` |
| Dirichlet-character carriers (Leg B) | **HONEST NEGATIVE** | χ_d carriers Heegner-order coherence (0.0355>0.0153>0.0086) but recall WORSE + SimHash unchanged — operationally inert; random ±1 stays the carrier. Engine `d7d96fe` |
| Ring-3 organism native (FFT ripped out) | **CLOSED GREEN** | live loop on native `sp_pr_mul`; D=1024 = direct sum of two 512-blocks; dualroute + nightshift GREEN, CAP=32 held. Engine `1f0f6be` |
| Frobenius integer Ring-2 store (T4 form) | **CLOSED GREEN** | rank-2 integer coords; 24b relL2 1.2e-7 sub-ULP @ 0.76× store; bit-width = the lever (12b 2.86×/16b 2.0×). Fidelity-proven, not n=42-PPL. Engine `dbe4103`/`d076797` |
| Frobenius entropy coding | **NEGATIVE** | lzma/zlib on the residual = dead weight (1.02×); int8 residual incompressible. Engine `e6d17bb` |
| Möbius compression of Ring-3 M | **NEGATIVE** | M is 99.6% dense; divisor-recon error 1.35× signal; masking sheds memories. Engine `1e70763` |
| Full organism loop (native, real episodes) | **CLOSED GREEN** | audio→discrete integer memory→KV out, autonomous; C2 sig accepts audio/rejects text; SP_REPLAY checks=5 fails=0. Engine `15e7051` |
| T2 Möbius on real 12b weights | **NEGATIVE (T2's own object)** | 43.6% energy non-square-free (claim ~0%); composite-row recon worse than random — trained embeddings have no multiplicative index structure. Engine `ac76c8e` |
| Period-6 rebase (correctness tidy-up) | **CLOSED GREEN** | content-hash 8→6 (true SWA period); separation cleaner (decoy 154→129); all prior gates stand. Engine `d2d7ceb` |

**The whole XBAR memory stack is structurally proven end-to-end on the 12B within a 12 GB footprint.** The substrate reads, writes, compresses to O(1), retrieves under poison, replays bit-exactly, and recalls without breaking perplexity (P3). The curator indexes (registry), addresses (256-bit hash), selects (integer Hamming), is inert when off, and on metal promotes the matched recall at zero deflection cost and discards the corrupted one (C2). The neocortical gist tier superimposes many episodes into a bounded vector, recall@1 lossless to N=32, misses gate-caught, idle-loop seals 349.8 MB of resident KV down to a 16.3 KB Ring-3 index (Ring-3 Path A). The EAR→Ring-2 seam is proven for audio episodes, with a foreign-by-design deflection caveat correctly on the record. Endurance: 6h soak GREEN (formal ≥24h gate un-pursued by operator choice, not failed). GNA "EAR" CLOSED on physical silicon (§4.6). **And as of 2026-06-18 the whole memory tier is UNIFIED onto the exact-integer O_K substrate (§9): native CRT-NTT bind (256/256 bit-identical, reduction-order-immune), Frobenius integer Ring-2 store (sub-ULP at 24b), the full organism loop running native on real episodes, and the period-6 rebase CLOSED — bounded by four honest negatives that establish the boundary thesis (the substrate wins on the algebraic container, never on the high-entropy content). **NEXT = T4 Frobenius π^k quantization of the 9.4 GB model weights** (the validated lever; NOT Möbius, which failed its own object), then KAIROS post-organism state.** Standing hygiene queued: cudaEvent journal-tax, `gemma4_kv_decode` first-token boundary, compact-slab globals wrap-rewind, P3.4 larger-N multi-chunk hardening run.

---

## 8. Hardware reality (so numbers are read correctly)

- **Host GPU:** RTX 2060, **12 GB** VRAM, sm_75. Core clock locks for timing; **the memory clock does not lock** (vendor-unsupported), so bandwidth-bound decode has an irreducible ±~12% wall-clock jitter floor. Use within-config slopes or CUDA-event timing for sub-10% deltas, never a difference of two sequential wall-clock series.
- **Model:** Gemma-3-12B, QAT 4-bit (the "B1" / OK_Q4B artifact), the only mathematically-intact sub-5-bit Gemma-4-12B we could produce (paper 06).
- **Scope of claims:** the **0.6B** model is used for the memory-ladder and control experiments; the **12B** carries the XBAR and KAIROS headline results. Any "one model, one host" boilerplate in older docs is stale and should read "0.6B for the ladder, 12B for XBAR/KAIROS."

---

*Pointers: the canonical proven-record is `papers/PPT-LAT-STATE.md`; the active contracts are `papers/CONTRACT-KAIROS-K0-K1.md` (KAI-0/1, §5.5-5.8 are freshest), `papers/CONTRACT-XBAR-P3-ring-on-exec.md`, and `papers/RFC-XBAR-auditable-latent-crossbar.md`; the public receipts ledger is in the `Position_Is_Arithmetic` repo (`LEDGER.md`).*
