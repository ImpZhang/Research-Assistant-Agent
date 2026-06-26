#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

python3 - <<'PYIN'
from pathlib import Path
import subprocess
import sys

ROOT = Path.cwd()

errors: list[str] = []
warnings: list[str] = []
notes: list[str] = []


def read_required(path: str) -> str:
    file_path = ROOT / path
    if not file_path.exists():
        errors.append(f"missing required file: {path}")
        return ""
    if not file_path.is_file():
        errors.append(f"required path is not a file: {path}")
        return ""
    return file_path.read_text(encoding="utf-8")


def require_file(path: str) -> None:
    file_path = ROOT / path
    if not file_path.exists():
        errors.append(f"missing required file: {path}")
    elif not file_path.is_file():
        errors.append(f"required path is not a file: {path}")


def require_tokens(path: str, tokens: list[str]) -> None:
    text = read_required(path)
    for token in tokens:
        if token not in text:
            errors.append(f"{path} is missing `{token}`")


required_files = [
    ".env.example",
    ".gitignore",
    "AGENTS.md",
    "README.md",
    "TODO.md",
    "pyproject.toml",
    "uv.lock",
    "backend/app.py",
    "backend/research/config.py",
    "backend/research/db.py",
    "backend/static/workbench/index.html",
    "backend/static/workbench/app.js",
    "backend/static/workbench/styles.css",
    "configs/benchmark_profiles.example.json",
    "docs/deployment.md",
    "docs/documentation_index.md",
    "docs/local_agent_distribution.md",
    "docs/local_isolation.md",
    "docs/model_provider_strategy.md",
    "scripts/env.sh",
    "scripts/setup-local.sh",
    "scripts/run-local.sh",
    "scripts/build_local_backup_manifest.py",
    "scripts/clean.sh",
    "scripts/deep-clean.sh",
    "scripts/docker-clean.sh",
    "scripts/check_model_provider_config.py",
]
for path in required_files:
    require_file(path)

require_tokens(
    ".gitignore",
    [
        ".env",
        ".env.*",
        "!.env.example",
        ".venv/",
        ".cache/",
        "data/",
        "models/",
        "outputs/",
        "logs/",
        ".docker/",
        "configs/benchmark_profiles.json",
    ],
)
require_tokens(
    ".env.example",
    [
        "MAIN_MODEL=",
        "MAIN_BASE_URL=",
        "MAIN_API_KEY=",
        "EXTRACTION_MODEL=",
        "EXTRACTION_BASE_URL=",
        "EXTRACTION_API_KEY=",
        "JUDGE_MODEL=",
        "JUDGE_BASE_URL=",
        "JUDGE_API_KEY=",
        "EMBEDDER=",
        "EMBEDDER_BASE_URL=",
        "EMBEDDER_API_KEY=",
        "RETRIEVAL_EMBEDDING_PROVIDER=auto",
        "RERANK_MODEL=",
        "RERANK_BINDING_HOST=",
        "RERANK_API_KEY=",
        "RETRIEVAL_RERANK_PROVIDER=auto",
        "RESEARCH_DB_URL=sqlite:///./data/research/research_assistant.db",
        "PAPER_UPLOAD_DIR=./data/papers",
        "BENCHMARK_RUNNER_OUTPUT_DIR=./outputs/benchmark-runs",
        "BENCHMARK_PROFILE_MANIFEST_PATH=./configs/benchmark_profiles.json",
        "API_KEY_AUTH_ENABLED=false",
        "WRITE_AUDIT_DIR=./data/audit",
    ],
)
require_tokens(
    "scripts/env.sh",
    [
        'export PROJECT_ROOT',
        'export XDG_CACHE_HOME="$PROJECT_ROOT/.cache"',
        'export PIP_CACHE_DIR="$PROJECT_ROOT/.cache/pip"',
        'export UV_CACHE_DIR="$PROJECT_ROOT/.cache/uv"',
        'export HF_HOME="$PROJECT_ROOT/.cache/huggingface"',
        'export TORCH_HOME="$PROJECT_ROOT/.cache/torch"',
        'export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-research_assistant_agent_local}"',
        'export RESEARCH_DB_URL="${RESEARCH_DB_URL:-sqlite:///$PROJECT_ROOT/data/research/research_assistant.db}"',
        'export PAPER_UPLOAD_DIR="${PAPER_UPLOAD_DIR:-$PROJECT_ROOT/data/papers}"',
        'export WRITE_AUDIT_DIR="${WRITE_AUDIT_DIR:-$PROJECT_ROOT/data/audit}"',
        '"$PROJECT_ROOT/data"',
        '"$PROJECT_ROOT/models"',
        '"$PROJECT_ROOT/outputs"',
        '"$PROJECT_ROOT/logs"',
        '"$PROJECT_ROOT/.docker"',
    ],
)
require_tokens(
    "scripts/setup-local.sh",
    [
        'PYTHON_BIN="${PYTHON_BIN:-python3}"',
        "Python >= 3.12 is required",
        "mkdir -p .cache data models outputs logs .docker",
        'source "$PROJECT_ROOT/scripts/env.sh"',
        "uv sync --frozen --extra dev",
    ],
)
require_tokens(
    "scripts/run-local.sh",
    [
        'source "$PROJECT_ROOT/scripts/env.sh"',
        'HOST="${HOST:-127.0.0.1}"',
        'PORT="${PORT:-8000}"',
        "uvicorn backend.app:app",
    ],
)
require_tokens(
    "docs/local_agent_distribution.md",
    [
        "personal, local-deployable",
        "Clone-To-Run Flow",
        "local `.env`",
        "Explicitly Out Of Scope For Now",
        "Multi-user account management",
    ],
)
require_tokens(
    "docs/local_isolation.md",
    [
        ".venv/",
        ".cache/",
        "data/",
        "models/",
        "outputs/",
        "logs/",
        "scripts/clean.sh",
        "scripts/deep-clean.sh",
    ],
)
require_tokens(
    "README.md",
    [
        "Current Distribution Target",
        "docs/local_agent_distribution.md",
        "scripts/check_local_agent_readiness.sh",
        "scripts/build_local_backup_manifest.py",
        "scripts/check_model_provider_config.py",
        "./scripts/setup-local.sh",
        "./scripts/run-local.sh",
    ],
)

