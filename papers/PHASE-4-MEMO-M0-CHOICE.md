# Phase 4-MeMo M.0 — Memory model artifact CHOICE + CLOSURE

## Headline

Memory model stub for the heterogeneous CRT mesh is a byte-identical
copy of the already-Phase-4-SPEC-validated
`qwen25-coder-0.5b-target.sp-model` at the stable cache path
`D:\F\shannon-prime-repos\models\qwen25-coder-0.5b-memory.sp-model`
(473.22 MB, sha256 `812df63f189719047b05735d7f9034965dfaa828cf7a8940351f10665cc1126a`).
Four substantive gates run, all PASS. Path A taken. M.1+ unblocked.

## Path decision

**PATH A — STUB.** Path B (real SFT on factual corpus) was explicitly
out of scope per the sprint prompt ("fast unblock for protocol
validation"). Path A satisfies M.0's contract: an existing,
DIFFERENT-CHECKPOINT `.sp-model` artifact that loads, forwards, and
produces distinct outputs from the Executive — enough to unblock
M.1 (dual-load budget audit), M.2 (zero-copy dialogue loop), and M.5
(KSTE routing). M.0-real (Path B, real SFT) is filed below as
follow-on.

## Path A stub source rationale

Three candidates evaluated against the Roadmap line 5808-5811 directive
"Memory model is **trained differently** (SFT on factual corpora), not
necessarily smaller":

| Candidate | Status | Distinct enough? | Decision |
|---|---|---|---|
| Qwen3-0.6B-Unsloth-Q4_K_M | already on disk (`D:\Files\Models\New folder\Qwen3-0.6B-Q4_K_M.gguf`, 378 MB) | NO — same base checkpoint, only quant differs (Unsloth re-quant of the Qwen3-0.6B-Base weights used for Executive); divergence only via quant noise | REJECT |
| Qwen2.5-Coder-0.5B-Instruct (already transcoded) | `.sp-model` artifact exists at engine `build-cpu/qwen25-coder-0.5b-target.sp-model` (473 MB, generated for Phase 4-SPEC) | YES — different arch (Qwen2.5 vs Qwen3), different training corpus (code SFT vs base pretrain), different config (24L×896H vs 28L×1024H) | **ACCEPT** |
| Qwen3-0.6B-Instruct (HuggingFace fetch) | NOT on disk; would require download + transcode (~30-60 min) | YES (Instruct vs Base SFT) — but same arch | DEFER to M.0-real |

The accepted stub satisfies T_MEMO_M0_DISTINCT_FROM_EXECUTIVE by
construction (different architecture, different training corpus,
different output distribution).

## Artifact details

| Field | Value |
|---|---|
| Memory model path (stable cache) | `D:\F\shannon-prime-repos\models\qwen25-coder-0.5b-memory.sp-model` |
| Memory tokenizer path | `D:\F\shannon-prime-repos\models\qwen25-coder-0.5b-memory.sp-tokenizer` |
| Memory model size | 473.22 MB (496,202,752 B) |
| Memory model sha256 | `812df63f189719047b05735d7f9034965dfaa828cf7a8940351f10665cc1126a` |
| Memory tokenizer sha256 | `848515f27a0d852dd5b27b5772c6183188efa2eb2fd9bdc3d8685bd6375d1bf1` |
| Memory architecture | Qwen2.5 (`SP_ARCH_ID_QWEN25`), 24 layers, hidden_dim=896, vocab_size=151936 |
| Source HuggingFace ID | `lmstudio-community/Qwen2.5-Coder-0.5B-Instruct-GGUF` |
| Source GGUF | `Qwen2.5-Coder-0.5B-Instruct-Q8_0.gguf` (506.5 MB on disk) |
| Quantization | per-tensor `OK_Q8` packed bytes + Frobenius scale siblings (`SP_FROB_ARENA_LAYOUT_VERSION=1`) |
| Conversion command (original, NOT re-run) | `sp_transcode Qwen2.5-Coder-0.5B-Instruct-Q8_0.gguf qwen25-coder-0.5b-target.sp-model qwen25-coder-0.5b.sp-tokenizer --verify` (executed during Phase 4-SPEC closure 2026-05-26) |
| Copy operation (M.0) | `Copy-Item engine\build-cpu\qwen25-coder-0.5b-target.sp-model -> models\qwen25-coder-0.5b-memory.sp-model` (byte-identical, MD5/SHA256-verified pre and post) |

**Why a byte-identical copy and not a fresh transcode:** the source
`.sp-model` is the artifact validated through the full Phase 4-SPEC
gate run (E_FMT_4_QWEN25 via test_sp_model_roundtrip + cafb349 dual-
model AppState). Re-transcoding would produce a different artifact
(timestamps + CRC delta) and require re-validation. A byte-identical
copy preserves all prior validation. The Phase 4-SPEC closure note
(`SESSION-CLOSED-lat-4-SPEC.md:11-13`) anchors the source artifact's
provenance.

## Companion Executive (for reference)

| Field | Value |
|---|---|
| Executive model path | `D:\F\shannon-prime-repos\shannon-prime-system-engine\build-cpu\tests\qwen3_rt.sp-model` (engine build dir; NOT copied to stable cache for M.0) |
| Executive size | 754,551,808 B (~720 MB) |
| Executive arch | Qwen3 (`SP_ARCH_ID_QWEN3`), 28 layers, hidden_dim=1024, vocab_size=151936 |
| Source | `Qwen3-0.6B-f16.gguf` at `D:\Files\Models\Qwen\Qwen3-0.6B-GGUF\` (1439 MB BF16) |
| Provenance | Phase 2-FMT E_FMT_4_QWEN3, confirmed in L3.FG cross-compile closure |

## Gates

All four substantive gates RUN and PASS.

| Gate | Method | Observed | Verdict |
|---|---|---|---|
| `T_MEMO_M0_MODEL_EXISTS` | `Get-Item` size + `Get-FileHash` sha256 against copy at stable cache path | path exists, size = 473.22 MB (within 300 MB - 1.5 GB band for 0.5B-param Q8), sha256 byte-identical to source artifact | **PASS** |
| `T_MEMO_M0_LOADS` | `tools/sp_daemon/target/release/probe.exe <memory>` (READ-ONLY engine binary; loads `.sp-model` via `sp_model_load`, queries arch, creates+clones session) | exit 0, "PROBE PASS", `arch: vocab=151936 n_layers=24 hidden=896`, `load_wall_ms`≈3110, `peak_rss_mb`≈487.9 | **PASS** |
| `T_MEMO_M0_FORWARDS` | same `probe.exe` continues: `sp_prefill_chunk(tokens=[1,2,3])` + `sp_decode_step(pos=4)` | prefill OK with logits[0..3] = `[13.456209, 13.751482, 15.366035]`, decode OK at position=4 with logits[0..3] = `[12.027878, 9.764421, 14.937441]`, all finite, wall_ms=3110 < 5000 threshold | **PASS** |
| `T_MEMO_M0_DISTINCT_FROM_EXECUTIVE` | identical token sequence `[1,2,3]` driven through both models; logits[0..3] compared | Memory   prefill=`[13.456, 13.751, 15.366]` decode=`[12.028, 9.764, 14.937]`<br>Executive prefill=`[ 9.358,  9.667, 11.928]` decode=`[10.353, 7.127, 14.557]`<br>6/6 positions diverge; architectures also structurally different (24L×896H vs 28L×1024H) | **PASS** |

Reproducible end-to-end via `scripts\m0_smoke.ps1` (committed in this
sprint).

Note on T_MEMO_M0_FORWARDS prompt choice: the M.0 spec suggested
"The capital of France is" as a sample prompt, but probe.exe's hard-
coded `[1,2,3]` token sequence is what we have. This satisfies the
gate's underlying intent ("model can run forward through prefill +
decode and produce sane logits") without requiring a separate
tokenizer-driven harness. The semantic "is the output plausible"
check is the equivalent test of `PROBE PASS` semantics: probe asserts
position advances correctly (4 after prefill(3)+decode(1)), all FFI
calls return `SP_OK`, no NaN/Inf in logits. Sufficient for M.0
bring-up; M.2 dialogue loop will exercise tokenized prompts properly.

## Sanity check (6/6 divergent positions, same input tokens)

```
Memory (Qwen2.5-Coder-0.5B-Instruct):
  arch:        vocab=151936  n_layers=24  hidden=896
  prefill[0..3]: [13.456209, 13.751482, 15.366035]
  decode[0..3]:  [12.027878,  9.764421, 14.937441]

Executive (Qwen3-0.6B-Base):
  arch:        vocab=151936  n_layers=28  hidden=1024
  prefill[0..3]: [ 9.357915,  9.666773, 11.927754]
  decode[0..3]:  [10.353107,  7.126801, 14.557454]

T_MEMO_M0_DISTINCT_FROM_EXECUTIVE: 6/6 positions diverge.
```

## Stub caveat (load-bearing for M.3)

The architectural difference between Memory (Qwen2.5) and Executive
(Qwen3) means:

- **M.1 dual-load (cDSP-internal)** will exercise TWO DIFFERENT forward
  kernels. Acceptable for budget audit + concurrent dispatch gate —
  these are protocol/budget concerns, not weight-space concerns. The
  cDSP scheduler doesn't care about arch; it cares about marshalling
  and dispatch.
- **M.2 zero-copy dialogue loop** is also fine — DmaBuffer routing is
  arch-agnostic; Spinor audit envelope wraps `(model_id, in_hash,
  out_hash)` not arch.
- **M.3 Frobenius-lifted TIES merge** REQUIRES same architecture
  between Memory and Executive (TIES merges weights tensor-by-tensor;
  Qwen2.5 and Qwen3 have different tensor shapes). M.3 will be
  blocked on M.0-real (Path B), not on M.0-stub. This is the only
  M-block sprint that M.0-stub does NOT unblock.

This is documented for the dispatcher of M.3: do not attempt to merge
the M.0-stub Memory model into the Qwen3 Executive — shape mismatch
will reject. M.0-real (a Qwen3-0.6B-Instruct or SFT-on-factual-corpus
of Qwen3-0.6B) must ship before M.3.

## Files changed

| File | Δ | Notes |
|---|---|---|
| `papers/SESSION-PLAN-lat-4-memo-m0.md` | +178 | Stage 0 reference reading + Path A decision + gate methodology |
| `scripts/m0_smoke.ps1` | +135 | Harness that drives probe.exe against both models + computes 3 runtime gates |
| `papers/PHASE-4-MEMO-M0-CHOICE.md` | +THIS | this closure note |
| `papers/PPT-LAT-Roadmap.md` | +~70 | Phase log entry appended after K.beta.2.5b closure |
| **Out-of-tree artifact (NOT git):** `D:\F\shannon-prime-repos\models\qwen25-coder-0.5b-memory.sp-model` + `.sp-tokenizer` | 473.22 + 3.92 MB | byte-identical copy of engine `build-cpu/qwen25-coder-0.5b-target.sp-model` |

## Commits on `sprint/memo-m0`

| Commit | Stage | Summary |
|---|---|---|
| `686c157` | plan | Stage 0 reference reading + Path A decision committed before any artifact action |
| `7abdef6` | stage 2 | smoke harness `scripts/m0_smoke.ps1` (Stage 1 was the out-of-tree artifact copy — not git-tracked per M.0 spec) |
| (closure) | stages 3+4 | this CHOICE doc + roadmap phase-log + per-stage closure of M.0 |

Base: `3dc2aa4` (lattice main @ K.beta.2.5b closure block).

## Proposed sub-tag

`lat-phase-4-memo-m0-stub` — names that this is the stub artifact for
M.0, not the real SFT-trained Memory model that M.3+ will need.

## What's NOT done in this sprint (explicit)

- **M.0-real (Path B)** — actual SFT on a target factual corpus. Would
  require: pick corpus (Wikipedia, PubMed, or domain-specific), set up
  training pipeline (likely qwen3 + LoRA or full SFT on Qwen3-0.6B),
  run SFT, validate. Future sprint: M.0-real. Blocks M.3 (TIES merge
  requires Memory and Executive to share architecture); does NOT
  block M.1, M.2, M.5, M.6.
- **M.1 (dual-load on cDSP)** — needs Android device + S22U
  measurement environment. M.0 unblocks dispatch.
- **M.2 (zero-copy dialogue loop)** — orchestrator state machine on
  Cortex-X2. M.0 unblocks dispatch.
- **M.3-M.6** — gated per Roadmap §5851-5949 prereq DAG. M.0-stub
  unblocks all except M.3.
- **No new conversion tooling written** — `sp_transcode` from
  `tools/sp_transcode/sp_transcode.c` was reused as-is (the
  pre-existing artifact it produced was copied; not re-invoked).
- **No new test harness written into the engine repo** — `probe.exe`
  pre-existed at `tools/sp_daemon/target/release/probe.exe` and
  was used READ-ONLY.

## What unblocks now

- **M.1 — Memory budget audit + dual-load (cDSP-internal).** Dispatch
  authorized; M.0 artifact in place at stable cache path.
- **M.2 — Zero-copy dialogue loop.** Dispatch authorized; both
  Executive and Memory load + forward via the same L1 ABI surface.
- **M.5 — KSTE-routed sparse Memory activation.** Dispatch authorized
  for measure-and-report measurements.
- **M.0-real (Path B)** — dispatch authorized as a parallel-track
  follow-on for the M.3-specific need.
- **MeMo × SPEC crossover** (Phase 4-SPEC × MeMo) — already partially
  done since SPEC already dual-loads. Memory-as-draft + Executive-
  as-verify protocol is one orchestrator commit away.

NOT unblocked: **M.3 (Frobenius-lifted TIES merge)** — requires
Memory + Executive to share architecture. Blocked on M.0-real.

## Worktree status

- Worktree: `D:\F\shannon-prime-repos\lattice-memo-m0` (added per
  `feedback-parallel-agents-separate-worktrees`).
- Branch: `sprint/memo-m0` (base `3dc2aa4` = K.beta.2.5b closure).
- All commits on this sprint authored from this worktree exclusively.
- Main lattice worktree (`D:\F\shannon-prime-repos\shannon-prime-lattice`):
  NOT TOUCHED. Engine main worktree
  (`D:\F\shannon-prime-repos\shannon-prime-system-engine`): READ-ONLY
  consulted (transcode tool inspection, probe.exe execution, source
  artifact copy).
- K.beta.2.5c agent's worktree
  (`D:\F\shannon-prime-repos\engine-kbeta-2-5c`): NOT TOUCHED.
- Push: `git push -u origin sprint/memo-m0` at sprint end (operator
  reviews + merges to main).

## References

- `papers/PPT-LAT-Roadmap.md:5772-5956` — Phase 4-MeMo block + M.0 spec.
- `papers/SESSION-CLOSED-lat-2-l3-fg-cross-compile.md:56-57` — L3.FG
  2.2 GB dual-load context (CPU + DSP rpcmem of same model; clarified
  to be different from M.0's two-distinct-checkpoint need).
- `papers/SESSION-CLOSED-lat-4-SPEC.md:11-13` — provenance of the
  source `qwen25-coder-0.5b-target.sp-model` artifact.
- `tools/sp_transcode/sp_transcode.c:1-21` — conversion tool (READ-ONLY).
- `tools/sp_daemon/src/bin/probe.rs:1-114` — probe harness (READ-ONLY).
- `tools/sp_daemon/src/state.rs:46-58` — existing dual-model AppState
  (`model` + `draft_model`) infrastructure from Phase 4-SPEC
  `cafb349`; M.1 will reuse semantically as Executive + Memory.
- `lib/shannon-prime-system/core/session/sp_model_bridge.c:442-535` —
  Qwen2.5 bridge (`sp_model_to_qwen25`) used at runtime to construct
  the Memory model's forward path.
- `include/sp/sp_status.h:20-55` — status enum (consulted to interpret
  probe.exe exit codes during sprint).
- Memory entries consulted: `reference-zero-copy-invariant` (.sp-model
  zero-copy contract; satisfied by byte-identical copy of validated
  artifact), `feedback-no-silent-gate-revisions` (gate discipline),
  `feedback-parallel-agents-separate-worktrees` (worktree-discipline),
  `feedback-lead-with-reference-then-theory` (Stage 0 reference-first
  workflow).
