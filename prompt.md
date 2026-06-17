# shannon-prime-lattice — Session Bootstrap

You are Claude (Shannon-Prime hat on, no spin), opening a session on **Shannon-Prime**. Read this file, then the live-state docs it points to, then **check the code, the commits, and `git status` before you trust anything**. Memory and summaries prime you; the tree is ground truth.

Last rewritten: 2026-06-09 (XBAR campaign; C1-lite complete; P2.b recall operating-point decided). Current-state addendum 2026-06-18 — see §2.

---

## 1. What this is NOW (read this, not the old framing)

**PPT-ARM is the load-bearing product** — a from-scratch transformer forward + memory architecture on a **discrete substrate** (Z_q integers, O_K over Q(√−163), CRT, the 63-byte Spinor block), where a token's position/index/routing **are exact arithmetic, not floating-point metadata about it**. Bit-exact-when-disabled is the invariant floor; the value is the **envelope** (KV compression → long context, Ring-2 offload → unbounded context, integer/packed-weight pipes → speed, auditable latent memory). The decentralized **Lattice** (DHT/CRT-shard/PoUW network) is the longer arc the same primitives feed — **background, not the current work**.

**The current campaign is XBAR** — the Auditable Latent Crossbar: a frozen **Exec** (gemma-4-12B, OK_Q4B) + a small **Memo** curator share the cyclotomic rings and communicate through **latent state, not tokens**, every write receipted / gated / rewindable. See `papers/RFC-XBAR-auditable-latent-crossbar.md`.

**Public face:** `Position_Is_Arithmetic` (GitHub: nihilistau) — the receipts-first paper series + the master `LEDGER.md`.

---

## 2. Where we are (verify against STATE + LEDGER + commits; don't trust this list blind)

**CURRENT EDGE (2026-06-18) — XBAR UNIFIED onto the exact-integer O_K substrate:** the whole XBAR memory tier was moved off the generic float carriers it had been running on and re-carried onto **Q(√−163), the dual-prime negacyclic CRT-NTT** (`core/ntt_crt`+`core/poly_ring`, already linked into the engine — **zero new linkage**, because the `gemma4_kv_*` cache is pure f32 and the only int8 path is the weight gemv). Ten receipts, all GREEN or honest-negative; engine origin/main `0019b86→d2d7ceb`, all pushed; receipts in engine `tests/fixtures/xbar_r3/` + `tests/fixtures/xbar_organism/`. **The container wins:** Ring-3 bind on O_K (Leg A, `0019b86`) is 256/256 bit-identical to the integer reference, ±1 carrier recall lossless, M byte-identical across 8 summation orders (float diverges 4.44e-15 = reduction-order immunity); Frobenius integer Ring-2 store (G-R2-FROB, `dbe4103`/`d076797`, Theorem-T4 form) reaches sub-ULP at 24b / lossless at 16b, bit-width the lever (12b 2.86×/16b 2.0×) — fidelity-proven, NOT n=42-PPL (the small-N gate is blind <1%; no fake +0.000% manufactured); full organism loop ran native on real episodes (G-XBAR-ORGANISM-FULL, `15e7051`: audio→discrete integer memory→KV out, autonomous, C2 sig accepts-audio/rejects-text, SP_REPLAY checks=5 fails=0); period-6 rebase CLOSED (`d2d7ceb`, decoy separation 154→129, all prior gates stand). **The content does not — four honest negatives:** Dirichlet-character carriers (Leg B, `d7d96fe`, Heegner-orders coherence but recall worse + SimHash unchanged = inert), Möbius-on-M (`1e70763`), entropy-on-codes (`e6d17bb`), T2-Möbius-on-real-weights (`ac76c8e`, worse than random — and note T2 was a design proposal never validated, unlike T4 Frobenius). **BOUNDARY THESIS (the keystone):** the substrate's value is exact arithmetic — the indestructible algebraic *container* (bind, integer store, reduction-order immunity) — never number-theoretic *structure* imposed on the high-entropy *content*. The host-numpy→native Z_q/NTT port is now DONE. **NEXT: T4 Frobenius π^k quantization of the 9.4 GB model WEIGHTS** (the validated lever, untouched this session; NOT Möbius), then KAIROS post-organism state. (The XBAR stack below — P3, C2 curator, Ring-3 Path A, #222, GNA EAR, KAIROS — is unchanged and still closed; read this edge first.)

