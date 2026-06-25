#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

python3 - <<'PYIN'
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path.cwd()
STRICT_GIT = os.environ.get("PILOT_PREFLIGHT_STRICT_GIT", "").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
ALLOWED_DIRTY_STATUS = {
    "?? research_assistant_requirements.md",
    "?? research_assistant_technical_design.md",
}

errors = []
warnings = []
notes = []


def read_required(path):
    file_path = ROOT / path
    if not file_path.exists():
        errors.append(f"missing required file: {path}")
        return ""
    if not file_path.is_file():
        errors.append(f"required path is not a file: {path}")
        return ""
    return file_path.read_text(encoding="utf-8")


def require_file(path):
    file_path = ROOT / path
    if not file_path.exists():
        errors.append(f"missing required file: {path}")
    elif not file_path.is_file():
        errors.append(f"required path is not a file: {path}")


def require_tokens(path, tokens):
    text = read_required(path)
    for token in tokens:
        if token not in text:
            errors.append(f"{path} is missing `{token}`")


def run_git(args):
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


required_files = [
    "README.md",
    "Dockerfile",
    "docker-compose.yml",
    ".env.example",
    "backend/app.py",
    "backend/research/config.py",
    "backend/research/db.py",
    "backend/static/workbench/index.html",
    "backend/static/workbench/app.js",
    "backend/static/workbench/styles.css",
    "scripts/check_remote_safe_suite.sh",
    "scripts/check_pilot_readiness.sh",
    "scripts/check_product_effect_smoke.sh",
    "scripts/check_secret_file_guard.sh",
    "scripts/check_deployment_contracts.sh",
    "scripts/check_handoff_docs.sh",
    "scripts/mcp_http_bridge.py",
    "scripts/smoke_api.py",
    "docs/deployment.md",
    "docs/database_migration_strategy.md",
    "docs/demo_runbook.md",
    "docs/admin_authorization_policy.md",
    "docs/write_audit_retention_policy.md",
]
for path in required_files:
    require_file(path)

require_tokens(
    ".env.example",
    [
        "APP_ENV=",
        "RESEARCH_DB_URL=",
        "PAPER_UPLOAD_DIR=",
        "PAPER_UPLOAD_ALLOWED_EXTENSIONS=",
        "PAPER_UPLOAD_MAX_BYTES=",
        "API_KEY_AUTH_ENABLED=",
        "API_KEY=",
        "WRITE_AUDIT_ENABLED=",
        "AUDIT_ADMIN_EXPORT_ENABLED=",
        "EXTERNAL_LITERATURE_SEARCH_ENABLED=",
    ],
)
require_tokens(
    "docker-compose.yml",
    [
        "APP_ENV: production",
        "API_KEY_AUTH_ENABLED",
        "${API_KEY:?Set API_KEY in .env before starting production compose}",
        "/app/data",
        "research_assistant_data",
        "/health/ready",
    ],
)
require_tokens(
    "Dockerfile",
    [
        "uvicorn backend.app:app",
        "COPY backend ./backend",
        "COPY scripts ./scripts",
        "COPY docs ./docs",
        "mkdir -p /app/data/research /app/data/papers",
    ],
)
require_tokens(
    "docs/deployment.md",
    [
        "Local Deployment Checklist",
        "Local Operational Preflight",
        "Backup And Restore Notes",
        "database_migration_strategy.md",
        "PILOT_PREFLIGHT_STRICT_GIT=true",
        "Do not read or print real `.env` values",
        "Commands that rebuild containers, restart services, change file ownership, or modify databases",
    ],
)
require_tokens(
    "docs/database_migration_strategy.md",
    [
        "No automatic migration execution",
        "Pre-Migration Checklist",
        "Back up `/app/data`",
    ],
)
require_tokens(
    "docs/demo_runbook.md",
    [
        "Demo Decision",
        "Workbench-first",
        "Product-effect scorecard",
    ],
)
require_tokens(
    "README.md",
    [
        "check_pilot_operational_preflight.sh",
        "check_remote_safe_suite.sh",
        "API-key-backed and project-scope-aware pilot access",
    ],
)
require_tokens(
    "scripts/check_remote_safe_suite.sh",
    [
        "bash scripts/check_pilot_operational_preflight.sh",
        "bash scripts/check_pilot_readiness.sh",
    ],
)

inside_worktree = run_git(["rev-parse", "--is-inside-work-tree"])
if inside_worktree.returncode != 0 or inside_worktree.stdout.strip() != "true":
    errors.append("not running inside a git worktree")
else:
    branch = run_git(["branch", "--show-current"])
    branch_name = branch.stdout.strip() or "(detached)"
    head = run_git(["rev-parse", "--short", "HEAD"])
    head_short = head.stdout.strip() or "unknown"
    notes.append(f"git branch: {branch_name}")
    notes.append(f"git head: {head_short}")
    if STRICT_GIT and branch_name != "main":
        errors.append(f"strict git preflight requires branch `main`, found `{branch_name}`")

    origin_main = run_git(["rev-parse", "--verify", "--short", "origin/main"])
    if origin_main.returncode == 0:
        origin_short = origin_main.stdout.strip()
        notes.append(f"origin/main: {origin_short}")
        if STRICT_GIT and origin_short != head_short:
            errors.append("strict git preflight requires HEAD to match origin/main")
    elif STRICT_GIT:
        errors.append("strict git preflight could not resolve origin/main")
    else:
        warnings.append("origin/main is not available for comparison")

    status = run_git(["status", "--short"])
    if status.returncode != 0:
        errors.append("could not read git status")
    else:
        dirty_lines = [line for line in status.stdout.splitlines() if line]
        unexpected_dirty = [line for line in dirty_lines if line not in ALLOWED_DIRTY_STATUS]
        allowed_dirty = [line for line in dirty_lines if line in ALLOWED_DIRTY_STATUS]
        if allowed_dirty:
            notes.append(
                "known untouched untracked handoff docs: " + ", ".join(sorted(allowed_dirty))
            )
        if unexpected_dirty:
            message = "unexpected git status entries: " + "; ".join(unexpected_dirty)
            if STRICT_GIT:
                errors.append(message)
            else:
                warnings.append(message)
        elif not dirty_lines:
            notes.append("git status: clean")

venv_tools = [".venv/bin/python", ".venv/bin/pytest", ".venv/bin/ruff"]
for tool in venv_tools:
    path = ROOT / tool
    if path.exists():
        notes.append(f"tool available: {tool}")
    else:
        warnings.append(f"local development tool not found: {tool}")

if (ROOT / ".env").exists():
    notes.append(".env file exists; contents were not read")
else:
    warnings.append(".env file not found; create it from .env.example before local deployment")

if errors:
    print("Local operational preflight failed:")
    for error in errors:
        print(f"- {error}")
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"- {warning}")
    sys.exit(1)

print("Local operational preflight passed.")
if warnings:
    print("Warnings:")
    for warning in warnings:
        print(f"- {warning}")
if notes:
    print("Notes:")
    for note in notes:
        print(f"- {note}")
if not STRICT_GIT:
    print("Set PILOT_PREFLIGHT_STRICT_GIT=true before sharing a packaged local release.")
PYIN
