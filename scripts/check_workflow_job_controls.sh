#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

.venv/bin/ruff check tests/test_app.py backend/research/services/workflow_service.py backend/research/routes.py
.venv/bin/ruff format --check tests/test_app.py backend/research/services/workflow_service.py backend/research/routes.py
.venv/bin/pytest -q \
  tests/test_app.py::test_literature_to_ideas_workflow_runs_full_pipeline \
  tests/test_app.py::test_async_literature_to_ideas_workflow_completes_job_trace \
  tests/test_app.py::test_job_cancel_and_retry_controls