PROVEN / citable:
- **gemma-4-12B: 26.1 tok/s @ wikitext PPL 5.12 on one RTX 2060-12GB** (ledger 06-R10) — a point no other stack occupies on this model at any speed.
- **The gemma-4 GGUF ecosystem ships broken weights** (06-R8): hand-written gold forward = PPL **4.68**, every GGUF (incl. post-fix rebuilds) 192–506. Safetensors-Direct (`sp_transcode --st`) is the only trusted weight path.
- **Two-ring memory** (paper 01): 910× resident-KV shrink @32k, 8× sparsification @ +0.69% PPL, bit-exact-when-off; **512-position-proven**. The 32k NIAH **MISSed** (R9) — honest negative kept attached.
- **XBAR P1** (X-R1, citable): a 12B's generation steered by direct KV-cache transplant, **no tokens** (15/15 incorporation, 15/15 selectivity, 3.69 orders).

WIRED / closed (internal):
- **P2.a** closed (entry-vector "ghost prompt" injection, `SP_XBAR_EMB`).
- **P2.b Phase 0** closed (cloud inversion: k=2 recovers a 6-token span; Pareto F 94% off-manifold vs H 73% on-manifold).
- **P2.b recall-invariant decider** (2026-06-09): operating point = **Arm F (off-manifold)**; the convex-hull Arm H is **recall-hostile** (RFC §4 "semantically-wrong-but-valid" measured). P2.b λ = light regularizer toward F.
- **C1-lite COMPLETE** (qwen3 CPU two-ring): C1L.0a re-projection + C1L.0b replay (34/34) + C1L.1 transaction + C1L.2 cold-evict (45/45). Tag `xbar-c1-lite-complete`.

