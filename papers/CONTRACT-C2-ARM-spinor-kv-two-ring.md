# CONTRACT C2 — ARM memory: Spinor-KV inline compression + the two rings

**Parent:** RFC-001 §2. **Builds on:** C1 (the reducing `.sp-model` + arena swivel). **Status:** DRAFT + first measurement landed.
**One line:** make the KV/memory path the PPT-ARM envelope — inline Spinor-block KV compression (Ring 1), Ring-2 offload/disk-recall with residual/CRT bandwidth bypass, a System-1/System-2 regime split with a crossover oracle — and **measure the real numbers** (the headline ~120× is `[TARGET]`, not assumed).

> Discipline: gate each piece on ITS OWN metric (compression ratio, recall cost), never on assembled-system tok/s (PPT-LAT-STATE §0). The headline numbers are the point AND are unmeasured — measure before believing.

---

## C2.0 FIRST MEASUREMENT (landed 2026-06-02) — the honest Spinor-KV ratio

The frozen Spinor block (`sp/spinor_block.h`, LAYOUT v1) is **63 B = 7 vht2_header + 55 int8 mobius_body anchor coeffs + 1 CRC-8**. Per KV head-vector: `NBLK = ceil(HD/55)` blocks.

| HD | NBLK | Spinor bytes | f32 KV | ratio /f32 | /f16 |
|---|---|---|---|---|---|
| 64  | 2 | 126 | 256  | 2.03× | 1.02× |
| 128 | 3 | 189 | 512  | 2.71× | 1.35× |
| 256 | 5 | 315 | 1024 | 3.25× | 1.63× |

**What the block IS (canonical):** `Spinor 63-byte KV-cache block = VHT2 anchor projection + Möbius reorder + int8-quantized anchors + CRC-8 trailer + 0xA5 sentinel`. One ARM Cortex-X2 cache line. The FROZEN on-wire KV record format (`spinor_block.h`, LAYOUT v1). The encode does a **VHT2 anchor projection** of each ≤55-element chunk, Möbius-reorders the anchors, int8-quantizes them into `mobius_body[55]`, CRC-8 over header‖body.

**CORRECTION (2026-06-02, against canonical `PPT-LAT-Theory.md`):** there are **TWO distinct KV-compression overlays — I measured the wrong one for the headline.**
- **(a) KSTE 64-byte signature** (`core/kste/kste_encode.c`, E_CPU_6 / SP_KSTE_KV): maps R^d → **64 bytes regardless of d** (8 anchors + 55 residuals = top-coefficients of the VHT2/Möbius transform). This is the **~130× headline** (theory §3.4, T2, T8.2) — **LOSSY, valid up to ⪯_d-equivalence** (a dominance/dedup signature, NOT a reversible codec). **Production, 21/21 KSTE gate** (theory §10).
- **(b) `sp_spinor_encode_vec`** (`vht2/spinor_block.c`, E_CPU_8 / SP_KV_SPINOR): dimension-preserving multi-block int8, `NBLK=ceil(HD/55)`, **~2–3×/f32** (HD256 3.25×), more faithful, deterministic CRC decode. **This is what the earlier measurement reported — the wrong primitive for the 130× headline.**

Both are real and trade **fidelity for ratio**. The 130× requires the lossy KSTE signature; the ~3× is the faithful codec. **C2 must decide which the KV path uses** (and whether attention-on-signatures at ⪯_d-granularity is acceptable), then measure end-to-end accuracy. [Measurement of (b) PROVEN; (a) is theory-Production via the KSTE gate, not yet re-measured here.]

