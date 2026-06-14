# shannon-prime-lattice

**Shannon-Prime PPT ARM Lattice** — a byte-exact inference and memory
architecture for large transformer models built on a single discrete math
object: the prime-factored coordinate lattice over `Z_q` with dual-prime
Chinese-Remainder-Theorem (CRT) decomposition, the Friedman–Kruskal dominance
order `⪯_d`, and the CRT cyclotomic ring `R_q = Z_q[x]/(x^N + 1)`.

This repository is the **developer umbrella** and the project's working /
research repo: papers, roadmap, contracts, integration receipts, and the
bootstrap prompt for new working sessions. Code lives in the companion
repositories. Here for the results, not the source? Start at the public,
receipts-first front door: **[Position Is Arithmetic](https://github.com/nihilistau/Position_Is_Arithmetic)**
(live site: https://nihilistau.github.io/Position_Is_Arithmetic/).

| Repo | Role | URL |
|------|------|-----|
| `Position_Is_Arithmetic` | **Public front door** — receipts-first paper series + master `LEDGER.md` (every claim reproduces from a command) | https://github.com/nihilistau/Position_Is_Arithmetic |
| `shannon-prime-lattice` (this) | Developer umbrella: papers, roadmap, contracts, integration tests | https://github.com/nihilistau/shannon-prime-lattice |
| `shannon-prime-system` | Math-core: L1 C ABI, NTT, poly-ring, ARM two-ring, KSTE, Frobenius, sessions | https://github.com/nihilistau/shannon-prime-system |
| `shannon-prime-system-engine` | Engine backends (CPU/CUDA/Vulkan/Hexagon), `sp_daemon` HTTP/SSE, tools | https://github.com/nihilistau/shannon-prime-system-engine |

Discord: [Shannon-Prime-Lattice](https://discord.gg/rre9XZmvV)
License: MIT. See `LICENSE`.

**New here (human or agent)? Read [`CURRENT-STATE-OF-PROJECT.md`](CURRENT-STATE-OF-PROJECT.md)** —
a single human-readable synthesis of where the project stands: the XBAR latent crossbar, the
O(1) rewind, the KAIROS resident loop, the headline numbers, and the tests that prove each
(and why they can be trusted). It is the fastest way to get oriented.

**If you are a coding agent opening a session: read `prompt.md` first, then
`CURRENT-STATE-OF-PROJECT.md` (the synthesis) and `papers/PPT-LAT-STATE.md` (the proven
record). This README is the 2-minute orientation; those are the operating documents.**

---

## 1. What this is NOW

Three things, in order:

1. **PPT-ARM is the load-bearing product.** A from-scratch transformer
   forward (the 13-step PPT substitution) plus the ARM memory architecture
   (Spinor-KV two-ring recall + offload), on a **discrete substrate** —
   integers in `Z_q` (two frozen 30-bit Proth primes via CRT), where a
   token's position/index/routing are exact arithmetic, not floating-point
   metadata. **Bit-exact-when-disabled is the invariant floor; the value is
   the envelope**: KV compression → long context, Ring-2 offload → context
   beyond RAM, packed-integer pipes → speed, auditable latent memory.

2. **XBAR is the current campaign** — the Auditable Latent Crossbar: a
   frozen **Exec** (gemma-4-12B, OK_Q4B) plus a small **Memo** curator share
   the cyclotomic rings and communicate through **latent state, not tokens**,
   every write receipted, gated, and rewindable. Lanes: XBAR-P (probe /
   physics), XBAR-C (curator), XBAR-M (modality), XBAR-N (NIGHTSHIFT).
   Spec: `papers/RFC-XBAR-auditable-latent-crossbar.md` (v1.1).

3. **Position Is Arithmetic is the public face** — the receipts-first paper
   series and the master claims ledger. Nothing is public without a
   `LEDGER.md` row reproducible from a stated command.

The decentralized **Lattice** (Fibonacci-Prime DHT, CRT-shard mesh, PoUW
receipts network) is the longer arc the same primitives feed — background,
not the current work. The deployment ladder for all of it is the **stage
taxonomy** (Alpha … Eta, Omicron ο, Holon ⬢⃝) in `papers/PPT-LAT-STATE.md`
§5.07.

---

## 2. The system — four-tier memory hierarchy + XBAR

The architecture grew from the proven two-ring core (CONTRACT-C2) into a
four-tier hierarchy (RFC-XBAR §3/§3.1). Status tags follow the project
vocabulary: **[PROVEN]** evidence cited · **[WIRED]** built + gated ·
**[DESIGN]** spec'd, unbuilt · **[TARGET]** a number to measure.

```
      ┌────────────────────────── VRAM / RAM (owned arena) ───────────────────────────┐
      │                                                                               │
      │  Exec (gemma-4-12B, OK_Q4B) [PROVEN]      Memo (small curator)                │
      │  causal forward, generates                heuristic loop [PROVEN, C1-lite];   │
      │       │            ▲                      trained compaction organ [TARGET]   │
      │       ▼ write      │ attend                     │ propose        ▲ read       │
      │  ┌─ Ring 1 ─────┐  ┌─ Ring 2 (hippocampus) ─┐   ▼                │            │
      │  │ working KV   │  │ verbatim Spinor KV,    │  ┌─ Ring 2′ (shadow) ────────┐  │
      │  │ window+sinks │  │ Optane episodic store  │◄─│ proposals, promote-on-    │  │
      │  │ [PROVEN]     │  │ [PROVEN, qwen3 CPU     │  │ accept or REWIND [PROVEN, │  │
      │  └──────────────┘  │  ring; Exec path = P3] │  │ C1-lite]                  │  │
      │       ▲            └────────────────────────┘  └──────────┬────────────────┘  │
      │       │ recall from BOTH                                  │ promote (gated)   │
      │       │            ┌─ Ring 3 (neocortex) ─────────┐◄──────┘                   │
      │       └────────────│ adapter pseudo-tokens,       │  G-R3-LOSS bounded        │
      │                    │ consolidated long-term       │  (irreversible) [DESIGN]  │
      │                    └──────────────────────────────┘                           │
      │                                                                               │
      │       modality lanes — one CRT prime per modality [DESIGN; audio first,       │
      │       GNA 2.0 envelope pinned in SW-emu, HW bring-up kit staged]              │
      └───────────────────────────────────────────────────────────────────────────────┘
        NIGHTSHIFT [DESIGN, v0 next]: idle-time consolidation — read aging Ring 2
        episodes → adapter compress n→k → propose to Ring 2′ → gate → promote to
        Ring 3. schtasks-owned, banner echoes getenv, every promotion receipted.
```

| Tier | Substrate | Representation | Biological analogue | Status |
|---|---|---|---|---|
| **Ring 1** | RAM working window | verbatim KV, full attention | working memory | [PROVEN] — sink+W ring buffer, 910× resident shrink @32k (CONTRACT-C2 §C2.1) |
| **Ring 2** | Optane raw episodic store | verbatim Spinor KV blocks | **hippocampus** | [PROVEN] on the qwen3 CPU ring (7.57 µs/read, byte-identical spill/recall); Exec (gemma4-CUDA) wiring = P3, pending |
| **Ring 2′** | transient staging shadow | proposals awaiting the gate | (the audit mechanism) | [PROVEN] — C1-lite clone/gate/atomic-promote/rewind, tag `xbar-c1-lite-complete` |
| **Ring 3** | Optane consolidated store | P2.b-adapter pseudo-tokens (n→k gist) | **neocortex** | [DESIGN] — under the irreversible-aware G-R3-LOSS gate |

Beneath the rings, the substrate everything rides on (all [PROVEN], see
STATE §1–§2): the 13-step PPT discrete forward (argmax bit-exact on Qwen3,
Qwen2.5, Gemma3, Gemma4-E2B, Qwen3.6-35B-A3B GDN+MoE) · NTT-CRT dual-prime
poly-ring attention · Frobenius-lift Q4/Q8 packed arena + the **OK_Q4B**
per-32-block-scaled format (the 12B GPU vehicle) · Spinor 63-byte KV block
(0xA5 sentinel, one cache line) · KSTE encoder + `⪯_d` dominance · ±1
Rademacher recall router · PoUW receipt ledger · QUIC dual-prime residue
mesh (loopback-proven).

---

## 3. Measured highlights (each number carries its receipt)

| Result | Number | Receipt |
|---|---|---|
| **Gemma-4-12B on one RTX 2060 12GB** | **26.1 tok/s @ wikitext PPL 5.12** (24/24 gates, CUDA-graph path EXACT 256/256, dp4a top-1 256/256); llama.cpp on the same card: 31.29 tok/s @ PPL **192–506** (broken artifacts); SP engine bandwidth 245 vs 207 GB/s (+18%) | public LEDGER **06-R10** · `CONTRACT-SPEED` · receipts `tests/gemma4_gold/` |
| **The gemma-4 GGUF ecosystem ships broken weights** | hand-written gold reference forward = TRUE PPL **4.6776**; every GGUF (incl. post-fix rebuilds) 192–506; llama.cpp's *forward* exonerated, the *artifacts* convicted | LEDGER 06-R8 · `CONTRACT-SPEED` gold-instrument addendum · community fix `GEMMA4-QUANT-FIX.md` (public repo) |
| **X-R1 — latent crossbar physics** | a 12B's generation steered by **direct KV-cache transplant, no tokens**: 15/15 lexical incorporation (5×3 matrix), 15/15 selectivity (double dissociation), max 3.69-orders rank pull, measured dose-response, G0 null bit-identical | public LEDGER **X-R1** · `CONTRACT-XBAR-P1` |
| **KV sparsification** | **8× at +0.69% PPL** (2×/4× go negative), NIAH 6/6 at ≤8× @N=2k, Möbius-pinned sinks | `CONTRACT-C2` §C2.1 G2 · paper 01 |
| **Resident KV shrink** | **910× @32k** (7.5 GB → 8.3 MB Ring-1), needle served off physical Optane at **7.57 µs/read**, bit-exact when off | `CONTRACT-C2` §C2.1 · paper 01 |
| **Reducing loader** | GGUF → `.sp-model` **~50% smaller**, zero-copy, bit-faithful forward, 6/6 E_FMT | paper 02 (`EXPECTED.md`) |
| **C1-lite curator** | full propose→gate→promote/rewind loop on real recall: replay null 34/34, cold-evict 45/45 (lossless promotes, lossy rewinds) | `CONTRACT-XBAR-C1-lite` · tag `xbar-c1-lite-complete` |
| **The honest 32k MISS** | the composed 32k Optane finale **completed and MISSed the needle** at the 64× selection budget (config regression + budget regime; infrastructure proven at 16.3 h / 16.6 TB scale) — kept on the record; Ring 3 is the architectural answer | STATE §5.11 · `CONTRACT-C2` §C2.4-CLOSURE |

Honest negatives stay attached on purpose (the 32k MISS, the falsified KSTE
recall router, the retired 34.2 tok/s headline whose artifact failed the PPL
gate): they prove the gates discriminate. In-flight work (the P2.b capacity
arm) is **not** claimed here — no number lands before its run record.

---

## 4. Doc map — which file answers which question

| Question | Read |
|---|---|
| I'm an agent starting a session — how do I bootstrap? | `prompt.md` (then follow its procedure) |
| What is PROVEN, with what evidence? | `papers/PPT-LAT-STATE.md` — **the proven ledger; trust it, build on it** |
| What's the current architecture (rings, XBAR, NIGHTSHIFT)? | `papers/RFC-XBAR-auditable-latent-crossbar.md` |
| What's the phase structure / forward plan? | `papers/PPT-LAT-Roadmap.md` — read its **AGENT NAVIGATION box** first; the 8,500-line body is largely historical |
| What are the forward specs + run records per lane? | `papers/CONTRACT-*.md` (C1/C2/SPEED/XBAR-P1/P2/P2b/C1-lite) — contracts carry the gates and the run records |
| What's the math? | `papers/PPT-LAT-Theory.md` (13-step PPT, O_K, `⪯_d`, CRT-NTT, frozen Spinor/KSTE formats) — read before touching the substrate |
| The systems narrative / six-layer architecture? | `papers/PPT-LAT-Systems-v1.md` (supersedes v0 + the two standalone specs, now its Appendices A/B) |
| The frozen ABI / on-disk format? | `papers/PPT-LAT-L1-ABI-v0.md` + `papers/PPT-LAT-SP-MODEL-v0.md` (frozen), live header `shannon-prime-system/include/sp/sp_l1.h` |
| What did a given sprint ship? | `papers/SESSION-CLOSED-*.md` (audit trail) |
| How does the cloud training loop work? | `papers/RUNBOOK-cloud-compute.md` |
| The public claims + reproduce commands? | `Position_Is_Arithmetic/LEDGER.md` + `METHODOLOGY.md` |

Supersession order when documents disagree: **STATE > contract run records >
Roadmap amendments > Roadmap body**. The papers are scaffolding, not
artifacts — amendable when reality contradicts them — except the L1 ABI and
`.sp-model` specs, which are frozen.

---

## 5. Methodology (why the numbers are believable)

1. **Bit-exact when off.** Every mechanism is a flag, a strict no-op by
   default; the baseline is provably the unmodified model. On-state results
   are controlled deltas.
2. **No number without a command.** Nothing enters a paper, README, or
   ledger unless it reproduces from a stated command (model, corpus, flags,
   gate, commit).
3. **Scope travels with the number.** Every figure carries its model, ctx,
   corpus, and what it does NOT generalize to.
4. **No silent gate revisions.** If the implementation can't meet a spec'd
   gate, surface upstream and amend the contract formally — never retune
   fixtures, retreat to a weaker claim, or footnote a PASS.
5. **Falsification pre-stated.** The kill condition is written before the
   run; first run is telemetry, the gate is pinned after.
6. **Honest negatives stay.** Misses, falsified designs, and retired
   headlines remain on the record with their receipts.

Standing gates: **parity** (on-vs-off argmax identity), **deflection** (PPL
vs full-attention baseline, <2%), **poison** (NaN-evict on offload so silent
fallback fails loudly).

---

## 6. NIGHTSHIFT and the latent-space direction

**NIGHTSHIFT** (RFC-XBAR §7) is the idle-time consolidation loop — the
Optane subconscious. The substrate is already proven (byte-exact Ring-2
spill/recall, 16.3 h unattended saturation, receipts end to end); NIGHTSHIFT
adds episode persistence (a named `{K store, V store, manifest}` file set
that survives sessions), the offline consolidation pass (Memo walks an
episode non-causally: heuristic select/merge/evict in v0, P2.b-adapter n→k
span compression into Ring 3 in v1, always promote-on-accept), and the
operational discipline (OS-owned runs, getenv-echo banners). The
association-strength signal already exists — the measured LRU temporal-
locality telemetry. Status: [DESIGN], v0 next; episode bound ≤8k tokens
until the B∝N recall-budget question is answered (the C2.4 lesson).

**The latent-space direction.** XBAR's premise is that inter-model memory
should be a thing with receipts: a block of internal state provably
well-formed (Spinor 0xA5 sentinel + Frobenius-lift bit-identity), every
write gated through a shadow ring, promoted or rewound, auditable end to
end. The discrete substrate detects *invalid* blocks; it cannot detect
*semantically-wrong-but-valid* ones — which is why the coherence gate is
load-bearing on every promotion, forever (RFC §4). The same structure is,
incidentally, a defensive research direction the field lacks: deployed AI
safety scans text while cognition happens in latent space, and a substrate
that makes latent state verifiable and gated is a small proof that the
latent layer doesn't have to be an unmonitored canvas (RFC §6.2). Recorded
as motivation, not a project pivot.

---

## 7. Getting started

```bash
git clone https://github.com/nihilistau/shannon-prime-lattice.git
git clone https://github.com/nihilistau/shannon-prime-system.git
git clone --recurse-submodules https://github.com/nihilistau/shannon-prime-system-engine.git
```

The engine bundles `shannon-prime-system` as a submodule under
`lib/shannon-prime-system/` — that pin is what every engine build uses (and
the standalone math-core clone can sit behind it: `git fetch` + behind-check
before building or committing).

- **Run a model locally:** `shannon-prime-system-engine/README.md` — build,
  transcode (`sp_transcode`; use `--st` Safetensors-Direct for gemma-4),
  `curl` the daemon.
- **Understand the math:** `papers/PPT-LAT-Theory.md` →
  `papers/PPT-LAT-Systems-v1.md` → `papers/PPT-LAT-Roadmap.md`.
- **Write a kernel against the frozen ABI:** `papers/PPT-LAT-L1-ABI-v0.md`
  then `shannon-prime-system/include/sp/sp_l1.h`.
- **Add a model family:** `papers/PPT-LAT-SP-MODEL-v0.md` +
  `shannon-prime-system-engine/tools/sp_transcode/`.

---

## 8. Repository layout

```
shannon-prime-lattice/
├── papers/                       # the project's papers — the source of truth
│   ├── PPT-LAT-STATE.md          # THE PROVEN LEDGER (read first)
│   ├── PPT-LAT-Theory.md         # math foundations + 13-step PPT substitution
│   ├── PPT-LAT-Systems-v1.md     # canonical systems narrative
│   ├── PPT-LAT-Roadmap.md        # phases (living; nav box at top, body historical)
│   ├── RFC-XBAR-*.md             # the current campaign's architecture
│   ├── RFC-001 / CONTRACT-*.md   # north-star + forward specs with run records
│   ├── RUNBOOK-cloud-compute.md  # cloud training mechanism
│   ├── PPT-LAT-L1-ABI-v0 / -SP-MODEL-v0.md   # frozen specs
│   └── SESSION-CLOSED-*.md       # per-sprint closure notes (audit trail)
├── tests/                        # integration receipts (e.g. gemma4_gold/)
├── tools/                        # lattice-scope tools (curator, xbar_p2b)
├── scripts/                      # cross-repo helpers (m0_real SFT, render)
├── docs/superpowers/             # historical per-phase plan documents
├── frontends/                    # HTML mock-ups (daemon UI concepts)
├── demos/                        # phase demos
└── prompt.md                     # session bootstrap (agents start here)
```

---

## 9. Hard rules

Binding for any session that picks up the project:

- **Anti-contamination.** Do NOT read, copy, or vendor code from the
  archived `shannon-prime/` or `shannon-prime-engine/` repos. The math
  papers under `papers/PPT-ARM/` are conceptual reference — theory only,
  never code. The lattice is a clean rebuild.
- **No silent gate revisions.** Surface upstream; amendments land formally
  with rationale, never as footnotes on a PASS.
- **Honest closure notes.** Every closure enumerates gates, actual results,
  what was bundled vs isolated, and deltas vs spec.
- **One math object.** Features must touch a distinguishing primitive
  (§2's substrate list / the ten heterogeneous-SoC CRT tricks); otherwise
  they are drift.
- **Terminology is load-bearing.** Lattice · `⪯_d` · KSTE · ARM · CRT-NTT ·
  Spinor block · Frobenius lift · OK_Q4B · Exec / Memo / Ring 1/2/2′/3 ·
  XBAR lanes P/C/M/N · NIGHTSHIFT · stage taxonomy (Alpha…Eta, Omicron ο,
  Holon ⬢⃝). Don't invent new names or collapse two into one.
- **Worktrees per concurrent agent.** 2+ agents on one repo → each in its
  own `git worktree add`.

---

## 10. Contact

- GitHub Issues: project tracking lives in each repo.
- Discord: [Shannon-Prime-Lattice](https://discord.gg/rre9XZmvV).
- License: MIT (see `LICENSE`).
