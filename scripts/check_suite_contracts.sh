#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

python3 - <<'PYIN'
from pathlib import Path
import sys

safe_path = Path("scripts/check_remote_safe_suite.sh")
long_path = Path("scripts/check_remote_long_suite.sh")
safe = safe_path.read_text(encoding="utf-8")
long = long_path.read_text(encoding="utf-8")

errors = []
required_safe = [
    "bash scripts/check_suite_contracts.sh",
    "bash scripts/check_script_catalog.sh",
    "bash scripts/check_secret_file_guard.sh",
    "bash scripts/check_handoff_docs.sh",
    "bash scripts/check_generated_file_guard.sh",
    "bash scripts/check_focused_test_coverage.sh",
    "bash scripts/check_pilot_readiness.sh",
    "bash scripts/check_deployment_contracts.sh",
    "bash scripts/check_research_workflow_primitives.sh",
    "bash scripts/check_research_planning_contracts.sh",
    "bash scripts/check_write_audit_guardrails.sh",
    "bash scripts/check_workflow_job_controls.sh",
    "bash scripts/check_tool_bridge_contracts.sh",
    "bash scripts/check_graph_rag_lite.sh",
    "bash scripts/check_context_search_evaluations.sh",
]
for command in required_safe:
    if command not in safe:
        errors.append(f"{safe_path} is missing `{command}`")

for forbidden in [
    "bash scripts/check_remote_long_suite.sh",
    "bash scripts/check_research_proposal_contracts.sh",
]:
    if forbidden in safe:
        errors.append(f"{safe_path} must not run long check `{forbidden}`")

required_long = [
    "bash scripts/check_focused_test_coverage.sh",
    "bash scripts/check_research_proposal_contracts.sh",
]
for command in required_long:
    if command not in long:
        errors.append(f"{long_path} is missing `{command}`")

if "bash scripts/check_remote_safe_suite.sh" in long:
    errors.append(f"{long_path} must not recursively run the default remote-safe suite")

if errors:
    print("Focused suite contract violations:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("Focused suite contracts are valid.")
PYIN
