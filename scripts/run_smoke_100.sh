#!/usr/bin/env bash
set -euo pipefail

DATASET="${DATASET:-data/FormalRx_Test.jsonl}"
BASE_URL="${BASE_URL:-http://127.0.0.1:8001/v1}"
MODEL="${MODEL:-criticleanGPT-Qwen3-8B-RL}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
TIMEOUT="${TIMEOUT:-300}"
MAX_TOKENS="${MAX_TOKENS:-1024}"

"$PYTHON_BIN" -m clearrx.run_formalrx \
  --dataset "$DATASET" \
  --base-url "$BASE_URL" \
  --model "$MODEL" \
  --limit 100 \
  --timeout "$TIMEOUT" \
  --max-tokens "$MAX_TOKENS" \
  --output outputs/formalrx_first100_predictions.jsonl \
  --report outputs/formalrx_first100_report.json \
  --zip-output outputs/formalrx_first100_predictions.zip \
  --fail-on-error

"$PYTHON_BIN" scripts/validate_predictions.py \
  --dataset "$DATASET" \
  --predictions outputs/formalrx_first100_predictions.jsonl \
  --expected-count 100
