---
type: design
title: "RFC-ORGANISM — the unified recall organism as it actually stands (2026-06-21)"
description: "The current, honest-tiered synthesis of Shannon-Prime's conversational-memory organism: a served byte-exact O(1) Gemma-4-12B chat on a single latent entry point, a learned latent W_c head as the LIVE recall selector, the teacher-forced causal-ablation oracle as the ADMISSION gate, the NIGHTSHIFT offline curator, and the MEM-OKF content-addressed store (one format for agent facts AND latent episodes), receipted by PoUW. Records the boundary thesis (O_K wins on exact arithmetic / the container; a learned selector on a diverse corpus wins recall; every hand-designed number-theoretic structure-on-content lever is a measured honest-negative) and marks the native diffusion judge as the UNPROVEN open fork. Successor to RFC-XBAR; verified against the tree + git log on 2026-06-21."
tags: [design, organism, recall, w-c-head, ablation-oracle, nightshift, mem-okf, pouw, byte-exact, boundary-thesis, diffusion-judge]
timestamp: 2026-06-21T00:00:00Z
resource: shannon-prime-lattice/papers/RFC-ORGANISM-unified.md
sp_status: ACTIVE
sp_gate: "G-CHAT-B3-WC-DEPLOY (live recall) + G-NIGHTSHIFT-CURATOR (curator, synthetic) — each component carries its own gate below"
sp_commit: "engine edc8079 (W_c deploy), 7eb7231 (chat fullstack), 6107f3e (curator); math-core d9d96f3 (byte-exact)"
sp_repro: "see per-component gate rows §4; verify: git -C shannon-prime-system-engine log --oneline; read PPT-LAT-STATE.md + STATUS-MAP-2026-06-21.md"
---

# RFC-ORGANISM — the unified recall organism (current state)

**Status: v1 SYNTHESIS (2026-06-21).** This RFC describes the recall organism *as it actually stands on the metal*, with honest tiers throughout. It is the successor to [RFC-XBAR](RFC-XBAR-auditable-latent-crossbar.md) (the predecessor architecture / brainstorm that opened the latent-crossbar lane); RFC-XBAR remains the historical design record and the source of the Ring 1/2/2′/3 vocabulary. This RFC is the *current synthesis* — what is served, what is gated-but-off, and the one fork that is still unproven.

**One line.** A frozen Gemma-4-12B is served as a coherent, byte-exact, O(1)-context chat through a single latent entry point; a learned latent **W_c** head autonomously recalls the right stored episode (or refuses); a teacher-forced **causal-ablation oracle** decides what is allowed to *become* an episode; an offline **NIGHTSHIFT curator** distills raw turns into canonical episodes; and a **MEM-OKF** content-addressed store holds both the agent's don't-rebuild facts and the organism's latent episodes in one format, receipted by **PoUW**.

> **Honest-tier vocabulary (binding — from [DESIGN-FLEET-OVERHAUL-BRIEF](DESIGN-FLEET-OVERHAUL-BRIEF.md) §0):**
> - **GREEN-LIVE** — gated GREEN AND active on the served path by default.
> - **gated-GREEN / default-off** — passes its gate, behind an `SP_*` flag (null floor when unset). *NOT* "live."
> - **BUILT / WIRED** — in-tree, compiles, primitive-gated; not yet end-to-end gated.
> - **DESIGN** — spec'd, unbuilt. **UNPROVEN** — built but the deciding gate has not been won.
> - **HONEST-NEGATIVE** — measured + refuted, kept on the record.

Cross-links: predecessor [RFC-XBAR](RFC-XBAR-auditable-latent-crossbar.md) · served-chat spine [CONTRACT-CHAT-FULLSTACK](CONTRACT-CHAT-FULLSTACK.md) · curator [CONTRACT-NIGHTSHIFT-CURATOR](CONTRACT-NIGHTSHIFT-CURATOR.md) · store [MEMORY-OKF-PROFILE](MEMORY-OKF-PROFILE.md) · format [SP-OKF-PROFILE](SP-OKF-PROFILE.md) · proven ledger [PPT-LAT-STATE](PPT-LAT-STATE.md) · ground-truth audit [STATUS-MAP-2026-06-21](STATUS-MAP-2026-06-21.md) · forward plan [PPT-LAT-Roadmap](PPT-LAT-Roadmap.md).

