# SESSION-HANDOFF.md — where things stand

**Updated:** 2026-06-14 (XBAR P3 + Phase C CLOSED → **KAI-1 / 1b / 1c CLOSED GREEN** (heartbeat NO_OP, O(1) bit-exact
rewind, wrap-aware journaled ring, semantic crucible) → **G-KAIROS-1 ≥24h soak RUNNING** (PID 16412) → doc audit +
keystone + public papers 07-10 staged. Prior: P3.2-b-2a SWA RING SHRINK GREEN → **§P3.2-b-2b GLOBAL SPARSE RECALL MECHANISM CLOSED**
→ **M_GEMMA4 hygiene GREEN** (12B CUDA PPL ctest locked to `-b1`, SP PPL 4.6665 vs 4.6776) → **LARGER-N G2 VERDICT:
4× GREEN +1.65% / 8× RED +4.17% on the frozen router** — small-N deflection was an illusion; W-probe maps the Pareto
frontier (floor +3.74% @ W=64) → **§3q learned lane OPENS with measured justification**). Update this file at
every session end or major handoff. Read AFTER `prompt.md` + `ENVIRONMENT.md`, BEFORE anything.

---

## 1. IN FLIGHT right now (check these first)

- **▶ G-KAIROS-1 ≥24h SOAK IS RUNNING (launched 2026-06-14 ~11:11, `test_gemma4_cuda.exe` PID 16412).**
  `run_kairos_soak` (SP_G4_KAIROS_SOAK) loops the deterministic 24-event tape on the journaled-ring metal
  with per-loop re-anchor (bounded state), streamed/flushed telemetry, and in-process hard tripwires
  (CUDA / semantic-safety / pos / 3-consec-malformed / 5-consec-latency / VRAM-leak >256MiB / thermal >87C).
  **NO VERDICT FROM A MID-RUN LOG.** Monitor: `Get-Content shannon-prime-system-engine\results\kairos_soak.log -Tail 5`.
  Kill if GPU needed: `Stop-Process -Id 16412` then `nvidia-smi --reset-gpu-clocks`. **Watch item:** a slow VRAM
  creep (+59 MiB by loop 84) — either a per-loop close/reopen leak (the VRAM tripwire fires a clean abort ~loop 360/~6h)
  or cross-process nvidia-smi noise. Clocks: core pinned 1680; **the 2060 cannot lock its memory clock** (unsupported).
- **KAI-1 / 1b / 1c CLOSED GREEN this session** (engine through `b0d2bf6`, lattice `f3ab5be`): KAI-1 heartbeat NO_OP
  discipline; KAI-1b O(1) bit-exact rewind (G-1b-REWIND-NULL, metal 0.0073 vs prefix-grow 0.924 s/action);
  KAI-1c wrap-aware journaled ring (G-1b-WRAP-NULL byte-exact, 40 owners clobbered diffs=0) + journaled-ring O(1)
  telemetry + the `run_kairos_metal` semantic crucible (24 ticks: 0 false / 0 missed / 0 drift). Contract §5.5-5.8.
- **Doc audit + rewrite (2026-06-14):** new keystone `CURRENT-STATE-OF-PROJECT.md`; engine README promoted KAIROS into
  current-state; public `Position_Is_Arithmetic` surfaces refreshed + papers 07-10 staged (operator-signed-off, pushed).
  No leaked VMs/pods/schtasks; RunPod balance $0.
- **Open hygiene (non-blocking):** #220 cudaEvent journal-tax; #222 `gemma4_kv_decode` first-token boundary; compact-slab
  globals wrap-rewind; optional `papers/` archive reorg (~130 SESSION-CLOSED files).
