#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

.venv/bin/ruff check tests/test_app.py backend/research/services/graph_service.py
.venv/bin/ruff format --check tests/test_app.py backend/research/services/graph_service.py
.venv/bin/pytest -q \
  tests/test_app.py::test_graph_service_reuses_duplicate_edges \
  tests/test_app.py::test_graph_stats_reports_duplicate_edge_groups \
  tests/test_app.py::test_graph_stats_reports_orphan_edges_without_persisting_fixture \
  tests/test_app.py::test_graph_rag_lite_records_workflow_links
