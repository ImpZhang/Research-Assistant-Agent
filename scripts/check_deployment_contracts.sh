#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

.venv/bin/ruff check tests/test_app.py
.venv/bin/ruff format --check tests/test_app.py
.venv/bin/pytest -q \
  tests/test_app.py::test_deployment_artifacts_document_customer_runtime \
  tests/test_app.py::test_local_agent_readiness_contract \
  tests/test_app.py::test_local_runtime_smoke_contract
