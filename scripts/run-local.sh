#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# shellcheck disable=SC1091
source "$PROJECT_ROOT/scripts/env.sh"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

exec uvicorn backend.app:app --host "$HOST" --port "$PORT"
