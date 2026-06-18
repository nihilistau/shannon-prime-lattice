---
type: contract
title: CONTRACT — The Byte-Exact Forward (weights + the three fp32 islands)
description: "Status (2026-06-18): DESIGN + OFFLINE PROTOTYPES COMPLETE & GREEN."
tags: [contract, byteexact]
timestamp: 2026-06-18T04:52:34Z
resource: shannon-prime-lattice/papers/CONTRACT-BYTEEXACT-forward.md
sp_status: GREEN
sp_gate: none
sp_commit: TBD
sp_repro: none
---
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

### 5.1 G-BYTEEXACT-ISLANDS-CUDA — the verification scaffold (PRE-REGISTERED 2026-06-18)
The full integer-island forward (§4.3) is a later big effort — converting `k_rmsnorm*` / the `k_attn` softmax / `k_gelu_mul` / `k_rope*` in `cuda_forward.cu` from float to exact-integer. **Before** that, this gate proves the crate's already-built exact-integer references (`sp_islands_q_ref.rs`: `rmsnorm_q_ref` / `softmax_q_ref` / `gelu_q_ref` / `rope_q_ref`, G-ISLANDS-Q-REF GREEN) **agree with the CUDA forward's actual float island outputs on REAL 12B per-layer activations** to the contract tolerance — i.e. the integer islands, when wired in, will cost nothing measurable. It de-risks §4.3 and §5's G-BYTEEXACT-PPL by measuring island fidelity *on-model* (not synthetic) first.

**Thresholds (pre-registered; per-island, measured on real 12B activations — relerr = ‖cuda−ref‖₂ / ‖cuda‖₂):**

| island | metric | threshold | rationale |
|---|---|---|---|
| RMSNorm (ffn_norm, E-wide) | relerr | **< 1e-4** | crate ref is eps-free `√(n/Σx²)`; CUDA is `1/√(mean+eps)`, gemma `rms_eps≈1e-6` → sub-threshold; host gate measured 5.8e-6 synthetic |
| GELU-tanh (`k_gelu_mul`, fused ·up) | relerr | **< 1e-4** | tanh via the exp primitive; host gate 2.8e-6 synthetic |
| RoPE (post-q-norm q, NEOX) | relerr | **< 1e-4** | CORDIC cos/sin vs `sinf/cosf`; freq table rebuilt from dumped `rbase`+`ff`; host gate 9.2e-6 synthetic |
| softmax (attention logits) | max\|Δp\| | **< 1e-5** | gated offline by G-ISLANDS-Q-REF (1.3e-6) on the §3 prototype; the prefill comparator dumps the three POINTWISE islands and SKIPs softmax (a separate logit-dump seam closes it) |

**Mechanism (additive, env-gated, default-off = byte-inert null floor — the one-shot decode path stays byte-untouched):**
1. **Dump seam** — `cuda_forward.cu` `gemma4_cuda_probe`: `SP_BYTEEXACT_DUMP=<path>` writes the INPUT+OUTPUT of the three pointwise islands for ONE layer (`SP_BYTEEXACT_LAYER`, default = `n_layers/2` — a MID layer, since the `attn_only=1` driver breaks at the last layer *before* the FFN island captures) as a self-describing binary (header `BXI1` + per-record `{4-byte tag, rows, width}` + f32 payload; tags `RMSi/RMSw/RMSo`, `GELi/GELu/GELo`, `ROPi/ROPb/ROPf/ROPo`). Pure observation: D2H of the live device buffers around the existing kernels, no kernel behaviour change. (Independent of the §3q `SP_ARM_DUMP` K/q seam, which dumps post-RoPE K/q on the global owners during DECODE — wrong tensors/path for this gate, so a dedicated additive seam was added rather than overloading it.)
2. **Driver** — `tests/test_gemma4_cuda.c` `SP_G4_BX_DUMP=1` (→ `run_bx_dump`): loads the 12B `.sp-model`, runs `gemma4_cuda_probe(…, attn_only=1)` so the layer loop executes every layer, fires the dump at the chosen layer, and breaks at the last layer's attention residual — **never reaching the tied head** (which 12B can't run without the resident f32 embd). Tokens from `SP_PPL_TOKENS` or a small synthetic id sequence; `SP_BX_NTOK` sets the count (default 16).
3. **Comparator** — `tools/sp_dsp_smoke/src/bx_islands_compare.rs` (crate bin `bx_islands_compare`, host x86, no DSP/FFI): reads the dump, re-runs each island's dumped INPUT through the crate's `*_q_ref` (the SAME exact-integer references the future CUDA kernels gate against), and asserts the per-island thresholds above. Exit 0 iff all GREEN.

