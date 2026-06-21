---
type: project-state
title: "STATUS MAP — verified architecture ground-truth (2026-06-21)"
description: "A box-by-box ground-truth of the Shannon-Prime memory/recall organism, splitting every component into GREEN-LIVE / BUILT-DEFAULT-OFF / DESIGN-ONLY with the gate or commit next to each. Written to settle the 'two memories disagree' problem after the 72h diffusion-judge whirlwind. Verified against the tree (routes.rs branches, daemon wiring, receipt logs, git log, task ledger) on 2026-06-21 — NOT from memory."
tags: [project-state, status-map, recall, nightshift, kairos, pouw, diffusion-judge, wc-head, audit]
timestamp: 2026-06-21T00:00:00Z
resource: shannon-prime-lattice/papers/STATUS-MAP-2026-06-21.md
sp_status: GREEN
sp_gate: "audit only — each row carries its own gate/commit"
sp_commit: TBD
sp_repro: "verified via: git -C shannon-prime-system-engine log --oneline; grep SP_B3_WC|SP_B4_NIGHTSHIFT|kairos|ledger routes.rs; ls tools/sp_daemon/src/{recall,kairos,kairos_runner,pouw_ledger,memo_routing}.rs; find tests/fixtures -iname 'G-*.log'"
---

# STATUS MAP — verified architecture ground-truth (2026-06-21)

**Purpose.** Settle the recurring "two memories disagree" problem. This is a box-by-box ground-truth of the live recall organism, each component placed in one of three honest tiers with its gate or commit attached. Verified against the tree on 2026-06-21 — routes.rs branches, daemon wiring, receipt logs, `git log`, the task ledger — **not** from memory or from a summary.

**One-line verdict.** We are back on the original two-stage recall plan (admit → store/index → bounded recall → recite), and that is the good outcome. The shipped spine is real and GREEN. The diffusion judge is an ambitious, unproven, I/O-blocked upgrade to ONE stage. KAIROS / PoUW / offline-NIGHTSHIFT are built and primitive-gated but default-off in the live chat.

## Legend

- **GREEN-LIVE** — gated GREEN and active on the served `/v1/chat` path by default (or with the documented launcher).
- **BUILT / DEFAULT-OFF** — code exists, wired, has a passing gate as a primitive, but is `SP_*`-gated off in the live chat (null floor when unset). Not active unless explicitly enabled.
- **DESIGN-ONLY** — spec written, not built (or built but the real gate is unproven / still cooking).

---

## UPDATE 2026-06-21 (later) — NIGHTSHIFT offline curator GREEN + MEM-OKF ACTIVE

Promoted out of design-only, with honest tiers:

- **NIGHTSHIFT offline curator (`run_kairos_curator`) — BUILT + gated-GREEN (synthetic), default-off** (`SP_NIGHTSHIFT_OFFLINE`). Full loop on the 12B: model-call `ep.secret` extractor → teacher-forced causal-ablation admit (TAU=−8) → conformant MEM-OKF emit. **G-NIGHTSHIFT-CURATOR** GREEN criteria 1-4: novel "8-FALCON-7729" collapse **−33.59 ACCEPT** / parametric "Paris" **0.00 REJECT**, ~33-nat sep; emit rc=0, addr-join verified. Engine `9ad7ede`→`9ee4668`→`6107f3e`; record `CONTRACT-NIGHTSHIFT-CURATOR.md` §7. **Criterion 5 (live B4 in-distribution) PENDING** — proven on *synthetic* captures only; it is NOT yet running on real chat turns, so it is *gated-GREEN / default-off*, not GREEN-LIVE like the served chat.
- **MEM-OKF unified store — ACTIVE** (`tools/okf_mem.py` + `memory-okf/`, spec `MEMORY-OKF-PROFILE.md`). The content-addressed LUT→summary→full store + the `okf_mem lookup` **pre-flight** are wired into `prompt.md`/`CLAUDE.md`; the curator emits into it. The causal ablation oracle (TAU=−8) is the official admission gate; the learned **latent W_c head** (`SP_B3_WC`) is the live recall selector; the native Diffusion Judge stays in the drawer pending the OOD kill-test.

## The pipeline, box by box

