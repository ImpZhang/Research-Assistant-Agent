#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

.venv/bin/ruff check \
  tests/test_app.py \
  tests/test_evaluation_reports.py \
  tests/test_geoloc_eval_dataset_tools.py \
  tests/test_retrieval_provider_adapter.py \
  tests/test_sota_review_package.py \
  tests/test_sota_signoff_and_benchmark.py \
  tests/test_structured_idea_service.py \
  backend/app.py \
  backend/research/config.py \
  backend/research/routes.py \
  backend/research/schemas.py \
  backend/research/adapters/retrieval_provider_adapter.py \
  backend/research/adapters/model_adapter.py \
  backend/research/services/benchmark_comparison_service.py \
  backend/research/services/benchmark_evidence_service.py \
  backend/research/services/benchmark_runner_service.py \
  backend/research/services/evaluation_report_service.py \
  backend/research/services/experiment_run_service.py \
  backend/research/services/sota_review_service.py \
  backend/research/services/structured_idea_service.py \
  backend/research/services/retrieval_service.py \
  backend/research/services/embedding_service.py \
  scripts/evaluate_real_papers.py \
  scripts/build_geoloc_eval_dataset.py \
  scripts/check_geoloc_eval_dataset.py \
  scripts/benchmark_geoloc_predictions.py \
  scripts/prepare_local_geoloc_benchmark.py
.venv/bin/ruff format --check \
  tests/test_app.py \
  tests/test_evaluation_reports.py \
  tests/test_geoloc_eval_dataset_tools.py \
  tests/test_retrieval_provider_adapter.py \
  tests/test_sota_review_package.py \
  tests/test_sota_signoff_and_benchmark.py \
  tests/test_structured_idea_service.py \
  backend/app.py \
  backend/research/config.py \
  backend/research/routes.py \
  backend/research/schemas.py \
  backend/research/adapters/retrieval_provider_adapter.py \
  backend/research/adapters/model_adapter.py \
  backend/research/services/benchmark_comparison_service.py \
  backend/research/services/benchmark_evidence_service.py \
  backend/research/services/benchmark_runner_service.py \
  backend/research/services/evaluation_report_service.py \
  backend/research/services/experiment_run_service.py \
  backend/research/services/sota_review_service.py \
  backend/research/services/structured_idea_service.py \
  backend/research/services/retrieval_service.py \
  backend/research/services/embedding_service.py \
  scripts/evaluate_real_papers.py \
  scripts/build_geoloc_eval_dataset.py \
  scripts/check_geoloc_eval_dataset.py \
  scripts/benchmark_geoloc_predictions.py \
  scripts/prepare_local_geoloc_benchmark.py
bash scripts/check_local_geoloc_benchmark_smoke.sh
.venv/bin/pytest -q \
  tests/test_evaluation_reports.py \
  tests/test_geoloc_eval_dataset_tools.py \
  tests/test_retrieval_provider_adapter.py \
  tests/test_sota_review_package.py \
  tests/test_sota_signoff_and_benchmark.py \
  tests/test_structured_idea_service.py \
  tests/test_app.py::test_context_search_ranking_tie_breaks_by_matched_terms_and_recency \
  tests/test_app.py::test_context_search_empty_query_guard_fixture \
  tests/test_app.py::test_context_search_no_match_fixture \
  tests/test_app.py::test_context_search_idea_overall_score_bonus_breakdown \
  tests/test_app.py::test_context_search_gap_feasibility_bonus_breakdown \
  tests/test_app.py::test_context_search_evidence_confidence_bonus_breakdown \
  tests/test_app.py::test_context_search_exact_phrase_bonus_breakdown \
  tests/test_app.py::test_context_search_vector_hit_rescues_lexical_miss \
  tests/test_app.py::test_context_search_chunk_vector_hit_rescues_lexical_miss \
  tests/test_app.py::test_context_search_deduplicates_repeated_query_terms \
  tests/test_app.py::test_context_search_clamps_non_positive_limit \
  tests/test_app.py::test_context_search_clamps_large_limit \
  tests/test_app.py::test_context_search_paper_filter_evaluation_fixture \
  tests/test_app.py::test_context_search_graph_context_respects_paper_filter \
  tests/test_app.py::test_context_search_graph_expansion_keeps_relevant_edge_after_recent_noise \
  tests/test_app.py::test_context_search_returns_evidence_and_graph_context \
  tests/test_app.py::test_benchmark_profiles_report_builtin_readiness
