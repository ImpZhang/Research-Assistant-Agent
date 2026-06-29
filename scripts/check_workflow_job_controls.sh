#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

.venv/bin/ruff check tests/test_app.py backend/research/models.py backend/research/schemas.py backend/research/services/agent_trace_service.py backend/research/services/workflow_lineage_service.py backend/research/services/workflow_service.py backend/research/services/workflow_worker_service.py backend/research/routes.py scripts/run_workflow_worker.py
.venv/bin/ruff format --check tests/test_app.py backend/research/models.py backend/research/schemas.py backend/research/services/agent_trace_service.py backend/research/services/workflow_lineage_service.py backend/research/services/workflow_service.py backend/research/services/workflow_worker_service.py backend/research/routes.py scripts/run_workflow_worker.py
.venv/bin/pytest -q \
  tests/test_app.py::test_literature_to_ideas_workflow_runs_full_pipeline \
  tests/test_app.py::test_async_literature_to_ideas_workflow_completes_job_trace \
  tests/test_app.py::test_async_literature_to_ideas_workflow_can_run_from_local_worker \
  tests/test_app.py::test_literature_workflow_resumes_from_checkpointed_outputs \
  tests/test_app.py::test_literature_workflow_records_failure_taxonomy_for_missing_paper \
  tests/test_app.py::test_local_workflow_worker_recovers_stale_running_job \
  tests/test_app.py::test_local_workflow_worker_can_queue_bounded_retry_for_failed_job \
  tests/test_app.py::test_agent_trace_records_run_tool_call_and_replay_case \
  tests/test_app.py::test_advisor_chat_records_agent_trace_tool_calls \
  tests/test_app.py::test_advisor_chat_captures_context_search_miss_replay_case \
  tests/test_app.py::test_advisor_chat_records_failed_tool_call_and_replay_case \
  tests/test_app.py::test_advisor_chat_uses_model_ranked_read_tool_selection \
  tests/test_app.py::test_job_cancel_and_retry_controls
