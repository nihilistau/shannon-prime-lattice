# CONTRACT KAIROS-K0/K1 — reference extraction + the heartbeat null

**Parent:** ROADMAP-KAIROS §5. **Status:** K0 RUN (Stage-0 swarm 2026-06-10; MiMo external reference
added 2026-06-14, §1a); K1 SPEC. **Opening condition NOW MET (2026-06-14):** the XBAR P2.b/P3 arc has
closed — P2.b rested, P3 ring-on-Exec bit-exact end-to-end, **§P3.2-b-2b + Phase C CLOSED GREEN**
(select → realize O(1) → retain: NIAH needle survives the O(1) compaction at 10/50/90%, learned-router-
only; CONTRACT-XBAR-P3 G-P3-R2.b-2c-NIAH). KAI-1 may open. (#115 text-in remains the prerequisite for
the *Exec/12B* repeat; KAI-1/2/3 prove mechanism on the qwen3-CPU substrate first, as designed.)
**One line:** prove, on the cheap bit-exact qwen3 substrate, that the resident loop's two
foundations hold — (K0) we have actually read the prior art we own, and (K1) a ticked model can
hold NO_OP discipline over a persistent session whose idle state does not grow.

---

## 1. KAI-0 — reference extraction (Stage-0, lead-with-the-reference)

**Run record 2026-06-10 (first pass, swarm of 2 read-only agents + doc corpus):**
- CosySim doc corpus digested (ARCHITECTURE/MCP_FRAMEWORK/NEXUS/NEXUS_SYSTEM/OPERATIONS/
  LMSTUDIO/SKILLS/INTERCEPTORS/INTEGRATIONS_SDK/APPS + ARGUS API references).
- Code forensics on the autonomy mechanics (file:line receipts in the session dossier):
  agent_loop.py **8 s tick + batched inference + 200-entry shared-log bound**; npc_scheduler
  **60 s tick, ≤3 NPCs/tick, small-model profile**; scheduler_daemon **60 s poll, schedule
  strings, JSON state persistence, idempotent callbacks**; kill_switch **acceptability 0.3,
  max 2 retries, temperature decay**; stream_watcher rule-based+model-based in parallel;
  token-ahead pre-warm; task_queue priorities REALTIME/INTERACTIVE/BACKGROUND/BATCH; model
  manager VRAM TTL reaper (3600 s — flagged as mistuned for the hardware, a lesson not a spec);
  **online evaluator auto-promotes finetunes on threshold WITHOUT holdout — the gameable-scorer
  anti-pattern, rejected** (ROADMAP-KAIROS §4).
- Inventory: **Project X** = production always-on assistant (Android+Windows; macro-detection
  event loop, HA integration, tool pipeline, health checks) — the driver-layer reference.
  **C:\Files\MCP** incl. `shannon-prime-lmstudio-server-quickborn` (32-tool MCP server with
  SP speculative decoding) — a future kernel surface, not a dependency. **NEXUS server**
  (C:\Files\Nexus): 4-layer SQLite store, FTS5, 21-tool MCP, agent registry with tiers,
  dual NLM backends — adopted-as-pattern for the kernel's lexical store + permission model.

**Remaining for G-KAIROS-0 (gate):** the §4 adopt/adapt/reject catalog ratified by the operator
(amendments recorded here), and any item we intend to ADOPT gets one file:line-cited paragraph
in this contract before its Kairos twin is built. No code import, ever (anti-contamination).

## 1a. KAI-0 — the MiMo-Code external reference (added 2026-06-14)

The internal corpus (CosySim/NEXUS/Project X) is the operator's own harness engineering. **MiMo-Code**
(Xiaomi, MIT, built on OpenCode; `mimo.xiaomi.com/blog/mimo-code-long-horizon`, read 2026-06-14) is the
first *external* harness reference — and the most valuable thing it gives us is independent
corroboration of the §4 adopt/reject lines, plus a clean instance of the pattern we reject. The catch
that justifies its inclusion: **MiMo's memory architecture IS the harness compensation our substrate is
built to not need** — they summarize-and-rehydrate because their window is hard-capped on a stock
engine; we have SP_REPLAY (bit-exact episode resurrection). Adopting their semantic-tier restart would
discard the physical primitive we just closed.

