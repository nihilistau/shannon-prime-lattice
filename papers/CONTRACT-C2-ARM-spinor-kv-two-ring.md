---
type: contract
title: "CONTRACT C2 — ARM memory: Spinor-KV inline compression + the two rings"
description: "Parent: RFC-001 §2. Builds on: C1 (the reducing .sp-model + arena swivel)."
tags: [contract, spinor, arm]
timestamp: 2026-06-06T19:03:57Z
resource: shannon-prime-lattice/papers/CONTRACT-C2-ARM-spinor-kv-two-ring.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# CONTRACT C2 — ARM memory: Spinor-KV inline compression + the two rings

**Parent:** RFC-001 §2. **Builds on:** C1 (the reducing `.sp-model` + arena swivel). **Status:** C2.1 COMPLETE (2026-06-03) — two-ring recall wired live + all three walls down (router/sinks/Optane-IOCP/quickselect/Ring-1-shrink); see §C2.1. **C2.4 CLOSED (2026-06-06): the v5 composed 32k finale COMPLETED (16.3 h, zero errors) and the NIAH verdict is MISS** — infrastructure proven at scale, retrieval quality at 64× selection budget not; see §C2.4-CLOSURE for the verdict, the config regression it exposed, and the diagnostic plan.
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

## C2.0.6 RECALL ROUTER SOLVED (2026-06-02) — ±1 random projection, harness `tests/c2_router_proj.c`

The open problem from C2.0.4/C2.0.5 (KSTE falsified as a router) is **closed**. Router shootout on the same adversarial needle+decoy set:

| budget | KSTE (64 B) | **±1 proj r=16 (32 B)** | ±1 proj r=32 (64 B) | ORACLE |
|---|---|---|---|---|
| **B=64** | cos 0.997, **0/8** needles | **cos 1.0000, 8/8, 0 decoys** | 1.0000, 8/8, 0 | 1.0000, 8/8, 0 |
| B=512 | 0.995, 3/8 | 1.0000, 8/8 | 1.0000, 8/8 | 1.0000, 8/8 |

**A ±1 (Rademacher) random projection of rank 16 (= 32 B/token, SMALLER than the KSTE 64-B signature) is ORACLE-PERFECT at B=64: 8/8 needles, cosine 1.0000, 0 decoys.** Johnson–Lindenstrauss preserves the inner product, so the projected dot ranks by true relevance — and the **±1 matrix keeps it INTEGER / Z_q-native (discrete, Lattice-pure — NOT the "dirty float" it was framed as).** (At larger B the projection picks up some decoys, but so does the oracle — decoys have small-positive true scores that softmax down-weights; cosine stays 1.0.)

**Design decision: the recall router is a per-token ±1 projection sidecar (r=16/32), stored alongside the Spinor/KSTE record.** Path B (NTT low-freq coarse score) is unnecessary and would low-pass-smear spiky needles (predicted; not pursued). **This unblocks System-2 usable context** (C2.0.5): Ring-2 stores the cold tail; the projection sidecar (tiny, in-RAM for all tokens) routes the top-B recall; the fetched Spinor blocks are reconstructed by the codec. Router (projection) and Compressor (Spinor/Tail-Slayer) are now cleanly separated.

## C2.1 — long-context recall gate spec (the C2.1 target; NOT yet wired)

**Honest basis:** the reconstructed block is the **lossy Spinor codec** (~3.5×/f32, real-model **29/31 argmax** per E_CPU_8 — NOT "lossless"; the 0.99996 was per-vector cosine, which did not carry to perfect top-1). So the pipeline has **two independent loss sources** the gate must separate: **(i) router loss** (fetched the right blocks? — the ±1 projection) and **(ii) compressor loss** (block fidelity? — Spinor/Tail-Slayer, ~6.5% argmax flips, router-independent).

