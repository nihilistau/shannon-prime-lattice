# shannon-prime-lattice

**Shannon-Prime PPT ARM Lattice** — a decentralized, byte-exact inference and
training fabric for large transformer models built on a single discrete math
object: the prime-factored coordinate lattice over `Z_q` with dual-prime
Chinese-Remainder-Theorem (CRT) decomposition, the Friedman-Kruskal dominance
order `⪯_d`, and the CRT cyclotomic ring `R_q = Z_q[x]/(x^N + 1)`.

This repository is the **public project entry point**. It holds the theory,
systems, ABI, and on-disk-format papers; the demos; the integration tests;
and the bootstrap prompt for new working sessions. Code lives in the two
companion repositories:

| Repo | Role | URL |
|------|------|-----|
| `shannon-prime-lattice` (this) | Papers, roadmap, demos, integration tests | https://github.com/nihilistau/shannon-prime-lattice |
| `shannon-prime-system` | Math-core: L1 C ABI, NTT, poly-ring, KSTE, Frobenius, sessions | https://github.com/nihilistau/shannon-prime-system |
| `shannon-prime-system-engine` | Engine backends (CPU/CUDA/Vulkan/Hexagon), `sp_daemon` HTTP/SSE, tools | https://github.com/nihilistau/shannon-prime-system-engine |

