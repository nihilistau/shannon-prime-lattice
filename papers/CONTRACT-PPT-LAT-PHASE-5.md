---
type: contract
title: "CONTRACT-PPT-LAT-PHASE-5 — DiffusionGemma as specialist organ (drafter primary, judge proto), MoE-on-substrate gated behind a cheap signal proof"
description: "Phase 5 integration contract. T8 diffusion drafter = primary (zero-quality-risk bandwidth win). Diffusion judge = quarantined falsifiable proto, gated by G-DIFFJUDGE-1 run FIRST on the existing LMStudio bundle. MoE-on-substrate is ADAPTATION of the existing qwen35moe machinery, sequenced AFTER the signal is proven."
tags: [phase-5, diffusion, diffusiongemma, moe, drafter, judge, receipts-first]
timestamp: 2026-06-21T00:00:00Z
resource: shannon-prime-lattice/papers/CONTRACT-PPT-LAT-PHASE-5.md
sp_status: DESIGN
sp_gate: "G-DIFFJUDGE-1 (pre-registered, not yet run)"
sp_commit: TBD
sp_repro: TBD
---

# CONTRACT-PPT-LAT-PHASE-5 — DiffusionGemma, the specialist organ

## §0 Context (Phase 4 is sealed)
Phase 4 closed on the metal (engine `81049bb`): the conversational-memory organism runs observe→capture→index→page→**select** (generative AR judge, 85.7% recall@1)→**recite** (text-in-context). Two residual caveats are **diseases of the autoregressive (AR) carrier**, not implementation bugs: (1) the **selectivity wobble** — foreign queries occasionally mis-PICK an irrelevant episode (then ignore it); (2) the **echo capture** — paging can surface a NIGHTSHIFT-stored question-echo (no admission/distillation gate). The AR judge guesses relevance left-to-right, blind to the end of the candidate list.

**DiffusionGemma** (`google/diffusiongemma-26B-A4B-it`, Apache-2.0, released 2026-06-10) is the candidate structural cure: 26B-total / ~4B-active MoE, 256-token parallel **masked-discrete** block denoising, **bidirectional in-block attention**. **Hardware receipt (operator-measured):** it runs on THIS host at **30–40 tok/s** splitting 4 active experts (2 GPU / 2 CPU) through the custom LMStudio llama.cpp bundle. ⇒ **the A100 cloud lane is NOT required.** Honest counter-fact: DiffusionGemma scores **below** AR Gemma-4 (MMLU-Pro 77.6 vs 82.6, GPQA 73.2 vs 82.3, LiveCodeBench 69.1 vs 77.1). For the judge role (= reading comprehension), it brings **structural** wins at the cost of **weaker raw comprehension** — net effect is an empirical question, hence a gated bet.

## §1 Placements (priority order)
1. **T8 DIFFUSION DRAFTER — PRIMARY integration target, zero quality risk.** DiffusionGemma drafts a 256-token block compute-bound; the AR 12B verifies the block in ONE parallel forward. **Verification is exact, so drafter quality only moves hit-rate (speed), never output.** Converts the 2060's memory-bound decode into a compute-dense batch — the exact medicine for the bandwidth wall. Slots into the existing C4/MTP spec-decode machinery (the standing "needs a real draft source" negative). Inverse risk profile of every other diffusion use.
2. **DIFFUSION JUDGE — QUARANTINED R&D proto, falsifiable.** Masked-infill relevance canvas `[query | tagged candidates | ANSWER:<mask>]`, vocab-constrained to `{tags, NULL}`. **Bidirectional attention annihilates the selectivity wobble** (no primacy/recency, sees all candidates at once); **the constrained `{tags,NULL}` canvas makes parametric leak structurally impossible** (it cannot emit "Paris"). This directly targets Phase 4's two caveats — but rides a weaker model, so it is gated by §2 and **does not touch the live Phase-4 organism until it produces the receipt.**

**NON-placement (from `DESIGN-diffusion-lane.md`, retained):** the Exec does NOT become a diffusion model. Diffusion is a specialist organ; the AR spine keeps token-granular interruptibility + the XBAR KV physics (a bidirectional block model has no KV-cache in our sense — XBAR does not transfer).