- **▶ §P3.2-b-2b GLOBAL SPARSE RECALL — MECHANISM CLOSED GREEN 2026-06-13 (engine `a0b8d42`).** Built null-first:
  Phase 0/1 bit-exact (shadow `sp_arm_select_geom` + projk oracle-parity mism=0, live output unchanged) → G2 PPL
  deflection 4× −0.31% / 8× −3.21% **inside the locked < 2.0%** (OK_Q4B `-b1` baseline 4.6665 == gold; the plain
  `gemma4-12b.sp-model` is the coarse QAT variant @ 7.4M PPL — USE `-b1` FOR PPL) → G1 served-off-disk **bit-exact**
  (`SP_ARM_PAGE`: NaN-poison live globals + sparse page off Ring-2; gather-from-disk == gather-from-live diffs=0).
  Flags `SP_ARM_SHADOW`/`GATHER`/`PAGE` + `SP_ARM_B/W/SINK/R`, gates `SP_ARM_GATE`/`SP_ARM_PAGE_GATE`, byte-inert off.
  **FOLLOW-ONS STATUS:** (1) larger-N G2 — **DONE 2026-06-13 (G-P3-R2.b-2b-N).** Full wikitext-2 val corpus, N=2048×3
  = 3072 scored positions. The small-N (42-pos) negatives were noise: **4× = +1.65% GREEN, 8× = +4.17% RED**; W-probe
  {4,64,128} floors at **+3.74% @ W=64** (the frozen ±1 router's 8× Pareto frontier — high-projected-score keys it can't
  rank, not a window problem). **4× (B=512) is the locked v0 frozen-router operating point at N≤2k; 8× is RED on static
  geometry → triggers the lock-#4 §3q escalation.** projk oracle-parity bit-exact across 262,016 selections. Fixture
  `tests/fixtures/ppl/wiki.valid.g4tokens.txt` + bats committed (engine `587c8d7`). (2) the literal alloc-shrink —
  STILL OPEN (v0 allocs globals at full `P` + host-selects; alloc `B+sink+W` + device-side select = the real VRAM cut).
  (3) **M_GEMMA4 mis-registration** — **DONE (engine `51bdb76`):** `test_gemma4_ppl_cuda.c` default → `-b1`, registered
  `M_GEMMA4_CUDA_PPL` ctest GREEN (SP PPL 4.6665 vs oracle 4.6776, −0.24%).
- **▶ §3q ORACLE CEILING — 8× IS LEARNABLE (2026-06-13, G-P3-R2.b-2b-ORACLE, engine `dab7d36`).** Before training,
  measured the selection ceiling. `SP_ARM_DUMP` hook (engine `08d4d79`, reuses the shadow seam) dumped post-RoPE
  per-position K/q on the 8 globals over the 3 N=2048 windows → offline diagnostic (`_xbar/p2b/phaseA_diag.py`): exact
  top-B captures 96.7%/92.3% of attention mass at 4×/8× — **gemma globals are DIFFUSE, not concentrated**. Then
  `SP_ARM_ORACLE` (`k_qk_scores` GPU + host min-heap top-B → gather) measured the **on-engine oracle PPL: 8× = 5.1512
  (−0.08%), 4× = 5.1544 (−0.01%)** vs FULL 5.1551 — both GREEN. **8× is NOT information-bounded; the frozen +4.17% is
  100% router quality** (the diffuse 7.7% dropped mass is noise — C2.1 denoise on real wikitext).
- **▶ §3q LEARNED-LSH WINS 8× = +0.47% PPL — §P3.2-b-2b CLOSED GREEN (2026-06-13, G-P3-R2.b-2b-LSH, engine `222463a`).**
  Trained a single shared **512×32 projection R** (forward-KL distillation of the true attention dist + 0.2 hard-neg
  hinge + learnable τ; `tools/xbar_lsh/train_lsh.py`, GPU 0.8s/ep on the 2060 — **CUDA torch 2.6.0+cu124 now installed**).
  Deployed via `SP_ARM_LSH=M.bin` (M=R·Rᵀ, select=top-B by (Mq)·K, reuses `k_qk_scores`+`k_apply_M`, **zero new hot-path
  kernels, cost independent of r**). **G2 8× (N=2048×3): LSH r=32 = 5.1791 = +0.47% GREEN** vs frozen +4.17% RED, oracle
  −0.08%. **8× won on a 16,384-param matrix at v0 inference cost.** Weight: `tests/fixtures/lsh/lsh_M_r32.bin`. With SWA
  ring (b-2a) + globals at B, **KV decouples from context.**
