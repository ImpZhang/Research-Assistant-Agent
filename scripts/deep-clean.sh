#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

printf 'This will remove local datasets, uploaded papers, SQLite data, model weights, and outputs under:\n  %s\nContinue? [y/N] ' "$PROJECT_ROOT"
read -r answer
case "$answer" in
  y|Y|yes|YES)
    ;;
  *)
    echo "Canceled."
    exit 0
    ;;
esac

"$PROJECT_ROOT/scripts/clean.sh"
rm -rf "$PROJECT_ROOT/data" "$PROJECT_ROOT/models" "$PROJECT_ROOT/outputs"
mkdir -p "$PROJECT_ROOT/data" "$PROJECT_ROOT/models" "$PROJECT_ROOT/outputs" "$PROJECT_ROOT/logs" "$PROJECT_ROOT/.docker"
echo "Removed project-local data, models, and generated outputs."
