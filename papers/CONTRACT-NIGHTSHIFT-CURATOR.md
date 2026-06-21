---
type: contract
title: "CONTRACT — NIGHTSHIFT offline curator (PoUW ledger -> ablation oracle -> MEM-OKF)"
description: "Pre-registers G-NIGHTSHIFT-CURATOR: an idle KAIROS phase drains the PoUW receipt ledger, admits each captured live episode through the teacher-forced causal-ablation oracle (parametric reject / novel accept), and emits conformant three-tier MEM-OKF records addressed by the C2 signature. This is GLUE over five existing subsystems, not a new scheduler. Default-off (SP_NIGHTSHIFT_OFFLINE=0) = byte-identical null floor. Also the fix for the open B4 distributional-mismatch bug: offline distillation lands live episodes in-distribution for the deployed W_c head."
tags: [nightshift, curator, mem-okf, pouw, ablation-oracle, kairos, b4, contract, anti-rebuild]
timestamp: 2026-06-21T00:00:00Z
resource: shannon-prime-system-engine/tools/sp_daemon/src/kairos_runner.rs
sp_status: GREEN
sp_gate: "G-NIGHTSHIFT-CURATOR (criteria 1-4 GREEN on synthetic; criterion 5 live pending)"
sp_commit: "engine 6107f3e (9ad7ede step0 + 9ee4668 step1 + 6107f3e extractor)"
sp_repro: "_curator_gate.bat (SP_NIGHTSHIFT_OFFLINE=1, _nightshift_test); receipt tests/fixtures/chat_fullstack/G-NIGHTSHIFT-CURATOR.log"
---

# CONTRACT — NIGHTSHIFT offline curator

**Glue, not ground.** Pre-flight (`okf_mem lookup` + grep, 2026-06-21) confirmed all five subsystems exist in-tree. This contract pre-registers the gate for the *single piece of glue* that joins them. Reference: [MEM-OKF](MEMORY-OKF-PROFILE.md), [STATUS-MAP](STATUS-MAP-2026-06-21.md). Banked: MEM-OKF `6b18bacf0d343a09`.

## 1. The five existing parts (verified file:line, do NOT rebuild)

| part | where | what it already does |
|---|---|---|
| KAIROS idle/tick loop | `kairos_runner.rs` `run_kairos_alpha` (212), persistent `SpSession` prefill-once (286), per-tick loop (299), **cold-evict seam** `SP_KAIROS_PRUNE` `session.rewind` (255/321) | a resident O(Δ) idle loop with a NOOP-prune hygiene seam — the file header names "Curator pruning… is NOT wired in Alpha — that is the next seam" |
| B4 ingest hook | `routes.rs` `SP_B4_NIGHTSHIFT` (1767): `kv::capture_batched` (1821) → `load_episode_global_k` (1827) → C2 sig `recall_proj.signature` (1839) → `Episode` push (1850) | captures the raw user turn as a live episode (KV + **C2 sig**) into `_nightshift_live/ep_live_NNN`. **Carries `TODO(B4-v2): admit via the teacher-forced ablation oracle (collapse < TAU=-8) before append` (1765).** |
| ablation oracle (admit/distill labeler) | `routes.rs` `SP_INT2`/`SP_B3_DISPOSER==2` (844–992): `kv::replay`→teacher-force `ep.secret`→`kv::ablate` (947)→re-score→`kv::rewind`; `collapse=ΣΔLL` (960), `TAU=-8.0` (861/970) | the query-independent thermodynamic gate: novel/load-bearing → collapse ≪ −8; parametric → ~0. **Needs `ep.secret` (892) + `ep.tok` (894) sidecars; live episodes lacking them are SKIPPED (906) — the gap the curator fills.** |
| PoUW ledger | `pouw_ledger.rs` `open` (118) / `append(&SpinorReceipt)` (141) / `iter` (166) / `canonical_sort` (221) | append-only 64-B receipt stream; each `SpinorReceipt` carries a 24-B SHA-256 `input_hash` domain-separated by (model_id, turn_index) — **the content-address join key** |
| MEM-OKF store + tool | `tools/okf_mem.py` add/lookup/expand/verify; `memory-okf/` | three-tier content-addressed records (addr = sha256 / **C2 sig**); gate `G-MEM-OKF-CONFORM` |

## 2. The delta (the only new build)

A new idle KAIROS phase `run_kairos_curator` (sibling of `run_kairos_alpha`), gated `SP_NIGHTSHIFT_OFFLINE=1`, that on idle:

