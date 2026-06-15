#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

bash scripts/check_focused_test_coverage.sh
bash scripts/check_research_proposal_contracts.sh
exec bash scripts/check_project_delivery_loop.sh
