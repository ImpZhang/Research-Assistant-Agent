#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

.venv/bin/ruff check scripts/build_local_backup_manifest.py tests/test_local_backup_manifest.py
.venv/bin/ruff format --check scripts/build_local_backup_manifest.py tests/test_local_backup_manifest.py
.venv/bin/pytest -q tests/test_local_backup_manifest.py

python3 - <<'PYIN'
from pathlib import Path
import sys

errors = []


def require_tokens(path, tokens):
    text = Path(path).read_text(encoding="utf-8")
    for token in tokens:
        if token not in text:
            errors.append(f"{path} is missing `{token}`")


require_tokens(
    "docker-compose.yml",
    [
        "research_assistant_data",
        "/app/data",
        "sqlite:////app/data/research/research_assistant.db",
        "PAPER_UPLOAD_DIR: /app/data/papers",
    ],
)
require_tokens(
    "Dockerfile",
    [
        "mkdir -p /app/data/research /app/data/papers",
    ],
)
require_tokens(
    "docs/deployment.md",
    [
        "Backup And Restore Notes",
        "python3 scripts/build_local_backup_manifest.py",
        "The manifest is read-only and aggregate-only",
        "Back up this data before rebuilds, host moves, database migrations, or destructive maintenance.",
        "Keep `.env`, API keys, cookies, private keys, and provider credentials in a separate secret manager or operator vault.",
        "Cold backup is the preferred local path",
        "Restore should never write over a live service volume.",
        "Prefer restoring into a new empty target volume",
        "After restore or volume swap, verify `/health/ready`, authenticated `/research/status`, the Workbench launch panel, and a known project bundle or paper record",
        "Commands that rebuild containers, restart services, change file ownership, or modify databases should be run only after explicit operator approval.",
    ],
)
require_tokens(
    "docs/database_migration_strategy.md",
    [
        "Back up `/app/data` before any deployment that changes SQLAlchemy models or database-related settings.",
        "Keep `init_db()` as table creation only; do not hide data migrations inside application startup.",
        "Do not run ad hoc SQL against a user's local database without an operator-reviewed backup and rollback note.",
        "Restore-from-backup is often the safest rollback path.",
        "No automatic migration execution",
    ],
)

if errors:
    print("Backup/restore contract violations:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("Backup/restore contracts are valid.")
PYIN
