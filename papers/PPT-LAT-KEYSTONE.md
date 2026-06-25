---
type: foundation
title: "Shannon-Prime — KEYSTONE: the complete system, as built"
description: "The canonical, current, complete description of Shannon-Prime at the KEYSTONE milestone (keystone-1, 2026-06-25): the byte-exact O_K engine + the two-ring/XBAR memory + the autonomous memory agency + the tool-calling harness + the conversation-memory tiers, integrated into one self-supporting organism. The Rosetta stone: read this first, follow the links only as you need them."
tags: [keystone, foundation, architecture, memory, harness, agency, navigation, okf]
timestamp: 2026-06-25T00:00:00Z
resource: shannon-prime-lattice
sp_status: GREEN-LIVE
sp_gate: KEYSTONE-1
sp_commit: keystone-1
sp_repro: "see §10 (Run it) + §9 (Gate index)"
---

# Shannon-Prime — KEYSTONE

> **Read order for an agent or human:** this file is the map. Each section is self-contained.
> Pull a subsystem's detail only when you need it (the §11 navigation table says where it lives).
> Nothing here needs the whole tree in context — that is the point.

## 0. What Shannon-Prime is (90 seconds)

Shannon-Prime is a **fully local, byte-exact, auditable language-model organism**. It serves
Google's **Gemma-4-12B** (OK_Q4B quant) on a single RTX 2060, through **our own** inference
engine, on an **exact-integer arithmetic substrate** (`O_K = Z[(1+√-163)/2]`, dual-prime
negacyclic CRT-NTT), with a **working memory it owns**: it learns facts from conversation,
recalls them, forgets and supersedes and merges them on its own judgement, stores whole
conversations both complete and summarized, calls tools and runs code, and — between turns,
on a heartbeat — consolidates the live conversation and tidies its memory. Every mechanism
is a flag that is a **strict no-op when unset** (the "null floor"); every number has a
reproducing command and a gate. No cloud, no third-party inference, no telemetry.

**The thesis** (public name: *Position Is Arithmetic*): an LLM's container can be made
**exact arithmetic** (cross-machine-deterministic, auditable) without losing quality, and
memory can be **content/position-addressed** rather than token-shaped. Structure-on-content
compression is a **measured negative** (kept as honest negatives); the win is the *container*.

## 1. The KEYSTONE milestone (keystone-1)

KEYSTONE is the night (2026-06-25) the arches locked together. Before it, the pieces were
proven in isolation (byte-exact forward, the two-ring memory, the learned librarian, the
diffusion judge). KEYSTONE is the **integration**: the served chat now

- holds the **conversation thread faithfully** (system-prompt priming fixed parametric drift),
- **learns** facts as you state them, **recalls** them, and **forgets / supersedes / merges**
  them on the model's own verdict (LAYER-2 forget, LAYER-3 decide+merge),
- **calls tools** and **runs Python** through the re-hosted harness (ephemeral text-protocol),
- **manages its own memory** in an autonomous agency round on a **heartbeat** (KAIROS tick),
- stores conversations in **tiers** — live (short) → extracted facts (mid) → full+summary
  MEM-OKF (long) — gist by default, dig deeper on demand,
- knows **what it is and how to use itself** (system prompt + a recallable capabilities corpus),

…and the loop closes with **zero manual steps**: the daemon writes each turn's conversation to
disk, the agency scheduler consolidates it on its tick.

This document is the foundation we build forward on. Older roadmaps/RFCs are archived (§11);
this supersedes their "current state" sections.

## 2. The five repositories

| Repo | Role | Lang | Canonical entry |
|---|---|---|---|
| **shannon-prime-lattice** | umbrella: papers, contracts, RFC, roadmap, OKFS/MEM-OKF, this doc | md/py | `prompt.md`, `papers/` |
| **shannon-prime-system** | the math core (no engine deps): O_K, NTT-CRT, exact islands, ARM two-ring, L1 ABI | C | `include/sp/sp_l1.h`, `core/` |
| **shannon-prime-system-engine** | the inference engine + backends + the resident daemon + memory agency | C/CUDA/Rust | `tools/sp_daemon/`, `src/backends/cuda/` |
| **shannon-prime-harness** | the agent harness: tool calling, conversation memory, the agency loop (CosySim runtime re-hosted on sp-daemon) | Python | `harness/`, `run_agency.py` |
| **Position_Is_Arithmetic** | the public face: receipts-first papers + LEDGER | md | `README.md`, `SERIES.md`, `papers/` |

