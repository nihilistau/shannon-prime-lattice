# M.0-real — Memory Model SFT (RunPod)

Training script for the **Memory artifact** used by `sp_daemon`'s
`/v1/dialogue` endpoint (3-turn Grounding → Entity ID → Synthesis dialogue
protocol from sprint M.2). The Memory model handles the Entity-ID step;
this script fine-tunes a small base model (Qwen2.5-0.5B default) on
dialogue-formatted JSONL data.

Status filed in roadmap **Band D** as of 2026-06-01.

---

## 1. RunPod setup

Spin up a pod with the official PyTorch template:

```
runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04
```

Recommended GPU: **1× A40 / A6000 / RTX 4090 (24 GB)** for LoRA on
Qwen2.5-0.5B with `batch=16`. QLoRA (`--load_4bit`) drops VRAM to ~6 GB.

Persistent volume mounted at `/workspace`. Inside the pod:

```bash
cd /workspace
git clone https://github.com/nihilistau/shannon-prime-lattice.git
cd shannon-prime-lattice/scripts/m0_real
bash runpod_init.sh
```

`runpod_init.sh` is idempotent — installs deps, pins HF cache to persistent
volume, sanity-checks CUDA visibility.

---

## 2. Dataset format

JSONL, one example per line, HF chat-template `messages` format:

```json
{"messages": [
  {"role": "system",    "content": "You are the Memory module. Given a grounded fact, return its canonical entity ID."},
  {"role": "user",      "content": "Fact: Snapdragon 8 Gen 1 launched in late 2021 with Hexagon V69."},
  {"role": "assistant", "content": "ENTITY:CHIP/SNAPDRAGON_8GEN1"}
]}
{"messages": [...]}
```

Upload to `/workspace/data/m0_real.jsonl`. The script does a 90/10 train/eval
split automatically if `--eval_dataset` is not provided.

For the 3-turn protocol, each example can be a single turn (most efficient
for SFT) or all three turns concatenated — the chat template handles both.

---

## 3. Train

One-shot:

```bash
bash run_train.sh
```

That uses the defaults below. Override via env:

```bash
BASE_MODEL=Qwen/Qwen2.5-1.5B \
EPOCHS=5 \
BATCH=8 \
LR=1e-4 \
EXTRA='--load_4bit' \
bash run_train.sh
```

Or invoke `train_memory_sft.py` directly for full control. `python train_memory_sft.py --help` lists every flag.

### Default training config

| Parameter | Value | Notes |
|---|---|---|
| Base model | `Qwen/Qwen2.5-0.5B` | HD=64; small enough for 24 GB VRAM full SFT |
| Adapter | LoRA r=16 α=32 dropout=0.05 | targets q/k/v/o/gate/up/down |
| Epochs | 3 | bump to 5 for small datasets |
| Per-device batch | 16 | reduce for larger base models |
| Grad accum | 2 | effective batch = 32 (single GPU) |
| LR | 2e-4 | LoRA-typical |
| Schedule | cosine, 3% warmup | |
| Precision | bf16 | A100/A40/RTX40+ supported |
| Gradient checkpointing | on | -30% memory, ~+15% time |
| `--merge_lora` | yes | single combined checkpoint at output_dir/final |

### Multi-GPU

`run_train.sh` auto-detects multiple GPUs and launches via `accelerate`.
Force a single GPU with `CUDA_VISIBLE_DEVICES=0 bash run_train.sh`.

---

## 4. Export to `.sp-model`

After training, convert the HF checkpoint to GGUF, then to Shannon-Prime
`.sp-model` via the engine's `sp_transcode` tool:

```bash
# 1. HF -> GGUF (use llama.cpp's converter or HF gguf-my-repo)
python convert_hf_to_gguf.py /workspace/output/memory-sft-v0/final \
    --outfile /workspace/output/memory-sft-v0.gguf

# 2. GGUF -> .sp-model (Q8 by default; see sp_transcode --help for Q4)
/workspace/shannon-prime-system-engine/build-cpu/bin/sp_transcode \
    /workspace/output/memory-sft-v0.gguf \
    /workspace/output/memory-sft-v0.sp-model
```

The resulting `.sp-model` plugs into `sp_daemon` via the `--memo-model` flag.

---

## 5. Validation against math-core

After upload to the daemon, run `/v1/dialogue` end-to-end:

```bash
curl -X POST http://daemon-host:8080/v1/dialogue \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What chip is in the Samsung S22 Ultra?",
    "memo_model": "memory-sft-v0.sp-model"
  }'
```

Expected response includes 3 base64 `SpinorReceipt` envelopes (one per
turn). Bit-exact gate: the receipts replay byte-identically across runs
when sampled greedy. See `feedback-drop-fp32-baseline-comparing-to-ourselves`
— compare against the prior Memory model, not against fp32 ref.

---

## 6. Cost estimate (RunPod, June 2026)

| GPU | Qwen2.5-0.5B LoRA | Qwen2.5-1.5B LoRA | Qwen2.5-0.5B full SFT |
|---|---|---|---|
| RTX 4090 (24 GB) | ~$0.50/hr × 2-3 hr | ~$0.50/hr × 4-6 hr | OOM (use QLoRA) |
| A40 (48 GB) | ~$0.50/hr × 2-3 hr | ~$0.50/hr × 4-6 hr | ~$0.50/hr × 3-5 hr |
| A100 (80 GB) | ~$1.20/hr × 1-2 hr | ~$1.20/hr × 2-4 hr | ~$1.20/hr × 2-3 hr |

Typical 10k-example dataset, 3 epochs.

---

## 7. Files

- `train_memory_sft.py` — main training script
- `run_train.sh` — one-shot launcher with defaults
- `runpod_init.sh` — RunPod container bootstrap (idempotent)
- `requirements.txt` — pinned Python deps
- `README.md` — this file

---

## 8. Composition

- M-series sprints define the dialogue protocol this trains for (M.1 / M.2 / M.4 / M.5)
- `feedback-drop-fp32-baseline-comparing-to-ourselves` — baseline framing for evals
- Roadmap Band D — filed
