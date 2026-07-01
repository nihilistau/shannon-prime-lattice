---
type: reference
title: "shannon-prime-lattice — the umbrella / docs / OKFS repo"
description: "Top-level orientation for the Shannon-Prime umbrella repo: what each of the 5 repos controls, the architecture of the whole organism, the doc navigation (START-HERE → VERIFIED-SCOREBOARD → KEYSTONE → Roadmap → FINDINGS-LEDGER → ADR-002), the current state (faithfulness closed end-to-end; SWARM/DHT re-elevated primary), and the OKFS + MEM-OKF anti-rebuild knowledge discipline."
tags: [reference, umbrella, readme, navigation, okfs, mem-okf, architecture]
timestamp: 2026-07-01T00:00:00Z
resource: shannon-prime-lattice/README.md
sp_status: GREEN-LIVE
sp_gate: G-OKF-CONFORM
sp_commit: TBD
sp_repro: "python tools/okf_validate.py papers"
---

# shannon-prime-lattice — the umbrella

> **Shannon-Prime** is a fully local, byte-exact, auditable language-model **organism**. It serves
> Google's **Gemma-4-12B** (OK_Q4B quant) on a single **RTX 2060**, through **our own** inference
> engine, on an **exact-integer arithmetic substrate** (`O_K = Z[(1+√−163)/2]`, dual-prime
> negacyclic CRT-NTT), with a working memory it **owns**: it learns facts from conversation,
> recalls them faithfully, **forgets / supersedes / merges** them on its own judgement, calls
> tools and runs code, stores whole conversations both complete and summarized, and — between
> turns, on a heartbeat — consolidates the live conversation and tidies its memory. No cloud, no
> third-party inference, no telemetry.

**This repo is the umbrella / docs / knowledge-system.** It holds the canonical doc set
(`papers/`), the demos and integration receipts (`demos/`, `tests/`), the session bootstrap
(`prompt.md`, `AGENTS.md`), and — crucially — the two **knowledge stores** that keep the project
from rebuilding itself: **SP-OKF** (paper frontmatter + `tools/okf_validate.py`) and **MEM-OKF**
(`tools/okf_mem.py` + `memory-okf/`). **The code lives in the other four repos.** This repo is the
*map and the knowledge system*.

