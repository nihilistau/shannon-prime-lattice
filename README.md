# shannon-prime-lattice — the umbrella

> **Shannon-Prime** is a fully local, byte-exact, auditable language-model **organism**. It serves
> Google's **Gemma-4-12B** (OK_Q4B quant) on a single **RTX 2060**, through **our own** inference
> engine, on an **exact-integer arithmetic substrate** (`O_K = Z[(1+√−163)/2]`, dual-prime
> negacyclic CRT-NTT), with a working memory it **owns**: it learns facts from conversation,
> recalls them, **forgets / supersedes / merges** them on its own judgement, calls tools and runs
> code, stores whole conversations both complete and summarized, and — between turns, on a
> heartbeat — consolidates the live conversation and tidies its memory. No cloud, no third-party
> inference, no telemetry.

This repo is the **developer umbrella**: papers, contracts, the RFC, the roadmap, the OKFS/MEM-OKF
tooling, integration receipts, and the session bootstrap. Code lives in the companion repos.

**Read this first:** [`papers/PPT-LAT-KEYSTONE.md`](papers/PPT-LAT-KEYSTONE.md) — the canonical,
current, complete description of the whole system at the **KEYSTONE** milestone (2026-06-25). It is
the map; everything else is detail you pull only when you need it. Here for the results, not the
source? Start at the public, receipts-first front door:
**[Position Is Arithmetic](https://github.com/nihilistau/Position_Is_Arithmetic)**
(live: https://nihilistau.github.io/Position_Is_Arithmetic/).

License: MIT (`LICENSE`). Discord: [Shannon-Prime-Lattice](https://discord.gg/rre9XZmvV).

---

## The thesis

*Position Is Arithmetic.* An LLM's container can be made **exact arithmetic**
(cross-machine-deterministic, auditable) without losing quality, and memory can be
**content/position-addressed** rather than token-shaped. **Byte-exact = exact arithmetic /
cross-machine determinism / auditability — explicitly NOT compression.** Every structure-on-content
compression lever the project tried is a *measured negative*, kept on the record as an honest
negative; the win is the *container*. Every mechanism is a flag that is a **strict no-op when unset**
(the "null floor"); every number has a reproducing command and a gate.

## The Latent Interceptor & Telepathy (post-KEYSTONE)

The finetuned EAGLE **draft body** is repurposed as a **latent-native router** — a shared 1024-d body plus
tiny action/memory/tool heads that decide, recall, and route **on the latent manifold, without a tokenizer
round-trip**. The heads are **near-miss-hardened**: on isolated cross-distribution tests they never fire a
tool/action or write a memory on idle chatter (false-fire **0.000**; tool head 1.000, action head 0.979,
KEEP recall 1.000).

**Telepathy** is the named framework for **tokenizer-free latent→latent transfer between models** — a
`LatentBridge` (`src → adapter → dst`) plus a pluggable adapter registry. The first **cross-family** bridge
is proven: **gemma-3n-E2B ↔ qwen2.5-coder-0.5b** via a simple ridge affine map — geometry alignment
(retrieval@1 **1.000**, round-trip **0.891**), foreign rejection (AUC **0.999**), and generation
**steering** (an injected mapped latent measurably steers the destination, steer-accuracy **1.000** vs a
matched control).

> **Honest scope:** what's proven is *activation steering*, geometry alignment, and foreign rejection — **not**
> verbatim text-forcing (a single pooled latent can't force exact output, and we don't claim it).
>
> **Licensing (by design):** Telepathy is a **separately-licensed, proprietary** component layered on the
> MIT substrate (the base stays MIT). Commercial use is gated by a **fail-closed license-key + cryptographic
> attestation** model — without a valid license the bridge runs inert; the protections only ever disable the
> bridge's *own* operation and never reach the host. *(Enforcement mechanisms are SPEC; the commercial
> boundary is policy from the jump.)*

Spec: [`papers/PPT-LAT-TELEPATHY-LatentBridge-spec.md`](papers/PPT-LAT-TELEPATHY-LatentBridge-spec.md).

## The five repositories

| Repo | Role | Lang | Entry |
|---|---|---|---|
| **shannon-prime-lattice** (this) | umbrella: papers, contracts, RFC, roadmap, OKFS/MEM-OKF, the KEYSTONE map | md/py | `prompt.md`, `papers/` |
| **shannon-prime-system** | the math core (no engine deps): O_K, NTT-CRT, exact islands, ARM two-ring, the frozen L1 ABI | C | `include/sp/sp_l1.h`, `core/` |
| **shannon-prime-system-engine** | the inference engine + backends + the resident daemon + the memory agency | C/CUDA/Rust | `tools/sp_daemon/`, `src/backends/cuda/` |
| **shannon-prime-harness** | the agent harness: tool calling, conversation memory, the agency loop (CosySim runtime re-hosted on sp-daemon) | Python | `harness/`, `run_agency.py` |
| **Position_Is_Arithmetic** | the public face: receipts-first papers + `LEDGER.md` | md | `README.md`, `SERIES.md`, `papers/` |

`shannon-prime-system` is also vendored into the engine as the `lib/shannon-prime-system` submodule —
`git fetch` + check behind before building (the two can diverge).

## Architecture (the whole stack)

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
 │  O_K = Z[(1+√−163)/2]              │         ┌──────────────────────────────────┐
 │  dual-prime NTT-CRT (q1,q2≈2^60)   │         │  MEMORY                            │
 │  exact_islands (RMS/softmax/GELU/  │         │  registry.jsonl  (facts, mid/long) │
 │     RoPE, CORDIC, no libm)         │         │  _nightshift_live/ (episode ep.k)  │
 │  ARM two-ring KV  ·  Frobenius lift│         │  memory-okf*/  (LUT→sum→full, sha) │
 │  L1 ABI (forward + kvdecode verbs) │         │  _current_conversation.json (short)│
 └───────────────────────────────────┘         └──────────────────────────────────┘
```

Full subsystem-by-subsystem detail: [`papers/PPT-LAT-KEYSTONE.md`](papers/PPT-LAT-KEYSTONE.md) §3–§6.

## The unique features (each with a gate)

- **Byte-exact exact-integer O_K arithmetic** — the whole Gemma-4-12B forward runs exact-integer
  on the dual-prime CRT-NTT (the 4 nonlinear islands — RMSNorm/softmax/GELU/RoPE — plus attention),
  behind the default-off `SP_BYTEEXACT` flag. Cross-machine-deterministic, auditable — **not**
  compression. `G-BYTEEXACT-FORWARD-12B` (OFF = PPL 4.6665 byte-identical null floor / ON = 4.6569
  parity / run-to-run bit-identical). Detail: `papers/CONTRACT-BYTEEXACT-forward.md`.

- **Model-owned memory agency** — the served model **decides what it keeps**: STORE (NIGHTSHIFT
  capture), FORGET (`SP_FORGET`), and DECIDE+MERGE (`SP_DECIDE`: supersede a changed fact, or
  consolidate two complementary facts into one synthesized truth). Gates `G-FORGET` / `G-DECIDE` /
  `G-MERGE`. Default-off = null floor.

- **The autonomous librarian (W_c)** — a learned head does live instance-level episodic recall on
  the served chat, with clean foreign-reject. `G-CHAT-B3-WC-DEPLOY` / `-DIV2` (360/361 recall +
  50/50 reject, int16 == f32). The win is a *learned head on a diverse corpus*, not a hand-designed
  signal (~10 hand-designed signals are honest negatives).

- **Ephemeral tool-calling harness** — the model emits `<tool name="…">{json}</tool>` in plain
  text; the harness parses, runs, and feeds the result back (ReAct, no native tool channel). Live:
  `calculate` → 4183, `run_python` → 5050. Harness gates `G-HARNESS-TOOLCALL-E2E` (H2) and on up.

- **Tiered MEM-OKF conversation memory** — three sha256-/C2-addressed tiers (SHORT live conversation
  → MID extracted facts → LONG full+summary conversations), with a binding *look-it-up-before-you-
  build* anti-rebuild pre-flight. Spec: `papers/MEMORY-OKF-PROFILE.md`, tool `tools/okf_mem.py`.

## Honest tier summary (the served system vs the gated experiments)

`gated-GREEN` is **not** GREEN-LIVE: a default-off flag is a null floor until set.

| Capability | Tier | Evidence |
|---|---|---|
| Coherent + byte-exact + O(1)-context **12B chat** with learned **W_c** recall + memory agency (forget/decide/merge) + tool calling | **GREEN-LIVE** (served) | `CONTRACT-CHAT-FULLSTACK`, `G-CHAT-B3-WC-DEPLOY`, `G-FORGET`/`G-DECIDE`/`G-MERGE`, harness `G-HARNESS-*` |
| **Byte-exact exact-integer forward** (`SP_BYTEEXACT`) | **gated-GREEN / default-off** | `G-BYTEEXACT-FORWARD-12B` |
| **Production recall/reject judge** — deterministic token-overlap (Jaccard) verifier @≈0.6 (83% recall / 95% reject on a CPU string op) | **GREEN** | `project_judge_deterministic_gate`, `G-JUDGE-BATTERY` |
| **NIGHTSHIFT offline curator** (`SP_NIGHTSHIFT_OFFLINE`) | **gated-GREEN on the SYNTHETIC gate / default-off** | `G-NIGHTSHIFT-CURATOR` (criteria 1-4) |
| Native **diffusion judge** (DiffusionGemma 26B selector) | **UNPROVEN / in the drawer** — superseded by the deterministic verifier above | `STATUS-MAP` §4 |

The full box-by-box tier map is `papers/STATUS-MAP-2026-06-21.md`; the proven record is
`papers/PPT-LAT-STATE.md`.

## Doc map — which file answers which question

| Need | Read |
|---|---|
| **The whole system, current + complete** | **`papers/PPT-LAT-KEYSTONE.md`** (the foundation — read first) |
| API reference | `papers/PPT-LAT-KEYSTONE-API.md` |
| Agent entry + navigation + the MEM-OKF pre-flight | `AGENTS.md` |
| Session bootstrap (agents) | `prompt.md` |
| The proven record / the math | `papers/PPT-LAT-STATE.md` / `papers/PPT-LAT-Theory.md` |
| Human-readable synthesis of where things stand | `CURRENT-STATE-OF-PROJECT.md` |
| The current architecture (rings, XBAR, NIGHTSHIFT) | `papers/RFC-XBAR-auditable-latent-crossbar.md` |
| Forward specs + run records per lane | `papers/CONTRACT-*.md` |
| Byte-exact / O_K | `papers/CONTRACT-BYTEEXACT-forward.md`; system `core/exact_islands/` |
| Memory agency / tool calling / conversation memory | engine `routes.rs`; harness `CLAUDE.md`, `docs/SPEC-TOOL-CALLING.md` |
| Knowledge formats | `papers/SP-OKF-PROFILE.md`, `papers/MEMORY-OKF-PROFILE.md` |
| Commit history (hashed Tier-0 LUT) | `HISTORY.md` (the git short-hash IS the address) |
| Public claims + reproduce commands | `Position_Is_Arithmetic/LEDGER.md` + `METHODOLOGY.md` |

Supersession order when documents disagree: **KEYSTONE > STATE > contract run records > Roadmap
amendments > Roadmap body**. The papers are scaffolding, amendable when reality contradicts them —
except the L1 ABI and `.sp-model` specs, which are frozen.

## The knowledge system (this repo owns the OKFS tooling)

Six months in, the binding constraint stopped being code and became *knowledge discipline* — sessions
kept rebuilding subsystems that already existed. The answer is a small, content-addressed knowledge
layer, and this repo owns its tooling.

- **SP-OKF** (`papers/SP-OKF-PROFILE.md`, `tools/okf_validate.py`) — Shannon-Prime's profile of
  Google's **Open Knowledge Format v0.1**. Every knowledge `.md` carries `type` + receipts-first
  frontmatter (`sp_status/sp_gate/sp_commit/sp_repro`); gate `G-OKF-CONFORM`.
- **MEM-OKF** (`papers/MEMORY-OKF-PROFILE.md`, `tools/okf_mem.py`, `memory-okf/`) — the
  content-addressed, tiered (**LUT → summary → full**) **anti-rebuild memory**, one format for agent
  facts AND XBAR/NIGHTSHIFT episodes. **The `okf_mem lookup` pre-flight is binding** before building
  anything (a new file for an existing capability is a defect). Gate `G-MEM-OKF-CONFORM`.
- **HISTORY** (`HISTORY.md`, `tools/okf_history.py`) — a hashed Tier-0 commit LUT; `git show <hash>`
  is the Tier-2 store.

## Methodology (why the numbers are believable)

1. **Bit-exact when off.** Every mechanism is a flag, a strict no-op by default; the baseline is
   provably the unmodified model.
2. **No number without a command.** Nothing enters a paper/README/ledger unless it reproduces from a
   stated command (model, corpus, flags, gate, commit).
3. **Scope travels with the number.** Every figure carries its model, ctx, corpus, and what it does
   NOT generalize to.
4. **No silent gate revisions.** Surface upstream; amend the contract formally — never retune
   fixtures or footnote a PASS.
5. **Falsification pre-stated; honest negatives stay.** The 32k NIAH MISS, the falsified recall
   signals, the inert content-side number-theory levers — all on the record with their receipts.

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
alongside it (`shannon-prime-harness/run_agency.py`). Full procedure: `PPT-LAT-KEYSTONE.md` §10.

## Hard rules

- **Anti-contamination.** Do NOT read, copy, or vendor code from the archived `shannon-prime/` or
  `shannon-prime-engine/` repos. The lattice is a clean rebuild.
- **No silent gate revisions.** Surface upstream; amendments land formally with rationale.
- **Terminology is load-bearing.** Lattice · `⪯_d` · KSTE · ARM · CRT-NTT · Spinor block · Frobenius
  lift · OK_Q4B · Exec / Memo / Ring 1/2/2′/3 · XBAR lanes P/C/M/N · NIGHTSHIFT · KAIROS.
- **Worktrees per concurrent agent.** 2+ agents on one repo → each in its own `git worktree add`.
- **Git on these repos: native PowerShell, not the Linux mount** (the mount CRLF-churns + locks).

---

*KEYSTONE-1, 2026-06-25. Built by the operator (Knack) + Claude + Gemini. Receipts-first; honest
negatives attached; default-off is the null floor.*
