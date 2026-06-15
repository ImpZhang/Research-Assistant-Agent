#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

RUN_ID="${RUN_ID:-$(date +%s%N)}"
TEST_DATA_DIR="${PROJECT_DELIVERY_LOOP_TEST_DATA_DIR:-./data/test-runs/project-delivery-loop-${RUN_ID}}"
mkdir -p "${TEST_DATA_DIR}/papers" "${TEST_DATA_DIR}/research"

.venv/bin/ruff check tests/test_app.py backend/research/routes.py
.venv/bin/ruff format --check tests/test_app.py backend/research/routes.py
exec env \
  RESEARCH_DB_URL="sqlite:///${TEST_DATA_DIR}/research/research_assistant.db" \
  PAPER_UPLOAD_DIR="${TEST_DATA_DIR}/papers" \
  EXTERNAL_LITERATURE_SEARCH_ENABLED=false \
  timeout "${PROJECT_DELIVERY_LOOP_TIMEOUT_SECONDS:-900}" \
  .venv/bin/pytest -q tests/test_app.py::test_project_delivery_loop_bundles_proposal_to_pilot_handoff
