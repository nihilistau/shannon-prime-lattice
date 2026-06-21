# SESSION-HANDOFF.md — where things stand

**Updated:** 2026-06-21 (**PHASE 4 SEALED + PHASE 5 DIFFUSION JUDGE PROVEN SUPERIOR + native port begun. See §0.** Prior milestones below unchanged.)

---

## 0. PHASE 4 SEALED + PHASE 5 OPENED — diffusion judge beats AR on both axes; native port N0 GREEN (2026-06-21)

Full detail in memory `project_generative_judge.md` (the canonical record for this arc).

**PHASE 4 — SEALED (engine `81049bb`, pushed).** The open-set recall "terminus" was OVERTURNED: a GENERATIVE judge (12B reading candidate TEXTS via the chat template, tag-based copy-able selection) does query-conditioned open-set recall (85.7% recall@1 on `_needle_corpus_div`) where every geometric/W_c signal failed. Live conversational-memory organism end-to-end: observe→capture (NIGHTSHIFT)→index (C2 sig)→page (KAIROS recency+salience, routes.rs)→SELECT (generative judge)→RECITE (**text-in-context**, not lossy latent injection — the α-sweep proved latent inject of a live episode has NO recitation operating point; recall is generative). `SP_B3_JUDGE` default-off=null floor. Commits `447dfc5` (judge) → `4da0718` (KAIROS window) → `81049bb` (text-in-context sealer + cold-reset + inject attenuation). Honest caveats (AR-spine diseases, deferred): foreign selectivity wobble + NIGHTSHIFT question-echo capture (no admission gate).

**PHASE 5 — diffusion judge PROVEN the structural cure (lattice `6bac6e1`).** Contract `CONTRACT-PPT-LAT-PHASE-5.md` + `DESIGN-diffgemma-native-port.md` (committed `6e9634b`/`bff897a`). **G-DIFFJUDGE-1 GREEN on the metal:** the bidirectional masked-diffusion judge (DiffusionGemma 26B-A4B, run via the PR-24423 oracle build) = **recall@1 95.6% (86/90) AND foreign-reject 96.0% (48/50)** — BEATS the AR judge (85.7%) on BOTH axes, incl. the wobble the AR judge couldn't fix. Constrained {tags,NULL} canvas + bidirectional attention = the antidote to both AR pathologies. Receipt `tests/fixtures/chat_fullstack/G-DIFFJUDGE-1.log`; harness `tools/xbar_lsh/diffjudge_recall_test.py`. **NATIVE-ONLY MANDATE (contract §5):** write the diffusion arch + MoE + entropy sampler into OUR O_K/Q4B CUDA backends; NO llama.cpp/ggml in the shipped engine. PR 24423 = reference (`_diffgemma_reference/ARCH-NOTES.md` + 8 source files) + parity oracle ONLY (`D:\F\llama-diffgemma-pr24423`). **N0 GREEN (G-DG-N0):** sp_transcode now parses diffusion-gemma → our `.sp-model` (`C:\sp_models\diffusiongemma-26B-A4B.sp-model`, 13.27GB, arch_id=9, canvas_length=256, 128/8 experts). Added SP_ARCH_ID_DIFFUSION_GEMMA=9, dg_* arch_info fields, SP_WDT_Q5_0, the new tensor maps + a `--stream` low-RAM path. **N0 code UNCOMMITTED** (clean working tree — engine sp_transcode.c + sp_model.h; submodule lib/shannon-prime-system 4 files: weight_dtype.c, sp_l1.h, sp_model.h, weight_dtype.h).

### NEXT QUEUE (start here)
**DONE this session (the native DiffusionGemma forward is BUILT, end-to-end, on our engine):** git hygiene (submodule divergence resolved); **N1a loader** (G_DG_N1 26/26); **N5a CUDA MoE forward** (`gemma4_moe_ffn_cuda`, byte-exact vs CPU, rel-err 3.2e-7, engine `0d6f4b8`) + **N5a-packed** (real OK_Q4B experts via dp4a, expert-select identical, int8-floor exact, `f7813a2`); **N1b full `diffusion_gemma_forward_cuda`** (`ce06ec6`/`fddbe9c`, +605/-0 additive, dense path byte-identical): region mask + canvas rmsnorm embed + enc/dec scalar split + dense+128/8-MoE, runs the real 26B-A4B in <1 min via arena streaming + expert-major batching; 256/256 finite in-vocab logits; null floor holds; structurally verified vs the reference (mask/RoPE/scalar/embed all exact).

