---
type: roadmap
title: PPT-LAT-Roadmap — the forward roadmap (post-KEYSTONE)
description: "The clean, forward-facing roadmap for Shannon-Prime after the KEYSTONE milestone (2026-06-25): KEYSTONE is achieved (~90% of the envisioned organism), the DONE pillars are listed, and the four open edges are the next work. The full historical roadmap is archived; PPT-LAT-KEYSTONE.md is the current-state source of truth."
tags: [roadmap, keystone, forward, navigation, okf]
timestamp: 2026-06-25T00:00:00Z
resource: shannon-prime-lattice/papers/PPT-LAT-Roadmap.md
sp_status: GREEN-LIVE
sp_gate: KEYSTONE-1
sp_commit: keystone-1
sp_repro: "see PPT-LAT-KEYSTONE.md §10 (Run it) + §9 (Gate index)"
---

# PPT-LAT-Roadmap (post-KEYSTONE)

**Project:** shannon-prime-lattice · **Authors:** Knack + Claude + Gemini · **License:** MIT (all repos).
**Public front door:** [Position Is Arithmetic](https://github.com/nihilistau/Position_Is_Arithmetic) · [live site](https://nihilistau.github.io/Position_Is_Arithmetic/).

> **Read order.** The current-state source of truth is **[PPT-LAT-KEYSTONE.md](PPT-LAT-KEYSTONE.md)** (the map) + **[PPT-LAT-KEYSTONE-API.md](PPT-LAT-KEYSTONE-API.md)** (the call surface). This roadmap is the short forward-plan that sits on top of them. The pre-KEYSTONE roadmap (the full ~8,500-line phase history) is archived at **[Archived/PPT-LAT-Roadmap-pre-keystone.md](Archived/PPT-LAT-Roadmap-pre-keystone.md)** — read it only for per-phase gate definitions and historical context, never as current state.

---

## 0. Status — KEYSTONE is achieved (~90% of the organism)

KEYSTONE (keystone-1, 2026-06-25) is the night the arches locked together: the pieces that were
proven in isolation — the byte-exact O_K forward, the two-ring/XBAR memory, the learned librarian,
the diffusion judge, the agent harness — were **integrated into one self-supporting organism**. The
served Gemma-4-12B chat now holds the conversation faithfully, learns/recalls/forgets/supersedes/
merges facts on its own judgement, calls tools and runs Python, manages its own memory on a
heartbeat, and stores conversations in tiers — and the loop closes with **zero manual steps**.

**Every mechanism is a flag that is a strict no-op when unset (the null floor); every number has a
reproducing command and a gate.** This roadmap supersedes the "current state" of the archived one.

---

## 1. DONE — the pillars that are built, gated, and (where applicable) live

| Pillar | What it is | Gate(s) | State |
|---|---|---|---|
| **Byte-exact O_K forward** | The whole Gemma-4-12B forward on exact-integer `O_K = Z[(1+√-163)/2]` / dual-prime CRT-NTT; the 4 nonlinear islands (RMSNorm/softmax/GELU/RoPE) as exact-integer (CORDIC RoPE, no libm). Byte-exact = exact arithmetic / cross-machine determinism / AUDITABILITY, NOT compression. | G-BYTEEXACT-FORWARD-12B (off=4.6665 byte-identical null floor / on=parity / run-to-run bit-identical) | GREEN |
| **Coherent served chat** | Real 12B chat through the full stack on a single latent entry point — coherent, reproducible, byte-exact, O(1)-context. | G-CHAT-FULLSTACK | GREEN-LIVE |
| **Autonomous recall + reject** | The learned W_c librarian does instance-level episodic recall with clean foreign-reject, live on the served chat. | G-CHAT-B3-WC-DEPLOY (matched→RECALL / foreign→NULL→clean) | GREEN-LIVE |
| **Memory agency — FORGET / DECIDE / MERGE** | The model owns its memory: forget on intent, supersede a changed fact, consolidate two complementary facts into one synthesized truth. Default-off = null floor. | G-FORGET, G-DECIDE, G-MERGE | GREEN-LIVE |
| **Tool-calling harness (H1–H7)** | CosySim runtime re-hosted on sp-daemon: ephemeral text-protocol tool calling + Python exec, memory-as-tools, the agency loop, the KAIROS heartbeat tick, tiered conversation memory, the live consolidation hook. | G-HARNESS-{DAEMON,TOOLCALL,MEMTOOLS,AGENCY,KAIROS-TICK,CONVMEM,HOOK}-E2E | GREEN |
| **Tiered conversation memory** | SHORT (live convo, re-prefilled + faithfulness prompt) → MID (extracted facts, registry + ep.k) → LONG (full+summary MEM-OKF), one sha256/C2-sig scheme linking the tiers. | G-HARNESS-CONVMEM-E2E | GREEN |
| **Live consolidation loop** | The daemon writes each turn to disk; the KAIROS scheduler consolidates it + runs a maintenance round on its tick — zero manual steps. | G-HARNESS-HOOK-E2E (H7) | GREEN |
| **Deterministic recall/reject judge** | The production recall gate is a deterministic token-overlap (Jaccard) verifier @~0.6, not the 26B (83%/95% on a CPU string op; the 26B cascade retired). | G-JUDGE-BATTERY | GREEN |

Foundation context (the substrate these ride on): the two-ring ARM KV memory, the XBAR auditable
latent crossbar (C2 256-bit sigs, native integer Ring-3 VSA bind, Frobenius Ring-2 store), NIGHTSHIFT
the offline curator, KAIROS the resident kernel, the GNA "EAR" audio sense. All closed; see
[PPT-LAT-KEYSTONE.md §4](PPT-LAT-KEYSTONE.md) and the archived roadmap for the full closure record.

**Boundary thesis (kept):** O_K wins on **exact arithmetic** (the container); every
structure-on-content compression lever is **measured-inert and kept as an honest negative** (Dirichlet
carriers, Möbius-on-M, entropy-on-codes, T2/T4-on-weights). The win is the container, not the content.

---

## 2. NEXT — the four open edges (from [PPT-LAT-KEYSTONE.md §12](PPT-LAT-KEYSTONE.md))

These are the honest open edges, in no forced order — pick by the day's leverage.

1. **Persistent O(1) conversation KV.** The daemon re-prefills the whole conversation each turn —
   correct, but **O(n)**. The L1 stateful `sp_session_register_kvdecode_backend` verb already exists;
   wiring "continue the cache" through it makes a follow-up turn true **O(1)** (append, don't re-prefill).
   This is the structural fix that also makes long sessions cheap. *Kill: the persisted KV diverges from
   a fresh re-prefill (must stay byte-identical).*

2. **The 2-physical-GPU byte-exact check.** The one remaining EXTERNAL item for byte-exact: a
   bit-identical logit check across **two physical GPUs** (needs a 2nd machine). On-machine we have
   run-to-run bit-identity + integer-reduction order-immunity as the proxy; the cross-card check closes it.

3. **Deeper faithfulness via reliable tiered recall.** The model still leans on parametric priors over
   in-context grounding; the system prompt is the patch, **reliable tiered recall is the structural
   answer** — pull conversation facts into MID/LONG so they survive window-scroll/restart, and make
   recall dependable enough that the model trusts stated facts over its priors. Includes a fuller
   MEM-OKF capabilities corpus. *Kill: extracted facts don't survive a restart, or recall stays unreliable.*

4. **Native-C XBAR port + T4 Frobenius of the model weights.** Port the host-Python XBAR/VSA tooling
   into the native `core/` tree (the resident loop no longer needs Python — partially done via
   `core/ring3/`), and execute **T4 Frobenius π^k of the 9.4 GB model weights** — the validated,
   untouched compression lever (distinct from the convicted structure-on-content levers). *Kill: the
   native port regresses bit-identity, or T4 fails to net-reduce at bit-exact.*

---

## 3. Standing disciplines (binding)

- **Receipts-first.** No number without a reproducing command + a [LEDGER.md](../../Position_Is_Arithmetic/LEDGER.md) row, with scope attached. Bit-exact-when-off. No silent gate revision — surface upstream. Honest negatives stay attached.
- **OKFS / SP-OKF + MEM-OKF anti-rebuild pre-flight.** Before building ANY subsystem: `python tools/okf_mem.py lookup --root memory-okf <kw>` + grep the tree. A new file for an existing capability is a *defect* (the 20×-repeated rebuild failure). All knowledge docs carry the SP-OKF frontmatter; run `python tools/okf_validate.py papers` on a touched bundle before commit. Specs: [SP-OKF-PROFILE.md](SP-OKF-PROFILE.md), [MEMORY-OKF-PROFILE.md](MEMORY-OKF-PROFILE.md).
- **Check the code + commits + `git fetch` before trusting memory.** STATE ([PPT-LAT-STATE.md](PPT-LAT-STATE.md)) is the proven record. Git ops on these repos via **native PowerShell, not the Linux mount** (the mount CRLF-churns + locks).
- **Recurring lesson, banked:** served-model misbehavior is almost always *ours* (template / decode / sampler / forward / prompt), not the weights — verify vs llama.cpp + our PPL first. For meta-cognitive model-calls: frame as **detection, not decision**, and force the answer prefix.

---

## 4. Where current truth lives — supersession order

**[PPT-LAT-KEYSTONE.md](PPT-LAT-KEYSTONE.md) (current-state map) > [PPT-LAT-STATE.md](PPT-LAT-STATE.md) (proven ledger) > active contract run records > this roadmap > [Archived/PPT-LAT-Roadmap-pre-keystone.md](Archived/PPT-LAT-Roadmap-pre-keystone.md) (historical).**

| Need | Go to |
|---|---|
| Current-state map / API | [PPT-LAT-KEYSTONE.md](PPT-LAT-KEYSTONE.md), [PPT-LAT-KEYSTONE-API.md](PPT-LAT-KEYSTONE-API.md) |
| Proven state record | [PPT-LAT-STATE.md](PPT-LAT-STATE.md) |
| Bootstrap / methodology / operator | `prompt.md`, `CLAUDE.md` |
| Architecture RFC | [PPT-LAT-RFC-001-Universal-Discrete-Architecture.md](PPT-LAT-RFC-001-Universal-Discrete-Architecture.md) (see the KEYSTONE addendum) |
| Public papers / claims ledger | Position_Is_Arithmetic `SERIES.md`, `papers/`, `LEDGER.md` |
| Historical roadmap (full phase history) | [Archived/PPT-LAT-Roadmap-pre-keystone.md](Archived/PPT-LAT-Roadmap-pre-keystone.md) |

---
*Post-KEYSTONE roadmap, 2026-06-25. KEYSTONE achieved (~90% of the organism); four open edges remain. Receipts-first; honest negatives attached; default-off is the null floor.*