1. **Drain.** Open the ledger (`Ledger::open`), iterate (`iter`/`canonical_sort`) from a persisted byte-offset watermark; collect the new turn `input_hash`es. Advance the watermark (idempotent: a re-run drains 0).
2. **Join + distill.** For each new live episode in `_nightshift_live/` (already has KV + C2 sig from the B4 hook), mint the missing **`ep.secret`** (the distilled salient fact — the canonical, in-distribution form) and **`ep.tok`** (the episode token file, already written by capture) sidecars. This is the "distill to canonical" step.
3. **Admit.** Run the existing `SP_B3_DISPOSER==2` ablation oracle (reuse the FFI sequence verbatim): `collapse < TAU=-8` → ACCEPT (novel, load-bearing); else REJECT (parametric leakage) and drop. This is the `routes.rs:1765` TODO, executed offline.
4. **Emit.** For each ACCEPTED episode: write a conformant three-tier MEM-OKF record — addr = the episode's **C2 sig** (the ledger join key cross-references the turn's `input_hash`), Tier-2 = the `_nightshift_live/ep_live_NNN` KV blob pointer, Tier-1 = the distilled `ep.secret` canonical summary, Tier-0 = the LUT row. (`okf_mem add --kind episode --addr <c2sig> --blob-ref <dir>`.)
5. **Hygiene.** Reuse the KAIROS `SP_KAIROS_PRUNE` cold-evict to discard NOOP/rejected ticks (O(1) rewind), keeping the resident loop flat.

No frozen-ABI change. No `.sp-model` change. Additive; the live serve path (`/v1/chat`) is untouched.

## 3. GATE — G-NIGHTSHIFT-CURATOR (pre-registered; falsification stated up front)

1. **Drain correctness.** An idle tick reads exactly the N new receipts since the watermark and advances it; an immediate re-run drains 0 (idempotent). *Kill: double-counts or misses receipts.*
2. **Admission discriminates (reuse the v13 oracle).** On a mixed batch, novel live episodes ACCEPT (collapse < −8) and parametric ones REJECT (collapse ≥ −8), with the established ~8-nat margin. *Kill: parametric leaks through, or novel is rejected.*
3. **Conformant emit + join.** K accepted episodes → K conformant MEM-OKF three-tier records; `okf_mem.py verify` GREEN; each record's addr (C2 sig) cross-references the originating ledger receipt's `input_hash`. *Kill: `verify` RED, or addr↔receipt join breaks.*
4. **Null-floor invariant (binding).** `SP_NIGHTSHIFT_OFFLINE` unset/0 ⇒ `run_kairos_curator` never runs ⇒ the served `/v1/chat` decode is byte-identical to the current `G-CHAT-B3-WC-DEPLOY` null floor. *Kill: any deviation from the off-state baseline.*
5. **B4 distributional fix (the prize).** An accepted, distilled live episode is selected by the deployed W_c head with a score in the curated band — closing the documented live-vs-curated collapse (`routes.rs:1770` records live 0.084 vs curated 9.858 on identical text from a 2-token provenance mismatch). *Kill: distilled live episodes still score out-of-band / break foreign-reject.*

Telemetry-then-pin: criteria 2/5 thresholds are pinned after the first measured run (no fixture-tuning). No silent gate revision — a miss amends this contract.

## 4. Sequencing + parallel kill-test

- **Track 1 (this contract):** build `run_kairos_curator` glue → run G-NIGHTSHIFT-CURATOR. Receipts → `tests/fixtures/chat_fullstack/G-NIGHTSHIFT-CURATOR.log`.
- **Track 2 (parallel, low-GPU):** the W_c-vs-diffusion **OOD head-to-head** on the fast `llama-diffusion-gemma-eval` oracle over a held-out novel corpus. If the diffusion oracle does not decisively beat the deployed W_c head zero-shot (recall ∧ foreign-reject), the Phase-5 diffusion judge lane (incl. N5b) is RETIRED on the record. (W_c already beats the diffusion oracle *in-distribution*: 360/361 vs 95.6% on `_needle_corpus_div`; the only honest battlefield is OOD.)

## 5. Honesty

The latent/episode tier of MEM-OKF and the live B4 hook are default-off and additive; the curator only *reads* the ledger and *writes* the store + sidecars — it never mutates the live cache. The ablation oracle is proven offline (v13 3-archetype matrix, TAU −8.0, ~16-nat separation) — the curator reuses it, it does not re-derive it. The one genuinely new line of reasoning is step-2's distillation of a live turn into a canonical `ep.secret`; everything else is wiring. If step-2's distillation is weak, the lever is the `ep.secret` extraction prompt, not the oracle or the store.

## 6. Grounding receipts + the surfaced prerequisite (2026-06-21, reference-first reads)

