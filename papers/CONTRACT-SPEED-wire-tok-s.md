---
type: contract
title: CONTRACT SPEED — WIRE the integer pipes → tok/s vs llama.cpp (the north-star)
description: "Parent: RFC-001 §0 (the north-star) + §8 (the WIRE gap)."
tags: [contract, speed, wire]
timestamp: 2026-06-07T04:29:37Z
resource: shannon-prime-lattice/papers/CONTRACT-SPEED-wire-tok-s.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# CONTRACT SPEED — WIRE the integer pipes → tok/s vs llama.cpp (the north-star)

**Parent:** RFC-001 §0 (the north-star) + §8 (the WIRE gap). **Priority:** P1 (RFC-001 §11, STATE §5.1). **Status:** DRAFT + baseline in progress.
**One line:** the framework's *reason to exist* is to beat "llama.cpp + old SP hierarchical KV + custom lmstudio @ 40+ tok/s on Qwen3.6." That is a SPEED gate, and speed is the one axis we have **not** measured off-Hexagon. This contract wires the integer pipes into the forward shell and measures real tok/s.

> Why this is P1 (the honest case). C2 measured the context axis: KV ~3.5×/f32 (lossy, real-model 29/31), Ring-2 ~hundreds× effective context but largely disk-tiering. Those are real but secondary. The differentiators — speed on integer pipes, multi-device CRT, MTP — are unmeasured. And the one speed datapoint we have is a **warning**: HX.3b's vrmpy int8 forward was only **1.04× over ARM fp32 and bandwidth-bound** (the chat-shape inner loop missed its 1.20× gate because it's DRAM-traffic-limited, not ALU-limited). If the CPU/CUDA shells behave the same, the speed thesis is at risk — which is exactly why it must be measured before more is built on top.

---

## The WIRE gap (the diagnosis, STATE §6 / RFC §8)

The math-core primitives exist and are validated (Barrett `mod_q`, Frobenius dequant, packed Q4/Q8 arena). But the per-backend forward **shells still call scalar f32** on CPU/CUDA/Vulkan — only Hexagon was wired (HX.3b → vrmpy). **Until a shell calls the integer + packed-weight path, none of the speed/bandwidth envelope is realized — only correctness.** So "PPT-ARM is faster" is, today, entirely unmeasured off-phone.

## The real lever (corrected by HX.3b): bandwidth, not ALU

HX.3b taught us the chat-shape (batch-1 decode) matmul is **memory-bandwidth-bound**, not ALU-bound. So the win is NOT "VNNI does more MACs/cycle" — it is **less DRAM traffic**: reading packed **Q4/Q8 weights (4–8× smaller than f16/f32)** straight into the integer pipe means the matmul moves 4–8× fewer bytes per token. SP's reducing codec (C1) + integer dequant-in-register is exactly this. The gate must therefore measure **bytes-moved / token and tok/s**, and attack bandwidth (packed weights, prefetch, VTCM/cache residency), not just ALU width. VNNI/dp4a/vrmpy are the *consumers* of the packed bytes; the win is the smaller read.

## Gates (each on its own metric — STATE §0)