---

## 1. The organism, end to end

```
                         a user turn arrives
                                 │
   ┌─────────────────────────────┼──────────────────────────────┐
   │  SERVED PATH  (GREEN-LIVE)   │                              │
   │                              ▼                              │
   │  Gemma-4-12B (OK_Q4B)  byte-exact, O(1) context             │
   │  single latent entry point: gemma4_kv_inject_seq            │
   │                              │                              │
   │             ┌────────────────┴───────────────┐             │
   │             ▼ RECALL (live)                   ▼ recite      │
   │   ┌─ W_c head ─────────────┐         text-in-context        │
   │   │ logsumexp-over-pos →    │         recitation of the      │
   │   │ mean-over-heads;        │         chosen episode         │
   │   │ (E+1)-way argmax over   │         (NOT lossy latent      │
   │   │ [episodes, NULL=s0];    │          injection)            │
   │   │ replay winner @ M=42    │                               │
   │   │  or reject to clean     │                               │
   │   └──────────┬──────────────┘                               │
   └──────────────┼─────────────────────────────────────────────┘
                  │ scores over the episode registry
                  ▼
   ┌──────── episode store (MEM-OKF) ───────────────────────────┐
   │  Tier-0 LUT  →  Tier-1 summary (ep.secret)  →  Tier-2 full  │
   │  addr = C2 256-bit LSH signature (latent) | sha256 (text)  │
   └──────────────▲─────────────────────────────────────────────┘
                  │ emits accepted episodes
   ┌──────────────┴──── OFFLINE (gated-GREEN / default-off) ─────┐
   │  NIGHTSHIFT curator (run_kairos_curator, SP_NIGHTSHIFT_OFFLINE)│
   │   drain PoUW ledger → distill ep.secret → ADMIT via the     │
   │   causal-ablation oracle (TAU = −8) → emit MEM-OKF record   │
   └──────────────▲─────────────────────────────────────────────┘
                  │ records each transaction (the join key)
            PoUW append-only receipt ledger (input_hash)
```

The shipped spine is the **two-stage recall plan**: *admit → store/index → bounded recall → recite*. Selection happens **geometrically in latent space** (W_c); recitation happens **in language** (text-in-context). Each turn injects **at most one** recalled episode at **bounded mass M=42** — it is one gated, mass-bounded injection, not a large RAG dump.

---

## 2. The container — byte-exact O(1) Gemma-4-12B (GREEN-LIVE)

The served chat is **coherent + byte-exact + O(1)-context** on a **single latent entry point** (`gemma4_kv_inject_seq`): text-via-seam is bit-identical to prefill, so every memory write and every prompt enters through the same door. Contract: [CONTRACT-CHAT-FULLSTACK](CONTRACT-CHAT-FULLSTACK.md), engine →`7eb7231`; launcher `run_console_recall.bat`.

The forward itself can run **exact-integer end-to-end** on the same dual-prime CRT-NTT substrate that carries the memory ring (q1=1073738753, q2=1073732609, M≈2⁶⁰ fits u64 ⇒ no `__int128`): the four nonlinear islands (RMSNorm / softmax / GELU / RoPE) + attention convert to exact-integer device kernels behind default-off `SP_BYTEEXACT`. **`G-BYTEEXACT-FORWARD-12B`** is gated-GREEN (OFF = PPL 4.6665 byte-identical null floor / ON = 4.6569 parity / run-to-run bit-identical); engine `69c0588` + math-core `d9d96f3`. **byte-exact = exact arithmetic / cross-machine determinism / AUDITABILITY — explicitly NOT compression** (the structure-on-content compression levers are convicted; see §6). The daemon drives the 12B prefill + token-by-token decode through the L1 verb `sp_session_register_kvdecode_backend` (`G-WIRE-CUDA-DECODE-GEMMA4`, 32/32 == oracle, VRAM flat O(1)).

