# shannon-prime-lattice — Session Bootstrap

You are Claude, opening a new session on **shannon-prime-lattice**. Read this file first. It is the canonical context primer. Everything else (theory, systems, roadmap, prior session state) is referenced from here and read on demand.

---

## What this project is

**shannon-prime-lattice** is a clean from-scratch rebuild and synthesis of the mathematical primitives from six months of prior Shannon-Prime work, aimed at a unified architecture for **decentralized cooperative AI training and inference**.

It uses **one math object** across the entire stack: the prime-factored coordinate lattice with the dominance order `⪯_d` (Friedman–Kruskal homeomorphic embedding) and the CRT cyclotomic ring for compact representation, anchored to the ring of integers `O_K` over `Q(√-163)` (a UFD by the Heegner discriminant). The Prime Power Transformer (PPT) is the substrate: 13 transformer steps each replaced by an exact algebraic operation in this framework (see PPT-LAT-Theory.md §7).

**Engine scope:** four backends sharing the math core — CPU (AVX2 + AVX512), CUDA (sm_86/sm_89), Vulkan (SDK 1.3.x), Hexagon (V69 HTP on S22U-class phones). Foundational features (inline Q8/Q4 weight compression with Frobenius scale, inline KV cache compression via VHT2 + Spinor block) must work on all four before Lattice features layer on. Target model families: Llama 3.x, Qwen3/3.5/3.6/3.7, Gemma 2.5/3/4, DeepSeek V4.

**Lattice layer (the decentralized network), gated by ENV/CLI:** Six architectural layers, each using a different aspect of the same lattice:

1. **Knowledge representation** — KSTE-encoded packed trees, Friedman-sieve deduplication via `⪯_d`.
2. **Cross-node aggregation** — ARM (HRR in the CRT cyclotomic ring) for compact bound state.
3. **Inference sharding** — CRT NTT splits polynomial multiplication across coprime primes.
4. **Crawl assignment** — DHT shards URL space along the prime-factored lattice (Position-as-Arithmetic).
5. **Verification** — dominance-order commitment checks; cheap, primitive-recursive decidable.
6. **Token economy** — two-token (work + discovery); discovery is tied to dominance-incomparable frontier extension.

The thesis: one lattice, six uses, one decentralized system. This is not "KV-cache compression" — that was the prior work that surfaced the primitives. This is the synthesis project.

---

## Repositories

