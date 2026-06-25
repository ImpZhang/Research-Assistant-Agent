#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed or not on PATH."
  exit 1
fi

printf 'This will run docker compose down -v --remove-orphans for this project. Continue? [y/N] '
read -r answer
case "$answer" in
  y|Y|yes|YES)
    ;;
  *)
    echo "Canceled."
    exit 0
    ;;
esac

COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-research_assistant_agent_local}" docker compose down -v --remove-orphans
echo "Removed project containers and Docker volumes for $COMPOSE_PROJECT_NAME."
