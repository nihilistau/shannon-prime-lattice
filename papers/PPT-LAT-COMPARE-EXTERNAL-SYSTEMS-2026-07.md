---
type: design
title: "External-systems comparison + adoption roadmap: Icarus, OpenSelfRevise, and the latent/looped-reasoning paper cluster vs Shannon-Prime"
description: "A three-way review of external memory/reasoning systems (esaradev/icarus-memory-infra incl. codex/v2-architecture and feat/wiki-v1.1; DeadByDawn101/OpenSelfRevise; and 9 arXiv papers) against the Shannon-Prime organism. Similarities, differences, where we are ahead, where they are ahead, and — the point of the exercise — a prioritized set of ADR-style, gate-backed, null-floored plans to fold the best ideas into MEM-OKF, the recall/consolidation path, and a new latent recurrent-depth thinking channel. Every plan is anchored to an existing SP subsystem so it EXTENDS rather than rebuilds (anti-rebuild pre-flight in §7)."
tags: [design, comparison, external-systems, icarus, openselfrevise, latent-reasoning, looped-transformer, coconut, universal-transformer, memory, provenance, consolidation, mem-okf, recall, roadmap, okf]
timestamp: 2026-07-08T00:00:00Z
resource: shannon-prime-lattice/papers/PPT-LAT-COMPARE-EXTERNAL-SYSTEMS-2026-07.md
sp_status: DESIGN
sp_gate: none
sp_commit: TBD
sp_repro: "n/a (analysis + design). Each adoptable idea in §4 carries its own pre-registered gate to be run at implementation time."
---

# External-systems comparison + adoption roadmap (2026-07-08)

> **Scope.** Reviewed and compared against Shannon-Prime: (1) **esaradev/icarus-memory-infra** — main (== `codex/v2-architecture`, the Python `icarus_memory` v0.3.0 rewrite) and `feat/wiki-v1.1` (the older bash "fabric" lineage + LLM wiki); (2) **DeadByDawn101/OpenSelfRevise** — a ~300-line categorical scaffold implementing arXiv:2606.01444; (3) **nine arXiv papers**: 2606.01444 (categorical self-revising discovery), 2604.07822 (Loop-Think-Generalize), 2604.12946 (Parcae stable looped LMs), 1807.03819 (Universal Transformers), 2412.06769 (Coconut), 2502.17416 (Reasoning with Latent Thoughts), 2605.20670 (LT2 linear-time looped), 2410.20672 (Relaxed Recursive Transformers), 2604.21215 (Recurrent Transformer). Data gathered by a 7-agent fleet reading source + full-text papers + our own OKFS tree.
>
> **Bottom line.** The external work splits cleanly into two families. **Family M (memory/provenance/self-revision)** — Icarus + OpenSelfRevise + 2606.01444 — is where the *directly adoptable, low-risk* ideas live; our MEM-OKF is already more capable than Icarus on the substrate but Icarus has a cleaner, tested *lifecycle discipline* (trust×freshness axes, non-destructive rollback, taint-safe recall) and 2606.01444 gives us a *formal* version of our anti-rebuild rule. **Family R (latent/looped reasoning)** — the 6-paper cluster — is a whole capability we **do not have**: recurrent-depth latent reasoning (spend compute, not parameters). It is the biggest opportunity and the biggest bet. The single highest-leverage, lowest-risk new thing is a **Coconut-style continuous-thought channel** that fits ADR-002 and is byte-exact-friendly; the biggest structural payoff is a **looped/recursive Gemma variant** (a real training sprint).

---

## 0. TL;DR — what to take, ranked

| # | Idea (source) | Folds into | Leverage | Effort | Risk |
|---|---|---|---|---|---|
| A4 | **Retrieval / Search / Discovery trichotomy + Kan-obstruction** as the formal law behind anti-rebuild (2606.01444) | OKFS / okf_mem pre-flight | ★★★ | Low | Low |
| A1 | **Orthogonal `verified`×`lifecycle` axes + non-destructive supersede/rollback with taint cascade** (Icarus) | MEM-OKF v2 + DECIDE/FORGET | ★★★ | Low-Med | Low |
| B1 | **Coconut continuous-thought latent channel** (2412.06769) | ADR-002 latent tier; new `SP_COCONUT` | ★★★ | Med | Med |
| A3 | **MDL/AIC deterministic consolidation gate** (2606.01444 / OpenSelfRevise) | DECIDE/MERGE Stage-2 | ★★ | Low | Low |
| A2 | **Taint-safe-by-default recall + explicit audit path** (Icarus) | recall.rs delivery | ★★ | Low | Low |
| B3 | **Parcae ρ(Ā)<1 stability gate** for any iterative loop (2604.12946) | prerequisite for B1/B6 | ★★ | Low | Low |
| B4 | **Exact IO-aware KV tiling** (bit-exact, Θ(N log N)) (2604.21215) | byte-exact prefill perf | ★★ | Med | Med |
| B5 | **DPLR delta-rule as in-KV editable-memory primitive** (2605.20670) | MEM-OKF write/supersede research | ★★ | Med-High | Med |
| A5 | **Human/agent co-edit markers + grounded citation `ask()`** (Icarus wiki) | OKFS docs + faithfulness | ★ | Low | Low |
| B6 | **Recursive/looped Gemma distill** (effective depth + KV cut + throughput) (2410.20672 / 2605.20670 / 2502.17416) | whole-machine perf; new model variant | ★★★ | High | High |
| B2 | **ACT adaptive halting** for the think budget (1807.03819) | rides on B1 | ★★ | Med | Med |

Detailed ADR-style plans (flag, null floor, pre-registered gate, pre-flight) in **§4**.

---

## 1. The landscape — what each thing actually is

