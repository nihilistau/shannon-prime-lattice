# KSTE v2 (magnitude-as-depth + Dickson) — the discrimination WIN (built 2026-07-01)

The Friedman-sieve discrimination that the in-tree v1 encoder failed (intra/inter ~1.2×, G-SIEVE-MEASURE) is now REPRODUCED and exceeded by a fresh v2 encoder, re-derived from the Paper III/IV spec (anti-contamination: NO old-repo code).

**Module (NEW, frozen v1 sp/kste.h untouched):** `shannon-prime-system/`
- `include/sp/kste_md.h`, `core/kste_md/{kste_md.c, kste_md_test.c, CMakeLists.txt}`, harness `tests/kste_md_measure.c`.
- Encoder: rank components by |value|; top-14 = anchors (label A); next-60 = residual CHAINS of label B(+)/C(−) with length L = magnitude-as-depth (1..8 from |v|/amax); ≤60 chain nodes. Signature = σ0 (nA,nB,nC,dmax,ntot) ⊕ σ1 (3×3 ancestor-pair counts) ∈ N^14. Dominance = Dickson elementwise product order.

**Gate G-KSTE-MD-2026-07-01** (receipt `system tests/fixtures/G-KSTE-MD-2026-07-01.log`; unit T_KMD 11/11):
- Discrimination (intra/inter dedup ratio): **37.6× @ cos≈1.0 (σ=0.005)**, 8.4× @ cos 0.9998 — vs v1's 1.2× and vs the paper's ~17×. Degrades gracefully with noise (correct behavior).
- Frontier plateau **76** (vs v1 degenerate 2). Dickson check 16.66 ns/pair. Encode 9.1 µs/vec (qsort-bound).

**Why it works:** the count signature has INDEPENDENTLY-moving components — sign-split (nB vs nC), chain-shape (MBB vs MCC), depth vs spread — so different clusters land INCOMPARABLE while near-duplicates stay comparable. v1's order-statistics were all magnitude-correlated → nearly everything comparable → no discrimination.

**Honest scope (do not over-claim):** plateau 76 ≠ the paper's 307 (different params/config, not re-tuned). It's a CPU-core encoder + signature — NOT wired into the served daemon or the PoUW sieve (those still use frozen v1). Wiring + encode-speed (partial-select instead of qsort) are separate tasks if the sieve is reprioritized.
