---
type: index
title: Gate-receipt registry — every headline claim → its receipt on disk
description: The claim-to-receipt loop for Shannon-Prime; maps each headline gate to the actual *.log receipt under the engine repo, the citable commit, and its status, so a reader can walk claim → evidence.
tags: [index, gate-receipt, receipts-first, byteexact, xbar]
timestamp: 2026-06-18T00:00:00Z
resource: shannon-prime-system-engine/tests/fixtures
sp_status: ACTIVE
sp_gate: G-OKF-CONFORM
sp_commit: TBD
sp_repro: python tools/okf_validate.py papers
---

# Gate-receipt registry

The receipts-first loop, made walkable: every headline gate below links to the **actual `*.log` receipt on disk**. Receipt paths are repo-relative to **`shannon-prime-system-engine/`** (the engine repo, where the gate harnesses run) unless noted. Commits are the citable anchors from `PPT-LAT-STATE.md` and the per-gate CLAUDE.md headers. Receipts marked `(path TBD)` are cited in the record but were **not** found on disk in this scan — surfaced honestly rather than fabricated.

Cross-references: the proven record is [PPT-LAT-STATE.md](PPT-LAT-STATE.md); the public claim ledger is `Position_Is_Arithmetic/LEDGER.md` (claim IDs `X-*`, `KAIROS-*`, `01-*` in the right-hand notes below).

