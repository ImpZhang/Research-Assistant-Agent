#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cd "$PROJECT_ROOT"

if ! "$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)'; then
  echo "Python >= 3.12 is required. Set PYTHON_BIN=/path/to/python3.12 and rerun." >&2
  exit 1
fi

mkdir -p .cache data models outputs logs .docker
"$PYTHON_BIN" -m venv .venv

# shellcheck disable=SC1091
source "$PROJECT_ROOT/scripts/env.sh"

python -m pip install --upgrade pip
if [ -f "$PROJECT_ROOT/uv.lock" ]; then
  python -m pip install uv
  uv sync --frozen --extra dev
else
  python -m pip install -e ".[dev]"
fi

echo "Local environment ready at $PROJECT_ROOT/.venv"