**Read this first:** [`papers/START-HERE.md`](papers/START-HERE.md) — the 2-minute navigable map,
then [`papers/VERIFIED-SCOREBOARD.md`](papers/VERIFIED-SCOREBOARD.md) (what is built, commit+gate
per claim; receipts-checked 2026-07-01). Here for the results, not the source? Start at the public,
receipts-first front door: **[Position Is Arithmetic](https://github.com/nihilistau/Position_Is_Arithmetic)**
(live: https://nihilistau.github.io/Position_Is_Arithmetic/).

License: MIT (`LICENSE`). GitHub: [nihilistau/shannon-prime-lattice](https://github.com/nihilistau/shannon-prime-lattice).

---

## State in one line (2026-07-01)

**The faithfulness axis is CLOSED end-to-end**, and **SWARM/DHT is re-elevated to a primary
forward axis**. The organism is built and live: byte-exact 12B forward, O(1) persistent KV,
learned recall, memory agency (forget/decide/merge), tool calling, and a proven cross-family
latent bridge (Telepathy). Faithfulness is now solved on BOTH general-knowledge conflict AND
private zero-prior data: **L5-cosine recall** (`SP_RECALL_L5`, τ=0.30, **86.89%** live paraphrase
obey, `G-L5-RECALL-LIVE`); the heavy **generative judge is PARKED** (the hard-foreign kill-test:
0 benefit over L5-direct+τ, and it PASSed 15/18 — it earned nothing the cheap levers didn't); and
the one hole native robustness does NOT cover — **zero-prior / private data** — is closed by a
deterministic **attribute-grounding gate** + query-token guard + a **ZERO-INFERENCE symbolic
decline** (`G-SNE-ATTRGATE-ZEROINF`: confabulation 80→0, secret-leak 5→0, recall 100%, paraphrase
untouched — the decline streams a fixed string with **no gemma4 forward**, so hallucination is
mathematically impossible). Full lever/constant map: `papers/PPT-LAT-FINDINGS-LEDGER.md`.

And the **SWARM axis is now BUILT end-to-end**: the SP-SWARM private memory mesh (L0 QUIC transport,
L1 content addressing, L2 have/want replication, L3 Ed25519 provenance, L4 C2-SimHash discovery) is
GREEN across 9 gates, cross-language byte-parity with the Python prototype, and integrated into
`sp-daemon` behind a default-off `swarm` feature — remaining work is multi-host deployment only. Call
surface: `papers/PPT-LAT-MESH-API.md`.

## The thesis

*Position Is Arithmetic.* An LLM's container can be made **exact arithmetic**
(cross-machine-deterministic, auditable) without losing quality, and memory can be
**content/position-addressed** rather than token-shaped. **Byte-exact = exact arithmetic /
cross-machine determinism / auditability — explicitly NOT compression.** Every structure-on-content
compression lever the project tried is a *measured negative*, kept on the record as an honest
negative; the win is the *container*. Every mechanism is a flag that is a **strict no-op when unset**
(the "null floor"); every number has a reproducing command and a gate.

**Governing law — ADR-002, the Decide→Execute spine** ([`papers/PPT-LAT-ADR-002-DECIDE-EXECUTE-SPINE.md`](papers/PPT-LAT-ADR-002-DECIDE-EXECUTE-SPINE.md)):
**DECIDE in latent** (cheap heads + selectors: route / select / gate / reject / draft), **EXECUTE
in clean symbol/text** (deliver / answer / tool / delegate / KV replay), **NEVER fuse latent
content into generation**, and **a decider must not execute**. Every win this campaign converged on
that shape; every failure violated it (fused latent+text transmit = 0.000; a judge that delivered
its own pick lost context-authority). A Rust typestate boundary makes fusion structurally
impossible.

## The five repositories

This repo is the map; here is what each repo *controls*.

| Repo | Controls | Lang | Entry |
|---|---|---|---|
| **shannon-prime-lattice** (this) | **umbrella / docs / OKFS.** The whole canonical doc set (`papers/`: STATE, KEYSTONE, Roadmap, RFC-001, the ADRs, the contracts, VERIFIED-SCOREBOARD, FINDINGS-LEDGER, START-HERE, the SWARM design), `demos/`, `tests/`, integration glue, and both knowledge stores (SP-OKF + MEM-OKF) | md/py | `papers/START-HERE.md`, `prompt.md` |
| **shannon-prime-system** | the **math core** (no engine deps): O_K, dual-prime NTT-CRT, exact islands, Frobenius, ARM two-ring KV, + the **frozen L1 C ABI** | C | `include/sp/sp_l1.h`, `core/` |
| **shannon-prime-system-engine** | the **inference engine**: `sp-daemon` + CUDA/CPU backends + the served `/v1/chat` + recall/agency (memory, judge, NIGHTSHIFT, Telepathy) | C/CUDA/Rust | `tools/sp_daemon/`, `src/backends/cuda/` |
| **shannon-prime-harness** | the **Python agent harness**: tool calling (ReAct), tiered conversation memory, the agency loop + scheduler (KAIROS) | Python | `harness/`, `run_agency.py` |
| **Position_Is_Arithmetic** | the **public paper series**: receipts-first papers + `LEDGER.md` | md | `README.md`, `SERIES.md`, `papers/` |

`shannon-prime-system` is also vendored into the engine as the `lib/shannon-prime-system`
submodule — `git fetch` + check behind before building (the two can diverge).

## Architecture (the whole organism)

```
                              ┌──────────────────────────────────────────────┐
   USER (browser console)     │  Position Is Arithmetic — papers / LEDGER     │  public face
        │  index.html         └──────────────────────────────────────────────┘
        │  POST /v1/chat (messages, knobs)             ▲ receipts
        ▼                                              │
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │  sp-daemon  (Rust, shannon-prime-system-engine/tools/sp_daemon)              │
 │  ───────────────────────────────────────────────────────────────────────    │
 │  /v1/chat  →  template → prefill → DECODE → SSE {delta}                       │
 │   DECIDE (latent) ──────────────┐        EXECUTE (clean text) ─────────────┐  │  ADR-002 spine
 │    ├─ L5-cosine recall select    │         ├─ text-in-context recite         │  │
 │    │    (SP_RECALL_L5, τ=0.30)   │         ├─ EOT bias (clean turn-stop)      │  │
 │    ├─ attribute-grounding gate   │         ├─ zero-inference symbolic DECLINE │  │
 │    │    + query-token guard      │         │    (no gemma4 forward)           │  │
 │    ├─ judge (PARKED)             │         ├─ delegate → qwen coder (Telepathy)│ │
 │    ├─ LAYER-2 FORGET / LAYER-3   │         └─ KV replay (novel needles)       │  │
 │    │    DECIDE+MERGE (agency)    │                                            │  │
 │    └─ NIGHTSHIFT capture ────────┘  writes turn → SP_CURRENT_CONVO (consolidation hook) │
 │  registers L1 backends:  forward (prefill) + kvdecode (token-by-token)        │
 └───────────────┬───────────────────────────────────────────────┬─────────────┘
                 │ L1 ABI (sp_l1.h)                                │ POST /v1/chat
                 ▼                                                 ▼
 ┌───────────────────────────────────┐         ┌──────────────────────────────────┐
 │  ENGINE backends (CUDA/CPU/…)      │         │  HARNESS (Python)                 │
 │  gemma4 forward + decode           │         │  SPDaemonClient ─ to_sp_chat      │
 │  OK_Q4B GEMV (dp4a)                │         │  run_with_tools  <tool …> ReAct   │
 │  SP_BYTEEXACT exact-int islands    │         │  memory tools: list/remember/forget│
 │  diffusiongemma-26B judge (drawer) │         │  conversation_memory: tiers + caps │
 └───────────────┬───────────────────┘         │  agency: round + scheduler (KAIROS)│
                 │ consumes                      └──────────────┬───────────────────┘
                 ▼                                              │ reads SP_CURRENT_CONVO
 ┌───────────────────────────────────┐                         │ writes registry + MEM-OKF
 │  MATH CORE (shannon-prime-system)  │                         ▼
 │  O_K = Z[(1+√−163)/2]              │         ┌──────────────────────────────────┐
 │  dual-prime NTT-CRT (q1,q2≈2^60)   │         │  MEMORY                            │
 │  exact_islands (RMS/softmax/GELU/  │         │  registry.jsonl  (facts, mid/long) │
 │     RoPE, CORDIC, no libm)         │         │  _nightshift_live/ (episode ep.k)  │
 │  ARM two-ring KV  ·  Frobenius lift│         │  memory-okf*/  (LUT→sum→full, sha) │
 │  L1 ABI (forward + kvdecode verbs) │         │  _current_conversation.json (short)│
 └───────────────────────────────────┘         └──────────────────────────────────┘

   FORWARD AXIS (re-elevated 2026-07-01):  SP-SWARM / DHT  =  private, signed, content-addressed
   replication of the MEM-OKF store across the operator's nodes (rides byte-exact addressing +
   the receipt ledger; audited crypto, invite-only mesh).  Blueprint: PPT-LAT-DESIGN-SWARM-MEMORY-MESH.md
```

Full subsystem-by-subsystem detail: [`papers/PPT-LAT-KEYSTONE.md`](papers/PPT-LAT-KEYSTONE.md).

## Doc navigation (read in this order)

1. **[`papers/START-HERE.md`](papers/START-HERE.md)** — the 2-minute navigable map (5 repos, doc set, anti-rebuild law, roadmap). *Start every session here.*
2. **[`papers/VERIFIED-SCOREBOARD.md`](papers/VERIFIED-SCOREBOARD.md)** — what is actually built (commit + gate per claim) and what is open. Receipts-checked 2026-07-01 (9 VERIFIED · 1 PARTIAL · 0 false-greens). *For status.*
3. **[`papers/PPT-LAT-KEYSTONE.md`](papers/PPT-LAT-KEYSTONE.md)** — the detailed current-state map of the whole organism, end to end.
4. **[`papers/PPT-LAT-Roadmap.md`](papers/PPT-LAT-Roadmap.md)** — the forward plan (the axes below).
5. **[`papers/PPT-LAT-FINDINGS-LEDGER.md`](papers/PPT-LAT-FINDINGS-LEDGER.md)** — the measured constants / layers / levers / boundaries + the per-test ledger (which layer, what τ, what K, where the lever is — without re-deriving).
6. **[`papers/PPT-LAT-ADR-002-DECIDE-EXECUTE-SPINE.md`](papers/PPT-LAT-ADR-002-DECIDE-EXECUTE-SPINE.md)** — the governing architecture law (decide in latent, execute in clean text, never fuse, deciders don't execute).

Supporting: `papers/PPT-LAT-RFC-001-Universal-Discrete-Architecture.md` (north-star architecture),
`papers/PPT-LAT-STATE.md` (the proven record / "20th rewrite" ledger),
`papers/PPT-LAT-Theory.md` (the math), `papers/PPT-LAT-FRAMEWORK-API.md` (+ grep index
`papers/PPT-LAT-FRAMEWORK-INDEX.md`) for the call surface, and the per-lane `papers/CONTRACT-*.md`
run records. Session bootstrap for agents: `prompt.md` + `AGENTS.md`. Human-readable synthesis:
`CURRENT-STATE-OF-PROJECT.md`.

**Supersession order when documents disagree:** VERIFIED-SCOREBOARD > KEYSTONE > STATE > contract
run records > Roadmap amendments > Roadmap body. The papers are scaffolding, amendable when reality
contradicts them — except the L1 ABI and `.sp-model` specs, which are frozen.

## The forward roadmap — the axes

1. **Sovereign Telepathy** — make cross-family delegation fully in-engine (native Qwen transmit); v1 is DONE (TELE-15/16 GREEN, wired into `/v1/chat`).
2. **CRT residue split** — run a model across discrete devices by shipping CRT residues, not float tensors (RFC-001 Trick #1); the 2-physical-GPU byte-exact check is the one remaining external item.
3. **Absolute faithfulness** — **CLOSED (2026-07-01)** — L5-cosine recall + zero-inference attribute-gate decline (see State one-liner).
4. **Native consolidation** — port the host-Python XBAR tooling + T4 Frobenius of weights down to C/Rust; single-binary deployment.
5. **SP-SWARM / DHT memory mesh (PRIMARY, re-elevated 2026-07-01) — NOW BUILT (L0–L4 GREEN, 2026-07-01)** — private, content-addressed, signed replication + discovery of MEM-OKF across the operator's nodes (rides byte-exact content addressing + the receipt ledger; invite-only mesh, audited crypto). The full stack is built + gated (9 `G-SWARM-*` gates), Rust↔Python byte-parity, integrated into `sp-daemon` behind a default-off `swarm` feature + a standalone `sp-swarm-node` bin; **remaining = multi-host deployment only.** Blueprint (*why*): `papers/PPT-LAT-DESIGN-SWARM-MEMORY-MESH.md`; call surface (*how*: `sp_swarm` crate, `SP_SWARM_*` flags, QUIC/Ed25519 wire, gates): `papers/PPT-LAT-MESH-API.md`.

## The knowledge system (this repo owns the OKFS tooling)

Six months in, the binding constraint stopped being code and became *knowledge discipline* — sessions
kept rebuilding subsystems that already existed (12+ times). The answer is a small, content-addressed
knowledge layer, and **this repo owns its tooling**.

- **SP-OKF** — Shannon-Prime's profile of Google's **Open Knowledge Format v0.1**. Every knowledge
  `.md` carries `type` + receipts-first frontmatter (`sp_status/sp_gate/sp_commit/sp_repro`). New
  `type`s register in `papers/SP-OKF-PROFILE.md` §2 first. Gate **`G-OKF-CONFORM`**:
  ```bash
  python tools/okf_validate.py papers      # GREEN 155/155
  ```
- **MEM-OKF** — the content-addressed, tiered (**LUT → summary → full**) **anti-rebuild memory**,
  one format for agent facts AND XBAR/NIGHTSHIFT episodes (sha256 for text, C2-LSH-sig for latent
  episodes). Spec `papers/MEMORY-OKF-PROFILE.md`; store `memory-okf/`; tool `tools/okf_mem.py`.
  **The `okf_mem lookup` pre-flight is BINDING before building anything** — a new file for an
  existing capability is a *defect*:
  ```bash
  python tools/okf_mem.py lookup --root memory-okf "<keyword>"   # anti-rebuild pre-flight
  python tools/okf_mem.py verify --root memory-okf               # gate G-MEM-OKF-CONFORM
  ```
- **HISTORY** (`HISTORY.md`, `tools/okf_history.py`) — a hashed Tier-0 commit LUT; `git show <hash>`
  is the Tier-2 store.

## The unique features (each with a gate)

- **Byte-exact exact-integer O_K arithmetic** — the whole Gemma-4-12B forward runs exact-integer
  on the dual-prime CRT-NTT (the 4 nonlinear islands — RMSNorm/softmax/GELU/RoPE — plus attention),
  behind default-off `SP_BYTEEXACT`. Cross-machine-deterministic, auditable — **not** compression.
  `G-BYTEEXACT-FORWARD-12B` (OFF = PPL 4.6665 byte-identical null floor / ON = 4.6569 parity /
  run-to-run bit-identical). Detail: `papers/CONTRACT-BYTEEXACT-forward.md`.
- **Faithful L5-cosine recall** — the fact signal is layer-localized (global layer 5); a live
  cosine selector obeys episodic memory over parametric priors at **86.89%** paraphrase
  (`SP_RECALL_L5` τ=0.30, `G-L5-RECALL-LIVE`), with a **zero-inference attribute-gate decline**
  closing the zero-prior/private-data hole (`G-SNE-ATTRGATE-ZEROINF`). The generative judge is
  PARKED (earned nothing over the cheap levers). Full map: `papers/PPT-LAT-FINDINGS-LEDGER.md`.
- **Model-owned memory agency** — the served model **decides what it keeps**: STORE (NIGHTSHIFT
  capture), FORGET (`SP_FORGET`), and DECIDE+MERGE (`SP_DECIDE`). Gates `G-FORGET`/`G-DECIDE`/`G-MERGE`.
- **The autonomous librarian (W_c)** — a learned head does live instance-level episodic recall for
  novel high-entropy needles, with clean foreign-reject. `G-CHAT-B3-WC-DEPLOY`/`-DIV2`.
- **Cross-family Telepathy** — a `LatentBridge` decides route in latent and delegates execution to a
  qwen coder on **clean text** (never fusing). Live two-stage delegate wired into `/v1/chat`
  (`SP_TELEPATHY_CHAT`, default-off). `G-TELEPATHY-LIVE` / `G-TELEPATHY-CHAT-LIVE`. Honest scope =
  gist/intent routing + clean-text execution, NOT latent verbatim.
- **Ephemeral tool-calling harness** — the model emits `<tool name="…">{json}</tool>` in plain
  text; the harness parses, runs, and feeds the result back (ReAct, no native tool channel). Live:
  `calculate` → 4183, `run_python` → 5050. Harness gates `G-HARNESS-TOOLCALL-E2E` and up.
- **SP-SWARM private memory mesh (L0–L4)** — replication + discovery over the content-addressed
  MEM-OKF store (not a new store): L1 addressing, L2 have/want replication with verify-on-arrival,
  L3 Ed25519 provenance vs an invite-only roster, L0 QUIC (quinn/rustls) + Ed25519 mutual handshake,
  L4 C2-SimHash discovery gossip (`SIM` shortlist → exact-fetch). The `sp_swarm` Rust crate (in the
  engine repo) is byte-parity-proven vs the Python prototype and integrated into `sp-daemon` behind a
  default-off `swarm` feature. Gates `G-SWARM-*` (9). Call surface: `papers/PPT-LAT-MESH-API.md`.

## Honest tier summary (the served system vs the gated experiments)

`gated-GREEN` is **not** GREEN-LIVE: a default-off flag is a null floor until set. The full verified
scoreboard is `papers/VERIFIED-SCOREBOARD.md`; the proven record is `papers/PPT-LAT-STATE.md`.

| Capability | Tier | Evidence |
|---|---|---|
| Coherent + O(1)-context **12B chat** with learned recall + memory agency (forget/decide/merge) + tool calling | **GREEN-LIVE** (served) | `CONTRACT-CHAT-FULLSTACK`, `G-CHAT-*`, `G-FORGET`/`G-DECIDE`/`G-MERGE`, harness `G-HARNESS-*` |
| **Faithful L5-cosine recall** + zero-inference attribute-gate decline | **GREEN-LIVE, default-off** | `G-L5-RECALL-LIVE` (86.89%), `G-SNE-ATTRGATE-ZEROINF` |
| **Byte-exact exact-integer forward** (`SP_BYTEEXACT`) | **gated-GREEN / default-off** | `G-BYTEEXACT-FORWARD-12B` |
| **Cross-family Telepathy** (two-stage delegate, wired into `/v1/chat`) | **gated-GREEN / default-off** | `G-TELEPATHY-LIVE`, `G-TELEPATHY-CHAT-LIVE` |
| **NIGHTSHIFT offline curator** (`SP_NIGHTSHIFT_OFFLINE`) | **gated-GREEN / default-off** — criteria 1-4 synthetic + criterion-5 (B4 provenance/distributional fix) CLOSED live | `G-NIGHTSHIFT-CURATOR` + `G-CHAT-B4-NIGHTSHIFT-provenance` (live==curated 9.858; novel in-band + foreign-reject) |
| **Generative judge** / native diffusion judge (26B selector) | **PARKED / in the drawer** — superseded by L5-direct+τ | `G-HARDFOREIGN-JUDGE`, FINDINGS-LEDGER §3 |
| **SP-SWARM private memory mesh** (L0–L4: QUIC transport, content addressing, replication, Ed25519 provenance, C2 discovery) | **gated-GREEN / default-off** — L0–L4 complete, integrated; remaining = multi-host deploy | `G-SWARM-*` (9), `PPT-LAT-MESH-API.md` |

## Methodology (why the numbers are believable)

1. **Bit-exact when off.** Every mechanism is a flag, a strict no-op by default; the baseline is provably the unmodified model.
2. **No number without a command.** Nothing enters a paper/README/ledger unless it reproduces from a stated command (model, corpus, flags, gate, commit).
3. **Scope travels with the number.** Every figure carries its model, ctx, corpus, and what it does NOT generalize to.
4. **No silent gate revisions.** Surface upstream; amend the contract formally — never retune fixtures or footnote a PASS.
5. **Falsification pre-stated; honest negatives stay.** The 32k NIAH MISS, the falsified recall signals, the parked judge, the inert content-side number-theory levers — all on the record with their receipts.

**Recurring lesson, banked:** served-model misbehavior is almost always *ours* (template / decode /
sampler / forward / prompt), not the weights — verify vs llama.cpp + our PPL first.

## Getting started

```bash
git clone https://github.com/nihilistau/shannon-prime-lattice.git
git clone https://github.com/nihilistau/shannon-prime-system.git
git clone --recurse-submodules https://github.com/nihilistau/shannon-prime-system-engine.git
git clone https://github.com/nihilistau/shannon-prime-harness.git
```

Run the live organism (from clean): start the daemon (`shannon-prime-system-engine/run_console.bat`
→ `http://127.0.0.1:3000/`), seed capabilities once
(`python tools/xbar_lsh/_seed_capabilities.py`), then run the agency + consolidation scheduler
alongside it (`shannon-prime-harness/run_agency.py`). Full procedure: `papers/PPT-LAT-KEYSTONE.md`.

## Hard rules

- **Anti-contamination.** Do NOT read, copy, or vendor code from the archived `shannon-prime/` or `shannon-prime-engine/` repos. The lattice is a clean rebuild.
- **Anti-rebuild pre-flight is binding.** `okf_mem.py lookup` + `grep` the tree before building anything (see the knowledge-system section).
- **No silent gate revisions.** Surface upstream; amendments land formally with rationale.
- **Terminology is load-bearing.** Lattice · `⪯_d` · KSTE · ARM · CRT-NTT · Spinor block · Frobenius lift · OK_Q4B · Exec / Memo · decide→execute · L5 selector · attribute-gate · NIGHTSHIFT · KAIROS · Telepathy · SP-SWARM.
- **Worktrees per concurrent agent.** 2+ agents on one repo → each in its own `git worktree add`.
- **Git on these repos: native PowerShell, not the Linux mount** (the mount CRLF-churns + locks).

---

*Umbrella / docs / OKFS repo. State current as of 2026-07-01 (faithfulness closed end-to-end;
SWARM/DHT re-elevated primary). Built by the operator (Knack) + Claude + Gemini. Receipts-first;
honest negatives attached; default-off is the null floor.*
