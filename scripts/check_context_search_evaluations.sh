#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

.venv/bin/ruff check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py
.venv/bin/ruff format --check tests/test_app.py backend/research/services/retrieval_service.py backend/research/services/embedding_service.py
.venv/bin/pytest -q \
  tests/test_app.py::test_context_search_ranking_tie_breaks_by_matched_terms_and_recency \
  tests/test_app.py::test_context_search_empty_query_guard_fixture \
  tests/test_app.py::test_context_search_deduplicates_repeated_query_terms \
  tests/test_app.py::test_context_search_clamps_non_positive_limit \
  tests/test_app.py::test_context_search_clamps_large_limit \
  tests/test_app.py::test_context_search_paper_filter_evaluation_fixture \
  tests/test_app.py::test_context_search_returns_evidence_and_graph_context
