#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

.venv/bin/ruff check tests/test_app.py backend/research/services/literature_search_service.py backend/research/services/related_work_service.py backend/research/services/novelty_service.py backend/research/services/structured_extraction_service.py
.venv/bin/ruff format --check tests/test_app.py backend/research/services/literature_search_service.py backend/research/services/related_work_service.py backend/research/services/novelty_service.py backend/research/services/structured_extraction_service.py
.venv/bin/pytest -q \
  tests/test_app.py::test_literature_search_returns_local_results_with_external_disabled \
  tests/test_app.py::test_literature_search_rejects_empty_query \
  tests/test_app.py::test_literature_search_clamps_limit_and_sorts_combined_results \
  tests/test_app.py::test_literature_search_clamps_low_limit_and_truncates_results \
  tests/test_app.py::test_external_literature_provider_config_normalization \
  tests/test_app.py::test_external_literature_search_reports_not_configured_status \
  tests/test_app.py::test_external_literature_search_reports_completed_status \
  tests/test_app.py::test_external_literature_search_returns_partial_status \
  tests/test_app.py::test_external_literature_search_reports_failed_status \
  tests/test_app.py::test_openalex_literature_item_parser \
  tests/test_app.py::test_openalex_literature_item_parser_fallbacks \
  tests/test_app.py::test_openalex_inverted_index_abstract_reconstruction_edges \
  tests/test_app.py::test_arxiv_literature_item_parser \
  tests/test_app.py::test_arxiv_literature_item_parser_fallbacks \
  tests/test_app.py::test_semantic_scholar_literature_item_parser \
  tests/test_app.py::test_semantic_scholar_literature_item_parser_fallbacks \
  tests/test_app.py::test_extract_paper_card_from_evidence \
  tests/test_app.py::test_mine_research_gaps_from_evidence \
  tests/test_app.py::test_generate_ideas_from_gap \
  tests/test_app.py::test_review_and_experiment_plan_for_idea \
  tests/test_app.py::test_novelty_check_records_local_collision_screening \
  tests/test_app.py::test_novelty_service_scores_overlap_with_caps_and_weights \
  tests/test_app.py::test_novelty_service_external_overlap_score_respects_statuses \
  tests/test_app.py::test_novelty_service_missing_searches_risk_and_actions \
  tests/test_app.py::test_related_work_matrix_persists_overlap_rows_and_markdown \
  tests/test_app.py::test_related_work_service_build_query_cleans_defaults_and_clamps \
  tests/test_app.py::test_related_work_service_missing_searches_cover_external_statuses \
  tests/test_app.py::test_related_work_service_rows_sort_truncate_and_preserve_metadata \
  tests/test_app.py::test_markdown_exports_for_card_and_idea_dossier \
  tests/test_app.py::test_structured_extraction_prompt_limits_evidence_payload \
  tests/test_app.py::test_structured_card_extraction_falls_back_without_model_config
