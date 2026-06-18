#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

.venv/bin/ruff check tests/test_app.py backend/app.py backend/research/config.py
.venv/bin/ruff format --check tests/test_app.py backend/app.py backend/research/config.py
.venv/bin/pytest -q \
  tests/test_app.py::test_health \
  tests/test_app.py::test_health_ready_includes_build_metadata \
  tests/test_app.py::test_health_ready_checks_database_and_storage \
  tests/test_app.py::test_health_ready_reports_missing_api_key_when_auth_is_enabled \
  tests/test_app.py::test_health_ready_checks_write_audit_dir_when_enabled \
  tests/test_app.py::test_health_ready_checks_external_literature_configuration \
  tests/test_app.py::test_research_status \
  tests/test_app.py::test_project_scope_reports_default_compatibility_boundary \
  tests/test_app.py::test_optional_api_key_guard_protects_research_routes \
  tests/test_app.py::test_write_audit_admin_summary_disabled_by_default \
  tests/test_app.py::test_write_audit_admin_summary_requires_separate_admin_key \
  tests/test_app.py::test_upload_rejects_unsupported_file_type \
  tests/test_app.py::test_upload_respects_allowed_extensions_override_before_writing \
  tests/test_app.py::test_upload_allowed_extensions_override_normalizes_values \
  tests/test_app.py::test_upload_accepts_uppercase_allowed_extension \
  tests/test_app.py::test_upload_rejects_empty_file_before_writing \
  tests/test_app.py::test_upload_rejects_file_larger_than_limit \
  tests/test_app.py::test_upload_invalid_max_bytes_falls_back_to_default_limit \
  tests/test_app.py::test_upload_non_positive_max_bytes_falls_back_to_default_limit \
  tests/test_app.py::test_upload_rejects_binary_text_file_before_writing \
  tests/test_app.py::test_upload_rejects_non_utf8_text_before_writing \
  tests/test_app.py::test_upload_rejects_pdf_without_pdf_header_before_writing \
  tests/test_app.py::test_upload_sanitizes_path_traversal_filename \
  tests/test_app.py::test_upload_text_paper \
  tests/test_app.py::test_upload_markdown_paper_uses_default_allowed_extension \
  tests/test_app.py::test_workbench_static_assets_are_served \
  tests/test_app.py::test_workbench_user_path_contract_supports_pilot_demo_loop \
  tests/test_app.py::test_project_onboarding_readiness_tracks_first_run_and_upload \
  tests/test_app.py::test_project_setup_wizard_saves_profile_and_returns_readiness \
  tests/test_app.py::test_project_onboarding_tasks_create_task_board_items_and_graph_edges \
  tests/test_app.py::test_project_onboarding_progress_tracks_task_completion \
  tests/test_app.py::test_project_pilot_report_combines_onboarding_and_cockpit_state \
  tests/test_app.py::test_project_pilot_report_snapshots_persist_and_export_markdown
