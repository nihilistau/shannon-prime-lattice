# Shannon-Prime — Current State of the Project

**As of 2026-06-16 (KAI-2 CLOSED bounded, KAI-3 CLOSED GREEN, GNA Stage 2 next).** This is the human-readable map of where the project stands: what we built, the numbers that matter, the tests we used to prove each claim, *why* those tests are the right ones, and why the results can be trusted. It is written to be read top-to-bottom by a person, and to orient an agent in one pass. Detailed, citable records live in the contracts and `PPT-LAT-STATE.md`; this document is the synthesis, not the ledger.

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

### 4.6 GNA Stage 2 — the next milestone (the real "EAR")
With the KAI-3 delivery + projection architecture **LOCKED**, the next step (task **#154**) is **GNA Stage 2**: replace the synthetic anchor matrix `A` with the real **GNA/CNN audio front-end** — live audio/telemetry → 40 ms / 640-float / 16 kHz frames; `audio_token_id = 258881` — so the model gets an always-on, real-world audio sense. This is the GNA "EAR" line proper; KAIROS latent memory (XBAR) resumes after it.

---

## 5. Latent-space steering (the P2b adapter line)

Parallel to the substrate work, we investigated whether the latent write of §1.2 can be made *general* — learning an adapter that fills cache slots 