**Where 120× would actually come from (the C2 investigation, [TARGET]):** the per-vector int8 block alone cannot give 120×. Candidates to investigate, each gated:
1. **True anchor-basis compression** — if the 55 `anchor_coeff` are a *low-rank/sparse basis* that reconstructs HD ≫ 55 elements (not 1 int8/element), the ratio rises with HD. Need to confirm whether the encoder is 1:1 quant (current, ~3×) or a genuine basis projection.
2. **Ring-2 effective-context ratio** — "120× context" may mean *effective context vs in-RAM footprint*: with Ring-2 disk/Optane offload, the in-RAM KV stays bounded while context grows ~unbounded → the "120×" is an effective-context multiplier, not a per-vector byte ratio.
3. **Aggressive sub-int8** (2-bit anchors / shared exponents) — a denser body.
**Do not claim 120× until one of these is measured.** The current honest headline is ~3×/f32 lossy-deterministic.

---

## C2.0.1 MEASURED (2026-06-02) — both overlays, math-core harness `tests/c2_kv_measure.c`

Built gcc -O2 against `vht2 + kste` only (no model). Representative K head-vectors (σ=2.0 gaussian + spike channels). **This closes gate C2_KV_RATIO and the fidelity side of C2_120X_INVESTIGATION.** Reproduce (from `shannon-prime-system/`):
```
gcc -O2 -std=c11 -Iinclude tests/c2_kv_measure.c \
    core/vht2/spinor_block.c core/vht2/vht2.c core/vht2/mobius_reorder.c \
    core/kste/kste_encode.c -lm -o c2_kv_measure && ./c2_kv_measure
```

**(a) `sp_spinor_encode_vec` — faithful, dimension-preserving (in-RAM 63 B/block, NBLK=⌈HD/55⌉):**

| HD | NBLK | spinor B | ratio /f32 | ratio /f16 | maxAbsErr | RMSE | cosine |
|---|---|---|---|---|---|---|---|
| 64 | 2 | 126 | 2.03× | 1.02× | 0.046 | 0.025 | 0.999955 |
| 128 | 3 | 189 | 2.71× | 1.35× | 0.044 | 0.018 | 0.999970 |
| 256 | 5 | 315 | 3.25× | 1.63× | 0.052 | 0.020 | 0.999963 |
| 512 | 10 | 630 | 3.25× | 1.63× | 0.049 | 0.015 | 0.999975 |
| 1024 | 19 | 1197 | 3.42× | 1.71× | 0.055 | 0.014 | 0.999977 |
| 2048 | 38 | 2394 | 3.42× | 1.71× | 0.043 | 0.012 | 0.999982 |
| 4096 | 75 | 4725 | 3.47× | 1.73× | 0.056 | 0.013 | 0.999980 |

→ **The faithful codec asymptotes at ~3.5×/f32 and only ~1.0–1.7×/f16, at very high per-vector fidelity (cosine ≥ 0.99996).** It is NOT a 120× scheme and never will be — it is 1 int8/element + a per-block scale. **Sobering for the north-star gate:** a production KV cache is usually f16, so the real win over the baseline is only ~1.4–1.7× at typical HD.

**CORRECTION (real-model measured, supersedes my "top-1-safe" optimism above):** the high per-vector cosine does NOT carry to perfect end-to-end top-1. The engine gate **E_CPU_8 (`test_kv_spinor`, Qwen3-0.6B, scalar)** run live 2026-06-02: **argmax = 29/31, KL mean = 2.300e-02, max = 2.585e-01 — PASS** (the gate is a *bounded-divergence* gate: KL mean ≤ 2.0e-1, not bit-exact). So **Spinor-KV is a LOSSY overlay that flips ~6.5% of argmax tokens** accumulated over 28 layers — it is NOT bit-exact to the f32-KV baseline. This means the "bit-exact is table stakes" floor (RFC §0) holds for the *weight* path and gate-OFF, but the *Spinor-KV overlay itself trades a small top-1 divergence for the ~3.5× ratio.* Honest envelope choice (see C2.0.3): Ring-2 can offload *faithful f32/decoded* KV bit-exact (memory tiering, zero compression loss) OR Spinor-compressed KV (3.5× smaller, 29/31 argmax) — two distinct points, choose per accuracy need.

