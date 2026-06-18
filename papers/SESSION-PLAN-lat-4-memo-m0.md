---
type: session-handoff
title: Sprint M.0 — Memory model artifact (PROTOCOL BRING-UP STUB) — PLAN
description: "1. Phase 4-MeMo roadmap block — papers/PPT-LAT-Roadmap.md:5772-5956"
tags: [session-handoff, memo]
timestamp: 2026-05-30T00:39:37Z
resource: shannon-prime-lattice/papers/SESSION-PLAN-lat-4-memo-m0.md
sp_status: ACTIVE
sp_gate: none
sp_commit: TBD
sp_repro: none
---
# Sprint M.0 — Memory model artifact (PROTOCOL BRING-UP STUB) — PLAN

## Stage 0 — Reference reading (citations)

1. **Phase 4-MeMo roadmap block** — `papers/PPT-LAT-Roadmap.md:5772-5956`
   ("Phase 4-MeMo — Memory-as-a-Model on the heterogeneous CRT mesh
   (FILED 2026-05-30)"). M.0 specified at `5853-5857`:
   > **M.0 — Memory model artifact (prerequisite).** Either fine-tune
   > Qwen3-0.6B on a target factual corpus via SFT (~hours on single
   > GPU), or stub with a known-different checkpoint for protocol
   > validation. Without M.0, M.1+ are hypothetical.

2. **Current Executive model state** — discovered at
   `D:\F\shannon-prime-repos\shannon-prime-system-engine\build-cpu\tests\qwen3_rt.sp-model`
   (754,551,808 B / ~720 MB, sha256 prefix `30717fbd...f122376`,
   `LastWriteTime 26/05/2026`). Source: transcoded from
   `Qwen3-0.6B-f16.gguf` (at `D:\Files\Models\Qwen\Qwen3-0.6B-GGUF\`,
   1509 MB on disk). Architecture: Qwen3-0.6B-Base. Quantization:
   per-tensor `OK_Q8` packed bytes + Frobenius scale siblings
   (per `papers/PPT-LAT-SP-MODEL-v0` §9 + `tools/sp_transcode/sp_transcode.c:1-20`).
   Confirmed Executive in L3.FG closure at
   `papers/SESSION-CLOSED-lat-2-l3-fg-cross-compile.md:56-57` (the
   CPU mmap chat path uses this artifact).

3. **L3.FG closure dual-load context** — `papers/SESSION-CLOSED-lat-2-l3-fg-cross-compile.md:56-57`:
   > **Dual-model footprint held:** CPU mmap (754 MB, chat) + DSP
   > rpcmem (1433 MB, model_info/echo) ≈ 2.2 GB — no OOM/thermal
   > trip during the run.

   Critical finding: the "2.2 GB dual-model" in L3.FG is **CPU model
   + DSP rpcmem upload of the same Qwen3-0.6B model**, NOT two distinct
   models. M.0 needs a SECOND, distinct-checkpoint `.sp-model`.

   Separate finding: a **dual-model AppState already exists** in
   `tools/sp_daemon/src/state.rs:46-58` (Phase 4-SPEC commit
   `cafb349` per Roadmap line 4907) — `model` / `session` for target,
   `draft_model` / `draft_session` for draft. M.1 will reuse this
   slot semantically as the Memory model. **M.0 infrastructure side
   is already present**; M.0 is purely the artifact-existence story.

4. **`reference-zero-copy-invariant`** memory entry — reviewed.
   Memory model must satisfy the same zero-copy invariant: on-disk
   `.sp-model` IS the arena, no Q→fp16 inflation, runtime bridge
   aliases the mmap. Both candidate Path A artifacts already satisfy
   this (they were produced by `sp_transcode --verify` and are loaded
   via `sp_model_load` which mmaps directly).

5. **Existing conversion tooling** — `tools/sp_transcode/sp_transcode.c`,
   built artifact at `D:\F\shannon-prime-repos\shannon-prime-system-engine\build-cpu\tools\sp_transcode\sp_transcode.exe`
   (100 KB, LastWriteTime 26/05/2026 11:33). Usage at
   `sp_transcode.c:19-21`:
   ```
   sp_transcode <in.gguf> <out.sp-model> <out.sp-tokenizer> [--verify]
   ```
   Writes OK_Q8 + per-row Frobenius scale siblings directly in
   `SP_FROB_ARENA_LAYOUT_VERSION=1` form (zero-copy invariant
   satisfied).

6. **`feedback-no-silent-gate-revisions`** memory entry — discipline
   rule. If gates cannot meet criteria, surface UPSTREAM with
   diagnostic detail + path options for operator decision.

## Path A vs Path B decision

**PATH A SELECTED.** Path B (real SFT on factual corpus) is out of
scope for a fast-unblock prep sprint per the sprint prompt itself.

## Path A stub source: which checkpoint?

**Candidates evaluated:**

| Candidate | Source | Status | Distinct from Executive? | Verdict |
|---|---|---|---|---|
| Qwen3-0.6B Unsloth Q4_K_M | `D:\Files\Models\New folder\Qwen3-0.6B-Q4_K_M.gguf` (378 MB) | already downloaded | same base checkpoint, only quant differs (Unsloth re-quant of same weights) — divergence only via quant noise | REJECT: not "trained differently" per Roadmap line 5808-5811 ("Memory is trained differently") |
| Qwen2.5-Coder-0.5B-Instruct | already transcoded at `engine/build-cpu/qwen25-coder-0.5b-target.sp-model` (473 MB) + `qwen25-coder-0.5b.sp-tokenizer` (4 MB) | `.sp-model` artifact exists from Phase 4-SPEC, no work needed | YES — different arch (Qwen2.5 vs Qwen3), different training (code SFT vs base pretrain), different vocab/tokenizer | ACCEPT |
| Qwen3-0.6B-Instruct (HuggingFace download) | requires download (~1.5 GB BF16 / 800 MB Q8) | not on disk; would need fetch + transcode | YES (Instruct vs Base SFT) — same arch | DEFER: clean choice but slower; if M.0-real wants same-arch stub, do here |

**Selection: `qwen25-coder-0.5b-target.sp-model` as Memory model.**

Rationale:
- Already in `.sp-model` format; zero conversion work.
- Different architecture (Qwen2.5 vs Qwen3) → `T_MEMO_M0_DISTINCT_FROM_EXECUTIVE` PASSes trivially.
- Different training corpus (SFT on code vs base pretrain) → fits Roadmap line 5808-5811 "Memory is trained differently".
- Has its own tokenizer + math-core bridge (`sp_model_to_qwen25` at
  `lib/shannon-prime-system/core/session/sp_model_bridge.c:442-535`).
- L3.FG architecture surface is fully exercised on Qwen2.5 already
  (test_sp_model_roundtrip + Phase 3 Cell 2 session_test.c:720+).

**Caveat (documented in M.0 CHOICE doc):** different-architecture
stub means M.1 dual-load will exercise two different forward kernels.
Real M.0 (M.0-real, future sprint) will SFT a Qwen3-0.6B on a factual
corpus so Executive and Memory share architecture — that's a
correctness-tighter setup for M.3+ TIES merge, which assumes weight-
space compatibility. M.0-stub still unblocks M.1 (dual-load budget
audit), M.2 (dialogue loop protocol), and M.5 (KSTE routing) — which
are protocol/budget concerns, not weight-space-compat concerns.

## Stable cache path

The engine `build-cpu/` directory gets blown away on clean rebuilds.
Per the sprint prompt's "stable cache path" requirement, copy the
artifact + tokenizer to:

- `D:\F\shannon-prime-repos\models\qwen25-coder-0.5b-memory.sp-model`
- `D:\F\shannon-prime-repos\models\qwen25-coder-0.5b-memory.sp-tokenizer`

(`D:\F\shannon-prime-repos\models\` is a non-git scratch dir adjacent
to the repos; this is NOT in any git tree.)

If a more canonical path is preferred (e.g. `%LOCALAPPDATA%\shannon-prime\models\`
or `~/.cache/shannon-prime/models/`), document in CHOICE.md and
update path; for this sprint use the repo-adjacent stable path.

## Stages

- **Stage 1 — Artifact copy + sanity.** Copy
  `qwen25-coder-0.5b-target.sp-model` → stable path as
  `qwen25-coder-0.5b-memory.sp-model`. Copy tokenizer adjacent.
  Verify file size + sha256. Gate T_MEMO_M0_MODEL_EXISTS reportable
  at this stage.
- **Stage 2 — Smoke validation.** Run sp_transcode `--verify` against
  the copied model, OR run the existing `test_sp_model_roundtrip.exe`
  in E_FMT_4_QWEN25 mode against the copied model to demonstrate
  `sp_model_load` + forward pass succeed. Probably write a small
  Rust harness `tools/m0_smoke/sp_memo_m0_smoke.rs` invoking the
  L1 ABI directly. Decision: deferred to Stage 2 entry; reuse
  existing test harness if it accepts a path arg.
- **Stage 3 — Documentation.** Write `papers/PHASE-4-MEMO-M0-CHOICE.md`
  + append phase-log entry to `papers/PPT-LAT-Roadmap.md` after the
  K.beta.2.5b closure block.
- **Stage 4 — Closure.** Commit, propose sub-tag
  `lat-phase-4-memo-m0-stub`, push branch.

## Gate measurement methodology

| Gate | Method | Pass criterion |
|---|---|---|
| `T_MEMO_M0_MODEL_EXISTS` | `Get-Item <path>` size + sha256 | file present, size in 300 MB - 1.5 GB band, sha256 matches source artifact |
| `T_MEMO_M0_LOADS` | invoke `sp_transcode --verify` against copied path (or, if that does not accept `.sp-model` direct input, invoke `test_sp_model_roundtrip.exe E_FMT_4_QWEN3` against engine fixture) | load returns SP_OK; arch query returns SP_ARCH_ID_QWEN25; record load_wall_ms + peak_rss_mb |
| `T_MEMO_M0_FORWARDS` | drive 4-token greedy generation via existing C harness (test_generate-style call against `qwen25_forward`) with prompt token IDs corresponding to "The capital of France is" (decoded via the qwen2.5 tokenizer) | wall_ms < 5000; tokens non-degenerate (not all same id, not <pad>) |
| `T_MEMO_M0_DISTINCT_FROM_EXECUTIVE` | run same prompt token IDs (re-encoded for each tokenizer if needed) through Memory and Executive; compare first 4-8 decoded tokens | sequences diverge at some position |

Note on T_MEMO_M0_DISTINCT_FROM_EXECUTIVE: because Memory (Qwen2.5)
and Executive (Qwen3) have different tokenizers, "same prompt" means
"same text" not "same token IDs." Each model tokenizes "The capital
of France is" under its own tokenizer, runs forward, decodes 4-8
output tokens to text. Sequences are compared as text. PASS criterion
is text divergence (which is overwhelmingly likely since vocabs differ
+ training differs).

If a forward-execution harness is unavailable on Windows host for
the M.0 Memory model, surface UPSTREAM: do NOT silently relax to a
load-only smoke. The Roadmap M.0 spec frames the bring-up STUB as
"protocol validation" — a model that loads but cannot forward is not
a useful stub. Path-out if T_MEMO_M0_FORWARDS cannot be measured:
file UPSTREAM-REQUIRED gate state, document why, defer the gate to
M.1 (where dual-load is exercised).

## Anti-contamination acknowledgments

- Operate ONLY in `D:\F\shannon-prime-repos\lattice-memo-m0` (worktree, branch `sprint/memo-m0`).
- Read-only consult of `D:\F\shannon-prime-repos\shannon-prime-system-engine` for transcode tooling + existing artifacts.
- READ-ONLY copy from engine build-cpu/ to stable cache path (no modification of source).
- Do NOT touch `D:\F\shannon-prime-repos\shannon-prime-lattice` (main), `engine-kbeta-2-5c` (K.beta.2.5c agent worktree), `engine-kbeta-2-5b` (prior sprint worktree), or any archive dirs.
- Worktree-discipline per `feedback-parallel-agents-separate-worktrees`.

## What's NOT in M.0

- Real SFT on a factual corpus → M.0-real (future sprint).
- Wiring Memory model into MeMo orchestrator loop → M.2.
- Budget audit + dual cDSP load → M.1.
- TIES merge in Frobenius domain → M.3 (gated on K.beta.2.5b math).

## What unblocks after M.0 closure

- M.1 (dual-load on cDSP-internal) — needs a Memory artifact to load.
- M.2 (zero-copy dialogue loop) — needs a Memory artifact.
- M.5 (KSTE-routed sparse activation) — needs a Memory artifact for measurement baseline.
