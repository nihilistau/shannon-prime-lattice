# SESSION-HANDOFF.md — where things stand

**Updated:** 2026-06-18 (**XBAR UNIFIED onto the exact-integer O_K substrate** — ten receipts, all GREEN or honest-negative; engine `0019b86→d2d7ceb`, all pushed; **period-6 rebase + host-numpy→native Z_q/NTT port both CLOSED**; **nothing baking**).

---

## 0. State in one paragraph

The XBAR memory architecture is now UNIFIED onto the exact-integer O_K substrate (Q(√−163), the dual-prime negacyclic CRT-NTT in `core/ntt_crt`+`core/poly_ring`, already linked into the engine — **zero new linkage**, because the `gemma4_kv_*` cache is pure f32 and the only int8 path is the weight gemv). **The container wins:** Ring-3 bind re-carried native (Leg A, engine `0019b86`) is 256/256 bit-identical to the integer reference, ±1 carrier recall lossless, and the superposition M is byte-identical across 8 summation orders (the float M diverges 4.44e-15 — reduction-order immunity, a *correctness* guarantee); the Frobenius integer Ring-2 store (G-R2-FROB, `dbe4103`/`d076797`, Theorem-T4 form) reaches sub-ULP at 24b / lossless at 16b with bit-width as the compression lever; the **full organism loop ran native on real episodes** (G-XBAR-ORGANISM-FULL, `15e7051`): continuous audio → discrete integer memory → continuous KV out, autonomous, C2 sig accepts-audio/rejects-text, SP_REPLAY checks=5 fails=0; and the period-6 rebase is CLOSED (`d2d7ceb`, decoy separation 154→129). **The content does not:** four honest negatives bound the win — Dirichlet-character carriers (Leg B, `d7d96fe`, inert), Möbius-on-M (`1e70763`), entropy-on-codes (`e6d17bb`), and T2-Möbius-on-real-weights (`ac76c8e`, worse than random). The **boundary thesis** is the session keystone: the substrate's value is exact arithmetic — the indestructible algebraic container — not number-theoretic structure imposed on the high-entropy content. The prior XBAR stack (P3, C2 curator, Ring-3 Path A, #222, GNA EAR, KAIROS) is unchanged and still closed.

**No runs in flight. No pods. No schtasks. RunPod balance: $0.**

---
## 0b. BYTE-EXACT FORWARD — campaign status (2026-06-18, late session)

Goal: the entire gemma-4-12B forward **byte-exact** (cross-machine bit-identical, deterministic-integer) — auditability mission, not compression (see `papers/CONTRACT-BYTEEXACT-forward.md`). **Course-correction landed (operator): the byte-exact math is owned by the UNIVERSAL Rust crate `engine tools/sp_dsp_smoke` (L2 orchestrator + scalar bit-exact reference), NOT hand-rolled per backend.** The crate already had the LINEAR algebra bit-exact-gated (Barrett, mod-q matmul, Garner CRT w/ `Q1_INV_MOD_Q2=894602413`, the NTT ladder); this session's offline ATTN-NTT/ATTN-FULL prototypes + the CUDA `bx_*` re-derived it (lesson banked).

DONE + GREEN this session:
- **Islands → crate** (the genuinely-new nonlinear piece): `sp_dsp_smoke/src/sp_islands_q_ref.rs` (`rmsnorm/softmax/gelu_q_ref`, FB30 exact-integer) + host gate `sp_islands_q_ref_test.rs` — **G-ISLANDS-Q-REF GREEN** (RMS 5.8e-6 / softmax 1.3e-6 / GELU 2.8e-6, order-immune; `cargo run --bin sp_islands_q_ref_test`, host x86 no DSP). Engine `4511a10`.
- **Bridge step 1**: `case SP_ARCH_GEMMA4: gemma4_forward_cuda` added to `tools/sp_daemon/c_backend_cuda/sp_daemon_cuda_glue.c` — the crate's existing `register_forward_backend` hook (feature `wire_cuda_backend`, gate `T_WIRE_CUDA_RUNTIME_ACTIVE`) can now drive the real 12B. Engine `3f021d9`.
- **(provisional)** committed CUDA `k_attn_decode_win_bx` (exact-integer dual-prime attention, on-12B PPL 4.6069 vs 4.6665 baseline, `9c2aad3`) — left as a CUDA-side datapoint pending reconciliation into the crate-driven path. The wrong-layer CUDA RMS edits were **reverted**.

