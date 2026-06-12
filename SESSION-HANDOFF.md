# SESSION-HANDOFF.md — where things stand

**Updated:** 2026-06-12 (the P2.b-close → P3 push: Fork-5 KV-prefix → Fork-6 contrastive →
P2.b CAMPAIGN CLOSED → P3.1/P3.1b-1/P3.1b-2 READ-PATH COMPLETE → **P3.2-a shadow spill GREEN, write-path
started**). Update this file at every session end or major handoff. Read AFTER `prompt.md` + `ENVIRONMENT.md`, BEFORE anything.

---

## 1. IN FLIGHT right now (check these first)

- **NOTHING in flight. No leaked VMs/pods/schtasks.** All Colab sessions self-cleaned (stop-verified).
  RunPod balance $0 (no runs possible). Repos clean; engine + lattice committed (push pending below).
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
  **NEXT = P3.2-b recall + Ring-1 shrink (G-P3-R2.b):** serve an evicted needle off Ring 2 + knobs-off parity;
  device cache shrinks toward sink+W per owner.

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