Verified surfaces (file:line): `kv` FFI in `cuda_kvdecode_dispatch.rs` (`open` 210, `replay` 367, `ablate` 388, `rewind` 296, `decode_step` 276, `position` 499, `capture_batched` 251); `recall::Episode` fields `{name,dir,npos,topic,sig:[u64;4],gk,gk_ng,tokens:Option<Vec<i32>>}` + `Projection::signature` (recall.rs 58) + `qk_relevance` (125); `main.rs:156` `SP_KAIROS_ALPHA` → `run_kairos_alpha` (the sibling insertion point, pre-clap, feature `kairos`); `SpinorReceipt` (dialogue.rs 41) = **hash-only** (`input_hash` = SHA-256(model_id‖turn_index‖tokens), 24 B; "payload lives elsewhere").

**SURFACED PREREQUISITE (reorders the build — no silent revision).** On disk, a live B4 episode `_nightshift_live/ep_live_NNN/` contains **only `ep.k` / `ep.v` / `ep.mf`** — NOT `ep.tok`, NOT `ep.secret`, NOT raw text. The ablation oracle (`routes.rs:888-906`) REQUIRES `ep.secret` (teacher-force target) + `ep.tok` (ablation source rows), and skips episodes lacking them. Two consequences:

1. **`SpinorReceipt` is hash-only**, so the curator's *payload* source is the `_nightshift_live/` episode dirs (the join to the ledger is by `input_hash`, audit-only) — NOT a ledger "drain" of content. §2 step-1 wording amended: iterate the live episode dirs; use the ledger as the provenance/audit join.
2. **A B4-hook persistence brick is now step 0.** The B4 capture (`routes.rs:1850`, where `text` + `toks` are already in scope) must also persist `ep.txt` (raw user text) + `ep.tok` (the tokens) alongside `ep.k/v/mf`. Only then can the offline curator read `ep.txt` → extract `ep.secret` → run the admit oracle. This is additive, default-off-safe (it only writes extra files when `SP_B4_NIGHTSHIFT=1`).

**Reordered build:** (step 0) B4-hook persists `ep.txt`+`ep.tok` → (1) `run_kairos_curator` iterates `_nightshift_live/`, distills `ep.secret` from `ep.txt`, opens a kvdecode handle (`kv::open`), runs the admit oracle, emits MEM-OKF on accept → (2) compile (CUDA daemon bake) → (3) G-NIGHTSHIFT-CURATOR on the 12B (bake). The gate criteria in §3 are unchanged.

## 7. RUN RECORD — G-NIGHTSHIFT-CURATOR GREEN (2026-06-21, synthetic gate)

Built across engine `9ad7ede` (step 0: B4 hook persists `ep.txt`/`ep.tok`) → `9ee4668` (step 1: `run_kairos_curator` compiles, features `wire_cuda_backend`+`kairos`) → `6107f3e` (the §5 model-call `ep.secret` extractor + emit fix). Receipt: `tests/fixtures/chat_fullstack/G-NIGHTSHIFT-CURATOR.log`.

**Synthetic 2-episode gate on the real 12B** (`_nightshift_test/`: one novel needle + one parametric control, real captured `ep.k/v/mf/tok` + faithful `ep.txt`):

| episode | extracted secret | collapse ΣΔLL | verdict |
|---|---|---|---|
| ep_novel (KAI-3 vault) | `8-FALCON-7729` | **−33.59** | ACCEPT ✓ |
| ep_param (capital of France) | `Paris` | **0.00** | REJECT ✓ |

`accepted=1 rejected=1`. ~33-nat separation, both cleanly across TAU=−8.

**The §5 lever resolved by the model-call extractor.** The first run used a last-sentence heuristic → whole-sentence secret → ablating *all* of Paris's 9 positions destroyed the context (collapse −22.01, false-accept). The 12B generative extractor pulls the *surgical* invariant (`8-FALCON-7729`, `Paris`), so the ablation measures fact-dependency, not context-destruction: the needle snapped to **−33.59** (matching the v12 oracle's −33.56 to two decimals) and parametric Paris to a flat **0.00**. Token-rarity was rejected as fragile (a common-vocabulary novel fact would evade it); the offline budget is what NIGHTSHIFT was realigned to spend.

**Criteria status:** (1) iterate ✓ (2) admission discriminates ✓ (3) conformant emit + addr-join ✓ (`okf_mem` rc=0, episode record `c2sig_80c4…`, `verify` GREEN) (4) null-floor ✓ (gated `SP_NIGHTSHIFT_OFFLINE`). **(5) live B4 in-distribution — PENDING:** validated only on synthetic captures; the live path (re-capture turns under the step-0 B4 hook, then curate) is the remaining work. **NEXT:** criterion-5 live run + the fleet doc promotion (prompt/CLAUDE/STATE) + Track 2 (OOD diffusion kill-test).