**ALL FOUR ISLANDS in the crate + the 3-agent fleet closed the remaining bridge work (2026-06-18, late):**
- **RoPE island DONE** — `rope_q_ref` + `cordic_cossin` (deterministic fixed-point CORDIC, no libm) — all 4 islands GREEN (engine `38dc133`).
- **#265 wire_cuda bridge GREEN** (engine `eee3aac`): the universal daemon drives `gemma4_forward_cuda` on the real 12B through `sp_session_register_forward_backend` (`cuda_forward_count 0→1`, `wire_cuda_active:true`). Build fix = added `xbar_episode.c` to the CUDA-backend CMake (build-system only); stale math-core libs rebuilt. Receipt `G-WIRE-CUDA-GEMMA4.log`.
- **Persistent-KV decode verb SCAFFOLDED** (engine `9da91f6`): `sp_session_register_kvdecode_backend` (open/prefill/decode_step/rewind/pos/close) → `tools/sp_daemon/WIRE-CUDA-DECODE-GEMMA4.md` + Rust trampoline `cuda_kvdecode_dispatch.rs` + C glue + AppState slot; `cargo check` GREEN w/ and w/o `wire_cuda_backend`. The one ABI gap: an additive `gemma4_kv_decode_logits` (decode currently returns argmax ids, not logits). Gate = `G-WIRE-CUDA-DECODE-GEMMA4`.
- **.sp-model Q4B loader RECONCILED** (engine `e9fb9b0`, decision **B**): the crate consumes the engine's resident `qwen3_model*`/`g_w` device weights; OK_Q4B is decoded engine-side; a 2nd crate decode would risk a divergent dequant. The crate's HVX `sp_model_layer.rs` Q8 loader stays HVX-track-only. Doc `SP-MODEL-Q4B-RECONCILIATION.md`.
- **#261 island exactness gate PRE-REGISTERED + harness written** (engine `92b93d2`, lattice `34a93d1`): `G-BYTEEXACT-ISLANDS-CUDA` (contract §5.1) — env-gated `SP_BYTEEXACT_DUMP` seam in `gemma4_cuda_probe` (default-off null floor) dumps real-12B RMSNorm/GELU/RoPE in+out → host comparator bin `bx_islands_compare` diffs vs the crate `*_q_ref` (thresholds RMS/GELU/RoPE relerr<1e-4, softmax max|Δp|<1e-5). RUN DEFERRED (needs the warm VS22/CUDA `test_gemma4_cuda.exe` rebuild — run procedure in §5.1).

NEXT (the heavier integrations, all named + scaffolded): (1) the `G-BYTEEXACT-ISLANDS-CUDA` RUN — rebuild `test_gemma4_cuda` (VS18/CUDA), dump + compare on the 12B → real on-model island-fidelity numbers; (2) `G-WIRE-CUDA-DECODE-GEMMA4` integration — add `gemma4_kv_decode_logits` to cuda_forward.cu (additive) + fill the `TODO(WIRE-CUDA-DECODE)` glue/Rust bodies + the L1 verb in `sp/sp_l1.h` (frozen-ABI change, commit submodule upstream first) → full 12B decode through the daemon; (3) the BIG one — convert the CUDA forward's float islands to the integer `*_q_ref` for true logit-bit-identicality (§4.3). Build note: crate host bins run `cargo run --bin <name>`; the CUDA backend builds under VS18 BuildTools (`D:\Program Files (x86)\...\18\BuildTools`, cl 14.50) + CUDA 13.2, feature `wire_cuda_backend`.

---
## 1. IN FLIGHT right now (nothing; all clean)