- **G1 — NIAH retrieval-accuracy curve (isolates the router).** Plant one fact at depth ∈ {10,50,90}% of an N-token context; query; pass = model emits it. Sweep **N ∈ {2k, 8k, 32k}** (Qwen3-0.6B's *trained* window; beyond it = a separate extrapolation regime, flagged not gated). Gate: retrieval ≥ full-attention at budget **B ≪ N**; the measured **B(N)** = the recall-budget schedule / baton-pass boundary.
- **G2 — PPL deflection curve (compounded).** `deflection(N,B) = PPL[Spinor-KV + proj-recall@B] / PPL[full-f32] − 1`. Run **B=full-recall** to isolate the compressor floor, then **B<N** to add the router contribution. Gate: total deflection **< ~2%** to target N (loosened from the ~1% T_FRO_4/M_GEMMA4 bound since the KV path is now itself lossy).
- **The "boundary":** where, at fixed B, deflection crosses 2% as N grows (or where B must grow to hold it) — the *empirical* System-1→System-2 crossover, replacing the analytic Ncrit≈1–4k (C2.0.5).

**Prereqs before any 32k green gate — incremental ladder:** (1) **DONE (engine `67f4997`)** — ±1 projection sidecar wired into live `qwen3_generate_kv` + PARITY VERIFIED: recall OFF == `SP_RECALL_B`≥ctx == baseline tokens bit-identical (frozen-seed R, post-RoPE per-kv-head projection, recall-set = recent-W ∪ top-(B−W), integrated with the OpenMP attention threading; gated `SP_RECALL_B`/`SP_RECALL_R`/`SP_RECALL_W`). (2a) **DONE (engine `2e7f325`)** — two-ring spill/recall mechanism wired into live forward with a **mock RAM Ring-2**: sliding-W (recent-W in Ring-1, older spilled), per-token attention routing (old→Ring-2, recent→Ring-1), **parity PROVEN via poison** — Ring-1 kc/vc NaN-poisoned on window-exit, so `SP_RING2=1 W=8 B=512` == baseline bit-identical *only because* old tokens are fetched from Ring-2 (a stale Ring-1 read → NaN). Round-trip byte-faithful. pread>mmap decided (random recall). (2b) **TODO** — swap the RAM mock for real Optane E:/F: `ReadFile` (block-aligned), validated under (3). (3) **TODO** — G1/G2 curves on a REAL prompt + long context (the dummy `{1,2,3,4}` prompt is degenerate — need real tokens). Wire incrementally — the real-model path was fragile this session (the struct-divergence segfault). Bring up at N=2k–8k before the 32k edge.

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

---

## C2.1 COMPLETE — the two-ring recall system, wired + measured (2026-06-03)

C2.1 took the C2 measurements (±1 router proven in harness, Ring-2 recall byte-exact, Spinor-KV ~3.5× lossy) and **wired them into the live `qwen3_generate_kv` decode path**, then drove the three architectural walls down one at a time, each gated on the N=512 NIAH parity gauntlet (GEN_KV bit-parity + NIAH HIT on a real `837492` needle in the Alice haystack). All engine-side; commits in `shannon-prime-system-engine`.

**Step 1 — ±1 projection router sidecar** (engine `67f4997`): frozen-seed Rademacher R, post-RoPE per-kv-head projection, recall-set = sinks ∪ top-(B−W−sink) ∪ recent-W. Parity: recall-off / B≥ctx == full-attention baseline, bit-identical.

**Step 2a — two-ring spill/recall** (engine `2e7f325`): mock RAM Ring-2, parity proven via NaN-poison.

**Step 3 G1 — NIAH retrieval gate** (engine `7055964`, `tests/niah.c`): self-contained needle-in-haystack on the decode path, tokenized with the engine's own validated tokenizer (no Python). Boundary at N=512/d50: HIT to B=256 (2× KV) at r=16. Expanded sweep (r=32, all HIT): N=512 B=128 (4×) rescued; N=2k holds 2×/4×/**8×**; depth 10/50/90 all HIT (**no recency bias — global directional retrieval**). Finding: required budget B is an **absolute** token count, so achievable compression *ratio grows with context length*.

**Step 3 G2 — autoregressive PPL deflection** (engine `d56c1a7` harness + `e916365` sinks): PPL through the *decode* path (`qwen3_ppl_decode`, teacher-forced) so recall is exercised — `sp_perplexity`'s prefill path has no recall knobs. **First result FAILED (4× = +40%, 8× = +104%)**: hard top-B drops the softmax tail and evicts the StreamingLLM attention sinks. **Fix = pin first 4 tokens (`SP_RECALL_SINK`, Möbius cold-start, kept in Ring-1).** With sinks, N=2k: **2× = −0.71%, 4× = −0.92%, 8× = +0.69%** — all pass <2%, 2×/4× negative (sparsification denoises). Intelligence wall solved at 8×. 8k full-attn PPL baseline = 23.814 (recall+sink confirm pending).

**Step 2b — physical Optane Ring-2** (engine `2707f60` v0 / `fdc0f07` v1a / `e895ef4` v1b; module `src/backends/cpu/ring2_disk.c`): `FILE_FLAG_NO_BUFFERING` (hits the drive, not the OS page cache) + IOCP async. N=512 disk smoke HIT off F: Optane. **Latency arc: v0 48.71 µs (16-thread `ReadFile` contention) → v1a 18.86 µs (dedupe: per-layer union staging — blocks are per-token, one fetch serves all heads) → v1b 7.57 µs (IOCP deep-queue async).** 6.4× latency / 36× wall; 7.57 µs ≈ Optane media floor. v1b fixed a `0xC0000374` heap corruption (binding write handles to the IOCP broke the sync spill; fix = separate IOCP-bound read handles).

**Compute wall — O(N) quickselect** (engine `b7a1f92`): replaced the O(B·N) max-extract (the ~10-h-at-32k bottleneck) with median-of-three Hoare quickselect over [score,index] pairs. Set-equivalent (GEN_KV parity + NIAH HIT).

**Memory wall — Ring-1 window shrink** (engine `f8ea920`): `kc/vc`, when offloading, is a **(sink+W) ring buffer** per layer (`r1slot(s)=s<sink?s:sink+(s−sink)%W`). The router's `s<winlo` eviction ⟺ "overwritten by s+W in the ring" — ring + router agree by construction. Gated to `ring2_on` so baseline keeps the full cache (parity held). **N=512: 122.9 → 8.3 MB (15×); at 32k = 910×.**

### C2.1 honest scoreboard — all three walls down

| Wall | Mechanism | Proof | Honest caveat |
|---|---|---|---|
| **Compute** | O(N) quickselect router | GEN_KV parity, set-equivalent NIAH | win asymptotic (invisible @512) |
| **Intelligence** | Möbius sinks + ±1 router | 8× = +0.69% PPL deflection (N=2k) | confirmed @2k; 8k/32k pending |
| **Memory** | Ring-1 window + Optane two-ring | 910× cache shrink @32k, NIAH HIT @7.66 µs/read off Optane | **`projk` router index still full-P ≈ 940 MB @32k → net 32k RAM 7.5 GB → ~950 MB (~8×), projk-dominated; int8/int4 router quant is next** |

**FINALE (in progress):** NIAH N=32768, B=512 (4×), depth-50, disk on F: via IOCP, sinks=4 — now ~1–2 h (not ~10 h). Retrieval at 32k off physical NVMe at queue-depth latency with a 910× KV-RAM shrink — all three walls in one run. *(Outcome 2026-06-06: completed as v5; verdict MISS — see §C2.4-CLOSURE. Note the "4×" label here was the N=2048 sparsification frame; at N=32768, B=512 is a 64× selection budget — a regime no quality gate ever covered.)*

### C2.1 prefill/decode modes + compact-and-spill fusion (2026-06-03)

The recall system now has three decode modes, all parity-exact when off, additive/gated (proven paths untouched):

| Mode | Env | Prefill | Decode RAM | Best for |
|---|---|---|---|---|
| **Streaming** (default) | recall+ring2 on | recall during prefill, O(B·N) | window throughout (always-low-RAM) | the 32k headline |
| **Decode-only** | `SP_RECALL_DECODE_ONLY` (`a5e9b86`) | dense-exact in RAM | full cache during ingest, window at decode | fast exact ingest, RAM ok |
| **Fusion** | `SP_RECALL_FUSE` (`7896bc4`) | dense-exact in full-P buffer | buffer **freed** at boundary → window | exact ingest AND window decode RAM |

Fusion = dense-exact prefill in a full-P RAM buffer, then ONE bulk spill of the cold tail to Optane at the prefill→decode boundary, copy sinks/window into the (sink+W) cache, and free the prefill buffer. **Verified N=512** (boundary fired, needle off disk) and **timed N=8192** (51.4 min wall, 1.88 GB buffer freed, HIT `837492`, 5.35 M reads @ 10.62 µs). Upgrades paper-01 §3.7 future-work → result.

**Honest cost:** fusion prefill is exact O(N²) attention (recall off during ingest), so 32k dense-exact ≈ 18 h on one f16 core — the stock cost of exact attention, not a fusion defect, consistent with the ~1.34× throughput gap. The 32k **headline** therefore uses the streaming path (O(B·N), always-low-RAM); fusion's receipts are the 512 + 8k runs. R9 (streaming 32k) in flight; its retrieval/read-count/latency/wall-clock land in paper-01 §4 + abstract + EXPECTED + landing hero on completion.

---

## C2.2 COMPLETE — canonical math-core two-ring + dual-prime NTT fusion + the network tier (2026-06-04)

C2.1 lived engine-side. C2.2 **promoted the architecture into the canonical math-core** and closed the discrete-object claim at every storage scale. One day, fully gated; math-core `9c26475→54ee28b`, engine `005473d→57c9a53`.

**1. ARM into math-core (Stages A–D).** `core/arm/` fills the reserved L1 module slot: frozen ±1 Rademacher router (seed `SP_ARM_PROJ_SEED`), quickselect select, `sp_arm_r1slot`, and the **abstract Ring-2 backend in the L1 ABI** (`sp_arm_ring2_backend`: write/read/optional batched read/aligned-alloc hooks; portable stdio reference; `sp_arm_ring2_register` = the platform hook, registered backends are borrowed). The full two-ring (recall sidecar, Ring-1 sink+W ring, mock + backend Ring-2, dedupe staging, decode-only + compact-and-spill fusion modes) is wired into `qwen3_generate_kv`/`qwen3_ppl_decode` in their own TU (`core/forward/decode.c`) — **the only decode in the tree**: the engine's ~430-line duplicate was deleted, and engine binaries resolve the canonical decode at engine speed via the always-pulled-object dispatch seam (`cpu_overlay.c`: sp_matmul→OMP/AVX, AVX2 `sp_pr_resdot`). Run-gates `T_ARM_GENKV` (11 gates incl. registered-backend counting proof + identity-budget structural parity: B≥P ⇒ selection identity ⇒ **eviction is the poison — spill/fetch must be byte-exact or the sequence diverges**). Suite 21/21.

**2. Dual-prime NTT keystore fusion (stages 1–3 + SIMD).** Under `SP_NTT_KV` the K stream is **residues end-to-end**: K cached write-once post-RoPE as a dual-prime residue block (NKV·2N u32); score = residue dot ⊕ N⁻¹ ⊕ scalar Garner = exact centered ⟨q,k⟩ — coefficient-0 of the negacyclic correlation, **no inverse butterflies, permutation-invariant**. Bluestein keystore covers every pow-2 HD ≤ 256 (weights for the coefficient-0 functional derived *empirically* at init through the public `ntt_inverse` — convention-proof — and folded into the stored key). V stays f32 (never scored — fp is plumbing). `sp_pr_resdot` in its own TU with **deferred reduction (15 products accumulate exactly in u64 → one mod per 15)**; engine AVX2 override. Bit-exact gates `T_PR_KSTORE`/`_BLUE`/`_RESDOT` + fixture-native fusion run-gates. **Measured (qwen3_rt, engine kernels): f32 baseline 22.6 / NTT overlay 5.98 / fusion 15.68 → 18.35 tok/s after Barrett-SIMD (+17%), sequences identical; residual −16% = the per-token q-transforms (448 fwd NTT pairs), not the dot.**

**3. The storage/network tier — one discrete object at four scales.**
- **Optane dual-size** (engine `a0d4e8e`): two independent NO_BUFFERING+IOCP stores (8192 B K-residue / 4096 B V-f32), routed by stream, registered through the L1 hook. **Live F: proof: 16.25 tok/s, sequence identical to baseline** — residue blocks physically on NVMe mid-decode, back exact.
- **QUIC peer = Ring-2 backend** (Trick #8, engine `2aad7db`): 64-byte SPR2 header + the **raw untranslated u32 residue block** as the wire payload; one bi-stream per request (HoL-free); `read_batch` = concurrent streams (the IOCP analog). Gate `M_NET_RING2`: 8 KB K + 4 KB V byte-exact over a real loopback socket through the same fn-pointer surface the decode uses.
- **Two-process showpiece** (engine `57c9a53`, `sp_ring2_showpiece` + `SP_RING2_SERVE` daemon switch): canonical decode, NTT fusion + 6-slot Ring-1, remote process as THE Ring-2 store. **MEASURED over 127.0.0.1: 840 block writes + 2520 reads (504 batched flights) = 20,160 KB of raw dual-prime residue payload crossing the socket mid-decode — zero serialization/deserialization/fp translation — SEQUENCE IDENTICAL to the knobs-off baseline (1.46 vs 1.48 tok/s on the daemon tier's reference kernels: transport absorbed by compute).**

### C2.2 honest scoreboard

| Claim | Number | Proof | Caveat |
|---|---|---|---|
| One decode, every tier | engine = math-core `decode.c` at 22.62 tok/s | symbol-resolution seam; T_ARM_GENKV | dispatch shims must live in an always-pulled object |
| Fusion speed | 18.35 tok/s (84% of f32) | bit-identical sequences | residual = q-transform amortization (next lever) |
| Optane tier | 16.25 tok/s live F:, identical sequence | dual-size registered backend | 7.57 µs/read floor inherited from C2.1 |
| Network tier | 20.16 MB residues over QUIC, identical sequence | showpiece A/B logs | loopback; cross-host run pending |
| RAM tier | Ring-1 910× shrink @32k (C2.1) + 6-slot forcing function here | `f8ea920`; showpiece | projk index still full-P (router-quant owned) |

**The C2 thesis is now closed end-to-end: compute operand = cache line = disk block = wire packet — the same dual-prime residue object, byte-exact at every boundary, gated on real silicon and a real socket.** Remaining inside C2 scope: cross-host (non-loopback) run, projk router-index quant, q-transform amortization (CONTRACT-SPEED).

---

## C2.3 — bit-packed popcount router (SimHash) FIDELITY-GATED (2026-06-04)

The last full-P RAM resident was the r-float `projk` router sidecar (~940 MB @32k at r=32). `SP_RECALL_BITS=1` packs the SIGN of each Rademacher projection into ONE u64 per (pos,kvh) — **r=32: 128 B → 8 B (16×); r=64: 256 B → 8 B (32×); @32k the u64 sidecar is ~59 MB** (28 × 32768 × 8 kv-heads × 8 B) **vs ~940 MB r=32-float / ~1.88 GB r=64-float** — and candidate scoring becomes hardware `popcount(qsig ^ ksig)` (Hamming = the SimHash angle estimator). *(CORRECTION 2026-06-04: an earlier revision of this section said "→ ~29 MB (32×)" — that conflated the r=64 ratio with the r=32 baseline; 940/16 = 58.7 MB. The decode banner prints the computed sizes; trust the banner.)* math-core `92c07fe` (sp_arm_project_sig / sp_arm_select_sig + T_ARM_SIG), engine `3d2d2c3` (NIAH swivel harness).

**Fidelity gate (NIAH, N=512, W=64 sink=4, qwen3_rt OK_Q8 swivel, needle `837492` in wikitext):**

| Cell | f32 router | bits u64 r=32 | bits u64 r=64 |
|---|---|---|---|
| B=256 (2×) d10 | — | HIT | — |
| B=256 (2×) d50 | HIT | HIT (answer **identical** to f32) | — |
| B=256 (2×) d90 | — | HIT | — |
| B=128 (4×) d10 | — | HIT | — |
| B=128 (4×) d50 | HIT | HIT | — |
| **B=128 (4×) d90** | **HIT** | **MISS** (answered `839210`) | **HIT** |

**Verdict (honest, both directions):** the r=32 signature retains full retrieval at 2× compression at every depth, but LOSES the 4×-budget deep needle (just outside the recall window, where the candidate pool is largest and the r+1-valued Hamming scores tie densely) — a real SimHash resolution failure, since the f32 router retrieves that same cell. **r=64 — the SAME 8-byte signature, double the rows — restores full fidelity.** Production guidance: `SP_RECALL_BITS=1` + `SP_RECALL_R=64`. Per the arm.h contract this stays an overlay knob, never a default; **named remaining gate before any default-on: PPL deflection at bits-r=64** (retrieval proven; distributional deflection not yet measured). The structural fix beyond r=64, if a future regime needs it: Hamming-prefilter → exact-rescore shortlist, surfaced upstream rather than tuned silently.

## C2.4 — DISPOSITION OF THE COMPOSED 32k FINALE (2026-06-05): terminated at 44.7%, GATE REMAINS PENDING — NOT CLAIMED

Run v2 (AVX512-scan binary) reached pos 14,645/32,768 over 8.6 h with all
four axes live (NTT fusion + bits-r64 router + Optane dual-size + streaming
NIAH), zero errors. Operator terminated: a host restart killed the process
(it was owned by the agent shell tree), and the measured read-amplification
tail (CONTRACT-SPEED) put completion ~30 h out.

What the partial run PROVED:
- 8.6 h of saturated dual-store NO_BUFFERING+IOCP operation at the device
  ceiling (~528 MB/s, ~1 GB/token) — no deadlock, no leak, no drift.
- The AVX512 scan collapsed the routing wall: v1 was compute-bound (1.0
  core, ~70 h projected); v2 was I/O-bound — the CPU waiting on the drive,
  exactly as the architecture intends.
- The read-amplification physics now pinned in CONTRACT-SPEED.

What it did NOT prove: the single-log 32k needle retrieval under full
composition. That gate STAYS OPEN, deliberately sequenced AFTER the GQA
kv-head selection lever — fix the amplification first and the identical
gate costs ~2-3 h instead of ~30, while re-gating the lever's NIAH in the
same run. No partial number from this run may be quoted as the composed
32k result.

Ops lesson: multi-hour bakes are OWNED BY THE OS (schtasks ONCE), never by
the agent process tree — v2 died with an app restart at 44.7%.

**PPL DEFLECTION AT bits-r64 — THE NAMED GATE, MEASURED (2026-06-05, ppl_ar N=2048 warm=512 scored=1535, qwen3_rt OK_Q8 swivel, router-only by design — Ring-2 is byte-exact transport and cannot move PPL):**

| Config | PPL | deflection | verdict |
|---|---|---|---|
| baseline (recall off) | 12.68574 | — | — |
| bits-r64 B=1024 (2x) | 12.56238 | -0.97% | PASS (<2%) |
| bits-r64 B=512 (4x)  | 12.66996 | -0.12% | PASS (<2%) |
| bits-r64 B=256 (8x)  | 13.45711 | +6.08% | FAIL (<2% bar; f32 router was +0.69% here) |

**REGIME VERDICT (final for C2.3):** `SP_RECALL_BITS=1 SP_RECALL_R=64` is
production-admissible at budgets up to 4x — retrieval 6/6 (NIAH) AND
distributionally transparent (PPL within noise, slightly negative). At 8x the
1-bit resolution cost is real on BOTH gates' axis: the f32 router holds +0.69%
where bits-r64 deflects +6.08%. Production guidance: bits-r64 for <=4x;
f32 router (or a future Hamming-prefilter -> exact-rescore two-stage) for 8x+.
The estimator is free until you starve it. Both named C2.3 gates now closed;
the overlay remains a knob, never a default.

## DECISION (2026-06-06): v5 is the TERMINAL finale run; 4 GB slab DOCUMENTED-NOT-RUN

Operator call, economic discipline: the composed 32k finale has been killed
+ relaunched 4x chasing levers (v2 scan / v3 split / v4 overlap / v5 cache).
Each lever was real and is now SHIPPED + gated. But the C2.4 gate has stayed
PENDING for ~a week and the optimization treadmill costs operator time/money
with no banked result. STOP.

- v5 (KVSEL + bits-r64 + fusion + split-Optane + overlap + 2 GB LRU cache)
  RIDES TO COMPLETION untouched (schtasks SP_FinaleV5, self-owned). On
  FINALEDONE it CLOSES C2.4 with whatever hit-rate the teardown prints.
- The 4 GB / 8 GB slab is a KNOWN, CONFIGURABLE lever (SP_RING2_CACHE_MB).
  The absorption-vs-depth curve is already MEASURED at 2 GB (86/69/50/42%);
  scaling the slab widens the reuse horizon predictably. NOT re-run — the
  answer is known; paying to confirm it is the treadmill. Filed as the
  first config knob anyone tunes for production, gate-free (it's a cache
  size, parity is unaffected — T_CACHE_EXACT already proved that).
- NO MORE finale relaunches. NO agent poll-watching of bakes (that, not the
  machine, was the real cost — the run is free, the babysitting is not).
- The 2 GB measured run + its completed log IS the C2.4 evidence; the
  68% partial already proved indestructibility (8h, zero leak, RAM flat).

NEXT = the rest of the project (Stage Beta / Eta / Omicron), not more 32k.

## C2.4-CLOSURE (2026-06-06): v5 COMPLETED — NIAH verdict **MISS**. Gate closed on an honest negative.

**The receipt** (`D:\F\shannon-prime-repos\_finale32k.log`, `FINALEDONE`, `WALL_SECONDS=58674` = 16.30 h, exit 3):

```
[niah] MISS N=32768(actual=32768) depth=50% inj_tok=16366  B=512 W=- R=- RING2=1
       answer=" 1234567890.   = = = Optane = = =   Optane"
[ring2-optane] K-stream: 1353081713 reads, 26458.285 s, 19.55 us/read avg
[ring2-cache]  K-stream: 2741903500 hits / 1353081713 misses = 67.0% hit-rate
[ring2-optane] V-stream: 1353081713 reads, 26495.314 s, 19.58 us/read avg
[ring2-cache]  V-stream: 2741903500 hits / 1353081713 misses = 67.0% hit-rate
```

Secret was the default `837492` (scorer = `strstr`); the answer contains the
needle's *context* ("Optane", twice) but not the digits. Genuine retrieval MISS.

**What the run PROVED (the infrastructure thesis, at full scale):**
- 16.3 h of saturated dual-store NO_BUFFERING+IOCP with **zero errors, no
  deadlock, no leak**, clean teardown — completion of what v2 only sampled.
- **1.353 × 10⁹ device reads per stream** (K: 11.1 TB off F:, V: 5.5 TB off
  E:) at **19.55/19.58 µs/read** at queue depth (vs 7.57 µs single-stream
  best — the QD tax, now measured).
- The 2 GB LRU temporal cache absorbed **67.0% on both streams** (2.74 × 10⁹
  device reads avoided each) — consistent with the measured 86/69/50/42%
  absorption-vs-depth curve at full 32k depth mix.
- Ring-1 shrunk 482× (15.6 MB vs 7.5 GB); NTT-KV fusion ran exact-score
  (residue dot + Garner) for the entire run at 32k.

**What it DISPROVED, and the config regression it exposed (no spin):**
1. **v5 did not run the declared composition.** The script header says
   "KVSEL + bits-r64" but that line is hand-written prose. The env receipts:
   `_finale32k.ps1` (v2) set `SP_RECALL_BITS=1 SP_RECALL_R=64`; those lines
   were **dropped at v4 and never restored** — v5's env block has neither.
   `SP_RECALL_KVSEL` defaults OFF (`core/forward/decode.c:89`) and was never
   set in ANY finale script. niah's own knob-echo proves the as-run config:
   `[recall] sidecar ON: r=16 B=512` — the **f32 r=16 router**, our
   lowest-resolution selector. This is also why the wall was 16.3 h, not the
   predicted ~2–3 h: the read-amplification lever was never engaged.
2. **The budget regime was never gated.** B=512 at N=32768 is a **64×
   selection ratio**. Every retrieval/quality gate on record (NIAH 6/6, PPL
   +0.69%) was at N=2048, i.e. 2×–8×; §C2.3's own verdict bounds bits-r64 at
   ≤4× and puts the f32 router at its +0.69% boundary at 8×. 64× is an
   extrapolation no gate covered.
3. **No model-ceiling control exists.** There is no full-attention 32k NIAH
   baseline for Qwen3-0.6B; "the router diluted at 64×" and "a 0.6B model
   cannot do 32k NIAH at all" are not yet separable. (The answer shape —
   correct format, generic digits, needle-context words present — is
   consistent with either.)

**Lesson (banked):** a runner's banner must echo `getenv`, never aspiration.
niah's knob-echo line (`B=%s W=%s R=%s`) is what caught the regression; the
script header is what hid it for three revisions.

**Disposition (operator call, 2026-06-06):** C2.4 closes AS A MISS per the
standing decision ("whatever the teardown prints"). NO Optane relaunch. A
**RAM-only diagnostic ladder** (N=2k/4k/8k/16k, B=512, `SP_RING2=1` mock RAM
store — minutes per rung, zero device cost) localizes where retrieval breaks
on the budget-ratio axis before any further finale spend. Paper 01 releases
on the **512-position-proven** Optane HIT + 910× shrink + PPL numbers; the
32k needle is an open diagnostic, not a claim. Public README corrected the
same day (it had pre-claimed the 32k HIT ahead of the ledger — that violates
the series' own rule and is now fixed).

**Ladder results (2026-06-07, `_diag_ladder.log`, B=512 RAM Ring-2,
depth-50):** 2k **HIT** · 4k **MISS-by-one-digit** (correct format, one digit
off) · 8k **HIT** · 16k **MISS** (model emitted the cliché "123456" guess —
a clean retrieval failure, not a formatting one). Read: the budget-ratio axis
is a NOISY MARGIN through 8k (4× → 16× selection budget) and a real break by
32× (16k). The 64× budget at the 32k finale was past the cliff edge before the
config regression even entered. Quality work therefore targets the selection
budget (B vs N scaling, e.g. B∝N or two-stage re-rank), not more finale spend
at fixed B=512. Host note: the ladder + finale left the box in an
Available=0 memory wedge (driver-pinned pages; reboot) — budget a reboot into
any post-bake session plan.