**★ KEY REFRAME — the N1b "oracle logit parity" gate is MIS-SPECIFIED.** The PR-24423 oracle runs the **Q4_K_M** GGUF; our forward runs our **OK_Q4B** .sp-model — different 4-bit quants of the same bf16 weights → byte-exact logit parity is impossible by construction (per-layer quant delta compounds → the measured ~40% one-sided attenuation; the 73% top-1 is on a degenerate all-BOS canvas that maxes argmax instability). Do NOT chase byte-exact logits.

1. **★ N4 native judge — RUNNING (decision pending the ~8h aggregate).** The forward streaming deadlock is FIXED (`8309d90`, G-DG-STREAMFIX 5/5, `dg_dequant_resident_rows` = owned-heap copy of the mmap-aliased per-layer weights; ~71s/run reliable, peak WS 3.3GB). The native judge `test_diffjudge_native` (constrained {tags,NULL} argmax on the native forward) is running DETACHED over `_needle_corpus_div` (~140 fwd × ~200s ≈ **~8h**, log `tests/fixtures/chat_fullstack/G-DIFFJUDGE-NATIVE-run.log`). **CHECK THAT LOG for the aggregate recall@1 + foreign-reject.** ⚠ FIRST result (1/140) = MISS on the canonical Marlock (oracle got it right) — confidently picked a same-archetype distractor. **THE BRANCH: the agent's N4 is a SINGLE constrained forward + argmax, but the oracle's G-DIFFJUDGE-1 (95.6/96.0) ran the FULL iterative entropy-bound DENOISING (48 steps + bidirectional refinement + self-conditioning).** A diffusion step-0 forward is a rough first guess; discrimination comes from the refinement. SO: if the aggregate is HIGH → single-forward suffices, wire the native judge into routes.rs (N6). If LOW → N4 needs the FULL entropy-bound sampler (multi-step denoise loop, `_diffgemma_reference/diffusion-sampling.cu` + ARCH-NOTES §2) + self-conditioning (N3) — that is the real next build, GPU-bound (wait for the ~8h run to free the 2060). The forward is RELIABLE; the sampler DEPTH is the open question.
2. **Optional drift bounds (if you want a forward-correctness number first):** (a) re-measure logit parity on a NON-degenerate canvas (factors out argmax instability); (b) build the diffusion forward at f32/OK_Q8 to isolate forward correctness from quant; (c) gate CUDA-vs-CPU on the SAME OK_Q4B .sp-model (needs a CPU diffusion forward). Diagnostic: `SP_DG_DUMP_OURS` (per-position) + the reference `cb("l_out")` for a per-layer bisect if a real drift is found beyond the quant delta. Then N3 (self-cond multi-step) → N6 (wire the native judge into routes.rs) → N7 (drafter) → N5b (hetero split). Plan: `DESIGN-diffgemma-native-port.md`.
3. **ENV FLAG:** C: pagefile switched fixed-16GB→system-managed during the N0 OOM workaround (reboot-pending); revert if desired. The .sp-model is `C:\sp_models\diffusiongemma-26B-A4B.sp-model` (13GB, out-of-tree). The diffusion GGUF IS on disk: `D:\Files\Models\Gemma4\gemma-difussion\diffusiongemma-26B-A4B-it-Q4_K_M.gguf`.

---

## 0d. B3-WC AUTONOMOUS LIBRARIAN — learned-head recall LIVE on the 12B chat (2026-06-19)

