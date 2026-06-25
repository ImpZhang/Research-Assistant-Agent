#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

find . -type d \( \
  -name '__pycache__' -o \
  -name '.pytest_cache' -o \
  -name '.mypy_cache' -o \
  -name '.ruff_cache' -o \
  -name '.ipynb_checkpoints' \
\) -prune -exec rm -rf {} +

find . -type f \( -name '*.pyc' -o -name '*.pyo' -o -name '.coverage' -o -name 'coverage.xml' \) -delete

rm -rf \
  .venv \
  .conda \
  node_modules \
  htmlcov \
  dist \
  build \
  *.egg-info \
  .cache \
  outputs/* \
  logs/*

mkdir -p .cache data models outputs logs .docker
echo "Removed rebuildable dependencies, caches, logs, and generated outputs."