### 1. Ingest & Admission — the causal ablation oracle
**Tier: GREEN (as an OFFLINE curator/labeler), not a live per-turn gate.**
The teacher-forced ablation knockout (`SP_B3_SECRET`, `gemma4_kv_ablate_rows`) separates load-bearing novel memory (collapse −33.56) from parametric facts (−0.15) at **TAU = −8.0**. Gate `G-CHAT-B3-NEEDLE-v13-MATRIX` GREEN; commit `b6470cc`. **Honest:** this runs at corpus-mint / admission time (it needs the answer key), so it is the admission oracle + the perfect labeler — it is NOT firing on every live dialogue turn. Gemini's diagram frames it as a live ingest gate; in reality it gates what enters the registry.

### 2. The filing cabinet — Ring-2 episode store + LSH index
**Tier: GREEN for HOT persistence; BUILT/partial for the cold tier.**
HOT f32-payload persistence round-trips byte-identical: `G-INT-1` GREEN (math-core `0bfdbb3`, f32 payload memcmp 0 + C2-sig Hamming 0). Episodes persist as `ep.k/v/mf/tok` sidecars; curated corpora (90-div / 200 / 300) are on disk; C2 256-bit LSH signatures exist (`G-XBAR-ORGANISM-FULL`). **Honest:** the two-tier cold pool (quarantined cold spinor + eviction) is coded in `core/arm` (cold-evict mask) but there is **no running continuous cold-tier curator** — "Optane cold store, continuously reorganized" is design, not a live daemon.