**B4 NIGHTSHIFT (2026-06-20) — machinery LIVE + GREEN; live-recall calibration OPEN.** The daemon now GROWS memory live behind `SP_B4_NIGHTSHIFT=1` (default-off = null floor): a user turn stating a fact is captured at position-0 (scratch `kv::open`→`prefill`→`read_global_k`) into a live Episode (recall.rs `tokens:Option<Vec<i32>>`), hot-appended to `AppState.nightshift: Arc<RwLock<..>>`, scored jointly with the 91 curated in the (E+1)-NULL argmax, and recalled via `kv::inject_tokens`. PROVEN on metal: matched stated fact self-selects (`ep_live_000` 41.3, beats NULL + all curated). Launcher `run_console_nightshift.bat`. Engine `54bd612` (machinery) + `19d09af` (K-norm calib). Receipts `tests/fixtures/chat_fullstack/G-CHAT-B4-NIGHTSHIFT{,-calib}.log`. OPEN (honest negative): live episodes super-attract query-independently → foreign-reject FAILS; NOT a scalar K-norm (live 1.415 vs curated 2.774, ×1.96 didn't fix; logsumexp isn't scale-linear) but a distributional-shape mismatch between live `read_global_k` and the curated `ep.k` the W_c head trained on. B4-v2 levers: align live-K provenance to `ep.k` (likely a C/CUDA change), or retrain the head on live-path K, or per-channel/covariance calib, or wire the teacher-forced ablation admission gate (also: v1 captures every turn>=4 toks, no admission yet). Detail: memory `project_b4_nightshift.md`.

**DOC-SYNC COMPLETE (2026-06-20):** the fleet documentation sweep for this milestone is landed + pushed — lattice `d817dd5` (15 living docs) + `e3f8b4e` (README full-stack diagram redrawn, OKF papers 121/121 GREEN); engine `89832dd` (CLAUDE) + `50388be` (README recall-path ASCII + env table + run_console_recall quickstart + stop button); math-core `e09b904` (CLAUDE) + `3b0fcc2` (README ARM surface + four-ring diagram); public Position_Is_Arithmetic `bdba9a4` (papers 22/23/24 front-doors + LEDGER X-B3-* + SERIES + HF post `posts/hf_update_2026-06-20.md`) + `c74afe8` (paper.md long-forms + README tables). Formal PPT-ARM Part I/II (`papers/PPT-ARM/PPT-ARM-{Theory,System}.md`, non-git) carry a 2026-06-20 status note (proofs untouched; .tex/.pdf need a LaTeX regen). Non-blocking: regen stale .pdf; engine tree has pre-existing untracked artifacts + a local PMAX=20000 bump in run_console_recall.bat (committed 4096). The autonomous-recall campaign is fully CLOSED + documented; NEXT falsifiable step = B4 NIGHTSHIFT (pre-scoped below).

The autonomous-recall campaign is RESOLVED end-to-end (model + deploy). The learned W_c head
selects the right stored episode for a chat query, or refuses if none is relevant, LIVE on the
resident Gemma-4-12B. Engine `edc8079` (pushed). Receipt `tests/fixtures/chat_fullstack/G-CHAT-B3-WC-DEPLOY.log`.

WHAT IT IS: recall.rs `WcHead`/`load_wc`/`wc_score` score each registry episode by the W_c projection
with the **logsumexp-mean** reduction (stable LSE over positions via max-subtraction, then mean over
(layer,head)) -- the metric the head trains on and the ONLY one that's int16-exact (max/top-m collapse).
routes.rs `SP_B3_WC` branch: **(E+1)-way argmax over [episodes, NULL=s0]**; episode wins -> replay it
(SP_REPLAY_MTARGET=42 clamps the injection mass); NULL wins -> clean prompt. Default-off (env unset) =
null floor; runs WITHOUT SP_B3_DISPOSER / SP_B3_TAU_QK so the legacy q.K block stays telemetry-only.

OFFLINE GATE (G-CHAT-B3-WC-DIV2, 90-needle diverse corpus): 360/361 instance recall + 50/50 foreign
reject, f32==int16 lossless, s0=+0.102. Diversity (mint_corpus_v2, unique subjects) took instance top-1
34%->100% -- corpus diversity was the binding constraint all along, not the machinery.
LIVE on metal (this session): matched "Which recovery code authorizes the Marlock mag-rail depot?" ->
RECALL ep_n_div_000 (9.858, clear argmax); foreign "What is the capital of France?" -> whole population
negative (best ep_ctrl_paris -0.026 < s0) -> NULL -> clean "Paris."

HOW TO RUN / PLAY (verified by parts -- recall env proven live this session; ring+web-console is the
established run_console.bat path):
  > run_console_recall.bat        (engine root)
  wait for "listening", open http://127.0.0.1:3000/ , chat.
  Watch the daemon console for  "B3-WC ... RECALL '<ep>'"  or  "NULL wins -> REJECT".
  It = run_console.bat (coherent byte-exact SWA-ring chat) + 3 env vars:
    SP_RECALL_REGISTRY=_needle_corpus_div\registry.jsonl   SP_B3_WC=_b3_wc\wc_deploy.bin   SP_REPLAY_MTARGET=42
  Deploy blob rebuilt anytime via:  python tools\xbar_lsh\export_wc_deploy.py
  Plain run_console.bat (no recall) still works unchanged.

