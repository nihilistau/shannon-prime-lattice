# SESSION-HANDOFF.md — where things stand

**Updated:** 2026-06-11 (the marathon session: k-sweep verdict → capacity arm → data arm →
horizon arm → KAIROS registration → #115 closed → env build-out). Update this file at every
session end or major handoff. Read AFTER `prompt.md` + `ENVIRONMENT.md`, BEFORE doing anything.

---

## 1. IN FLIGHT right now (check these first)

- **hor-s09** — RunPod pod `lej3uuama69mdh` (A6000): P2.b HORIZON ARM seed 20260609, epochs 8,
  pinned config (k=2, λ_read=0.25, d512/L2), fixed selector (recovery s.t. recall≥75),
  1.4M-token wikitext-103-train corpus. ~23 h run launched late 2026-06-11 AEST; 30-min salvage
  uploads to HF `results_horizon/s09/`. **Pull:** `python3 _xbar/p2b/fetch_horizon.py` (WSL).
  Verdict reads pre-registered in CONTRACT-P2b §3m (ASYMPTOTE-FOUND / STILL-RISING /
  recall-floor-breach). NOTE: s10/s11 were KILLED at launch (budget); single-seed read =
  PROVISIONAL by standing rule; 3-seed confirm when RunPod balance refreshes (~$10 left,
  ~$7.60 committed to s09).
- Colab lane: idle, zero burn (correct resting state). RunPod: only hor-s09. No schtasks.

## 2. The decision queue (locked order — do not reshuffle without the operator)

1. **Horizon verdict** (on hor-s09 DONE) → apply §3m reads.
2. **Fork-3 conditioning arm** — the KNOWN defect: `Adapter.forward(span_emb)` is context-free
   while Phase-0 golden targets were context-conditioned (train_p2b.py:179) → one-to-many
   ceiling. **BUILT + toy-smoked 2026-06-11 (`75f316f`):** `--conditioning` flag (default off =
   byte-inert), encoder ingests `[ctx ; span]`, +32k params only (7.46→7.49M toy) = INFORMATION
   not capacity — reconciles capacity-arm(NOT-CAPACITY)+k-sweep(not-k) into the info-limited
   hypothesis. Spec = CONTRACT-P2b §3n (gate G-P2b-COND + kill condition). LAUNCH only after the
   horizon read; Colab A100 fits a single prototype seed.
3. **InfoNCE/contrastive** — if conditioning doesn't close the gap (needs batch-negative
   refactor of train_p2b.py).
4. **wd-grok probe** — **CLOSED-as-SHELVED 2026-06-11** (CONTRACT-P2b §3k; receipts HF
   `results_grok/grok/`). Ran the precondition (train-subset vs val on d1024L3 49.9M, bf16 gold,
   3 seeds): **HARD UNDERFIT** — 3-seed median TRAIN recovery 0.203 ≈ VAL 0.175 (delta +0.027,
   deltas straddle zero), a third of the 0.60 memorization bar. The adapter cannot memorize its
   own train set ⇒ no phase-1 ⇒ weight decay has nothing to force. Permanently shelved; confirms
   NOT-CAPACITY, converges with k-sweep onto Fork-3 (information-limited). $0.16 on the A6000.
5. **P3 ring-on-Exec** — CONTRACT-XBAR-P3 **RATIFIED (operator, 2026-06-11)**; 5-gate ladder
   P3.0→P3.4, host-router v0, 12B/E2B split. Substrate (geom API) landed core `64b698c`.
   **P3.0 CLOSED GREEN 2026-06-11** (G-P3-0 PASS, system `9a2b0a9`): episode/owner-map manifest
   (`include/sp/xbar_episode.h` + `core/xbar/xbar_episode.c`) + standalone gate — round-trip
   byte-exact, uniform-null (qwen3 + 12B KVD-const) == legacy layout, E2B jagged == prefix-sum
   oracle. Next stage P3.1 (recall router on CUDA decode) is decode-wiring → sequenced behind
   horizon → Fork-3 → InfoNCE (no launch yet). Code may ship per-stage.
6. **Stage KAIROS** — registered, OPENS ONLY after P2.b/P3 close (`ROADMAP-KAIROS.md`).

## 3. P2.b state in one breath

Mechanism WORKS (Fork-2 readback-CE, 3-seed). k-sweep: ADAPTER-limited, k RETIRED, knee k=2.
Capacity arm: NOT-CAPACITY (4.4× params = zero recovery, recall degrades; smallest config
Pareto-optimal). **Operating point PINNED: k=2, λ_read=0.25, d512/L2 (11.3M).** Data arm:
PARTIAL (operator-ratified; selector defect surfaced+fixed; s09 hit 0.272/88; curves still
rising at 3-epoch cutoff) → horizon arm now extends to 8 epochs. Phase-0 per-span ceiling 0.94;
amortized capture ~19-27% so far. Full chain: CONTRACT-XBAR-P2b §3g→§3m.

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