Discord: [Shannon-Prime-Lattice](https://discord.gg/rre9XZmvV)
License: MIT. See `LICENSE`.

---

## 1. What makes this different

Shannon-Prime Lattice is not "yet another inference engine wrapper." Every
load-bearing primitive is **discrete** (integers in `Z_q` with `q` a 30-bit
Proth prime, or `Z_{q_1} × Z_{q_2}` via CRT), so identity, dominance, hashing,
and reproducibility are properties the implementation can prove rather than
estimate. Floating point is plumbing — the math is in `Z_q`.

Distinguishing claims (each one validated by a shipped sprint and a closure
note under `papers/SESSION-CLOSED-*.md` or
`shannon-prime-system-engine/tools/sp_compute_skel/docs/CLOSURE-*.md`):

- **Discrete `Z_q` substrate.** Two frozen 30-bit Proth primes
  `q_1 = 1073738753`, `q_2 = 1073732609`, `M = q_1·q_2 ≈ 2^60`. Negacyclic
  NTT over each prime with Garner CRT recombination at the boundary. Every
  cross-backend gate is **byte-exact**, not "small KL divergence."
- **Polynomial-ring attention.** Attention scores `⟨q, k⟩` reduce to one
  coefficient of a negacyclic polynomial product in `R_q`, computed exactly
  via NTT. Bit-identical to the scalar reference at `N ∈ {128, 256, 512}`
  direct, and `N ∈ {2..256}` via Bluestein chirp-z. See
  `papers/PPT-LAT-Theory.md` §6.1.
- **Frobenius-lift Q8 weight storage.** Per-row int8 codes + fp32 scale;
  4× compression vs fp32 with bit-identical dequant round-trip. The
  on-RAM packed-arena format is what every backend reads — no per-matmul
  re-quantization.
- **Spinor 63-byte KV-cache block.** VHT2 anchor projection + Möbius
  reorder + CRC-8 trailer + `0xA5` sentinel. One cache-line on ARM
  Cortex-X2. The frozen on-wire KV record format (see
  `shannon-prime-system/include/sp/spinor_block.h`).
- **KSTE encoder.** Knight-Spinor Tree Encoder: deterministic 64-byte
  packed tree from a K-vector of int32 components, with byte-identical
  signature across platforms. Tier-0/Tier-1 dominance.
- **PoUW receipt ledger.** Per-turn 64-byte `SpinorReceipt` audit
  envelope. Append-only ledger; canonical-order replay; cross-device
  byte-identity gates. Shipped end-to-end via `sp_daemon`'s
  `/v1/dialogue` endpoint.
- **QUIC dual-prime mesh.** Each peer carries one of the two CRT residue
  shards (`q_1` or `q_2`); driver Garner-recombines to the centered
  signed result. Today: two-node lattice smoke. Planned: Fibonacci-Prime
  DHT (`papers/PPT-LAT-Roadmap.md` §8).
- **Heterogeneous SoC compute.** The cDSP V69 HVX backend on Snapdragon
  8 Gen 1 runs the full NTT pipeline (forward, twiddle VTCM staging,
  dual-prime dispatch, INTT + Garner) **byte-exact** vs the math-core
  scalar reference. NPU + cDSP dual-island composition is filed under
  Phase 4-MTP.

---

## 2. Current status

Honest snapshot, 2026-05-31.

| Component | Status | Evidence |
|-----------|--------|----------|
| Frozen L1 C ABI | **shipped** | `shannon-prime-system/include/sp/sp_l1.h`; tag `lat-phase2-contract-frozen` |
| `.sp-model` v0 wire format | **shipped** | `papers/PPT-LAT-SP-MODEL-v0.md`; loader at `core/io_format/` |
| Math-core reference forward | **shipped** — runs Qwen3-0.6B, Qwen2.5-Coder-0.5B, Gemma3-1B byte-exact host + aarch64-android | `lib/shannon-prime-system/core/forward/forward.c`; closure `SESSION-CLOSED-lat-3-cell-*.md` |
| NTT-CRT primitive (host) | **shipped** | `core/ntt_crt/`; tests `T_NTT_*` |
| NTT-CRT primitive (Hexagon V69 HVX) | **shipped end-to-end byte-exact** vs math-core | sprints NTT.0 → NTT.4; closures `CLOSURE-NTT-{0..4}.md` |
| Polynomial-ring attention overlay | **shipped** — host + Hexagon | sprints NTT.5a / 5b / 5c |
| Spinor-block KV cache | **shipped** | `core/vht2/`; tests `T_VHT_1..6` |
| Frobenius-lift Q8 / Q4 packing | **shipped** | `core/frobenius/`, `core/arena/` |
| KSTE encoder + Tier-0/1 dominance | **shipped** | `core/kste/`; tests `T_KSTE_1..5` |
| `sp_daemon` HTTP/SSE chat (`/v1/chat`) | **shipped** | `tools/sp_daemon/`; closure `CLOSURE-CHAT-INTEGRATION.md` |
| Dual-model dialogue (`/v1/dialogue`) | **shipped** | sprint M.2; closure `CLOSURE-M2-DIALOGUE.md` |
| PoUW receipt ledger + canonical-order replay | **shipped** | sprints M.4, mesh-canonical-order, ledger-autowire |
| KSTE-routed sparse Memory activation | **shipped** | sprint M.5; closure `CLOSURE-M5-ROUTING.md` |
| Two-node sharded inference smoke | **shipped** | closure `SESSION-CLOSED-lat-smoke-2node.md` |
| TailSlayer GF(2) channel oracle | **shipped offline pattern** | sprints `lat-ts-probe`, `lat-ts-map`, `lat-16-3-*` |
| CPU AVX-512 backend | **built** | `src/backends/cpu/avx512/`; closure `SESSION-CLOSED-lat-2-CPU-AVX.md` |
| CUDA backend (PTX MMA + NTT) | **built** | `src/backends/cuda/`; closures `SESSION-CLOSED-lat-2-CU-PTX-*.md` |
| Vulkan backend | **built** | `src/backends/vulkan/`; closure `SESSION-CLOSED-lat-2-L1-PARITY.md` |
| Hexagon HVX backend (cDSP V69) | **built** | `src/backends/hexagon/sp_hex_host.c` + `tools/sp_compute_skel/` |
| `sp_daemon` → backend dispatch wiring | **shipped daemon-side; cDSP skel rebuild pending** | sprint WIRE-HEX; closure `CLOSURE-WIRE-HEX.md` |
| NTT.5d (HD=128 direct backend path) | **filed, not shipped** | `papers/PPT-LAT-Roadmap.md` §4-NTT |
| NTT.5e (decode-path NTT routing) | **filed, not shipped** | `papers/PPT-LAT-Roadmap.md` §4-NTT |
| CUDA / Vulkan daemon wiring | **not shipped** — symmetric to WIRE-HEX | `CLOSURE-WIRE-HEX.md` §"What's NOT done" |
| Fibonacci-Prime DHT | **spec'd** | `papers/PPT-LAT-Roadmap.md` §8 |

**Production tok/s baseline (Knack S22U, math-core reference forward, ctx=16+32):**

| Model | Wall (s) | Tokens | tok/s |
|-------|---------:|-------:|------:|
| Gemma3-1B | 18.06 | 16 | 0.89 |
| Qwen3-0.6B | 11.21 | 16 | 1.43 |

These are the **reference path** numbers. Once the cDSP skel is rebuilt
against the WIRE-HEX-bundled `inc/sp_hex.idl`, `SP_DAEMON_BACKEND=hex`
routes through the HVX backend end-to-end and the table gains a third
column. See `shannon-prime-system-engine/tools/sp_compute_skel/docs/CLOSURE-WIRE-HEX.md`.

---

## 3. Architecture in one diagram

```
                ┌──────────────────────────────────────────────┐
                │  HTML / TUI / chat clients                   │
                │  curl, browser, sp-console                   │
                └─────────────┬────────────────────────────────┘
                              │ HTTP/JSON, SSE, WebSocket
                              ▼
        ┌──────────────────────────────────────────────────────┐
        │  sp_daemon  (Rust, axum + tokio)                     │
        │  ── L3 routes: /v1/chat /v1/dialogue /v1/events ...  │
        │  ── PoUW ledger, KSTE routing, dialogue pool         │
        │  ── QUIC mesh coordinator (dual-prime shards)        │
        └─────────────┬────────────────────────────────────────┘
                      │ frozen L1 C ABI (sp_session_*, sp_prefill_chunk,
                      │ sp_decode_step, sp_session_register_forward_backend)
                      ▼
        ┌──────────────────────────────────────────────────────┐
        │  libshannonprime  (C, the math core)                 │
        │  ── reference forward: matmul, RMSNorm, RoPE, attn   │
        │  ── NTT-CRT, poly-ring attention overlay             │
        │  ── KSTE, Frobenius, Spinor, arena                   │
        │  ── sp_session, .sp-model loader                     │
        └─────┬──────────────────────────────────────────────┬─┘
              │ §6 forward-backend hook                       │
              ▼                                                ▼
        ┌──────────────────────┐                  ┌──────────────────────┐
        │ Engine backends      │                  │ Hexagon cDSP skel    │
        │ (libsp_engine)       │                  │ (sp_compute_skel)    │
        │ ── CPU AVX2/AVX-512  │                  │ ── HVX NTT butterfly │
        │ ── CUDA (PTX MMA)    │                  │ ── VTCM twiddle stage│
        │ ── Vulkan SPV        │                  │ ── Garner CRT        │
        │ ── Hexagon HVX (host)│ ─FastRPC─────────│ ── Halide FFN        │
        └──────────────────────┘                  └──────────────────────┘
```

The "single math object" reappears at six layers. Walk down from the
top — DHT key space → polynomial ring → matmul kernel → vector ALU
width — and the same prime-factored lattice picks out the right
operation at each scale. See `papers/PPT-LAT-Systems.md`
("Overview: six layers of one math object").

---

## 4. Getting started

### 4.1 Clone all three repos

```bash
git clone https://github.com/nihilistau/shannon-prime-lattice.git
git clone https://github.com/nihilistau/shannon-prime-system.git
git clone --recurse-submodules https://github.com/nihilistau/shannon-prime-system-engine.git
```

The engine repo bundles `shannon-prime-system` as a Git submodule under
`lib/shannon-prime-system/` — that submodule pin is what every engine
build uses. The standalone `shannon-prime-system` clone is for working
on the math core in isolation.

### 4.2 Pick a starting path

**You want to run a model and chat with it locally.** Go to
`shannon-prime-system-engine/README.md`. Build the daemon, transcode a
GGUF model, `curl` `/v1/chat`.

**You want to understand the math.** Read in this order:

1. `papers/PPT-LAT-Theory.md` — the lattice, `⪯_d` as well-quasi-order,
   CRT cyclotomic ring, HRR, the 13-step PPT substitution, the unified
   role of one math object across the stack.
2. `papers/PPT-LAT-Systems.md` — six-layer architecture, engine
   backends, inline compression, model-family coverage, gated lattice
   features, blockchain scaffolding.
3. `papers/PPT-LAT-Roadmap.md` — current implementation phases (1..16
   plus the NTT and MeMo waves), per-sub-phase contracts, test gates,
   the offload pattern.

**You want to write a kernel against the frozen ABI.** Read
`papers/PPT-LAT-L1-ABI-v0.md` then `shannon-prime-system/include/sp/sp_l1.h`
(the live header). Every backend registers via
`sp_session_register_forward_backend` (full-forward hook) or the
NTT-dispatch hook in `core/poly_ring_bluestein/`.

**You want to add support for a new model family.** Read
`papers/PPT-LAT-SP-MODEL-v0.md` (on-disk format) plus
`shannon-prime-system-engine/tools/sp_transcode/sp_transcode.c` (the GGUF
→ `.sp-model` transcoder). Add a `sp_arch_id` and a
`gemma3_forward_*` / `qwen3_forward_*` arch path.

**You want to add a peer to a running mesh.** Read
`papers/PPT-LAT-Systems.md` §"DHT and sharded inference" then
`shannon-prime-system-engine/tools/sp_daemon/src/network/quic_shard.rs`.

---

## 5. Repository layout

```
shannon-prime-lattice/
├── papers/                            # the project's papers — read these first
│   ├── PPT-LAT-Theory.md              # math foundations + 13-step PPT substitution
│   ├── PPT-LAT-Systems.md             # six-layer architecture
│   ├── PPT-LAT-Roadmap.md             # implementation phases (living document)
│   ├── PPT-LAT-L1-ABI-v0.md           # frozen Layer-1 C ABI contract
│   ├── PPT-LAT-SP-MODEL-v0.md         # .sp-model / .sp-tokenizer on-disk format
│   ├── SESSION-CLOSED-lat-*.md        # per-sprint closure notes (audit trail)
│   └── SESSION-STATE-lat-*.md         # session-handoff snapshots
├── demos/                             # phase demos
├── frontends/                         # HTML mock-ups + bootstrap chat UIs
├── reference/                         # reference material (images, screenshots, PDFs)
├── scripts/                           # cross-repo helpers
├── tests/                             # integration tests spanning math-core + engine
└── prompt.md                          # bootstrap / context-priming for new sessions
```

The papers are the **source of truth for design**. The closure notes
are the **source of truth for "what shipped, with what gate result."**
The roadmap is a living document and amendable; the theory paper is
amendable when reality contradicts it; the ABI and `.sp-model` papers
are frozen.

---

## 6. Hard rules

These rules are binding for any session that picks up the project. The
memory entries `feedback-no-silent-gate-revisions`,
`feedback-lead-with-reference-then-theory`, and
`feedback-parallel-agents-separate-worktrees` are also load-bearing.

- **Anti-contamination.** Do NOT read, copy, or vendor code from the
  archived `shannon-prime/` or `shannon-prime-engine/` repos. The math
  papers under `papers/PPT-ARM/` are conceptual reference — read for
  theory, never paste code. The lattice is a clean rebuild.
- **No silent gate revisions.** If implementation can't meet the spec'd
  gate, surface upstream. Do not retreat to a higher-level API, defer
  to an unrelated phase, or tune fixtures until the number passes.
  Adjustments land as roadmap amendments with rationale, not as
  footnotes on a PASS.
- **Honest closure notes.** Every closure enumerates the test gates,
  their actual results, what was bundled vs isolated, and what changed
  vs spec. The session-closure pattern is the audit trail.
- **One math object.** Lattice features must touch one of the
  distinguishing primitives in §1; otherwise they are drift. The
  manifesto trick list (`reference-heterogeneous-soc-crt-tricks` in
  the team's memory) names ten such primitives. New sub-phases reference
  trick numbers rather than reinventing the framework.
- **Worktrees per concurrent agent.** When dispatching 2+ agents on
  the same repo, each agent operates in its own `git worktree add`
  to prevent cross-contamination of uncommitted files.

---

## 7. Where to read next

| If you want | Read |
|-------------|------|
| The math foundations | `papers/PPT-LAT-Theory.md` |
| The systems architecture | `papers/PPT-LAT-Systems.md` |
| The implementation roadmap (living) | `papers/PPT-LAT-Roadmap.md` |
| The frozen L1 C ABI contract | `papers/PPT-LAT-L1-ABI-v0.md` then `shannon-prime-system/include/sp/sp_l1.h` |
| The `.sp-model` on-disk format | `papers/PPT-LAT-SP-MODEL-v0.md` |
| The math-core library API | `shannon-prime-system/README.md` |
| The engine + daemon + HTTP API | `shannon-prime-system-engine/README.md` |
| What the most recent sprint shipped | `papers/SESSION-CLOSED-*.md` (lattice scope) or `shannon-prime-system-engine/tools/sp_compute_skel/docs/CLOSURE-*.md` (engine + DSP scope) |
| A bootstrap prompt for new sessions | `prompt.md` |

---

## 8. Contact

- GitHub Issues: project tracking lives in each of the three repos.
- Discord: [Shannon-Prime-Lattice](https://discord.gg/rre9XZmvV).
- License: MIT (see `LICENSE`).