> The crossbar and the forward share **one algebra** — the exact-integer O_K container. That is the auditability claim, and it is the only structural property the boundary thesis (§6) endorses.

---

## 3. The recall policy — three organs, three honest tiers

The recall-relevance problem RFC-XBAR §3.1 posed — *which* episode does the chat pull for a query, and how does it refuse when none fits — is answered by a **division of labour** across three organs, NOT a single signal:

### 3.1 ADMISSION — the causal-ablation oracle (the gate on what enters)
**Tier: GREEN as an OFFLINE oracle / labeler; not a live per-turn gate.**
The teacher-forced ablation knockout (`SP_B3_SECRET`, `gemma4_kv_ablate_rows`): teacher-force the known secret tokens, ablate exactly the secret's source KV rows by `cudaMemset`, score `ΣΔLL` with vs without, then O(1)-rewind. Load-bearing **novel** memory collapses ≪ −8 (e.g. `8-FALCON-7729` → −33.56); **parametric** facts the model already knows stay ≈ 0 (e.g. "Paris" → −0.15). **PINNED TAU = −8.0**; the 3-archetype matrix (high-entropy code / parametric-contradiction / relational multi-hop) shows ~16-nat separation, no overlap. Gate `G-CHAT-B3-NEEDLE-v13-MATRIX` GREEN, commit `b6470cc`. **Honest:** this needs the answer key, so it runs at corpus-mint / admission time — it is the admission oracle AND a *perfect labeler*, NOT a signal firing on every live dialogue turn.

### 3.2 RECALL — the learned latent W_c head (the live selector)
**Tier: GREEN-LIVE.**
`recall.rs WcHead`/`load_wc`/`wc_score`: relevance = **logsumexp-over-positions then mean-over-heads** through an HD=512→r=32 projection; `routes.rs SP_B3_WC` takes the **(E+1)-way argmax** over `[episodes, NULL=s0]` and replays the winner @ `SP_REPLAY_MTARGET=42` (bounded mass) or rejects to a clean prompt. Default-off (env unset) = byte-identical null floor. Gate **`G-CHAT-B3-WC-DIV2`**: 360/361 recall + 50/50 foreign-reject, int16==f32 lossless, s0=+0.102. **`G-CHAT-B3-WC-DEPLOY`** = LIVE on the metal (matched → RECALL `ep_n_div_000` 9.858; foreign → NULL → clean "Paris"). Engine `edc8079`. The deploy blob is `_b3_wc/wc_deploy.bin` (WCB1).

W_c is trained, so its binding constraint is **corpus diversity** — it routes archetype + rejects foreign cleanly, and once the corpus gave every needle a unique subject + varied carrier structure, instance top-1 went **34% → 100%**. It cannot adjudicate arbitrary unseen episodes open-world without a retrain — which is exactly what the open fork (§5) is about.

### 3.3 RECITATION — text-in-context (the mouth)
**Tier: GREEN-LIVE.**
The chosen memory's raw text is recited in-context — **text-in-context, NOT lossy latent injection.** The `α`-sweep (`SP_REPLAY_ALPHA`) proved there is no clean recitation operating point for *live-episode latent* injection (recall == hijack mass-dominance coupling). Selection is latent (W_c), generation is language (recitation).

---

## 4. The curator + the store + the receipts

