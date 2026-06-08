# P2b Phase 0 — cloud RUNBOOK (ready for the 7pm unlock)

**Goal tonight:** G-P2b-0 telemetry — 50 spans × Arm F + 50 × Arm H, k=2, n=6.
Telemetry-then-pin: tonight produces the numbers; the tolerance band is pinned
from them, never before them. **No pass/fail is claimed tonight.**

## 0. Pod spec
- RunPod: 1× A100 80GB (or 40GB — fits: 23.9 GB bf16 weights + tiny activations
  at T≈94, batch 1). Colab Pro A100 40GB also works.
- Image: any recent PyTorch CUDA image. No pip installs needed beyond torch
  (the harness is dependency-free on purpose — no transformers, no datasets).

## 1. Get the weights (two options)
- **(A) preferred:** download the official gemma-4-12b checkpoint pod-side
  (HF hub), then VERIFY against `bucket_manifest.json` (uploaded, tiny):
  file sizes, safetensors header sha256 (`d8b49f99…`), tensor_count 678,
  head/tail-1MB digests. **Any mismatch = STOP** (the GGUF campaign is why).
- **(B) exact:** upload our local bucket (23.9 GB — slow; only if (A) mismatches).

## 2. Upload (small files)
`invert_p0.py`, `bucket_manifest.json`, `wiki_tokens.txt`
(= local `_g4_12b_wiki_tokens.txt` — the verified llama-dumped == HF fixture;
the harness consumes token IDS, so no tokenizer is needed pod-side).

## 3. Smoke, then the batch
```
# 2-span smoke (~2 min): confirms load + forward + both arms on the GPU
python invert_p0.py --model-dir <bucket> --tokens wiki_tokens.txt \
    --spans 2 --steps 50 --arm F --out smoke_F
python invert_p0.py --model-dir <bucket> --tokens wiki_tokens.txt \
    --spans 2 --steps 50 --arm H --out smoke_H

# the G-P2b-0 telemetry batch (est. 1-3 h total; per-span prints are the heartbeat)
python invert_p0.py --model-dir <bucket> --tokens wiki_tokens.txt \
    --spans 50 --steps 300 --arm F --out p0_F
python invert_p0.py --model-dir <bucket> --tokens wiki_tokens.txt \
    --spans 50 --steps 300 --arm H --out p0_H
```
Toy mode (already run green locally 2026-06-09, both arms; XBE1 header
byte-verified): `--toy` exercises every code path without the model.

## 4. What to bring home (the receipts)
- `p0_F/receipts_F.json`, `p0_H/receipts_H.json` — args echo + per-span
  kl_start / kl_final / kl_span_dropped + manifold diagnostics
  (dist_nearest_tok; hull_entropy for H).
- `golden_s*_{F,H}.pt` + `.xbe1` — the golden vectors; the `.xbe1` files go
  STRAIGHT into the 2060 parity probe (G-P2b-3) via `SP_XBAR_EMB` —
  the deployment interface is the P2.a harness, already built and G0E-proven.
- GPU model + wall-clock per span (for the Phase-1 training budget estimate).

## 5. Reading the numbers (what Phase 0 answers)
- **recovery_ratio = kl_final / kl_span_dropped.** The span-dropped baseline
  measures how much the span mattered at all; ratio ≪ 1 ⇒ the k=2 vectors
  recover most of the span's information ⇒ **amortized compression is licensed**
  (G-P2b-0 pins its band from tonight's distribution).
- **Arm F vs Arm H:** H is on-manifold by construction (watch hull_entropy);
  F's dist_nearest_tok maps how far off-hull free optima sit — the local
  manifold geometry the Phase-1 adapter needs.
- **Falsification (pre-stated in the contract):** if neither arm's k=2 beats
  the span-dropped baseline meaningfully across spans, 6→2 compression is dead
  at this ratio; re-scope per CONTRACT-XBAR-P2b §1.

## 6. Discipline carried over
Banner echoes every arg (printed at start — check it in the log before the
batch). Receipts before conclusions. The pod is ephemeral; download receipts
BEFORE shutting it down. No number is citable from the cloud alone — every
behavioral claim re-verifies on the 2060/B1 artifact via G-P2b-3.
