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
