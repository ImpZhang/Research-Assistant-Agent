#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

.venv/bin/ruff check tests/test_app.py tests/test_mcp_http_bridge.py scripts/mcp_http_bridge.py backend/research/routes.py
.venv/bin/ruff format --check tests/test_app.py tests/test_mcp_http_bridge.py scripts/mcp_http_bridge.py backend/research/routes.py
.venv/bin/pytest -q \
  tests/test_app.py::test_tool_manifest_lists_mcp_ready_research_tools \
  tests/test_app.py::test_tool_bridge_spec_maps_manifest_to_http_tool_schemas \
  tests/test_mcp_http_bridge.py
