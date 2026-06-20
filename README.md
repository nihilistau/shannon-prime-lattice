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

**Latest (2026-06-20) — the AUTONOMOUS LIBRARIAN is LIVE on the served Gemma-4-12B chat.** The byte-exact, O(1)-context, single-entry 12B chat (`CONTRACT-CHAT-FULLSTACK`) now has an autonomous, instance-level episodic memory. A learned **W_c head** (`HD=512 → r=32`; relevance = logsumexp-over-positions then mean-over-heads) scores every stored episode against the live query, takes an **(E+1)-way argmax over [episodes, NULL=s0]**, and either **replays the winning episode at a bounded mass budget (`M=42`)** or **rejects to a clean prompt** — default-off (env unset) is byte-identical to the null floor. The relevance foundation is a **teacher-forced ablation knockout** (cudaMemset-ablate a needle's source KV rows and re-score: a genuinely-novel needle collapses −**33.56** nats, a parametric fact only −**0.15** — `TAU=−8.0`), which is both the admission oracle and the head's labeler; a curator mints the diverse corpus the head trains on. **Gates:** G-CHAT-B3-WC-DIV2 = **360/361 instance recall + 50/50 foreign-reject, int16==f32 lossless, s0=+0.102**; **G-CHAT-B3-WC-DEPLOY = LIVE on the metal** (matched query → RECALL `ep_n_div_000`; foreign "capital of France" → whole population negative → NULL → clean "Paris"). It is **host-side in the engine daemon (`recall.rs`/`routes.rs`); NO frozen-ABI change and NO `.sp-model` format change.** Boundary thesis: autonomous recall is won by a **learned head on a diverse corpus, not hand-designed number-theoretic signals** (all ~10 hand-designed signals are measured negatives; corpus DIVERSITY — instance top-1 **34% → 100%** — was the binding constraint). Launch `run_console_recall.bat`; the console Send button toggles to an interrupt (`/v1/abort/:id`). Engine `edc8079`; record `papers/CONTRACT-CHAT-FULLSTACK.md` + public Paper **24** ("the learned librarian").

**Prior (2026-06-18) — the BYTE-EXACT FORWARD is CLOSED GREEN on the real gemma-4-12B.** The gemma-4-12B *forward pass itself* now runs **exact-integer end-to-end**: the four nonlinear fp32 islands (RMSNorm / softmax / GELU-tanh / RoPE) and the attention (Q·K / p·V) convert to exact-integer on the **same dual-prime CRT-NTT the XBAR memory ring uses** (q1=1073738753, q2=1073732609, Garner inv 894602413, M=q1·q2≈2⁶⁰ fits u64 ⇒ no `__int128`), behind a default-off `SP_BYTEEXACT` flag (the one-shot production decode stays byte-untouched = null floor). **Byte-exact here means EXACT ARITHMETIC → logits bit-identical across reduction-order and machine — an auditability / cross-machine-determinism property, explicitly NOT a compression result.** Gates on the real 12B (`gemma4-12b-b1.sp-model`, RTX 2060): **G-BYTEEXACT-FORWARD-12B GREEN** — OFF = PPL 4.6665 byte-identical to baseline / ON = 4.6569 parity (−0.21% n=42) / run-to-run **bit-identical**; the universal daemon drives the 12B prefill + token-by-token decode through a new L1 verb `sp_session_register_kvdecode_backend` (**G-WIRE-CUDA-DECODE-GEMMA4: 32/32 bit-identical to the `gemma4_kv_decode` oracle, VRAM flat / O(1)**). The byte-exact *linear* algebra was already built + gated in the universal crate `tools/sp_dsp_smoke`; the new piece was the four nonlinear islands (`sp_islands_q_ref.rs` + math-core `core/exact_islands/`). Only the external 2-physical-GPU bit-identical check remains. Engine `69c0588`, math-core submodule `d9d96f3`; record `papers/CONTRACT-BYTEEXACT-forward.md`.

**Prior (2026-06-18):** **The XBAR memory architecture is UNIFIED onto the exact-integer O_K substrate** (`Q(√-163)` / the dual-prime negacyclic CRT-NTT, frozen primes q1=1073738753 q2=1073732609 M=1152908312643096577) — the organism breathes end-to-end on the discrete container, no generic float carriers. **G-R3-BIND-on-O_K** (engine `0019b86`): the Ring-3 VSA bind re-carried onto native `sp_pr_mul`/`ntt`/`sp_pr_score_kstore` is **256/256 bit-identical** to the native path, ±1 carrier int==float, and **reduction-order-immune** (M byte-identical across permutations vs float 4.44e-15 drift). **G-R3-ORGANISM-NATIVE** (`1f0f6be`): the live dualroute+nightshift loop runs on native `sp_pr_mul` (D=1024 = two 512-blocks; CAP=32). **G-R2-FROB** (`dbe4103`/`d076797`): a Frobenius π^k INTEGER Ring-2 episode store (rank-2 O_K lattice; a16 ~lossless / a16b8 sub-ULP relL2 1.2e-7 at 0.76× store) — honest: "lossless" is by reconstruction fidelity (the n=42 PPL gate is blind below ~1%; no fake +0.000%). **G-XBAR-ORGANISM-FULL** (`15e7051`): the full loop on **real episodes** — continuous audio (EAR) → C2 256-bit sig → native integer Ring-3 superposition (with text decoys) → audio-cue top-1 retrieve → C2 Hamming verify (accept audio / reject text) → Frobenius integer store → continuous float lands clean into the 12B resident cache (checks=5 fails=0). **G-PERIOD6-REBASE** (`d2d7ceb`): the C2/Ring-3 content-hash period 8→6 to the true gemma4 global layers {5,11,…,47}, re-gated GREEN. **The boundary thesis** the receipts bore out: O_K wins on **exact arithmetic** (the container); every structure-on-*content* lever is measured-inert and kept as an honest negative — split-prime O_K Dirichlet carriers (`d7d96fe`, operationally inert), Möbius-on-M (`1e70763`, 1.000→0.969@N=32), entropy-coding the Frob codes (`e6d17bb`, 1.02× dead weight), T2-Möbius on the real 12B embedding (`ac76c8e`, recon cos 0.032 == random). **NEXT: B4 NIGHTSHIFT** (between-turn memory consolidation, pre-scoped), then **T4 Frobenius π^k of the 9.4GB model WEIGHTS** (the validated, untouched lever) and KAIROS post-organism.

*(Prior: full XBAR memory stack CLOSED — P3 (P3.0→P3.4), C2 Memo curator, #222 O(1) rewind, Ring-3 Path A, G-XBAR-ORGANISM step 1; KAIROS KAI-1/1b/1c + 6h soak GREEN; KAI-2 CLOSED-BOUNDED; KAI-3 CLOSED GREEN; GNA EAR CLOSED on silicon.)*

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
   **The autonomous librarian (B3-WC) is LIVE** — a learned `W_c` head
   selects or rejects episodes on the served 12B chat (see §0/§3).
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
   user query ──► served Gemma-4-12B chat  (run_console_recall.bat → :3000)
                  coherent · byte-exact · O(1)-context (SWA ring) · ONE inject seam
                            │                                       [PROVEN — CHAT-FULLSTACK]
                            ▼
   ┌──────────────── AUTONOMOUS LIBRARIAN  (W_c head, host-side) ───────────────┐
   │  score every stored episode  e1…eE   (relevance = logsumexp-over-pos,      │
   │                                        mean-over-heads; HD=512 → r=32)      │
   │                       │                                                     │
   │                       ▼   (E+1)-way argmax over [ e1 … eE , NULL=s0 ]       │
   │            ┌──────────┴───────────┐                                         │
   │       winner ≠ NULL          argmax = NULL                                  │
   │            │                       │                                        │
   │   replay episode @ M=42      reject → clean prompt   [PROVEN — G-B3-WC      │
   │   (bounded mass budget)      (no false fire)          DIV2 360/361+50/50,   │
   │            │                       │                  LIVE G-B3-WC-DEPLOY]  │
   └────────────┼───────────────────────┼───────────────────────────────────────┘
                │ inject KV (gated)      │ foreign → "Paris."
                ▼                        ▼
   ┌──────────────────── TWO-RING EPISODIC MEMORY ───────────────────────────────┐
   │  Ring 1  working KV window+sinks  [PROVEN]   Memo curator: mint → admit      │
   │  Ring 2  verbatim Spinor KV, Optane store     (ablation oracle TAU=−8.0) →   │
   │          (hippocampus)  [PROVEN]              label → train W_c  [PROVEN]     │
   │  Ring 2′ shadow: propose → gate → promote/REWIND  [PROVEN — C1-lite]         │
   │  Ring 3  consolidated (neocortex); G-R3-LOSS bounded  [PROVEN — native core] │
   │          B4 NIGHTSHIFT idle-time consolidation  [DESIGN, pre-scoped, next]   │
   └─────────────────────────────────────────────────────────────────────────────┘
                ▼  every bind / store / replay rides the discrete container
   ┌──────────── O_K EXACT-INTEGER SUBSTRATE  (Q(√−163), dual-prime CRT-NTT) ─────┐
   │  q1=1073738753  q2=1073732609  M≈2^60  ·  Frobenius lift / OK_Q4B packed     │
   │  byte-exact forward (4 islands + attention, SP_BYTEEXACT) = auditability     │
   │  reduction-order-immune · run-to-run bit-identical  [PROVEN — BYTEEXACT-12B] │
   └─────────────────────────────────────────────────────────────────────────────┘
                ▲
   KAIROS — the time/agency axis: resident daemon, idle-tick NO_OP/ACTION, EAR
   audio → KV pivot, the consolidation clock that drives NIGHTSHIFT.  [PROVEN]
```

| Tier | Substrate | Representation | Biological analogue | Status |
|---|---|---|---|---|
| **Ring 1** | RAM working window | verbatim KV, full attention | working memory | [PROVEN] — sink+W ring buffer, 910× resident shrink @32k (CONTRACT-C2 §C2.1) |
| **Ring 2** | Optane raw episodic store | verbatim Spinor KV blocks (+ Frobenius integer store) | **hippocampus** | [PROVEN] qwen3 CPU ring (7.57 µs/read, byte-identical) **+ on the 12B Exec via P3 + the native O_K organism** (G-XBAR-ORGANISM-FULL) |
| **Ring 2′** | transient staging shadow | proposals awaiting the gate | (the audit mechanism) | [PROVEN] — C1-lite clone/gate/atomic-promote/rewind, tag `xbar-c1-lite-complete` |
| **Ring 3** | Optane consolidated store | VSA-bound consolidated long-term | **neocortex** | [PROVEN] — native-C core (`core/ring3/`, T_RING3_NATIVE 42/42) under the irreversible-aware G-R3-LOSS step-gate |
| **Recall** | learned W_c head (host-side) | logsumexp-mean relevance → (E+1)-NULL argmax | **the librarian** | [PROVEN] — G-CHAT-B3-WC-DIV2 360/361 recall + 50/50 reject (int16==f32), LIVE G-CHAT-B3-WC-DEPLOY; replay@M=42 / NULL-reject; engine `edc8079` |

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
| **Autonomous recall on the 12B chat (B3-WC)** | a learned **W_c** head (HD=512→r=32, logsumexp-mean) does LIVE instance-level episodic recall on the served chat: (E+1)-argmax over [episodes, NULL=s0] = **360/361 recall + 50/50 foreign reject, int16-exact** offline; live matched→RECALL, foreign→NULL reject (clean "Paris"). Corpus DIVERSITY (not machinery) was the binding constraint: instance top-1 **34%→100%**. Hand-designed signals all failed open-world (honest negatives). | `CONTRACT-CHAT-FULLSTACK.md` · receipts `tests/fixtures/chat_fullstack/G-CHAT-B3-WC-{DEPLOY,DIV2}.log` · engine `edc8079` |
| **Gemma-4-12B on one RTX 2060 12GB** | **26.1 tok/s @ wikitext PPL 5.12** (24/24 gates, CUDA-graph path EXACT 256/256, dp4a top-1 256/256); llama.cpp on the same card: 31.29 tok/s @ PPL **192–506** (broken artifacts); SP engine bandwidth 245 vs 207 GB/s (+18%) | public LEDGER **06-R10** · `CONTRACT-SPEED` · receipts `tests/gemma4_gold/` |
| **Byte-exact forward (Gemma-4-12B)** | the whole forward (4 nonlinear islands + attention) runs **exact-integer** on the dual-prime CRT-NTT: OFF = PPL **4.6665 byte-identical** null floor / ON = **4.6569** parity / **run-to-run bit-identical** (cross-machine determinism proxy). Auditability, NOT compression. Daemon-driven prefill + decode (new L1 kvdecode verb, 32/32 == oracle, VRAM O(1)) | `CONTRACT-BYTEEXACT-forward.md` §5.2/§7/§8 · receipts `tests/fixtures/xbar_r3/G-BYTEEXACT-FORWARD-12B.log` · engine `69c0588` |
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
| Where does the project stand right now (human-readable synthesis)? | `CURRENT-STATE-OF-PROJECT.md` (repo root) |
| How do I chat the real 12B / use autonomous recall? | `run_console.bat` (plain) / `run_console_recall.bat` (B3-WC librarian armed) in the engine repo; record `papers/CONTRACT-CHAT-FULLSTACK.md` |
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
locality telemetry. **Status: the R3.4 idle-loop mechanism is GREEN** (G-R3-NIGHTSHIFT: SELECT→BIND→SHADOW-GATE→PROMOTE+EVICT→SEAL, native-C `core/ring3/`); **B4 — between-turn consolidation on the live chat — is the named next piece (pre-scoped, [DESIGN]).** Episode bound ≤8k tokens until the B∝N recall-budget question is answered (the C2.4 lesson).

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