- No active GPU runs. No pods. No schtasks. GPU clocks at default.
This session's closures (engine `0019b86→d2d7ceb`, all pushed; receipts in engine `tests/fixtures/xbar_r3/` + `tests/fixtures/xbar_organism/`):
- ✓ **XBAR UNIFIED onto exact-integer O_K substrate** — ten receipts GREEN/honest-negative (2026-06-18). G-R3-BIND-on-OK Leg A GREEN (`0019b86`); Leg B honest-negative (`d7d96fe`); organism-native FFT-ripped-out GREEN (`1f0f6be`); G-R2-FROB integer store GREEN (`dbe4103`/`d076797`); G-R2-FROB-ENTROPY negative (`e6d17bb`); G-R3-MOBIUS negative (`1e70763`); G-XBAR-ORGANISM-FULL GREEN (`15e7051`); G-T2-WEIGHTS negative (`ac76c8e`); G-PERIOD6-REBASE GREEN (`d2d7ceb`). **Period-6 rebase + host-numpy→native Z_q/NTT port both CLOSED here.**
Previously closed (all on record, nothing in flight):
- ✓ **C2 Memo curator CLOSED** Steps 1–3.1 + #222 + G-XBAR-ORGANISM step 1 GREEN (2026-06-17). Contracts: `CONTRACT-XBAR-C2-memo-curator-loop.md`.
- ✓ **Ring-3 Path A CLOSED** R3.1→R3.4 GREEN, parameter-free (2026-06-17). Contract: `CONTRACT-XBAR-R3-consolidation.md`.
- ✓ **XBAR P3 CLOSED** P3.0→P3.4 GREEN (2026-06-17). Contract: `CONTRACT-XBAR-P3-ring-on-exec.md`.
- ✓ **GNA EAR CLOSED** on physical silicon (2026-06-17). Contract: `CONTRACT-KAIROS-K0-K1.md §7.4–7.6`.
- ✓ **G-KAIROS-1 6h soak GREEN** (2026-06-16); KAI-1/1b/1c CLOSED; KAI-2 CLOSED-BOUNDED; KAI-3 CLOSED GREEN. Contract: `CONTRACT-KAIROS-K0-K1.md §5.5–5.9, §6.6, §7.3`.
- ✓ **Phase C alloc-shrink + C-c NIAH CLOSED** (2026-06-14). §P3.2-b-2b LSH 8× +0.47% CLOSED (2026-06-13). Contracts: `CONTRACT-XBAR-P3-ring-on-exec.md`.

## 2. The decision queue (locked order — do not reshuffle without the operator)

1. **▶▶ T4 Frobenius π^k quantization of the 9.4 GB model WEIGHTS (2026-06-18).** This is the validated lever — Frobenius cancellation, 6-sig-fig on Gemma3-1B, per-tensor π^k scale is FREE (no propagation), now operational on the Ring-2 episode store (G-R2-FROB). Apply it to the *weights*: embedding / FFN / attention tensors. **NOT Möbius** — G-T2-WEIGHTS proved Möbius fails its own object (trained embeddings have no multiplicative index structure; composite-row reconstruction worse than random). Pre-register the quality gate (top-1 / PPL deflection vs the OK_Q4B baseline 4.6665) before coding; the bit-width is the lever (cf. 12b 2.86× / 16b 2.0× / 24b 1.36× on episodes). No budget (local 2060).

2. **▶ KAIROS post-organism state.** With the organism loop closed native, the next agency-axis step is the resident KAIROS loop over the unified substrate. Scope to be set against the existing KAIROS contracts.

3. **Hygiene queue (non-blocking; pick up when convenient).**
   - #220 cudaEvent journal-tax (exact per-tick overhead; wall-clock floor on 2060 makes it noise otherwise).
   - `gemma4_kv_decode` first-token boundary reconcile (the #222 OPEN from 2026-06-14; kv-path seam alignment with the one-shot `SP_XBAR_EMB` path).
   - Compact-slab globals wrap-rewind (slab + SWA-ring journal = the joint regime; not exercised yet).
   - P3.4 larger-N multi-chunk hardening run (the named pre-public lever; deterministic, not noise-flippable, just a wider corpus run).
   - G-R3-PROV provenance tag (Ring-3 deferred item; the Z_q/NTT engine port is now DONE via Leg A + organism-native).

## 3. Open threads (persistent small items)

- HF model bucket `KnackAU/sp-diffusion-stage` — staged for diffusion/spec-decode prototypes; no active run.
- WSL gcloud unauthed (fine; Windows is canonical).
- HF-token path: `_xbar/p2b` scripts read `archive/notes_and_stuff/claude-hf-token.txt`; `creds/claude-hf-token.txt` is the authoritative path — keep in sync or repoint scripts.

## 4. Standing watch procedure

No pods, no RunPod balance to check. Before any new cloud run: `check_pods.py` (any pods?) → verify `papers/RUNBOOK-cloud-compute.md` pattern → per-unit upload in the loop → verify-then-terminate. ⬢
