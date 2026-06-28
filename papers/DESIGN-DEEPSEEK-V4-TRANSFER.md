---
type: design
title: "DESIGN — DeepSeek-V4 (arXiv 2606.19348) transferable mechanics, mapped to PPT-ARM"
description: "The arXiv link in the June DSpark thread (2606.19348) is actually DeepSeek-V4, not DSpark. V4 is genuinely relevant: it is a million-token long-context efficiency paper whose whole thesis (FLOP + KV reduction at extreme context) is the same envelope PPT-ARM targets. This doc distils V4's transferable ideas — MTP, sequence-dimension KV compression, the Sinkhorn doubly-stochastic 'manifold-constrained hyper-connections', FP4-QAT/Muon — onto our exact-integer substrate, with honest verdicts on what fits and what is out of scope."
tags: [design, deepseek-v4, kv-compression, mtp, sinkhorn, manifold, fp4, positioning]
timestamp: 2026-06-28T00:00:00Z
resource: https://arxiv.org/abs/2606.19348
sp_status: DESIGN
sp_gate: none
sp_commit: TBD
sp_repro: "n/a — analysis/positioning doc; transferable items route into CONTRACT-C4-SPECDECODE and the rebuild roadmap"
---

# DESIGN — DeepSeek-V4 transferable mechanics, mapped to PPT-ARM

> **Provenance note (receipts-first):** the thread cited `arxiv.org/html/2606.19348v1` as "the DSpark paper." It is not — `2606.19348` is **DeepSeek-V4: Towards Highly Efficient Million-Token Context Intelligence**. DSpark is the in-repo `DSpark_paper.pdf` (handled in [CONTRACT-C4-SPECDECODE](CONTRACT-C4-SPECDECODE-DSPARK.md)). The V4 capture we read was partial (abstract → §2.2; the KV/inference sections appear only as ToC). Numbers below are from the captured abstract/intro; flagged where the detail section was not in the captured text.

## 0. Why V4 is worth a doc

V4 is a **long-context efficiency** paper. Its headline is FLOP + KV-cache reduction at million-token context — *the same envelope thesis as PPT-ARM* (RFC-001 §0: inline KV compression → unlimited context; Ring-2 offload → multi-device; bit-exact as the floor). The frontier lab and us are pushing the same lever from opposite sides: **they reduce KV with learned lossy compression; we reduce it with exact + disk-backed two-ring offload.** That makes V4 both a validation and a sharp positioning contrast for *Position Is Arithmetic*.

## 1. MTP — confirms the C4 pillar (no new work)

V4 inherits Multi-Token Prediction "identical to that of DeepSeek-V3," adopted without modification. Read against our stack: the frontier's production decode-acceleration primitive *is* MTP, which is exactly our T8 / C4 pillar. **Action:** none beyond C4 — but cite V4 as external evidence that the MTP framing (not a bespoke geometric oracle) is the right home for speculative decode. Note our structural edge: **T8.1 (clean $\mathbb{Z}_q$ rollback, no ghost contamination)** is a property V4's float MTP cannot claim — its rejected drafts can leave numerical residue in the KV cache.

## 2. Sequence-dimension KV compression (CSA / HCA) — convergent with the two-ring

V4 compresses the KV cache **along the sequence dimension** (the captured text names *Compressed Sparse Attention* + *Heavily Compressed Attention*). Reported: at 1M context, V4-Pro uses ~**27% of single-token FLOPs and ~10% of the KV cache** vs V3.2; Flash ~**10% FLOPs / ~7% KV** (captured abstract; the mechanism section was ToC-only).

Map onto us: we already attack KV on **two axes** — *per-vector* (Spinor block, measured **~3.5×/f32**, lossy ~6.5% argmax flips, C2) and *along the sequence* (the **±1 Rademacher rank-16 recall router** picking a top-B budget, + Ring-2 disk offload, measured **400–1190× effective context**, C2.1). V4's "~10% KV" is structurally **our top-B recall budget** (keep ~10% of positions live). 

