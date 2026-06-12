# PPT-LAT — PROJECT STATE LEDGER (the proven record)

**This is the authoritative record of what is PROVEN. Read it first. Trust it. Build on it. Do NOT re-derive it.**

> To the next session/agent: this is the **20th rewrite**. Six months of validation live behind these lines. The operator remembers; you don't. **Your default is TRUST.** Each PROVEN line cites its evidence (commit / tag / gate / closure doc). If — and only if — you have a concrete reason to doubt a specific line, the reverify command is given; running it is the exception, not the warm-up. Re-proving the whole stack from scratch *is the failure mode this project has hit 20 times.* Don't.
>
> Status vocabulary: **[PROVEN]** evidence cited · **[WIRED]** built + in-tree, gated · **[DESIGN]** spec'd, unbuilt · **[TARGET]** a number to measure, not yet measured · **[SPECULATIVE]** idea. Promotion requires a gate + an entry here.
>
> **READ FIRST, before any work: `papers/PPT-LAT-Theory.md`** — the canonical theory (the 13-step PPT substitution, O_K/Q(√−163), CRT primes, the frozen Spinor + KSTE formats, theorems T1–T8, production status). Skipping it caused real drift this session (a fresh agent inverted the PPT/Lattice hierarchy AND measured the wrong Spinor primitive — both because the theory wasn't read). It IS in the repo; read it.
> Companion docs: **PPT-LAT-Theory.md** (the math/why — FIRST) · **RFC-001** (north-star preamble) · **PPT-LAT-Systems-v1.md** (the canonical systems narrative — supersedes v0 Systems + the two standalone v0 specs, which are now its Appendices A/B) · the **C1–C6 contracts** (forward work) · per-cell **SESSION-CLOSED-*.md** (closure detail) · the **roadmap** (sequence). This ledger is the *backward* record; the contracts are the *forward* plan; Systems v1 is the *current* synthesis.

Last updated: 2026-06-10.

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

**[MEASURED 2026-06-02, harness `tests/c2_sparse_recall.c`, contract C2.0.4/C2.0.5]** Sparse-recall fidelity vs full attention (needle-in-haystack, N=4096): **ORACLE top-B reproduces full attention at B=64 (cosine 1.0, 8/8 needles)** — so Ring-2 storage *does* become usable context IF the recall router is good. **Query-agnostic SWA/φ capture the recent cluster but miss distant needles (0–1/8)**; pure Fibonacci-φ is the *worst* router (φ is for eviction *coverage*, not peaked-mass recall). **KSTE-signature recall looked best (4–6/8) but ADVERSARIAL test (`tests/c2_kste_router_adv.c`) FALSIFIES it: permuted decoys (same histogram, ~0 dot product) get KSTE tier-0 distance-to-q 937 vs needles' 985 — INDISTINGUISHABLE; the router pulls 21/32 zero-score decoys.** KSTE order-statistics are a histogram (permutation-invariant), dot-product is directional → KSTE is structurally NOT a recall router (the 6/8 was an artifact of needles being the only histogram-distinctive vectors). Recall router MUST be a cheap *directional* score (low-rank/projected dot-product or NTT coarse pre-score); KSTE ruled out (stays valid for dedup/dominance only). Caught by adversarial verification, not theory. **System-1/2 oracle DERIVED:** switch at `Ncrit = min(RAMbudget/pt_f32, ~(W+B)) ≈ 1–4 k tokens` (forced by RAM at tens of k); System-2 quality is bounded by router fidelity → oracle exposes a quality floor (widen B / denser fallback). The recall-router fidelity gap is the open C2 item. **→ SOLVED 2026-06-02 (C2.0.6, `tests/c2_router_proj.c`, core `186aadb`): a ±1 Rademacher random projection (rank-16 = 32 B/token, SMALLER than KSTE 64B) is ORACLE-PERFECT — 8/8 needles, cosine 1.0000, 0 decoys at B=64, where KSTE got 0/8. JL preserves the dot; ±1 keeps it INTEGER/Z_q-native (Lattice-pure, not "dirty float"). Router=±1 projection sidecar, Compressor=Spinor/Tail-Slayer, cleanly separated. Path B (NTT low-freq) unnecessary. Unblocks System-2 usable context.**

---

## 5. TARGET — the envelope (the value; measure, don't assume)

These justify the project and are **not yet measured here**. They are the point. Measuring them is the next phase's job (contracts C1/C2).

| Target | Where measured | Status |
|---|---|---|
| KV compression — TWO overlays (per `PPT-LAT-Theory.md` §3–4, T2, T8.2) | C2 | **[MEASURED 2026-06-02, gate C2_KV_RATIO, harness `tests/c2_kv_measure.c`]** (a) **`sp_spinor_encode_vec`** (faithful, dimension-preserving, 63 B/block, NBLK=⌈HD/55⌉): **asymptotes ~3.5×/f32 but only ~1.0–1.7×/f16, at cosine ≥ 0.99996** (top-1-safe pending real-model confirm). NOT 120× — it is 1 int8/elem + per-block scale (candidate "anchor-basis reconstructs HD≫55" FALSIFIED by linear NBLK scaling). (b) **`sp_kste_encode`** (lossy ⪯_d signature, 64 B regardless of HD): ratio = HD/16 → **the ~130× headline = KSTE at HD≈2048**; discrimination ~1.0 even at scale 65536 (the M.5 i16-clamp does NOT collapse continuous-K discrimination — only token-ID). It is a dedup/routing signature, NOT reconstructable attention KV. **Decisive: neither overlay alone is "120× reconstructable KV" → the headline = faithful ~3.5× × Ring-2 effective-context multiplier. Ring-2 recall (C2_RING2_RECALL) is now the load-bearing unmeasured piece, not the per-vector block.** **REAL-MODEL CONFIRM (C2_KV_DECODE_DETERMINISM, live E_CPU_8 `test_kv_spinor` Qwen3-0.6B scalar, 2026-06-02): Spinor-KV vs f32-KV argmax 29/31, KL mean 2.300e-02 (gate ≤2.0e-1) — PASS as a BOUNDED-DIVERGENCE overlay. HONEST: Spinor-KV is LOSSY (~6.5% argmax flips over 28 layers), NOT bit-exact; the per-vector cosine 0.99996 did NOT carry to 31/31. Bit-exact floor = weight path + gate-OFF, not the Spinor-KV overlay. Gate-OFF == f32 forward bit-identical still holds.** |
| `.sp-model` converter REDUCTION ratio (≤ source; sub-Q4) | C1 | [TARGET] |
| tok/s vs the bar: **beat llama.cpp + old SP hier-KV @ 40 tok/s, Qwen3.6** | P1 SPEED contract; system gate | [TARGET] — **REFERENCE MEASURED 2026-06-02:** llama.cpp Qwen3-0.6B-f16 CPU greedy = **210 t/s prompt / 28.2 t/s gen** (dev host i9-11900KB). f16 decode already bandwidth-bound at 28 t/s → confirms the SP lever is reduced weight-read traffic (packed Q8/Q4), not ALU. **SP-side MEASURED 2026-06-02** (`sp_toks`, after segfault fix `0fb39ab`): f16 **0.84** → Q8 arena **1.58** (1.88×, bandwidth lever) → **Q8+threaded matmul `10.53` (`8975753`) → +threaded attn/per-head `12.55` (`d7735a4`) → +AVX2 int8×f32 dot `39.52` (`5e443c9`, 3.15×) = 47× over the 0.84 f16 baseline.** **FAIR quant-matched scoreboard: SP-Q8 39.52 vs llama.cpp-Q8_0 52.8 → SP ~0.75× (llama.cpp ~1.34× faster); SP-Q8 beats llama.cpp-f16 (28.2) but that's not apples-to-apples.** From ~33× behind to ~1.34× behind on the fair fight — competitive, not yet winning. **VNNI int8×int8 TESTED (gated SP_VNNI=1, engine `a2ad1dc`) — DOCUMENTED NEGATIVE:** only **+9%** (43.95 vs 40.38) AND **top-1 gate FAILS** (divergent tokens). Falsifies the "ALU gap" hypothesis: **Q8 decode is BANDWIDTH-bound** (VNNI reads the same int8 weight bytes as AVX2; 4× ALU barely helps), and naive per-vector int8 act-quant is too lossy (needs per-channel/SmoothQuant). **AVX2-f32 dot (40 t/s, accurate, parity-safe) stays the production CPU kernel.** The ~1.34× gap to llama.cpp-Q8 is **memory layout/bandwidth (Q8_0 32-elem blocks / fewer passes), NOT ALU** — that's the real follow-up. Threading + AVX2 parity-safe (oracle=SP_CPU_SCALAR). **The speed thesis is validated: SP within ~2.7× of llama.cpp on 0.6B from packed-Q8 + threading, no SIMD yet.** See `CONTRACT-SPEED` SPEED_WIRE_CPU ladder. |
| Ring-2 disk offload + recall cost + **effective-context multiplier** | C2/C3 | **[MEASURED 2026-06-02, gate C2_RING2_RECALL PASS, harness `tests/c2_ring2_measure.c`]** spill→recall byte-identical (2000/2000); recall ~10 µs/token + ~2 µs/block decode (page-cached) ≪ recompute (no weights/matmul). **Effective-context multiplier = (RAM_window+Optane)/RAM_window: ~400× @16 GB, ~794× @32 GB, ~1190× @48 GB at a 512-token window → the "~120×/unlimited context" headline is CONSERVATIVE and lives HERE (candidate #2), not in the per-vector codec.** Scope limit: solves the memory wall, NOT the compute wall — usable context needs a sparse/recalled-attention pattern (SWA / Fibonacci φ sub-sampling / retrieval); re-measure on real Optane. |
| Dual-GPU / multi-device residue-sharing (ship residues, not tensors) | C3 + Trick #1 | [TARGET] |
| int-end-to-end (no per-matmul fp dequant; only logits) | WIRE-* + C2 | [DESIGN] |

---

## 5.05 C2.1 COMPLETE (2026-06-03) — two-ring recall wired live, all three walls down

C2.1 wired the C2 measurements into the live `qwen3_generate_kv` decode path and drove the three walls down, each gated on an N=512 NIAH parity gauntlet (GEN_KV bit-parity + real `837492`-needle HIT). Engine commits `67f4997`→`f8ea920`; full record in **CONTRACT-C2 §C2.1**.

- **Router (Step 1, `67f4997`):** ±1 Rademacher projection sidecar, recall-set = sinks ∪ top-(B−W−sink) ∪ recent-W; parity-exact when off / B≥ctx.
- **G1 NIAH (`7055964`, `tests/niah.c`):** decode-path needle gate. r=32 holds 2×/4×/**8×** at N=2k; depth 10/50/90 all HIT (**no recency bias**). Budget B is *absolute* → achievable ratio grows with context.
- **G2 PPL (`d56c1a7`+`e916365`):** autoregressive decode-path PPL. v1 FAILED (4× +40%, 8× +104% — dropped softmax tail + attention sinks). **Fix = Möbius-pinned sinks (`SP_RECALL_SINK=4`).** v2 N=2k: 2× −0.71%, 4× −0.92%, 8× +0.69% — all <2%. **Intelligence wall solved @8×.**
- **Step 2b Optane (`2707f60`/`fdc0f07`/`e895ef4`, `ring2_disk.c`):** NO_BUFFERING + IOCP async. Latency v0 48.7 → v1a 18.9 (dedupe) → v1b **7.57 µs/read** (≈ media floor). NIAH HIT off F: Optane.
- **Compute wall (`b7a1f92`):** O(B·N) max-extract → **O(N) quickselect** (the ~10-h-at-32k bottleneck removed).
- **Memory wall (`f8ea920`):** Ring-1 `kc/vc` → **(sink+W) ring buffer** when offloading. N=512 15× shrink; **32k = 910× (7.5 GB → 8.3 MB)**.

**Honest RAM floor @32k:** Ring-1 = 8.3 MB but the `projk` ±1 router index stays full-P ≈ 940 MB → net 7.5 GB → **~950 MB (~8×), projk-dominated**; int8/int4 router-index quant is the next optimization (owned, not hidden).

## 5.055 C2.1 prefill/decode modes + fusion + release prep (2026-06-03)

Three decode modes now exist, all parity-exact when off, additive/gated (proven paths untouched):

- **Streaming** (default): recall during prefill, always-low-RAM (Ring-1 = sink+W throughout). O(B·N) prefill. This is the 32k headline path.
- **Decode-only** (`SP_RECALL_DECODE_ONLY`, engine `a5e9b86`): dense-exact prefill in RAM, recall engages only at decode (pos ≥ n_prompt). Trades peak-RAM-during-ingest for fast exact ingest.
- **Fusion / compact-and-spill** (`SP_RECALL_FUSE`, engine `7896bc4`): dense-exact prefill in a full-P RAM buffer, then ONE bulk spill of the cold tail to Optane at the prefill→decode boundary + copy sinks/window into the (sink+W) cache + **free the prefill buffer** → window-sized decode RAM with exact ingest. **Verified N=512** (boundary fired, needle off disk) **and timed N=8192** (51.4 min wall, 1.88 GB buffer freed, HIT `837492`, 10.62 µs/read). Upgrades paper-01 §3.7 future-work → result.

**Honest cost note:** fusion prefill is exact O(N²) attention (recall off during ingest), so 32k dense-exact is ~18 h on one f16 core — the stock cost of exact attention, not a fusion defect, consistent with the ~1.34× throughput gap. The 32k *headline* therefore runs on the streaming path (always-low-RAM, O(B·N)); fusion's receipt is the 512 + 8k runs. **R9 (streaming 32k) in flight** — drop its retrieval/read-count/latency/wall-clock into paper-01 §4 + abstract + EXPECTED.md + landing hero on completion.

**Release prep (publishing track):** paper-02 repro **green** — 6/6 E_FMT gates, L1 reducing (Qwen3-0.6B-f16 1,439.4 → 719.6 MB, 50.0%), L4 bit-faithful forward on gemma-3 + qwen3, captured in `EXPECTED.md`. **License = MIT** (wired through LICENSE / CITATION.cff / README / site). Release staging assembled in `comms/release/` (papers 01–02, site, ledger); **`shannon-prime-papers` repo set up** for the papers series. Public remote URL + first release tag deferred (operator deciding).

## 5.06 C2.2 COMPLETE (2026-06-04) — canonical two-ring + NTT fusion + the network tier

The day the discrete object closed at every scale. Full record in **CONTRACT-C2 §C2.2**; math-core `9c26475→54ee28b`, engine `005473d→57c9a53`, suite 21/21.

- **[PROVEN] ARM in math-core.** `core/arm/` + the abstract Ring-2 backend **in the L1 ABI** (`sp_arm_ring2_register`; registered = borrowed). The full two-ring decode lives in `core/forward/decode.c` — **the only decode in the tree** (engine duplicate ~430 lines incinerated; engine resolves the canonical decode at engine speed via the `cpu_overlay.c` dispatch seam: 22.62 tok/s). Run-gates `T_ARM_GENKV` (11 gates incl. counting-backend registration proof). Reverify: `ctest -R T_ARM`.
- **[PROVEN] Dual-prime NTT keystore fusion.** `SP_NTT_KV`: K cached write-once as the dual-prime residue block; score = residue dot + Garner = exact ⟨q,k⟩, **no inverse butterflies**. Bluestein keystore (empirical coefficient-0 weights folded into the key) covers every pow-2 HD ≤ 256 — the HD=8 fixture runs fusion natively in-tree. `sp_pr_resdot` deferred reduction (15 u64 products per mod) + engine **AVX2 Barrett-SIMD override: fusion 15.68 → 18.35 tok/s (84% of the 22.6 f32 baseline), sequences bit-identical.** Residual −16% = per-token q-transforms (448 fwd NTT pairs + 224 K-encodes) — the named next lever.
- **[PROVEN] Optane tier, dual block size.** Two NO_BUFFERING+IOCP stores (8192 B K-residue / 4096 B V-f32) registered through the L1 hook. **Live F: run: 16.25 tok/s, sequence identical** — inherits the C2.1 7.57 µs/read queue-depth floor.
- **[PROVEN] Network tier — Trick #8 closed.** QUIC peer as `sp_arm_ring2_backend` (`M_NET_RING2`), then the **two-process showpiece** (`sp_ring2_showpiece` + `SP_RING2_SERVE`): **20,160 KB of raw untranslated u32 residue payload (840 writes + 2520 reads, 504 batched flights) over 127.0.0.1 mid-decode, zero serialization/fp translation, SEQUENCE IDENTICAL to baseline (1.46 vs 1.48 tok/s — transport absorbed by compute).** Caveat: loopback; cross-host pending.
- **[PROVEN, honest-negative corrected] MTP T8** (CONTRACT-C4-C5-C6): KV-reuse verify machinery bit-identical; the 1.76× was a degenerate-prompt artifact — real prose/code prompts 0.87× with prompt-lookup drafting; needs a real draft source. The rollback substrate stands.

**Composed claim, now run-gated end-to-end: compute operand = cache line (Ring-1, 910× @32k) = disk block (Optane, 7.57 µs floor) = wire packet (QUIC loopback, 20.16 MB) — one dual-prime residue object, byte-exact at every boundary.**

- **[PROVEN, regime-bounded] Bit-packed popcount router (C2.3, same day).** `SP_RECALL_BITS`: projk sidecar → one u64 of projection signs per (pos,kvh) (**~940 MB r=32-float → ~59 MB @32k, 16×; 32× vs the r=64-float equivalent** — an earlier revision said "~29 MB/32×", corrected: 940/16 = 58.7 MB; the decode banner prints actuals), scoring = popcount XOR. NIAH gate: **r=32 passes 2× all depths (d50 answer identical to f32) but MISSES 4×/d90 where f32 HITs — honest SimHash resolution loss; r=64 (same 8 bytes) restores full fidelity 6/6.** Production: `SP_RECALL_BITS=1 SP_RECALL_R=64`. Named remaining gate before default-on: PPL deflection at bits-r=64. CONTRACT-C2 §C2.3; math-core `92c07fe`, engine `3d2d2c3`.
- **[PROVEN] q-transform SoA head-batch (same day).** `sp_ntt_fwd_batch` seam + AVX2 lanes=heads override: fusion **18.35 → 22.3 tok/s (gap to f32 16% → ~7%)**, fusion×rings×backend 16.08 → 20.14, sequences identical; T_PR_BATCH bit-exact. math-core `f7b9b6d`, engine `144d445`. The NTT compute-optimization arc is CLOSED — residual ~7% buys the whole discrete envelope.

## 5.07 THE STAGE TAXONOMY (operator-minted 2026-06-04) — the heterogeneous deployment ladder

Canonical names for the physical deployment tiers. Each stage is a strict optimization target for the compiler/router/orchestrator; a stage is claimed only when its composed run-gate exists (the Alpha discipline).

| Stage | Substrate | Status |
|---|---|---|
| **Alpha** | CPU / RAM / Optane (Beast Canyon) | **PROVEN-in-parts; composed 32k finale COMPLETED 2026-06-06 — NIAH verdict MISS** (infrastructure proven at 16.3 h scale; retrieval quality at 64× budget not — see §5.11 + CONTRACT-C2 §C2.4-CLOSURE) — context machinery cache-adjacent (~82 MB @32k), Optane = active memory tier, weights remain the DDR bandwidth budget |
| **Beta** | RTX 2060 12GB (pure VRAM) | NEXT after Alpha closeout. SoA lanes→warps; model+context <6% of VRAM; **sm_75 constraints pinned**: no cp.async/ldmatrix/mbarrier, single INT32 ALU port (see reference-cuda-sm-feature-tiers), and **mul.wide/mad.wide.u32 are BANNED** (nvcc paired-register miscompile, reference-nvcc-paired-register-bug — decompose to mul.lo/mul.hi + add.cc, anchor ptx_ntt.cuh) |
| **Gamma** | RTX 2060 + Optane | beyond-VRAM contexts/models: cold tail DMA'd across PCIe; Optane stays load-bearing for MUCH larger models even with the GPU present |
| **Delta** | CPU + RAM + Optane + RTX 2060 as ONE engine | asymmetric split: CPU owns the O(N) popcount routing scan + Optane I/O; GPU owns the O(B) residue inner products; pinned-memory (cudaHostAlloc) DMA keeps the QUIC zero-serialization packet intact across PCIe |
| **Epsilon** | Snapdragon DSP/SVM/ARM/ISP/NPU/UFS (S22U) | UMA frontier — groundwork live (Mode-D FastRPC, V69 HVX, QNN NPU Unsigned PD, Tricks #1-#10) |
| **Zeta** | Alpha–Delta + Epsilon as one system | the QUIC mesh as nervous system: the byte on the Optane platter == the byte scored in VTCM, no translation anywhere |
| **Eta** | Gemma 4 — the Native Sensory Lattice (encoder-free multimodal ingest) | RUNWAY CLEAR: `gemma-4-12b-it-Q4_K_M.gguf` on disk; ingest = ONE OK_Q4 matmul per modality (48×48 patches / 640-float 40ms audio frames), so pixels and sound enter the discrete pipeline at the sensor boundary; same 3-G4 port spine (oracle → bridge → transcode → top-1/PPL); MTP drafters = standalone checkpoints (the T8 draft source); embedding-layer audio round-trip (overcomplete 640→E injective projection ⇒ exact-then-pseudoinverse recovery) gets an SNR gate — "the cache is the audio file," claimed only at the embedding layer, never the K layer |
| **Omicron ο** | Intel GNA 2.0 — the small-o coprocessor (NUC11 on-die) | PROBE QUEUED: the always-on milliwatt integer affine engine (int16/int8 MAC, int32 accum, EXACT in range, 64-byte-aligned DMA — already our ABI). Named for little-o: the lower-order term that never dominates but never sleeps, and Ptolemy's ο-as-zero — the placeholder that holds the cell while the system idles. Ladder of ambition (each gated by Stage-0 read of the archived LGPL kernel source + die probe, NEVER by "designed for" copy): (1) wake-gate VAD, (2) the entire Gemma-4 audio embedder as a native affine layer, (3) the ±1 Rademacher router projection (SimHash minted off-core), (speculative) small-prime CRT-NTT in int16 lanes |
| **Kairos καιρός** | the sp-kernel — escape from turn-based execution (the time/agency axis) | [DESIGN — registered 2026-06-10; opens AFTER P2.b/P3 close] hierarchical tick (GNA→router→Exec), latent interrupts (the X-R1 mechanism as delivery path), eos→yield + gated NIGHTSHIFT idle loop, drivers (ears/HA/TTS), registry+permissions, receipted flywheel. Own doc set: `ROADMAP-KAIROS.md` + `CONTRACT-KAIROS-*.md` (kept separate to not pollute the live campaign). Reference corpus: CosySim/NEXUS/Project X (KAI-0 extraction first-pass done) |
| **Holon ⬢⃝** | the bonded whole | the Universal Discrete Architecture, one Garner formula from L1 cache line to QUIC packet (Trick #8 closed the wire; #9 the ABI; #10 the receipts). The space/distribution axis — composes with (does not absorb) Kairos |

## 5.08 STAGE ALPHA CLOSED + STAGE BETA OPENED ON THE GPU (2026-06-05/06)

**STAGE ALPHA (CPU/RAM/Optane) — the C2 envelope is closed-in-parts; the composed 32k gate is deliberately deferred behind the amplification fix.** Full detail in CONTRACT-C2 §C2.2/C2.3/C2.4 + CONTRACT-SPEED. The day's arc:
- **C2.2** canonical two-ring in math-core + dual-prime NTT fusion (18.35 tok/s, 84% of f32, bit-identical) + Optane dual-size + QUIC peer + two-process showpiece (20.16 MB raw residues over loopback, sequence identical). math-core `9c26475→54ee28b`, engine `005473d→57c9a53`.
- **q-transform SoA head-batch** (math-core `f7b9b6d`, engine `144d445`): fusion 18.35→22.3 tok/s, gap to f32 16%→7%; T_PR_BATCH bit-exact. **NTT compute-optimization arc CLOSED.**
- **C2.3 bit-packed popcount router** (math-core `92c07fe`, engine `3d2d2c3`): projk → 1 u64/(pos,kvh) (16× @r32). **Both named gates GREEN: NIAH 6/6 + PPL transparent (−0.97%/−0.12%) at ≤4×; FAILS 8× (+6.08% vs f32 +0.69%). Production: `SP_RECALL_BITS=1 R=64` ≤4×.**
- **Amplification bundle** (`2441e0b`/`9cd502f` + `200c0ec`/`2484650`/`16e15e3`): KVSEL group-centroid kv-head selection (NIAH 3/3 @4× incl d90; PPL −0.92%, beats per-Q-head), split-device Optane (K→F: CPU-slot / V→E: PCH), `read_batch2` device-overlap ABI (the serialization-tax fix: serial split 4u/S WORSE than single-device 3u/S; overlapped 2u/S), bounded LRU temporal staging cache (T_CACHE_EXACT bit-identical).
- **THE TEMPORAL-LOCALITY FINDING (novel):** adjacent decode steps' recall sets DRIFT slowly — measured ~9.46 TB Optane reads to serve ~3 GB unique blocks at 32k; the 2 GB LRU cache absorbs 86%→42% as the reuse-window union outgrows it with depth (full curve mapped). The router's working set glides; the cache surfs it. CONTRACT-SPEED.
- **C2.4 composed 32k finale: TERMINATED at 44.7%, gate PENDING — NOT claimed.** Four versions chased four real walls (v2 scan, v3 split, v4 overlap, v5 cache); each shipped+gated, but the single composed log was never banked. **DECISION (operator, economic): v5 is terminal; the 4 GB-slab scaling is documented-not-run; no more finale relaunches.** Partial run proved indestructibility (8.6 h saturated, RAM flat, zero leak). The composed gate closes when re-run cheaply post-amplification — not load-bearing for the rest of the project. *(Outcome: v5 completed 2026-06-06 — verdict MISS; see §5.11.)*

**STAGE BETA (RTX 2060 12GB, Turing sm_75) — OPENED + GPU GENERATION LIVE (2026-06-06).** Full detail in Roadmap §21 + SESSION-CLOSED-stage-beta-s0.md.
- **Stage 0 verified ON THE CARD:** CUDA 13.2 still targets compute_75; build-cuda clean (48/48). CUDA_SMOKE + E_CU_5 NTT-attention (KL 2.4e-10) + E_CU_6 KSTE all PASS. The discrete dual-prime poly-ring attention reproduces math-core scalar to fp noise on Turing.
- **Prefill forward gated:** M_GEMMA3_CUDA PASS; M_QWEN3_CUDA functionally PASS on f32 + Q8 (argmax 31/31, KL ~1e-11 — the ship precisions); fp16 sub-gate fails the f32-parity threshold (precision floor, GPU twin of E_CPU_8 — decision owed).
- **GPU autoregressive KV-cache DECODE built + gated** (engine `3b6831c`): `qwen3_decode_cuda` (k_rope_at position-aware RoPE + k_attn_decode single-query + k_argmax device reduction, KV resident in VRAM, zero per-step host sync). M_QWEN3_DECODE_CUDA = GPU decode == GPU prefill teacher-forced, 5/5.
- **Speed pass 1** (engine `1af7c9a`): f32 6.93 → **Q8 11.97 tok/s (1.7×).** Honest wall = **kernel-launch overhead** (~250 launches/token at 0.6B); device-argmax barely moved f32 (sync wasn't the wall). NEXT = CUDA graphs → fused kernels → discrete router on GPU (shared-mem-staged, NO L2 pin on Turing) → llama.cpp head-to-head. Then Stage Gamma (pinned-mem Optane→VRAM, consumer Turing has no GPUDirect Storage).

## 5.09 STAGE BETA SPEED CLOSED-IN-PARTS + STAGE ETA OPENED (2026-06-06)

**The Speed-pass-1 numbers above (6.93/11.97) were COLD-START artifacts** — corrected in this session. Full detail in CONTRACT-SPEED §BETA.2/3a/v3/v4 + SESSION-CLOSED-stage-beta-speed.md. The arc, all gated bit-exact / top-1-lossless on the actual RTX 2060:

- **BETA.2 — CUDA graphs.** Position-indirect decode kernels (device-scalar `int *dpos`) make the per-token launch sequence capturable; capture once, replay/token. First commit claimed `7.24→91.55, 12.65×` — **wrong** (per-step ran cold, graph ran warm). Anchored (warm + `n_gen=256` + both clocks pinned): graphs are **~1.06×**. Launch overhead was never the wall — **cold-start was** (CUDA lazy module load + cuBLAS JIT ≈ 13× first-call; a persistent warm daemon captures it).
- **BETA.3 — the INT8/Q4 dp4a bandwidth ladder.** Fused dp4a GEMV reads packed Q8/Q4 arena codes straight from VRAM (no f32 scratch); warp-per-row + 128-bit `int4` loads + shuffle reduction; **per-tensor precision dispatch** (`DevTensor.prec`) handles K-quant mixes (Q8 head + Q4 body). **Isolated GEMV sweep** (`tests/bench_gemv_int8.cu`, both clocks pinned): **f32 1× (~290 GB/s = 86% of the 2060's 336 GB/s peak, bus-saturated) → int8 ~3.8× → Q4 ~7.06×** at 12B-scale dims, hugging the byte ratio (4:1 / 8:1). Q4 correctness vs host ref: **1.34e-7**. At 0.6B/full-clock the decode is **overhead-bound** (~91 tok/s, all precisions converge); the win binds only at large-model scale.
- **Production wiring + gate.** Q4-dp4a wired into `qwen3_decode_cuda` (the K-quant-mix bug — Q8 head misread as Q4 → 0/256 — caught by the production gate, fixed via per-tensor precision). `M_QWEN3_DECODE_CUDA` = **28/28**: f32/Q8/Q4/.sp-model all 256/256 top-1 lossless.
- **`.sp-model` adapter fix** (engine `2138f89`): `sp_model_to_qwen3`/`qwen25` now honor the arch_struct **growth discipline** (min-copy of `min(arch_struct_size, sizeof)`, zero-fill the appended tail) per PPT-LAT-SP-MODEL-v0 §3 — older artifacts (e.g. `arch_struct_size=56` = base+FP16) now load instead of being hard-rejected.
- **METHODOLOGY (now standing discipline):** no GPU tok/s number without warmup + long window + **both clocks pinned** (`-lgc` locks SM only; a weight-GEMV is memory-bound → GDDR6 clock must be at full speed); confirm the kernel sits on the binding bottleneck (Amdahl); isolated benches validate kernel MATH, production gates validate the DATA-STRUCTURE handoff. See `feedback-gpu-microbench-methodology`.

**STAGE ETA OPENED (2026-06-06, branch `stage-eta-gemma4-cuda`).** Gemma4 (MatFormer/Gemma-3n E-series: AltUp + shared-KV + per-layer geometry + softcap) CUDA forward+decode, so the 6.6 GB Gemma-4-12B-Q4_K_M runs on the 2060 with the ~7× Q4 win. CPU `core/forward/gemma4.c` is the bit-exact oracle; gate target = `gemma-4-E4B`. Reference read + 6-stage gated plan (ETA.1–5) banked. **Do not rush the variable-geometry port; resume at ETA.1 (adapter + weightless V-norm).** Detail in Roadmap §21/§19 + memory `project-stage-eta-gemma4-cuda`.

## 5.10 STAGE ETA PHASE 1 CLOSED — THE GEMMA4 CUDA ENGINE (2026-06-06)

**The full Gemma 4 (MatFormer E-series) architecture runs on the RTX 2060 — forward AND autoregressive decode — gated 38/38 against the CPU oracle, both live runs green FIRST TRY.** Full receipt in SESSION-CLOSED-stage-eta-phase1.md; engine merged to main at `559435c`; Roadmap §19.

- **`gemma4_forward_cuda`**: 35 layers of per-layer GLOBAL/SWA geometry + shared-KV (15 owners/20 sharers) + proportional rope_freqs + weightless V-norm + elastic FFN + AltUp + out_scale + tied head + softcap → **argmax 12/12, max KL 2.663e-10** vs `gemma4_forward`. Distributional identity at machine-noise level.
- **`gemma4_decode_cuda`**: autoregressive greedy over a **JAGGED shared-KV cache** (per-owner [P×kvd_L]; sharers allocate nothing), per-step AltUp, windowed single-query attention → **the oracle teacher-forced-predicts every generated token.**
- **Why first-try:** the bisection bulkheads. Weight-ingest gate (8/8, incl. the cross-seam link — the fork tax collapsed to ONE `as_f32→sp_as_f32` shim), L0 math lock (+ the inline-Frobenius-lift finding: `gemm_w_lift` enforces the oracle's exact-integer-accumulate arithmetic on cuBLAS; + the ×25 norm-amplification analysis), L4 geometry-shift breach (rope_freqs handoff at the floor), L15 sharer-seam proof (cross-layer VRAM addressing exact at 1.1e-5). The monolith had nowhere left to fail.
- **Numerical findings banked:** the RMSNorm re-condenses amplified noise at each layer entry (self-healing over depth, no explosion through 16 layers); sharer attention is CLEANER than native (inherited normalized K/V + softmax squashing); ABS error is the gate currency at norm boundaries (rel inflates on near-zeros).
- **NEXT — ETA.5b, the velocity pass (pure physics, gated top-1):** device-side PLE gather (sever the per-step host sync) → CUDA-graph capture of the jagged topology → Q4-dp4a routing (the proven ~7× byte diet) → **12B-Q4_K_M transcode + load + tok/s vs llama.cpp.** The architecture is proven; what remains is the speedometer.

## 5.11 C2.4 CLOSED ON AN HONEST NEGATIVE — THE v5 FINALE VERDICT IS **MISS** (2026-06-06)

**The composed 32k Optane finale COMPLETED** (`FINALEDONE`, 58,674 s = 16.3 h, zero errors) **and the needle was not retrieved** (`837492` absent; the answer parroted the needle's context word "Optane" but generic digits). Full disposition: CONTRACT-C2 §C2.4-CLOSURE.

- **Infrastructure: PROVEN at full scale.** 1.353B device reads/stream (K 11.1 TB, V 5.5 TB) at 19.55/19.58 µs/read at queue depth; 2 GB LRU absorbed **67.0%** on both streams; Ring-1 482×; NTT fusion exact for the whole run; clean teardown. The storage thesis stands.
- **Config regression exposed (no spin):** v5 ran the **f32 r=16 router** — `SP_RECALL_BITS/R=64` were dropped from the runner at v4 and never restored, and `SP_RECALL_KVSEL` was never set in ANY finale script. The script's "KVSEL + bits-r64" header was prose, not config; niah's knob-echo (`r=16 B=512`) caught it. Also why 16.3 h, not ~2–3 h. **Lesson: banners must echo `getenv`, never aspiration.**
- **Regime honesty:** B=512 @ 32k = **64× selection** — all quality gates were at 2×–8× (N=2048). And there is **no full-attention 32k control** for Qwen3-0.6B, so router-dilution vs model-ceiling is not yet separable.
- **Disposition:** closed AS A MISS per the standing operator decision; NO Optane relaunch. A RAM-only NIAH ladder (N=2k/4k/8k/16k, B=512, mock RAM Ring-2 — minutes/rung) localizes the break point on the budget axis. **Paper 01 releases on the 512-position-proven claims; the public README's pre-claimed 32k HIT was corrected same-day.**

## 5.13 THE GEMMA-4 CAMPAIGN CLOSED — SOVEREIGN PIPELINE + CITABLE 06-R10 (2026-06-08)

The ETA.5b anchor (§5.12 below) detonated, and the campaign that followed closed
the whole arc in two days. Full record: CONTRACT-SPEED (GOLD INSTRUMENT addendum
→ RESOLUTION → Q4B SPEC + decision matrix → CLOSED GREEN); receipts lattice
`tests/gemma4_gold/`; public LEDGER 06-R8/R9/R10 + papers 04/05/06 (written).

- **THE GOLD INSTRUMENT:** a from-scratch reference forward off the official
  safetensors measured gemma-4-12B's TRUE wikitext PPL at **4.6776** — llama.cpp's
  397–506 was the ARTIFACTS, not the engine (same arithmetic over GGUF-dequantized
  tensors reproduces the breakage: pre-fix 271–364, post-June-5 rebuilt still
  192.9). Forensics: no permutation, in-place period-6 damage, layer_output_scale
  class independently defective (scalar swap 364→97). GGUF lane DEAD for this model.
- **SAFETENSORS DIRECT (the sovereign pipeline):** `sp_transcode --st` takes weight
  values from the checkpoint (GGUF = verified-clean metadata/tokenizer only;
  mapped-but-missing = hard error). OK_Q8 artifact: **4.7396 (+1.33%)**.
- **OK_Q4B (arena layout v2, formal migration):** per-32-block f16 scales,
  store-then-derive; recipe **B1** (Q4B gate/up + Q8 rest, chosen from a 6-recipe
  SIMULATION matrix — gemma4 is PTQ-hostile, all-sym-32 = +45%) → 9.4 GB artifact
  at **5.1259 = the simulation to four decimals**; GPU kernel `k_gemv_q4b_dp4a_v2`
  (one weight block per 128-bit chunk) landed **5.1160** — triple-instrument
  agreement. Core `85aadd3`, engine `bea361e`.
- **SHOOTOUT-2 (CITABLE, 06-R10):** **26.1 tok/s at PPL 5.12 on the 2060-12GB**
  (graph EXACT 256/256, dp4a top-1 256/256, 24/24). llama.cpp: 31.29 tok/s at PPL
  192–506. Engine bandwidth 245 vs 207 GB/s (+18%). §5.12's 34.2 is formally
  RETIRED with its quality-failed per-row artifact — the series' own anchor rule
  caught it. Community deliverables: public `GEMMA4-QUANT-FIX.md` + issue post.
- **Open from the campaign:** gemma4 tokenizer dispatch (SPEC written), B2 asym
  upgrade, in-engine CPU 12B PPL gate behind harness fixes (progress prints +
  score-only-positions; the serial oracle was killed undetermined at 331 min).

## 5.14 XBAR — THE AUDITABLE LATENT CROSSBAR (RFC v1.1; P1 CITABLE · P2.b CLOSED · P3 READ-PATH COMPLETE — P3.1/P3.1b-1/P3.1b-2 all BIT-EXACT on the 12B · P3.2 WRITE-PATH: spill BYTE-EXACT (G-P3-R2.a) + paged-read BIT-EXACT (G-P3-R2.b-1, history off disk + live source POISONED) + SWA RING SHRINK BIT-EXACT (G-P3-R2.b-2a, FIRST REAL VRAM WIN — 40/48 layers, dominant kvd, ring==full-cache diffs=0)) (2026-06-09; refreshed 2026-06-12)

The post-gemma4 campaign: a token-free inter-model memory architecture — Exec + a small Memo curator sharing the cyclotomic rings, every write receipted/gated/rewindable. Docs: `RFC-XBAR-auditable-latent-crossbar.md` (v1.1) + `CONTRACT-XBAR-P1/P2/P2b/C1-lite`. **[PROVEN/CITABLE]** and **[WIRED]** items:

- **[PROVEN — ledger X-R1, public]** **P1 Inception Probe**: a 12B's generation is steered by **direct KV-cache transplant, no tokens** — 15/15 (5×3 matrix) lexical incorporation, 15/15 selectivity (double dissociation), max **3.69 orders** rank pull, dose-response (1 row ~4% attn mass bends ranks; 6 contiguous rows bend words), G0 null bit-identical 7/7, dual-metric coherence (gold-instrument PPL 1.70–4.10). Engine: `SP_XBAR_*` knobs in `cuda_forward.cu` (capture/splice/emb/rank), `tests/test_xbar_p1_cuda.c`. Ledger row X-R1 in Position_Is_Arithmetic.
- **[PROVEN — measured, internal]** **P2.b Phase 0 (cloud inversion, RunPod A6000)**: k=2 pseudo-tokens recover a 6-token span on the real bf16 12B — **existence proven in two regimes**; kl-dropped-weighted Pareto: **Arm F (free) ~94–96% gap-closed but off-manifold (~17–25), Arm H (hull) ~64–73% on-manifold (~0.8).** Operating point = a P2.b training-time λ-selection (recall-invariant primary), NOT a parity test — the free-generation parity gate was convicted as unusable (greedy decode loops on this it-model in every regime; honest negative banked).
- **[WIRED — gated]** **C1-lite curator** (the local immune system, qwen3 CPU two-ring): **C1L.1** transactional core (`tools/curator/curator_core.c`: clone/gate/atomic-promote/rewind/receipts, G-C1L-1 null PASS) + **C1L.0a** episode persistence + router re-projection determinism (`tools/curator/curator_replay.c` links real `arm.c`/`arm_scan.c`; `projk` recovered bit-identically from the persisted K store — no projk serialization needed). Episode format `{k.bin, manifest}` = NIGHTSHIFT's standard.
- **[DESIGN]** **Ring 3** (RFC §3.1): a four-tier hierarchy — Ring1 working / Ring2 verbatim episodic (**hippocampus**) / Ring2′ transient shadow / Ring3 adapter-compressed consolidated (**neocortex**); NIGHTSHIFT transfer-and-transform under the **irreversible-aware G-R3-LOSS** gate; resolves the C2.4 64× recall ceiling. RFC §6.1 (verified external work — AI Harness Engineering / RHO, with the PPL-delta-over-self-preference sharpening) + §6.2 (latent-vs-lexical threat-landscape note).
- **[PROVEN — 2026-06-09, tag `xbar-c1-lite-complete`] C1-lite COMPLETE** *(supersedes the C1L.0b "NEXT" that stood here)*: C1L.0a re-projection + C1L.0b replay (`SP_REPLAY` seam in `decode.c`, off-path bit-exact; `T_GENKV_REPLAY_NULL` 34/34) + C1L.1 transaction + C1L.2 cold-evict (`T_GENKV_COLD_EVICT` 45/45 — lossless cold-evict PROMOTES, hot-evict diverges and REWINDS). The curator's transactional control flow + episode replay proven on the uniform-geometry qwen3 ring. P3 pre-flight audit (CONTRACT-C1-lite §3b, line-cited against `gemma4.c`): TWO real port gaps — **G-P3-GEOM** (per-layer-class NKV/HD; `decode.c:317` allocates `projk` on a single uniform HD) + **G-P3-SHARED** (shared-KV owner-indirect spill/recall); episode byte layout + `SP_REPLAY` seam transfer as-is; the V-less alarm was a false read (SP projects V independently).
- **[MEASURED — 2026-06-09] P2.b Fork-2: the recall invariant WORKS, 3-seed reproducible.** Adding the through-model readback-CE term (`+λ_read·L_readback`) flipped held-out span recall from chance (§3g: 58/100) to **80–84/100 final on all 3 seeds** with recovery held (~0.18) — clean causal attribution; the loss must be computed at the END of the forward. λ_read sweep: usable band **[0.25, 0.5]**, knee 0.5 (n=1, unconfirmed vs the 3-seed 0.25 anchor). **Fork-1 k-sweep DONE (2026-06-09): verdict ADAPTER-LIMITED** — the k=6 no-compression control did NOT lift recovery (0.155 best / 0.191 final ≈ the k≥2 plateau; both pre-stated predictions hit, incl. the ~60/100 recall endpoint); dilution monotone over the full curve (recall 88→84→72→70→60 for k=1→6). **k=2 = the operating knee (dominates all k≥3 on both axes; the only 3-seed point); the recovery lever is adapter capacity/data, NOT k** (CONTRACT-P2b §3i verdict).
- **[WIRED — SW-emu proven; HW bring-up unblocked] GNA 2.0 audio lane** (RFC-XBAR §3.2): Stage 0–2 probes on real linked libGNA pin the envelope — FiLM = native ElementWiseAffine (accepted to N=32768; ~65k element cap), device memory ≈224 MB usable, 1D conv is the 2.0-native primitive (i16 conv weights, batch=1, single in-channel), i8/i16 + i32 accum (OK_Q4/Q8 maps as a storage codec). **Bring-up kit staged locally** (`archive/notes_and_stuff/GNA/`): Windows + Linux drivers, wsj_dnn5b / rm_lstm4f / librispeech_s5 (incl. OpenVINO IR) reference models, aclnet int8 ONNX audio-CNN exemplar (`rm_cnn4a_smbr` absent — aclnet is the local conv-layout candidate).
- **[MEASURED — 2026-06-10] CAPACITY ARM: verdict NOT-CAPACITY.** 12-receipt grid (4 configs ×3 seeds): all recovery medians inside the baseline noise band (0.145–0.168 vs 0.148±0.034); 4.4× params bought zero recovery AND degraded recall (84→68 at 49.9M; overfit signature exactly as pre-named). The ~0.18 plateau is **data/objective-limited**. λ-leg resolved too: λ=0.5's edge was seed luck (one final-epoch collapse); **OPERATING POINT PINNED: k=2, λ_read=0.25, d512/L2 11.3M — the smallest config is Pareto-optimal on both axes** (CONTRACT-P2b §3j verdict). NIGHTSHIFT inherits a high-selectivity (80–84/100), bounded-loss substrate; G-R3-LOSS governs.
- **[CLOSED 2026-06-12] P2.b CAMPAIGN + P3.1/P3.1b GREEN.** Diagnostic arms all converged: not-capacity (§3j) · not-k (k-sweep) · grok HARD-UNDERFIT (§3k) · context channel-limited (§3o Fork-4) · horizon ASYMPTOTE ~0.28 (§3m) · KV-prefix injection net-harmful (§3p Fork-5, incl. RoPE'd kv2 best −0.249) — **GENERATION dead at k=2; the wall is the objective↔task mismatch, NOT channel width.** Pivot to RECOGNITION (§3q Fork-6 contrastive native-attention addressing) = real-but-sub-usable: 32-way top-1 **0.462 < 0.50 PASS ⇒ REST** (pre-registered, no goalpost move; 15× chance, beats native-key 3.3×; **top-5 0.77** = shortlister-not-sniper → the two-stage retrieve-verify door). P2.b lane rests; memory cells get a heuristic/two-stage addresser, not a learned sole-top-1. **P3 ring-on-Exec is now the active lane:** P3.0 manifest CLOSED GREEN (system `9a2b0a9`) → **P3.1 decode-wiring G-P3-1 BIT-EXACT GREEN on the real 12B** (`off[L]` episode-store indirection in the gemma4 CUDA decode; recall seq == legacy, token-identical; engine `cuda_forward.cu`) → **P3.1b-1 serialized-store G-P3-1b BIT-EXACT GREEN** (`xbar_episode.c` linked into `sp_engine_cuda`; serialize→disk→deserialize→mount→decode == legacy) → **P3.1b-2 recall-as-history G-P3-1b-2 BIT-EXACT GREEN** (mount episode into the live-cache FRONT `[0,H)`, decode prompt at `[H,..)`; no offset threading since pos is already absolute; fix = seed `dpos=H` because the loop-skip bypassed `k_incr_pos`; continuation == monolithic, diffs=0). **THE XBAR READ-PATH IS COMPLETE** — bit-exact on the real 12B at every rung (off[L] mirror → serialized disk episode → prepended history). **P3.2-a WRITE-PATH STARTED — shadow spill G-P3-R2.a BYTE-EXACT GREEN** (the inverse: `SP_XBAR_SPILL=dir`, per-step owner K/V spilled through the `sp_arm_ring2_backend` stdio ABI at `off[L]+pos·kvd·4`, read back byte-identical to the live cache — **diffs=0** at the DEC gate (P=16, 5.2 MiB) AND the 259-position velocity decode (85.3 MiB), 48 owners / **0 sharer blocks in store**; store length = `store_bytes − last-owner-unwritten-slot` confirms the `[0,P-1)` byte law; one-staging-buffer/one-sync batching, per-step-sync perf tax deferred to a P3.2 overlap follow-on). Built on the **VS2022/VS18 host** (VS2019 can't build the CUDA tree — `<stdatomic.h>`). **P3.2-b-1 PAGED-READ G-P3-R2.b-1 BIT-EXACT GREEN** — the closed loop runs live: per step spill `pos` → POISON `[0,pos]` (zero the live cache) → page `[0,pos)` back off Ring-2 (`read_block(off[L])` → H2D) before attention. Paged decode token-identical to legacy full-cache (`diffs[4..16)=0`, both `2 10 100 1000 497 564 …`); the poison proves the bytes came off disk, not a stale live copy. **The model's entire history lived on disk and fed attention bit-exactly — write-path ∘ read-path as one loop.** SCOPE (honest): proves the recall READ; does NOT shrink VRAM (globals attend all positions → need *sparse* recall, the router; only SWA owners shrink on the substrate alone). **P3.2-b-2a SWA RING SHRINK G-P3-R2.b-2a BIT-EXACT GREEN — the FIRST REAL VRAM WIN.** Refinement (caught): gemma SWA is a pure sliding window, NO sinks → the window is always live, nothing to page → the shrink is a `W`-slot RING (not two-source-with-paging, which is the globals' job). The 40 SWA owners (carrying the *dominant* kvd=2048) shrink from `P` to `W` slots: write `pos→slot pos%W`, `k_attn_decode_ring` reads in POSITION order `(s0+j)%W` so the fp reduction is byte-identical. Gate: ring-of-4 == full-cache window-4 decode, `diffs[4..16)=0`, P=16 wraps 3×. Globals untouched (full P; b-2b's job). **Effect: the dominant context-linear cache term (SWA, ~21 GB @ 32k) becomes CONSTANT (~0.67 GB @ W=1024); only the 8 small globals still scale (~1 GB @ 32k) — the last linear term, which b-2b's router collapses.** Bit-exact shrink on 40/48 layers, substrate-only, no router, no disk. Full record CONTRACT-XBAR-P2b §3j–§3q + CONTRACT-XBAR-P3 §P3.1 + §P3.2-a (G-P3-R2.a) + §P3.2-b-1 (G-P3-R2.b-1) + §P3.2-b-2a (G-P3-R2.b-2a). **NEXT = P3.2-b-2b the GLOBAL shrink (sparse top-k recall on the 8 globals via the P2.b §3q router — where the last context-linear term dies and VRAM fully decouples from context).**
- **NEXT:** **P3.2 write/consolidation** (the INVERSE of the read-path: spill stale live-cache blocks → the episode store on context overflow) → **P3.2b** Ring-1 shrink. Then KAIROS two-stage retrieve-verify recall policy ABOVE the now-complete read substrate (the §3q top-5 door). Also queued: Gemma-4 MTP draft head (Unsloth GGUF) as an Exec velocity upgrade to the existing T8 verify loop — gated by a PPL-vs-4.68-gold check first (don't re-enter the condemned GGUF lane on faith; MTP costs ~2GB VRAM, doesn't free it). NIGHTSHIFT v0 + Stage Kairos open as P3 matures.
- **Cloud infra proven + documented**: SSH-free HF-mediated self-terminating RunPod pattern (A6000 $0.33/hr); see `RUNBOOK-cloud-compute.md` + memory `reference-cloud-compute-runpod-hf`.

## 5.12 ETA.5b CLOSED — THE 12B SHOOTOUT WON (2026-06-07) *(SUPERSEDED by §5.13: the 34.2 is RETIRED — its artifact failed the PPL gate)*

**SP 34.2 tok/s vs llama.cpp-CUDA 31.29 ± 0.20 (+9.3%) — Gemma-4-12B, RTX 2060, tg256, SM pinned** (`-lmc` unsupported on GeForce; memory free-ran for BOTH engines). Engine `af738f9`, core `e8708f7`. Full record CONTRACT-SPEED §ETA.5b; receipt `_12b_shootout.log`.

- **ANCHOR: not citable until the PPL gate closes** — the SP artifact squeezes Q6_K source tensors to Q4 (5.56 GB vs the 6.62 GB GGUF; fewer bytes = part of the win, more weight-quant error). Named release-blocking gate for paper 06: wikitext PPL, both engines.
- **E2B ladder (44/44):** lift 10.3 → graph 10.6 → dp4a 62.3 (6.05×) → **graph+dp4a 75.7 tok/s (7.35×)** — Amdahl-clean composition (device PLE gather + packed tied head + jagged graph capture).
- **The dense 12B ≠ E-series:** PL=0 but out_scale + rope_freqs present (now presence-keyed); no KV sharing; per-layer kv-head ARRAY (8 SWA/1 global); **V-less globals (V = raw K projection)** — landed across transcode/bridge/oracle/CUDA, E2B regression held throughout.
- **THE L11 KILL:** per-VECTOR int8 activation quant collapsed on the 12B's outlier-heavy activations (L11, trained out_scale 0.005) → oracle-rank 205596. Operator-directed bisection (provenance → embed 0.000e+00 → norms smooth → layer bisect → **LIFT discriminator: structure at 1.5e-4 floors everywhere**) pinned it to the quant. Fix = per-16-BLOCK scales aligned to the 128-bit loads (zero extra bus). Verdict: **rank 2 at gap 0.31 — a measured top-2 near-tie** (gates now print oracle-rank on any flip). 12B 24/24, E2B 44/44, qwen3 green.

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
