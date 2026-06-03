# PLAN — SPEED / WIRE-CPU-V3: close the last 1.34× (memory layout, not ALU)

**Parent:** `CONTRACT-SPEED-wire-tok-s.md` (P1, RFC-001 §0/§8/§11). **Status:** PLAN (design only; no kernel changes here). **Box-contention:** all measurement stages need the dev host CPU — schedule them when the R9 32k run has freed the box.

## Where we are (measured, not assumed)

The WIRE-CPU ladder already moved Qwen3-0.6B CPU decode **0.84 → 39.52 tok/s (47×)**: Q8 packing 1.88× (bandwidth), threaded matmul 6.7×, threaded attention +19%, AVX2 int8×f32 dot 3.15×. Standing on the fair quant-matched scoreboard:

| engine / quant | gen tok/s |
|---|---|
| SP Q8 (threaded + AVX2 f32-dot) | **39.52** |
| llama.cpp Q8_0 | **52.8** |
| **gap** | **~1.34× behind (SP 0.75×)** |

**VNNI was tested and falsified** (`a2ad1dc`): int8×int8 `dpbusd` gave only **+9%** over the AVX2 f32-dot and **broke top-1** (naive per-vector act-quant too lossy). The 4× ALU barely moved the needle → **Q8 decode is bandwidth-bound on weight reads, not ALU-bound.** The remaining 1.34× is therefore a **memory-layout** problem, not a compute one. This plan attacks layout.

## The diagnosis: per-row scale vs Q8_0 32-element blocks

SP's packed format (`core/frobenius/frobenius_lift.h`) is **per-row**: `packed[r*cols + c]` int8 codes + one `row_scale[r]` fp32 per row. llama.cpp's `Q8_0` is **per-32-element block**: 32 int8 + one fp16 scale, laid out contiguously. The block format is why their Q8 decode is faster:

1. **Locality / one pass.** A Q8_0 block is a single cache-line-friendly unit (34 B). The dot reads weight + scale together, streaming, one pass. SP reads the int8 row, then separately broadcasts the row scale — two streams, and the act-quant/scale handling adds passes.
2. **Smaller activation-side work.** llama.cpp pre-quantizes activations to Q8 blocks once per token and does int8×int8 with block scales folded — fewer fp conversions in the inner loop.
3. **Prefetch friendliness.** Contiguous 34-B blocks prefetch cleanly; a separate `row_scale[]` array is a second, strided stream.

The hypothesis to test: **SP is moving more bytes / making more passes per token than Q8_0, and that — not ALU — is the 1.34×.** It must be *measured* (Stage 0) before building the block packer (Stage 1), per the contract's "measure before believing" rule and the HX.3b lesson.

## Stages (each its own gate; bit-exact-when-off is the invariant under all of them)

### Stage 0 — PROFILE (measure where the 1.34× lives) *(box)*
Re-confirm the 39.52 vs 52.8 baseline on the current box/build, then profile the SP decode hot loop:
- **bytes-moved / token** (weight stream + scale stream + activation), SP vs an estimate of Q8_0's.
- **LLC miss rate + memory-bandwidth utilization** (perf counters / VTune / `perf stat`) on the matmul.
- **passes over the weight tensor per token** in `matmul_arena`.
- **Gate:** a one-page profile that says, with numbers, whether the gap is (a) bytes moved, (b) passes/locality, or (c) per-token fp overhead. No code changes until this points somewhere. If the profile says we're already at DRAM-bandwidth saturation reading the *same* bytes as Q8_0, then layout won't help and the gap is elsewhere (act-quant passes, threading overhead at this token count) — follow the data.