### 4.1 NIGHTSHIFT — the offline curator
**Tier: BUILT + gated-GREEN on SYNTHETIC, default-off (`SP_NIGHTSHIFT_OFFLINE`); criterion-5 live PENDING.**
`run_kairos_curator` (engine `9ad7ede` step-0 B4-hook persists `ep.txt`/`ep.tok` → `9ee4668` step-1 curator → `6107f3e` the model-call extractor): on idle it iterates the live `_nightshift_live/` episode dirs, uses the **12B model-call `ep.secret` extractor** to pull the surgical invariant (not token-rarity, which a common-vocabulary novel fact would evade), runs the §3.1 ablation oracle to ADMIT (collapse < TAU=−8 → accept; parametric → reject), and emits a conformant three-tier MEM-OKF record joined to the PoUW receipt by content address. Gate **`G-NIGHTSHIFT-CURATOR`** criteria 1-4 GREEN on the synthetic 2-episode gate (novel `8-FALCON-7729` collapse −33.59 ACCEPT / parametric "Paris" 0.00 REJECT, ~33-nat sep; emit rc=0, addr-join verified). **Criterion 5 (live B4 in-distribution) is PENDING** — proven on synthetic captures only; it is NOT yet running on real chat turns. Contract: [CONTRACT-NIGHTSHIFT-CURATOR](CONTRACT-NIGHTSHIFT-CURATOR.md).

Moving NIGHTSHIFT offline is also the plausible fix for the documented **B4 distributional-shape mismatch**: live `read_global_k` differs in shape from the curated `ep.k` the W_c head trained on (the ×1.96 norm patch did not fix it → shape, not scale), so live episodes super-attract and foreign-reject fails (`SP_B4_NIGHTSHIFT`, default-off). If consolidation runs offline through the *same proven minting pipeline* (mint → capture → admit @ TAU −8 → C2 sig → registry), distilled episodes land **in-distribution** for the head — closing the recorded live-0.084-vs-curated-9.858 gap. That is Strike 1 in the roadmap.

### 4.2 MEM-OKF — the content-addressed store (one format, two callers)
**Tier: ACTIVE.**
[MEM-OKF](MEMORY-OKF-PROFILE.md) (`tools/okf_mem.py` + `memory-okf/`) is a three-tier (LUT → summary → full) content-addressed store: **agent facts** addressed by `sha256(normalized_body)[:16]`, **latent episodes** addressed by the existing **C2 256-bit LSH signature**. One format, two callers — the agent's don't-rebuild memory AND the XBAR/NIGHTSHIFT episode store share the same shape, tooling, curator, and receipt ledger. The Tier-0 LUT is tiny and always-loadable; the **`okf_mem lookup` pre-flight is binding** (before building anything, look it up — a new file for an existing capability is a defect; this project has rebuilt the same subsystems 20+ times). Gate `G-MEM-OKF-CONFORM` (`python tools/okf_mem.py verify --root memory-okf`).

### 4.3 PoUW — the receipt ledger (the join key)
**Tier: BUILT / default-off in live chat.**
`pouw_ledger.rs` (M.4 sprint) is a real append-only 64-byte `SpinorReceipt` ledger (0xA5 sentinel, atomic `O_APPEND`); each receipt carries a 24-byte SHA-256 `input_hash` domain-separated by (model_id, turn_index) — the **content-address join key** that ties a transaction to its MEM-OKF record. Wired into `daemon.rs`/`state.rs`/`/v1/receipts`; gates `G-MEMO-LOOP`/`G-MEMO-CUE`/`G-MEMO-NULL` GREEN. It is a transaction-receipt ledger today; wiring it as the NIGHTSHIFT *input* is net-new but small.

---

## 5. The open fork — the native diffusion judge (UNPROVEN, in the drawer)

The one genuinely unsettled component. The idea: replace *geometric latent* selection (W_c) with *language* selection — a native DiffusionGemma judge that reads candidate episode TEXTS and adjudicates zero-shot, no retrain. Tier: **DESIGN-ONLY / UNPROVEN, in the drawer.**

Honest status:
- The **95.6% / 96.0% figure is the EXTERNAL llama.cpp PR-24423 oracle (Q4_K_M), NOT our engine.**
- Our **native single-forward judge was FALSIFIED at ~25%** (`f8f76a5`).
- The iterative denoise loop + sampler are BUILT (`0244800`; sampler entropy err 5.8e-6, N3 step-0 memcmp==0), but the deciding gate `G-DIFFJUDGE-NATIVE-full` is still cooking and is I/O-blocked behind **N5b**, which is **design-only** ([DESIGN-diffgemma-n5b-reservoir](DESIGN-diffgemma-n5b-reservoir.md)).

