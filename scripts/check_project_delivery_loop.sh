#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

.venv/bin/ruff check tests/test_app.py backend/research/routes.py
.venv/bin/ruff format --check tests/test_app.py backend/research/routes.py
.venv/bin/pytest -q tests/test_app.py::test_project_delivery_loop_bundles_proposal_to_pilot_handoff
