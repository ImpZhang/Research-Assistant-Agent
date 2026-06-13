#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

.venv/bin/ruff check tests/test_app.py backend/research/routes.py
.venv/bin/ruff format --check tests/test_app.py backend/research/routes.py
.venv/bin/pytest -q \
  tests/test_app.py::test_research_profile_guides_ranking_and_advisor_briefs \
  tests/test_app.py::test_refine_idea_creates_traceable_revision \
  tests/test_app.py::test_rank_ideas_deduplicates_lineage_and_returns_breakdown