### 3. KAIROS window — temporal assembly (recency + salience)
**Tier: BUILT / primitive-gated GREEN / present in the recall path.**
`kairos.rs` (484 lines) + `kairos_runner.rs` (383) wired via `main.rs::run_kairos_alpha`; the recency-axis + cold-pool salience rescue is in `routes.rs` (the `kairos_rescued` branch: cold pool = curated registry ∪ older nightshift). Gates: `G-KAIROS-1` 24h soak GREEN (task #223), `G-CHAT-B3-JUDGE-KAIROS.log`. **Honest:** Gemini labels this "Shipped." It is built and soak-gated as a primitive, but its windowing in the live `/v1/chat` recall is bound to the B3-judge/nightshift branches, not a standalone always-on assembler. Call it built-and-wired, not sealed-as-live-default.

### 4. The selection seam — THIS IS THE FORK (see below)
**Tier: GREEN-LIVE (latent W_c) ‖ DESIGN-ONLY (native diffusion judge).**
- **Deployed, live:** the learned **W_c head** — `recall.rs WcHead`/`wc_score` (logsumexp-over-positions → mean-over-heads relevance) + `routes.rs SP_B3_WC` ((E+1)-way argmax over [episodes, NULL=s0], replay winner @ `SP_REPLAY_MTARGET=42` or reject). This selects **geometrically in latent space**. Gate `G-CHAT-B3-WC-DIV2` (360/361 recall + 50/50 foreign-reject, int16==f32); LIVE `G-CHAT-B3-WC-DEPLOY`, commit `edc8079`.
- **Aspiration, unproven:** the **native diffusion judge** (DiffusionGemma 26B-A4B reads candidate TEXTS, selects via language). The **95.6% / 96.0% is the EXTERNAL llama.cpp PR-24423 oracle (Q4_K_M), NOT our engine.** Our native single-forward judge was FALSIFIED at ~25% (`f8f76a5`); the iterative denoise loop + sampler are built (`0244800`, sampler entropy err 5.8e-6, N3 step-0 memcmp==0) but the real gate `G-DIFFJUDGE-NATIVE-full` is still cooking and is I/O-blocked behind N5b, which is **design-only** (`DESIGN-diffgemma-n5b-reservoir.md`, lattice `2f43ba6`; task #331 pending).

### 5. Recitation & synthesis — the mouth
**Tier: GREEN-LIVE.**
Chosen memory's raw text recited in-context (text-in-context, NOT lossy latent injection — the α-sweep proved no recitation operating point for live-episode latent injection). Served chat is coherent + byte-exact + O(1)-context on the single latent entry point `gemma4_kv_inject_seq`. Contract `CONTRACT-CHAT-FULLSTACK` GREEN (engine → `7eb7231`); launcher `run_console_recall.bat`.

---

## The fork that actually matters

W_c (latent, trained, cheap, **live**) and the diffusion judge (language, zero-shot, heavy, **unproven**) are being treated as competitors. They should not be:

- W_c's binding constraint is **corpus diversity** — it must be trained and cannot adjudicate arbitrary unseen episodes open-world without a retrain.
- The generative/diffusion judge reads arbitrary candidate **text zero-shot** — no retrain — but costs minutes/query today and is not native-proven.

**The synthesis is tiered, not either/or:** W_c does cheap Stage-1 ranking; the judge adjudicates only the top-k. This is exactly the "Selection Seam" with two paths — the honest version just admits the diffusion path isn't built. **The real decision to make before more GPU burns on N5b:** is the judge's I/O cost worth it over simply shipping W_c + M=42 bounded-harm? Tagline correction: "latent for selection, language for generation" describes the *shipped* system (W_c selects, text recites); the entire Phase-5 effort is trying to move selection INTO language. Pick one consciously.

---

## NIGHTSHIFT realignment — endorse, and it fixes the open bug

Returning NIGHTSHIFT to an **offline curator** (idle-woken, reads the PoUW ledger, distills raw turns into canonical fact episodes, updates the LSH/registry) is correct AND has a non-obvious payoff:

The live B4 NIGHTSHIFT consolidation is currently broken (`SP_B4_NIGHTSHIFT=1`, default-off): live episodes super-attract and foreign-reject fails. Root cause (measured, project memory): a **distributional-shape mismatch** — live `read_global_k` differs in shape from the curated `ep.k` the W_c head trained on (the ×1.96 norm patch did NOT fix it → shape, not scale). If NIGHTSHIFT runs **offline** through the *same proven minting pipeline* (`mint_corpus_v2` → capture → admit via the ablation oracle @ TAU −8 → C2 sig → registry), consolidated episodes land **in-distribution** for the head. So moving it offline is not just tidiness — it is plausibly the route around the measured wall. It reuses proven parts; the only new piece is the idle scheduler reading the receipt log.

**PoUW status (verified):** `pouw_ledger.rs` (M.4 sprint) is a real append-only 64-byte `SpinorReceipt` ledger (0xA5 sentinel, atomic O_APPEND), wired into `daemon.rs` (opens if `pouw_ledger_path` set) + `state.rs` + `/v1/receipts`. Gates `G-MEMO-LOOP` / `G-MEMO-CUE` / `G-MEMO-NULL` GREEN. **Tier: BUILT / default-off in live chat.** It is a transaction-receipt ledger today; it is NOT yet driving curation. Wiring it as the NIGHTSHIFT input is net-new but small.

---

## Direct answers (the questions that prompted this)

**Are long-term / offline memories stored currently?** Partially. Episodes + curated corpora persist on disk; HOT f32 persistence is GREEN. The B4 hook writes `ep_live_NNN` but is default-off and buggy. There is **no running offline-curation daemon** and no continuous cold tier. That is the gap NIGHTSHIFT-offline fills.

**What context does the live system run on?** Real Gemma-4-12B at **O(1) context** via `gemma4_kv_inject_seq`, byte-exact. Each turn = current prompt + **at most one** recalled episode injected at **bounded mass M=42** (or text-in-context recitation). Recall scores over the registry loaded at boot ∪ live nightshift (if B4 on). It is one gated, mass-bounded injection — NOT a large RAG dump.

**PoUW / summaries / LUT / long-term RAG?** PoUW: built, default-off, transaction-log only (above). **Summaries: NO** — there is no distillation/summary pipeline shipped; that is precisely the NIGHTSHIFT distillation gap. LUT / RAG: the LSH-C2 signature index + W_c recall over the episode store **is** the live latent-RAG analog.

---

## What this audit verified vs. did not

**Verified by code/commit/log:** the W_c deploy branch + gate; the chat-fullstack spine; byte-exact forward; the ablation oracle; HOT persistence; the existence + wiring + primitive gates of KAIROS and PoUW; the native diffusion sampler/self-cond builds; the single-forward falsification; N5b is design-only.

**Did NOT verify this pass (flag for follow-up):** whether KAIROS windowing is genuinely exercised on a default `/v1/chat` turn vs only under the B3-judge branch; the exact current value of the cooking `G-DIFFJUDGE-NATIVE-full` subset (log not yet in lattice fixtures — check `D:\F\_diffjudge_full.log`); whether any cold-tier eviction has ever run end-to-end on real episodes outside the organism smoke. None of these change the tier assignments above; they would only sharpen rows 2–3.