- **▶ §3q Phase C ALLOC-SHRINK in progress (2026-06-13).** **C-a DONE (engine `7195100`):** `SP_ARM_DEVSEL` moves top-B
  onto the GPU (`k_topb_dev`) — selection-invariant (5.1791==5.1791), severs the host round-trip (unblocks graph capture
  + C-b). **C-b.1 DONE (engine `7cd7482`):** `SP_ARM_LSH_R=R.bin` projected-key **sidecar** — selection scores the r=32
  resident `RᵀK` (16× smaller than full K), not full K. The KEY ARCHITECTURE FINDING: you can't rank evicted keys, so the
  compact-slab shrink REQUIRES this resident r-dim router state. Gate +0.24% (deflection-invariant; sidecar is the truer
  r-dim form, slightly better than M-path +0.47%). Weight `tests/fixtures/lsh/lsh_R_r32_raw.bin`. **▶▶ NEXT = C-b.2 (the
  actual VRAM cut):** cap the 8 globals' `dKc/dVc` at `B+sink` slots (not `P`); page the selected union from pinned host
  RAM (Ring-2 backend, option-a) into compact slots `[0,m)`; remap the gather absolute→compact-slot. Gate = output-invariant
  + `nvidia-smi` flat-line at 32k. THEN C-c (G1 NIAH under poison w/ learned router) → P3.3/P3.4. Contract: §P3.2-b-2b +
  -N/-ORACLE/-LSH run-records (Phase C receipts land at C-b.2 VRAM gate).
- **(superseded) §P3.2-b-2b SPEC-LOCK note — the spec is now implemented + gated.**
  The contract section + 4 immutable parameter locks are in CONTRACT-XBAR-P3 §P3.2-b-2b. v0 = frozen `sp_arm_select_geom`
  ±1 projection router on the 8 global owners (host shadow-select → `read_block(off[L]+ri[j]·kvd·4)` pages only the
  selected set → new `k_attn_decode_gather` index-list kernel attends recall-set+sinks+recent-W; SWA keep the b-2a ring;
  globals alloc `B+sink+W` not `P`). Knobs `SP_ARM_B/W/SINK/R`. Gate `G-P3-R2.b-2b` (NON-bit-exact, the first one):
  **G1** NIAH needle ≥ full-attention with the live global cache NaN-poisoned (HIT only off Ring-2) + **G2** PPL-deflection
  **< 2.0%**, both strictly **within ≤ 8× / N ≤ 2k** (32k/64× = ungated, do NOT report past the band — C2.4-cliff lesson);
  top-1 retention reported non-gating; §3q learned two-stage shortlist→verify is the fallback lever, un-rested ONLY on a
  v0 breach. Proposed v0 phasing is in the chat log (shadow-select-then-log first, then the gather kernel, then the gate).
  See [[feedback_exact_to_heuristic_gate_shift]].