| Gate | Proves | Receipt (engine-repo-relative) | Commit | Status |
|---|---|---|---|---|
| **G-BYTEEXACT-FORWARD-12B** | Whole gemma-4-12B forward exact-integer: OFF = PPL 4.6665 byte-identical null floor / ON = 4.6569 parity / run-to-run bit-identical (X-BX-ISLANDS) | `tests/fixtures/xbar_r3/G-BYTEEXACT-FORWARD-12B.log` | engine `69c0588` / submodule `d9d96f3` | GREEN |
| G-BYTEEXACT-ISLANDS-CUDA | The 4 nonlinear islands (RMSNorm/softmax/GELU/RoPE) as device exact-integer kernels, on-model fidelity | `tests/fixtures/xbar_r3/G-BYTEEXACT-ISLANDS-CUDA.log` | engine `69c0588` | GREEN |
| G-ISLANDS-Q-REF | Host exact-integer island references (RMS/softmax/GELU/RoPE), order-immune, RoPE via fixed-point CORDIC (no libm) | `tests/fixtures/xbar_r3/G-ISLANDS-Q-REF.log` | submodule `d9d96f3` | GREEN |
| G-BYTEEXACT-ATTN-12B | Attention `k_attn_decode_win_bx` exact-integer (negacyclic dot, device dual-prime) on the 12B | `tests/fixtures/xbar_r3/G-BYTEEXACT-ATTN-12B.log` | engine `69c0588` | GREEN |
| **G-WIRE-CUDA-DECODE-GEMMA4** | Daemon drives the 12B token-by-token via the new L1 `sp_session_register_kvdecode_backend` verb: 32/32 == oracle, VRAM flat O(1) (X-BX-WIRE) | `tests/fixtures/xbar_r3/G-WIRE-CUDA-DECODE-GEMMA4.log` | engine `69c0588` | GREEN |
| G-WIRE-CUDA-GEMMA4 | Daemon prefill/full-forward of the 12B via `sp_session_register_forward_backend` | `tests/fixtures/xbar_r3/G-WIRE-CUDA-GEMMA4.log` | engine `69c0588` | GREEN |
| **G-R3-BIND-on-O_K** | Ring-3 VSA bind 256/256 bit-identical to native `sp_pr_mul`/`ntt`; reduction-order-immune (X-OK-BIND) | `tests/fixtures/xbar_r3/G-R3-BIND-on-OK.log` | engine `0019b86` | GREEN |
| G-R3-BIND-on-O_K (Leg B) | Split-prime O_K Dirichlet carriers — operationally inert (honest negative) | `tests/fixtures/xbar_r3/G-R3-BIND-on-OK-legB.log` | engine `d7d96fe` | HONEST-NEGATIVE |
| G-R3-ORGANISM-NATIVE | Live dualroute + nightshift on native integer bind (D=1024, CAP=32) | `tests/fixtures/xbar_r3/G-R3-ORGANISM-NATIVE.log` | engine `1f0f6be` | GREEN |
| **G-R2-FROB** | Frobenius π^k integer Ring-2 episode store, rank-2 O_K lattice, a16b8 sub-ULP relL2 1.2e-7 (X-OK-FROB) | `tests/fixtures/xbar_r3/G-R2-FROB-PARITY.log`, `.../G-R2-FROB-AB.log` | engine `dbe4103` / `d076797` | GREEN |
| G-R2-FROB-ENTROPY | Entropy-coding the Frob codes — 1.02× dead weight (honest negative; lever is bit-width) | `tests/fixtures/xbar_r3/G-R2-FROB-ENTROPY.log` | engine `e6d17bb` | HONEST-NEGATIVE |
| G-R3-MOBIUS | Möbius-on-M sheds memories 1.000→0.969@N=32 (honest negative) | `tests/fixtures/xbar_r3/G-R3-MOBIUS.log` | engine `1e70763` | HONEST-NEGATIVE |
| G-T2-WEIGHTS | T2-Möbius on the real 12B embedding — recon cos 0.032 == random (honest negative) | `tests/fixtures/xbar_r3/G-T2-WEIGHTS.log` | engine `ac76c8e` | HONEST-NEGATIVE |
| **G-XBAR-ORGANISM-FULL** | Full real-episode loop: audio→C2 sig→native integer Ring-3→Hamming verify→Frobenius store→12B cache (checks=5 fails=0) (X-OK-ORG) | `tests/fixtures/xbar_organism/G-XBAR-ORGANISM-FULL.log` | engine `15e7051` | GREEN |
| **G-CHAT-B3-WC-DEPLOY** | Learned W_c head does LIVE autonomous instance recall on the 12B chat: matched->RECALL (ep_n_div_000 9.858), foreign->NULL reject (clean Paris) | `tests/fixtures/chat_fullstack/G-CHAT-B3-WC-DEPLOY.log` | engine `edc8079` | GREEN |
| **G-CHAT-B3-WC-DIV2** | W_c offline deploy gate, 90-needle diverse corpus: (E+1)-argmax over [episodes,NULL=s0] = 360/361 recall + 50/50 foreign reject, int16==f32, s0=+0.102 | `tests/fixtures/chat_fullstack/G-CHAT-B3-WC-DIV2.log` | engine `87044d8` | GREEN |
| G-XBAR-ORGANISM (write) | Audio→Ring-2 write seam, signature separation | `tests/fixtures/xbar_organism/G-XBAR-ORGANISM-write.log` | engine `6600cf4` | GREEN |
| G-PERIOD6-REBASE | C2/Ring-3 content-hash period 8→6 to the true gemma4 global layers {5,11,…,47} | `tests/fixtures/xbar_r3/G-PERIOD6-REBASE.log` | engine `d2d7ceb` | GREEN |
| G-P3-SHARED (12B) | SP_REPLAY episode-replay into the resident cache: intact bit-exact, zeroed diverges 12/12 (X-222) | `tests/fixtures/xbar_p3_replay/G-P3-SHARED_12B_GREEN.log` | engine (P3.3 lineage) | GREEN |
| G-P3-SHARED (E2B) | Same, owner-indirection on E2B (15 owners / 20 sharers) | `tests/fixtures/xbar_p3_replay/G-P3-SHARED_E2B_GREEN.log` | engine (P3.3 lineage) | GREEN |
| G-P3-PPL (P3.4) | PPL-deflection gate (<2%) on the replay path | `tests/fixtures/xbar_p3_replay/G-P3-PPL_run.log` | engine (P3.4) | GREEN |
| **NIAH (slab O(1), learned router)** | Needle survives the O(1) compaction at every depth, only with the learned LSH router; frozen ±1 = MISS (X-R2 retain leg) | `tests/fixtures/lsh/results/niah_C_d10_16k.log`, `.../niah_C_d90_16k.log`, `.../niah_B_d50_8k.log`, `.../niah_A_d50.log` | engine `8e35877` / `3218d73` | GREEN |
| G2 slab O(1) ladder | KV cache O(1) vs context: 8k vs 16k VRAM delta ~50 MiB; union cap nh·B (X-R2 realize leg) | `tests/fixtures/lsh/results/g2_cb2_8k_fixed.log`, `.../g2_cb2_16k_fixed.log` | engine `33ac632` | GREEN |
| G2 LSH select (8×) | Learned 512×32 LSH router wins 8× at +0.47% vs frozen +4.17% (X-R2 select leg) | `tests/fixtures/lsh/results/g2_cb2_measure.log`, `.../diag_8k.log` | engine `222463a` | GREEN |
| **G-KAIROS-3-AUDIO** | Real TTS speech → log-mel → GNA Conv1d+CTC → 12B pivots 7/8; EAR thesis proven | `tests/fixtures/gna_ear/G-KAIROS-3-AUDIO_7of8.log` | engine (KAI-3) | GREEN |
| G-KAIROS-3-GNA-HW | GNA front-end on PHYSICAL silicon = 0.877 == emu == FP32; EAR physically realized | `tests/fixtures/gna_ear/G-KAIROS-3-GNA-HW.log` | engine (KAI-3 / GNA) | GREEN |
| G-KAIROS-3-GNA-i16 | GNA i16 quant gate (POT GNA-native PTQ full recovery 0.877) | `tests/fixtures/gna_ear/G-KAIROS-3-GNA-i16_quant_gate.log` | engine (KAI-3 / GNA) | GREEN |
| KAIROS-02 (rewind null) | O(1) cold-evict at the metal, byte-exact rewind; O(actions)→O(1) telemetry (slope 0.0073 vs 0.924 s/action) | `results/kai1b_rewind_null_gate.log`, `results/kai1b_oactions_to_o1_telemetry.log` | engine `e06e3ae` / `0bb94f1` | GREEN |
| KAIROS-03 (ring + soak) | O(1)-space SWA ring wrap-aware rewind + full semantic daemon 6h soak | `results/kai1c_wrap_null_gate.log`, `results/kairos_soak.log` | engine (KAI-1c) | GREEN |
| G-MEMO-CUE / G-MEMO-LOOP | C2 Memo curator: discrete bit-collision resolver (r=256 LSH, Hamming gate) + propose/gate/promote loop | `tests/fixtures/xbar_c2/G-MEMO-CUE_discrete.log`, `.../G-MEMO-LOOP.log`, `.../G-MEMO-NULL.log` | engine (C2) | GREEN |
| G-222-REWIND-NULL | Ring-2 #222 persistent-KV + O(1) rewind null floor | `tests/fixtures/xbar_c2/G-222-REWIND-NULL.log`, `.../G-222-WRAP.log` | engine (C2 / #222) | GREEN |
| KAI-2 (bounded) | KAI-2 Phase-1 delivery GREEN, Phase-2 compressed packet bounded | `tests/fixtures/kai2/train.log`, `results/kai2_gate4.log` | engine `e35a227` | GREEN |
| **G-OKF-CONFORM** | Every SP-OKF bundle validates (memory 243/243, papers 119+/119+, PIA 13/13) | run live (no persisted `.log`) — see this session's verdict lines | lattice (this rollout) | GREEN |

## Honest scan notes

- **Receipts found:** all paths above without a `(path TBD)` marker were enumerated on disk under `shannon-prime-system-engine/tests/fixtures/*.log` and `.../results/*.log` in the 2026-06-18 scan.
- **G-OKF-CONFORM has no persisted `.log`** — it is the validator's live VERDICT line, not a stored receipt file. Recorded here as run-live; reproduce with `python tools/okf_validate.py <bundle>`.
- **Commits** are taken from `PPT-LAT-STATE.md` and the three repos' `CLAUDE.md` headers; where a single gate spans a commit lineage, the headline anchor is given (e.g. `69c0588` for the byte-exact forward).
- This registry covers the **headline** gates (~30 rows), not the full set — the `xbar_r3/`, `lsh/results/`, and `gna_ear/` trees hold many more build/diagnostic logs (`_build_*`, `diag_*`, `niah_err`, etc.) that are intermediate, not headline receipts.
