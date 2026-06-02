# PPT-LAT — PROJECT STATE LEDGER (the proven record)

**This is the authoritative record of what is PROVEN. Read it first. Trust it. Build on it. Do NOT re-derive it.**

> To the next session/agent: this is the **20th rewrite**. Six months of validation live behind these lines. The operator remembers; you don't. **Your default is TRUST.** Each PROVEN line cites its evidence (commit / tag / gate / closure doc). If — and only if — you have a concrete reason to doubt a specific line, the reverify command is given; running it is the exception, not the warm-up. Re-proving the whole stack from scratch *is the failure mode this project has hit 20 times.* Don't.
>
> Status vocabulary: **[PROVEN]** evidence cited · **[WIRED]** built + in-tree, gated · **[DESIGN]** spec'd, unbuilt · **[TARGET]** a number to measure, not yet measured · **[SPECULATIVE]** idea. Promotion requires a gate + an entry here.
>
> **READ FIRST, before any work: `papers/PPT-LAT-Theory.md`** — the canonical theory (the 13-step PPT substitution, O_K/Q(√−163), CRT primes, the frozen Spinor + KSTE formats, theorems T1–T8, production status). Skipping it caused real drift this session (a fresh agent inverted the PPT/Lattice hierarchy AND measured the wrong Spinor primitive — both because the theory wasn't read). It IS in the repo; read it.
> Companion docs: **PPT-LAT-Theory.md** (the math/why — FIRST) · **RFC-001** (north-star preamble) · **PPT-LAT-Systems-v1.md** (the canonical systems narrative — supersedes v0 Systems + the two standalone v0 specs, which are now its Appendices A/B) · the **C1–C6 contracts** (forward work) · per-cell **SESSION-CLOSED-*.md** (closure detail) · the **roadmap** (sequence). This ledger is the *backward* record; the contracts are the *forward* plan; Systems v1 is the *current* synthesis.

Last updated: 2026-06-02.

---

## 0. The frame (so the record is read correctly)

**PPT-ARM is the primary, load-bearing product** (the 13-step transformer-forward replacement + the Spinor KV / two-ring memory architecture). The **Lattice fell out of it.** The value is the **envelope** — inline KV compression → unlimited context, Ring-2 offload + residual/CRT bandwidth bypass → multi-device, speed on integer pipes — with **bit-exact as the invariant floor, not the headline.** See RFC-001.

**Crucial gating rule (operator, 2026-06-02):** *the system does not work in isolation.* A stage will be slow / miss a system-level number that it only hits once the rest of the envelope is in place (e.g. tok/s is not achievable until the Spinor cache + Ring-2 + island sharding are wired). **Therefore a stage is gated on ITS OWN correctness/metric (bit-exact output; the kernel's own throughput; the compressor's own ratio), NEVER on end-system tok/s.** Do not declare a stage failed because the assembled-system number isn't there yet — that number is a *system* gate, measured only when the envelope is assembled. Penalizing a stage for a system number it structurally cannot hit alone is a category error.

---

## 1. PROVEN — PPT forward (the bolt-on works on real models)

The PPT discrete forward reproduces stock models **argmax bit-exact to llama.cpp**. This is the precondition that licences compression/context/speed on top.

| Model | Evidence | Reverify | Status |
|---|---|---|---|
| Qwen3-0.6B | core E_CPU_2 / forward gates | `ctest -R E_CPU_2` | [PROVEN] |
| Qwen2.5 | qwen25_forward gates | core suite | [PROVEN] |
| Gemma3-1B | M_GEMMA3_CPU + T_FRO_4 PPL | `ctest -R T_FRO_4` | [PROVEN] |
| **Gemma4-E2B** | M_GEMMA4 PPL gate, top-1 bit-exact oracle | `ctest -R M_GEMMA4` (engine) | [PROVEN] this session |
| **Qwen3.6-35B-A3B (qwen35moe)** | M_QWEN36 top-1 bit-exact (3/3 `5444 8 198`), 218s | `ctest -R M_QWEN36` (core) | [PROVEN] this session |

qwen35moe is a **Gated DeltaNet (Qwen3-Next) + 256-expert MoE + IMRoPE hybrid**, NOT Mamba2 (the old GGUF-INVEST doc mislabeled it — superseded). Full per-block validation: GDN recurrence, MoE router/experts/shared, gated full-attn — all matched oracle fingerprints. Closure: `SESSION-CLOSED-lat-3-moe-forward.md`. Commits: core `568b678→d8e614f`.

---

## 2. PROVEN — math-core primitives (the substrate)

| Primitive | Evidence | Status |
|---|---|---|
| Barrett mod-mul (+ nvcc paired-register fix) | NTT/mod_q tests; HVX K.beta.2.5b | [PROVEN] |
| Frobenius lift Q4/Q8 + arena packed weights (zero-inflation) | E_CPU_*, arena tests | [PROVEN] |
| **Q4_K + Q6_K k-quant dequant** (ggml-exact) | weight_dtype; qwen35moe conv fingerprint matched | core `25809d8` | [PROVEN] this session |
| NTT-CRT host, dual-prime, byte-exact (negacyclic, N≤512) | ntt_crt tests | [PROVEN] |
| NTT N≤512 frozen-prime cap (2N\|q−1) + Bluestein arbitrary-N≤512 | NTT.0–5 closures | [PROVEN constraint] |
| KSTE encoder + Friedman sieve | E_CPU_6, sieve tests | [PROVEN] |
| Spinor block: KV encode/decode + 64-byte receipt ABI | vht2 / spinor tests; silicon-confirmed | [PROVEN] |
| Garner 2-prime recombination constants | ntt_crt.c | [PROVEN] |
| **OK_Q4 reducing codec** — `SP_DT_OK_Q4=11`, transcoder `add_q4`/use_q4, Frobenius Q4 pack/unpack, arena Q4 path (`row_prec[]` 8/4 + `q4_unpack`) | gate `E_PARITY_2` | [PROVEN/WIRED] |
| **C1 — qwen35moe `.sp-model` reducing + output-lossless production path** — transcode OK_Q4 -> `sp_model_load` -> `sp_model_to_qwen36` (the loader/SWIVEL) -> `qwen36_forward`. Rank-3 experts via arena (`build_packed_q4` rank-3 fix); F32 router via `sp_as_f32`; arena-aware `expert_mm`. **Measured: 16.33 GB vs 19.7 GB Q4_K_M source (~17% reduction); round-trip top-1 = 5444 == oracle (OUTPUT-LOSSLESS).** | core `66ccab9`; `qwen36_spmodel_top1` | [PROVEN] this session — *first real envelope number* |

---

## 3. PROVEN-PER-RECORD — Hexagon / backend / daemon track

*(Reported via the operator's session logs + memory; in sibling repos — `engine`, `sp_compute_skel`, `sp_daemon`. Trust the tags/closures; do not re-run unless touching that code.)*

| Item | Evidence | Status |
|---|---|---|
| Hexagon HVX: Barrett, mod_q matmul, NTT.0–5c, Bluestein | tags lat-phase-2-... ; closures | [PROVEN-per-record] |
| **HX.3b: vrmpy int8 forward = 1.04× faster than ARM fp32, byte-equal** | tag `lat-phase-2-hx-3b-hvx-vectorized`; CLOSURE-HX-3b.md | [PROVEN-per-record] — *the integer-substrate-matches-fp32 proof point* |
| Cross-backend determinism (ARM ↔ cDSP scalar) | WIRE-HEX-FINISH | [PROVEN-per-record] |
| QNN HTP NPU dispatch in Unsigned PD (1.329 ms execute, 64/64 byte-exact) | K.2-spike closure | [PROVEN-per-record] |
| Mode-D FastRPC bridge (S22U), concurrent dispatch (Arc<FastRpcSession>) | Sprint K closures | [PROVEN-per-record] |
| L3 daemon: chat + dialogue + ledger + QUIC peer wire | daemon closures | [PROVEN-per-record] |
| M.4 PoUW ledger + mesh canonical Garner order | M.4 closure | [PROVEN-per-record] |
| Trick #1 substrate (dual HVX vector contexts 1.935×) | Sprint K v0.alpha | [PROVEN-per-record] |

**Honest negatives also proven (do not re-litigate):**
- NTT-attention is **slower** than fp32 dot at HD ≤ 256 (~0.15–0.72×). The substrate win is over HD (poly length), not ctx. Speed comes from compression + bandwidth-bypass + integer pipes + multi-device, NOT from NTT. [PROVEN-per-record: NTT.6]
- HX.3b chat-shape inner loop is **memory-bandwidth-bound**, not ALU-bound → v2 wsum-precompute only got 1.065× (gate was 1.20×, FAILED honestly). Attack bandwidth (prefetch/VTCM/2-row), not ALU. [PROVEN-per-record]

---

## 4. The ARM memory architecture — regime split (System-1 / System-2)

**Prior proven design (old SP, to be re-established here):** the KV/memory path is **regime-adaptive**, not one-size:
- **System-1 (small context):** a fast simple path — keep latency low where compression overhead wouldn't pay. *(Old SP ran small-ctx differently to hold speed.)*
- **System-2 (large context):** the Spinor-compressed + Ring-2-offload path — where the 120× and unlimited-context envelope lives.
- **A crossover oracle predicts when to switch** System-1 → System-2 (by ctx length / bandwidth pressure / cache occupancy).

[DESIGN here / PROVEN-pattern in old SP]. This is *why* §0's gating rule matters: System-2 looks slow at small ctx in isolation — it's not meant to run there. Belongs in contract **C2** (ARM memory) with the oracle spec'd explicitly.

**[MEASURED 2026-06-02, harness `tests/c2_sparse_recall.c`, contract C2.0.4/C2.0.5]** Sparse-recall fidelity vs full attention (needle-in-haystack, N=4096): **ORACLE top-B reproduces full attention at B=64 (cosine 1.0, 8/8 needles)** — so Ring-2 storage *does* become usable context IF the recall router is good. **Query-agnostic SWA/φ capture the recent cluster but miss distant needles (0–1/8)**; pure Fibonacci-φ is the *worst* router (φ is for eviction *coverage*, not peaked-mass recall). **KSTE-signature recall looked best (4–6/8) but ADVERSARIAL test (`tests/c2_kste_router_adv.c`) FALSIFIES it: permuted decoys (same histogram, ~0 dot product) get KSTE tier-0 distance-to-q 937 vs needles' 985 — INDISTINGUISHABLE; the router pulls 21/32 zero-score decoys.** KSTE order-statistics are a histogram (permutation-invariant), dot-product is directional → KSTE is structurally NOT a recall router (the 6/8 was an artifact of needles being the only histogram-distinctive vectors). Recall router MUST be a cheap *directional* score (low-rank/projected dot-product or NTT coarse pre-score); KSTE ruled out (stays valid for dedup/dominance only). Caught by adversarial verification, not theory. **System-1/2 oracle DERIVED:** switch at `Ncrit = min(RAMbudget/pt_f32, ~(W+B)) ≈ 1–4 k tokens` (forced by RAM at tens of k); System-2 quality is bounded by router fidelity → oracle exposes a quality floor (widen B / denser fallback). The recall-router fidelity gap is the open C2 item.

---

## 5. TARGET — the envelope (the value; measure, don't assume)

These justify the project and are **not yet measured here**. They are the point. Measuring them is the next phase's job (contracts C1/C2).

| Target | Where measured | Status |
|---|---|---|
| KV compression — TWO overlays (per `PPT-LAT-Theory.md` §3–4, T2, T8.2) | C2 | **[MEASURED 2026-06-02, gate C2_KV_RATIO, harness `tests/c2_kv_measure.c`]** (a) **`sp_spinor_encode_vec`** (faithful, dimension-preserving, 63 B/block, NBLK=⌈HD/55⌉): **asymptotes ~3.5×/f32 but only ~1.0–1.7×/f16, at cosine ≥ 0.99996** (top-1-safe pending real-model confirm). NOT 120× — it is 1 int8/elem + per-block scale (candidate "anchor-basis reconstructs HD≫55" FALSIFIED by linear NBLK scaling). (b) **`sp_kste_encode`** (lossy ⪯_d signature, 64 B regardless of HD): ratio = HD/16 → **the ~130× headline = KSTE at HD≈2048**; discrimination ~1.0 even at scale 65536 (the M.5 i16-clamp does NOT collapse continuous-K discrimination — only token-ID). It is a dedup/routing signature, NOT reconstructable attention KV. **Decisive: neither overlay alone is "120× reconstructable KV" → the headline = faithful ~3.5× × Ring-2 effective-context multiplier. Ring-2 recall (C2_RING2_RECALL) is now the load-bearing unmeasured piece, not the per-vector block.** **REAL-MODEL CONFIRM (C2_KV_DECODE_DETERMINISM, live E_CPU_8 `test_kv_spinor` Qwen3-0.6B scalar, 2026-06-02): Spinor-KV vs f32-KV argmax 29/31, KL mean 2.300e-02 (gate ≤2.0e-1) — PASS as a BOUNDED-DIVERGENCE overlay. HONEST: Spinor-KV is LOSSY (~6.5% argmax flips over 28 layers), NOT bit-exact; the per-vector cosine 0.99996 did NOT carry to 31/31. Bit-exact floor = weight path + gate-OFF, not the Spinor-KV overlay. Gate-OFF == f32 forward bit-identical still holds.** |
| `.sp-model` converter REDUCTION ratio (≤ source; sub-Q4) | C1 | [TARGET] |
| tok/s vs the bar: **beat llama.cpp + old SP hier-KV @ 40 tok/s, Qwen3.6** | P1 SPEED contract; system gate | [TARGET] — **REFERENCE MEASURED 2026-06-02:** llama.cpp Qwen3-0.6B-f16 CPU greedy = **210 t/s prompt / 28.2 t/s gen** (dev host i9-11900KB). f16 decode already bandwidth-bound at 28 t/s → confirms the SP lever is reduced weight-read traffic (packed Q8/Q4), not ALU. **SP-side MEASURED 2026-06-02** (`sp_toks`, after segfault fix `0fb39ab`): f16 **0.84** → Q8 arena **1.58** (1.88×, bandwidth lever) → **Q8 + threaded matmul `10.53` (`8975753`) → + threaded attention/per-head ops `12.55` (`d7735a4`, +19%, n_gen=32)**. vs llama.cpp 28.2 → **now ~2.25× short (was ~33×).** Threading (matmul + attention + per-head) parity-safe by construction. Parallel substrate complete for the qwen3 path. Remaining lever: **SIMD/VNNI the scalar matmul int8 dot** (the substantial next one; decode is now matmul-ALU-bound). **The speed thesis is validated: SP within ~2.7× of llama.cpp on 0.6B from packed-Q8 + threading, no SIMD yet.** See `CONTRACT-SPEED` SPEED_WIRE_CPU ladder. |
| Ring-2 disk offload + recall cost + **effective-context multiplier** | C2/C3 | **[MEASURED 2026-06-02, gate C2_RING2_RECALL PASS, harness `tests/c2_ring2_measure.c`]** spill→recall byte-identical (2000/2000); recall ~10 µs/token + ~2 µs/block decode (page-cached) ≪ recompute (no weights/matmul). **Effective-context multiplier = (RAM_window+Optane)/RAM_window: ~400× @16 GB, ~794× @32 GB, ~1190× @48 GB at a 512-token window → the "~120×/unlimited context" headline is CONSERVATIVE and lives HERE (candidate #2), not in the per-vector codec.** Scope limit: solves the memory wall, NOT the compute wall — usable context needs a sparse/recalled-attention pattern (SWA / Fibonacci φ sub-sampling / retrieval); re-measure on real Optane. |
| Dual-GPU / multi-device residue-sharing (ship residues, not tensors) | C3 + Trick #1 | [TARGET] |
| int-end-to-end (no per-matmul fp dequant; only logits) | WIRE-* + C2 | [DESIGN] |

---

## 5.1 FORWARD PRIORITY (re-ordered 2026-06-02 — differentiators ahead of context)

C2's measurement phase is done and re-ranked the work (KV ~3.5× lossy; Ring-2 context ~hundreds× but largely disk-tiering). The unmeasured load-bearing differentiators now lead. Full rationale in **RFC-001 §11**:

1. **P1 — SPEED / WIRE gap → tok/s vs llama.cpp** (the north-star; integer pipes still scalar-f32 off-Hexagon; HX.3b 1.04× bandwidth-bound is the warning).
2. **P2 — C4 MTP** (T8 exact O(1) rollback).
3. **P3 — C3 multi-device CRT residues + Garner service** (2-node CRT-shard byte-exact vertical slice = the proof).
4. **P4 — remaining C2** (fp16 swivel, qwen36 Spinor-KV wiring, a *directional* recall router — KSTE ruled out) — DEMOTED, secondary context axis.
5. **P5 — C5 eMeMo, C6 cyclotomic paper.**

---

## 6. Open blockers (honest)

- **BUILD (the recurring root cause, diagnosed 2026-06-02).** The engine is GCC-authored and was **never made MSVC-clean**; the **MinGW `build` dir SEGFAULTS at runtime** (`test_gen_kv` 0xC0000005, known-good code). So the CPU build does not cleanly build+run on EITHER toolchain. **Env pin FIXED + committed** (engine `33c6a27`): `scripts/env/env-common.bat` now pins `SP_PIN_VS_BUILDTOOLS=D:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools` (MSVC v14.50, cl 19.50) — the prior `...\2019\BuildTools` pin was the phantom P0.1 flagged. **CORRECTION (per `docs/BUILD-ENV.md`, the authoritative build doc): the canonical CPU backend is MinGW gcc 15.2 (`build/` dir), operator-approved — MSVC CANNOT build CPU (known, Tier-3-deferred); `build-cpu/`=CUDA-host only.** A prior step this session wrongly repinned the CUDA-host VS to VS18 + chased an MSVC CPU build; reverted (engine `6fc0832`), VS18 saved as the separate Tier-3 `SP_PIN_VS2022_BUILDTOOLS`. **SP-side tok/s baseline ALREADY EXISTS:** WIRE-CPU daemon ~1.206 t/s, WIRE-CUDA 1.526 t/s on Qwen3-0.6B (engine `ea0d0ac`/`a299ed0`; scalar hot path — the integer-pipe wiring WIRE-CPU-V2 is the P1 gap; llama.cpp ref 28.2 t/s → ~23× to close). The de-GCC work below is Tier-3 MSVC-parity progress (kept, GCC-safe), NOT the CPU build.
**Tier-3 MSVC-parity: engine lib + `sp_toks.exe` now COMPILE + LINK UNDER VS18 (de-GCC committed).** Commits: engine `db84bf3` (SP_TARGET macro / ternlog alignas / persist tail) + core submodule `777a10e` (sp_channel `/experimental:c11atomics`) + `33c6a27` (persist atomics shim). Still GCC-only but NON-BLOCKING (micro-benches off the forward path): `tests/test_avx512_persist.c` (`__ATOMIC_*`), `tests/bench_avx_spinor_sweep.c` (`stream_nt`) — de-GCC later for the full suite; `cmake --build build-cpu --target sp_toks` builds the forward path now. **RUNTIME SEGFAULT — FIXED 2026-06-02 (engine `0fb39ab`).** Root cause = the **fork-tax struct divergence** (cf. `project-arch-struct-divergence`): the engine's `include/sp_engine/model.h` `qwen3_config`/`qwen3_layer`/`qwen3_model` were STALE — missing the gemma4 (`g4_*`) + qwen36 (`q36_*`) fields the core added in the `d8e614f` bump. Since `cfg` is embedded by value, `sizeof(qwen3_config)` differed → `token_embd` (every field after `cfg`) sat at the wrong offset → core's `qwen3_load` wrote it where the engine read NULL → `embed_row` segfaulted. Localized by instrumentation (cfg read fine, `token_embd`=NULL in `embed_row`), NOT the toolchain/de-GCC/harness. **Fix: synced the engine's three structs to core byte-for-byte (+ do-not-diverge note).** `sp_toks` now RUNS. **SPEED_BASELINE MEASURED: Qwen3-0.6B-f16 CPU = 0.84 tok/s** (sp_toks, as-is f16 path) vs llama.cpp 28.2 t/s → **~33× gap = the WIRE-CPU-V2 integer-pipe work (P1).** (Consistent with the WIRE-CPU daemon's ~1.2 t/s.) See `reference-cpu-build-toolchain` memory.


- **WIRE gap:** CPU/CUDA/Vulkan forward shells still call scalar f32 (Hexagon done via HX.3b). The envelope isn't realized until shells call the integer + Spinor-KV primitives.
- **qwen35moe `.sp-model`:** needs the *reducing* OK_Q4 artifact (OK_Q8 was backwards → 35 GB) + `sp_model_to_qwen36` bridge + arena-aware expert path. Forward already gated GGUF-direct (M_QWEN36).
- **engine↔core fork tax:** duplicated forwards / dequant / row_bytes / arch-id enums. "One object" presupposes de-duplication.

---

## 6.1 Disk / storage layout (Knack's host, 2026-06-02)

| Drive | Kind | Role |
|---|---|---|
| **C:** | OS SSD (~50 GB free) | build trees, scratch |
| **D:** | working SSD (~50 GB free) | repos (`D:\F\shannon-prime-repos`), source GGUFs, active `.sp-model` (transcode source+artifact side-by-side, ~40 GB peak — fits) |
| **E: / F:** | Intel Optane (16 / 32 GB) | **reserved for Ring-2 KV offload spill/recall** — near-RAM latency + byte-addressable = the tier that keeps "context beyond RAM" *fast*. A C2/C3 design input, not just storage. |
| **G:** | Google Drive 5 TB (streaming) | cold archive only (backups, superseded artifacts). **Never mmap'd live.** |
| **H:** | external SD 1 TB | bulk cold model storage + transcode overflow |

qwen35moe transcode: source (D:, 19.7 GB) → OK_Q4 `.sp-model` (D:, ~20 GB). No longer blocked.

## 7. Discipline that is working (keep it)

Clean rewrite · bounded crates + frozen seams · contract system (RFC + C1–C6) · per-cell closure docs · oracle-fingerprint validation · honest PROVEN/TARGET tagging · surface-upstream-never-silently-revise-a-gate · separate worktrees for parallel agents · this STATE ledger updated every session. **This is the structure that finally works. Maintain it. Update this file at the end of every session.**