- **(superseded) prior NEXT-SESSION note: DRAFT the spec** — done 2026-06-13. The XBAR bare-metal
  C/CUDA substrate is CLOSED (read-path / write-spill / paged-read / SWA-ring all bit-exact, engine `1a08d3d` =
  the definitive baseline). b-2b crosses into the KAIROS **policy** domain. **THE DOMAIN TRANSITION (the thing to
  hold):** the substrate gates were `diffs=0` because they preserved 100% of keys + the exact reduction order;
  sparse top-k recall DROPS keys by construction → the reduction tree changes, logits drift, **bit-exactness dies
  by definition.** So the b-2b gate is NOT `diffs=0` — it is a **pre-registered bounded-degradation** gate:
  (a) PPL-deflection ceiling, (b) needle-HIT retention (HIT off sparse recall where b-1 HIT from full attention),
  (c) top-1 coherence tolerance. **PRE-REGISTER THE BOUND BEFORE ANY CODE** (the P2.b no-goalpost-move discipline —
  bind hands before the telemetry lands). The §3q evidence already shapes the answer: top-1 0.462 = sub-usable sole
  sniper, top-5 0.77 = shortlister → the router MUST be **two-stage retrieve-verify** (top-5 shortlist → verify
  against the live query), the verify step riding on b-1's proven page-in. Only the 8 global owners (kvd=512) remain
  context-linear; b-2a already made the 40 SWA owners constant. See [[project_p31_decode_wiring_green]] + CONTRACT-XBAR-P3
  §P3.2-b-2a + [[feedback_exact_to_heuristic_gate_shift]].
- **P2.b CAMPAIGN CLOSED ✓ 2026-06-12** (CONTRACT-XBAR-P2b §3p/§3q). GENERATION dead at k=2 (6 forks
  all convicted: capacity/k-sweep/grok/context/KV-prefix/RoPE — the wall is the objective↔task
  mismatch, NOT channel width). RECOGNITION real-but-sub-usable (Fork-6 contrastive addressing
  **top-1 0.462 < 0.50 PASS ⇒ REST**, no goalpost move; 15× chance, beats native 3.3×; top-5 **0.77**
  = shortlister-not-sniper DOOR → two-stage retrieve-verify is a P3/KAIROS architecture choice, not
  more epochs). Lane rests; memory cells get a heuristic/two-stage addresser, not a learned sole-top-1.
- **P3.1 + P3.1b-1 + P3.1b-2 ALL GREEN ✓ 2026-06-12 — THE READ-PATH IS COMPLETE** (every rung bit-exact
  on the real 12B, host 2060). Read-path ladder: off[L] mirror read ✓ → serialized episode from disk ✓ →
  prepended episode as history ✓ (recall-as-history: pre-load episode into cache front `[0,H)`, decode
  prompt at `[H,..)`; fix = seed `dpos=H` since the loop-skip bypassed `k_incr_pos`; continuation ==
  monolithic, diffs=0). See CONTRACT-XBAR-P3 §P3.1 run-records (G-P3-1 / G-P3-1b / G-P3-1b-2). Built on the
  **VS2022/VS18 BuildTools host** (cl 19.50 has `<stdatomic.h>`; VS2019 can't build the CUDA tree),
  `build-cuda-vs22`.
- **P3.2-a SHADOW SPILL GREEN ✓ 2026-06-12 — WRITE-PATH STARTED** (the inverse of the read-path).
  `SP_XBAR_SPILL=dir`: per-step, after the layer loop writes `dKc/dVc[L][pos]` for all owners, batch-async-D2H
  all owner rows into one pinned buffer + ONE sync + `write_block(off[L]+pos·kvd·4)` through the `sp_arm_ring2_backend`
  stdio ABI (the CPU `decode.c` Ring-2 twin; owners only, **0 sharer blocks**). Gate **G-P3-R2.a** (in-engine at
  `download:`): read each spilled block back + memcmp vs final live-cache D2H → **diffs=0** at DEC (P=16, 5.2 MiB)
  AND the 259-position velocity decode (85.3 MiB), `TEST_EXIT=0`, no leak. Store length = `store_bytes − last-owner
  unwritten-slot` confirms the `[0,P-1)` byte law. **PERF CAVEAT:** per-step-sync spill serializes the longer
  decode (the pinned-overlap optimization is a P3.2 follow-on; null/identity-first held). Engine `cuda_forward.cu`,
  all behind `SP_XBAR_SPILL` (byte-inert off). Scratch `_run_p32a.bat`. CONTRACT-XBAR-P3 §P3.2-a run-record.
  device cache shrinks toward sink+W per owner.
- **P3.2-b-1 PAGED-READ GREEN ✓ 2026-06-12 — the spill∘page CLOSED LOOP runs.** `SP_XBAR_PAGE=dir` (implies spill).
  Per step: page-in `[0,pos)` from Ring-2 (`read_block(off[L])` → H2D, one read/H2D per owner, `[0,pos)` contiguous)
  at loop top → layer loop writes `pos` live + attends `[0,pos]` → spill `pos` → **POISON** `[0,pos]` (`cudaMemset 0`)
  so next step MUST page it back. Gate **G-P3-R2.b-1** (in-engine, `SP_XBAR_PAGE_GATE=1`): legacy full-cache decode vs
  paged decode → **token-identical, diffs[4..16)=0** (both `2 10 100 1000 497 564 …`), `TEST_EXIT=0`, no leak. The poison
  is the rigor — the live cache is provably not the source, so every read came off disk through `off[L]`. **The model's
  whole history lived on disk and fed attention bit-exactly.** **SCOPE (honest, told the operator):** this is the recall
  READ proof, NOT a VRAM shrink — globals attend ALL positions so they can't drop below `ctx` without *sparse* recall (the
  router); page-in reconstructs into the full-size cache. Engine `cuda_forward.cu` (page-in + poison, behind `SP_XBAR_PAGE`,
  byte-inert off). Scratch `_run_p32b.bat`. CONTRACT-XBAR-P3 §P3.2-b-1 run-record.
  **NEXT = P3.2-b-2 THE SHRINK (G-P3-R2.b-2):** SWA owners alloc'd at sink+W + a two-source attention kernel (window-from-cache
  + recalled-from-staging); globals get sparse top-k recall via the router (the P2.b §3q two-stage retrieve-verify door) —
  that's where VRAM finally decouples from context length. This is the real paging win and it needs a kernel change + the router.
