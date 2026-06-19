---
type: roadmap
title: "ROADMAP — STAGE KAIROS (καιρός): the Shannon-Prime Kernel"
description: "Status: DESIGN (stage registered 2026-06-10; no gate has run; nothing here is claimed)."
tags: [roadmap, kairos]
timestamp: 2026-06-17T21:25:38Z
resource: shannon-prime-lattice/papers/ROADMAP-KAIROS.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# ROADMAP — STAGE KAIROS (καιρός): the Shannon-Prime Kernel

**Status:** DESIGN (stage registered 2026-06-10; no gate has run; nothing here is claimed).
**Document role:** the self-contained roadmap for the post-XBAR stage — escaping the turn-based
execution model. Deliberately a SEPARATE file set (this roadmap + `CONTRACT-KAIROS-*.md`) so the
live XBAR campaign docs stay unpolluted. This stage **does not start until the current P2.b/P3
arc closes**; until then it is a plan with pre-registered gates, not work.
**Parents:** PPT-LAT-STATE §5.07 (stage taxonomy) · RFC-XBAR (the memory substrate this runs on)
· the heterogeneous-SoC manifesto · CosySim/NEXUS/Project X (the operator's prior harness corpus —
the REFERENCE, per lead-with-the-reference discipline).
**Authors:** Knack + Claude + Gemini (Gemini's three-architecture sketch critiqued and extended in §3).

---

## 0. The name

**Chronos vs Kairos.** Greek has two words for time. *Chronos* is sequential time — the tape,
the transcript, the turn. *Kairos* is the opportune moment — event-time, the moment demanding
action. Every chat-era system lives in chronos: a linear, append-only token tape that user and
model take turns extending. This stage's thesis is that our substrate dissolves that tape, and
the system that replaces it acts in kairos — when events warrant, not when a turn arrives.

The built artifact is the **sp-kernel**: the event loop + scheduler + driver layer that turns
the proven Exec/Memo/ring stack from a callable into a resident.

**Taxonomy placement:** Kairos slots after Eta/Omicron as the *time/agency axis*; **Holon ⬢⃝
remains the endgame** on the *space/distribution axis* (one Garner formula, L1→QUIC). They are
orthogonal and compose: the bonded Holon mesh ultimately RUNS on the Kairos loop. Kairos is not
folded into Holon precisely because conflating "always-on agency" with "distributed compute"
would let each blur the other's gates.

---

## 1. The question, answered: harness or kernel?

**Verdict: the XBAR three-ring system is not a harness. It is the memory subsystem and syscall
layer of a kernel that does not have a scheduler yet.**

The distinction that matters is not "does scaffolding exist" — scaffolding always exists; an OS
kernel is itself code. The distinction is **where the state lives and what the unit of execution
is**:

- A **harness** keeps the durable state OUTSIDE the model as text, and re-enters it through the
  tokenizer every call. The unit of execution is the turn because the model's internal state
  (the KV cache) *dies between calls*. Everything a harness does — re-prompting, RAG, recaps,
  summarize-when-long, interceptor context-stuffing — is compensation for that death. CosySim's
  36-interceptor pre-call pipeline is the most evolved form of this compensation we have ever
  examined: priority-ordered prompt hydration, because prompt hydration is all a stateless model
  permits.
- A **kernel** owns persistent process state, schedules execution against events, and mediates
  I/O. The §2 inventory shows we have already built, and *gated*, the load-bearing kernel
  components — for memory. What does not exist is the scheduler (the event loop), the driver
  layer (sensors/actuators), and the process/permission model. That is this stage.

So: today, wrapped in NEXUS/PM2/SSE, the system would still be harnessed — Gemini is right. But
the reason it can BECOME a kernel while no fp/API stack can is specific and technical, and it is
ours: **the turn is a memory artifact, not a scheduling artifact, and we changed the memory.**

## 2. Why the turn dissolves on THIS substrate (the geometric/arithmetic escape)

The operator asked whether the escape can be geometric/arithmetic rather than scaffolding. Yes —
four primitives we have already gated are exactly the four things that were missing, and each
maps to a classic kernel mechanism:

| Kernel mechanism | Classic LLM blocker | The SP primitive that removes it | Receipt |
|---|---|---|---|
| **Persistent process state** | KV cache dies between calls; state must round-trip through text | Episode persistence + `SP_REPLAY` (post-RoPE K/V resurrected bit-exact); sessions clone/rewind | C1L.0b 34/34; T8 |
| **Interrupt delivery** | Context is an append-only tape; you cannot insert an event "now" | **Position is arithmetic**: a ring entry is (L, pos, K, V) at exact coordinates; the cache is random-access, and a foreign write steers generation with NO tokens | **X-R1** (15/15 incorporation, 15/15 selectivity — the latent interrupt is not a design, it is a measured result) |
| **Memory hierarchy / MMU** | One flat context window; cost O(context) per step | Ring 1/2/2′/3 + ±1 router recall: the decode window stays small, the past is recalled by CONTENT, not by positional contiguity | C2.1/C2.2 gates; 910× @32k |
| **Cheap speculation & rollback** | Generation is irreversible; exploring futures costs full re-decode | MTP draft→verify→**byte-exact accept** + O(1) watermark rollback = branch prediction with transactional rewind | T8 (engine 145bf43) |

The *geometric* statement: chronos-systems model history as a **line** (a growing 1-D token
sequence; turns are how two writers share a line). Our substrate models history as an
**addressable lattice of minted coordinates** — written at exact (layer, position) addresses,
recalled by content, evicted, consolidated, replayed. Two writers (or ten sensors) do not need
turns to share a lattice; they need addresses and an arbiter. We have addresses (position
arithmetic + RoPE-phase-exact minting) and an arbiter (the curator's propose→gate→promote/rewind).

The *arithmetic* statement: an always-on system is viable iff attention-to-the-world costs
~nothing when nothing happens, and a step costs O(event), not O(history). Both hold here and
nowhere in the API world: (a) the always-on tier is NOT the 12B — it is the GNA (milliwatts,
Stage Omicron's literal design purpose: "never dominates, never sleeps") feeding a CPU router
(±1 projections / a finetuned tiny router), with the Exec woken on salience — a **hierarchical
tick**, hardware→router→Exec; (b) with persistent KV + ring recall, the marginal cost of an
event is a forward over the DELTA at a minted position, not a re-prefill of the transcript.
Tick cost O(Δ) is what makes kairos-time affordable; only persistent-KV systems have it.

**The "ideas that were waiting for our system" (the operator's direct question):** each
known turnless paradigm was blocked on a primitive we now hold. Full-duplex models (Moshi-class
dual-stream audio LMs — turnless by construction) need cheap persistent parallel streams →
our CRT modality lanes + rings. Interrupt-driven context editing needs a random-access,
phase-correct cache → X-R1. Speculative execution of likely futures during idle needs O(1)
rollback → T8. Always-on sensing needs a milliwatt front-end → GNA + rm_cnn4a kit. Idle-time
self-improvement needs an UNGAMEABLE scorer → our receipts/gates (see §4, the one place the
reference corpus consistently fails). None of these required new theory; they required this
substrate.

## 3. Gemini's three architectures — adopted, with corrections on the record

Gemini proposed: (1) the asynchronous Tick (game-engine model), (2) Context Interleaving
(hardware-interrupt model), (3) the proactive Inner Monologue (idle-loop model). All three are
directionally right and all three are *scheduling* answers. Corrections and sharpenings:

1. **Tick — adopted, but hierarchical and O(Δ).** A flat 1–5 Hz tick of a 12B emitting `[NO_OP]`
   is an arithmetic non-starter on a 2060 (and CosySim's own operating points agree: its agent
   loop runs at 8 s, its NPC scheduler at 60 s, on small models — measured reference, §5). The
   sp-kernel tick is tiered: **GNA/sensor tier (always-on, mW) → router tier (CPU, ~1 Hz-ish,
   tiny model / ±1 projection salience score) → Exec tier (interrupt-woken only)**. And a tick
   that does reach the Exec appends an event frame to a PERSISTENT session — never re-feeds the
   transcript. NO_OP discipline is gated, not assumed (G-KAIROS-1 below): an it-tuned model was
   RLHF'd to always answer; whether it can reliably shut up is an open empirical question and a
   named falsification risk.
2. **Context interleaving — this is not a proposal for us; it is X-R1 with the receipts.** The
   correction is the framing: Gemini's "eternal rolling document" re-imports the tape. No
   eternal document — events are minted into ring coordinates and the window stays small; the
   long past is Ring 2/3 recall. The second correction is the law: nothing enters the cache
   that does not honor the geometry (RFC §3 rule 4), and on THIS substrate an interrupt packet
   has a natural ABI — **k≈2 adapter pseudo-tokens (P2.b: the interrupt payload format, already
   trained for selectable recall) or a Spinor block (63 B + 0xA5 = one cache line = manifesto
   trick #9)**. The sensor encoder is the P2.b recipe with the source swapped (S3) — the audio
   lane was always this.
3. **Inner monologue — adopted as NIGHTSHIFT, REJECTED as free-running generation.** "The model
   is essentially always generating" is how you get a confabulating daemon: RFC §4's honest
   negative says injected-memory-as-realization and confident-hallucination are the same event,
   and a self-loop amplifies exactly that. The idle loop must be the **gated curator**:
   propose→gate→promote/rewind with receipts, episodes consolidated under G-R3-LOSS, plus
   bounded, *pre-registered* idle jobs (consolidation, router retraining, eval sweeps — the
   NIGHTSHIFT/N1 design, scheduler-owned). `<eos>` = yield, yes — but yield TO THE SCHEDULER,
   not to an unsupervised monologue. Idle compute runs jobs with kill conditions, not vibes.

One more correction that matters operationally: "you own the silicon, so no API physics" is
half-true. The binding local physics is **one 12 GB card + 32 GB RAM**: Exec-resident (~9.4 GB)
+ consolidation + any finetune job share it. The kernel therefore needs a resource manager
(VRAM-aware model TTL — NEXUS's reaper pattern, tuned properly) and the proven cloud-burst lane
(RunPod runbook) as a scheduler tier, from day one.

## 4. The reference corpus — what CosySim/NEXUS/Project X teach (adopt / adapt / reject)

Six months of the operator's harness engineering = our Stage-0 reference (lead-with-the-
reference; anti-contamination applies: we import LESSONS and patterns, never code, and the
sp-kernel is built on the SP substrate from scratch). Forensics receipts: swarm dossiers
2026-06-10 (agent_loop.py 8 s tick + batch inference + 200-entry log bound; npc_scheduler 60 s,
3 NPCs/tick, small-profile; scheduler_daemon 60 s poll + JSON state persistence + idempotent
callbacks; kill_switch threshold 0.3 / 2 retries / temperature decay; token-ahead pre-warm;
online evaluator auto-promote **without holdout**).

**ADOPT (pattern, rebuilt tight):**
- **Tiered task priorities** (REALTIME / INTERACTIVE / BACKGROUND / BATCH) — maps 1:1 to
  interrupt / converse / NIGHTSHIFT / training.
- **Scheduler-daemon shape**: 60 s poll, schedule strings, persisted task state, idempotent
  zero-arg callbacks returning dicts. (= NIGHTSHIFT's schtasks discipline, matured.)
- **Process supervision** (PM2 / ecosystem file) + health endpoints on every service.
- **Kill-switch + stream-watcher**: rule-based output guards DURING generation (cheap), with
  retry-decay. Our twin already exists at the memory layer (poison gate); Kairos adds it at the
  action layer.
- **Agent registry with tiered access** — closes the RFC §8 "permissions" gap before
  multi-writer rings exist. NEXUS's readonly/worker/expert/system/admin tiering is the shape.
- **Telemetry→dataset→finetune→A/B→promote flywheel** (router models) — adopt the LOOP, fix the
  scorer (below).
- **Operator inbox** (off-turn directive intake) — the human's interrupt channel, same ABI as a
  sensor.

**ADAPT (right idea, wrong layer):**
- **Nexus-first tiered query routing** (Q&A cache → vector → FTS → … → LLM, auto-store-back) is
  a LEXICAL ring hierarchy — Nexus is, structurally, a Ring 3 built in text space. Keep it as
  the kernel's *filesystem* (text knowledge, rules, receipts, sessions) coexisting with the
  latent rings (the *page cache*). The auto-store-back behavior = lexical consolidation;
  gate it like everything else.
- **Interceptor pipeline** → the receipts/gate discipline applied at the prompt boundary. We
  keep a THIN version for the lexical channel, but its main job (context hydration) is replaced
  by ring recall.
- **Speculative decoding** (quickborn server, draft profiles) → fold into the SP MTP/T8 lane.

**REJECT (with reasons on the record):**
- **Inline tag side-channel** (`[MOOD:x]`, `[STAT:±]` parsed from the text stream) — the model
  signaling its own state through magic strings in its output is the detokenize/retokenize loss
  XBAR exists to delete. State flows through the latent/receipt channel, not through prose.
- **Prompt-stuffing as the primary context mechanism** (36 interceptors appending to
  system_prompt) — replaced by recall; what survives is the *ordering/priority* lesson.
- **Ungated auto-promotion**: the online evaluator promotes a fine-tuned model on threshold
  crossing with NO holdout — the gameable-scorer anti-pattern (the same critique we filed
  against RHO's self-preference). The Kairos flywheel promotes ONLY on a held-out, receipts-
  backed gate (the capacity-arm discipline: pre-registered matrix, ≥3 seeds, no verdict from a
  partial log).
- **Cookie-jar cloud lanes** (NLM batchexecute, account pools) as kernel dependencies — optional
  accessories at most; the kernel must be sovereign-local (the gold-instrument lesson applied to
  infrastructure).
- **Python-everything** as the substrate — the daemon/QUIC/C lane is ours.

**Project X** (production Android+Windows assistant: macro detection loop, HA integration, tool
pipeline, health checks) is the closest thing to a deployed sp-kernel v0 in the corpus — its
event-audit + thread-pool/asyncio coordination patterns and its 12-tool actuator surface are
the driver-layer reference. **quickborn** (C:\Files\MCP\shannon-prime-lmstudio-server-quickborn)
shows an SP-flavored MCP serving lane already exists and folds in later as a kernel surface.

## 5. The phases (each gated; falsification pre-stated; cheap substrate first)

Discipline carried over verbatim: bit-exact when off (the kernel is a FLAG around the proven
stack; loop off = today's daemon, byte-identical) · no number without a command · telemetry-
then-pin · no silent gate revision · honest negatives stay attached · qwen3-CPU-first for
mechanism proofs, Exec/CUDA for deployment gates (the C1-lite lesson) · contracts per phase.

| Phase | What | Gate (its own metric) | Falsification (pre-stated) |
|---|---|---|---|
| **KAI-0 — reference extraction** | The CosySim/NEXUS/Project X pattern catalog with file:line receipts (§4; first pass DONE 2026-06-10, swarm dossiers). Deliverable: this §4 + the contract's Stage-0 record. | catalog complete; adopt/adapt/reject ratified by operator | n/a (survey) |
| **KAI-1 — heartbeat null** | Minimal tick loop around the existing qwen3 daemon: scheduler ticks at fixed Hz with environment-delta frames appended to a PERSISTENT session; idle frames pruned by the C1-lite cold-evict (idle must not grow state). | **G-KAIROS-1**: against a scripted event tape — false-action rate (acted on nothing) and missed-event rate (slept through salience) both under pinned thresholds (telemetry-then-pin on run 1); **loop-off = bit-exact daemon**; 24 h soak: flat RSS, zero leaks, full receipts | if the model cannot hold NO_OP discipline at ANY usable threshold (action spam), the flat tick is DEAD → interrupt-only architecture (KAI-2 becomes the front door) and that finding ships as the honest negative |
| **KAI-2 — the latent interrupt** | Event packets injected mid-decode/mid-idle via the proven seams (SP_XBAR_EMB pseudo-tokens; cache splice for KV-class events): the X-R1 mechanism promoted from probe to delivery path. A/B: same event as (a) latent packet vs (b) text appended next tick. | **G-KAIROS-2**: incorporation latency (steps-to-behavioral-pivot, rank telemetry — the X-R1 instrument reused) and selectivity vs the text-delivery baseline; G0-style self-injection null bit-exact | if latent delivery is not faster/cleaner than text delivery, the interrupt thesis on the cheap substrate is falsified → re-test on Exec before any retreat |
| **KAI-3 — yield & the idle loop** | `<eos>`→yield-to-scheduler; idle compute runs NIGHTSHIFT consolidation + pre-registered jobs; a KAI-2 interrupt PREEMPTS idle work (rewind-safe via clone/rewind). | **G-KAIROS-3**: unattended multi-hour run — net-positive gated promotions, zero canonical corruption (the N1 gate inside the loop), preemption-latency measured, kill-switch fires on seeded runaway | a seeded runaway that the kill layer does NOT catch halts the phase (safety gate is load-bearing) |
| **KAI-4 — drivers** | Sensor/actuator layer, one driver at a time: ears (GNA VAD/mel front-end → event packets — Omicron's near-term track, kit in hand), Home Assistant actuator surface (allow-listed, cooldown/budgeted, receipted — CosySim's skill governance pattern at the action layer), TTS out; webcam later. | **G-KAIROS-4** per driver: end-to-end sensory→decision→action demo with full receipts; actuator null (allow-list empty = provably no side effects) | any actuator action without a receipt = phase halt |
| **KAI-5 — scheduler + registry + flywheel** | Priority classes wired end-to-end; agent registry + tiered permissions on ring/actuator writes (closes RFC §8 gap); telemetry→finetune→A/B with HELD-OUT receipted promotion (fixing the reference's gameable scorer); VRAM resource manager + cloud-burst tier. | **G-KAIROS-5**: a BACKGROUND job provably never starves a REALTIME interrupt (latency budget held under load); one full flywheel cycle promotes a router model through a held-out gate | promotion that cannot beat holdout = no promotion (that outcome is valid and logged) |
| **KAI-6 — the seeding question** | The operator's open question, run as an experiment, not settled by opinion: same kernel, arms = {unseeded, goal-seeded, schedule-seeded}, fixed unattended windows, measure action coherence/usefulness/drift (instruments pinned in the contract before spend). | **G-KAIROS-6**: pre-registered matrix decides how much direction the resident agent needs | all arms incoherent → the autonomy layer needs the trained-curator generation (C2/Memo v1) before residency; that verdict gates, not embarrasses |

Sequencing constraint: KAI-1/2/3 run on the qwen3 CPU substrate (bit-exact, cheap, the C1-lite
pattern); Exec-grade deployment of each gate repeats on the 12B AFTER P3 (ring-on-gemma4-CUDA)
closes — P3 and #115's text-in are the prerequisites that make the Exec residency real.

## 6. Risk register (owner-gate per item, started now)

| Risk | Held where |
|---|---|
| Always-on GPU cost (flat tick burns the card) | hierarchical tick (GNA→router→Exec); G-KAIROS-1 cost telemetry; VRAM TTL manager |
| Self-loop drift/confabulation (the §4 negative, amplified by residency) | idle loop = GATED curator only; no free-running monologue; G-KAIROS-3 corruption gate |
| RLHF'd-to-answer prior breaks NO_OP discipline | named falsification of KAI-1; fallback = interrupt-only; finetune lane exists if needed |
| Actuators = real-world side effects | allow-list + budget + cooldown + receipt per action; empty-allow-list null; operator inbox as override channel |
| Always-on sensors widen the §6.2 latent attack surface | every sensor packet is a PROPOSAL through Ring 2′ gates, never a direct canonical write — the kernel is the first deployment of "gated latent state" as defense |
| Gameable self-improvement (reference corpus's repeated failure) | held-out receipted promotion only; the capacity-arm discipline is the template |
| One-box resource contention (12 GB / 32 GB) | resource manager + priority preemption + cloud-burst tier (RunPod runbook) |
| Scope creep into the live XBAR campaign | this stage DOES NOT START until P2.b/P3 close; separate doc set; any cross-edit needs a contract amendment |

## 7. Doc map for this stage

- This file — the stage thesis + phase plan (the *forward* doc).
- `CONTRACT-KAIROS-K0-K1.md` — Stage-0 reference record + the first two gates (the only contract
  written now; later phases get contracts when they open, per standing practice).
- Run records land in the contract; PROVEN results land in PPT-LAT-STATE (one line each);
  public claims, if any ever, go through Position_Is_Arithmetic LEDGER like everything else.
- Terminology added by this stage (keep distinct, do not collapse): **Kairos** (the stage) ·
  **sp-kernel** (the artifact) · **tick tiers** (GNA/router/Exec) · **event packet** (the
  pseudo-token/Spinor interrupt ABI) · **yield** (eos→scheduler) · **driver** (sensor/actuator
  module). Everything else reuses existing names (NIGHTSHIFT, rings, curator, Exec/Memo).

---
**KAI-1 CLOSED (2026-06-14):** control-plane mechanism proven on qwen3-0.6B (cold-evict + salience policy + O(Δ)); production cognition+stability proven on gemma4-12B (perfect 24-tick crucible, tick-5 post-action reversion). See CONTRACT-KAIROS-K0-K1.md §4. Prefix-grow architecture + 0.6B-vs-12B cognitive threshold documented. ≥24h soak = pending operational run.


**KAI-1b METAL EVICTION CLOSED (2026-06-14, engine 0bb94f1, contract §5.5):** the cold-evict dropped from the host token-array hack to the XBAR tensor layer. Persistent-KV ABI `gemma4_kv_open/prefill/decode/rewind/pos/snapshot/close` (cuda_forward.cu; `gemma4_decode_cuda` left byte-untouched = null floor for every Physics-Phase gate). **G-1b-REWIND-NULL GREEN**: idle-tick+`rewind(Δ)` ⇒ [0,anchor) byte-identical across 48 owner layers (16.5 MB, diffs=0) + EQUIV gen-reproduce. **O(actions)→O(1) telemetry**: idle-tick latency vs retained-action count A — prefix-grow slope 0.924 s/action vs metal 0.0073 (127× shallower), grow/metal 16.7× @ A=16. The crossbar time-axis is now plugged into the ring pointer. Scope: full-cache rewind (SWA via windowed attn); ring/slab wrap-aware rewind + full semantic run_kairos_metal loop = follow-ons.


**G-KAIROS-1 6h SOAK GREEN (2026-06-16, contract §5.9):** `_run_kairos_soak.bat 6` on the DEDICATED local RTX 2060 — `SOAK_EXIT=0`; 351 loops / ~8,400 ticks / 6h01m; 0 false / 0 missed / 0 malformed / 0 pos-violation; salient→ACTION, idle→NO_OP throughout; clocks reset on exit. The journaled-ring metal ran a multi-hour reflex loop unattended on consumer silicon with zero drift/leak (the strongest endurance receipt to date). Dedicated GPU fixed the contention false-aborts the shared desktop hit (prior best 6.5h = contention-aborted, not a substrate failure). The **formal ≥24h gate is un-pursued by operator choice (NOT failed)** — the §5 phase KAI-1 legs were already PASSED.

**KAI-2 phase-2 CLOUD PIPELINE GREEN; G-KAIROS-2 gate PENDING (2026-06-16, contract §6.4):** the Colab-G4 lane runs the codec distillation end-to-end on the real bf16 `google/gemma-4-12B` — transformers-HEAD loaded the new `gemma4_unified` arch (no parser crash), the `inputs_embeds` inject seam ran the distillation, the single-linear KAI2Codec (640→3840·k) trained via forward-KL distill from the 12B text teacher, exported 8 packets + ckpt (10 files) to HF `KnackAU/xbar-p2b-run/results_kai2/kai2_k4/`, `STATUS="DONE rc=0"`. **CAVEAT: rc=0 = the distillation LOOP completed; it does NOT prove the packet pivots the model — per-epoch KL was on the ephemeral VM and is gone, codec quality UNVERIFIED. NOT "KAI-2 closed / pivot proven."** Status string everywhere = **"phase-2 cloud pipeline GREEN; G-KAIROS-2 pivot/selectivity gate PENDING."** NEXT = G-KAIROS-2: pull packets → `gemma4_kv_inject` → measure ≤2-step pivot (vs §6.2's 44 text-delivery steps) + selectivity 2×2.

**GNA "EAR" line CLOSED on PHYSICAL SILICON; XBAR P3 CLOSED END-TO-END — the audio pivot is DONE, project pivoted BACK to XBAR (2026-06-17, contract §7.4–§7.6).** The GNA EAR (the real-audio sibling that KAI-3 bridges into) is now realized on the hardware: real TTS speech → log-mel → GNA-conservative Conv1d + CTC head → `gemma4_kv_inject_seq` → the 12B pivots **7/8** (CTC token recovery 0.44→0.868, multi-voice bake of 924 samples / 2 voices / 400 ep; all 4 NO_OPs correct, 3/4 ACTIONs coherent, 1 conservative ACTION→NO_OP miss). The front-end lowers clean to GNA 2.0 (encoder conv padding `1→0` VALID, CTC head `33→36` filters mult-of-4), and **POT GNA-native i16 PTQ = 0.877 full FP32 recovery** (naive i16 sheared 0.877→0.667; NNCF INT8 on CPU = 0.860 but won't compile on GNA); **GNA_HW on the physical Intel GNA 2.0 (Beast Canyon i9-11900KB, driver `gna_03.05.00.2116`) = 0.877 == SW_EXACT emu == FP32 — PHYSICALLY REALIZED** (native-Windows OpenVINO 2023.3; WSL2 has no GNA MMIO passthrough). Receipts `_xbar/p2b/kai3/G-KAIROS-3-{AUDIO_7of8,GNA-i16_quant_gate,GNA-HW}.log`; tooling `engine/tools/audio_port/{ov_gna_score,ov_score_ir,pot_gna_quantize}.py` + `run_gna_hw.bat` + `GNA_HW_BRINGUP.md`. **On the XBAR axis, P3.3 (replay-write `SP_REPLAY`, `G-P3-SHARED` 3-leg PASS on 12B+E2B) + P3.4 (recall-quality `G-P3-PPL` +1.38% < 2% gate) are CLOSED GREEN — XBAR P3 is CLOSED end-to-end (P3.0→P3.4).** **▶ NEXT (the active phase) = the Memo curator / Ring-3 orchestration tier ABOVE P3** — the autonomous recall loop (recall-cue → episode-id → `SP_REPLAY`), with Ring-3 gist consolidation budget-gated via the P2.b adapter (the semantic memory tier above the rings). This is the KAIROS-harness lane proper.

**G-XBAR-ORGANISM-FULL CLOSED on silicon — the autonomous sense→memory→act loop runs end-to-end (2026-06-18, engine 15e7051; `tools/ring3/g_xbar_organism_full.py`).** The orchestration tier the line above named as NEXT is now closed as a full loop on REAL episodes (the EAR audio packet + text decoys), unifying the previously-separate sibling programs (GNA EAR + XBAR latent memory) into one resident organism:

1. **C2 signature separation** — audio self 256 / decoys 147,129 (both << TAU_BITS=168) ⇒ the 256-bit discrete address cleanly admits the audio episode and rejects the text decoys.
2. **NIGHTSHIFT native bind** — consolidation via the native `sp_pr_mul` bind (Ring-3 R3.x); shadow-gate recall@1 holds for all bound episodes.
3. **DUALROUTE** — audio cue → ep_audio retrieved **TOP-1**; the C2 Hamming verify **accepts audio / rejects text** (the cross-modal verify is by SIGNATURE, not text-PPL — the right tool for a non-text modality).
4. **LAND** — Frobenius a16b8 decode → float, sub-ULP (the T4 store form).
5. **METAL** — `SP_REPLAY` of the integer-decoded ep_audio into the 12B resident cache: **checks=5 fails=0** (PPL 88.89, foreign-by-design — a cross-modal episode is not a text continuation).

**Continuous audio → discrete integer memory → continuous KV out, autonomous.** This is the KAIROS organism thesis (sense → gated latent memory → act, all receipted) demonstrated on physical silicon: the GNA "EAR" front-end and the XBAR three-ring latent memory are no longer two programs but one closed loop. (Caveat carried: the METAL replay PPL is foreign-by-design — the gate here is the loop *completing* with the right episode selected/verified/landed, not a text-continuation deflection.) Receipts `engine tests/fixtures/xbar_organism/`. **▶ NEXT = T4 Frobenius πᵏ of the 9.4 GB model WEIGHTS** (the one validated structural lever, RFC §3.0 boundary thesis) **→ KAIROS post-organism** (the resident scheduler/driver phases KAI-4/5, now standing on a proven organism loop).

---

**AUTONOMOUS RECALL ON THE EXEC CHAT — the §6 "▶ NEXT" autonomous recall loop is now REALIZED (B3-WC, 2026-06-20).** The Memo-curator-tier autonomous recall loop (recall-cue → episode-id → `SP_REPLAY`) that this roadmap repeatedly names as the active phase above P3 is now closed on the live served gemma-4-12B chat by a **learned `W_c` content addresser**: it selects the right stored episode for a query, or refuses to a NULL class if none is relevant. Hand-designed relevance signals were proven inadequate open-world (honest negatives: 6 verifiers + 4 Disposer signals + cosine-qK + ΔLL-polarity, dominated by per-episode bias at N=3 wiki — because wiki facts are PARAMETRIC and episodic dependency is unmeasurable on them); the unlock was a teacher-forced ablation knockout on a NOVEL needle (`SP_B3_SECRET`, novel −33.56 vs parametric −0.15, TAU −8.0) that both gates and labels a curator-minted diverse corpus, training the W_c head (HD=512→r=32, logsumexp-mean, InfoNCE over [episodes + NULL/s0]). Corpus diversity was the binding constraint (instance top-1 34%→100%). **G-CHAT-B3-WC-DIV2** 360/361 recall + 50/50 reject (int16-exact, `87044d8`); **G-CHAT-B3-WC-DEPLOY** LIVE (`edc8079`). The KAIROS organism now has an autonomous *librarian* on the agency axis. **▶ NEXT for KAIROS = B4 NIGHTSHIFT** (between-turn consolidation: fold each turn into the episode store via curator-mint → ablation-admit → hot-append; the W_c head needs no retrain to score a new episode — DEFERRED, pre-scoped, `SESSION-HANDOFF.md §0d`), then the resident scheduler/driver phases. Record `CONTRACT-CHAT-FULLSTACK.md`.
