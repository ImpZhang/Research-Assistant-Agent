#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

.venv/bin/ruff check tests/test_app.py backend/research/routes.py backend/research/services/proposal_service.py backend/research/services/proposal_review_service.py backend/research/services/proposal_revision_service.py backend/research/services/decision_memo_service.py backend/research/services/assumption_audit_service.py backend/research/services/evidence_ledger_service.py backend/research/services/experiment_run_service.py backend/research/services/workflow_lineage_service.py
.venv/bin/ruff format --check tests/test_app.py backend/research/routes.py backend/research/services/proposal_service.py backend/research/services/proposal_review_service.py backend/research/services/proposal_revision_service.py backend/research/services/decision_memo_service.py backend/research/services/assumption_audit_service.py backend/research/services/evidence_ledger_service.py backend/research/services/experiment_run_service.py backend/research/services/workflow_lineage_service.py
.venv/bin/pytest -q \
  tests/test_app.py::test_proposal_draft_service_summarizes_attached_artifacts \
  tests/test_app.py::test_proposal_review_service_scores_decisions_and_missing_evidence \
  tests/test_app.py::test_downstream_artifacts_record_standalone_lineage \
  tests/test_app.py::test_proposal_revision_service_applies_review_actions_and_fallbacks