`shannon-prime-system` is also vendored into the engine as the `lib/shannon-prime-system`
submodule — `git fetch` + check behind before building (the two can diverge).

## 3. Architecture (the whole stack)

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
 │     ├─ EOT bias (clean stop)        ├─ auto_recall: W_c head → judge →        │
 │     │                               │     text-in-context recite / reject     │
 │     ├─ LAYER-2 FORGET (SP_FORGET)   ├─ NIGHTSHIFT capture (statements→reg)     │
 │     ├─ LAYER-3 DECIDE+MERGE (SP_DECIDE)                                       │
 │     └─ writes the turn → SP_CURRENT_CONVO (the consolidation hook)            │
 │  registers L1 backends:  forward (prefill) + kvdecode (token-by-token)        │
 └───────────────┬───────────────────────────────────────────────┬─────────────┘
                 │ L1 ABI (sp_l1.h)                                │ POST /v1/chat
                 ▼                                                 ▼
 ┌───────────────────────────────────┐         ┌──────────────────────────────────┐
 │  ENGINE backends (CUDA/CPU/…)      │         │  HARNESS (Python)                 │
 │  gemma4 forward + decode           │         │  SPDaemonClient ─ to_sp_chat      │
 │  OK_Q4B GEMV (dp4a)                │         │  run_with_tools  <tool …> ReAct   │
 │  SP_BYTEEXACT exact-int islands    │         │  memory tools: list/remember/forget│
 │  diffusiongemma-26B judge (dg_*)   │         │  conversation_memory: tiers + caps │
 └───────────────┬───────────────────┘         │  agency: round + scheduler (KAIROS)│
                 │ consumes                      └──────────────┬───────────────────┘
                 ▼                                              │ reads SP_CURRENT_CONVO
 ┌───────────────────────────────────┐                         │ writes registry + MEM-OKF
 │  MATH CORE (shannon-prime-system)  │                         ▼
 │  O_K = Z[(1+√-163)/2]              │         ┌──────────────────────────────────┐
 │  dual-prime NTT-CRT (q1,q2≈2^60)   │         │  MEMORY                            │
 │  exact_islands (RMS/softmax/GELU/  │         │  registry.jsonl  (facts, mid/long) │
 │     RoPE, CORDIC, no libm)         │         │  _nightshift_live/ (episode ep.k)  │
 │  ARM two-ring KV  ·  Frobenius lift│         │  memory-okf*/  (LUT→sum→full, sha) │
 │  L1 ABI (forward + kvdecode verbs) │         │  _current_conversation.json (short)│
 └───────────────────────────────────┘         └──────────────────────────────────┘
