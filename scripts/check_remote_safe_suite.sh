#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

bash scripts/check_suite_contracts.sh
bash scripts/check_script_catalog.sh
bash scripts/check_local_agent_readiness.sh
bash scripts/check_secret_file_guard.sh
bash scripts/check_handoff_docs.sh
bash scripts/check_generated_file_guard.sh
bash scripts/check_focused_test_coverage.sh
bash scripts/check_project_skills.sh
bash scripts/check_pilot_operational_preflight.sh
bash scripts/check_pilot_readiness.sh
bash scripts/check_deployment_contracts.sh
bash scripts/check_backup_restore_contracts.sh
bash scripts/check_research_workflow_primitives.sh
bash scripts/check_research_planning_contracts.sh
bash scripts/check_write_audit_guardrails.sh
bash scripts/check_workflow_job_controls.sh
bash scripts/check_tool_bridge_contracts.sh
bash scripts/check_graph_rag_lite.sh
bash scripts/check_context_search_evaluations.sh