**Icarus (icarus-memory-infra).** A local-first, **markdown-native memory layer for AI agents**, framework-agnostic (library / CLI / MCP server). Two lineages:
- *v1 (`feat/wiki-v1.1`, originally `icarus-daedalus`):* a database-free bash "fabric" — every agent writes YAML+markdown into `~/fabric/`, everyone reads it; **hot/warm/cold age tiers** compacted by a `curator.py`; a Hermes plugin, a React dashboard, git cross-machine sync, and a **self-training pipeline** that turns fabric history into fine-tune data for a cheaper mirror model. The **LLM wiki** (v1.0→1.1→1.2) layers a Karpathy-style *compounding* knowledge base on top of the chronological log: immutable raw sources → agent-generated entity/topic pages with provenance, Obsidian wikilinks, multi-provider LLM extraction with silent heuristic fallback, `ICARUS_GENERATED:<key>:START/END` markers so agent re-ingest never clobbers human edits, and a grounded `ask()` that answers only with in-context citations.
- *v2 (`main` == `codex/v2-architecture`, `icarus_memory` 0.3.0):* a typed Python rewrite. A **memory is a Pydantic `Entry`** (YAML-frontmatter markdown at `YYYY/MM/icarus-<id>.md`, no DB, no index — disk globs). Central design: **two orthogonal status axes** — `verified ∈ {unverified, verified, contradicted, rolled_back}` (trust) × `lifecycle ∈ {active, superseded}` (freshness); first-class **provenance** (`EvidencePointer` with sha256 hashes); a **verification state machine** with legal transitions; **non-destructive rollback** that walks the `revises` chain to the last verified ancestor and can **cascade-quarantine tainted descendants**; **taint-safe-by-default retrieval** (`search`/`recall` exclude contradicted/rolled_back/superseded; a separate `audit_search` sees everything; results sorted so verified rises and tainted sinks); optional **hybrid BM25 + embedding RRF (k=60)** recall; a **three-layer model** (working memory 24h TTL / per-agent session archive / shared wiki) fused into a pre-task **briefing**.

**OpenSelfRevise.** A ~300-line **conceptual scaffold** (single commit, no tests, no model) that re-implements the categorical framework of arXiv:2606.01444: `Schema` = category of types+ops, `ArtifactState` = copresheaf population, `ProvenanceGraph` = DAG, an **MDL gate** (`gain = ΔmodelLen + Δfit`), a Builder/Breaker loop, and "Kan-extension transport" (in code: a type-name filter). The intelligence — builder, breaker, real MDL measurement — is left entirely to the caller; `search()` is a no-op stub. **The value is the paper it points at, not the code.**