**Run procedure** (needs the warm CUDA build `build-cuda-vs22/tests/test_gemma4_cuda.exe` + the 12B `gemma4-12b-b1.sp-model`):
```
# 1. dump real 12B islands (last layer, 16 tokens)
set SP_GEMMA4_SPMODEL=D:\F\shannon-prime-repos\models\gemma4-12b-b1.sp-model
set SP_GEMMA4_SPTOK=D:\F\shannon-prime-repos\models\gemma4-12b-b1.sp-tokenizer
set SP_G4_BX_DUMP=1
set SP_BYTEEXACT_DUMP=tests\fixtures\xbar_r3\bx_islands_12b.bin
build-cuda-vs22\tests\test_gemma4_cuda.exe
# 2. gate vs the crate refs (host cargo, no CUDA)
cd tools\sp_dsp_smoke
cargo run --release --bin bx_islands_compare -- ..\..\tests\fixtures\xbar_r3\bx_islands_12b.bin ^
    | tee ..\..\tests\fixtures\xbar_r3\G-BYTEEXACT-ISLANDS-CUDA.log
```
Receipt: `engine tests/fixtures/xbar_r3/G-BYTEEXACT-ISLANDS-CUDA.log`. This gate is the named §8-step-2 precondition for wiring the integer islands into the CUDA forward.

### 5.2 G-BYTEEXACT-FORWARD-12B — the islands wired into the CUDA decode (PRE-REGISTERED 2026-06-18)
The §5.1 scaffold proved the integer refs match the float islands on real 12B activations (RMS 3.84e-5 / GELU 8.18e-7 / RoPE 9.62e-6, all < 1e-4). This gate is the WIRE-IN: the exact-integer islands now run *inside* the gemma4 CUDA decode, gated by `SP_BYTEEXACT`. Builds on the already-landed integer **attention** (`k_attn_decode_win_bx`, §7; G-BYTEEXACT-ATTN-12B: LEG A 4.6665 / LEG B 4.6069 on n=42).

**Mechanism (additive, env-gated, default-off = byte-identical null floor):** a `__device__ __constant__ int d_bx_flag` is set ONCE at `gemma4_decode_cuda` entry (`cudaMemcpyToSymbol` from `getenv("SP_BYTEEXACT")`, BEFORE graph capture so the captured graph bakes the chosen path). Each float island kernel gains an `if (d_bx_flag) { …integer… return; }` branch in front of its existing float body:
- **RMSNorm** — `k_rmsnorm` / `k_rmsnorm_head` / `k_rmsnorm_head_noweight` → shared `bx_rmsnorm_core` (int64 sum-of-squares reduction = order-immune; `bx_rms_inv` = the 64-bit-split isqrt, SH=50 `num=(n<<50)/sumsq; val=num<<22; inv=bx_isqrt_u64(val)`; Q16/IB20/Qw16, out / 2^52).
- **GELU** — `k_gelu_mul` + the AltUp gate `k_altup_gate` → `bx_gelu` (FB30 cubic+tanh; `bx_mulshift_fb` = `__umul64hi`-based signed `(a*b)>>FB` for the `X*X`/`X*X*X`; tanh via the shared `bx_exp_fixed`).
- **RoPE** — `k_rope` / `k_rope_at` / `k_rope_freqs` / `k_rope_freqs_at` / `k_rope_dyn` / `k_rope_freqs_dyn` → `bx_cordic_cossin` (rotation-mode CORDIC, the ref atan table + K) via `bx_rope_pair` (Q16 fixed-point rotate); `freq` recomputed from the same float `rbase`/`ff` inputs the float kernel uses, encoded to FB30 (`bx_rope_theta`, `pos*freq_fix` < 2^50 so no `__int128`).
- **softcap** — `k_softcap` (LM-head) → integer tanh via `bx_tanh_fixed`.

All wide products avoid `__int128` (NVCC): `__umul64hi` for the GELU cubic and the exp's `d*LOG2E`; the 64-bit isqrt split for the RMS numerator. Reductions are exact integer ⇒ **reduction-order-immune** (the cross-machine bit-identity proxy; a true two-GPU check is external/future).

