# CONTRACT — The Byte-Exact Forward (weights + the three fp32 islands)

**Status (2026-06-18):** DESIGN + OFFLINE PROTOTYPES COMPLETE & GREEN. Engine build is the next campaign.
**Mission:** make the *entire* gemma-4-12B forward **byte-exact** — bit-identical logits across reduction-order and machine — so the weights and the activation path join the memory tier in the exact-integer O_K container. This is the **auditability/exactness** mission, explicitly **not** compression.

## 0. The de-conflation (load-bearing)
Two separate things were conflated and are now split:
- **Better quant (compression)** — CONVICTED, do not pursue. Incoherence rotation (~1.37×@int4, shrinks at lower bits, no 3-bit unlock) and column re-ordering (~1.05×) are both **redundant vs our per-32-block OK_Q4B**, which already sits at gold PPL 4.6665 ≈ 4.68. Receipts: `engine tests/fixtures/xbar_r3/G-WEIGHT-{TRANSFORMS,FOLD-ORACLE}.log`. The 3-bit unlock is a different axis (QAT / codebook / mixed-precision), not a transcode trick — that is the operator's future gguf-v4 study, separate.
- **Byte-exact (this contract)** — the primary mission.

## 1. The key insight: byte-exact = EXACT ARITHMETIC, not the π^k cancellation
T4 §3.2 (Projective Cancellation) is the *elegant* route — a per-tensor π^k that vanishes at RMSNorm — but it **forces per-tensor scaling → 8-bit** (per-tensor int4 is 0.399 matmul-relerr, dead; int8 0.023, viable), i.e. **OK_Q8 ≈ 18 GB, does not fit the 2060-12GB**. Receipt `G-WEIGHT-T4-BYTEEXACT.log`.
**Therefore the Q4 route:** keep **OK_Q4B per-block** (gold PPL, 9.4 GB, fits the card) and get byte-exactness from **exact fixed-point arithmetic** instead of the cancellation — the π^k scale is exactly *applied*, not exactly *cancelled*. Not perfect (no cancellation elegance), but better (fits, gold, byte-exact).

## 2. Where the forward is NOT byte-exact today
The engine runs the **linear algebra** in O_K exactly (the dp4a int4×int8→int32 accumulate is order-immune), but `RMSNorm / softmax / SiLU(GELU)` are **float "fp32 islands"** (`sp_rmsnorm_bridge` decodes a+bω→fp32, computes 1/√ in float, re-encodes; PPT-ARM-System §8). The 1B validation's only nonzero deltas were exactly these islands. **Byte-exactness is blocked at the islands, not the weights.**

## 3. The three islands — exact-integer prototypes GREEN
Shared primitive: fixed-point `exp` via 2^x (integer poly, coeffs (ln2)ᵏ/k!). `engine tools/ring3/g_norm_integer.py` + `g_islands_integer.py`; receipts `G-NORM-INTEGER.log` + `G-BYTEEXACT-ISLANDS.log`.

| island | replacement | fidelity vs float | byte-exact property |
|---|---|---|---|
| 1. RMS norm (keystone) | y = x·√(E/Σx²)·(1+w); Σx² exact int64, 1/√ via integer `isqrt`, (1+w) fixed-point | relerr 7.6e-6 | Σx² reduction-order-immune |
| 2. softmax | exact-integer logits (poly-ring `sp_pr_inner`) → fixed-point exp → exact-integer Σ → fixed-point divide | max\|Δp\| 1.0e-6, **KL 8.8e-8** (= §6 "KL=0 to ULP") | Σexp reduction-order-immune |
| 3. GELU-tanh (gemma `k_gelu_mul`) | 0.5x(1+tanh(k(x+0.044715x³))); tanh via the exp primitive | relerr 1.5e-6 | deterministic per-element integer fn |

All match float to ~1e-6 (lossless for inference) and are reduction-order-immune / deterministic.

## 4. The byte-exact-Q4 forward (the build)
1. **Weights:** keep OK_Q4B per-block; make the per-block scale-apply **exact fixed-point** (the f16 scale + float multiply is the only non-exact step in the weight path).
2. **GEMV:** dp4a int4×int8→int32 accumulate — *already* exact-integer.
3. **Islands:** port the three integer functions (§3) into the math-core + CUDA kernels, replacing the fp32-island bridges.
4. **RoPE:** integer angle table (the last float op; closes exactly via Mersenne-context on a *co-designed* model — gemma's E=3840 is not Mersenne, so use a deterministic fixed-point table for the retrofit).

## 5. Gates
- **G-BYTEEXACT-FORWARD:** 12B logits **bit-identical** across reduction-order and machine (CPU/GPU), with the islands integer.
- **G-BYTEEXACT-PPL:** PPL-parity vs the bf16 gold (4.68) — i.e. the integer islands cost nothing measurable (the ~1e-6 island fidelity predicts this; **measure on-model, do not assume**).

## 6. Note for the gguf-v4 successor
A *from-scratch* model would **choose** Mersenne hidden dims ({8191, 32767, 131071}) so RMSNorm/RoPE division becomes an exact bit-shift, closing all islands by construction — the natural end state this retrofit approximates with fixed-point. Out of scope here; in scope for the successor study.