## §2a TOOLING PREREQUISITE (recon 2026-06-21 — corrects the "existing bundle" assumption)
**DiffusionGemma does NOT run on mainline llama.cpp yet**, so it does NOT run on the operator's current LMStudio bundle. llama.cpp support is PR #24427 (ggml-org/llama.cpp) — UNMERGED, conflicted as of 2026-06-18, needs rebase — and it requires a **dedicated DiffusionGemma branch + a separate `llama-diffusion-cli` runner** (standard `llama-cli`/`llama-server`, which LMStudio + Ollama build on, cannot load it). The model the operator currently has loaded ("gemma-4-19B/31B-A4B DECKARD Heretic Thinking") is an **autoregressive** Gemma-4 MoE finetune — NOT the diffusion model; running the judge on it tests another AR judge (same selectivity wobble), not the bidirectional cure. **So G-DIFFJUDGE-1 is BLOCKED until one of these stands up:** (i) build the dedicated DiffusionGemma llama.cpp branch (rebase PR #24427) + `llama-diffusion-cli` — fits the 2060/heterogeneous-MoE split, real setup work; (ii) vLLM/Transformers proto (needs the A100 lane after all, PROTO-only); (iii) wait for PR #24427 to land in mainline → then LMStudio works directly. RECOMMENDED first step next session: acquire `google/diffusiongemma-26B-A4B-it` GGUF + stand up option (i).

## §2 Gate G-DIFFJUDGE-1 (pre-registered) — the cheap falsification, FIRST (once §2a tooling exists)
**Run BEFORE any engine work, on a DiffusionGemma runner (per §2a — NOT the current mainline LMStudio bundle).** Python proto, same `_needle_corpus_div` the AR judge ran (90 needles + 60 foreign). The constrained masked-infill judge must clear BOTH:
- **(a) recall@1 ≥ 85.7%** (match-or-beat the AR judge baseline), AND
- **(b) clean `[NULL]` foreign-reject** (the precise caveat the AR judge wobbled on — mis-PICK-then-ignore).

PASS ⇒ the structure-beats-comprehension bet is proven; the substrate build (§3/§4) is justified. FAIL ⇒ **honest negative: keep the AR judge for selection, use DiffusionGemma only for the T8 drafter.** Either outcome is a banked receipt.

**FINAL — GREEN (2026-06-21, oracle = PR 24423 build, full run 90 matched + 50 foreign):** **recall@1 = 95.6% (86/90) vs AR 85.7%, AND foreign-reject = 96.0% (48/50) — the diffusion judge BEATS the AR judge on BOTH axes, including the foreign-reject WOBBLE the AR judge could not fix.** The constrained {tags,NULL} canvas + bidirectional attention is the empirical antidote to BOTH autoregressive pathologies (selectivity wobble + recall). Cost: ~92s/query @ngl=20 partial offload, 48 denoise steps (the native O_K/Q4B forward + heterogeneous MoE split + prompt-KV-cache decode target exactly this). The native port (§3/§4) is JUSTIFIED. Harness `tools/xbar_lsh/diffjudge_recall_test.py`, receipt `G-DIFFJUDGE-1.log`.

