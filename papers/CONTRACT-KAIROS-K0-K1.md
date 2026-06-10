# CONTRACT KAIROS-K0/K1 — reference extraction + the heartbeat null

**Parent:** ROADMAP-KAIROS §5. **Status:** K0 partially RUN (Stage-0 swarm 2026-06-10); K1 SPEC —
**does not open until the XBAR P2.b/P3 arc closes** (standing sequencing rule; building it early
is drift).
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

## 3. Scope discipline

K1 proves the LOOP's nervous system on synthetic events. It claims nothing about sensors,
actuators, autonomy quality, or the Exec. No ledger row from this contract before G-KAIROS-1 +
the Exec repeat are both green — and none is expected; this is internal mechanism work. The
XBAR campaign's docs and gates are untouched by this stage until its opening condition (P2.b/P3
closed) is met.