```

## 4. The subsystems (what / where / how it integrates)

- **O_K substrate + byte-exact** (`system/core/ntt_crt`, `core/poly_ring`, `core/exact_islands`;
  engine `SP_BYTEEXACT`). Exact-integer arithmetic on `O_K`, dual-prime negacyclic CRT-NTT
  (primes q1=1073738753, q2=1073732609, M≈2^60 fits u64 → no __int128). The 4 nonlinear islands
  (RMSNorm/softmax/GELU/RoPE) have exact-integer references (RoPE via fixed-point CORDIC, no
  libm). *Byte-exact = exact arithmetic / cross-machine determinism / AUDITABILITY — NOT
  compression.* Gate G-BYTEEXACT-FORWARD-12B (off=4.6665 byte-identical null floor / on=parity,
  run-to-run bit-identical). Detail: `papers/CONTRACT-BYTEEXACT-forward.md`.

- **The engine + daemon** (`engine/src/backends/`, `engine/tools/sp_daemon/`). gemma4 CUDA
  forward + token-by-token decode (per-layer SWA/global, shared-KV, AltUp/PL=0, softcap, OK_Q4B
  dp4a GEMV, CUDA-graph decode). The **universal resident daemon** drives the 12B end-to-end via
  the L1 ABI: prefill (`sp_session_register_forward_backend`) + DECODE (`sp_session_register_
  kvdecode_backend`, the §6b persistent-KV verb). VRAM flat O(1). Detail: `CONTRACT-CHAT-FULLSTACK`.

- **ARM — two-ring KV memory** (`system/core/arm/`). ±1 Rademacher recall router, Ring-1 slot map,
  Ring-2 episode store, recall-hit telemetry, cold-evict. The substrate the episodic memory rides.

- **XBAR — the auditable latent crossbar** (lattice `papers/CONTRACT-XBAR-*`, engine `SP_XBAR_*`,
  `tools/ring3/`). C2 256-bit content signatures, native integer Ring-3 VSA bind on `sp_pr_mul`,
  Frobenius π^k integer episode store. Boundary thesis lives here: O_K wins on the *container*;
  structure-on-content levers are measured-inert (honest negatives kept).

- **The memory agency** (engine `tools/sp_daemon/src/routes.rs`). The model owns its memory:
  - **STORE** — NIGHTSHIFT captures statements (loose admission: skip questions/requests/forget-turns).
  - **FORGET** (`SP_FORGET`) — "forget X" → token-overlap match → drop from live set + rewrite registry.
  - **DECIDE** (`SP_DECIDE`) — on a capturing turn that overlaps an existing memory, a side model-call
    asks the model itself: supersede (`CHANGED=n`, the "cannot both be true at once" test) or
    consolidate (`MERGE:: combined`, drop both + capture the synthesis). Default-off = null floor.
  Gates: G-FORGET, G-DECIDE, G-MERGE. Detail: memory `project_memory_agency_forget`.

- **NIGHTSHIFT — the offline curator** (lattice `CONTRACT-NIGHTSHIFT-CURATOR`, engine
  `run_kairos_curator`). Live capture → (optional) teacher-forced causal-ablation admission
  (TAU=-8: load-bearing facts collapse, parametric ones don't) → conformant MEM-OKF emit.

- **The learned librarian (W_c)** (engine `recall.rs`, `SP_B3_WC`). A learned head does autonomous
  instance-level episodic recall (logsumexp-over-positions, mean-over-heads; (E+1)-way NULL argmax;
  bounded-mass replay). The boundary-thesis win: recall is a *learned head on a diverse corpus*,
  not a hand-designed signal. Paper 24 (the learned librarian).

- **The diffusion judge** (engine `cuda_forward.cu` `dg_*`, diffusiongemma-26B-A4B MoE). A native
  iterative-denoise recall/reject judge; perf levers SP_DG_SCRATCHREUSE (default-on ~1.46x),
  SP_DG_ASYNC (byte-exact ~2x), prefix-KV (~1.6x, answer-lossless). NOTE: the *production* recall
  gate is the **deterministic token-overlap (Jaccard) verifier** @0.6, not the 26B (83%/95% on a
  CPU string op; the 26B cascade was retired). Detail: memory `project_judge_deterministic_gate`.

- **KAIROS — the heartbeat / agency tick** (engine `kairos.rs` stub control plane; the model-driven
  realization is harness `agency.py`). The "auto rounds" where the organism *does things* between
  turns instead of only stopping.

- **The harness** (`shannon-prime-harness/`). CosySim's agent runtime re-hosted on sp-daemon
  (lmstudio stripped). The inference seam is `InferenceConfig.to_sp_chat()` → `SPDaemonClient`
  (`POST /v1/chat`, SSE). **Ephemeral tool calling**: the model emits `<tool name="…">{json}</tool>`
  in plain text, `run_with_tools` parses + executes + feeds back (ReAct loop, no native tool channel
  needed). `ToolSpec.from_callable` derives the schema from a Python signature; `@skill` decorators
  bridge to tools. Memory tools (`skills/memory.py`) + conversation memory + the agency loop.

- **MEM-OKF — content-addressed tiered memory** (`tools/okf_mem.py`; the SP-OKF knowledge format).
  Every object sha256-addressed; three disclosure tiers: **LUT** (index) → **sum/** (gist) →
  **full/** (complete). The conversation tier and the capabilities corpus both ride it. Anti-rebuild
  pre-flight is binding: `okf_mem lookup` before building anything. Spec: `papers/MEMORY-OKF-PROFILE.md`.

## 5. The memory model (the heart of KEYSTONE)

Three tiers, one signature scheme (sha256 / C2-sig) linking them so the model can get the gist
and dig deeper only when needed:

| Tier | What | Where | How it fills |
|---|---|---|---|
| **SHORT** | the live conversation | prefilled `messages` each turn; `_current_conversation.json` | the daemon carries full history (re-prefill); a system prompt makes the model *faithful* to it |
| **MID** | durable facts | `registry.jsonl` (+ `_nightshift_live/ep.k`) | NIGHTSHIFT live capture of statements; harness `consolidate_conversation` extraction; `remember()` (idempotent) |
| **LONG** | whole conversations + capabilities | `memory-okf-conv/` (full+summary), `memory-okf-caps/` | `store_conversation` (sha-linked full/sum); `seed_capabilities` |

**Agency over the tiers:** the model forgets / supersedes / merges facts (LAYER-2/3); the agency
scheduler consolidates the live conversation and tidies memory on its heartbeat. **Recall:**
`recall_conversations(query)` → the gist; `read_conversation(addr)` → the full transcript.

**Seeding & priming.** On init the model is primed about *itself*: (a) a default **system prompt**
(served console `index.html`) states identity + capabilities + the faithfulness rule ("use what
the user said; never substitute a stated fact"); (b) a **capabilities corpus** of recallable
self-knowledge facts seeded into the served registry (`_seed_capabilities.py`); (c) optional
**diverse non-parametric seed facts** (`_seed_mint.py`) that bootstrap recall without priming
performance. Principle: seed facts the model *can't* parametrically know (self / hardware /
operator), so recall is clean proof and any self-model is genuine.

## 6. A turn, end to end (the data flow)

1. Console accumulates `history` (system + user + assistant), POSTs `messages` + knobs to `/v1/chat`.
2. Daemon templates the **full** conversation (gemma4 control tokens 105/106/107), prefills, and —
   if `SP_CURRENT_CONVO` is set — **writes the conversation to disk** (the consolidation hook).
3. If `auto_recall`: the W_c head / judge scores stored episodes; on a confident match it recites
   via **text-in-context**; otherwise it abstains (token-overlap verifier @0.6 guards false fires).
4. Decode streams tokens (SSE `{delta}`), EOT-biased so it stops cleanly.
5. Post-response: NIGHTSHIFT **captures** the user statement (if admitted); LAYER-3 **DECIDE** may
   supersede/merge a related memory.
6. Out of band, on the **KAIROS tick** (harness `run_agency_scheduler`, idle-gated): **consolidate**
   the written conversation (facts → mid, transcript → long) then a **maintenance round** where the
   model curates its own memory. Zero manual steps.

## 7. The knobs (env flags + GUI)

All `SP_*` flags are **default-off = byte-identical null floor**. The GUI knobs live in the served
console (`index.html`, left pane "sampler · knobs") and flow into the `/v1/chat` body.

| Knob | Where | Effect |
|---|---|---|
| `SP_BYTEEXACT` | engine env | exact-integer islands + attention (auditable decode) |
| `SP_EOT_BIAS` / `eot` (GUI) | daemon | logit bias on stop tokens so the model ends cleanly (≈4) |
| `SP_AUTO_RECALL_DEFAULT` / `auto-recall` (GUI) | daemon | autonomous episodic recall on |
| `SP_FORGET` | daemon | LAYER-2 forget primitive |
| `SP_DECIDE` | daemon | LAYER-3 supersede + merge |
| `SP_B4_NIGHTSHIFT` / `SP_NIGHTSHIFT_PERSIST` | daemon | live capture / persist facts across restart |
| `SP_CURRENT_CONVO` | daemon | write the turn's conversation for the consolidator |
| `SP_RECALL_REGISTRY` | daemon + harness | the shared mid/long fact store path |
| `SP_CONV_OKF_ROOT` / `SP_CAPS_OKF_ROOT` | harness | the conversation / capabilities MEM-OKF roots |
| `SP_AGENCY_INTERVAL` / `SP_CURRENT_CONVO` | harness scheduler | tick cadence / conversation to consolidate |
| `temperature/top_p/top_k/rep/max` (GUI) | sampler | standard decode controls (temp 0 = byte-exact-friendly argmax) |

## 8. The API surface

**Daemon (`POST`/`GET` on :3000):** `/v1/chat` (messages|prompt|prompt_tokens + knobs → SSE
`{delta}` ending `[DONE]`), `/v1/abort/{id}`, `/v1/capture` (mint an episode), `/v1/metrics`,
`/v1/mesh/peers`, `/v1/debug/backend_counts`. L1 ABI (`sp_l1.h`): `sp_session_register_forward_
backend`, `sp_session_register_kvdecode_backend` (§6b persistent-KV decode).

**Harness (Python):** `SPDaemonClient.chat / chat_stream`; `InferenceConfig.to_sp_chat`;
`run_with_tools(messages, tools)` + `ToolSpec.from_callable`; `skills.memory.{list_memories,
remember,forget}`; `skills.conversation_memory.{summarize_conversation,store_conversation,
recall_conversations,read_conversation,extract_facts,consolidate_conversation,seed_capabilities,
init_primer}`; `control.agency.{agency_round,run_agency_scheduler,consolidate_current}`.

Full reference: `papers/PPT-LAT-KEYSTONE-API.md`.

## 9. Gate / receipt index (the proof map)

Memory agency: G-FORGET, G-DECIDE, G-MERGE (engine `tests/fixtures/chat_fullstack/`).
Harness: G-HARNESS-DAEMON-E2E (H1), G-HARNESS-TOOLCALL-E2E (H2), G-HARNESS-MEMTOOLS-E2E (H3),
G-HARNESS-AGENCY-E2E (H4), G-HARNESS-KAIROS-TICK (H5), G-HARNESS-CONVMEM (H6), G-HARNESS-LIVE +
G-HARNESS-HOOK-E2E (H7) — all in `shannon-prime-harness/tests/`. Byte-exact:
G-BYTEEXACT-FORWARD-12B. Recall: G-CHAT-B3-WC-DEPLOY. Judge: G-JUDGE-BATTERY. Each receipt has a
`python tests/<gate>.py` (or the contract's repro). Rule: **no number without a command + a row.**

## 10. Run it (live, from clean)

1. Daemon: `_e2e_seed_serve.bat` (port 3000; sets EOT bias, auto-recall, forget, decide, nightshift,
   persist, current-convo, the seed registry).
2. Seed capabilities (once): `python tools/xbar_lsh/_seed_capabilities.py` then restart the daemon.
3. Agency + consolidation: `run_agency.bat` (the harness scheduler, alongside the daemon).
4. Chat: `http://127.0.0.1:3000/` (hard-refresh; the knobs are on the left).
Build: CUDA = VS2019 BuildTools + CUDA, `build-cuda/`, ninja (sm_75 on the 2060); daemon =
`cargo build --release --features wire_cuda_backend`. Git on these repos: **native PowerShell, not
the Linux mount** (the mount CRLF-churns + locks).