- **P3.2-b-2a SWA RING SHRINK GREEN ✓ 2026-06-12 — the FIRST REAL VRAM WIN, bit-exact on 40/48 layers.**
  Refinement caught: gemma SWA is a PURE sliding window (no sinks) → the window is always live → nothing to page →
  the shrink is a `W`-slot RING, not the two-source-with-paging kernel (that's the globals' b-2b). SWA owners (`L<kvfs`,
  `!global`) alloc `Wring=min(W,P)` slots (globals keep full `P`); live write → `slot pos%Wring` (eviction free); new
  `k_attn_decode_ring` reads the window in POSITION order `(s0+j)%Wring` → fp reduction byte-identical to the full kernel.
  Flags `SP_XBAR_SWA_RING` + `SP_XBAR_SWA_W=<w>` (window override for cheap gating). Gate `SP_XBAR_SWA_GATE=1`: full-cache
  window-4 vs ring-of-4 → **token-identical, diffs[4..16)=0** (P=16 wraps the ring 3×), `TEST_EXIT=0`, no leak. **WHY IT'S
  THE WIN:** the 40 SWA owners carry the *dominant* kvd=2048 (vs globals' 512) — capping them at `W` turns the ~21 GB-@-32k
  SWA term CONSTANT (~0.67 GB @ W=1024); only the 8 small globals still scale (~1 GB @ 32k). Engine `cuda_forward.cu`
  (`k_attn_decode_ring` + ring alloc/write/dispatch, behind the SWA flags, byte-inert off). Scratch `_run_p32b2a.bat`.
  CONTRACT-XBAR-P3 §P3.2-b-2a. **NEXT = P3.2-b-2b the GLOBAL shrink:** sparse top-k recall on the 8 global owners via the
  P2.b §3q two-stage retrieve-verify router (the KAIROS plug-in point) — the last context-linear term; this is where the
  read-path (b-1, proven) + the SWA shrink (b-2a) compose into full VRAM-decoupled-from-context. It is a SEPARATE domain
  (needs the §3q top-5 shortlister), not substrate-only.

## 2. The decision queue (locked order — do not reshuffle without the operator)

1. **Horizon verdict — DONE 2026-06-12: ASYMPTOTE-FOUND ~0.28, DATA-WORKS (provisional/single-seed).**
   Data lever confirmed + exhausted → Fork-4 (#2) is now unblocked (information-vs-channel). ✓
2. **Fork-4 — contextualized-state input (RUN FIRST; the SP-native fix, operator-driven 2026-06-12)**
   — instead of learning context (Fork-3's cross-attention), feed the adapter the FROZEN 12B's own
   context-resolved residual state at the span positions — it already computed the integration; read
   it, don't re-learn it. **BUILT + toy-smoked 2026-06-12:** `--ctx-state --ctx-layer L` (default off
   = byte-inert), taps `forward_logits` after layer L, slices span positions `[CTX,CTX+N)`, ZERO new
   params. Rig ready: `bootstrap_ctxstate.sh` + `launch_pod_ctxstate.py` (context-free baseline + the
   L-sweep {12,24,36} as a matched pair in one pod, per-run upload, self-terminate). Spec = CONTRACT-P2b
   **§3o** (gate G-P2b-CTXSTATE: **LIFT = information-limited**, **KILL = k=2 channel-limited** — the
   clean adjudication §3k left open). Leakage guard = readback primary + prefer earliest-lifting layer.
   LAUNCH gated on horizon read + an operator budget go (default cheap 16k-corpus fast read ~$2–3;
   horizon-matched 1.4M corpus is the confirm).
3. **Fork-3 conditioning** (the dumb-ML baseline, in the chamber) — `--conditioning`, built+smoked
   `75f316f`, +32k params, CONTRACT-P2b §3n. Fire only if Fork-4's null needs a capacity-bearing
   cross-check. Then **InfoNCE/contrastive** if neither context play closes the gap (batch-negative
   refactor of train_p2b.py).
   - **VSA / Harmonic Binding → Ring-3 ONLY** (design banked 2026-06-12, `papers/DESIGN-VSA-ring3-holographic.md`):
     condemned for Ring-0/1 steering (manifold shock — the 1-vs-6-layer result IS the evidence; exact
     spectral inverse unstable → use the involution; sm_75 NTT is ALU-bound not TC) and relocated to its
     native home as the Ring-3 holographic associative-consolidation tier (gate G-R3-VSA: must beat a
     hash-indexed Ring-2 on capacity-per-byte + partial-cue completion, else retire). Opens with K1/NIGHTSHIFT.
4. **wd-grok probe** — **CLOSED-as-SHELVED 2026-06-11** (CONTRACT-P2b §3k; receipts HF
   `results_grok/grok/`). Ran the precondition (train-subset vs val on d1024L3 49.9M, bf16 gold,
   3 seeds): **HARD UNDERFIT** — 3-seed median TRAIN recovery 0.203 ≈ VAL 0.175 (delta +0.027,
   deltas straddle zero), a third of the 0.60 memorization bar. The adapter cannot memorize its
   own train set ⇒ no phase-1 ⇒ weight decay has nothing to force. Permanently shelved; confirms
   NOT-CAPACITY, converges with k-sweep onto Fork-3 (information-limited). $0.16 on the A6000.
5. **P3 ring-on-Exec — NOW THE ACTIVE LANE (P2.b closed).** CONTRACT-XBAR-P3 RATIFIED; 5-gate ladder.
   **P3.0 CLOSED GREEN** (manifest + standalone gate, system `9a2b0a9`). **P3.1 decode-wiring CLOSED
   GREEN 2026-06-12** (G-P3-1: `SP_XBAR_RECALL_SELFTEST` off[L] indirection in gemma4 CUDA decode;
   recall decode seq == legacy, token-identical on real 12B). **P3.1b-1 serialized-store CLOSED GREEN
   2026-06-12** (G-P3-1b: `xbar_episode.c` linked into `sp_engine_cuda`; `SP_XBAR_RECALL_WRITE/LOAD`
   serialize→disk→deserialize→mount→decode == legacy, token-identical; caveat = read-only LOAD store
   must cover the window). Engine `cuda_forward.cu` seam ~2154; contract §P3.1 run-records.

   **P3.1b-2 recall-as-history — CLOSED GREEN 2026-06-12 (G-P3-1b-2; THE READ-PATH IS COMPLETE). ▶ NEXT = P3.2 write/consolidation** (the inverse: spill stale live-cache → episode store). The design below was the plan; the actual fix was **seed `dpos=H`** (the loop-skip over the pre-loaded episode bypassed `k_incr_pos`, lagging the device position counter the packed embed indexes with — diagnostic-found, not reasoned). Continuation == monolithic, diffs=0 on the 12B. [historical design ↓, now implemented:] Wire the
   loaded episode as PREPENDED history the current prompt attends back over (`[episode ++ prompt]`).
   **THE OFFSET PLAN (operator-specified, bank-don't-touch-tired):** inject a static token-length offset
   `P_offset = P_episode` into the sequence-position tracker (`dpos`) BEFORE the main prompt decode loop
   evaluates; inside the decode kernels (`k_attn_decode` + `_win`/`_dyn` variants) shift the linear
   indexing for positional embeddings (RoPE) and attention-mask lookups so live prompt tokens register
   at `pos + P_offset`; the read path treats the loaded episode's flat `off[L]` blocks as an absolute
   historical baseline (positions `[0, P_episode)`), preventing index clashing/overwrites in the active
   KV-cache. **Claude's added mechanism note:** this is a DUAL-SOURCE read — attention must span
   `[episode-store(0..P_ep) ++ live-cache(P_ep..)]`, NOT the current pure-redirect (P3.1b-1 replaced ALL
   reads with the store; recall-as-history reads the store for history AND the live cache for the
   prompt's own positions). RoPE is coherent for free: the episode's stored K was already roped at its
   write-time positions `0..P_ep-1`, so a query roped at `pos+P_offset` gives the correct relative phase.
   GATE = bit-exact vs the monolithic `[episode++prompt]` decode (NOT model-finds-needle — that confounds
   12B NIAH skill). The needle demo rides on the green gate. Then → P3.2 write/consolidation → P3.2b Ring-1.
6. **Stage KAIROS** — registered, OPENS ONLY after P2.b/P3 close (`ROADMAP-KAIROS.md`).

## 3. P2.b state in one breath — CLOSED 2026-06-12

GENERATION dead at k=2 (every arm convicted: capacity/k-sweep/grok/context §3o/KV-prefix §3p/RoPE).
The wall is the **objective↔task mismatch** (continuation-KL demands a generative sufficient statistic),
NOT channel width (k-sweep flat). RECOGNITION (Fork-6 §3q contrastive addressing) is real-but-sub-usable:
32-way top-1 **0.462 < 0.50 PASS ⇒ REST** (pre-registered, no goalpost move); 15× chance, climbs, beats
native-key 3.3×; **top-5 0.77 = shortlister-not-sniper DOOR**. Lane RESTS; the path is a two-stage
retrieve-and-verify KAIROS loop (architecture, not more epochs). Full chain: CONTRACT-XBAR-P2b §3g→§3q.
Trainer `_xbar/p2b/train_p2b.py` (staged HF `KnackAU/xbar-p2b-run`) carries `--contrastive` (AddrAdapter,
B×B InfoNCE, N-way gate, honest controls); receipts HF `results_contrastive/ct1/`.

## 4. Landed this session (receipts)

- **#115 CLOSED + 12B text-in LIVE**: GEMMA4_BPE dispatch 5432/5432 both lanes, roundtrip 60/60
  (engine `3457a41..3253a82`, core `9d3cc72`); blob regen + SHA re-pair all four 12B pairs +
  `T_G4_TOK_12B_PAIRED` + B1 GPU decode smoke 6/6 (engine `d8ba947`). Gold `.pre115` backups →
  `G:\My Drive\shannon-prime-cold\pre115-2026-06-10\`.
- **G-P3-GEOM substrate** (core `64b698c`): sp_arm_*_geom API, legacy delegates, T_ARM_GEOM
  26/26. + gemma4.c owner bounds guard, standalone frobenius link fix, T_FRO_5 v2 align
  (core `c608b2f`). Suite restocked green from H:\ (E_CPU_9 disposition: AVX2 reassociation
  `5e443c9` → scalar pin `5cd5870`).
- **CONTRACT-XBAR-P3 drafted** (`aabafec`) + §3b audit corrections (V-less IS real on the 12B;
  KVD-const is 12B-only) — pointer in C1-lite §3b (`3d42477`).
- **Stage KAIROS registered** (`ROADMAP-KAIROS.md` + `CONTRACT-KAIROS-K0-K1.md`, `a4d8f71`):
  the sp-kernel thesis (turn = memory artifact; tick/interrupt/yield mapped to gated SP
  primitives), CosySim/NEXUS/Project X = KAI-0 reference corpus (adopt/adapt/reject done).
- **DESIGN-diffusion-lane** (`038dd0d`): T8 drafter = headline; recall-time gist upsampling
  FORBIDDEN; consolidation-time ε-instrument; Exec stays AR.
- **Doc fleet**: all four repo READMEs modernized; public site's stale 32k-HIT hero CORRECTED
  (PIA `1d52e85`); Roadmap agent-nav box; engine root swept to `_bake/` (`7914429`) +
  `.gitattributes` line-ending physics (`7ab91a7`); `shannon-prime-papers` repo DELETED
  (PIA is the only series repo).
- **Environment build-out**: Colab CLI lane live (T4 smoke green); gws + gcloud installed and
  authed (project `sp-ppt-arm-lat`, Drive smoke green); credentials registry created
  (`ENVIRONMENT.md` §1); ecosystem = HF PRO + Colab Pro + GitHub Pro + RunPod + Drive 5TB +
  GCloud.

## 5. Open threads (small, don't lose)

- New HF model bucket (operator 2026-06-11) — **repo id = `KnackAU/sp-diffusion-stage`** (RESOLVED;
  the air-gap for speculative-decode + MoE / DiffusionGemma prototypes). Push target for the
  diffusion/spec-decode lane; banked in memory `reference-hf-diffusion-bucket`.
- `.pre115` backups: D: copies deletable once operator confirms Drive uploads complete.
- WSL gcloud unauthed (fine; Windows is canonical).
- **HF-token path fixed 2026-06-11:** the creds-registry restructure MOVED the token into
  `creds/claude-hf-token.txt`, but `_xbar/p2b` scripts read the old `archive/notes_and_stuff/
  claude-hf-token.txt` → `fetch_horizon`/etc. were dead. Restored the synced duplicate at the old
  path (ENVIRONMENT §1's "keep in sync"). DURABLE FIX TODO: repoint scripts to the `creds/` path
  so a future move can't re-break them.
- E2B/12B per-stage artifact assignments for P3 are pinned in CONTRACT-P3 §4 — drafting agent
  noted §3b's geometry line conflates the two artifacts.
- The operator floated zeta-PE / prime-harmonic positional encoding (his CosySim
  `apps/prime_encoding` research) as a future lattice-native experiment — parked, unbanked
  beyond this line.

## 6. Standing watch procedure

`check_pods.py` (any pods?) → `fetch_horizon.py` (receipts/STATUS) → verdict ONLY on
STATUS=DONE (no reads from partial logs — the §3g lesson) → §3m matrix → contract run-record +
STATE line + memory + commit/push. The watch holds. ⬢
