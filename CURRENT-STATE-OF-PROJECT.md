# Shannon-Prime — Current State of the Project

**As of 2026-06-14.** This is the human-readable map of where the project stands: what we built, the numbers that matter, the tests we used to prove each claim, *why* those tests are the right ones, and why the results can be trusted. It is written to be read top-to-bottom by a person, and to orient an agent in one pass. Detailed, citable records live in the contracts and `PPT-LAT-STATE.md`; this document is the synthesis, not the ledger.

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

### 4.3 The endurance soak (in-flight — no verdict yet)
`run_kairos_soak` loops the deterministic tape with a per-loop re-anchor (bounded state), streams two-tier flushed telemetry, and arms in-process tripwires: CUDA error, any false-action/missed, pos-violation, 3-consecutive malformed, latency (5-consecutive spikes — *consecutive* precisely to tolerate the unlockable memory clock's jitter), VRAM leak, and thermal. A 3-loop smoke passed clean; the full **≥24h run is currently executing** (~36,700 ticks). **Per our own discipline we do not call a verdict from a mid-run log** — at the time of writing it is 2,000+ ticks in with zero faults, with one honest watch item: a slow VRAM creep (+59 MiB by loop 84) that the VRAM tripwire will catch cleanly if it's a real per-loop leak rather than cross-process noise. Three possible outcomes, all informative: a clean 24h GREEN, a tripwire abort that *found* an endurance bug, or (unlikely) a semantic surprise.

---

## 5. Latent-space steering (the P2b adapter line)

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

## 7. The state of the board

| Axis | Status | Headline receipt |
|---|---|---|
| XBAR latent write (P1) | CLOSED | 15/15 incorporation + 15/15 selectivity; self-null 7/7 bit-identical |
| XBAR ring + spill + page (P3) | CLOSED | bit-exact paged decode under a poisoned live cache |
| O(1) VRAM (C-b.2) | CLOSED | 8k↔16k flat within ~50 MiB |
| Learned router (8×) | CLOSED | +0.47% PPL (oracle −0.08%; frozen +4.17%) |
| NIAH retention (C-c) | CLOSED | needle survives at 10/50/90% depth; frozen-router control MISSES |
| O(1) rewind (KAI-1b) | CLOSED | byte-identical 48 layers; 0.0073 vs 0.924 s/action |
| Wrap-aware ring (KAI-1c) | CLOSED | byte-identical across a forced wrap (40 layers clobbered, diffs=0) |
| Journaled-ring O(1) telemetry | CLOSED | ring slope 0.00365 ≈ full 0.00371 s/action |
| Semantic crucible (KAIROS) | CLOSED | 24 ticks perfect: 0 false / 0 missed / 0 drift |
| ≥24h endurance soak | **IN-FLIGHT** | running; no verdict from a mid-run log |

**The crossbar substrate — space ⊗ time ⊗ cognition — is structurally complete on a 12B within a 12 GB footprint.** The remaining gates are the endurance soak (running) and a short list of hygiene follow-ons (exact journal-tax via CUDA events; the `gemma4_kv_decode` first-token boundary reconcile; compact-slab globals wrap-rewind).

---

## 8. Hardware reality (so numbers are read correctly)

- **Host GPU:** RTX 2060, **12 GB** VRAM, sm_75. Core clock locks for timing; **the memory clock does not lock** (vendor-unsupported), so bandwidth-bound decode has an irreducible ±~12% wall-clock jitter floor. Use within-config slopes or CUDA-event timing for sub-10% deltas, never a difference of two sequential wall-clock series.
- **Model:** Gemma-3-12B, QAT 4-bit (the "B1" / OK_Q4B artifact), the only mathematically-intact sub-5-bit Gemma-4-12B we could produce (paper 06).
- **Scope of claims:** the **0.6B** model is used for the memory-ladder and control experiments; the **12B** carries the XBAR and KAIROS headline results. Any "one model, one host" boilerplate in older docs is stale and should read "0.6B for the ladder, 12B for XBAR/KAIROS."

---

*Pointers: the canonical proven-record is `papers/PPT-LAT-STATE.md`; the active contracts are `papers/CONTRACT-KAIROS-K0-K1.md` (KAI-0/1, §5.5-5.8 are freshest), `papers/CONTRACT-XBAR-P3-ring-on-exec.md`, and `papers/RFC-XBAR-auditable-latent-crossbar.md`; the public receipts ledger is in the `Position_Is_Arithmetic` repo (`LEDGER.md`).*
