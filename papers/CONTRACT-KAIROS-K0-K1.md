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
| **Dream** (periodic dedup/compress of memory) | **ADOPT — already exists as NIGHTSHIFT/the curator** | XBAR-N idle job = schedule the C1-lite curator + cold-evict | RFC §3.1/§7 + CONTRACT-XBAR-C1-lite §3a: cold-evict + G-R3-LOSS consolidation **CLOSED GREEN** (T_GENKV_COLD_EVICT 45/45: cold-evict lossless ⇒ promote, hot-evict diverges ⇒ rewind). We *schedule* it; MiMo validates the 7-day cadence |
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
