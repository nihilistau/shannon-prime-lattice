# SESSION CLOSED — Stage Eta ETA.5b: the velocity pass + THE 12B SHOOTOUT (2026-06-07)

**One session, opened on the C2.4 finale verdict and closed on a beaten industry baseline.**

## The headline (receipt `_12b_shootout.log`; engine `af738f9`, core `e8708f7`)

| engine | artifact | Gemma-4-12B, RTX 2060, tg256 |
|---|---|---|
| llama.cpp-CUDA b8861, ngl 99 | Q4_K_M GGUF 6.62 GB | 31.29 ± 0.20 tok/s |
| **SP (graph + dp4a)** | **reducing .sp-model 5.56 GB** | **34.2 tok/s (+9.3%)** |

SM pinned 2100 MHz; `-lmc` unsupported on GeForce — the memory clock free-ran
for BOTH engines (same conditions, same card, same source model).

**THE ANCHOR (no spin):** the SP artifact squeezes the source's Q6_K tensors to
Q4 codes — fewer bytes read (part of the win), more weight-quant error than
llama.cpp's mixed K-quants. The number is **not citable** until the wikitext
PPL gate closes (release-blocking for paper 06). Quality currency banked so
far: oracle-anchored top-1/top-2 on short streams, prefill parity at f32
floors, graph 256/256 exact.

## What shipped (the session's arc, all gated)

1. **ETA.5b.1 — device-fed decode** (E_G4_CU_DEC oracle byte-match ALL):
   dseq/dpos resident; packed PLE table + `k_ple_gather_at` (TRUE-division
   host-mirror arithmetic); packed tied head (`embd_packed`); zero per-token
   D2H at eos<0.
2. **ETA.5b.2 — jagged graph capture** (256/256 EXACT): one generate step
   captured, replayed per token; per-owner cache pointers fixed per layer.
3. **ETA.5b.3 — dp4a routing** (256/256 top-1): E2B ladder lift 10.3 → graph
   10.6 → dp4a 62.3 (6.05×) → **graph+dp4a 75.7 tok/s (7.35×)** — Amdahl-clean.
4. **ETA.5b.4 — the dense 12B** (gate 24/24): NOT the E-series — PL=0 with
   out_scale + rope_freqs PRESENT (presence-keyed now), no KV sharing,
   per-layer kv-head ARRAYS (8 SWA / 1 global), **V-less global layers**
   (V = the raw K projection; llama.cpp "use_alternative_attention" read
   reference-first). Transcode REDUCES 6.63 → 5.56 GB. f32 embd skipped past
   a 2 GB budget → packed embed gather + dp4a head.
5. **THE L11 KILL** — the session's engineering centerpiece. Decode diverged at
   the second generated token (oracle-rank 205596, gap 27.9). The
   operator-directed bisection, one strike per run: provenance (innocent) →
   embed intercept 0.000e+00 (innocent) → layer-norm telemetry (smooth —
   directional damage) → layer bisect vs the prefill probe (32 → **214 inside
   L11**, the layer whose TRAINED out_scale is 0.005) → **the LIFT
   discriminator: exact arithmetic = 1.5e-4 floors everywhere — structure
   innocent, per-VECTOR activation quant guilty.** Fix: per-16-BLOCK scales
   aligned exactly to the GEMVs' 128-bit loads (one f32 mul per block, zero
   extra bus). Verdict: **rank 2 at gap 0.31 — a measured top-2 near-tie**,
   the top-1-trust currency. The DEC gate now prints oracle-rank + logit gap
   on any flip.

## Regressions held

E2B 44/44 after every change (incl. the kernel rewrite); qwen3 decode suite
green; the E2B-pinned parity gates are now SCOPED to E2B (other geometries run
telemetry until their own floors are pinned — gate-currency hygiene, not
relaxation).

## The diagnostic toolkit (banked in-tree, env-gated)

`SP_G4_FASTPROBE` (2-minute iteration loop), `SP_G4_DEC_PROBE=<pos>` (embed
intercept + per-layer |x| telemetry), `SP_G4_DEC_DUMP` (per-layer x at the
FFN-residual boundary), `SP_G4_LIFT` (the arithmetic discriminator),
`SP_G4_NO_OSCALE`, the probe-vs-decode boundary differ. The suite that killed
this bug in five strikes is now standing equipment.

## Open (the named follow-ups)

1. **THE PPL GATE** — wikitext perplexity, both engines, same text, protocol
   disclosed. Release-blocking for paper 06's headline.
2. 12B parity floor pinning (telemetry-then-pin).
3. Q8-keep option for Q6_K-source tensors (fidelity vs ~0.7 GB of reads) if
   the PPL gate shows a squeeze cost.

*The math won today.* ⬢⃝