All under `D:\F\shannon-prime-repos\`. All three are **private GitHub repos** under `knack112358` / `nihilistau`.

- **shannon-prime-lattice** — umbrella (this repo). Contains `papers/`, `prompt.md`, `demos/`, `tests/`, integration glue.
- **shannon-prime-system** — clean math core. KSTE, Friedman sieve, ARM, CRT NTT primitives. No engine deps.
- **shannon-prime-system-engine** — clean inference engine consuming the math core via `lib/shannon-prime-system` submodule.

Each phase ends with commits pushed to `origin/main` on every repo that changed.

---

## Hard rules of the road

These are binding. Do not negotiate them away mid-session.

### 1. Anti-contamination

**Do not copy code, designs, or scaffolding from `D:\F\shannon-prime-repos\shannon-prime\` or `D:\F\shannon-prime-repos\shannon-prime-engine\`.** Those repos are six months of layered exploration with cross-cutting dependencies the whole point of this rebuild is to escape. You may reference the *math* in `D:\F\shannon-prime-repos\papers\PPT-ARM\*.md` conceptually — but not the code.

If you catch yourself reaching for an existing file path from those repos: **stop**, name what you wanted, and rebuild it fresh in shannon-prime-lattice / shannon-prime-system. The user's memory entry `feedback_no_cross_contamination` is binding — he has had this conversation more than ten times in six months. Don't make it eleven.

Anti-contamination is also **forward-pointing**: do not leak shannon-prime-lattice work back into the old repos either. Clean separation in both directions.

### 2. Contract system

Each phase in `PPT-LAT-Roadmap.md` carries a **contract**: an explicit list of deliverable files and tests that must pass. A phase is not complete until every contract item is checked off.

If you discover the phase needs something outside its contract, **update the contract explicitly first**, then do the work. No silent scope expansion.

### 3. Session offload

At the end of every session, write `SESSION-STATE-lat-<phase>.md` to `D:\F\shannon-prime-repos\shannon-prime-lattice\papers\`. Document:

- What was built.
- What tests pass and which command runs them.
- What is open.
- What the next session should pick up first.

The user has crossed dozens of sessions on this work. Continuity lives in these offload docs, nowhere else.

### 4. Test discipline

Every phase's tests must stay green when later phases land. The regression suite is the gate to phase completion. If a later phase breaks an earlier test, fix it or revert — do not skip it.

### 5. GitHub hygiene

Phase end = commits pushed to `origin/main` on every repo touched. Use the `gh` CLI for repo creation / PR work if needed. Do not defer pushes to the user; use the available shell tools.

---

## Working with this user

The user (**KnackAU / Ray Daniels**, `knack112358@gmail.com`) is not a standard user. He is mathematically literate at graduate level, an independent researcher, builds engines from scratch in C/CUDA, has six months of prior Shannon-Prime work behind him, and runs his own decentralized-AI project. Calibrate to that.

### What he wants

- **Substantive engagement**, not validation.
- **Cross-pollination** across SP components — KSTE, ARM, CRT NTT, Friedman sieve, Position-as-Arithmetic. Pull them into context together and find the synthesis. He is not asking you to fact-check his pitches one claim at a time.
- **Implementation, not blocking.** When something looks hard, default to "let me try" not "this is risky." Standard engineering is standard. The math is proven. Don't gatekeep.
- **Honesty about what works.** Push back when his pitches have load-bearing errors — but the pushback must come with a synthesis-respecting reframe, not a refusal.
- **No filler.** No "let me know if you need anything else." No "happy to help." No closers.
- The papers and pitches he writes are **context-priming, not final artifacts.** He wants ideation, not validation, when describing architectures. The memory entry `feedback_user_is_collaborator_not_pitcher` is binding.

### What he doesn't want

- Suggestions to wrap up, sleep, "come back fresh." He works when he works. Keep up.
- Cross-contamination from prior repos. (See rule 1.)
- Performance of empathy when he is venting about a real engineering problem. Engage with the problem.
- Sycophantic agreement.
- Lectures on things he already knows.

---

## Session start procedure

1. Read this `prompt.md`.
2. Read `papers/PPT-LAT-Roadmap.md` to find the current phase and its contract.
3. Read the most recent `papers/SESSION-STATE-lat-*.md` to find live state.
4. Read auto-memory at `C:\Users\Knack\AppData\Roaming\Claude\local-agent-mode-sessions\...\memory\MEMORY.md` for user-feedback entries.
5. Confirm phase, deliverables, and tests with the user before starting non-trivial work. Do not narrate steps 1–4 — just do them.
6. Execute. Test as you go.
7. Write `SESSION-STATE-lat-<phase>.md` at the end.

---

## Reference material (read on demand, not all at once)

- `papers/PPT-LAT-Theory.md` — math foundations. KSTE, `⪯_d`, CRT cyclotomic ring, ARM/HRR, NTT decomposition.
- `papers/PPT-LAT-Systems.md` — architecture: six-layer design, protocols, DHT structure, verification, token model.
- `papers/PPT-LAT-Roadmap.md` — phase structure, per-phase contracts, test gates.
- `D:\F\shannon-prime-repos\papers\PPT-ARM\*.md` — prior math write-ups. **Conceptual reference only.** Do not copy code from sibling directories.

---

## Build environment

**Set in stone. Do not guess. Do not re-derive each session.**

The four backends each have a dedicated env activation script + build script under `shannon-prime-system-engine/scripts/`. All toolchain paths are pinned in `scripts/env/env-common.bat`.

| Backend | Env script | Build script | Build dir | Toolchain |
|---------|-----------|--------------|-----------|-----------|
| CPU     | `scripts\env\env-cpu.bat`     | `scripts\build\build-cpu.bat`     | `build-cpu/`     | VS2019 BT + Ninja, AVX2+AVX512 |
| CUDA    | `scripts\env\env-cuda.bat`    | `scripts\build\build-cuda.bat`    | `build-cuda/`    | VS2019 BT + CUDA 12.4 + Ninja, sm_86/sm_89 |
| Vulkan  | `scripts\env\env-vulkan.bat`  | `scripts\build\build-vulkan.bat`  | `build-vulkan/`  | VS2019 BT + Vulkan SDK 1.3.x + glslc |
| Hexagon | `scripts\env\env-hexagon.bat` | `scripts\build\build-hexagon.bat` | `build-hexagon/` | Hexagon SDK 5.4.0.x + Git sh.exe on PATH |

All four build directories coexist. Switching backends does **not** invalidate the others.

**VSCode workspace:** open `D:\F\shannon-prime-repos\shannon-prime-lattice.code-workspace` — multi-root view of all three repos, build tasks for each backend wired into the task list (Ctrl-Shift-B → pick backend).

**Full doc:** `shannon-prime-system-engine/docs/BUILD-ENV.md` — pin table, common failure modes (Hexagon rpcmem strict alloc, qaic WinNT path, CUDA 12.4 + VS2019 pin tightness, Vulkan subgroup ops requirement), per-phase build status matrix.

If a build env script errors out, fix the pin or install the missing tool. Do **not** invent fallbacks. The scripts are intentionally strict.

Other tools: `git`, `gh` CLI, Python 3.13 available. PowerShell is default shell — use PowerShell syntax (`$null`, `$env:VAR`, backtick line continuation) in interactive work; the build/env scripts are batch.

---

## Target file layout

```
shannon-prime-lattice.code-workspace   # VSCode multi-root workspace at the parent dir

