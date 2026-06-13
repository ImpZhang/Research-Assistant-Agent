#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

.venv/bin/ruff check tests/test_app.py backend/app.py backend/research/config.py backend/research/services/write_audit_service.py
.venv/bin/ruff format --check tests/test_app.py backend/app.py backend/research/config.py backend/research/services/write_audit_service.py
.venv/bin/pytest -q \
  tests/test_app.py::test_write_operation_audit_jsonl_records_sanitized_metadata \
  tests/test_app.py::test_write_operation_audit_records_failed_api_key_fingerprint \
  tests/test_app.py::test_write_operation_audit_disabled_by_default \
  tests/test_app.py::test_write_audit_admin_summary_disabled_by_default \
  tests/test_app.py::test_write_audit_admin_summary_requires_separate_admin_key \
  tests/test_app.py::test_write_audit_admin_summary_returns_sanitized_aggregates \
  tests/test_app.py::test_write_audit_admin_export_returns_bounded_sanitized_jsonl