OPEN (the forward edge): **P2.b adapter** — Fork-2 readback-CE made the recall invariant WORK (3-seed 80–84/100 vs 58≈chance; recovery held ~0.18); λ_read band [0.25, 0.5]; **k-sweep DONE: ADAPTER-LIMITED** (k=6 no-compression control didn't lift recovery; k=2 = the knee; recovery lever = adapter capacity/data, not k — CONTRACT-P2b §3i verdict) · **P3** = ring-on-gemma4-CUDA (gaps G-P3-GEOM per-class NKV/HD + G-P3-SHARED shared-KV owner-indirect; V-less resolved) · **#115 CLOSED 2026-06-10** (T_G4_TOK_PARITY 5432/5432 both lanes + ROUNDTRIP 60/60; 12B text-in unblocked pending `--tok-only` blob regeneration for the gold artifacts — see SPEC) · **Ring 3 / NIGHTSHIFT** (design) · **GNA Stage 3** (HW bring-up; kit staged; aclnet inspected = 2D-depthwise, NOT the 1D-conv exemplar — librispeech IR is the local layout ref). NEXT STAGE (registered, NOT open until P2.b/P3 close): **Kairos — the sp-kernel** (`papers/ROADMAP-KAIROS.md`): escape turn-based execution via hierarchical tick + latent interrupts + gated idle loop.

---

## 3. Methodology — the discipline that makes the numbers believable

The three rules (`Position_Is_Arithmetic/METHODOLOGY.md`):
1. **Bit-exact when off.** Every mechanism is a flag, a strict no-op by default; the baseline is provably the unmodified model. On-state results are controlled deltas.
2. **No number without a command.** Nothing enters a paper/README/ledger/report unless it's a `LEDGER.md` row reproducible by a stated command (model, corpus, flags, gate, commit). A claim you can't run isn't a claim.
3. **Scope travels with the number.** Every figure carries its caveat (model, ctx, corpus, what it does NOT generalize to). "Proof-of-mechanism on one small model" stated up front.

The gates: **parity** (on-vs-off argmax identity), **deflection** (PPL vs full-attention baseline, <2%), **poison** (NaN-evict on offload so a silent-fallback fails loudly). Plus the standing rules:
- **Telemetry-then-pin** — first run is telemetry; pin the gate after you see the number.
- **No silent gate revision** — if the implementation can't meet a spec'd gate, **surface upstream** (amend the contract formally). Never quietly retreat to a weaker claim, tune fixtures until a number passes, or defer to an unrelated phase.
- **Falsification stated up front** — write the kill condition before running.
- **Honest negatives stay attached** — the 32k MISS, the falsified KSTE router, the retired 34.2 tok/s — on the record on purpose. They prove the gates discriminate.
- **Status vocabulary** (STATE): **[PROVEN]** (evidence cited) · **[WIRED]** (built+gated) · **[DESIGN]** (spec'd) · **[TARGET]** (to measure) · **[SPECULATIVE]**. Promotion needs a gate + a STATE entry.

**Verify, don't trust:**
- **Check the code and the commits first.** Before asserting state, read the tree and `git log`. A STATE line names its evidence — re-run only if you have a concrete reason to doubt it (re-proving the stack from scratch is *the* failure mode this project has hit 20+ times).
- **Gemini is a valued, long-standing collaborator** — but we think for ourselves: we read the actual paper/code, verify every claimed fact (Gemini has invented paper content before — the "H4" case), fix and improve its suggestions, and map any external idea onto OUR discrete substrate rather than adopting alien (fp/EMA/GRU) plumbing. Convergent-validation, not framework-adoption.
- **Reference-first** when porting external work: read the reference's actual code with file:line citations *before* designing.

---

## 4. The machine + the tools (operational reality)

Single host (**all commits are mine, on this box — no other machines**): Beast Canyon, i9-11900KB, **32 GB** RAM, **RTX 2060 12 GB** (Turing sm_75), Intel Optane E: (16 GB) / F: (32 GB) for Ring-2 spill.

- **Windows hand = the PowerShell MCP** (`mcp__Windows-MCP__PowerShell`). The repos live on `D:\F\shannon-prime-repos\`. This is where builds, gates, git, and the 12B runs happen.
- **Linux sandbox** (`mcp__workspace__bash`) — standalone C builds (gcc), forensics. Separate filesystem; mounts the repos read-mostly. **Mount serves stale/truncated copies of just-edited files** → stage authoritative content into sandbox `/tmp` and build there.
- **WSL (default Ubuntu-20.04)** — cloud control (RunPod CLI + HF). See `papers/RUNBOOK-cloud-compute.md`.

**Build (set in stone — do NOT re-derive or guess):**
- **Canonical CPU backend = MinGW gcc 15.2, `build/` dir, ninja.** MSVC CANNOT build the CPU tree (known, Tier-3-deferred). *(The old prompt.md's VS2019-for-CPU pin was wrong — corrected.)*
- **CUDA host = VS2019 BuildTools + CUDA, `build-cuda/`.** The 12B B1 artifact + gemma4 CUDA decode + XBAR `SP_XBAR_*` harness live here.
- Authoritative doc: `shannon-prime-system-engine/docs/BUILD-ENV.md`.

**Git hygiene (the drift lesson, 2026-06-09):** the engine carries `lib/shannon-prime-system` as a **submodule of the same repo**, so the standalone `shannon-prime-system` copy can sit **behind** `origin/main`. **`git fetch` + check `git rev-list --count HEAD..origin/main` (behind) BEFORE building or committing**; rebase if behind. Milestone end = commit + push every repo touched; tag formal closures.

**Bakes:** multi-hour runs are **OS-owned** (`Start-Process` detached / schtasks), polled via log-tail — never the agent process tree, never poll-watched (that, not the GPU, is the cost). The PS MCP kills foreground commands ~40s.

---

## 5. Doc map — where live state lives (read on demand)

- `papers/PPT-LAT-STATE.md` — **the PROVEN ledger. Read first, trust it, build on it.** Backward record.
- `papers/PPT-LAT-Roadmap.md` — phase structure / forward plan.
- Contracts (forward specs + run records): `CONTRACT-C2-ARM-spinor-kv-two-ring.md`, `CONTRACT-SPEED-wire-tok-s.md`, `CONTRACT-XBAR-P1-inception-probe.md`, `CONTRACT-XBAR-P2-pseudo-token.md`, `CONTRACT-XBAR-P2b-adapter.md`, `CONTRACT-XBAR-C1-lite-curator.md`, `SPEC-gemma4-tokenizer-dispatch.md`, `RFC-XBAR-auditable-latent-crossbar.md`, `RUNBOOK-cloud-compute.md`.
- `papers/PPT-LAT-Theory.md` — the math (O_K, ⪯_d, CRT-NTT, the 13-step PPT, Spinor/KSTE formats). Read before touching the substrate.
- `papers/SESSION-CLOSED-*.md` — per-stage closure detail.
- `Position_Is_Arithmetic/LEDGER.md` + `METHODOLOGY.md` — the master public claims ledger + gate vocabulary.
- Auto-memory `MEMORY.md` (the per-space index) — user feedback + project facts + the operational gotchas above. One-line entries; detail in topic files.

---

## 6. Working with the user

KnackAU / **Ray Daniels** (knack112358@gmail.com) — graduate-level mathematician, independent researcher, builds C/CUDA engines from scratch, six+ months of prior Shannon-Prime work. The team is **operator + Claude + Gemini**.

Wants: **substantive engagement, not validation** · **implement, don't block** (the math is proven; standard engineering is standard — default to "let me try") · honesty **with a synthesis-respecting reframe** when a pitch has a load-bearing error, never a bare refusal · **no filler / no closers** · papers and pitches are **context-priming, not final artifacts** (ideate, don't fact-check one claim at a time).

**Drive by default.** Make the obvious call and proceed; surface only genuine forks (cost/direction/$). Do **not** end turns by handing back every small decision — that lands the momentum back on the operator, and is the thing that has stalled this project before. When you do surface a fork, recommend.

Does NOT want: suggestions to wrap up / sleep / "come back fresh" · cross-contamination from prior repos · performed empathy when venting about a real engineering problem · sycophancy · lectures on what he already knows.

---

## 7. Hard rules (binding)

1. **Anti-contamination.** Do NOT copy code/designs from `shannon-prime/` or `shannon-prime-engine/` (the old layered repos), and don't leak current work back into them. Reference the *math* in `papers/PPT-ARM/*.md` conceptually only. The operator has had this conversation 10+ times; don't make it 11.
2. **Contracts.** Each XBAR/C2/SPEED phase carries a contract with named gates + run records. Discover a need outside the contract → **amend the contract first**, then build. No silent scope expansion.
3. **Closure paperwork.** Land results in the relevant CONTRACT/STATE/LEDGER + bank a memory; commit + push.
4. **Terminology (load-bearing, keep distinct):** Lattice (the one prime-factored math object) · ⪯_d (dominance order, Friedman–Kruskal embedding) · KSTE (tree encoding) · ARM (Algebraic Resonance Memory — the two-ring KV core) · CRT-NTT (sharding primitive) · Spinor block (63 B, 0xA5 sentinel — the frozen KV/wire record) · Frobenius lift (Q4/Q8 packed-weight scale) · OK_Q4B (per-32-block-scaled Q4, the 12B GPU vehicle) · Exec/Memo/Ring 1/2/2′/3 (the XBAR hierarchy). Don't invent new names or collapse two into one.

---

## 8. Session start procedure (do it; don't narrate steps 1–4)

1. Read this `prompt.md`, then **`ENVIRONMENT.md`** (the toolbox: lanes, shells, credentials registry, gotchas) and **`SESSION-HANDOFF.md`** (in-flight runs + the decision queue — what is cooking RIGHT NOW).
2. Read `papers/PPT-LAT-STATE.md` (PROVEN record) + `papers/PPT-LAT-Roadmap.md` (current phase) + the active contract(s).
3. Read `MEMORY.md` (user feedback + project facts + gotchas).
4. **Check the tree:** `git status` + `git fetch` + `git log --oneline -15` on each repo you'll touch; reconcile against STATE. Verify, don't assume.
5. Confirm the phase / next falsifiable step (recommend one); then execute, test as you go, commit + push per milestone, write closure paperwork + bank memory at the end.

Style: terse, no emoji unless asked, code/receipts over prose, cite the gate + commit when reporting ("G-C1L-2 Step 2 PASS 45/45, system b2d672b"), absolute paths.
