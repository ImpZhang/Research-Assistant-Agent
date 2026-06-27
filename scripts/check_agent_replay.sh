#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

.venv/bin/ruff check scripts/replay_agent_case.py tests/test_agent_replay_script.py
.venv/bin/ruff format --check scripts/replay_agent_case.py tests/test_agent_replay_script.py
.venv/bin/pytest -q tests/test_agent_replay_script.py