## 11. Navigation — where to look for what

| Need | Go to |
|---|---|
| Bootstrap / methodology / operator | lattice `prompt.md`, `CLAUDE.md` |
| Proven state record | lattice `papers/PPT-LAT-STATE.md` |
| This map | lattice `papers/PPT-LAT-KEYSTONE.md` (here) |
| API reference | lattice `papers/PPT-LAT-KEYSTONE-API.md` |
| Memory agency detail | memory `project_memory_agency_forget`; engine `routes.rs` |
| Harness / tool calling | harness `CLAUDE.md`, `docs/SPEC-TOOL-CALLING.md`, `harness/` |
| Tiered conversation memory | harness `skills/conversation_memory.py`; this §5 |
| Byte-exact / O_K | lattice `CONTRACT-BYTEEXACT-forward.md`; system `core/exact_islands/` |
| XBAR / boundary thesis | lattice `CONTRACT-XBAR-*`; Position_Is_Arithmetic papers 18-24 |
| MEM-OKF format | lattice `papers/MEMORY-OKF-PROFILE.md`; `tools/okf_mem.py` |
| RFC / Roadmap (current) | lattice `papers/PPT-LAT-RFC-001-*`, `PPT-LAT-Roadmap.md` |
| Public papers | Position_Is_Arithmetic `SERIES.md`, `papers/`, `LEDGER.md` |
| Historical (archived) | lattice `papers/Archived/`, Position_Is_Arithmetic `Archived/` |

