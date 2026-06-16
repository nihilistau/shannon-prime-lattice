#!/usr/bin/env bash
# M.0-real — one-shot training launcher with sensible defaults for RunPod.
#
# Override any flag with env vars or by editing this file.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── tunables (override via env) ────────────────────────────────────────
BASE_MODEL="${BASE_MODEL:-Qwen/Qwen2.5-0.5B}"
DATASET="${DATASET:-/workspace/data/m0_real.jsonl}"
OUTPUT_DIR="${OUTPUT_DIR:-/workspace/output/memory-sft-$(date +%Y%m%d-%H%M%S)}"
EPOCHS="${EPOCHS:-3}"
BATCH="${BATCH:-16}"
GRAD_ACCUM="${GRAD_ACCUM:-2}"
LR="${LR:-2e-4}"
MAX_SEQ="${MAX_SEQ:-2048}"
EXTRA="${EXTRA:-}"   # space-separated extra flags, e.g. EXTRA='--load_4bit --no_lora'

# ── sanity ─────────────────────────────────────────────────────────────
if [[ ! -f "$DATASET" ]]; then
  echo "ERROR: dataset not found at $DATASET" >&2
  echo "  upload your JSONL or set DATASET=<path>" >&2
  exit 1
fi
mkdir -p "$OUTPUT_DIR"

echo "[run] base=$BASE_MODEL"
echo "[run] data=$DATASET ($(wc -l <"$DATASET") lines)"
echo "[run] out=$OUTPUT_DIR"
echo "[run] epochs=$EPOCHS batch=$BATCH grad_accum=$GRAD_ACCUM lr=$LR"

# Multi-GPU detection
NGPU="$(python -c 'import torch; print(torch.cuda.device_count())')"
if [[ "$NGPU" -gt 1 ]]; then
  echo "[run] detected $NGPU GPUs — using accelerate launch"
  exec accelerate launch \
      --num_processes "$NGPU" \
      --mixed_precision bf16 \
      "$SCRIPT_DIR/train_memory_sft.py" \
      --base_model "$BASE_MODEL" \
      --dataset "$DATASET" \
      --output_dir "$OUTPUT_DIR" \
      --epochs "$EPOCHS" \
      --batch_size "$BATCH" \
      --grad_accum "$GRAD_ACCUM" \
      --lr "$LR" \
      --max_seq_len "$MAX_SEQ" \
      --merge_lora \
      $EXTRA
else
  echo "[run] single GPU"
  exec python "$SCRIPT_DIR/train_memory_sft.py" \
      --base_model "$BASE_MODEL" \
      --dataset "$DATASET" \
      --output_dir "$OUTPUT_DIR" \
      --epochs "$EPOCHS" \
      --batch_size "$BATCH" \
      --grad_accum "$GRAD_ACCUM" \
      --lr "$LR" \
      --max_seq_len "$MAX_SEQ" \
      --merge_lora \
      $EXTRA
fi
