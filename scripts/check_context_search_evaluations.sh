#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

.venv/bin/ruff check tests/test_app.py
.venv/bin/ruff format --check tests/test_app.py
.venv/bin/pytest -q \
  tests/test_app.py::test_context_search_empty_query_guard_fixture \
  tests/test_app.py::test_context_search_paper_filter_evaluation_fixture \
  tests/test_app.py::test_context_search_returns_evidence_and_graph_context
