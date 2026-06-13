#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

.venv/bin/ruff check tests/test_app.py backend/app.py backend/research/config.py
.venv/bin/ruff format --check tests/test_app.py backend/app.py backend/research/config.py
.venv/bin/pytest -q \
  tests/test_app.py::test_health \
  tests/test_app.py::test_health_ready_checks_database_and_storage \
  tests/test_app.py::test_health_ready_checks_write_audit_dir_when_enabled \
  tests/test_app.py::test_optional_api_key_guard_protects_research_routes \
  tests/test_app.py::test_write_audit_admin_summary_disabled_by_default \
  tests/test_app.py::test_write_audit_admin_summary_requires_separate_admin_key \
  tests/test_app.py::test_upload_rejects_unsupported_file_type \
  tests/test_app.py::test_upload_rejects_file_larger_than_limit \
  tests/test_app.py::test_upload_rejects_binary_text_file_before_writing \
  tests/test_app.py::test_upload_rejects_pdf_without_pdf_header_before_writing \
  tests/test_app.py::test_workbench_static_assets_are_served \
  tests/test_app.py::test_project_onboarding_readiness_tracks_first_run_and_upload \
  tests/test_app.py::test_project_pilot_report_combines_onboarding_and_cockpit_state