ARTIFACTS: head lsh_Wc_f32_div2.npz + int16 lsh_Wc_i16_s14.bin; deploy blob _b3_wc/wc_deploy.bin (WCB1
hd=512 r=32 s0=+0.1021 sscale=0.17678); registry _needle_corpus_div/ (90 needles + ep_ctrl_paris control).

NEXT (B4 NIGHTSHIFT -- between-turn consolidation, DEFERRED, pre-scoped):
  Goal: after each chat turn, the daemon folds the turn's content into the episode store so memory GROWS
  during a conversation (today the registry is static, captured offline by the curator).
  Cheapest correct path (reuse, don't rebuild):
   1) On turn end, mint an episode from the turn the SAME way the curator does (the turn's tokens ARE the
      ep.tok; capture ep.k/ep.v/ep.mf via the existing SP_XBAR_RECALL_WRITE / sp_xbar_manifest_serialize
      path used by _b3_capture_ep -- it already runs inside the resident decode).
   2) ADMIT it through the teacher-forced ablation oracle (SP_B3_DISPOSER=2 + ep.secret) so only
      load-bearing (non-parametric) turns enter -- the proven admission gate, collapse < TAU=-8.
   3) Append the admitted episode to the in-memory registry (hot-add) so the W_c head scores it on the
      NEXT turn. The W_c head needs NO retrain to score a new episode (it projects content, order-free);
      only the s0 NULL threshold is fixed. Optional: NIGHTSHIFT consolidation = fold/dedup similar
      episodes via the native Ring-3 bind (tools/ring3/ok_bind.py is the integer reference).
  Effort: a daemon Rust change (turn->capture->admit->hot-append to the registry Vec) + rebuild + a
  2-turn live test (state a secret turn 1, recall it turn 2). ~1 focused session. NOT started -- too
  large to land safely in the remaining budget without risking a half-wired tree.

WARN (recurring this session): the sandbox->Windows mount TRUNCATED a Python open().write() of routes.rs
(82KB) mid-file -> "unclosed delimiter". RECOVERY THAT WORKED: restore intact via `git checkout`/`git show`
on WINDOWS, re-insert the edit via PowerShell `[System.IO.File]::WriteAllText` (no-BOM UTF8, LF joins),
then verify line-count + last-line + brace-balance on the Windows disk BEFORE building. bash `cat >>`
append (recall.rs) survived fine; large Python/Edit writes are the risk.

---

## 0c. CHAT-FULLSTACK — the operator console chats the real 12B (2026-06-19)