**Gate (`test_gemma4_ppl_cuda`, NCTX=84, CHUNKS=1, n_scored=42, `build-cuda-vs22`, model `gemma4-12b-b1.sp-model`):**
| leg | env | threshold | meaning |
|---|---|---|---|
| **LEG A** | `SP_BYTEEXACT` unset | **PPL == 4.6665 EXACTLY** | the null floor — default-off MUST be byte-identical to baseline |
| **LEG B** | `SP_BYTEEXACT=1` | **PPL parity** (within small-N deflection; attention-only gave 4.6069) | the integer islands cost nothing measurable |
| **DETERMINISM** | `SP_BYTEEXACT=1`, run twice | **run-to-run bit-identical** | integer reductions are order-immune (cross-machine proxy) |

LEG A is the hard byte-identical constraint; LEG B is a parity band (the n=42 deflection is ±~1.5%, see `feedback_small_n_deflection_illusion`). Receipt: `engine tests/fixtures/xbar_r3/G-BYTEEXACT-FORWARD-12B.log`.

## 6. Note for the gguf-v4 successor
A *from-scratch* model would **choose** Mersenne hidden dims ({8191, 32767, 131071}) so RMSNorm/RoPE division becomes an exact bit-shift, closing all islands by construction — the natural end state this retrofit approximates with fixed-point. Out of scope here; in scope for the successor study.

## 7. Scope upgrade — FULL cross-machine byte-exact (operator decision, 2026-06-18)
The "3 islands + already-exact dp4a" framing held for the PPT *architecture* (where attention is the poly-ring kernel) but **undercounts the gemma4 ENGINE as built**: `cuda_forward.cu`'s decode still runs the **float** attention (`k_attn_decode_win`: `acc += qh[i]*kh[i]` over the float K cache, the `expf` softmax, and the float p·V sum) and **float RoPE** (`sinf/cosf`). These are deterministic on one machine but **not** machine-independent (FMA contraction, libm `expf/sinf`). So the literal G-BYTEEXACT-FORWARD gate (logits bit-identical *across machine*) needs them integerized too. Operator chose the **full** path; both mechanisms are canonical PPT and already substrate-proven:

- **Attention Q·K / p·V → dual-prime CRT-NTT negacyclic convolution** (PPT-ARM-Theory §13.1 / System §6). `⟨q,k⟩ = coeff_{N-1}(Q(x)·K(x̂))/Δ²`; CKKS encode `e(v)=round(Δ·v)`, Δ≥2¹⁰ ⇒ ULP-exact / KL=0 at d_k≤N=256. Dual-prime (q1=1073738753, q2=1073732609) keeps every product <2⁶⁰ in int64 (no `__int128`) + Garner CRT ⇒ cross-machine bit-identical (System §5: Linux GCC == Windows MSVC). **Gate G-BYTEEXACT-ATTN-NTT GREEN** (engine `tools/ring3/g_byteexact_attn_ntt.py`, receipt `tests/fixtures/xbar_r3/G-BYTEEXACT-ATTN-NTT.log`): negconv coeff == exact integer dot at every Δ, <2⁶³ throughout, fidelity 2.2e-3@Δ2¹⁰ → 1.76e-6@Δ2¹⁸, order-immune. The O(N log N) acceleration is the engine's proven `sp_pr_mul` (G-R3-BIND-on-O_K, native NTT == schoolbook bit-identical). **Build = wire `sp_pr_mul` into the gemma4 decode in place of `k_attn_decode_win`** (the KV cache moves to the integer/CKKS-encoded representation — overlaps the XBAR KV work).
- **RoPE → deterministic integer angles** (PPT-ARM-Theory §RoPE, E9.1 Stern–Brocot / CM-endomorphism, discrepancy 0.00134 ≪ 0.0558). The exact *index-shift closure* (one int32 offset/token, ~128× cache cut) requires **Mersenne context** (gguf-v4 co-design); gemma's E=3840 retrofit uses a deterministic fixed-point/Stern–Brocot **integer angle table** (machine-independent, replaces `sp_rope_bridge`/`k_rope_freqs`).

Full float-surface ledger for G-BYTEEXACT-FORWARD: RMSNorm×3 (islands ✓ C-gated), softmax (island ✓), GELU-tanh (island ✓; `k_gelu_mul` is already GELU-tanh, not SiLU), logit softcap (integer tanh via the exp primitive), OK_Q4B GEMV scale-apply (fixed-point), **attention Q·K + p·V (CRT-NTT ✓ gated)**, **RoPE (integer angle table)**, embedding √E scale + AltUp scalars (deterministic fixed-point). The decode path stays env-gated (`SP_BYTEEXACT` default-off = byte-identical null floor).

