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

**Finding:** the current per-vector Spinor encoding is **lossy int8 (one int8 anchor/element), ~2–3× over f32 (~1–1.6× over f16), with a deterministic CRC-checked decode** (bit-exact decode, NOT lossless KV — gate E_CPU_8). **This is NOT 120×.** [PROVEN measurement.]

**Where 120× would actually come from (the C2 investigation, [TARGET]):** the per-vector int8 block alone cannot give 120×. Candidates to investigate, each gated:
1. **True anchor-basis compression** — if the 55 `anchor_coeff` are a *low-rank/sparse basis* that reconstructs HD ≫ 55 elements (not 1 int8/element), the ratio rises with HD. Need to confirm whether the encoder is 1:1 quant (current, ~3×) or a genuine basis projection.
2. **Ring-2 effective-context ratio** — "120× context" may mean *effective context vs in-RAM footprint*: with Ring-2 disk/Optane offload, the in-RAM KV stays bounded while context grows ~unbounded → the "120×" is an effective-context multiplier, not a per-vector byte ratio.
3. **Aggressive sub-int8** (2-bit anchors / shared exponents) — a denser body.
**Do not claim 120× until one of these is measured.** The current honest headline is ~3×/f32 lossy-deterministic.

---

## C2.1 Scope (the contract)

- **Ring 1 — inline Spinor KV.** Each cached K/V head-vector encoded to NBLK Spinor blocks on write, decoded on read during attention. Already wired in `forward.c` (SP_KV_SPINOR, gemma3/qwen3 decode path; E_CPU_8). **C2 task:** wire it into `qwen36_forward`'s GDN+full-attn KV (currently plain f32 KV), and report the round-trip determinism + ratio.
- **Ring 2 — offload/recall.** Spill committed Spinor blocks to the **Optane tier (E:/F:)** — near-RAM latency keeps "context beyond RAM" fast (PPT-LAT-STATE §6.1). Residual/CRT reconstruction for cheap recall + multi-device residue exchange. [DESIGN]
- **System-1 / System-2 + crossover oracle.** System-1 = small-ctx fast path (skip compression/offload overhead); System-2 = large-ctx Spinor+Ring-2; oracle switches by ctx/bandwidth/occupancy. [DESIGN; prior SP design]
- **fp16 swivel.** The loader can expand to an fp16 runtime container (arch_struct `preferred_precision=FP16` + `sp_matmul` `g_f16_act`), halving activation/working RAM, matching native fp16 compute. Orthogonal to the on-disk codec (C1). **C2 task:** expose an explicit swivel flag + measure the RAM delta + confirm top-1 unchanged.

---

## C2.2 Gates (each on its own metric)

- **C2_KV_RATIO** — report measured Spinor-KV bytes vs f32/f16 KV per head-vector + aggregate over a real context. (Landed: ~3×/f32 for the current int8 block.)
- **C2_KV_DECODE_DETERMINISM** — Spinor encode→decode round-trip is deterministic (CRC-valid) and the decoded-KV forward top-1 is stable run-to-run (E_CPU_8 extends to qwen36).
- **C2_RING2_RECALL** — Ring-2 offload to Optane + recall reproduces the in-RAM result bit-exact; report recall latency vs recompute. [DESIGN]
- **C2_FP16_SWIVEL** — fp16 runtime container: top-1 unchanged vs f32 swivel; report working-RAM reduction. [DESIGN]
- **C2_120X_INVESTIGATION** — determine which mechanism (anchor-basis / Ring-2 effective-context / sub-int8) yields the headline, or honestly restate the achievable KV-compression number. **No 120× claim without a measurement.**

---

## C2.3 Why this is the decisive contract

C1 proved the reducing weight artifact + the swivel. C2 is where the **PPT-ARM value thesis is proven or broken**: if the achievable KV compression + Ring-2 effective-context + fp16 swivel + integer-pipe speed (HX.3b 1.04×) compose to beat the 40-tok/s bar at long context, the project is justified. The first measurement already corrected the headline from "120× per-vector" to "~3×/f32 per-vector, deterministic-lossy" — the rest of C2 finds the real envelope number, honestly.