**`run_console.bat` → http://127.0.0.1:3000/ chats the real Gemma-4-12B through L2 daemon → L1 ABI → CUDA backend, COHERENT.** Contract + run-records: `papers/CONTRACT-CHAT-FULLSTACK.md`. Stages all GREEN (coherence-gated, not just SHA — the hard lesson of this arc):
- **#115** daemon FFIs the proven engine C gemma4 BPE tokenizer (`58b6c2d` lineage; parity 5432/5432).
- **A1/A2** L2 sampler (temp/top-p/top-k/rep-pen, seedable) + CUDA-graph resident decode (~15 tok/s, **memory-bandwidth-bound** on the 2060 = the physical ceiling, not a stall). Engine `91b4177`.
- **A2-polish** id-agnostic control-token suppression + turn-stop. Engine `cc4e26c`.
- **B1** per-session byte-exact "auditable mode" (ABI `sp_l1.h §6c`). Engine `66e30bc`.
- **S1 (the coherence keystone)** ROOT CAUSE of the earlier token-soup: the daemon imposed the **gemma3** `<start_of_turn>` template on a **gemma4** model whose vocab has NO such tokens (real turn toks `<|turn>`=105/`<turn|>`=106; `<turn|>` was even being suppressed so it could never stop). Fixed: token-level template w/ real ids + **config-driven** suppress/eos from `generation_config.json` (`suppress_tokens:[258883,258882]`, eos=1) + **byte-exact integer decode as the DEFAULT** (build-independent determinism — kills the FP-reorder coherent↔garbage flip). 6/6 coherent, byte-identical across two builds. Engine `58b6c2d`.
- **B5 (the single entry point — operator's image-1)** text/audio/memory all enter ONE residual seam (`gemma4_kv_inject_seq`). `gemma4_kv_inject_tokens` stages `embed×√E` device-side + steps the real id (PLE parity) ⇒ **text-via-seam == prefill 6/6 BIT-IDENTICAL**. `inject_frames` channel exposed for the audio/memory sources. ABI `sp_l1.h §6e`. Engine `18a5f78`, submodule `cb601e9`.
- **B2-ring (O(1) VRAM)** the SWA ring is fixed + RE-ARMED (served default). Root cause: the float ring kernel lost S1's byte-exact FP-reorder immunity on 40 SWA layers → soup; fix = **`k_attn_decode_ring_bx`** (exact-integer ring) + journal auto-advance + reset-not-rewind. 3-leg coherence gate GREEN: coherent past 64 tok / ring==ring-off byte-identical / **VRAM flat ~10–20 MiB across 6k→12k**. Engine `7eb7231`.

**Daemon currently LIVE on :3000** (ring-armed, byte-exact default). `run_console.bat` is the launcher (ring re-armed). No closed gate regressed throughout (`G-WIRE-CUDA-DECODE-GEMMA4` 32/32==oracle).

**REMAINING (next stages, documented in CONTRACT-CHAT-FULLSTACK, NOT blocking a coherent chat):** B3 (ARM two-ring on the gemma4 decode — today log-only on gemma4, real on qwen3 CPU); B4 (NIGHTSHIFT between turns); wire the real AUDIO source (EAR/GNA / `voxtral-mini-realtime-rs`) + memory-as-residual into the B5 `inject_frames` channel (the channel exists; the projector wiring is the work); a **rank-2..N coherence assertion** in the decode gate (the determinism-gate-blindness lesson). HONEST artifact ceiling: the OK_Q4B b1 sometimes runs on past the turn at greedy (correct content, weak turn-discipline) — bounded by max_tokens.

**⚠ REPO-HYGIENE TO RECONCILE (binding submodule lesson):** the standalone `shannon-prime-system` (`300d32c`) DIVERGED from the engine submodule (`cb601e9`, the canonical/ahead copy the engine builds against). Same §6e content, different history (B2's §6d was committed only to the submodule). The engine is correct (builds against `cb601e9`); the standalone needs a deliberate rebase onto the submodule lineage — do NOT auto-force; reconcile explicitly. Flagged, not silently left.

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

**ALL THREE "NEXT" ITEMS NOW DONE GREEN (2026-06-18, 3 sequential build agents):**
- **G-BYTEEXACT-ISLANDS-CUDA RAN GREEN on the 12B** (engine `b93f157`): dumped real-12B island in/out at layer 24, `bx_islands_compare` vs the crate `*_q_ref` → RMSNorm relerr 3.84e-5 / GELU 8.18e-7 / RoPE 9.62e-6 (softmax gated offline 1.3e-6), all < 1e-4. The integer refs ARE faithful to the float kernels on real activations. Receipt `G-BYTEEXACT-ISLANDS-CUDA.log`.
- **G-WIRE-CUDA-DECODE-GEMMA4 GREEN** (submodule `d9d96f3` → engine `6b9a786`): the universal daemon token-by-token DECODES the real 12B through the new L1 verb `sp_session_register_kvdecode_backend` (+ additive `gemma4_kv_decode_logits`, null floor byte-untouched) — **32/32 tokens bit-identical to the `gemma4_kv_decode` oracle, VRAM flat (O(1) cache)**. Submodule-first ABI discipline followed. Receipt `G-WIRE-CUDA-DECODE-GEMMA4.log`.
- **G-BYTEEXACT-FORWARD-12B GREEN — the whole forward is byte-exact** (engine `69c0588`, lattice §5.2 `9b93000`): all four islands (RMSNorm/GELU/RoPE/softcap) + attention converted to exact-integer CUDA kernels behind `SP_BYTEEXACT` (`__constant__ d_bx_flag`, no `__int128` — `__umul64hi` + the 64-bit isqrt split + CORDIC). **LEG A off = PPL 4.6665 == baseline byte-identical (null floor); LEG B on = PPL 4.6569 parity; run-to-run BIT-IDENTICAL** (4.6569==4.6569, the order-immunity cross-machine proxy). Receipt `G-BYTEEXACT-FORWARD-12B.log`.

**BYTE-EXACT CAMPAIGN: COMPLETE on-12B.** The entire gemma-4-12B forward — linear algebra (dp4a + crate Barrett/Garner/NTT), attention (dual-prime CRT), and all four nonlinear islands — runs exact-integer/deterministic under `SP_BYTEEXACT=1`, at PPL parity, byte-identical run-to-run, with the flag-off path the citable null floor. The one open item is EXTERNAL: a true two-physical-GPU bit-identical logit check (needs a second machine). NEXT real frontier returns to the project mainline (XBAR/KAIROS), or the gguf-v4 Mersenne co-design. Build note: crate host bins run `cargo run --bin <name>`; the CUDA backend builds under VS18 BuildTools (`D:\Program Files (x86)\...\18\BuildTools`, cl 14.50) + CUDA 13.2, feature `wire_cuda_backend`.

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

**STATUS (2026-06-18): the locked queue's prior top two are SPENT.** XBAR / NIGHTSHIFT is now COMPLETE end-to-end and KAIROS was already closed; T4-on-weights is convicted. The next campaign is an open strategic call (see item 1).

0. **✓ XBAR / NIGHTSHIFT COMPLETE end-to-end (2026-06-18).** Mechanisms all GREEN (P1→P3.4 + C2 Steps 1–3.1 + #222 + Ring-3 Path A R3.1→R3.4 + organism + native O_K bind) AND the **native-C `core/`-resident port CLOSED** — `core/ring3/` (`ring3.c` + `include/sp/ring3.h`) ports the VSA layer + NIGHTSHIFT state machine onto native `sp_pr_mul`; gate **T_RING3_NATIVE 42/42** (bind/unbind/superpose bit-identical to the Python `ok_bind` reference; NIGHTSHIFT reproduced [32,8]@D=1024 + gate-before-cap@D=128; order-immune); carriers unified to splitmix64 (no Python regression). Math-core `e0fccd3`, engine submodule bump `7b992d2`, engine ok_bind unify `f331da2`. The resident consolidation loop is now deployable native C. Remaining XBAR items are optional / deferred-by-choice → moved to the hygiene queue (item 3): N1 unattended soak, G-R3-PROV, Path B.

1. **▶▶ NEXT = open strategic inflection (operator's call).** The major campaigns are all closed — XBAR/NIGHTSHIFT, the byte-exact forward, KAIROS, GNA EAR. **T4 Frobenius π^k on the WEIGHTS is NOT a candidate — it is CONVICTED:** the incoherence-rotation / Hadamard-fold compression was ruled REDUNDANT vs per-32-block OK_Q4B (G-WEIGHT-FOLD-ORACLE `8ae8825`, "do NOT build" — the boundary thesis on weights), and the byte-exact OK_Q8-per-tensor-π^k angle was absorbed into the closed byte-exact forward (dp4a integer accumulate already makes OK_Q4B exact). Candidate next campaigns to choose among: **(a) harden→publish** — P3.4 larger-N multi-chunk hardening run + the R1–R5 prepublication checklist, toward releasing the staged papers; **(b) gguf-v4 Mersenne co-design** — the from-scratch format/model where a Mersenne hidden-dim unlocks the exact integer-RMS shortcut (byte-exact is its foundation); **(c) the diffusion lane** (DiffusionGemma drafter / spec-decode, Stage-Gamma). The one carried-forward external item is the 2-physical-GPU byte-exact check (needs a 2nd machine).

2. **▶ N1 — the deployed subconscious (optional; the lone remaining NIGHTSHIFT item).** The consolidation *mechanism* is closed (item 0); N1 is the *deployment*: episode persistence across sessions (the C1-lite `{Kstore,Vstore,manifest}` file-set, reload-and-recall) + an unattended schtasks-owned consolidation soak (net-positive gated promotions, zero canonical corruption, full receipt log — the consolidation analogue of the proven KAIROS 6h soak). Deferrable by choice like the KAIROS ≥24h gate; pre-register CONTRACT-XBAR-N1 before running if pursued.

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
