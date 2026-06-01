#!/usr/bin/env bash
# M.0-real — one-shot dataset generation launcher.
#
# Two stages:
#   1. Template bootstrap (no GPU; ~1k examples in seconds) — runs first
#      so you have *something* to feed the train pipeline immediately.
#   2. Teacher-LLM enrichment (uses GPU) — generates richer, more diverse
#      examples. Concatenates onto the bootstrap output.
#
# Override the entity table by passing ENTITIES=/path/to/entities.json.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

DATA_DIR="${DATA_DIR:-/workspace/data}"
OUT="${OUT:-$DATA_DIR/m0_real.jsonl}"
SEEDS="${SEEDS:-$SCRIPT_DIR/seed_topics.txt}"
ENTITIES="${ENTITIES:-}"
N_TEMPLATE="${N_TEMPLATE:-30}"      # examples per entity in template mode
N_TEACHER="${N_TEACHER:-50}"        # examples per entity in teacher mode
TEACHER="${TEACHER:-Qwen/Qwen2.5-7B-Instruct}"
MULTI_TURN="${MULTI_TURN:-0}"       # set to 1 to use full 3-turn examples
SKIP_TEMPLATE="${SKIP_TEMPLATE:-0}"
SKIP_TEACHER="${SKIP_TEACHER:-0}"

mkdir -p "$DATA_DIR"

EXTRA_FLAGS=""
if [[ "$MULTI_TURN" == "1" ]]; then
  EXTRA_FLAGS="$EXTRA_FLAGS --multi_turn"
fi
if [[ -n "$ENTITIES" ]]; then
  EXTRA_FLAGS="$EXTRA_FLAGS --entities $ENTITIES"
fi

# ── Stage 1: template bootstrap ────────────────────────────────────────
if [[ "$SKIP_TEMPLATE" != "1" ]]; then
  BOOT="$DATA_DIR/m0_real_bootstrap.jsonl"
  echo "[1/2] template bootstrap -> $BOOT"
  python "$SCRIPT_DIR/generate_dataset.py" \
      --mode template \
      --out "$BOOT" \
      --seeds "$SEEDS" \
      --n_per_seed "$N_TEMPLATE" \
      $EXTRA_FLAGS
  cp "$BOOT" "$OUT"
  echo "[1/2] $(wc -l <"$BOOT") bootstrap examples"
else
  echo "[1/2] SKIP_TEMPLATE=1 — skipping bootstrap"
  : > "$OUT"   # empty file so the cat below succeeds
fi

# ── Stage 2: teacher-LLM enrichment ────────────────────────────────────
if [[ "$SKIP_TEACHER" != "1" ]]; then
  ENRICH="$DATA_DIR/m0_real_teacher.jsonl"
  echo "[2/2] teacher-LLM enrichment -> $ENRICH"
  echo "      teacher=$TEACHER  n_per_seed=$N_TEACHER"
  if ! python -c 'import torch; assert torch.cuda.is_available()' 2>/dev/null; then
    echo "      WARNING: no CUDA visible — teacher mode will be very slow on CPU"
  fi
  python "$SCRIPT_DIR/generate_dataset.py" \
      --mode teacher \
      --out "$ENRICH" \
      --seeds "$SEEDS" \
      --n_per_seed "$N_TEACHER" \
      --teacher "$TEACHER" \
      $EXTRA_FLAGS
  cat "$ENRICH" >> "$OUT"
  echo "[2/2] $(wc -l <"$ENRICH") teacher examples appended"
else
  echo "[2/2] SKIP_TEACHER=1 — skipping enrichment"
fi

# ── Summary ────────────────────────────────────────────────────────────
TOTAL=$(wc -l <"$OUT")
echo "── done ─────────────────────────────────────────────────────"
echo "  combined dataset: $OUT"
echo "  total examples:   $TOTAL"
echo "  next: bash run_train.sh   (will pick up DATASET=$OUT)"
