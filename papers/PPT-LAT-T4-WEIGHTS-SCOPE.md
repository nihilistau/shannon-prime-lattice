---
type: design
title: "T4 Frobenius π^k of the model WEIGHTS — pre-registered feasibility kill-test (G-T4-WEIGHTS)"
description: "The falsifiable scope for applying the T4 Frobenius π^k integer codec (validated on Ring-2 episodes as G-R2-FROB) to the real gemma-4-12B WEIGHT tensors. Pre-registers the decisive question — does the Frobenius representation beat the shipped OK_Q4B (~4.5 effective bits/weight) either by compressing below it at ≤ its reconstruction error, or by improving fidelity at ≤ 4.5 bits — with the honest-negative branch (T4 redundant vs OK_Q4B) stated up front. Resolves the standing tension between the roadmap ('validated, untouched lever') and the CLAUDE.md prior-edge note ('CONVICTED redundant vs OK_Q4B'). Method reuses tools/curator/frob_episode.py::encode; no GPU, no full-model load."
tags: [design, scope, kill-test, t4, frobenius, weights, quantization, ok_q4b, boundary-thesis]
timestamp: 2026-07-01T00:00:00Z
resource: shannon-prime-lattice/papers/PPT-LAT-T4-WEIGHTS-SCOPE.md
sp_status: HONEST-NEGATIVE
sp_gate: G-T4-WEIGHTS
sp_commit: "engine (t4_weights_probe + G-T4-WEIGHTS.log); lattice (this commit)"
sp_repro: "python tools/t4_weights_probe.py D:/Files/Models/Gemma4/gemma-4-12b-bucket/model.safetensors model.language_model.layers.0.self_attn.q_proj.weight"
---

# T4 Frobenius π^k of the model WEIGHTS — pre-registered kill-test

## 0. The standing tension this test resolves

The canon disagrees, on purpose, and this test settles it with a number:

- **Roadmap §2.4 + STATE §NEXT + Theory T4:** "T4 Frobenius π^k of the 9.4 GB model WEIGHTS is the validated, untouched lever" (Frobenius cancellation, bit-identical 6-sig-fig on Gemma3-1B; the per-tensor π^k scale is *free*; distinct from Möbius/T2 which failed its own object in `G-T2-WEIGHTS`).
- **CLAUDE.md prior-edge note:** "T4 Frobenius π^k of the model WEIGHTS (since **CONVICTED redundant vs OK_Q4B** — see PPT-LAT-STATE)".

Both can be true depending on the operating point, which is exactly why this is a measurement, not an argument. The resolution (Theory T4, 2026-06-18): **exact Frobenius *cancellation* needs the Q8 form (OK_Q8 ≈ 18 GB, does not fit the 2060); the shipped forward runs OK_Q4B (4-bit, 9.4 GB) which *applies* the per-block scale in fixed-point instead of cancelling it.** So the honest question is not "is T4 exact" (it is, at Q8) but **"does the Frobenius representation earn its keep at the 4-bit operating point we actually ship?"**

## 1. The decisive question (falsifiable)

**OK_Q4B baseline cost** (STATE: arena layout v2 = 4-bit codes + one f16 scale per 32-element block):
`4 + 16/32 = 4.5 effective bits/weight`.

The T4 win, if real, comes from the **"free" π^k scale**: if the Frobenius scale can be amortised over a group **much larger than 32** (per-row or per-tensor) and still reach 4-bit-code fidelity, then T4 spends fewer *scale* bits than OK_Q4B's per-32-block f16 — a genuine net reduction below 9.4 GB at equal quality. If instead the scale must shrink back to per-block to hold fidelity, the "free scale" property **does not transfer to weights** and T4 is redundant vs OK_Q4B.

## 2. Method (offline, reuses proven code)

- **Weights:** `D:/Files/Models/Gemma4/gemma-4-12b-bucket/model.safetensors` (bf16 source). Read a few representative tensors by parsing the safetensors header (no GPU, no full-model load): one FFN projection (the param bulk), one attention projection, and a slice of `embed_tokens`.
- **Baseline codec (OK_Q4B-equivalent):** per-32-block symmetric 4-bit + f16 block scale. Report reconstruction `relL2` and effective bits/weight (4.5).
- **T4 candidate codec:** `tools/curator/frob_episode.py::encode` (the validated G-R2-FROB rank-2 O_K-lattice π^k codec: coarse coord `a` at scale `s_a` + optional error-feedback residual `b` at `s_b`), swept over **scale granularity** {per-tensor, per-row, per-32-block} × **bit config** {a4, a4b2, a4b4, a8}. Report `relL2` + effective bits/weight for each (scale bits amortised by group size).
- **Anti-rebuild:** reuse `frob_episode.encode`; the only new file is the probe harness `tools/t4_weights_probe.py`.