### Stage 1 — Q8 BLOCK LAYOUT (the main lever) *(box; cross-cutting)*
Add a **block-scoped Q8 layout** to the Frobenius packer (`core/frobenius` + `core/arena`): 32-element blocks, per-block scale, contiguous `[32×int8 | scale]` records — a SP-native analogue of Q8_0. This is a **math-core format change** (the on-RAM arena every backend reads), so it is gated and additive: keep per-row Q8 as the default, add block-Q8 behind `SP_ARENA=q8blk`, and the AVX2 dot reads block scales inline.
- **Gate (a) parity:** block-Q8 forward stays **top-1 identical** to the per-row Q8 reference in deterministic mode (or document the exact bound; the per-block scale changes rounding, so this may be a *new* quantization, not bit-identical to per-row — decide and state which, do not silently widen).
- **Gate (b) speed:** tok/s vs the 39.52 baseline and vs llama.cpp Q8_0; report bytes/token delta from Stage 0.
- **Gate (c):** confirm the lever actually paid (the Stage-0 metric that was the bottleneck improved).

### Stage 2 — PASSES / FUSION / PREFETCH *(box)*
If Stage 0 fingered passes or fp overhead rather than raw bytes: fuse the activation Q8 quant with the dot (one pass), software-prefetch the next block, ensure the threaded tiling keeps each thread's weight slice cache-resident. Small, Amdahl-bound gains stacked.

### Stage 3 — GENERALIZE THE KERNEL *(box)*
The 39.52 win is Qwen3-specific in places. Extend the threaded + AVX2 (+ block-Q8) pattern to **gemma3 and qwen3.6 attention/FFN** (they share the head-loop threading pattern). Gate: same tok/s methodology, parity preserved per arch.

### Stage 4 — VNNI, ONLY IF act-quant is fixed *(box; research, not free)*
VNNI stays a documented dead-end **for naive per-vector act-quant**. Re-open *only* behind a per-channel / SmoothQuant-style activation scheme that keeps top-1. Treat as research; do not spec a tok/s gate on it until accuracy is proven.

## The north-star is a different lever (do not conflate)
`SPEED_NORTHSTAR` = **Qwen3.6-35B-A3B ≥ 40 tok/s**. That is **not** a dense-0.6B-kernel problem — it is dominated by **MoE expert memory traffic / residency**. The 0.6B kernel work above closes a *plumbing* gap on a shape where llama.cpp is already an excellent ceiling; SP's *actual* speed differentiator is the **composed envelope on large MoE**: C1 reducing weights (smaller expert reads) + expert streaming/prefetch (PoUW-predicted residency) + the Spinor-KV window. Honest strategic call: **match llama.cpp on the 0.6B dense dot (close the 1.34×, don't over-invest trying to beat a tuned ceiling there), and put the real speed-win effort into the 35B-A3B system gate**, where the reducing codec + expert residency compose into a lever llama.cpp doesn't have.

## CUDA / Vulkan WIRE (symmetric follow-ons, after CPU layout lands)
- **CUDA:** dp4a / PTX int8 dot, **sm-tier-aware** (Turing dev host: INT8-TC peak ratio is silicon-fixed — floor/stretch gates per tier, see `reference-cuda-sm-feature-tiers`).
- **Vulkan:** SPV int8 path; symmetric to WIRE-CPU.
Both gate on the same parity + tok/s + bytes/token methodology.

## Discipline (binding)
- **Bit-exact-when-off** holds under every stage — the regression invariant.
- **No silent gate revisions.** If a stage can't hit its number, surface upstream as a roadmap amendment with the measured reason; do not retreat to a higher-level API or tune fixtures.
- **Measure before believing** (the HX.3b + VNNI lesson): Stage 0 profile gates Stage 1; a falsified hypothesis is a result, documented like VNNI was.
- **Baseline = prior SP + llama.cpp-Q8 as the silicon ceiling reference** (not load-bearing pass/fail beyond "match it").

## First actionable when the box frees
Run **Stage 0** (`sp_toks` re-baseline + `perf stat` / counters on `matmul_arena`) and write the one-page profile. That single measurement decides whether Stage 1's block packer is worth building or whether the gap is passes/overhead. Everything downstream forks on it.
