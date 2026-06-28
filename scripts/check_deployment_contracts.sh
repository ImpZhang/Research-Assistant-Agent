#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

.venv/bin/ruff check \
  tests/test_app.py \
  tests/test_local_doctor.py \
  tests/test_sqlite_maintenance.py \
  tests/test_single_user_docker_deployment.py \
  tests/test_migration_baseline.py \
  tests/test_model_provider_config.py \
  scripts/check_single_user_docker_deployment.py \
  scripts/check_sqlite_maintenance.py \
  scripts/check_migration_baseline.py \
  scripts/check_model_provider_config.py
.venv/bin/ruff format --check \
  tests/test_app.py \
  tests/test_local_doctor.py \
  tests/test_sqlite_maintenance.py \
  tests/test_single_user_docker_deployment.py \
  tests/test_migration_baseline.py \
  tests/test_model_provider_config.py \
  scripts/check_single_user_docker_deployment.py \
  scripts/check_sqlite_maintenance.py \
  scripts/check_migration_baseline.py \
  scripts/check_model_provider_config.py
.venv/bin/pytest -q \
  tests/test_app.py::test_deployment_artifacts_document_customer_runtime \
  tests/test_app.py::test_local_agent_readiness_contract \
  tests/test_app.py::test_local_runtime_smoke_contract \
  tests/test_local_doctor.py \
  tests/test_sqlite_maintenance.py \
  tests/test_single_user_docker_deployment.py \
  tests/test_migration_baseline.py \
  tests/test_model_provider_config.py
