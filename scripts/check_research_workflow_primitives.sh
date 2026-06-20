#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

.venv/bin/ruff check tests/test_app.py scripts/smoke_api.py backend/research/services/literature_search_service.py backend/research/services/related_work_service.py backend/research/services/novelty_service.py backend/research/services/structured_extraction_service.py backend/research/services/document_ingestion.py backend/research/services/gap_service.py backend/research/services/idea_service.py backend/research/services/evidence_ledger_service.py backend/research/services/paper_card_service.py backend/research/services/review_service.py backend/research/services/experiment_service.py
.venv/bin/ruff format --check tests/test_app.py scripts/smoke_api.py backend/research/services/literature_search_service.py backend/research/services/related_work_service.py backend/research/services/novelty_service.py backend/research/services/structured_extraction_service.py backend/research/services/document_ingestion.py backend/research/services/gap_service.py backend/research/services/idea_service.py backend/research/services/evidence_ledger_service.py backend/research/services/paper_card_service.py backend/research/services/review_service.py backend/research/services/experiment_service.py
.venv/bin/pytest -q \
  tests/test_app.py::test_product_effect_scorecard_separates_quality_from_completion \
  tests/test_app.py::test_literature_search_returns_local_results_with_external_disabled \
  tests/test_app.py::test_literature_search_rejects_empty_query \
  tests/test_app.py::test_literature_search_clamps_limit_and_sorts_combined_results \
  tests/test_app.py::test_literature_search_clamps_low_limit_and_truncates_results \
  tests/test_app.py::test_external_literature_provider_config_normalization \
  tests/test_app.py::test_markdown_gap_sections_are_mined_from_headings \
  tests/test_app.py::test_upload_preserves_preamble_when_only_reference_heading_matches \
  tests/test_app.py::test_upload_detects_roman_heading_sections_and_claim_gap_topup \
  tests/test_app.py::test_upload_filters_metadata_checklist_and_leading_chart_noise \
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
  tests/test_app.py::test_paper_card_service_maps_evidence_and_fills_problem_fallback \
  tests/test_app.py::test_paper_card_service_reports_missing_inputs \
  tests/test_app.py::test_extract_paper_card_from_evidence \
  tests/test_app.py::test_gap_service_builds_titles_reasons_and_approaches \
  tests/test_app.py::test_idea_service_builds_variants_and_preserves_lineage \
  tests/test_app.py::test_idea_service_carries_source_paper_evidence_context \
  tests/test_app.py::test_idea_service_uses_source_evidence_for_geolocalization_profiles \
  tests/test_app.py::test_idea_service_excludes_source_method_names_from_geolocalization_baselines \
  tests/test_app.py::test_evidence_ledger_routes_typed_source_evidence_to_claims \
  tests/test_app.py::test_evidence_ledger_ignores_source_context_collision_signals_as_counterevidence \
  tests/test_app.py::test_evidence_ledger_treats_local_related_work_rows_as_context \
  tests/test_app.py::test_research_packet_pins_latest_evidence_tasks_when_task_list_is_crowded \
  tests/test_app.py::test_mine_research_gaps_from_evidence \
  tests/test_app.py::test_generate_ideas_from_gap \
  tests/test_app.py::test_review_and_experiment_services_create_traceable_outputs \
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
