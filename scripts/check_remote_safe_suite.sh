#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

bash scripts/check_pilot_readiness.sh
bash scripts/check_graph_rag_lite.sh
bash scripts/check_context_search_evaluations.sh
