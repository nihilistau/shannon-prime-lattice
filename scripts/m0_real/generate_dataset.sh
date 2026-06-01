#!/usr/bin/env bash
# M.0-real — one-shot dataset generation launcher.
#
# Pulls public HF Q&A + instruction datasets, reformats into the
# Memory-role chat-template, writes a single shuffled JSONL ready for
# run_train.sh. No teacher LLM needed — the source datasets are
# high-quality curated factual data covering broad topics, which is
# what the general-purpose Memory model must learn.
#
# Override defaults via env:
#   DATA_DIR=/workspace/data
#   OUT=/workspace/data/m0_real.jsonl
#   SOURCES=trivia_qa,nq_open,dolly_15k,squad_v2,sciq
#   PER_SOURCE=20000
#   CUSTOM=/path/to/your_in_domain.jsonl   (optional, appended)

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

DATA_DIR="${DATA_DIR:-/workspace/data}"
OUT="${OUT:-$DATA_DIR/m0_real.jsonl}"
SOURCES="${SOURCES:-trivia_qa,nq_open,dolly_15k,squad_v2,sciq}"
PER_SOURCE="${PER_SOURCE:-20000}"
CUSTOM="${CUSTOM:-}"

mkdir -p "$DATA_DIR"

EXTRA=""
if [[ -n "$CUSTOM" ]]; then
  if [[ ! -f "$CUSTOM" ]]; then
    echo "ERROR: CUSTOM=$CUSTOM does not exist" >&2
    exit 1
  fi
  EXTRA="--custom_jsonl $CUSTOM"
fi

echo "[gen] out=$OUT"
echo "[gen] sources=$SOURCES"
echo "[gen] per_source=$PER_SOURCE"
[[ -n "$CUSTOM" ]] && echo "[gen] custom=$CUSTOM"

python "$SCRIPT_DIR/generate_dataset.py" \
    --out "$OUT" \
    --sources "$SOURCES" \
    --per_source "$PER_SOURCE" \
    $EXTRA

echo "── done ─────────────────────────────────────────────────────"
echo "  dataset: $OUT"
echo "  total:   $(wc -l <"$OUT") examples"
echo "  next:    bash run_train.sh"
