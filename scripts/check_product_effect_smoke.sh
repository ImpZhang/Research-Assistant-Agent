#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

RUN_ID="${RUN_ID:-$(date +%s%N)}"
SMOKE_DATA_DIR="${PRODUCT_EFFECT_SMOKE_DATA_DIR:-./data/test-runs/product-effect-smoke-${RUN_ID}}"
SMOKE_TIMEOUT_SECONDS="${PRODUCT_EFFECT_SMOKE_TIMEOUT_SECONDS:-300}"
mkdir -p "${SMOKE_DATA_DIR}/papers" "${SMOKE_DATA_DIR}/research"

if [[ -n "${PRODUCT_EFFECT_SMOKE_BASE_URL:-}" ]]; then
  exec timeout "${SMOKE_TIMEOUT_SECONDS}" \
    .venv/bin/python scripts/smoke_api.py --base-url "${PRODUCT_EFFECT_SMOKE_BASE_URL}"
fi

exec env \
  RESEARCH_DB_URL="sqlite:///${SMOKE_DATA_DIR}/research/research_assistant.db" \
  PAPER_UPLOAD_DIR="${SMOKE_DATA_DIR}/papers" \
  EXTERNAL_LITERATURE_SEARCH_ENABLED="${PRODUCT_EFFECT_EXTERNAL_LITERATURE_SEARCH_ENABLED:-false}" \
  timeout "${SMOKE_TIMEOUT_SECONDS}" \
  .venv/bin/python scripts/smoke_api.py