## 3. Pre-registered gate — G-T4-WEIGHTS

Decided on **fidelity-per-effective-bit**, on **every** probe tensor:

- **GREEN (proceed to wire a real weight path):** some T4 config attains `relL2 ≤` the OK_Q4B baseline `relL2` at **strictly fewer** effective bits/weight (e.g. per-tensor `a4` ≈ 4.03 bits matching per-32-block 4.5-bit fidelity), OR strictly lower `relL2` at ≤ 4.5 bits — a real net win, on all tensors.
- **HONEST-NEGATIVE (bank + attach; T4-on-weights redundant vs OK_Q4B):** no T4 config beats OK_Q4B's fidelity-per-bit — i.e. matching fidelity requires the scale to shrink to ~per-block, so the Frobenius "free scale" does not transfer to trained weight tensors. This would extend the boundary thesis to one more object (structure-on-content inert; the container wins, not the content).
- **Kill condition (stated up front):** per-tensor / per-row Frobenius scale collapses fidelity and only per-block recovers it ⇒ NEGATIVE.

No silent gate revision: whichever branch fires is recorded with receipts in `VERIFIED-SCOREBOARD.md` + `PPT-LAT-FINDINGS-LEDGER.md`, and banked to MEM-OKF.

## 4. Result — HONEST-NEGATIVE (G-T4-WEIGHTS, 2026-07-01)

**T4 Frobenius π^k is redundant vs OK_Q4B as a 4-bit weight compression lever** — 3/3 probe tensors, layers {0, 23}, attention + FFN. Receipt: engine `tests/fixtures/t4_weights/G-T4-WEIGHTS.log` (`t4_weights_probe.py` on the bf16 source).

| tensor | OK_Q4B (per-32blk, 4.5 b/w) | T4 per-tensor a4 (4.0 b/w) | T4 per-row a4 (~4.0 b/w) | T4 per-32blk a4 (4.5 b/w) |
|---|---|---|---|---|
| `L0 q_proj` | relL2 **0.1211** | 0.3962 | 0.2377 | 0.1211 (== baseline) |
| `L0 down_proj` (FFN bulk) | relL2 **0.1219** | 0.3986 | 0.2787 | 0.1219 (== baseline) |
| `L23 o_proj` | relL2 **0.1012** | 0.4074 | 0.2146 | 0.1012 (== baseline) |

The pre-registered **kill condition fired exactly**: to match OK_Q4B's fidelity the Frobenius scale must be **per-32-block** (where the codec is *identical* to OK_Q4B — the harness sanity check). Amortising the scale to per-tensor (the "free scale" T4 win) costs **~3.3–4× the reconstruction error to save 0.5 bits**; per-row is ~2× worse. The rank-2 error-feedback residual (`a4b2`/`a4b4`) lowers error only by **spending more bits** (6–9 b/w), never beating OK_Q4B's fidelity-per-bit.

**Why (mechanism):** trained weight tensors carry **per-block dynamic range / outliers** that per-block scaling captures and a single per-tensor/per-row π^k scale cannot. The Frobenius "free scale" property that holds on the Ring-2 **episodes** (`G-R2-FROB`, sub-ULP at 24b) **does not transfer to the weights**.

**No overclaim:** this refutes T4 as a *weight-compression* lever below OK_Q4B — **not** the T4 exact *cancellation* property (real, needs Q8 ≈ 18 GB, buys **auditability**, not compression). This resolves the standing tension in favour of the CLAUDE.md prior-edge note ("CONVICTED redundant vs OK_Q4B") and extends the **boundary thesis** to one more object: the container wins on exact arithmetic; number-theoretic structure imposed on the high-entropy **content** (now the weights, as with T2/Möbius in `G-T2-WEIGHTS`) is measured-inert. Honest negative — banked, attached, closed. `sp_status: HONEST-NEGATIVE`.