## 12. State & open edges (honest)

**GREEN-LIVE:** byte-exact 12B; coherent served chat; autonomous recall + reject; the full memory
agency (store/forget/decide/merge); the harness end-to-end (daemon, tool calling, python exec,
memory-as-tools, the agency loop + heartbeat tick); tiered conversation memory + capabilities; the
live consolidation hook. ~90% of the envisioned organism.

**Open edges (next):** (1) **persistent O(1) conversation KV** — the daemon re-prefills the whole
conversation each turn (correct but O(n)); the L1 stateful kvdecode verb can make "continue the
cache" true O(1). (2) The external **two-physical-GPU** bit-identical check for byte-exact.
(3) Deeper **faithfulness** — the model still leans on parametric priors over grounding; the
tiered memory (reliable recall) is the structural answer, prompts are the patch. (4) Native-C port
of the host-Python XBAR tooling; T4 Frobenius of the model weights (validated lever, untouched).

**Recurring lesson, banked:** served-model misbehavior is almost always *ours* (template / decode /
sampler / forward / prompt), not the weights — verify vs llama.cpp + our PPL first. And for
meta-cognitive model-calls: frame as **detection, not decision**, and force the answer prefix.

---
*KEYSTONE-1, 2026-06-25. Built by the operator (Knack) + Claude + Gemini. Receipts-first; honest
negatives attached; default-off is the null floor. This is the foundation — build forward from here.*