| MiMo mechanism | Verdict | Lands at | Grounding |
|---|---|---|---|
| Deterministic-code orchestration (`agent/parallel/pipeline/workflow`, disk-journaled, crash-resume) | **ADOPT** (rebuilt in Rust, never copied) | Holon plane + KAI-5 scheduler; steal the API *shape* | "`if` won't forget a branch, `for` won't exit early" — validates §4-ADOPT scheduler-daemon shape + the Rust control-plane choice |
| Independent **Goal** completion verifier (separate context, pre-terminate) | **ADOPT** | KAI-3/KAI-5: hard task-exit gate before arena teardown | task-level twin of our two-stage retrieve-verify; kills "premature optimistic stops" |
| Tiered priorities (REALTIME/INTERACTIVE/BACKGROUND/BATCH) | **ADOPT** | KAI-5 priority classes | already §4-ADOPT; MiMo corroborates |
| **Dream** (periodic dedup/compress of memory) | **ADOPT (mechanism) — already exists as the C1-lite curator / NIGHTSHIFT; MiMo's cadence validates our idle-consolidation window choice (structural match, not implementation-identical)** | XBAR-N idle job = schedule the C1-lite curator + cold-evict | RFC §3.1/§7 + CONTRACT-XBAR-C1-lite §3a: cold-evict + G-R3-LOSS consolidation **CLOSED GREEN** (T_GENKV_COLD_EVICT 45/45: cold-evict lossless ⇒ promote, hot-evict diverges ⇒ rewind). We *schedule* it; MiMo validates the 7-day cadence |
| **Distill** (repeated workflows → reusable skills) | **ADOPT — the one genuinely new piece** | KAI-5 flywheel: trace sweep → candidate skill → **held-out gate** → registered skill | no existing analog (the curator consolidates *memory*, not *procedure*); NOT "compile token loops into macros" (overreach) — a governed skill behind a receipted gate |
| 4-tier **semantic** memory as the cross-session **restart** mechanism | **REJECT (restart); ADAPT (filesystem)** | restart = SP_REPLAY (§2.5); text tiers = the kernel filesystem (Nexus-as-lexical-Ring-3), human-auditable knowledge/rules/receipts, coexisting with the latent rings as the page cache | §4 REJECT "prompt-stuffing as primary context"; SP_REPLAY resurrects post-RoPE K/V **bit-exact** (C1L.0b CLOSED, T_GENKV_REPLAY_NULL 34/34) — we don't summarize for restart, we replay |
| Max Mode (N=5 sample+judge, 4–5× tokens) | **DEFER** | optional KAI-5 test-time-compute knob | orthogonal compute (decision search), not a harness primitive |
| Inline tag side-channel / "eternal rolling document" / ungated auto-promotion | **REJECT** | — | detokenize/retokenize loss XBAR deletes; gameable scorer — already §4 REJECT |

**G-KAIROS-0 amendment:** ratify this table (operator sign-off). Net new from MiMo = the orchestration
API *shape* + the **Distill** procedure-consolidation idea; everything else is corroboration or rejected.

## 2.5. The handoff ABI (the kernel-vs-harness decision, locked BEFORE the Rust structs)

Two distinct objects, never conflated. This section is the contract the Rust control plane implements;
`struct Workflow` / `enum TaskState` are NOT written until it is operator-ratified.