env_example = read_required(".env.example")
for key_name in [
    "MAIN_API_KEY",
    "EXTRACTION_API_KEY",
    "JUDGE_API_KEY",
    "EMBEDDER_API_KEY",
    "RERANK_API_KEY",
    "API_KEY",
    "AUDIT_ADMIN_KEY",
]:
    if f"{key_name}=\n" not in env_example and f"{key_name}=\r\n" not in env_example:
        errors.append(f".env.example must keep `{key_name}` empty")

for directory in [".cache", "data", "models", "outputs", "logs", ".docker"]:
    path = ROOT / directory
    if path.exists() and path.is_dir():
        notes.append(f"local artifact directory exists: {directory}/")
    else:
        warnings.append(f"local artifact directory not found yet: {directory}/")

venv_python = ROOT / ".venv" / "bin" / "python"
if venv_python.exists():
    result = subprocess.run(
        [
            str(venv_python),
            "-c",
            "import sys; print('.'.join(map(str, sys.version_info[:3]))); raise SystemExit(0 if sys.version_info >= (3, 12) else 1)",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    version = result.stdout.strip() or "unknown"
    if result.returncode == 0:
        notes.append(f"local virtualenv python is ready: {version}")
    else:
        errors.append(f".venv python must be >= 3.12, found {version}")
else:
    warnings.append(".venv is not present; run ./scripts/setup-local.sh before starting the app")

if (ROOT / ".env").exists():
    notes.append(".env exists; contents were not read")
else:
    warnings.append(".env is not present; copy .env.example to .env and fill local model keys")

if (ROOT / "configs" / "benchmark_profiles.json").exists():
    notes.append("local benchmark profile override exists; contents were not read")
else:
    notes.append("local benchmark profile override is absent; built-in profiles remain available")

if errors:
    print("Local agent readiness failed:")
    for error in errors:
        print(f"- {error}")
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"- {warning}")
    sys.exit(1)

print("Local agent readiness passed.")
if warnings:
    print("Warnings:")
    for warning in warnings:
        print(f"- {warning}")
if notes:
    print("Notes:")
    for note in notes:
        print(f"- {note}")
PYIN
