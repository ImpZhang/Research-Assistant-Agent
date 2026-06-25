#!/usr/bin/env bash
set -euo pipefail

if [ -n "${BASH_SOURCE:-}" ]; then
  ENV_SCRIPT="${BASH_SOURCE:-}"
elif [ -n "${ZSH_VERSION:-}" ]; then
  ENV_SCRIPT="${(%):-%x}"
else
  ENV_SCRIPT="$0"
fi

case "$ENV_SCRIPT" in
  */*) PROJECT_ROOT="$(cd "$(dirname "$ENV_SCRIPT")/.." && pwd)" ;;
  *) PROJECT_ROOT="$(pwd)" ;;
esac
PROJECT_SLUG="$(basename "$PROJECT_ROOT" | tr '[:upper:]' '[:lower:]' | tr -c '[:alnum:]_-' '-')"

export PROJECT_ROOT
export XDG_CACHE_HOME="$PROJECT_ROOT/.cache"
export PIP_CACHE_DIR="$PROJECT_ROOT/.cache/pip"
export UV_CACHE_DIR="$PROJECT_ROOT/.cache/uv"
export POETRY_CACHE_DIR="$PROJECT_ROOT/.cache/pypoetry"
export PDM_CACHE_DIR="$PROJECT_ROOT/.cache/pdm"
export PIPENV_CACHE_DIR="$PROJECT_ROOT/.cache/pipenv"
export CONDA_PKGS_DIRS="$PROJECT_ROOT/.cache/conda/pkgs"

export HF_HOME="$PROJECT_ROOT/.cache/huggingface"
export HF_HUB_CACHE="$HF_HOME/hub"
export HF_DATASETS_CACHE="$HF_HOME/datasets"
export TORCH_HOME="$PROJECT_ROOT/.cache/torch"
export MPLCONFIGDIR="$PROJECT_ROOT/.cache/matplotlib"

export npm_config_cache="$PROJECT_ROOT/.cache/npm"
export YARN_CACHE_FOLDER="$PROJECT_ROOT/.cache/yarn"
export PNPM_HOME="$PROJECT_ROOT/.cache/pnpm-home"
export npm_config_store_dir="$PROJECT_ROOT/.cache/pnpm-store"
export COREPACK_HOME="$PROJECT_ROOT/.cache/corepack"
export BUN_INSTALL="$PROJECT_ROOT/.cache/bun"
export DENO_DIR="$PROJECT_ROOT/.cache/deno"

export CARGO_HOME="$PROJECT_ROOT/.cache/cargo"
export CARGO_TARGET_DIR="$PROJECT_ROOT/.cache/cargo-target"
export GOPATH="$PROJECT_ROOT/.cache/go"
export GOMODCACHE="$PROJECT_ROOT/.cache/go/pkg/mod"
export GOCACHE="$PROJECT_ROOT/.cache/go-build"
export GRADLE_USER_HOME="$PROJECT_ROOT/.cache/gradle"
export MAVEN_OPTS="-Dmaven.repo.local=$PROJECT_ROOT/.cache/maven/repository ${MAVEN_OPTS:-}"
export RENV_PATHS_CACHE="$PROJECT_ROOT/.cache/renv"
export JULIA_DEPOT_PATH="$PROJECT_ROOT/.cache/julia"

export JUPYTER_CONFIG_DIR="$PROJECT_ROOT/.cache/jupyter/config"
export JUPYTER_DATA_DIR="$PROJECT_ROOT/.cache/jupyter/data"
export JUPYTER_RUNTIME_DIR="$PROJECT_ROOT/.cache/jupyter/runtime"

export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-research_assistant_agent_local}"
export APP_ENV="${APP_ENV:-development}"
export APP_COMMIT_SHA="${APP_COMMIT_SHA:-$(git -C "$PROJECT_ROOT" rev-parse --short HEAD 2>/dev/null || printf local)}"
export RESEARCH_DB_URL="${RESEARCH_DB_URL:-sqlite:///$PROJECT_ROOT/data/research/research_assistant.db}"
export PAPER_UPLOAD_DIR="${PAPER_UPLOAD_DIR:-$PROJECT_ROOT/data/papers}"
export WRITE_AUDIT_DIR="${WRITE_AUDIT_DIR:-$PROJECT_ROOT/data/audit}"
export PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"

mkdir -p \
  "$XDG_CACHE_HOME" \
  "$PIP_CACHE_DIR" \
  "$UV_CACHE_DIR" \
  "$HF_HOME" \
  "$TORCH_HOME" \
  "$MPLCONFIGDIR" \
  "$PROJECT_ROOT/data" \
  "$PROJECT_ROOT/models" \
  "$PROJECT_ROOT/outputs" \
  "$PROJECT_ROOT/logs" \
  "$PROJECT_ROOT/.docker"

if [ -d "$PROJECT_ROOT/.venv" ]; then
  # shellcheck disable=SC1091
  source "$PROJECT_ROOT/.venv/bin/activate"
elif [ -d "$PROJECT_ROOT/.conda" ]; then
  export CONDA_PREFIX="$PROJECT_ROOT/.conda"
  export PATH="$CONDA_PREFIX/bin:$PATH"
fi