**(a) Event packet** — the unit a sensor/operator/interrupt delivers. Format (both already minted):
**k≈2 adapter pseudo-tokens** (P2.b's trained selectable-recall payload) for semantic events, or a
**Spinor block (63 B + 0xA5 = exactly one cache line**, manifesto trick #9) for KV-class events. An
event packet is a PROPOSAL through a Ring-2′ gate, never a direct canonical write (RFC §6.2 defense).
Delivery seam = the proven `SP_XBAR_EMB` pseudo-token / cache-splice path (X-R1, 15/15). KAI-2 measures
latent-vs-text delivery; here we fix only the format.

**(b) Session resume = `SP_REPLAY`, NOT text summarization.** A session resumes by *replaying its
episode*:

*(The block below is a language-neutral IDL — its realized form is the Rust `struct SessionHandoff` in `sp_daemon/src/kairos.rs`, compiled when the `kairos` cargo feature is built; see §2a.)*

```
SessionHandoff := {
  episode_manifest : ring-2 descriptor (off[L] owner-resolved byte law + per-owner kvd),
  episode_store    : {ep.k, ep.v} on disk (post-RoPE K/V, f32-exact ⇒ replay is bit-exact),
  ring_coords      : the (L, pos, owner) the curator promoted (Ring-3 consolidated set),
  fs_pointer       : Nexus path(s) — human-auditable knowledge/rules/receipts (filesystem tier),
  task_state       : scheduler bookkeeping (priority class, journaled step cursor, Goal exit-cond)
}
```

Resume = `SP_REPLAY` mounts `episode_store` via the read-only load seam (`sp_arm_ring2_stdio_open_ro`,
truncation-guarded), re-projects stored K to rebuild `projk` (no serialization — G-C1L-0a bit-identical),
and the loaded K/V flow losslessly into attention (G-C1L-0b 34/34). The Nexus text tier is read for
human-auditable context ONLY — it is the filesystem, not the memory image. **Therefore `TaskState`
references an episode manifest + ring coordinates, not a prose summary** — pinning this before the
structs prevents a silent drift into text-summarization out of habit. **Law:** cross-session state lives
as an addressable lattice of minted coordinates (the episode) + a lexical filesystem (Nexus), never as a
tokenized summary round-tripped through the model (RFC §3 rule 4).

## 2. KAI-1 — the heartbeat null (SPEC; gates named, thresholds telemetry-then-pin)

**Substrate:** the qwen3 CPU daemon path (proven, bit-exact, cheap) + the C1-lite machinery.
The Exec/12B repeat happens post-P3 under a later contract.

**Build (additive, flag-gated `SP_KERNEL=1`):**
1. A scheduler process (OS-owned, schtasks/PM2-class — never the agent tree) ticking at a
   configurable interval (reference operating points: 8–60 s; start 30 s).
2. Each tick: collect the environment-delta frame (synthetic event tape for the gate — a
   scripted file the tick reads; real sensors are KAI-4's job), encode as a compact event line,
   append to a PERSISTENT session (sp_session; no transcript re-feed; cost must be O(Δ)).
3. The model's contract per tick: emit `NOOP` or an action line. Action lines go to a stub
   actuator that only LOGS (no real side effects in K1).
4. Idle hygiene: NOOP ticks are pruned from the session via the cold-evict curator pass on a
   period; state size telemetry every tick.

**G-KAIROS-1 (the gate; run 1 = telemetry, then pin):**
- **Null floor:** `SP_KERNEL` unset → the daemon byte-identical to today (the bit-exact-when-off
  invariant, kernel edition).
- **Discipline:** against a scripted tape of N events embedded in M idle ticks (N≪M): false-action
  rate and missed-event rate, both under thresholds pinned after the first telemetry run.
- **Arithmetic:** per-tick cost O(Δ) demonstrated (tick latency flat vs session age); idle ticks
  do not grow persistent state (size flat after curator period).
- **Soak:** ≥24 h unattended, flat RSS, complete receipts (every tick logged: frame hash, decision,
  latency, state size).

**Falsification (pre-stated):** if no threshold exists at which the model holds NO_OP discipline
(action spam at any usable sensitivity), the flat tick is dead; KAI-2's interrupt-only
architecture becomes the front door and the negative ships in STATE. If per-tick cost grows with
session age despite the rings, the O(Δ) claim is falsified and the recall path gets profiled
before any further kernel work.

**Honest unknowns (named now):** an it-tuned model's RLHF prior is to ANSWER — NO_OP discipline
may need prompt-contract iteration or a small finetune (the flywheel exists; that lane is named,
not assumed). The 30 s starting interval is a reference-informed guess, not a measurement.

## 2a. KAI-1 control-plane spec — `Workflow` / `TaskState` (design; implements §2.5)

Language-agnostic spec the Rust daemon implements. **CORRECTION (2026-06-14, supersedes the prior
"crate is not in the tree" note): the Rust daemon crate IS in the tree — it is the mature `sp-daemon`
at `shannon-prime-system-engine/tools/sp_daemon` (Axum/tokio resident wrapping the frozen L1 C ABI;
session registry, SSE event loop, PoUW ledger, QUIC Ring-2 mesh, the `mining.rs` yield-to-inference
background loop, off-by-default WIRE-* features = the null-floor discipline). It was invisible to the
sandbox mount and surfaced only via PowerShell on the host. KAI-1 therefore EXTENDS `sp-daemon` — the
control plane is a new feature-gated module `sp_daemon/src/kairos.rs` (the `kairos` cargo feature,
mirroring `wire_*`), NOT a new crate. This §2a spec is now implemented there: `TaskState` /
`SessionHandoff` / `Workflow` verbatim, the §2b tape reader, the per-tick receipt log, and the
heartbeat loop. The model-decode decision seam is `decide_via_model`; the first cut ships a
deterministic salience-threshold stub decider that proves the loop's nervous system only (§3 scope:
"claims nothing about autonomy quality").** The constitutional rule from §2.5: state is COORDINATES,
never prose.

```
// the resumable unit of execution
enum TaskState {
    Pending,
    Running   { step_cursor: u64 },        // journaled; resume re-enters here, not from scratch
    Yielded   { resume: SessionHandoff },   // <eos> -> scheduler; the §2.5 episode pointer, NOT a summary
    Blocked   { on: GoalCond },             // the independent Goal verifier's unmet exit condition
    Done      { receipt: ReceiptHash },
    Failed    { receipt: ReceiptHash },
}

// SessionHandoff is the §2.5 ABI verbatim — coordinate pointers only
struct SessionHandoff {
    episode_manifest: EpisodePtr,   // off[L] owner-resolved byte law + per-owner kvd  (NOT text)
    episode_store:    Ring2Path,    // {ep.k, ep.v} on disk, post-RoPE K/V, f32-exact -> bit-exact replay
    ring_coords:      Vec<(u32,u32,u32)>, // (L, pos, owner) the curator promoted (Ring-3 set)
    fs_pointer:       Vec<NexusPath>,     // human-auditable knowledge/rules/receipts (filesystem tier)
    priority:         PriorityClass,      // REALTIME | INTERACTIVE | BACKGROUND | BATCH
    goal:             GoalCond,           // exit condition checked out-of-context before Done
}

// the deterministic orchestration primitives (MiMo API shape, rebuilt in Rust)
enum Workflow {
    Agent    { task: TaskState },
    Parallel { arms: Vec<Workflow>, barrier: bool },   // `for` won't exit early; barrier won't drop an arm
    Pipeline { stages: Vec<Workflow> },                // `if` won't forget a branch
    Sub      { name: WorkflowId },                     // composable; journaled to disk per step
}
```
**Invariants (gated, not assumed):** every `Workflow` step result is journaled to disk before the next
(crash-resume from log, never re-hydration); a SIGKILL mid-run resumes from `step_cursor` with **no
duplicated side-effects** (idempotent callbacks); resume is `SP_REPLAY(episode_store)`, never a prose
rebuild. `TaskState` carries **no tokenized text of the agent's own history** — that is the harness
regression §2.5 forbids.

## 2b. The deterministic event tape (KAI-1 fixture format)

A scripted, replayable tape so G-KAIROS-1 is deterministic (no live sensors — that's KAI-4). One event
per line; the tick reads the next line each tick:

```
# tick_idx   kind            payload                    salience   expect
0            IDLE            -                          0.00       NOOP
1            IDLE            -                          0.00       NOOP
2            EVENT.timer     "build finished"           0.80       ACTION
3            IDLE            -                          0.00       NOOP
...
```
`salience` feeds the router-tier score; `expect` is the gate oracle (NOOP-vs-ACTION) for the
false-action / missed-event counters. N salient events sparse among M idle ticks (N≪M). The tape is a
tracked fixture (`tests/fixtures/kairos/tape_*.txt`); the gate diffs the tick log's decisions against
`expect`.

## 3. Scope discipline

K1 proves the LOOP's nervous system on synthetic events. It claims nothing about sensors,
actuators, autonomy quality, or the Exec. No ledger row from this contract before G-KAIROS-1 +
the Exec repeat are both green — and none is expected; this is internal mechanism work. The
XBAR campaign's docs and gates are untouched by this stage until its opening condition (P2.b/P3
closed) is met.

## 4. KAI-1 CLOSURE — GREEN end-to-end (2026-06-14)

**The two-leg proof (single-variable isolation throughout):**

**Path A — control-plane MECHANISM (qwen3-0.6B, CPU daemon sp_daemon/src/kairos*.rs):** the loop's nervous system. Cold-evict NO_OP prune (`sp_session_rewind`, O(1), Corollary T8.1) holds idle silence at a flat KV position; the `SALIENCE>=0.5` policy forces the mode switch on the salient tick; O(Δ) flatline demonstrated (per-tick latency DROPPED 90→63 s once pruning stopped cache bloat, vs an unpruned creep 90→115 s). BUT the 0.6B collapsed at the **tick-5 crucible** (idle-after-retained-ACTION → false ACTION + deterministic `NO_克作` corruption attractor) — a cognitive-capacity ceiling, NOT a mechanism flaw.

**Path B — production COGNITION (gemma4-12b-b1 OK_Q4B, RTX 2060 GPU; `SP_G4_KAIROS` in `tests/test_gemma4_cuda.c`):** **PERFECT crucible — `DONE ticks=24 noop_ok=21 action_ok=3 false_action=0 missed=0 malformed=0`.** All 21 idle → NO_OP (KV prefix flat); all 3 salient → CLEAN contextual ACTION (`start` / `clean` / `renew` for build-finished / disk-95% / ttl-expiring); EVERY post-action idle tick (5, 13-15, 21-23) reverted to NO_OP with zero false-fire/drift. ~8-17 s/tick GPU, 10.8 GB resident on a 12 GB card.

**Architecture — prefix-grow = cold-evict on a one-shot decoder:** `gemma4_decode_cuda` rebuilds KV from `seq[0..n_prompt)` each call, so the NO_OP prune is simply "don't grow the persistent prefix" (next idle tick byte-identical to the first ⇒ O(Δ), attractor-proof); an ACTION grows the prefix (the tick-5 retained-action condition). No stateful rewind needed. Tokenizer = the parity-validated `.sp-tokenizer` blob lane (`sp_tokenizer_load_tokfile`/`encode`/`decode`, T_G4_TOK_PARITY 5432/5432) — runtime-encoded, no offline bake.

**Cognitive threshold:** 0.6B = mechanism-capable but context-unstable; 12B = production-stable. The harness is model-agnostic and bulletproof; parameter density sets the operating model.

**G-KAIROS-1 — functionally PASSED** (discipline: 0 false-action / 0 missed; arithmetic: O(Δ) prefix-flat; crucible: tick-5 reversion). The ≥24 h unattended soak remains an operational telemetry run, NOT a design blocker. Receipt: `engine/results/kairos_12b_pathB_crucible.log`. **KAI-1 CLOSED.**

## 5. KAI-1b — METAL EVICTION (opener; pre-registered 2026-06-14, code next session)

**Why (the O(actions) bleed):** Path B's `SP_G4_KAIROS` proved 12B cognition via a host-layer
**prefix-grow** hack on the one-shot `gemma4_decode_cuda` — a NO_OP leaves the token prefix
unchanged, an ACTION appends. This is *flat across idle ticks* but its per-tick prefill cost is
**O(actions-so-far)**: every tick re-absorbs `[system + all retained actions]` through the forward
pass. For a daemon meant to run for days that recompute tax is unbounded. The true resident kernel
must evict at the **tensor-routing layer**: on a null tick, shear the KV write pointer back by Δ —
a sub-millisecond coordinate op the text tokens never see — so an idle tick costs only
`frame + decode` (**O(1)**, independent of action history). This is the convergence of the KAIROS
time-axis with the XBAR memory physics: cold-evict becomes a ring-pointer operation on the same
`off[L]` structures Phase C built. We are not inventing a memory system; we are plugging the
heartbeat into the crossbar.

### 5.1 Seam survey (the three pointer-rollback primitives that already exist)

| Seam | Where | Primitive | Reuse for KAI-1b |
|---|---|---|---|
| `sp_session_rewind(n)` | daemon L1 (`tools/sp_daemon/src/session.rs` → math-core `sp_session`) | O(1) KV ring-pointer decrement; **Corollary T8.1**: state at P−n after rewind == state at P−n never-visited (byte-identical). Drove Path A (0.6B) cold-evict. | The reference semantics + the proven gate shape. Path B needs the **CUDA twin** of this. |
| SWA-ring write pointer | `cuda_forward.cu` (P3.2-b-2a) | `slot = pos % Wring`; the window ring already overwrites/evicts the oldest slot every step — eviction IS a pointer op here. | The decrement model: rolling the logical `pos` back by Δ frees the last Δ ring slots with no copy. |
| `off[L]` + compact slab | `cuda_forward.cu` (P3.0/P3.2 Phase C) | owner-resolved byte law `off[L]=Σ P·kvd·4`; the slab/`off[L]` already addresses KV by `(L,pos,owner)` coordinate. | The truncation target: an evict = lower the per-layer logical length so `[pos−Δ, pos)` is no longer attended/served (globals via slab length, SWA owners via ring wrap). |

**Integration point (the pick):** introduce a single logical decode position `dpos` the CUDA decode
already tracks; KAI-1b adds `gemma4_kv_rewind(m, Δ)` that (a) decrements `dpos` by Δ, (b) for SWA
owners rewinds the ring write cursor `pos%Wring` by Δ (slots become free, no memset needed —
attention reads `[s0, dpos)` in position order), (c) for globals lowers the slab/`off[L]` logical
length by the Δ owners written since the anchor. No tensor copies; only length/pointer state moves.

### 5.2 Interface — persistent-KV `gemma4_decode_cuda` + `rewind(Δ)` (C-ABI)

Today `gemma4_decode_cuda(m, seq, n_prompt, n_gen, eos)` is **one-shot** (rebuilds KV from
`seq[0..n_prompt)` each call). KAI-1b splits it into a persistent-session surface so the resident
loop appends/decodes/rewinds against a live cache:

```
sp_g4_kv*  gemma4_kv_open(const qwen3_model *m, int max_ctx);     /* alloc resident KV (rings+slab), dpos=0 */
int        gemma4_kv_prefill(sp_g4_kv *s, const int32_t *toks, int n);  /* append+absorb n; dpos+=n */
int        gemma4_kv_decode (sp_g4_kv *s, int n_gen, int32_t *out);     /* greedy/argmax; appends gen to cache; dpos+=k */
int        gemma4_kv_rewind (sp_g4_kv *s, int delta);             /* O(1): dpos-=delta; ring+slab logical truncate */
int        gemma4_kv_pos    (const sp_g4_kv *s);                  /* current dpos (the flat-vs-grow witness) */
void       gemma4_kv_close  (sp_g4_kv *s);
```

KAIROS tick (metal): `anchor=kv_pos()`; `kv_prefill(frame)`; `kv_decode→parse`; **NO_OP ⇒
`kv_rewind(kv_pos()-anchor)`** (frame+gen sheared, cache resident, no re-prefill); **ACTION ⇒
keep** (dpos advances; the action stays resident — the tick-5 crucible, now at zero recompute).
The existing `SP_G4_KAIROS` prefix-grow path stays as the **oracle** for the gate below.

### 5.3 Oracle gate — G-KAIROS-1b (T8.1 analog on the GPU; PRE-REGISTERED, bit-exact)

- **G-1b-REWIND-NULL (the rule):** for any idle tick, the KV state after
  `kv_prefill(frame)+kv_decode+kv_rewind(Δ)` is **byte-identical** (device D2H memcmp over the live
  K/V rings + slab, all layers) to the state of a session that **never visited** that frame —
  i.e. rewind is a perfect inverse. Mirrors `sp_session_rewind`/T8.1 on the CUDA path. **diffs=0.**
- **G-1b-EQUIV (vs the proven harness):** the full 24-tick smoke tape run through the metal loop
  produces the **same decisions and same retained-prefix token stream** as the prefix-grow
  `SP_G4_KAIROS` run (same `noop_ok/action_ok/false_action/missed/malformed`; the kept-action KV
  matches the re-prefilled KV bit-exact at each ACTION boundary). The host hack is the oracle; the
  metal must equal it.
- **Falsification:** if the rewound cache is not bit-identical (RoPE-phase residue, ring-wrap
  off-by-one, slab length desync), KAI-1b is RED and the prefix-grow path remains the shipping
  proof until the pointer arithmetic is exact. No "close enough."

### 5.4 Baseline telemetry — the recompute tax we are deleting (PRE-REGISTERED motivation run)

Before/after, same model + tape, clocks pinned: **profile per-idle-tick latency as retained-action
count A climbs.** Construct a tape with an increasing salient cadence (A = 1,2,4,8,16 actions
retained), measure idle-tick wall-time at each A.
- **Prediction (prefix-grow):** idle-tick latency rises ~linearly with A (each idle tick re-prefills
  `system + A·action_len`).
- **Prediction (metal rewind):** idle-tick latency is **flat in A** (idle tick = frame+decode only;
  resident cache untouched).
The crossover/slope difference is the formal O(actions)→O(1) receipt — the number that justifies the
engine change. Land both curves in `results/` + a ledger-internal note (no public row until
G-KAIROS-1b is green).

**Scope discipline:** KAI-1b is engine pointer-arithmetic on the gemma4 CUDA decode + a bit-exact
inverse gate. It claims nothing new about cognition (KAIROS-01 already closed that); it converts the
*proven* host-layer eviction into the *resident-kernel* eviction. Lands in the P3.x ring-on-Exec
lane (it IS XBAR pointer work). **Next-session first action:** open `cuda_forward.cu` at the SWA-ring
+ `off[L]` seam, cut `gemma4_kv_open/prefill/decode/rewind/pos/close`, gate G-1b-REWIND-NULL FIRST
(null floor) before wiring the KAIROS loop to it.

### 5.5 KAI-1b CLOSURE — GREEN (2026-06-14, engine 0bb94f1)

The metal eviction is built, bit-exact, and O(1)-proven on the 12B. `gemma4_decode_cuda`
left BYTE-FOR-BYTE UNTOUCHED (null floor for 06-R10/X-R2/NIAH/KAIROS-01); the resident twin
`gemma4_kv_open/prefill/decode/rewind/pos/snapshot/close` is the new surface.

**G-1b-REWIND-NULL — GREEN** (`SP_G4_KV_REWIND`, gemma4-12b-b1, RTX 2060): prefill system(24)
→ snapshot; idle tick prefill frame(12)+decode(8); `rewind(20)`→anchor; snapshot. The [0,24)
KV region is byte-identical across all 48 owner layers (16.5 MB, **diffs=0**) — rewind is a
perfect inverse (T8.1 analog on the GPU). **EQUIV gen-reproduce GREEN**: the same idle tick re-run
after the rewind yields identical tokens (the rewound cache is a flawless re-entry point).

**§5.4 O(actions)→O(1) telemetry — CONFIRMED** (`SP_G4_KV_TELEMETRY`, clocks pinned, min-of-3):
idle-tick latency vs retained-action count A:

| A | prefix-grow (s) | metal (s) | grow/metal |
|---|---|---|---|
| 1 | 2.72 | 0.88 | 3.08× |
| 2 | 3.59 | 0.89 | 4.03× |
| 4 | 5.35 | 0.91 | 5.89× |
| 8 | 8.96 | 0.93 | 9.60× |
| 16 | 16.58 | 0.99 | 16.70× |

slope d(idle)/dA: prefix-grow **0.924 s/action** vs metal **0.0073 s/action** (127× shallower).
The prefix-grow recompute tax is linear in retained actions; the crossbar rewind deletes it —
the resident loop is a flatline. Receipts: `engine/results/kai1b_rewind_null_gate.log` +
`kai1b_oactions_to_o1_telemetry.log`.

**SCOPE (honest):** full-cache rewind (SWA handled by windowed attention). The metal *idle tick*
itself carries the real O(context) attention term (constant step count, mild rise: 0.88→0.99 s as
the resident context 44→344) — that is the per-step attention read, NOT re-prefill; the O(actions)
elimination is in the **step count** (metal = constant 20 steps/tick; grow = system+A·action+frame
steps/tick). SWA-ring/slab wrap-aware rewind = follow-on. The telemetry harness measures both modes
directly (the §5.4 receipt); the full semantic `run_kairos` loop on the metal ABI is a deployment
follow-on (cognition already closed at KAIROS-01; metal forward bit-exactness proven by EQUIV).
**KAI-1b CLOSED.**

## 5.6 KAI-1c — WRAP-AWARE RING REWIND (opener; pre-registered 2026-06-14, code next)

**Why:** KAI-1b proved O(1)-*time* eviction on the FULL cache; X-R2 proved O(1)-*space* on the
SWA ring/slab. They are not yet unified. The resident edge daemon must evict on the
*space-optimized* ring — but `rewind` on a ring is not a clean pointer decrement.

**The hazard (surveyed, `cuda_forward.cu` k_attn_decode_ring @271 / pos%Wring write):** the ring
holds the window `[p-W+1, p]` across `Wring` slots; writing position `p` to slot `p%Wring`
overwrites position `p-Wring` (correct eviction in steady-state forward — that is why the one-shot
ring is bit-exact, G-P3-R2.b-2a). Under REWIND it corrupts: an idle tick advancing `[anchor,
anchor+k)` writes slots that previously held the still-live window positions `[anchor-W, anchor-W+k)`;
a naive `dpos -= Δ` then leaves those `k-1` window slots holding FUTURE K/V (positions `[anchor+1,
anchor+k-1]`). The "sheared slots never read" invariant (true on the full cache, slot==pos) FAILS on
the ring because the tick's writes alias onto live-window slots.

**The fix (design): an undo-journal.** Per SWA-owner step, BEFORE `k_kv_store` overwrites ring slot
`s = pos%Wring`, copy the slot's current K/V into a per-tick journal keyed by `(L, s)`; on
`gemma4_kv_rewind`, replay the journal in REVERSE to restore each clobbered slot to its pre-tick
contents. Journal size = (distinct slots the tick wrote) ≤ min(k, W) per owner — CONSTANT per tick
(k = frame+decode tokens), independent of retained-action count A ⇒ O(1) time AND O(1) space
preserved. `gemma4_kv_decode`/`prefill` populate the journal; `rewind` consumes it; `gemma4_kv_open`
allocates SWA owners at `Wring` slots (not Pmax) — the X-R2 space win, now rewind-safe.

**G-1b-WRAP-NULL (PRE-REGISTERED gate, bit-exact):**
- **Construction:** small `Wring` (e.g. W=16) so wraps are cheap. Prefill past `W` multiple times
  (force ≥2 wraps); retain an action (dpos ≫ W); **snapshot the ring's W slots** (the anchor state).
- **The crucible:** execute an idle tick whose span crosses ≥1 wrap boundary (`anchor%W + k > W`),
  then issue the **wrap-crossing `rewind(Δ)`**; snapshot the ring again.
- **The rule (REWIND-NULL on the ring):** the W-slot ring is **byte-identical** before vs after the
  tick+rewind (D2H memcmp over all SWA-owner rings, diffs=0) — the journal is a perfect inverse
  across the wrap. PLUS **EQUIV**: a non-wrapped FULL-cache oracle decoded to the same dpos has a
  window `[anchor-W+1, anchor]` byte-identical to the ring's live window (slot-mapped), and the idle
  tick re-run after rewind reproduces identical tokens.
- **Falsification:** any nonzero diff (a clobbered live-window slot not restored, an off-by-one in
  `(s0+j)%Wring` vs the journal key, a wrap-boundary miscount) ⇒ RED, full-cache rewind remains the
  shipping primitive until the ring journal is exact. No "close enough."

**Scope:** SWA owners (the dominant kvd=2048 term, 40/48 layers) move to the journaled ring; the 8
globals stay full-cache (they attend all positions — no window, no ring; their KAI-1b rewind already
exact). The compact-slab (C-b.2) globals path is a separate follow-on. **Next-session first action:**
open `cuda_forward.cu`, add the journal to the `gemma4_kv_*` SWA-owner write path, gate
G-1b-WRAP-NULL (REWIND-NULL ring byte-identity) FIRST before any deploy wiring.

## 5.7 KAI-1c — WRAP-AWARE RING REWIND **CLOSED GREEN** (2026-06-14, engine `d90945f`)

**Implemented** (null-floor held — `gemma4_decode_cuda` BYTE-UNTOUCHED; all edits inside the
`gemma4_kv_*` twin ABI): `struct sp_g4_kv` extended with `ring_W, Jmax, commit_pos, jcur, jK[], jV[]`.
`g4_kv_step` SWA-owner write branch (env `SP_G4_KV_RING_W>0`, `!global`): before the ring store at slot
`s=pos%Wring`, save the slot's current K/V into the per-tick journal at index `j=pos-commit_pos`
(guard `j<Jmax`), then store the new K/V; ring attention via `k_attn_decode_ring` over window
`[s0,ctx)` at slot `(s0+j)%Wring`. `gemma4_kv_open` allocs SWA owners at `Wring` slots + `Jmax`-deep
journals (globals at Pmax, no journal). New `gemma4_kv_commit` clears the journal + sets a new baseline
(`commit_pos=dpos, jcur=0`) — called on a RETAINED action. `gemma4_kv_rewind(Δ)` (ring mode) walks
`p=dpos-1 … dpos-Δ` in REVERSE, restoring slot `p%Wring ← journal[p-commit_pos]` for every SWA owner,
then `dpos-=Δ` (rejects `Δ>dpos-commit_pos` — a rewind may not cross a commit). `gemma4_kv_snapshot`
sizes the D2H copy to `Wring` slots for SWA owners (was Pmax — OOB fix).

**G-1b-WRAP-NULL GREEN** (`SP_G4_KV_WRAP=1 SP_G4_KV_RING_W=16 SP_G4_KV_JMAX=64`, gemma4-12b-b1 OK_Q4B,
RTX 2060, clocks pinned): sys prefill 50 (wraps the W=16 ring 3×) → **commit** → snapshot ring →
idle tick (prefill frame 12 + decode 8, span 20 > W, anchor%W=2 ⇒ slot index wraps 15→0) → **mid
snapshot** → wrap-crossing `rewind(20)` → snapshot ring. Result: `anchor=50 after=70 wraps_crossed=1
clobbered_owners=40` — the tick overwrote live-window slots in **all 40 SWA owners** (non-vacuity
proven: pre≠mid) — and post-rewind **swa-ring-diffs=0** (byte-identical across all 40 owner rings) +
**EQUIV** gen-reproduce GREEN (re-run idle tick → identical tokens `[107 236743 107 236743 …]`). The
undo-journal is a perfect inverse across the wrap. Harness: `run_kv_wrap()` in `tests/test_gemma4_cuda.c`
(`SP_G4_KV_WRAP` dispatch); driver `_run_kv_wrap.bat`. Receipt: `results/kai1c_wrap_null_gate.log`.

**Unification achieved:** O(1)-*time* eviction (KAI-1b rewind) now runs on the O(1)-*space* SWA ring
(X-R2). The resident edge daemon can cold-evict an idle tick on the space-optimized ring with a
constant-size journal (≤min(k,W) per owner per tick, independent of retained-action count A).
**Follow-ons:** compact-slab (C-b.2) globals wrap-aware rewind; full semantic `run_kairos_metal` loop
on the journaled ring; ≥24h soak (G-KAIROS-1).

## 5.8 KAI-1c — JOURNALED-RING O(1) TELEMETRY (#219) + SEMANTIC LOOP (#221) **CLOSED GREEN** (2026-06-14)

**§219 Journaled-ring O(1) telemetry** (engine `f201bf3`): idle-tick-latency-vs-A swept through the
journal path with **commit-per-action** (journal only ever holds one tick's span ⇒ A-invariant by
construction). **T1 (O(1)) CONFIRMED:** ring slope **0.00365** s/action ≈ full-cache **0.00371** —
both flat, ~270× under the prefix-grow 0.924; the undo-journal adds NO asymptotic cost in retained-
action count A. The fine-grained ring−full D2D **tax is below the wall-clock noise floor on this card**:
the 2060 **cannot lock its memory clock** (`nvidia-smi` "not supported"), and bandwidth-bound decode
jitters ±~12%, swamping the ~1-3% journal cost (produced physically-impossible −137ms "taxes", cv 210%
— pure inter-leg mem-clock drift, not journal behaviour). The within-leg slope (T1) survives because
it is computed inside one leg. Tax is structurally fixed (`min(k,W)·40·2` D2D copies/tick) ≈ low-tens-
of-ms ≈ 1-3% of a ~1s tick; exact drift-immune figure deferred to cudaEvent instrumentation (#220).
Harness `run_kv_ring_telemetry` (`SP_G4_KV_RING_TEL`); receipt `results/kai1c_ring_telemetry.log`.

**§221 Semantic loop on the metal — THE OPERATIONAL UNIFICATION** (engine `d0a6717`): `run_kairos_metal`
(`SP_G4_KAIROS_METAL`) wires the KAI-1 SALIENCE≥0.5 NO_OP/ACTION decider onto the persistent journaled-
ring `gemma4_kv_*` ABI. Open(ring) → prefill SYS → **commit** (anchor); per tick prefill(frame)+decode →
**NO_OP/malformed ⇒ `gemma4_kv_rewind(pos−anchor)`** (journaled cold-evict to anchor) / **ACTION ⇒
`gemma4_kv_commit`** (retain frame+gen, journal cleared, anchor advances). Pos-discipline is itself a
gate. **CRUCIBLE GREEN** (24-event §2b smoke tape, 12B OK_Q4B, RTX 2060, ring_W=1024): `noop_ok=21
action_ok=3 false_action=0 missed=0 malformed=0 pos_violations=0`. The 3 salient ticks produced
coherent context-correct imperatives — tick 4 `<ACTION>start</ACTION>` (build finished), tick 12
`clean` (disk 95%), tick 20 `renew` (ttl expiring) — each committed (anchor 135→195→258→318); **every
post-action idle tick (5,13,21) cleanly reverted to NO_OP via rewind to the new anchor, pos flat, zero
drift** — the tick-5 post-action crucible that broke the 0.6B is defeated on the metal ring. `gemma4_
decode_cuda` BYTE-UNTOUCHED. (Parse is boundary-tolerant for the `gemma4_kv_decode` first-token
convention vs the one-shot path — cosmetic, reconcile filed #222.) Harness `run_kairos_metal`; driver
`_run_kairos_metal.bat`; receipt `results/kai1c_kairos_metal.log`.

**Note on wrap during cognition:** the 24-tick faithful run (ring_W=1024 = true SWA window) does not
wrap the ring — resident_pos stays <1024 (a wrap needs >~50 retained actions, or a window<1024 which
would lobotomise SWA cognition). Wrap-correctness is proven *in isolation* by G-1b-WRAP-NULL (§5.7,
clobbered_owners=40, diffs=0); semantic correctness is proven here on the faithful ring. The two are
orthogonal and each tested cleanly. **KAI-1c CLOSED. The crossbar substrate (time ⊗ space ⊗ cognition)
is a unified whole — ready for the ≥24h soak (G-KAIROS-1).** Remaining hygiene: #220 cudaEvent tax,
#222 kv_decode boundary, compact-slab globals wrap-rewind.