- **SPEED_BASELINE** *(in progress)* — current SP forward tok/s vs llama.cpp on the SAME proven small model (Qwen3-0.6B, CPU, greedy), as-is (scalar f32 shell). Reports the **SP:llama.cpp ratio** = the gap the WIRE must close. *(0.6B is not the 40-tok/s bar — that's the 35B MoE — but the ratio is the actionable plumbing number.)*
- **SPEED_WIRE_CPU** — wire the packed-Q8/Q4 + AVX-512/VNNI matmul into the CPU decode shell (dev host i9-11900KB has AVX-512+VNNI). Gate: (a) output stays bit-identical to the scalar f32 forward in `deterministic` mode (or within the documented bound); (b) **measured tok/s gain + bytes/token reduction**; (c) does the bandwidth lever actually pay (compare packed-weight read traffic vs f16).
- **SPEED_WIRE_CU** — same for CUDA (dp4a/PTX int8), sm-tier-aware (Turing dev caveat: INT8-TC peak ratio fixed; see CUDA SM tiers).
- **SPEED_NORTHSTAR** — the real bar: **Qwen3.6-35B-A3B ≥ 40 tok/s** on the dev host, vs "llama.cpp + SP-hier-KV + lmstudio." System gate (envelope assembled: packed weights + integer pipe + Spinor-KV window + MoE expert residency). For the 35B-A3B the dominant cost is **weight/expert memory traffic**, so this composes C1 (reducing weights) + expert streaming + the CPU/GPU integer pipe.

## Honest risks (where this breaks)

1. **Bandwidth bound everywhere.** If decode is DRAM-bound on CPU/CUDA like it was on Hexagon, integer ALUs give ~1× and the only real lever is the packed-weight traffic reduction — which caps the win near the quant ratio (Q8→~2× vs f16, Q4→~4×), not more. A ~1.04×-style result on CPU would put the whole speed thesis in question. **Measure before believing.**
2. **MoE expert residency** dominates the 35B-A3B; if experts stream from disk, per-token latency is I/O-bound and the integer pipe is irrelevant until experts are resident/prefetched.
3. **Bit-exact under the integer pipe** must hold in deterministic mode or the regression invariant breaks; the Frobenius dequant ordering is the risk.

## Baseline measurements

- **llama.cpp reference (Qwen3-0.6B-f16, CPU `-ngl 0`, greedy, dev host i9-11900KB), MEASURED 2026-06-02:** **prompt 210.3 t/s, generation 28.2 t/s.** *(f16 decode on CPU is already bandwidth-heavy — only ~28 t/s for a 0.6B — which itself supports the "decode is DRAM-bound" thesis: even llama.cpp's optimized f16 path is bandwidth-limited here, so a packed Q8/Q4 read should help llama.cpp AND SP. The fair SP comparison is vs llama.cpp **Q8_0** (`Qwen3-0.6B-Q8_0.gguf`, on disk) since the SP Executive is OK_Q8 — run that next.)*
- **SP forward (qwen3_rt.sp-model = OK_Q8, qwen3_generate_kv, same box):** _[pending — needs a tok/s timing harness; `test_gen_kv` checks argmax identity only, no timing. **Immediate next build task:** a minimal `sp_toks` harness timing `qwen3_generate_kv` over N tokens → tok/s.]_
- **llama.cpp Q8_0 reference (fair vs OK_Q8):** _[pending — quick re-run on the Q8 gguf]_
- **SP:llama.cpp ratio:** _[pending the SP number]_ → defines the WIRE target multiple.

**First read of the baseline:** llama.cpp f16 0.6B decode at **28 t/s on CPU** confirms decode is bandwidth-bound even in a tuned engine — reinforcing the contract's thesis that the SP lever is **reduced weight-read traffic (packed Q8/Q4)**, not ALU width. The WIRE target: SP's OK_Q8 packed path should move ~2× fewer weight bytes/token than f16 → the gate is whether SP reaches/*beats* llama.cpp's Q8 decode tok/s once the integer pipe is wired (today the SP shell is scalar f32, so it will currently be *slower* — that gap is exactly SPEED_WIRE_CPU's target).

## SPEED_WIRE_CPU — MEASURED LADDER (2026-06-02, `sp_toks`, Qwen3-0.6B, CPU, single-thread)

Prereq unblocked: the engine forward crashed (fork-tax struct divergence) — FIXED engine `0fb39ab`. Then, env-only (no kernel change), via `SP_ARENA`:

| path | tok/s | vs f16 | note |
|---|---|---|---|
| f16 (gguf, dequant per row) | **0.84** | 1.0× | the as-is baseline |
| **Q8 arena** (`SP_ARENA=q8 SP_ARENA_EMBED=1`) | **1.58** | **1.88×** | packed int8, `matmul_arena` inline-lift, no unpack — **the bandwidth lever, confirmed** |
| Q4 arena (`SP_ARENA=q4`) | 0.85 | 1.0× | per-row `sp_frob_q4_unpack` overhead negates the smaller read → **Q4 needs a SIMD/streaming unpack or it's a wash in this scalar path** |
| **Q8 arena + OpenMP-threaded `matmul_arena`** (engine `8975753`) | **10.53** | **12.5×** | **6.7× over single-thread Q8.** Threading the per-output-row loop was the dominant lever. Parity-safe by construction (each Y[j] an independent single-threaded dot). |

**Finding:** packing to Q8 ~doubles throughput (bandwidth thesis), then **threading the matmul gives 6.7× more → 10.53 tok/s, 12.5× over the f16 baseline.** **vs llama.cpp 28.2 t/s, SP is now ~2.7× short (was ~33×).** Threading was the dominant gap, as predicted. Remaining WIRE-CPU-V2 levers (smaller now, Amdahl-bound):
1. ~~Multi-thread the decode matmul~~ **DONE (`8975753`, 6.7× → 10.53).**
3. ~~Thread the non-matmul ops~~ **DONE (`d7735a4`): per-head QK-norm/RoPE + attention head-loop (per-thread score scratch). → 12.55 tok/s (+19% at n_gen=32). Confirmed Amdahl: once matmul was threaded the per-head serial work mattered.**
2. **SIMD `matmul_arena` inner dot** [NEXT, the substantial one] — still scalar `acc += (float)cp[i]*x[i]`; AVX2/VNNI int8 dot. At 12.55 t/s the decode is matmul-ALU-bound, so this is where the next big gain is.
4. Q4: a vectorized unpack so its bandwidth win isn't eaten.

| add'l path | tok/s | |
|---|---|---|
| Q8 + threaded matmul | 10.53 | (n_gen=32) |
| Q8 + threaded matmul + threaded attention/per-head | 12.55 | +19% |
| **Q8 + threaded + AVX2 int8×f32 dot** (`5e443c9`) | **39.52** | **3.15× — the SIMD lever** |

**Full arc (Qwen3-0.6B, CPU, n_gen=32): 0.84 (f16) → 1.58 (Q8) → 10.53 (thread mm) → 12.55 (thread attn) → 39.52 (AVX2 dot) = 47× over baseline.**

### Fair quant-matched comparison (the honest scoreboard)
| engine / quant | gen tok/s | |
|---|---|---|
| SP **Q8** (threaded + AVX2) | **39.52** | |
| llama.cpp **f16** | 28.2 | SP-Q8 wins — but NOT apples-to-apples (f16 is bandwidth-heavier) |
| llama.cpp **Q8_0** | **52.8** | **the fair fight: SP is ~0.75× (llama.cpp ~1.34× faster)** |

**Honest standing:** SP went from ~33× behind to **~1.34× behind llama.cpp on the fair Q8-vs-Q8 comparison** — competitive, not yet winning. SP-Q8 *does* beat llama.cpp-f16, but the quant-matched number is the real one.

### VNNI int8×int8 — TESTED, DOCUMENTED NEGATIVE (2026-06-02, gated `SP_VNNI=1`, engine `a2ad1dc`)
Hypothesis: the ~1.34× gap is the AVX2-f32 (1 MAC/lane) vs VNNI `dpbusd` (4 int8-MAC/lane) ALU gap. **Wired it (dynamic per-vector int8 act-quant + `sp_avx512_vnni_matvec`, threaded, per-tensor bias=128·Σcodes + scale cached) and measured — hypothesis FALSIFIED:**
- **Speed: VNNI 43.95 vs AVX2 40.38 = only +9%.** VNNI reads the *same int8 weight bytes* as the AVX2-int8 dot; the 4× ALU barely helps → **Q8 decode is BANDWIDTH-bound (weight reads), not ALU-bound.** So the gap to llama.cpp-Q8 is **memory layout / Q8_0 32-elem block format / fewer passes**, NOT ALU/VNNI.
- **Accuracy: top-1 gate FAILS** — VNNI tokens diverge from the f32-act ref (`3 4 3 4…` vs `3 5 3 9 2 61…21389…`). Naive per-vector dynamic int8 act-quant is too lossy (one `max_abs` scale, outliers crush the rest). Needs per-channel/SmoothQuant = research, not a free win.

**Conclusion: AVX2-f32 dot (40 t/s, accurate, parity-safe) is the production CPU kernel.** VNNI stays gated+OFF as a documented dead-end for this scheme. **The real remaining gap is memory layout/bandwidth — a different investigation than ALU.** Live follow-ups: a Q8_0-style 32-elem block layout to cut passes/improve locality; gemma3/qwen36 attention threading. (gemma3/qwen36 attention share the threading pattern.)

## WIRE-CPU-V3 (the layout investigation) — planned

Full stage plan: **`PLAN-SPEED-WIRE-CPU-V3-memory-layout.md`**. Summary: Stage 0 profiles where the 1.34× lives (bytes/token, LLC misses, passes) before any code; Stage 1 adds a block-scoped Q8 layout (32-elem blocks + per-block scale, SP-native Q8_0 analogue) in the Frobenius packer; Stages 2–3 fuse/prefetch and generalize the kernel to gemma3/qwen36. **Strategic note:** the 0.6B dense dot is a *match-the-ceiling* (llama.cpp is tuned); SP's real speed differentiator is the composed **35B-A3B MoE** envelope (reducing weights + expert residency + Spinor-KV window) — that's `SPEED_NORTHSTAR`, a separate lever from the 0.6B kernel.

## WIRE-CPU-V3 Stage 0 + 1a — MEASURED (2026-06-03), and a correction

**The 39.52 is withdrawn — it does not reproduce.** A fresh build of the *exact* commit that recorded it (`5e443c9`) gives **15.68 tok/s (n=32) / 13.91 (n=128)** today; current `main` gives 14.06 / 13.47; a cooler run gave 16.78 (n=128). So `5e443c9 ≈ main` — **not a regression** (C2.1 is clean) — and the honest reproducible figure is **~14–17 tok/s**. **vs llama.cpp Q8_0 (52.8): SP is ~3.2–3.8× behind, not 1.34×.** Docs that cite 39.52 / 1.34× (READMEs, Systems-v1, RFC-001) overstate and should read ~14–17 / ~3.5× behind.

**Stage 0 (env-toggle triangulation):** threading the AVX2 dot on 16 cores adds only **1.24×** (vs ~5.5× on the scalar path) → the dot is **bandwidth/convert-bound**, not compute-bound (~8 GB/s effective, under DRAM peak). The per-row fp32 scale stream is negligible vs int8 weight bytes, so SP and Q8_0 move ~the same bytes — the gap is *passes / the int8→f32 convert / activation side*, not bytes.

**Stage 1a (AVX-512 16-wide int8×f32 dot, `SP_CPU_AVX512DOT=1`, engine `cpu_overlay.c`):** parity-exact (top-1 == scalar) and **+0.1% (16.78 → 16.80)**. Doubling SIMD width does nothing → ALU width is not the lever (same conclusion as VNNI's +9%). **Kept gated + OFF as a documented dead-end.**

**Stage 1b candidate:** a **block-Q8 int8×int8 dot with per-block activation quant** (Q8_0-faithful). Removes the per-element `int8→f32` convert + fixes the per-vector VNNI accuracy failure. **De-prioritized** — Stage 1a + the thread sweep show the dot ALU isn't the bottleneck, so this is unlikely to be the big lever.

**Stage 1b ACTUAL WIN — thread oversubscription (the real lever, FIXED 2026-06-03, engine `cpu_overlay.c`).** A no-rebuild OMP thread sweep on the existing binary:

| OMP threads | tok/s (Qwen3-0.6B Q8, n=64) |
|---|---|
| 1 | 11.84 |
| 4 | 24.85 |
| **5 (peak)** | **25.82–25.97** |
| 6 | 25.07 |
| 8 (physical) | 22.9 |
| **16 (the OLD default = all logical)** | **16.5** |

The box is 8 physical / 16 logical. **The OMP default of all-logical threads oversubscribes the 8 physical cores and runs ~1.5× SLOWER than the physical-core count** — so every prior measurement this session (incl. the "39.52" bisect at default‑16 → 15.68) ran the *worst* config. **Fix shipped:** `sp_kernels` now defaults OMP to physical cores (`omp_get_num_procs()/2`), overridable by `OMP_NUM_THREADS` / `SP_OMP_THREADS`. New default **22.91 tok/s** (1.39× free), tuned `SP_OMP_THREADS=5` **25.97**, top-1 parity-exact.

### Both engines re-measured on THIS box (2026-06-04) — the fair comparison

The earlier dot conclusions were measured at the broken 16-thread default; **re-measured at the correct thread counts**, both engines reproduced (so the comparison is now valid):

| engine (best config, Qwen3-0.6B Q8, CPU, this box) | gen tok/s |
|---|---|
| SP, 5 threads, scalar dot | 6.92 |
| SP, 5 threads, AVX2 dot | 26.05 |
| **SP, 5 threads, AVX-512 dot** | **27.32** |
| **llama.cpp Q8_0, 8 threads (its default)** | **53.27** |
| llama.cpp Q8_0, 5 threads | 50.50 |

**SP best ~27.3 vs llama.cpp best ~53.3 → ~1.95× behind** (matched at 5 threads: 27.3 vs 50.5 = 1.85×). **llama.cpp reproduces the recorded 52.8** (53.3 today) — it is a trustworthy reference; only SP's 39.52 was non-reproducible.

**Two earlier conclusions RETRACTED (both were measured in the wrong regime):**
- **The dot IS a lever.** At the correct 5 threads, AVX2 is **3.76×** over scalar (6.92→26.05) and **AVX-512 is +4.9%** (26.05→27.32, top-1 parity-exact). The earlier "+0.1%, dot dead" was measured at 16 oversubscribed threads where the cores thrash and nothing downstream shows. AVX-512 dot is a real (small) win — re-enable for default-on consideration.
- **block-Q8 is NOT de-prioritized.** The levers **stack** (thread-count × SIMD-width × layout); a faster int8×int8 block dot can still pay on top of the thread fix. Stage 1b remains live.

**Honest standing + what's left:** SP ~27 vs llama ~53 = **~1.95× behind**, both reproduced. The thread fix (physical-core default) is the shipped win; the remaining ~2× is open and **not capped** — llama scales to 8 threads while SP saturates at 5 (its kernels are more memory-efficient per thread), and the stacked levers (AVX-512 dot default-on, block-Q8 int8×int8, threading the serial pipeline parts, per-token overhead) are the path to close it. Note llama.cpp is itself built with AVX-512 (`AVX512=1`) and hits 53 — so SP's headroom is real.

### "Match llama" attempt — what was ruled out, and the call (2026-06-04)

Drove the dense-0.6B gap hard, measuring at the correct thread counts:
- **block-Q8 int8×int8 + per-32-block activation quant** (`SP_Q8BLK`, `sp_avx512_q8blk_matvec`): **top-1 parity-exact** (per-block scales fix the per-vector VNNI accuracy failure) but **~no speedup** (26.33 vs 26.25 AVX2 @5t; slower @8t) — the dpbusd ALU win is eaten by per-block hsum/float-combine + per-token act-quant. Gated OFF, kept as the accuracy-safe VNNI reference.
- **Thread affinity / wait-policy** (`OMP_PROC_BIND=close`, `OMP_WAIT_POLICY=active`): +2% at 5t, no change to the 8t degradation → **not** fork/join or migration.
- **Bandwidth probe (decisive):** Q4 (0.3 GB/tok) vs Q8 (0.6 GB/tok) at 5 threads = **5.82 vs 26.17 tok/s** — Q4 is *4.5× SLOWER*. If SP were memory-bandwidth-bound, halving the bytes would speed it up; it doesn't → **SP is NOT bandwidth-bound. It is compute / per-element-overhead bound** (the int8→f32 convert for Q8; the heavier nibble-unpack for Q4).

**What this actually means (no false ceiling):** the dense GEMV gap is *not* a memory wall and *not* unbeatable. My `q8blk` int8×int8 tied AVX2 (26.3) **only because its per-block `hsum` + float-combine reduction ate the `dpbusd` ALU win** — not because int8×int8 can't help. llama's q8_0 vec-dot avoids that with a vectorized block-scale reduction. **The untried real lever = a properly-tuned int8×int8 GEMV** (defer/vectorize the block-scale combine, no per-block hsum) — achievable kernel engineering, the next thing to build. The shipped thread fix (~14 → ~26, 1.85×) stands; ~1.95× behind llama; gap is compute-overhead in the dot reduction, **open and attackable**. (Separately, `SPEED_NORTHSTAR` — the 35B-A3B MoE envelope — remains SP's *structural* speed edge, but the dense-0.6B kernel is NOT conceded.)

## Read amplification via Q-head divergence — MEASURED MID-FLIGHT (2026-06-05, composed 32k finale v2)

Discovered live, not modeled: at 32k streaming ingest (B=512, bits-r64 router,
fusion blocks 8KB K / 4KB V, Optane F:), the per-(layer,token) Ring-2 fetch is
the UNION of all 16 Q-heads' independent selections. Under SimHash the heads
genuinely diverge, so the union balloons toward thousands of distinct
positions per layer:

    measured: ~1 GB of Optane reads PER TOKEN
              1.86e9 read ops / 11.4 TB total at pos ~11k of 32768
              drive sustained ~528 MB/s — the P1600X random-read ceiling
              at this block size, held for 6+ hours, no deadlock, no leak

Two readings, both true:
- STABILITY PROOF: the Ring-2 C-ABI + IOCP path saturates the physical device
  indefinitely. The architecture demands 1 GB/token and the hardware complies.
- COST DISCOVERY: independent per-Q-head routing multiplies disk traffic by
  the head-divergence factor (up to NH/dedupe-overlap). The 32k claim
  survives intact; we just learned its true price.

**PRIMARY STAGE-ALPHA FOLLOW-ON LEVER — GQA KV-head selection.** The 16
Q-heads sit in 8 GQA groups; group members score against the SAME physical
K/V. Selecting per KV-HEAD (8 selections, e.g. group-q signature or
union-of-2) instead of per Q-head halves the union at the source; a per-layer
joint top-k collapses it further. HONESTY CLAUSE: this CHANGES the recalled
set (group members currently select with their own q projections), so it is a
router-policy change requiring the full NIAH + PPL re-gate — it is NOT
fidelity-free and must not ship as a silent default. Applies equally to the
f32 and bits routers (both select per Q-head today).

Secondary levers, same family: V-stream on E: (second device, independent
queue — SP_RING2_OPTANE_DIR_V), staging-cache of hot union members across
adjacent tokens (temporal overlap is high in streaming ingest), and Spinor-V
(63B lossy) as an opt-in V-bandwidth diet (off the bit-exact path).

CALIBRATION RULE (two bad ETAs in one bake): composed-run wall estimates must
model READ AMPLIFICATION (union factor x block size x layers), not just op
counts and per-term FLOPs.

**KVSEL RE-GATE — BOTH GATES GREEN (2026-06-05, math-core `2441e0b` + engine `200c0ec`):**
- NIAH bits-r64 B=128 (4x), group-centroid selection: d10 HIT / d50 HIT / **d90 HIT** (the r=32-killer boundary cell holds).
- PPL N=2048 B=512: **12.56881 = −0.92% vs baseline 12.68574** — PASS (<2%), and slightly BETTER than per-Q-head bits at the same budget (12.66996). The centroid merge costs nothing distributionally at 4x; group members were structurally attending the same K anyway.
**KVSEL verdict: admissible at ≤4x alongside bits-r64. Production trio: `SP_RECALL_BITS=1 SP_RECALL_R=64 SP_RECALL_KVSEL=1` for ≤4x budgets.** 8x remains unmeasured under KVSEL (inherits the bits-r64 8x FAIL conservatively until measured). Composed 32k finale v3 (KVSEL + split K→F:/V→E: devices) fired same day.

## Temporal locality of attention routing — the LRU staging cache (FILED 2026-06-06, the first post-Alpha optimization)

OBSERVATION (v4 composed run, indirect but consistent): the recall sets of
adjacent decode steps drift slowly — token t and t+1 select nearly identical
top-k positions, so the staged-union working set GLIDES across the cold
store rather than thrashing. Consequence: the same hot blocks are re-fetched
from Optane every token. The marginal-rate decay curve and the union-growth
model both point at re-fetch volume, not unique-block volume, as the
dominant I/O term (~20 TB physical reads for a 32k ingest whose unique
block population is ~11 GB).

HONESTY STATUS: temporal locality is at this point an INFERENCE from the
drift argument + rate curves — the hit-rate is NOT yet measured. The first
deliverable of the cache sprint is therefore the MEASUREMENT, not the cache:
instrument the staging path with a shadow LRU counter (zero behavior change)
and report hit-rate vs cache size on a real run. Claim nothing until then.

THE LEVER (post-Alpha v5): a BOUNDED LRU cache over staged Ring-2 blocks
(e.g. 256 MB) in front of read_batch2. Bounded => still O(1) RAM in context
length; the window-sized-RAM claim survives with the honest amendment
"+ bounded staging cache". Predicted effect if locality holds: 5-10x I/O
collapse (20 TB -> low single-digit TB physical).

GATES (daylight work, never midnight work): T_CACHE_EXACT — cached decode
== uncached decode BIT-IDENTICAL sequences (a stale hit silently poisons
attention; this gate is the whole game); T_CACHE_HITRATE — measured curve
hit-rate(cache_bytes); plus the v4 run preserved as the UN-CACHED control
baseline so the v5 delta is attributable. Concurrency note: the cache sits
in the wrapper ABOVE the dual-device overlap — single-writer (the decode is
serial), so no coherency protocol needed, but the v5 design must pin that
assumption in writing before code.

## Stage Beta GPU decode — tok/s on the RTX 2060 (2026-06-06, engine 3b6831c/1af7c9a)

First token-generation numbers on Turing. qwen3_decode_cuda: KV resident in
VRAM, single-query attention, device argmax (zero per-step host sync at
eos=-1). qwen3_rt 0.6B, prompt {1,2,3,4}, n_gen=24, gate M_QWEN3_DECODE_CUDA
PASS (GPU decode == GPU prefill teacher-forced).

These Speed-Pass-1 numbers (6.93 / 7.04 / 11.97) were COLD-START dominated —
see the BETA.2 correction below. They are retained only as a record of the
mismeasurement, not as valid steady-state figures.

| Config                  | tok/s | note                                    |
| ----------------------- | ----- | --------------------------------------- |
| f32 + host argmax       | 6.93  | COLD-START artifact (first decode/proc) |
| f32 + device argmax     | 7.04  | COLD-START artifact                     |
| Q8 arena + device argmax| 11.97 | COLD-START artifact                     |

## BETA.2 — CUDA graphs + the measurement correction (2026-06-06, engine ebcbedb->664fae1->2138f89)

**No spin: the first BETA.2 commit claimed "7.24 -> 91.55, 12.65x". That was
THREE stacked measurement artifacts.** Corrected after KnackAU pushed to
measure the real .sp-model + longer windows.

The confounds (each dwarfs the real effect at 0.6B single-token decode):
1. COLD-START (~13x): CUDA lazy module load + cuBLAS JIT happen on the FIRST
   kernel launch of a process. The 12.65x timed per-step COLD (ran first) vs
   graph WARM (ran second).
2. SHORT-WINDOW JITTER: n_gen=24 ~ 0.3s; readings swung 32/88/92 for one path.
3. GPU CLOCK STATE (~5x): the RTX 2060 idles at 405 MHz vs 2100 max; a
   single-token 0.6B decode is too light to ramp boost clocks, so absolute
   tok/s sampled whatever P-state the card was in (31<->92 across runs).

ANCHORED RESULT (warmup + n_gen=256 + clocks LOCKED at 2100 MHz via
`nvidia-smi -lgc 2100,2100`, then reset):

| precision            | per-step | graph | graph win |
| -------------------- | -------- | ----- | --------- |
| f32 (f16 gguf)       | 92.3     | 97.7  | 1.06x     |
| Q8 (gguf transcode)  | 92.4     | 97.6  | 1.06x     |
| Q8 (.sp-model disk)  | 92.2     | 97.5  | 1.06x     |

FINDINGS (the reliable, within-run signals):
- CUDA graphs = ~6%, NOT 12.65x. Launch overhead was never the wall;
  COLD-START was. A persistent warm daemon captures that for free.
- Decode is PRECISION-INDEPENDENT (f32 == Q8 == .sp-model, within 0.3 tok/s):
  every path dequants packed weights to an f32 scratch BEFORE the SGEMM, so the
  GEMM never sees packed bytes -> no bandwidth delta. Q8 is a VRAM-CAPACITY
  play, not decode speed. The bandwidth win needs a true INT8 tensor-core GEMM
  consuming packed codes directly (BETA.3; sm_75 has INT8 mma).
- The .sp-model SHIP ARTIFACT now ingests + decodes identically to the
  transcode (adapter min-copy fix, engine 2138f89), gated 21/21.

MECHANISM (graph path, unchanged + correct): position-indirection — hold pos in
a device scalar int*dpos; kernels (k_embed_at, k_rope_dyn, k_kv_store,
k_attn_decode_dyn, k_argmax_at, k_incr_pos) DEREFERENCE dpos so graph topology +
node params stay constant -> cudaStreamBeginCapture once, cudaGraphLaunch
x n_gen. cuBLAS SGEMM + dequant capture-safe; prompt ingest stays per-step;
fixed attn shm = P floats, 48KB sm_75 guard. GATE 21/21: graph==per-step
byte-exact AND decode==prefill, per precision.

METHODOLOGY RULE (now standing): no GPU tok/s number without warmup + long
window + LOCKED clocks; trust within-run ratios over absolutes.

LEVER LADDER (BETA.3+): INT8-TC GEMM consuming packed Q8 codes directly (the
real bandwidth lever) + fused decode kernels (shrink the ~250-kernel graph) ->
BETA.4 discrete router on GPU (warp-per-head NTT + bits-r64 popcount; NO L2 pin
on Turing, MaxPersistingL2=0 measured, use 64KB shared) -> BETA.5 llama.cpp-CUDA
head-to-head (terminal gate, formal — same clock-lock + prompt).

WEIGHT-COMPRESSION HONESTY (corrected this session): the ".sp-model 50%" is
f16->OK_Q8 (quantization, top-1/output-lossless, NOT lossless). A model
already at 4-bit (Q4_K_M) has no 50% to take; OK_Q4 gives ~17% structural,
sub-Q4 is an open follow-up. Beta TIES llama.cpp on weight size; the win is
bandwidth-efficient O(1) deep-context attention, NOT smaller weights.

## BETA.3a — dp4a INT8 GEMV: the bandwidth thesis, validated (2026-06-06, engine bd87e99)

The anchored f32==Q8 result hid that the Q8 decode path was PATHOLOGICAL:
gemm_w dequants packed codes -> f32 scratch -> SGEMM EVERY step (~9 B/weight:
read code + write f32 + reread), so Q8 ran 3x SLOWER than f32. The packed
bytes never reached the GEMM.

Fix: decode is M=1, so the tensor-core mma m8n8k16 tile can't help (1 row fills
1/8 of MMA_M). The Turing GEMV lever is __dp4a (4-wide INT8 dot -> INT32, native
sm_75). k_quant_act_int8 (dynamic per-vector activation quant) + k_gemv_q8_dp4a
(one block/row, dp4a over codes read 1 B/weight STRAIGHT from VRAM, no scratch).

RESULT (RTX 2060, 0.6B, n_gen=256, clocks LOCKED 1500 MHz sustainable):

| path                       | tok/s | bytes/weight |
| -------------------------- | ----- | ------------ |
| Q8 dequant -> f32 -> SGEMM | 29.98 | ~9           |
| f32 cuBLAS SGEMM           | 91.77 | 4            |
| **Q8 dp4a INT8 GEMV**      | **84.27** | **1**    |

dp4a = **2.81x** the dequant path (3.01x at 2100 MHz), **top-1 LOSSLESS 256/256**
(activation int8 quant changes zero argmaxes). The bandwidth thesis holds:
keeping weights 1-byte to the ALU recovers the ~3x the dequant path threw away.
int8 (84) ~ f32 cuBLAS (92): the naive 1-block/row GEMV nearly matches SGEMM on
4x less data — a TUNED warp-per-row vectorized GEMV pushes past f32 (next).
NOTE (per methodology rule): the within-precision back-to-back ratio is the
reliable signal; absolute tok/s drifts with clock/thermal even when locked.

NEXT: tuned dp4a GEMV -> BETA.3b prefill mma m8n8k16 (ptx_mma.cuh, M=n_tok fills
the tile) -> BETA.4 GPU router -> BETA.5 llama.cpp-CUDA head-to-head.

## BETA.3a-v2 — tuned GEMV + the regime correction (2026-06-06, engine 3d43705)

Built the tuned k_gemv_q8_dp4a_v2 (warp-per-row, 128-bit int4 loads,
__shfl_down_sync reduction, 8 rows/block) — top-1 LOSSLESS 256/256. But it
exposed that the BETA.3a 2.81x/5.82x int8 'wins' were a THROTTLED-MEMORY-CLOCK
ARTIFACT. nvidia-smi -lgc locks only the SM clock; a weight-GEMV is MEMORY-bound,
so its tok/s tracked the free-running GDDR6 clock. With BOTH clocks at full speed
(mem 7001 + sm 1500, reproducible x3):

| path                       | tok/s |
| -------------------------- | ----- |
| f32 cuBLAS SGEMM           | 91.5  |
| Q8 dequant -> f32 -> SGEMM | 91.4  |
| Q8 dp4a INT8 GEMV (tuned)  | 91.5  |

ALL CONVERGE. At 0.6B/full-clock the decode is OVERHEAD-bound (~250 launches +
attention + argmax over 151936 vocab), NOT weight-bandwidth-bound, so a cheaper
weight-GEMV TIES f32 (Amdahl: weight matmuls aren't the dominant cost). The
dequant path's earlier 3x-slowness was likewise a low-memory-clock artifact
(30 -> 91 once mem pinned).

HONEST CONCLUSION: the int8 dp4a kernel is correct + top-1 lossless, but the
bandwidth win only BINDS in a memory-bound regime — a much larger model (12B
weight matrices ~20x bigger -> genuinely memory-bound at full clock), NOT 0.6B.
The kernel is kept as the right tool for that regime; it's a no-op tie here.
Methodology rule updated: lock BOTH clocks (SM + memory) and confirm the kernel
sits on the binding bottleneck before claiming a win.

NEXT: profile the real 0.6B decode ceiling (argmax-over-152k / attention /
launch count) OR validate int8 on the 12B Gemma where weight bandwidth binds.

## BETA.3a-v3 — isolated GEMV crossover: bandwidth thesis PROVEN (2026-06-06)

tests/bench_gemv_int8.cu: standalone nvcc microbench, f32 cuBLAS SGEMV vs int8
dp4a-v2 GEMV (single-token M=1), sweeping weight-matrix N=1K..16K with clocks
pinned. Strips attention/argmax/launch overhead to isolate the matmul — the one
thing the dp4a kernel optimizes. Within-N back-to-back ratio (reliable signal).

| N      | f32 us | int8 us | speedup | f32 GB/s |
| ------ | ------ | ------- | ------- | -------- |
| 1024   | 19     | 17      | 1.1x    | 218      |
| 2048   | 57-82  | 25      | 2.3-3.2x| ~290     |
| 4096   | 242    | 72      | 3.4x    | 277      |
| 8192   | 928    | 257     | 3.6x    | 290      |
| 12288  | 2068   | 542     | 3.7-3.95x | 292    |
| 16384  | 3642   | 961     | 3.79x   | 295      |

f32 SGEMV pins at ~290 GB/s = 86% of the 2060's 336 GB/s peak across all large
N -> genuinely bus-saturated. int8 saturates the SAME bus but moves 4x fewer
bytes -> converges to ~3.7-3.8x, hugging the 4:1 byte ratio. Crossover
(overhead -> memory-bound) ~ N=1024-2048. The 0.6B matmuls (N~1K-3K) sit at the
low edge AND are masked by decode overhead -> why int8 tied there. A 12B
(hidden ~3840, FF ~15360) sits firmly in the 3.7-3.8x regime.

CONCLUSION: the dp4a INT8 GEMV is mathematically sound (top-1 lossless) AND
physically dominant when the GDDR6 bus binds — proven in isolation, no 12B
integration tax. This MANDATES the Q4-dp4a kernel (the 6.6GB Q4 12B that fits
12GB VRAM) + the Gemma4-CUDA forward (Stage Eta) as the justified next sprints.
GeForce -lmc is unsupported (memory auto-boosts under load); the within-N ratio
is the reliable signal regardless.

## BETA.3a-v4 — Q4-dp4a: the full bandwidth ladder (2026-06-06)

Added k_gemv_q4_dp4a_v2 to the bench: Q4 arena = 2 nibbles/byte (low=even,
high=odd, sign-ext (n^8)-8, qmax=7). Read int4 (16 B = 32 packed weights) STRAIGHT
from VRAM, unpack nibbles -> int8 IN THE ALU (free under memory-bound), feed dp4a;
activation int8. 0.5 B/weight => 8:1 theoretical over f32. Host-reference
correctness gate @N=1024: max rel err 1.34e-7 -> PASS (exact int dot, nibble
decode matches the arena).

THE COMPLETE LADDER (RTX 2060, clocks pinned, isolated GEMV, reproducible):

| bytes/weight | path | speedup vs f32 @N>=12K | eff GB/s |
| ------------ | ---- | ---------------------- | -------- |
| 4.0          | f32 cuBLAS SGEMV | 1.0x (baseline) | ~293 (bus-saturated, 87% of 336 peak) |
| 1.0          | int8 dp4a GEMV   | ~3.8x           | ~280 |
| 0.5          | Q4 dp4a GEMV     | **~7.06x**      | ~260 |

Each halving of bytes/weight ~doubles throughput, tracking the byte ratio minus a
shrinking margin: int8 hits 3.8x of the 4:1 ceiling; Q4 hits 7.06x of the 8:1
ceiling. The Q4 nibble-unpack ALU tax is the only visible cost (Q4 saturates ~260
GB/s vs int8 ~280 => ~7%, so 7x not 8x). The ALUs are otherwise idle under
memory-bound conditions, exactly as predicted. Crossover (overhead -> bus-bound)
~ N=2K for both; the 0.6B matmuls sit below it (and are masked by decode overhead),
the 12B sits firmly above.

CONCLUSION: the discrete Z_q substrate's packed weights aren't just smaller on
disk -- at Stage-Eta (12B+) dimensions they are ~7x faster to COMPUTE on consumer
silicon, bit-exact-correct, because the GDDR6 bus is the wall and Q4 carries 8x
less traffic across it. This is the quantitative case for the Q4-dp4a decode path
+ Gemma4-CUDA port (Stage Eta), where the 6.6 GB Q4 12B fits the 12 GB VRAM.

## BETA.3a-v4 wired into the production decode (2026-06-06, engine a6c9d9f)

Promoted k_gemv_q4_dp4a_v2 from the bench into cuda_forward.cu; qwen3_decode_cuda
routes every matmul through gemv_w_packed (Q8/Q4 dp4a, no f32 scratch) under
SP_CUDA_DECODE_INT8. The PRODUCTION gate caught a bug the isolated bench could not
(it used uniform synthetic Q4): the SP_ARENA=q4 arena is MIXED PRECISION (head
kept Q8, body Q4); dispatching on the GLOBAL arena precision read the Q8 head as
Q4 -> Q4 top-1 0/256. Fix: DevTensor carries a per-TENSOR precision (from
row_prec[0] + uniformity scan -> dequant fallback for mixed rows); gemv_w_packed
dispatches on W->prec. Gate M_QWEN3_DECODE_CUDA now 28/28: f32/Q8/Q4/.sp-model all
256/256 top-1 lossless. LESSON: isolated benches validate kernel MATH; production
gates validate the DATA-STRUCTURE handoff. The 4-bit arena ingest+compute path is
now battle-tested for Stage Eta to drop into.

## ETA.5b — THE 12B SHOOTOUT: SP 34.2 tok/s vs llama.cpp-CUDA 31.29 (+9.3%) (2026-06-07, engine c89fc96→52b3379→af738f9, core e8708f7)

**THE NUMBER (receipt `_12b_shootout.log`):** Gemma-4-12B, RTX 2060, tg256, SM
pinned 2100 MHz (`-lmc` unsupported on GeForce — memory clock free-ran for BOTH
engines, same conditions):

| engine | artifact | tok/s |
|---|---|---|
| llama.cpp-CUDA b8861 (ngl 99) | Q4_K_M GGUF, 6.62 GB | 31.29 ± 0.20 |
| **SP (graph + dp4a)** | **reducing .sp-model, 5.56 GB** | **34.2 (+9.3%)** |

**ANCHOR — this number is NOT citable until the PPL gate closes:** the SP
artifact squeezes the source's Q6_K tensors (attn_v, ffn_down) into Q4 codes —
fewer bytes read (part of the win), MORE weight-quant error than llama.cpp's
mixed K-quants. Quality currency so far = oracle-anchored top-1/top-2 on short
streams. The named gate before paper 06 releases: wikitext PPL, both engines,
same text, protocol disclosed.

### The E2B ladder (the levers, isolated; suite 44/44)

| config | tok/s | gate |
|---|---|---|
| oracle lift | 10.3 | byte-match (E_G4_CU_DEC oracle ALL) |
| + CUDA graph | 10.6 | 256/256 EXACT |
| + dp4a (Q8) | 62.3 (6.05×) | 256/256 top-1 |
| graph + dp4a | **75.7 (7.35×)** | 256/256 top-1 |

Amdahl composition, on the record: graphs do ~nothing under the bandwidth wall;
dp4a removes the wall (6× ≈ the byte ratio at model scale); THEN the
launch-overhead saving appears (+21%). Levers: device-side packed PLE gather
(`pl_tok_embd` + `k_ple_gather_at`, TRUE-division host-mirror arithmetic —
byte-match gated), packed tied head (`embd_packed`, the single largest decode
matmul at 1 B/weight), jagged-topology graph capture (per-owner cache POINTERS
fixed per layer; position via `*dpos`).

### The dense 12B is NOT the E-series (ground truth: GGUF + llama.cpp gemma4-iswa.cpp)

PL=0 (no AltUp/PLE) yet layer_output_scale + rope_freqs PRESENT (now keyed on
tensor presence, not has_ple); shared_kv_layers=0; per-layer head_count_kv
ARRAY (8 SWA / 1 global, period 6); **V-LESS GLOBALS** — attn_v absent on all
8 global layers, V = the RAW K projection, weightless-normed, never roped
("use_alternative_attention"). f32 embd (4 GB) not uploaded past a 2 GB budget
— packed embed gather + dp4a tied head instead. Transcode REDUCES 6.63→5.56 GB.

### The L11 kill — per-vector activation quant collapses on outlier-heavy models

12B decode diverged at the SECOND generated token: oracle-rank 205596, logit
gap 27.9. The operator-directed bisection (one strike per run): provenance
bisect — innocent; embed intercept — 0.000e+00, innocent; layer-norm telemetry
— smooth (directional damage, not magnitude); layer bisect vs the prefill
probe — noise 32 through L11's entrance, **214 inside layer 11**, the layer
whose TRAINED out_scale is 0.005 (the model flags its own activation
magnitudes); **the LIFT discriminator** — identical path in exact arithmetic
= 1.5e-4 f32 floors at EVERY boundary. Structure innocent; the per-VECTOR
int8 activation quant guilty: one outlier ate the maxabs scale and stripped
the mantissa from the other 3839 dims. E2B's tame activations never tripped it.

**Fix:** per-16-BLOCK activation scales — blocks align EXACTLY with the GEMVs'
128-bit `int4` loads (q8_v2: one chunk == one block; q4_v2: one chunk == two
blocks), one extra f32 mul per block, ZERO extra bus traffic. The llama.cpp
activation-quant pattern; the GPU twin of WIRE-CPU stage-1b block-Q8.
**Verdict: rank 205596 → rank 2 at gap 0.31 — a MEASURED top-2 near-tie**, the
legitimate top-1-trust currency (the DEC gate now prints oracle-rank + gap on
any flip; rank ≫ 2 = damage, rank ≤ 2 = currency). 12B gate 24/24; E2B 44/44 +
qwen3 regates green on the new kernels.

### Open after ETA.5b

1. **THE PPL GATE (release-blocking for paper 06)** — wikitext, both engines.
2. 12B parity floors: telemetry-mode this run (E2B-pinned gates scope to E2B);
   pin the 12B's own floors per telemetry-then-pin.
3. Q8-head/Q4-body transcode option for the 12B (keep Q6_K-source tensors at
   Q8): trades ~0.7 GB of reads for weight-quant fidelity — measure BOTH axes
   if the PPL gate shows a squeeze cost.

### ADDENDUM 2026-06-07 — THE GOLD INSTRUMENT: the reference frame itself was broken

The PPL-gate campaign ran to a reference-shattering conclusion. All runs on the
SAME llama-dumped token fixture (`_g4_12b_wiki_tokens.txt`, verified == HF
tokenizer.json 5431/5431):

| run | weights | engine | protocol | PPL |
|---|---|---|---|---|
| llama ladder | Q4_K_M GGUF | llama.cpp-CUDA | c512×8 | 505.91 |
| llama ladder | QAT-Q4_0 GGUF | llama.cpp-CUDA | c512×8 | 397.49 |
| SP per-row | QAT→OK_Q4 per-row | SP CUDA | c512 chunk-0 | 37,596 |
| **T2 GOLD** | **official bf16 safetensors** | **hand-written torch forward** | **c512 chunk-0, targets [256,512)** | **4.6776** |

The gold instrument (`_t2_manual_forward.py`, receipt `_t2_gold.log`) is a
from-scratch forward off the checkpoint + config alone: plain-multiplier
RMSNorm (NOT gemma-classic 1+w — read from the stored weights), V-less globals
(V = raw K projection, weightless-normed, never roped), partial rotary 0.25 via
the proportional factor table over θ=1e6 / SWA full-rot θ=1e4, attention scale
1.0, GeGLU tanh, sandwich norms, per-layer layer_scalar, tied head, softcap 30.
Scored targets sit AT max-logit (nll ≈ 0.001) — the model is healthy and
supremely confident on raw wikitext. **llama.cpp's gemma4 stack is ~100× off on
this model; every number above it in the table was measured against a broken
reference.** The "IT-on-raw-wikitext is honestly ~400-500" calibration claim in
§ETA.5b is OVERTURNED (left in place per no-silent-revision; this addendum is
the formal amendment).

Forensics so far (`_t2b_gguf_forensics.py`): the +1-norm converter theory is
DEAD (q/k_norm byte-identical GGUF↔safetensors); GGUF metadata sane; the three
weight sources carry three different layer_scalar sets (QAT retrain drift, not
corruption). The remaining fork — llama.cpp FORWARD vs GGUF CONVERSION — is
isolated by `_t2c_gold_on_gguf.py`: the gold arithmetic over the QAT GGUF's own
dequantized tensors (single-digit condemns the forward; ~400 condemns the
conversion). T2c is BLOCKED on a host memory wedge (Available=0 with ~9GB in
processes after the bake ladder; reboot required) and runs first next session.

Consequences for this contract: (a) the 34.2 tok/s shootout number stays
NON-CITABLE until SP passes a PPL gate measured against **4.68**, not 505;
(b) the per-row OK_Q4 verdict (37,596) remains directionally valid — ~95×
worse than its own source's llama number on the same frame — but its absolute
magnitude re-bases; (c) llama.cpp is DEMOTED from oracle to cross-check for
the gemma4 12B; the gold instrument is the reference until the fork resolves.

### RESOLUTION 2026-06-07 (post-reboot): THE GGUF ARTIFACTS ARE CONVICTED

The discriminator ran. Gold arithmetic, identical fixture and window:

| weights | gold forward | llama.cpp |
|---|---|---|
| safetensors (base) | **4.68** | — |
| Q4_K_M GGUF (same checkpoint as gold) | **271.18** | 505.91 |
| QAT-Q4_0 GGUF | **364.33** | 397.49 |

K-quant noise costs percents, not 58×. **Both GGUF artifacts are broken at
the weight level; llama.cpp's forward is exonerated** (the two engines agree
on every artifact). Hybrid class-isolation: GGUF + safetensors layer_scalars
= 97.07 (the GGUF scalar set alone carries a 3.75× damage factor); + norms =
113.6 (WORSE — norms are coherent with the GGUF weights, innocent); + embed =
113.7 (innocent). Mechanism: NO layer permutation (blk.L↔layers.L diagonal
exact, cross-layer cos ≈ 0); the damage is IN-PLACE with period-6 severity —
layers ≡ 0,1 (mod 6) at cos 0.93-0.97 vs safetensors, the other four at
0.24-0.70. Receipts: `%TEMP%\_t2c_{self,B,C,D,E2}.log`, `_t2e.log`, `_t2g.log`.

The ecosystem record corroborates: llama.cpp PR #24118 "Fix Gemma 4 Unified
conversion" (merged 2026-06-04), issue #22407 (extreme gemma4 quant PPLs),
and Unsloth's June-5 GGUF rebuild with "re-download mandatory" + "the bugs
were universal, affected all training packages." Our artifacts predate or
missed the rebuilt wave.

**Standing doctrine from this resolution:** the safetensors bucket
(4.68-proven) is the ONLY trusted gemma4-12B weight source. The 12B path
becomes sp_transcode-from-safetensors (bf16 front-end → OK_Q8 / OK_Q4B),
bypassing GGUF entirely; rebuilt-GGUF re-download is an optional cross-check.
The SP PPL gate target for the 12B is **single-digit vs 4.68**, with the
gold instrument (lattice `tests/gemma4_gold/`) as the reference engine.

### SPEC OK_Q4B — block-scaled Q4, the 12B's GPU vehicle (drafted 2026-06-07)

Status: SPEC. Implements the principled branch of the §ETA.5b fix fork. The
per-row OK_Q4 verdict stands (one Frobenius scale per 3840-weight row at 15
levels destroys the 12B distributionally even on grid-trained weights);
OK_Q4B replaces the ROW scale with PER-32-BLOCK scales while keeping the
container, sibling and arena conventions of the O_K family.

**Format.** Codes: int4 two's-complement in [-7, +7] (15 levels, symmetric,
zero-free — unchanged from OK_Q4), nibble-packed 2/byte, row-major, low
nibble = even column. Scales: ONE f16 PER 32-ELEMENT BLOCK along the row,
stored as a `.bscale` sibling tensor [rows × ceil(cols/32)] f16, row-major,
emitted adjacent to its parent (the §9 sibling-adjacency rule, same as
`.scale`). Rows whose cols are not a multiple of 32 pad the final block's
codes with zeros (scale computed over real elements only). New dtype id:
`SP_DT_OK_Q4B`; `.bscale` dtype `SP_DT_BLOCK_SCALE_FP16`.

**Quantization (transcoder).** Per block: `s = maxabs/7` computed in f32,
ROUNDED THROUGH f16 FIRST, then `code = clamp(round(w / s_f16), -7, +7)` —
codes are quantized against the STORED scale, never the ideal one (the same
store-then-derive discipline as the Frobenius lift; skipping it costs a
systematic half-ULP bias across 357M blocks). Source: the safetensors bf16
stream via `--st` (doctrine above). All matmul weights + the tied embed go
Q4B; norms/scalars/rope stay F32.

**Budget (RTX 2060 12GB, nvidia-smi-verified).** ~11.4B matmul params:
codes ≈ 5.7 GB + bscales ≈ 0.71 GB + F32 smalls ≈ 6.4-6.6 GB resident →
~5 GB headroom for KV/activations/logits/graph. No mixed-precision or
per-64 compromises required.

**Kernel (the dp4a alignment story).** The shipped q4_v2 GEMV consumes 32
codes (16 bytes, one 128-bit `int4` load) per chunk — exactly ONE OK_Q4B
weight block — and the shipped activation quant is per-16 blocks, so each
weight block spans exactly TWO activation blocks. The chunk loop splits its
dp4a accumulation into two 16-element halves:
`facc += wscale * (ascale_a * (f32)acc_a + ascale_b * (f32)acc_b)` —
two extra FMAs per 32 weights, ZERO extra code-bus traffic; the bscale
stream adds 1/16th of code bytes (f16, `__ldg`-cached, sequential).
Symmetric CPU dequant path lands in the bridge/oracle for parity
(`build_packed_q4b` + lift-exact reference).

**Gates (telemetry-then-pin, no silent revisions).**
1. `T_Q4B_ROUNDTRIP` — transcode→load→dequant bit-exact vs the transcoder's
   own stored grid (container correctness).
2. `M_GEMMA4_Q4B_PPL` — chunk-0 wikitext vs gold **4.6776** on the pinned
   512/[256,512) protocol. Expectation: low-single-% inflation (4.5 bpw,
   block-scaled, bf16 source); first run is TELEMETRY, the pin follows.
3. DEC top-1/oracle-rank currency on generation (rank ≤ 2 = currency).
4. **SHOOTOUT-2** — tg256 vs llama.cpp-CUDA re-run on the SAME protocol as
   §ETA.5b; the tok/s number becomes CITABLE only with gate 2 green.

**Harness prerequisites (found the hard way, 2026-06-07/08):** before any
regate, `test_gemma4_ppl` gets (a) score-only-positions — logits computed
only for [n_ctx/2, n_ctx), halving the head cost; (b) per-layer + head
progress prints — the 4-hour silent CPU-oracle bake on the 12B was
diagnosable only by working-set forensics; reference paths must narrate.

**Sequencing.** harness fixes → transcoder Q4B writer → bridge
`build_packed_q4b` + CPU parity → CUDA q4b chunk loop → gates 1-3 →
SHOOTOUT-2 → LEDGER + paper 06.

### CLOSED GREEN (2026-06-08): OK_Q4B end-to-end + SHOOTOUT-2 — paper 06 anchored

Built in one block: arena layout **v2** (formal migration in arena.c — optional
`bscale`/`bs_nblk`, NULL = v1 exactly, all producers audited zero-init);
`build_packed_q4b` (core bridge, `.bscale` sibling aliased from mmap);
CPU dequant + `matmul_arena` per-block paths; CUDA `DevTensor.bscale` +
`k_gemv_q4b_dp4a_v2` (q4_v2 chunk loop, per-32 f16 block scale replaces the
per-row scale — codes/loads/unpack/dp4a UNCHANGED) + `k_dequant_arena_q4b`
(exact f32 prefill dequant, no post-lift) + routing in
gemm_w/gemm_w_lift/gemv_w_packed.

**GPU PPL GATE (M_GEMMA4_CUDA_PPL): 5.1160 vs gold 4.6776 (+9.37%) — PASS.**
Triple-instrument agreement on the B1 artifact: sim 5.1259 / CPU artifact
gate 5.1259 / GPU 5.1160. The Q4B math is preserved on the device.

**SHOOTOUT-2 (tg256, SM 2100, B1 9.4 GB):** graph+dp4a **26.1 tok/s**,
graph 256/256 EXACT, int8 256/256 top-1, 24/24 gates. vs llama.cpp-CUDA
31.29 tok/s on its 6.6 GB Q4_K_M — which scores PPL 192-506 (broken
weights, 06-R8). Decomposition: SP effective decode bandwidth 245 GB/s vs
llama 207 GB/s (**+18% engine efficiency**); the artifact is 42% heavier
because it is the only mathematically intact 4-bit gemma4-12B in existence.
**The citable claim (LEDGER 06-R10): 26.1 tok/s at PPL 5.12 on a 12 GB
card — a point no other stack can produce at any speed. 06-R6's 34.2 is
formally RETIRED with its quality-failed artifact.** Headroom: B2 asym
(sim 5.01) shrinks nothing but buys quality; artifact-size reduction
(quality-budgeted Q4B widening, imatrix) is the future speed lever.

### ARTIFACT GATE GREEN (2026-06-08): the sovereign pipeline reproduces gold

**safetensors → `sp_transcode --st` → OK_Q8 `.sp-model` → gold arithmetic =
PPL 4.7396 vs gold 4.6776 → +1.33%, PASS** (8% telemetry floor; receipt
`%TEMP%\_t2h_gate.log`, instrument `_t2h_spmodel_gate.py` — parses the
container directly, dequants OK_Q8 as q·s/127, runs the proven forward;
67 s wall). Residual norms track the bf16 run digit-for-digit per layer.
The 11.9 GB artifact (`models/gemma4-12b-st.sp-model`) is VALIDATED as the
12B weight source; +1.33% is the measured Q8 cost on this model.

### Q4B RECIPE DECISION MATRIX (sim'd via the gold instrument, 2026-06-08)

Naive PTQ Q4 on gemma4-12B is expensive — the model is quantization-hostile
(this is WHY Google ships QAT). All sims: identical fixture/protocol, vs
gold 4.6776:

| recipe | PPL | Δ | VRAM |
|---|---|---|---|
| all sym-32 Q4B | 6.79 | +45% | 6.4 GB |
| sym-32 Q4B + Q8 down/embed | 6.29 | +34% | 8.3 GB |
| sym-16 Q4B + Q8 down/embed | 6.13 | +31% | 8.7 GB |
| asym-32 Q4B + Q8 down/embed | 5.86 | +25% | 8.7 GB |
| **B1: sym-32 Q4B gate/up ONLY + Q8 rest** | **5.13** | **+9.6%** | **~8.9 GB** |
| B2: asym-32 gate/up + Q8 rest | 5.01 | +7.0% | ~9.2 GB |

**SHIPPING RECIPE: B1** (`sp_transcode --st … --q4b-ffn`, engine `32e74ce`,
core dtype enums `e06eb7d`) — single-digit PPL, fits the 2060-12GB with
~3 GB headroom, and its kernel is a ~30-line delta on the proven q4_v2
dp4a chunk loop (per-32 weight-block f16 scale replaces the per-row scale;
codes/nibble layout unchanged). B2 asym is the documented upgrade (needs
per-block activation SUMS in k_quant_act_int8 + min-term FMA — llama's
"bsums" pattern). The B1 telemetry pin: gate at sim-confirmed ≈5.13 ±2%
once the in-engine artifact run lands.

**ECOSYSTEM ADDENDUM — the rebuilt GGUFs are STILL broken (2026-06-08):**
Unsloth's post-June-5 `gemma-4-12B-it-qat-UD-Q4_K_XL.gguf` (downloaded
2026-06-07 13:20, after the rebuild wave) scores **192.94** through the
gold arithmetic — better than the old wave's 364 but still ~41× above
gold. PR #24118 fixed projector configs, not the text-tower damage. The
GGUF lane remains DEAD for this model; Safetensors Direct is not just
doctrine, it is the only working path anyone has.

**Scope honesty:** this gate validates the ARTIFACT via the gold instrument
(python), not the in-engine C path. The in-engine M_GEMMA4 12B run was
KILLED at 331 CPU-minutes without output: the serial CPU oracle's scalar
dot (~80× slower than threaded torch on identical math) made the 512-ctx
12B run economically absurd, and whether it was minutes from finishing or
looping is UNDETERMINED — instrument before rerun (per-layer progress
prints, score-only-positions, optional bit-safe row-parallel OMP in
sp_matmul). The C forward itself is NOT in doubt — it is E2B-gate-proven
bit-faithful and was never tonight's variable. The in-engine 12B regate
lands together with the OK_Q4B gates after the harness fixes.