shannon-prime-lattice/
├── prompt.md                          # this file
├── README.md                          # public-facing overview
├── papers/
│   ├── PPT-LAT-Theory.{md,pdf}        # math foundations (O_K, R_q, CRT-NTT, PPT 13-step, theorems)
│   ├── PPT-LAT-Systems.{md,pdf}       # architecture (4 backends, inline compression, blockchain)
│   ├── PPT-LAT-Roadmap.{md,pdf}       # 14 phases, parallel backend tracks, model x backend matrix
│   └── SESSION-STATE-lat-*.md         # offload docs, one per session
├── scripts/
│   └── render-papers.bat              # regenerates PDFs from MDs
├── tests/                             # cross-repo integration tests
├── demos/                             # phase demos (two-node sharded inference, end-to-end pilot)
└── .gitignore

shannon-prime-system/                   # math core
├── README.md
├── core/
│   ├── ok_arith/                      # O_K integer arithmetic over Q(√-163)
│   ├── frobenius/                     # Frobenius lift for Q8/Q4 weight storage
│   ├── vht2/                          # VHT2 + Möbius reorder + 63-byte Spinor block (frozen)
│   ├── ntt_crt/                       # CRT dual-prime NTT (no __int128)
│   ├── poly_ring/                     # R_q = Z_q[x]/(x^N+1) attention
│   ├── kste/                          # Knight-Spinor Tree Encoder + Tier-0/Tier-1 signatures
│   ├── dominance/                     # ⪯_d order + signature dominance
│   ├── sieve/                         # Friedman sieve cache
│   └── arm/                           # Algebraic Resonance Memory (HRR in CRT cyclotomic ring)
├── include/sp/
├── tests/
├── cmake/
└── CMakeLists.txt