**The deciding kill-test (Strike 2 in the roadmap):** an OOD head-to-head. W_c already beats the external diffusion oracle *in-distribution* (360/361 vs 95.6% on `_needle_corpus_div`); the only honest battlefield is **out-of-distribution**. Mint a held-out novel corpus W_c never trained on; run the fast `llama-diffusion-gemma-eval` oracle vs the live W_c head on zero-shot recall ∧ foreign-reject. **If the diffusion oracle does not decisively beat W_c, the Phase-5 native diffusion judge lane (incl. N5b resident reservoir) is RETIRED on the record.** The synthesis, if the judge ever earns it, is tiered (W_c does cheap Stage-1 ranking; the judge adjudicates only the top-k), not either/or — but that synthesis is not built, and the decision to spend more GPU on N5b is gated on this kill-test.

---

## 6. The boundary thesis (the keystone the whole organism bears out)

Every component above is governed by one measured boundary:

> **O_K (the exact-integer container) wins on EXACT ARITHMETIC; a LEARNED selector on a DIVERSE corpus wins RECALL; every hand-designed / number-theoretic structure-imposed-on-content lever is measured-inert and is kept as an honest negative.**

**The container wins (exact arithmetic):** native Ring-3 bind 256/256 bit-identical + reduction-order-immune (`G-R3-BIND-on-O_K`, `0019b86`); the Frobenius πᵏ integer Ring-2 store sub-ULP@24b (`G-R2-FROB`); the full organism loop native on real episodes (`G-XBAR-ORGANISM-FULL`, `15e7051`); the byte-exact forward sharing the same algebra (`G-BYTEEXACT-FORWARD-12B`).

**The learned selector on a diverse corpus wins recall:** ALL hand-designed relevance signals FAILED open-world — 6 verifiers + 4 Disposer signals (Yes/No, Δ-continuation, multi-token ΣΔLL, consensus) + cosine-qK + ΔLL-polarity, every one dominated by per-episode bias at N=3 wiki. The unlock was the teacher-forced ablation labeler on a NOVEL corpus → a learned W_c head; **corpus diversity, not machinery, was the binding constraint** (instance top-1 34%→100%).

**Content does not (honest negatives, kept attached):** split-prime O_K Dirichlet carriers (`d7d96fe`, inert); Möbius-on-M (`1e70763`, sheds memories 1.000→0.969@N=32); entropy-coding the Frob codes (`e6d17bb`, 1.02× dead weight); T2-Möbius on the real 12B embedding (`ac76c8e`, recon cos 0.032 == random); the incoherence-rotation / Hadamard-fold weight compression (`G-WEIGHT-FOLD-ORACLE` `8ae8825`, REDUNDANT vs per-32-block OK_Q4B — the "do NOT build" verdict). T4 Frobenius πᵏ on the *weights* is **CONVICTED, not next.**

---

## 7. What remains (cross-link to the forward plan)

- **Strike 1 (NIGHTSHIFT criterion-5):** re-capture real messy chat turns under the step-0 B4 hook, run the offline curator on them, prove distilled episodes land in-distribution for the live W_c head — turns the curator from gated-GREEN-on-synthetic into a real organism loop.
- **Strike 2 (the OOD diffusion kill-test):** settle §5 — retire the native diffusion judge lane unless it decisively beats W_c OOD.
- **Standing:** the SP-OKF + MEM-OKF content-addressed knowledge system is the project's permanent auditability discipline (lookup-before-build). The one carried-forward external item is the **2-physical-GPU byte-exact check** (on-machine we have run-to-run bit-identity + integer-reduction order-immunity as the proxy).

Forward sequencing + gates: [PPT-LAT-Roadmap](PPT-LAT-Roadmap.md). Proven backward record: [PPT-LAT-STATE](PPT-LAT-STATE.md). Box-by-box ground-truth: [STATUS-MAP-2026-06-21](STATUS-MAP-2026-06-21.md).
