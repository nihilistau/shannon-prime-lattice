#!/usr/bin/env bash
# M.0-real RunPod container bootstrap.
#
# Tested on the official RunPod template:
#   runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04
#
# Usage on a fresh pod (from /workspace):
#
#   git clone https://github.com/nihilistau/shannon-prime-lattice.git
#   cd shannon-prime-lattice/scripts/m0_real
#   bash runpod_init.sh
#   # then upload your dataset to /workspace/data/m0_real.jsonl
#   bash run_train.sh
#
# This script is idempotent — safe to re-run.

set -euo pipefail

WORKSPACE="${WORKSPACE:-/workspace}"
HF_CACHE="${HF_HOME:-$WORKSPACE/.hf_cache}"

echo "[init] workspace=$WORKSPACE  hf_cache=$HF_CACHE"
mkdir -p "$WORKSPACE/data" "$WORKSPACE/output" "$HF_CACHE"

# 1. Show GPU(s).
echo "[init] nvidia-smi:"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader || true

# 2. Pin HF cache to the persistent volume (NOT $HOME which is ephemeral on
#    many RunPod templates).
export HF_HOME="$HF_CACHE"
export TRANSFORMERS_CACHE="$HF_CACHE/transformers"
export HF_DATASETS_CACHE="$HF_CACHE/datasets"

# Persist across shells in this pod.
grep -q 'HF_HOME=' ~/.bashrc 2>/dev/null || cat >> ~/.bashrc <<EOF

# M.0-real M0-SFT environment
export HF_HOME="$HF_CACHE"
export TRANSFORMERS_CACHE="$HF_CACHE/transformers"
export HF_DATASETS_CACHE="$HF_CACHE/datasets"
export TOKENIZERS_PARALLELISM=false
EOF

# 3. Install python deps. RunPod's torch is already correct for the container's
#    CUDA; just skip torch if it's already at >=2.2.
echo "[init] installing python deps"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
pip install --no-cache-dir -r "$SCRIPT_DIR/requirements.txt"

# 4. Sanity-check torch CUDA visibility.
python - <<'PY'
import torch
print(f"[sanity] torch={torch.__version__}  cuda={torch.cuda.is_available()}  ngpu={torch.cuda.device_count()}")
if torch.cuda.is_available():
    for i in range(torch.cuda.device_count()):
        p = torch.cuda.get_device_properties(i)
        print(f"  gpu{i}: {p.name}  vram={p.total_memory / 1024**3:.1f} GB  sm{p.major}{p.minor}")
PY

# 5. Hugging Face login prompt (optional but recommended for gated bases like Llama).
echo "[init] (optional) huggingface-cli login  # for gated models"

echo "[init] done. Next steps:"
echo "  1. Place your training JSONL at $WORKSPACE/data/m0_real.jsonl"
echo "  2. Run: bash run_train.sh   (or invoke train_memory_sft.py directly)"