**Verdict — convergent validation, two honest contrasts.** (a) V4 confirms STATE's own finding that the envelope lives in **sequence-dim reduction**, not the per-vector codec. (b) Differentiators to bank publicly: ours is **exact/auditable** and **disk-unbounded** (Ring-2 → effectively unlimited, not a fixed 7–10% learned budget); theirs is learned and lossy but needs no retrieval router. **Action:** no new build; fold "V4-style sequence-dim KV reduction" into the C2/roadmap narrative as the industry's parallel, and keep the router-fidelity-at-high-budget gap (the 32k MISS at 64×) as the honest open edge it already is.

## 3. The real "manifold" — Sinkhorn doubly-stochastic hyper-connections

This is the interesting one, and the honest counterpoint to the thread's fictional elliptic "manifold." V4 stabilizes its residual stream with **Manifold-Constrained Hyper-Connections**: the residual/hyper-connection mixing matrix is constrained to the **Birkhoff polytope of doubly-stochastic matrices** via the **Sinkhorn–Knopp** algorithm (iterative row/column normalization). That is a genuine, well-defined geometric constraint with a concrete mechanism — unlike "a token falls off a CM elliptic curve," which had no defined map and no mechanism (see C4-SPECDECODE §5.1).

Where it could matter to us, honestly:
- It is a **training-time** residual regularizer. We **bolt onto pretrained weights and do not train the base** (RFC §0), so it is **out of scope for the forward**. Do not build it for inference.
- It is, however, **exactly computable in integer arithmetic** — Sinkhorn is just alternating normalizations, and a doubly-stochastic matrix **conserves mass**, which is the same invariant our **CRT sharding** and **Beatty/φ island partition** rely on (mass conserved across residues/islands). If **C5 (MeMo)** ever does continual-learning receipts or any weight-edit, a **doubly-stochastic / Birkhoff constraint is a real, exact-integer-friendly regularizer** to keep an additive receipt mass-conserving and stable — a far better "manifold" hook than anything in the Gemini thread.

**Verdict — note, don't build.** File as a candidate regularizer for C5 only; tag `[SPECULATIVE]` exactly like C5 itself. It earns a gate only if a concrete continual-learning task measurably improves with it.

## 4. FP4-QAT, Muon/Newton–Schulz, DeepSeekMoE — mostly out of scope

- **FP4 quantization-aware training:** V4 trains in FP4. Our analog is the **OK_Q4 reducing codec** applied **post-hoc** (C1: 17% smaller on qwen35moe, 50% on Qwen3-0.6B, **output-lossless top-1**). FP4-QAT needs retraining → out of scope; the data point is that **Q4 is the industry floor**, which our post-hoc path already meets without training.
- **Muon + Newton–Schulz iterations:** optimizer-side, training-only → out of scope. (Newton–Schulz is an exact-integer-friendly iteration, same footnote as Sinkhorn — irrelevant unless we train.)
- **DeepSeekMoE routing:** relevant only as confirmation — we already do a **256-expert MoE (qwen35moe) bit-exact** (M_QWEN36). Convergent; no action.

## 5. Positioning (for Position_Is_Arithmetic)

One paragraph worth banking: *the frontier (DeepSeek-V4) reaches million-token context by learned, lossy KV compression and FP4 training; Shannon-Prime reaches unbounded context by **exact** per-vector packing plus **disk-backed two-ring offload**, with the same MTP decode primitive — but byte-exact, auditable, and with clean rollback. Same lever, opposite philosophy: theirs is efficient and approximate; ours is efficient and **exact**.* This is a stronger framing than any number race, and it is already true on the measured record.

## 6. Verdict table

| V4 mechanic | Maps to (ours) | Verdict | Action |
|---|---|---|---|
| MTP (= V3's) | T8 / C4 spec-decode | external confirmation of the pillar | cite in C4; no build |
| Compressed/Heavily-Compressed Attention (seq-dim KV) | Spinor (per-vector) + ±1 router top-B + Ring-2 (seq-dim) | convergent; we are exact + disk-unbounded | roadmap narrative; no new build |
| Sinkhorn doubly-stochastic hyper-connections | (training-time) — candidate C5 receipt regularizer | real manifold, but out of scope for inference | note for C5 `[SPECULATIVE]` |
| FP4-QAT | OK_Q4 reducing codec (post-hoc) | Q4 floor already met without training | none |
| Muon / Newton–Schulz | — | training-only | none |
| DeepSeekMoE | qwen35moe MoE (bit-exact) | convergent | none |