**(b) `sp_kste_encode` — lossy ~130× signature (64 B regardless of HD):**

| HD | kste B | ratio /f32 | distinct-fraction @scale 65536 | @scale 2 |
|---|---|---|---|---|
| 128 | 64 | 8× | 1.0000 | 1.0000 |
| 1024 | 64 | 64× | 1.0000 | 1.0000 |
| 2048 | 64 | **128×** | 0.9995 | 1.0000 |
| 4096 | 64 | 256× | 0.9990 | 1.0000 |

→ **The ~130× headline = the KSTE signature at HD ≈ 2048** (ratio = HD/16). It is **lossy up to ⪯_d — a dominance/dedup/routing signature, NOT reconstructable attention KV.** Discrimination is ~1.0 even at the forward-path scale 65536: my hypothesis that the i16-clamp (M.5 gotcha) would collapse discrimination was **WRONG for the continuous-K domain** (the order-statistics still separate distinct vectors; the clamp only bit in the *token-ID* domain where IDs cluster). So KSTE-KV is a valid signature here — but you cannot run attention on it directly.

## C2.0.2 The decisive conclusion (now measured, not speculated)

**Neither single overlay gives "120× at bit-exact, reconstructable KV."** The faithful codec is ~3.5×/f32; the 130× one is a non-reconstructable signature. Therefore the "~120× inline KV → unlimited context" headline is **NOT a per-vector codec property** — it must be **(faithful ~3.5× reconstructable KV) × (Ring-2 effective-context multiplier)**, where Ring-2 disk/Optane offload keeps the in-RAM KV window bounded while context grows. **This makes Ring-2 recall the load-bearing piece for the headline, not the per-vector block.** The remaining C2/C3 work is therefore: measure the Ring-2 recall cost vs recompute (C2_RING2_RECALL) and the effective-context multiplier — that is where the "unlimited context" number actually lives. (Candidate #1 from C2.0 — "anchor-basis reconstructs HD≫55" — is **falsified**: the codec is 1 int8/element, confirmed by the linear NBLK=⌈HD/55⌉ scaling.)

## C2.0.3 MEASURED (2026-06-02) — Ring-2 offload/recall, harness `tests/c2_ring2_measure.c`

Built gcc -O2 against the Spinor codec only (no model). Models the KV cache as Spinor blocks with a bounded in-RAM window (W most-recent tokens) and the cold tail spilled to a file (tmpfs/ext4 page-cached = a near-RAM analogue for byte-addressable Optane E:/F:, STATE §6.1). Reproduce:
```
gcc -O2 -std=gnu11 -D_POSIX_C_SOURCE=199309L -Iinclude tests/c2_ring2_measure.c \
    core/vht2/spinor_block.c core/vht2/vht2.c core/vht2/mobius_reorder.c -lm -o c2_ring2_measure && ./c2_ring2_measure
```

**(1) C2_RING2_RECALL gate — PASS.** Spill → recall → decode is **byte-identical** to the in-RAM decode (2000/2000 recalled tokens, both configs). Trivially robust by construction (disk is a transparent byte store; Spinor decode is deterministic) — but now proven, not assumed.

**(2) Recall cost (qwen3-0.6B-like: L28, NKV8, HD128 → 84.7 KB/token Spinor):** read ~10.5 µs/token (~8 GB/s, page-cached), Spinor-decode ~2.0 µs/block. **Recall = read 84.7 KB compressed + decode, no weights, no matmul.** The recompute alternative re-runs the layer QKV projection for that token (hidden·KVD MACs) and needs the weight matrices resident — strictly heavier. So for KV, recall ≪ recompute. *Honest caveat:* the ~8 GB/s is page-cached ext4; cold Optane read is ~2–7 GB/s at ~few-µs latency (still ≫ recompute), spinning disk far worse — re-measure on the real E:/F: tier.

**(3) Effective-context multiplier — THIS is the honest "unlimited context" headline.** With a 512-token in-RAM window (~43 MB) and the cold tail on Optane:

| Optane budget | total tokens | in-RAM | effective-context multiplier |
|---|---|---|---|
| E: 16 GB | ~203 k | 512 | **397×** |
| F: 32 GB | ~406 k | 512 | **794×** |
| E+F: 48 GB | ~609 k | 512 | **1190×** |

→ **The "~120×" headline is conservative — even a 16 GB Optane offload at a 512-token RAM window gives ~400× effective context.** The multiplier is a capacity ratio (RAM_window : Optane), reached at a *fraction* of the available budget. Candidate #2 from C2.0 ("effective-context vs in-RAM footprint") is **CONFIRMED as the real source of the headline**, far exceeding the per-vector codec's ~3.5×.

**The honest scope limit (state it, don't bury it).** Ring-2 solves the **memory wall** (unlimited context at bounded RAM), NOT the **compute wall**: full attention over N tokens is still O(N) per step / O(N²) prefill, and naively every step would recall the whole history. Turning the storage multiplier into *usable* context requires a sparse/recalled-attention pattern — Gemma-style SWA windows, the Fibonacci φ sub-sampling eviction (§4.3 / `SP_KV_FIB`), or retrieval — so that only a bounded, relevant subset is recalled per step. The 794× is the **storage** multiplier; the usable-context multiplier is bounded by the recall pattern, which is the next design piece (C2.1 Ring-2 + the System-1/2 oracle deciding when to spill/recall).

## C2.0.4 MEASURED (2026-06-02) — sparse-recall fidelity + the System-1/2 oracle, harness `tests/c2_sparse_recall.c`

The Ring-2 multiplier is *storage*; usable context needs recalling only a budget B≪N tokens per query that reproduce full attention. Built gcc -O2 (kste only). Needle-in-haystack synthetic: N=4096, HD=128, a recent-coherent cluster (last 64) + 8 planted distant q-aligned "needles" + diffuse background; metric = cosine(o_pattern, o_full) and needles-captured. Reproduce: `gcc -O2 -std=gnu11 -Iinclude tests/c2_sparse_recall.c core/kste/kste_encode.c -lm -o c2_sparse_recall && ./c2_sparse_recall`.

| budget B | SWA (last B) | PHI (Fibonacci) | RECENT+PHI | KSTE-guided | ORACLE (top-B) |
|---|---|---|---|---|---|
| 64 | 0.9967 (0/8) | 0.9515 (0/8) | 0.9956 (0/8) | 0.9967 (0/8) | **1.0000 (8/8)** |
| 128 | 0.9967 (0/8) | 0.9515 (0/8) | 0.9967 (0/8) | 0.9985 (4/8) | 1.0000 (8/8) |
| 256 | 0.9967 (0/8) | 0.9842 (1/8) | 0.9967 (0/8) | 0.9990 (5/8) | 1.0000 (8/8) |
| 512 | 0.9967 (0/8) | 0.9842 (1/8) | 0.9843 (1/8) | **0.9994 (6/8)** | 1.0000 (8/8) |
| 1024 | 0.9967 (0/8) | 0.9842 (1/8) | 0.9843 (1/8) | 0.9994 (6/8) | 1.0000 (8/8) |

**Findings (honest):**
1. **Attention is sparse → the ORACLE recalls full attention at B=64 (cosine 1.0000, 8/8 needles).** The usable-context premise holds: *if* you can cheaply identify the high-mass tokens, a tiny budget reproduces full attention, so Ring-2's hundreds-× storage becomes usable context. The whole game is the **recall router**.
2. **Query-agnostic patterns (SWA, φ) capture the recent cluster but MISS the distant needles (0–1/8).** Their ~0.99 cosine is misleadingly high — it comes from recent+background mass; on a genuine long-range-retrieval task (needles matter) they fail. **Pure Fibonacci-φ is the *worst* recall router (0.95, 0–1/8)** — it is built for *uniform coverage*, not for finding peaked mass. (φ stays the right tool for *eviction* coverage, §4.3 — a different job.)
3. **KSTE-signature-guided recall LOOKED best (4–6/8) — but the adversarial test (C2.0.4.1) FALSIFIES it as a router.** The clean-test win was an artifact: needles were the *only* histogram-distinctive vectors, so ranking by KSTE tier-0 distance accidentally surfaced them.
4. **No cheap pattern hits oracle quality.** Closing the gap needs a genuine *directional* cheap score (a low-rank/projected dot-product, an NTT-attention coarse pre-score, or a small stored projection per token) — that is the open recall-router problem. **KSTE is NOT a candidate (see below).**

### C2.0.4.1 ADVERSARIAL (2026-06-02) — KSTE is NOT a directional recall router [harness `tests/c2_kste_router_adv.c`]

Planted 32 **permuted decoys**: each = a needle's components randomly shuffled → **identical order-statistics histogram, ~zero dot product with q** (mean true score: needle 16.30 vs decoy 0.47). If KSTE routed on *direction* it would ignore them.

| | KSTE-router top-B | ORACLE top-B |
|---|---|---|
| **mean KSTE tier-0 L1 dist → q** | needle **985.2** vs decoy **937.4** (decoys *closer*!) | — |
| B=512 | cos 0.9986, **6/8 needles, 21/32 decoys** | cos 1.0000, 8/8, (decoys down-weighted by softmax) |

**Verdict: the KSTE tier-0 order-statistics signature cannot distinguish a needle from a zero-alignment permuted decoy** — it ranks decoys *as close to q* as the needles, and pulls 21 of 32 into the budget. Order statistics are a *histogram* (permutation-invariant in dimension), but dot-product is *directional* — so KSTE is structurally the wrong tool for recall routing. It remains valid for its designed job (dedup/dominance signature, §4.2a). **The recall router must be a directional cheap-score; KSTE is ruled out.** *(This corrects an earlier overstatement — "KSTE best practical router" — caught by adversarial verification, not theory.)*

## C2.0.5 The System-1/System-2 crossover oracle (DERIVED from the measured numbers)

The regime split is now parameterized by measurement, not asserted. Let `pt` = per-token KV bytes, `RAMbudget` = KV RAM cap, `W` = recent window, `B` = recall budget, `Nctx` = context length.

- **System-1 (flat cache, full attention).** RAM = `Nctx·pt_f32`; compute = full attention O(Nctx)/step. Best while context is small — no compression/offload/recall overhead.
- **System-2 (Spinor Ring-1 window W + Ring-2 offload + recent-W ∪ KSTE-routed-B recall).** RAM = `W·pt_spinor` + `Nctx·(64 B signature/head)` [tiny index]; compute = attention over `W+B` + recall I/O of B tokens; context unbounded (Ring-2).

**Crossover rule (switch System-1 → System-2 when `Nctx > Ncrit`):**
`Ncrit = min( RAM-driven cap , compute-crossover )` where
- RAM-driven cap = `RAMbudget / pt_f32` (when the flat f32 cache no longer fits — *hard* switch). For qwen3-0.6B-like (`pt_f32`=224 KB) at an 8 GB KV budget ≈ **36 k tokens**; with Spinor-in-RAM (`pt_spinor`=84.7 KB) ≈ 99 k before offload is forced.
- compute-crossover = `(W+B)·k` — System-2's sparse attention over `W+B` beats System-1's full attention over `Nctx` once `Nctx ≳ W+B` plus recall overhead. With the measured best budget `W≈64, B≈512` (KSTE-router knee), this is **~1–4 k tokens**.

So: **stay System-1 below ~1–4 k tokens; switch to System-2 above** (and System-2 is *forced* by RAM at tens of k tokens). **The load-bearing dependency the oracle inherits:** System-2's *quality* at large Nctx is bounded by the recall-router fidelity (KSTE 6/8 today) — so the oracle must also expose a *quality floor*: if the router can't hit a target needle-capture, widen B or fall back to a denser recall. [DESIGN — oracle rule derived from measurement; the router-fidelity gap is the open item.]

---

## C2.1 Scope (the contract)

- **Ring 1 — inline Spinor KV.** Each cached K/V head-vector encoded to NBLK Spinor blocks on write, decoded on read during attention. Already wired in `forward.c` (SP_KV_SPINOR, gemma3/qwen3 decode path; E_CPU_8). **C2 task:** wire it into `qwen36_forward`'s GDN+full-attn KV (currently plain f32 KV), and report the round-trip determinism + ratio.
- **Ring 2 — offload/recall.** Spill committed Spinor blocks to the **Optane tier (E:/F:)** — near-RAM latency keeps "context beyond RAM" fast (PPT-LAT-STATE §6.1). Residual/CRT reconstruction for cheap recall + multi-device residue exchange. [DESIGN]
- **System-1 / System-2 + crossover oracle.** System-1 = small-ctx fast path (skip compression/offload overhead); System-2 = large-ctx Spinor+Ring-2; oracle switches by ctx/bandwidth/occupancy. [DESIGN; prior SP design]
- **fp16 swivel.** The loader can expand to an fp16 runtime container (arch_struct `preferred_precision=FP16` + `sp_matmul` `g_f16_act`), halving activation/working RAM, matching native fp16 compute. Orthogonal to the on-disk codec (C1). **C2 task:** expose an explicit swivel flag + measure the RAM delta + confirm top-1 unchanged.

---

## C2.2 Gates (each on its own metric)

- **C2_KV_RATIO** — report measured Spinor-KV bytes vs f32/f16 KV per head-vector + aggregate over a real context. (Landed: ~3×/f32 for the current int8 block.)
- **C2_KV_DECODE_DETERMINISM** — Spinor encode→decode round-trip is deterministic (CRC-valid); decoded-KV forward is a *bounded-divergence* overlay, not bit-exact. **[PASS 2026-06-02, live E_CPU_8 `test_kv_spinor` Qwen3-0.6B scalar]: argmax 29/31, KL mean 2.300e-02 (gate ≤ 2.0e-1), 7/7 checks.** Regression invariant (gate OFF == f32 forward bit-identical) also holds. *Honest:* Spinor-KV flips ~6.5% argmax — lossy, not bit-exact; the bit-exact floor is the weight path + gate-OFF, not the Spinor-KV overlay. (qwen36 wiring still pending — C2.1.)
- **C2_RING2_RECALL** — Ring-2 offload + recall reproduces the in-RAM result bit-exact; report recall latency vs recompute. **[PASS 2026-06-02, C2.0.3]** 2000/2000 byte-identical; recall ~10 µs/token + ~2 µs/block decode (page-cached), ≪ recompute; effective-context multiplier ~400× (16 GB) … ~1190× (48 GB) at a 512-token RAM window. *Follow-on:* re-measure on the real Optane tier; pair with a sparse-recall pattern (the storage multiplier ≠ the usable-context multiplier — see C2.0.3 scope limit).
- **C2_FP16_SWIVEL** — fp16 runtime container: top-1 unchanged vs f32 swivel; report working-RAM reduction. [DESIGN]
- **C2_120X_INVESTIGATION** — determine which mechanism (anchor-basis / Ring-2 effective-context / sub-int8) yields the headline, or honestly restate the achievable KV-compression number. **No 120× claim without a measurement.**

---

## C2.3 Why this is the decisive contract

C1 proved the reducing weight artifact + the swivel. C2 is where the **PPT-ARM value thesis is proven or broken**: if the achievable KV compression + Ring-2 effective-context + fp16 swivel + integer-pipe speed (HX.3b 1.04×) compose to beat the 40-tok/s bar at long context, the project is justified. The first measurement already corrected the headline from "120× per-vector" to "~3×/f32 per-vector, deterministic-lossy" — the rest of C2 finds the real envelope number, honestly.