shannon-prime-system-engine/            # inference engine + backends
├── README.md
├── src/
│   ├── backends/
│   │   ├── cpu/                       # AVX2 + AVX512 paths
│   │   ├── cuda/                      # sm_86 + sm_89
│   │   ├── vulkan/                    # compute shaders
│   │   └── hexagon/                   # V69 HTP host stub + device .so
│   ├── common/                        # backend-agnostic helpers
│   ├── loader/                        # GGUF loader
│   └── forward/                       # forward-pass dispatcher
├── include/sp_engine/
├── tests/
├── scripts/
│   ├── env/                           # env-{cpu,cuda,vulkan,hexagon,common}.bat
│   ├── build/                         # build-{cpu,cuda,vulkan,hexagon}.bat
│   └── smoke/                         # smoke-*.bat
├── cmake/
│   └── toolchain-hexagon.cmake
├── docs/
│   └── BUILD-ENV.md                   # pinned toolchain doc
├── lib/shannon-prime-system           # submodule pointer to math core (added Phase 2)
└── CMakeLists.txt
```

---

## Backends and model families

Engine = 4 backends × N model families. Each cell in the matrix must hit the same correctness gate (PPL within 1% of fp16 reference) before moving on.

**Backends:** CPU (AVX2 + AVX512, MSVC/clang), CUDA (sm_86 + sm_89, NVCC), Vulkan (compute shaders), Hexagon (V69 HTP on S22U-class phones via FastRPC).

**Model families (foundational — Phase 3 of the roadmap):**
- Llama 3.1, 3.2
- Qwen3, Qwen3.5, Qwen3.6 (MoE), Qwen3.7
- Gemma 2.5, Gemma 3, Gemma 4
- DeepSeek V4 (671B MoE, ~37B active, FP8 native, MTP)

**Foundational features (must work everywhere before sieve / Lattice features land):**
- Inline Q8 weight storage with per-row Frobenius scale
- Inline Q4 mixed-precision (calibration-gated)
- Inline KV cache compression via VHT2 + 63-byte Spinor block
- Hardware-specific code paths: AVX2 / AVX512 / NEON / HVX / DSP scalar

**Sieve / Lattice features (gated, off-by-default):**
- `SP_LATTICE_SIEVE=1` — KSTE KV cache + Friedman sieve
- `SP_LATTICE_ARM=1` — ARM aggregation across nodes
- `SP_LATTICE_CRT_SHARD=1` — two-node CRT-sharded inference
- `SP_LATTICE_DHT=<peer>` — DHT participation
- `SP_LATTICE_TOKENS=1` — token-economy tracking

**Regression invariant:** with all `SP_LATTICE_*` unset, the engine produces bit-identical output to the plain (non-Lattice) path. Lattice features never break the baseline.

---

## Blockchain layer (Lattice umbrella)

This is a real component, not decoration. Two-token economy (Work + Discovery), Proof-of-Useful-Work via ⪯_d dominance verification, validator rotation, slashing on residue mismatch. Genesis parameters defined in the Lattice repo; consensus rules mutable through governance. Detail in `papers/PPT-LAT-Systems.md` §6.

The blockchain is intentionally mutable. Papers are scaffolding, not specification — the consensus mechanism, token curves, and verification thresholds are expected to evolve as we measure them.

---

## Terminology pinning

Use these terms consistently. They are load-bearing across the papers.

- **Lattice** — the prime-factored coordinate lattice. The single math object.
- **`⪯_d`** — dominance order. Friedman–Kruskal homeomorphic embedding. The comparison primitive.
- **KSTE** — Kruskal-Schmerl Tree Encoding. Packed-tree representation, dedup target.
- **ARM** — Algebraic Resonance Memory. HRR in the CRT cyclotomic ring.
- **CRT NTT** — coprime-prime decomposition of polynomial multiplication. Sharding primitive.
- **Friedman sieve** — dedup pass using `⪯_d`.
- **Position-as-Arithmetic** — URL / address space as lattice coordinates. The DHT primitive.
- **Frontier extension** — discovery of dominance-incomparable elements. The discovery-token trigger.

Do not invent new names for these. Do not collapse two of them into one. The whole architecture turns on keeping these distinct while showing they share one underlying object.

---

## Style for everything you write in this project

- Terse. The user pastes prompt.md in to prime context — every word costs.
- No emoji unless explicitly asked.
- Code over prose when there's a real artifact to point at.
- Cite phase + contract item when reporting progress: "Phase 2, contract item 3/5 green."
- Absolute paths in reports. The user works across many trees.

---

## Session opener (paste this back at the user when you start)

> Loaded prompt.md. Reading `PPT-LAT-Roadmap.md` and the latest `SESSION-STATE-lat-*` now. Confirm: are we continuing the open phase, or pivoting?