## §3 MoE-on-substrate — ADAPTATION, not greenfield (verify-Gemini correction)
Gemini framed "Phase 4.5: Native Heterogeneous MoE Routing" as a from-scratch build. **CHECK THE TREE — it is largely already built (qwen35moe):**
- `tools/sp_transcode/sp_transcode.c` already parses MoE + slices experts (3D expert transcode, tasks #22–29 GREEN).
- `src/backends/cuda/cuda_forward.cu` carries the f32 router (softmax/top-k/renorm) + Z_q expert compute (15 expert/router refs).
- `qwen36-35b-a3b.sp-model` (17 GB) is transcoded + on disk; the Optane cold-tier expert paging exists (`DESIGN-diffusion-lane.md` §Hardware: "the qwen35moe machinery was built for exactly this shape").

So ~70% of "MoE routing" is **REUSE**. The **genuinely-new** pieces (these are real, and they are Phase 5 proper, not "4.5"):
- **(N1) Gemma-4-MoE arch geometry** in sp_transcode (Gemma-4 base + per-layer SWA/global + MoE FFN — distinct from the qwen35moe arch).
- **(N2) Heterogeneous live GPU/CPU expert split** (2 resident in VRAM / 2 paged from RAM-Optane), tuned for this model on the 2060. The paging concept exists; the live 2-resident/2-paged split + PCIe streaming budget is new tuning.
- **(N3) THE DIFFUSION FORWARD** — masked block denoising + bidirectional in-block attention. **Completely unlike the AR decode**; no KV-cache in our sense. This is the real new kernel and the bulk of the engine effort. Byte-exact-when-off discipline applies (a diffusion overlay defaults off = null floor).

## §4 Sequencing (receipts-first, LOCKED)
- **P5.0 (CHEAP, FIRST):** `G-DIFFJUDGE-1` on a DiffusionGemma runner — `llama-diffusion-cli` (llama.cpp PR 24423; mainline LMStudio CANNOT load it, see §2a), driven in `-cnv` conversation mode (model loaded once) via stdin/stdout. Falsify the bet before any engine work. **This is the only authorized next build.**
- **P5.1 (only if P5.0 GREEN):** adapt the qwen35moe MoE machinery to Gemma-4-A4B (N1) + the heterogeneous split (N2); `sp_transcode` DiffusionGemma → `.sp-model`; PPL/parity gate vs `llama-diffusion-cli` (oracle).
- **P5.2:** the diffusion forward kernel (N3) on the substrate; default-off null floor; gate vs the bundle oracle.
- **P5.3:** wire the **T8 drafter** (spec-decode, exact verify) — the PRIMARY integration; tok/s gate vs AR-only.
- **P5.4 (only if G-DIFFJUDGE-1 GREEN):** wire the diffusion judge as the Stage-2 selector, replacing the AR judge; re-run the Phase-4 live-loop + foreign-reject; must beat the two AR caveats.

## §5 Non-negotiables
**NATIVE IMPLEMENTATION ONLY (operator-locked 2026-06-21).** The diffusion-gemma arch, the heterogeneous MoE routing/splitting, and the entropy-bounded denoising sampler are written into OUR custom O_K/Q4B CUDA + engine backends. **NO llama.cpp / ggml dependency in the shipped Shannon-Prime engine.** llama.cpp PR 24423 is the **REFERENCE** (stashed `_diffgemma_reference/` + `ARCH-NOTES.md`) and the **PARITY ORACLE** ONLY — exactly as llama.cpp served the Gemma-4 byte-exact port (anti-contamination doctrine: read the reference with file:line, write our own, gate against the oracle). Byte-exact-when-off null floor on every overlay (verify it). The **AR 12B remains the guarantor of correctness** — the drafter is verified EXACT (quality only affects speed); the judge is gated by G-DIFFJUDGE-1 (never trusted unproven). Receipts-first: no number without a reproducing command + a LEDGER row. Honest negatives stay attached. The Exec stays AR. Run the OKF validator (`G-OKF-CONFORM`) on this bundle before commit.

## §6 Honest risk register
1. **Weaker model may not clear G-DIFFJUDGE-1** → the judge placement dies, the drafter survives (still a win). Most likely failure mode; cheapest to test → tested first.
2. **The diffusion forward is a large new kernel** (bidirectional, no KV-cache; XBAR does not transfer) — N3 is the real cost.
3. **Heterogeneous PCIe expert streaming** on the 2060: the operator's 30–40 tok/s is via llama.cpp; our byte-exact O_K/Q4B path may carry different latency — measure, don't assume.
4. **sm_75 weak tensor ALU** compresses diffusion's 4× (the blog's own footnote) → on the 2060 the diffusion win is a **capability** win (bias-free judge / leak-proof reject / block-drafting against the bandwidth wall), not necessarily raw speed.