**The paper cluster (Family R).** Six papers converging on one thesis: **loop a weight-shared block (or the residual state) for "effective depth" = latent reasoning that spends compute instead of parameters.**
- *1807.03819 Universal Transformers* — weight-tied depth recurrence + **ACT per-token adaptive halting**; Turing-complete.
- *2412.06769 Coconut* — reason in a **continuous latent space**: feed the last hidden state back as the next input embedding ("continuous thought"), no token decode while thinking; emergent BFS-like superposition; curriculum-trained; constant-length latent budget at inference.
- *2502.17416 Reasoning with Latent Thoughts* — **reasoning needs depth, memorization needs parameters**; a looped `(k⊗L)` block ≈ iso-FLOP full model on reasoning; **middle-looping**; a **cosine-similarity looping regularizer**; latent loops ≈ CoT steps; log-depth scaling law.
- *2604.07822 Loop-Think-Generalize* — recurrent-depth unlocks systematic generalization + **depth extrapolation**; **zero-init output projections** (identity block at init); **dynamic R ~ Poisson**; test-time depth scaling pays only if trained at R>4; "overthinking" failure mode.
- *2604.12946 Parcae* — **stable** looped LMs: cast the loop as an LTI system over the residual stream, enforce **spectral radius ρ(Ā)<1** (negative-diagonal state param + Prelude Norm), derive train- and test-time scaling laws; **test-time gains saturate at T≈μ_rec** (train at the depth you'll use).
- *2605.20670 LT2* — **linear-time** looped: swap quadratic attention inside the loop for DPLR linear mixers (DeltaNet/GDN/KDA) → **constant per-loop KV**, ~5.7× decode throughput; the delta rule `(I − βkkᵀ)S + βkvᵀ` is an **editable associative memory**; distill an existing model to linear-time with ~1B tokens; 1:4 full:linear ratio.
- *2410.20672 Relaxed Recursive Transformers* — convert a **pretrained** LLM to recursive (loop one shared block, init from its layers) + **depth-wise LoRA** to relax the tying; **continuous depth-wise batching + early exit** → 2–3× throughput.

And bridging the two families: *2606.01444* (Wang & Buehler, MIT) — a **categorical framework for self-revising discovery**: state as a **copresheaf**, provenance as the **category of elements** (the typed provenance DAG, not a metaphor), a sharp **retrieval / search / discovery** trichotomy, discovery = a **verified regime transition** (schema change) transported by **left Kan extension** with a **residual-outside-image** test for "did we actually learn something new," a **Kan obstruction (=∅)** meaning "this needs fresh evidence, can't be back-filled," an **MDL/AIC gate** for accepting revisions, and an **audit contract** (stable IDs, typed signatures, explicit parent lineage, append-only/explicit supersession, status for failed calls, **no silent merge or delete**).

---

## 2. Where Shannon-Prime already sits (the honest baseline)

From the OKFS survey (KEYSTONE, VERIFIED-SCOREBOARD, `recall.rs`, `routes.rs`, MEMORY-OKF-PROFILE, ADR-002):

- **Substrate nobody else has:** byte-exact integer forward (dual-prime CRT-NTT, `SP_BYTEEXACT`, G-BYTEEXACT-FORWARD-12B), cross-machine determinism, receipts-first gating, and a **null-floor discipline** (every `SP_*` flag is a byte-identical no-op when off). Gemma-4-12B OK_Q4B served on one RTX 2060 through our own Rust/C/CUDA daemon.
- **Memory (MEM-OKF):** content-addressed (sha256 or C2-256 LSH) 3-tier store (LUT / sum / full), `okf_mem.py`, gate G-MEM-OKF-CONFORM. Write via **NIGHTSHIFT** capture; retrieve via **L5-cosine query-to-query selection** (exact→paraphrase recall@1 ≈ 85.2%) + `tau` reject + a **deterministic Jaccard judge @0.6** (retired the 26B diffusion judge) + an **attribute-grounding gate** (SNE confab 80→0, leak 5→0); a learned **W_c head** (360/361 recall, int16-exact, logsumexp + NULL-slot reject). Consolidation: **DECIDE** (supersede via a 12B "cannot both be true" call) + **MERGE** (single synthesis) + **FORGET** (token-overlap removal). A **self-improvement flywheel** (telemetry → Alpaca JSONL → QLoRA → gate → deploy a CPU classifier that *beat* the 12B, 0.83 vs 0.33).
- **Agency / latent:** ADR-002 **decide-in-latent → execute-in-clean-text** spine (Rust typestate makes fusion impossible); latent interceptor heads (tool/action/memory/route, false-fire 0.000); cross-model **telepathy** (activation steering, not verbatim).
- **Known negatives kept honest:** last-token global-Q is **content-poor** (kste_md doesn't transfer, 1.6%); generative/diffusion judge **parked**; latent verbatim transfer **not claimed**; structure-on-content compression a **measured negative**.
- **What we do NOT have:** any **recurrent-depth / looped latent reasoning** (we run the 48-layer stack exactly once per token). No "think longer by iterating" knob. This is the gap Family R fills.

---

## 3. Three-way comparison — similarities, differences, who's ahead

### 3.1 Similarities (convergent design)
- **Markdown + YAML frontmatter as the memory substrate, no DB.** Icarus and MEM-OKF independently arrived at the same "just files" store. Icarus `Entry` ≈ our MEM-OKF concept; both cross-link; both are git-diffable.
- **Provenance-first + non-destructive lifecycle.** Icarus `supersede`/`rollback` ≈ our DECIDE-supersede; 2606.01444's "no silent merge/delete" audit contract ≈ our anti-rebuild + receipts discipline. All three treat "never overwrite, mark superseded" as the rule.
- **Compounding knowledge base.** Icarus wiki (Karpathy LLM-wiki) ≈ our OKFS LUT/sum/full progressive disclosure — both formalize the same "LLM wiki" pattern (OKF v0.1 is literally that pattern; we adopt it directly).
- **Deterministic gate over a model-call.** Icarus verified-status buckets + our Jaccard judge + 2606.01444's MDL gate all prefer a cheap deterministic decision to an expensive generative one — exactly our "Jaccard beat the 26B" lesson.
- **Self-training from memory.** Icarus v1 fabric→mirror-model ≈ our flywheel telemetry→QLoRA→CPU-classifier.
- **Latent reasoning family** ≈ our ADR-002 latent tier philosophically (decide/think in latent), though we don't yet iterate depth.

### 3.2 Differences (where the systems diverge)
- **Substrate.** We are a byte-exact **inference engine on the metal**; Icarus is a **pure Python bookkeeping layer** with no model (LLM calls are optional `gpt-4o-mini`); OpenSelfRevise has **no model at all**. We own the forward pass; they orchestrate around a black-box model.
- **Retrieval.** Icarus = keyword/BM25+embedding RRF over disk globs. We = **latent-geometry selection** (L5-cosine on the model's own hidden state) + learned head — a fundamentally richer signal, but one we've proven is **content-poor at the last token** (a real limit Icarus's content-embeddings sidestep).
- **Reasoning.** The paper cluster adds **iterative depth**; we add **exact arithmetic + agency heads**. Orthogonal axes — they're improving *how hard the model can think*, we've been improving *how faithfully and auditably it runs*.
- **Maturity shape.** Icarus is a **productized, 209-test, CI-gated library** with candid self-audits. OpenSelfRevise is a **skeleton**. We are a **deep research organism** (~90% GREEN-LIVE, receipts per claim) but with ad-hoc lifecycle plumbing.

### 3.3 Where we are ahead
1. **Auditable byte-exact substrate + null-floor + receipts** — unique; none of the others can reproduce a bit-identical run or prove a no-op.
2. **Real latent recall geometry on a live 12B** (85% L5) — Icarus never touches hidden states; its recall is lexical/embedding only.
3. **Deterministic gates that beat model-calls** (Jaccard judge, attr-gate) — more rigorous than Icarus's verified-bucket sort.
4. **Self-improvement flywheel with a promoted CPU classifier that beat the 12B** — ahead of Icarus's v1 self-train (which only produces fine-tune JSONL).
5. **Hardened latent agency** (tool/action/memory/route heads, false-fire 0.000) — no counterpart in any source.
6. **On-GPU O(1) context + cross-model telepathy** — infrastructure the others don't attempt.

### 3.4 Where they are ahead (what to steal)
1. **Icarus lifecycle discipline** — the **orthogonal verified×lifecycle axes**, **non-destructive rollback with taint cascade**, and **taint-safe-by-default recall + explicit audit path** are cleaner and more complete than our DECIDE (which *drops* the superseded fact via the forget path — destructive, no audit trail, no descendant taint). → **A1, A2.**
2. **2606.01444 formalism** — a rigorous, *computable* version of our anti-rebuild rule (Retrieval/Search/Discovery + Kan obstruction + residual test) and a principled **MDL/AIC accept gate**. → **A3, A4.**
3. **The entire Family-R capability** — recurrent-depth latent reasoning. We have no "think harder" axis at all. → **B1, B2, B6.**
4. **Inference techniques** — LT2 constant-per-loop KV / DPLR editable memory, Recurrent-Transformer's ~30% KV cut + **bit-exact IO-aware tiling**, Relaxed-Recursive's convert-pretrained-to-looped + depth-batching. → **B4, B5, B6.**
5. **Icarus wiki co-editing + grounded `ask()`** — the `ICARUS_GENERATED` marker pattern and citation-only answering. → **A5.**

---

## 4. Adoptable ideas — ADR-style plans (flag · null floor · gate · pre-flight)

Every plan below **extends a named existing subsystem** (anti-rebuild). Each is default-off with a byte-identical null floor and a pre-registered gate to run at implementation time.

### Group A — Memory / provenance / self-revision (low risk, high value, ship first)

#### A1 · Non-destructive supersede with orthogonal trust×freshness axes + taint cascade
- **Source:** Icarus v2 (`schema.py` two-axis model, `rollback.py` taint cascade); 2606.01444 audit contract ("no silent delete").
- **Problem it fixes:** our **DECIDE-supersede** currently executes via the *forget-removal* path (`routes.rs` ~L3947-4055) — it **drops** the old episode. That loses the audit trail, can't be rolled back, and doesn't quarantine facts derived from a now-contradicted one. 2606.01444 says a valid consolidation endofunctor must preserve refinement morphisms — i.e. append-only supersession, no silent delete.
- **Extends (not rebuild):** MEM-OKF v2 policy block (`mem_class`/`mem_delivery`) already exists (`okf_mem.py` `MEM_CLASSES`; OKFS `cada52f5ebc9a242`) and the registry already carries per-episode sidecars. We add two frontmatter fields + change DECIDE to mark-not-drop.
- **Plan:**
  1. Add to the MEM-OKF entry schema two orthogonal fields: `mem_verified ∈ {unverified, verified, contradicted, rolled_back}` and `mem_lifecycle ∈ {active, superseded}` (+ `superseded_by`, `supersedes`, `contradicted_by` addr links). Default on capture = `unverified` / `active`.
  2. Change **DECIDE** so a supersede verdict sets the old entry `mem_lifecycle=superseded, superseded_by=<new addr>` (append-only) instead of calling the forget-removal path. Keep the bytes; drop it only from the **live recall set**, not from disk.
  3. Add a **rollback verb** (`SP_MEM_ROLLBACK`) that walks a `revises`/`superseded_by` chain back to the last `verified` ancestor, marks intermediates `rolled_back`, and (opt-in) taints direct descendants that cite a `contradicted` entry.
  4. Extend `okf_mem.py verify` (gate G-MEM-OKF-CONFORM) to check the new state-machine legality (e.g. `verified` can't be set at capture; `contradicted`→`verified` illegal).
- **Flag / null floor:** `SP_MEM_LIFECYCLE=0` → capture writes neither field, DECIDE keeps today's forget-drop behavior → **byte-identical** to current registry.
- **Gate:** `G-MEM-LIFECYCLE` — (a) after a supersede, the old addr still resolves on disk and is excluded from live recall; (b) rollback restores the verified ancestor to the live set and the intermediate is `rolled_back`; (c) `okf_mem verify` rejects an illegal transition; (d) null-floor SHA of the registry with flag off == pre-change.
- **Pre-flight:** `okf_mem lookup --root memory-okf "supersede decide merge lifecycle"`; grep `routes.rs` for `CHANGED=`/`MERGE::`; confirm no existing lifecycle field before adding.
- **Risk:** Low. Pure additive metadata + a behavior swap behind a flag.

#### A2 · Taint-safe-by-default recall + explicit audit path
- **Source:** Icarus `retrieval.py` (`status_filter="safe"`, separate `audit_search`, verified-status sort bucket).
- **Extends:** `recall.rs` L5-direct+tau delivery (already has tau reject + attr-gate). We add a status filter *before* cosine ranking and an audit bypass.
- **Plan:**
  1. In the recall candidate set, drop `mem_lifecycle=superseded` and `mem_verified ∈ {contradicted, rolled_back}` before scoring (rides on A1's fields).
  2. Tie-break the L5 cosine ranking by verified bucket (`verified` > `unverified`) so a correctly-selected verified fact wins a near-tie.
  3. Add an **audit mode** (`SP_RECALL_AUDIT=1`) that disables the filter — for the operator/consolidator to see tainted history.
- **Flag / null floor:** `SP_RECALL_TAINTSAFE=0` → no filter → identical to today.
- **Gate:** `G-RECALL-TAINTSAFE` — a contradicted episode is never delivered on the hot path but *is* returned under audit; verified vs unverified tie resolves to verified; recall@1 on the 61-fact set unchanged for all-active corpora (no regression).
- **Pre-flight:** grep `recall.rs` for `tau`, `attr_gate`, `is_interrogative`; confirm no existing status filter.
- **Risk:** Low. Depends on A1.

#### A3 · MDL/AIC deterministic consolidation gate (complement, not replace, DECIDE/MERGE)
- **Source:** 2606.01444 (MDL/AIC accept gate, records the *rejected alternative* as provenance); OpenSelfRevise `gates.py` (`gain = ΔmodelLen + Δfit`).
- **Problem it fixes:** DECIDE/MERGE currently rely on a **12B model-call** ("cannot both be true", `MERGE::`). That's exactly the pattern we've repeatedly shown a cheap deterministic gate can beat (Jaccard judge vs 26B). An MDL gate gives a *first-pass, zero-inference* accept/reject for the common cases and reserves the model-call for the genuinely ambiguous ones.
- **Extends:** DECIDE/MERGE Stage-2 (`routes.rs` L4055-4125) and the Jaccard judge (`recall.rs` L664-770). Same "deterministic gate first" shape.
- **Plan:**
  1. Define a description-length proxy over MEM-OKF entries: `L(store) = Σ tokens(entry.body) + λ·|edges|`. For a proposed MERGE of A+B→C, accept iff `L(store without A,B with C) + fit_penalty(C) < L(store) − θ` (C must not lose facts present in A∪B — check via token-recall of A∪B key-terms in C, reusing the Jaccard machinery).
  2. Route: MDL-accept → merge deterministically (no model-call); MDL-inconclusive (|gain|<θ) → fall through to today's 12B DECIDE/MERGE call; MDL-reject → keep both.
  3. **Record the rejected alternative** as an audit entry (per 2606.01444) so consolidation decisions are themselves provenance.
- **Flag / null floor:** `SP_MEM_MDL_GATE=0` → every consolidation goes to the model-call as today.
- **Gate:** `G-MEM-MDL` — on a labeled set of {true-supersede, true-merge, keep-both} triples, MDL-first + model-fallback ≥ model-only accuracy at < (fraction) of the model-calls; a MERGE that would drop a fact present in A∪B is always rejected (0 fact-loss).
- **Pre-flight:** `okf_mem lookup "decide merge judge jaccard MDL"`; confirm the Jaccard token-overlap helper is reusable; check no prior MDL attempt banked as negative.
- **Risk:** Low. Deterministic, additive, model-call preserved as fallback.

#### A4 · Formalize anti-rebuild as Retrieval / Search / Discovery + Kan-obstruction
- **Source:** 2606.01444 (the trichotomy; discovery = verified regime transition; Kan obstruction `=∅` = "needs fresh evidence, can't be back-filled"; residual-outside-image = "did we actually learn something new").
- **Problem it fixes:** our anti-rebuild rule is a *prose discipline* ("a new derivation for something already in OKFS is a DEFECT") enforced by memory + reviewer vigilance. 2606.01444 makes it a **computable classifier** on every incoming knowledge write.
- **Extends:** the binding OKFS pre-flight (`okf_mem lookup` + grep) and `okf_validate.py` / G-OKF-CONFORM. This is the *most on-brand* idea in the whole review — it's literally the math of our recurring failure mode.
- **Plan:**
  1. Add an `okf_mem classify <candidate.md>` subcommand that labels an incoming write as:
     - **RETRIEVAL** — content-addr (sha256/C2) or high token-overlap match to an existing entry → **reject as duplicate** (this is the anti-rebuild catch, now automatic).
     - **SEARCH** — recombination expressible with the *current* type vocabulary + existing entries → allow, link to parents (a derivation, not a discovery).
     - **DISCOVERY** — requires a `type` not in the SP vocabulary or an entry with **no parent morphism** to anything in the store (the **Kan obstruction**: transport supplies nothing) → allow, but **flag that it needs fresh evidence / a receipt**, and require registering the new `type` in SP-OKF-PROFILE §2 first.
  2. Compute a cheap **residual** signal: fraction of the candidate's key-terms not covered by its nearest existing entries; near-zero residual on a "DISCOVERY"-claimed write = it's actually RETRIEVAL/SEARCH (a rebuild) → warn.
  3. Wire into a pre-commit hook alongside `okf_validate.py`.
- **Flag / null floor:** it's a *validator/advisory* tool, not a serving path — no runtime flag needed; default is warn-only (`--strict` to fail the commit).
- **Gate:** `G-OKF-DISCOVERY-CLASS` — on a labeled set of past commits (known rebuilds vs genuine new findings from the OKFS history), the classifier flags ≥ (target) of the known rebuilds as RETRIEVAL/low-residual and passes the genuine discoveries.
- **Pre-flight:** read `MEMORY-OKF-PROFILE.md` §0/§6 (the 20×-repeated rebuild failure) and `okf_mem.py addr_of/norm`; reuse existing content-addressing.
- **Risk:** Low. Tooling/advisory; directly attacks the project's most-named failure mode.

#### A5 · Human/agent co-edit markers + grounded citation `ask()` for OKFS docs
- **Source:** Icarus wiki `ICARUS_GENERATED:<key>:START/END` markers; grounded `ask()` (in-context citations only, "if not in the pages, say so").
- **Extends:** OKFS papers/memory `.md` files + our faithfulness system prompt + Jaccard judge (grounded answering is *already* our recall pattern; this generalizes it to whole-doc Q&A over the bundle).
- **Plan:**
  1. Adopt `<!-- SP_GENERATED:<key>:START/END -->` markers around agent-authored regions of OKFS docs so an agent re-generating a section edits only its own block and never clobbers hand edits (idempotent upsert). Add a `okf_mem upsert-block` helper.
  2. Add `okf_mem ask "<question>"`: rank bundle entries by token-overlap (reuse Jaccard/LUT), stuff top-N into the served 12B with the faithfulness prompt, answer with **only** `[[addr]]` citations resolvable in the bundle; decline if uncovered. This is the doc-level analogue of recall's "Context (authoritative)" delivery.
- **Flag / null floor:** tooling; no serving-path change. `ask` reuses the existing served daemon.
- **Gate:** `G-OKF-ASK` — answers cite only in-context addrs; on a held-out question whose answer is absent from the bundle, it declines (0 confabulation), mirroring the attr-gate result.
- **Pre-flight:** confirm the faithfulness prompt + Jaccard judge are reusable; check no existing `ask` verb.
- **Risk:** Low.

### Group B — Latent / looped reasoning (the missing capability)

> **Framing.** Our Gemma-4-12B is frozen and runs its 48 layers once per token. The papers agree (2604.07822, 2604.12946, 2502.17416) that **you must train/finetune at the recurrence depth you intend to exploit** — you can't just loop frozen Gemma layers and expect gains. So Group B splits into (i) a **decode-loop** change that needs only a light curriculum finetune of a small channel (**B1/B2**, adoptable soon), (ii) **stability + engine** techniques that are byte-exact-compatible and need no retrain (**B3/B4**), (iii) a **research primitive** (**B5**), and (iv) a **model-variant training sprint** (**B6**, biggest bet).

#### B1 · Coconut continuous-thought latent channel
- **Source:** 2412.06769 (hidden-state→next-input feedback; `<bot>`/`<eot>` markers; constant-length latent budget; curriculum).
- **Why it fits us best of all Family-R ideas:** it's a **decode-loop** change, not a weight change to the frozen stack; it needs **no logits/softmax/argmax while thinking** (deterministic map `h_t → next embedding`) which is **byte-exact-friendly and quantization-stable** (post-final-norm bounds magnitudes — exactly what our fixed-point islands want); and it is **ADR-002-native** — thinking happens in latent, only the post-`<eot>` answer is executed in clean text. It gives the organism a "think harder on this query" knob it currently lacks.
- **Extends:** the decode loop in the daemon (`gemma4_kv_*` decode; the same seam telepathy/inject_seq uses, `gemma4_kv_inject_seq`), ADR-002 spine (`spine.rs`), and the persistent-KV ring (each thought appends one slot — O(1)).
- **Plan:**
  1. Implement a **latent-thought decode mode**: between injected `<bot>`/`<eot>` markers, feed the last token's final-norm hidden state back as the next input embedding instead of decoding a token; append one KV slot per thought (reuse the O(1) ring). Constant thought-count `n` (Coconut shows constant length works as well as a learned stop; keep it simple first).
  2. **Curriculum-finetune only the entry/exit of the channel** (LoRA on the embedding-in adapter + optionally the first/last block) on a small multi-hop set (GSM8K-style / ProsQA-style / our own multi-hop recall-over-memory tasks), staged replacement of k text steps with k·c continuous thoughts, masking the latents. Keep the base 12B frozen and byte-exact.
  3. Expose as `SP_COCONUT=<n>` (n thoughts; 0=off). At `<eot>`, resume normal byte-exact decode for the answer.
  4. Add a **probe hook**: `softmax(W·h_thought)` read-out of a latent thought for a deterministic value/verifier signal (feeds A3/judge patterns) without committing a token.
- **Flag / null floor:** `SP_COCONUT=0` → no `<bot>`/`<eot>` injected, decode path unchanged → **byte-identical** to current chat.
- **Gate:** `G-COCONUT` — (a) on a held-out multi-hop set, `SP_COCONUT=n` (n>0) beats n=0 by a pre-registered margin at fixed decode budget; (b) answer tokens after `<eot>` are still byte-exact vs the null path for a non-thinking prompt; (c) the thinking loop is deterministic (bit-identical thought states run-to-run under fixed clocks).
- **Pre-flight:** `okf_mem lookup "latent inject_seq two-stage decide-execute telepathy coconut continuous-thought"` — verify the two-stage TELE-12 result (`a2b4dc7ab58afcfd`: *fused* latent+text = 0.000). **Critical distinction:** Coconut is **not** fusion — the latent thoughts live in their own `<bot>..<eot>` span and the answer is decoded cleanly afterward (sequential), which is precisely the shape TELE-12 validated. Confirm `gemma4_kv_inject_seq` accepts an embedding-sequence (it does; OKFS `c68b2f15dc30e641`).
- **Risk:** Med. Needs a small finetune; the honest-negative to respect is TELE-12 (don't fuse). Overthinking (2604.07822) is real — cap `n`.

#### B2 · ACT adaptive halting for the think budget (rides on B1)
- **Source:** 1807.03819 (per-token fixed-point halting mass, stop at threshold, copy-on-halt); 2604.07822 (dynamic R, overthinking).
- **Extends:** B1's latent-thought loop — replaces the constant `n` with an adaptive, bounded, **deterministic** stop rule (fits null-floor: no sampling).
- **Plan:** add a tiny scalar halting head on the thought state; accumulate fixed-point halting mass per query; stop when it crosses a threshold or hits `n_max`; use the remainder trick so contributions sum to ~1. Fixed-point arithmetic keeps it byte-exact.
- **Flag / null floor:** `SP_COCONUT_ACT=0` → constant-n (B1) behavior.
- **Gate:** `G-COCONUT-ACT` — matches or beats fixed-n accuracy at **fewer average thoughts**; halting is deterministic; harder queries provably ponder longer (report avg thoughts vs task difficulty, per UT Table 1).
- **Pre-flight:** confirm B1 landed; reuse the latent-interceptor head training harness (`tools/latent_interceptor/`).
- **Risk:** Med. Depends on B1; halting-head training is the tricky part.

#### B3 · Parcae ρ(Ā)<1 stability gate for ANY iterative loop
- **Source:** 2604.12946 (LTI view of the residual stream; monitor spectral radius of the effective update + `‖h_T‖`; negative-diagonal state param + Prelude Norm as the fix).
- **Why now:** the moment we add *any* loop (B1 thoughts, a memory-refine loop, B6), state-norm explosion is the #1 failure mode. This is a cheap, principled **guard rail** to bolt onto B1 from day one rather than debug loss spikes later.
- **Extends:** B1/B6 loops; the byte-exact monitoring already tracks tensors.
- **Plan:** instrument the thought loop to log `‖h_t‖₂` and estimate the effective linear update's spectral radius; if a loop diverges, apply Parcae's fixes (LayerNorm on the injected signal = "Prelude Norm"; if we ever train a looped block, parameterize its state matrix as `Diag(−exp(·))` to guarantee ρ<1).
- **Flag / null floor:** monitoring is inert (log-only) by default; the stabilizers are only used on trained looped variants.
- **Gate:** `G-LOOP-STABLE` — for `SP_COCONUT` runs, `‖h_t‖` stays bounded across the max thought budget; a deliberately unstable config is caught by the monitor.
- **Pre-flight:** none new; reuse existing tensor-dump tooling.
- **Risk:** Low. It's a diagnostic + a known fix.

#### B4 · Exact IO-aware KV tiling (bit-exact, Θ(N log N) traffic)
- **Source:** 2604.21215 (queries known in advance, KV revealed causally → FlashAttention-style tiling that reuses each KV tile across all future queries, **bit-exact**, cuts HBM traffic to Θ(N log N)); also its output-derived-KV framing.
- **Why relevant to us specifically:** our whole-machine perf is **bandwidth-bound**, not compute-bound (ADR-012 REFUTED the sync hypothesis; AVX-512/VNNI gave ~0 = memory-bound). A tiling that reduces HBM/DDR traffic while staying **byte-identical** is exactly the lever that could move our CPU-tail / prefill numbers where SIMD couldn't.
- **Extends:** the byte-exact prefill path (CRT-NTT GEMMs) and the CPU-FFN-offload tail (ADR-011/012). This is an *engine* optimization, no model change.
- **Plan:**
  1. Prototype the exact online-softmax tiling (interleave attention + FFN, reuse each revealed KV tile across all future queries) on the prefill attention, proving **bit-identical** output vs the current path (our byte-exact harness makes this checkable).
  2. Measure HBM/DDR traffic + wall-time on the 2060 and the CPU tail under locked clocks (per our perf methodology — lock SM+mem clocks, fresh process, warmup).
- **Flag / null floor:** `SP_KVTILE=0` → current prefill path; on must be **byte-identical** (gate).
- **Gate:** `G-KVTILE` — output bit-identical to null path (SHA); measured HBM/DDR-traffic reduction and wall-time delta at controlled clocks (report both, no doctoring).
- **Pre-flight:** `okf_mem lookup "prefill bandwidth ADR-012 cputail flash tiling KV"`; confirm ADR-012's bandwidth-bound verdict; reuse the byte-exact parity harness.
- **Risk:** Med. Exactness is provable; the win is empirical (could be small if already near the memory floor — pre-register that as an acceptable honest-negative).

#### B5 · DPLR delta-rule as an in-KV editable-memory primitive (research)
- **Source:** 2605.20670 LT2 (`S_t = (I − β_t k_t k_tᵀ)Diag(α_t)S_{t-1} + β_t k_t v_tᵀ` — an erase-then-write associative memory; T loops → rank-T write; window w → T·w receptive field).
- **Why interesting:** it's the most explicit "**self-revising memory write**" primitive in any source — a differentiable erase/overwrite over a recurrent state. It's a candidate mechanism for a *content-bearing* memory lane that sidesteps our proven **content-poor last-token global-Q** limit (kste_md doesn't transfer, `c90d457fd1e8fc97`).
- **Extends:** MEM-OKF write/supersede research; the telepathy content-bearing-vector lane (pooled-embedding TELE-1, where cosine *does* separate).
- **Plan (research, not production):** prototype a small DPLR recurrent memory over **pooled/content-bearing** embeddings (not last-token Q), test whether the delta-rule erase gives cleaner supersede/dedup than our current registry rewrite; measure recall/reject vs L5-direct+tau. Pre-register that this may be a negative (our honest-negative history here is strong).
- **Flag / null floor:** offline research harness; nothing wired to serving until it beats L5-direct head-to-head (per the deployed-selector-must-be-beaten rule, `2637657d74257930`).
- **Gate:** `G-DPLR-MEM` — head-to-head vs L5-direct+tau on the 61-fact + SNE sets; must beat the incumbent before earning a build.
- **Pre-flight:** `okf_mem lookup "kste_md content-poor global-Q pooled embedding TELE-1 delta-rule associative"`; **respect** `c90d457fd1e8fc97` (do not re-wire content-poor last-token Q).
- **Risk:** Med-High (research). Contain in an offline harness.

#### B6 · Recursive / looped Gemma variant — effective depth + KV cut + throughput (biggest bet)
- **Source:** 2410.20672 (convert pretrained→recursive by init-from-layers + depth-wise LoRA; continuous depth-wise batching + early exit → 2–3×); 2502.17416 (middle-looping; cosine-similarity regularizer; reasoning-vs-memorization split); 2605.20670 (distill to linear-time constant-KV with ~1B tokens).
- **Why it's the structural payoff:** whole-machine perf is dominated by "**model fills the card**" (~10.9GB, KV only ~0.78GB; ADR-010). A recursive Gemma with **fewer unique parameters** (one shared block looped) frees VRAM for context/KV, buys **reasoning depth without more weights** (2502.17416: reasoning ∝ depth, memorization ∝ params), and — via LT2 distillation — could give **constant-per-loop KV** and ~5.7× decode throughput. The cosine-regularizer result (adjacent layers ≥0.98 similar) also hints our weights are **alias-able** — directly relevant to our zero-copy weight-aliasing invariant.
- **Extends:** the `.sp-model` production path + OK_Q4B codec + the zero-copy weight-aliasing loader; would produce a **new served variant** (`gemma4-12b-recursive`), not replace the byte-exact 12B.
- **Plan (staged, each stage gated):**
  1. **Measure first (ceiling before training):** probe adjacent-layer cosine similarity in the served OK_Q4B Gemma-4-12B — if middle layers are already near-identical, looping/aliasing is cheap; if not, quantify the gap. (Reuse our "measure oracle ceiling before training" lesson.)
  2. **Convert (no full retrain):** init a recursive/middle-looped variant from the existing layers (Relaxed-Recursive recipe) + depth-wise LoRA; keep first/last layers unique.
  3. **Stabilize:** apply B3 (ρ<1) + zero-init output projections (2604.07822) so looped blocks start as identity.
  4. **Distill (optional):** LT2-style ~1B-token distillation to a linear-time constant-KV mixer for the looped middle.
  5. **Quantize + byte-exact:** run the variant through the OK_Q4B path; the loop is deterministic so byte-exactness is preserved by construction.
- **Flag / null floor:** it's a **separate model artifact**; the byte-exact 12B is untouched. Selectable, not default.
- **Gate:** `G-RECURSIVE-GEMMA` — the variant matches the base 12B within a pre-registered quality delta (PPL + our recall/faithfulness suite) at **measurably lower VRAM and/or higher tok/s**; byte-exact/deterministic; every claim clock-locked.
- **Pre-flight:** `okf_mem lookup "sp-model production path zero-copy aliasing OK_Q4B recursive looped depth"`; reuse the swivel loader + codec-by-source; **do not** inflate quantized weights (zero-copy invariant `reference_zero_copy_invariant`).
- **Risk:** High (a training/distillation sprint). Sequence it last; steps 1-2 are cheap probes that de-risk before committing.

---

## 5. Sequencing (leverage ÷ effort, and dependencies)

**Wave 1 — ship now (all low-risk, mostly deterministic, no retrain):**
`A4` (formal anti-rebuild classifier) → `A1` (non-destructive lifecycle) → `A2` (taint-safe recall) → `A3` (MDL gate) → `A5` (co-edit + ask). These harden the memory/knowledge layer where we're *behind* Icarus, and they're pure additive tooling/metadata with null floors. A1→A2 have a dependency; the rest are independent.

**Wave 2 — the new capability (light finetune of a small channel):**
`B3` (stability monitor, build first as a guard rail) → `B1` (Coconut continuous-thought) → `B2` (ACT halting). This gives the organism a byte-exact, ADR-002-native "think harder" knob — the biggest *new* thing, at moderate effort.

**Wave 3 — engine + research:**
`B4` (exact KV tiling — measure whether it beats the memory floor) in parallel with `B5` (DPLR editable-memory research, offline). Independent of Wave 2.

**Wave 4 — the big bet (training sprint, de-risked by cheap probes first):**
`B6` steps 1-2 (measure layer similarity, convert) are cheap and can start any time as a probe; steps 3-5 only if the probe is favorable.

---

## 6. What NOT to adopt (traps + respect our honest-negatives)

- **Don't loop the frozen Gemma stack expecting gains.** 2604.07822 / 2502.17416 / 2604.12946 all require training at the exploited depth. Looping our byte-exact 12B as-is will not reason deeper — it needs the B1/B6 finetune.
- **Don't fuse latent thoughts into the answer generation.** TELE-12 (`a2b4dc7ab58afcfd`) measured fused latent+text = 0.000. B1 is *sequential* (thoughts in `<bot>..<eot>`, then clean decode) — keep it that way.
- **Don't re-wire content-poor last-token global-Q.** `c90d457fd1e8fc97` — kste_md ran at 1.00× on real Gemma. B5's DPLR idea must target **pooled/content-bearing** vectors, not last-token Q, and prove itself head-to-head before any build.
- **Don't copy OpenSelfRevise's code.** It's a stub (no model, no learning, `search()` is a no-op). Take the *paper* (2606.01444), not the repo.
- **Don't adopt Icarus's disk-glob retrieval or its per-write OpenAI classification call** (its own audit flags the latter as the "single biggest behavioral break"). Our content-addressing + latent recall are better; only take Icarus's *lifecycle discipline*, not its I/O model.
- **Don't assume test-time thinking scales without bound.** Parcae: gains saturate at T≈μ_rec; 2604.07822: overthinking degrades. Cap the think budget (B2) and pre-register the ceiling.
- **Don't let B4/B5/B6 skip the "beat the incumbent head-to-head" bar** or the clock-locked perf methodology — our standing rules.

---

## 7. OKFS anti-rebuild pre-flight (what was checked before proposing)

Per the binding pre-flight, each proposal was checked against the existing OKFS tree so it **extends** rather than rebuilds:

- **Memory lifecycle / supersede / merge** already exist (`routes.rs` DECIDE/MERGE/FORGET; MEM-OKF v2 policy block `cada52f5ebc9a242`) → A1/A2/A3 **modify DECIDE + add metadata**, they do not add a new memory store.
- **Anti-rebuild** already a prose rule in `MEMORY-OKF-PROFILE.md` §0/§6 → A4 **adds a classifier** to the existing `okf_mem` + validator, not a new tool.
- **Grounded answering** already exists (recall "Context (authoritative)" + Jaccard judge + attr-gate) → A5 **generalizes** it to bundle-level Q&A.
- **Latent inject / two-stage / O(1) KV** already exist (`gemma4_kv_inject_seq` `c68b2f15dc30e641`; TELE-12 `a2b4dc7ab58afcfd`; persistent-KV ring) → B1 **rides these seams**; it is a decode-mode, not a new engine.
- **Perf is bandwidth-bound** (ADR-012 refuted sync; SIMD ~0) → B4 targets **HBM/DDR traffic**, the actual bottleneck.
- **Content-poor last-token Q** is a banked negative (`c90d457fd1e8fc97`) → B5 is scoped to pooled/content-bearing vectors and gated head-to-head.
- **`.sp-model` path + zero-copy aliasing** exist → B6 produces a **new variant artifact** through the existing loader/codec, honoring the zero-copy invariant.

**New `type`s / verbs to register before implementing:** `okf_mem classify` and `okf_mem ask`/`upsert-block` subcommands (A4/A5); `SP_MEM_LIFECYCLE`, `SP_RECALL_TAINTSAFE`, `SP_MEM_MDL_GATE`, `SP_COCONUT`, `SP_COCONUT_ACT`, `SP_KVTILE`, `SP_MEM_ROLLBACK` flags (register in KEYSTONE §7 flag index + VERIFIED-SCOREBOARD when gated). No new OKFS `type` needed (this doc is `type: design`).

---

## 8. Sources

**Repos:** esaradev/icarus-memory-infra (main == codex/v2-architecture, v0.3.0; feat/wiki-v1.1); DeadByDawn101/OpenSelfRevise.
**Papers:** arXiv 2606.01444 (Wang & Buehler, *Self-Revising Discovery Systems for Science*); 2604.07822 (Kohli et al., *Loop, Think, & Generalize*); 2604.12946 (Prairie et al., *Parcae: Scaling Laws for Stable Looped LMs*); 1807.03819 (Dehghani et al., *Universal Transformers*); 2412.06769 (Hao et al., *Coconut / Training LLMs to Reason in a Continuous Latent Space*); 2502.17416 (Saunshi et al., *Reasoning with Latent Thoughts: On the Power of Looped Transformers*); 2605.20670 (Deng et al., *LT2: Linear-Time Looped Transformers*); 2410.20672 (Bae et al., *Relaxed Recursive Transformers*); 2604.21215 (Oncescu et al., *The Recurrent Transformer*).
**Shannon-Prime (internal):** `papers/PPT-LAT-KEYSTONE.md`, `papers/VERIFIED-SCOREBOARD.md`, `papers/PPT-LAT-ADR-002-DECIDE-EXECUTE-SPINE.md`, `papers/MEMORY-OKF-PROFILE.md`, `papers/SP-OKF-PROFILE.md`; engine `tools/sp_daemon/src/recall.rs`, `routes.rs`; OKFS entries cited inline by 16-hex addr.