## 8. COURSE-CORRECTION — the byte-exact math lives in the universal Rust crate (operator, 2026-06-18)
The byte-exact **linear algebra was already built, bounded, and bit-exact-gated** in the Rust crate `engine tools/sp_dsp_smoke` (the §3-HX / NTT-sprint line; not in the 4 mounted folders — `git worktree` of the engine): dual-prime Barrett (`sp_barrett_oracle.rs`, same q1/q2/μ), mod-q matmul + **Garner CRT** (`sp_matmul_q_ref.rs`, `Q1_INV_MOD_Q2=894602413` — the constant the CUDA hand-roll re-derived — + `matmul_60bit_ref` + `T_GARNER_BIT_EXACT`), and the full NTT ladder (`sp_ntt_0..5b`, INTT round-trip gated). **The session's offline ATTN-NTT/ATTN-FULL prototypes + the CUDA `bx_*` kernels re-derived proven code.** Lesson banked: grep the crate before building byte-exact arithmetic ([[reference-byteexact-already-in-rust-crate]]).

**Architecture (L1-ABI, PPT-LAT-L1-ABI-v0):** the crate is **L2** (universal orchestrator + scalar bit-exact reference); **L1** = per-backend kernels (C/CUDA/HVX). CUDA is a first-class L1 backend (`SP_ECUDA=-40`). The forward backend seam **already exists**: `sp_session_register_forward_backend(session, handle, sp_forward_dispatch_fn)` with Rust trampoline `cuda_forward_dispatch.rs` (`sp_wire_cuda_forward_dispatch`) → C glue `c_backend_cuda/sp_daemon_cuda_glue.c` (`sp_daemon_cuda_forward`, arch-routes to the CUDA forward), feature `wire_cuda_backend`, gate `T_WIRE_CUDA_RUNTIME_ACTIVE`; `build.rs` links `sp_cuda_daemon_backend.lib` + cudart/cublas. **Gap:** the glue routes `gemma3_forward_cuda` but has no `SP_ARCH_GEMMA4` case, so it never reaches `gemma4_forward_cuda` (cuda_forward.cu:1662).

**The new piece — the nonlinear islands — now live in the crate** (greenfield; confirmed no prior island work): `sp_dsp_smoke/src/sp_islands_q_ref.rs` (`rmsnorm_q_ref`/`softmax_q_ref`/`gelu_q_ref`, FB=30 exact-integer, i128 intermediates) + host gate `sp_islands_q_ref_test.rs` (**G-ISLANDS-Q-REF GREEN**: RMS 5.8e-6 / softmax 1.3e-6 / GELU 2.8e-6, order-immune). Companion to `sp_matmul_q_ref`. The wrong-layer CUDA RMS edits were reverted; the committed `k_attn_decode_win_bx` (on-12B PPL 4.6069) is a provisional CUDA-side datapoint to be reconciled into the crate-driven path.

**BRIDGE PLAN (do the obvious — the plumbing exists):**
1. Add `case SP_ARCH_GEMMA4: return gemma4_forward_cuda(...)` to `sp_daemon_cuda_glue.c` (one line; entry already exported, same lib). Drives the real 12B through the existing `register_forward_backend` hook.
2. Wire the islands into a CUDA exactness gate: diff `gemma4_forward_cuda`'s RMSNorm/softmax/GELU/RoPE intermediates vs `*_q_ref`. **(RoPE reference DONE — `rope_q_ref` + `cordic_cossin` in `sp_islands_q_ref.rs`, deterministic fixed-point CORDIC, G-ISLANDS-Q-REF GREEN; all FOUR islands now in-crate.)**
3. Reconcile the `.sp-model` loader to OK_Q4B (crate currently reads OK_Q8 single tiles) — or pass the engine's resident `qwen3_model*`/`g_w` device weights rather than re-loading.
4. (New sprint) a persistent-KV L1 verb (open/step/rewind/close) for the `gemma4_kv_*` decode path — the current hook is prefill-only by contract.
5. End-to-end "byte-exact-when-off" gate: same tokens through the math-core reference forward and CUDA `gemma4_forward_cuda`, logits agree to tolerance — the universal contract, now spanning CUDA.
