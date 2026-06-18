#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

python3 - <<'PYIN'
from pathlib import Path
import sys

checks = {
    "AGENTS.md": [
        "/home/zhangwz/Research-Assistant-Agent",
        "source-of-truth",
        "git status --short",
        ".env",
        "git reset",
        ".venv",
    ],
    "README.md": [
        "AGENTS.md",
        "TODO.md",
        "codex_handoff/03_TODO.md",
        "docs/progress_log.md",
        "check_handoff_docs.sh",
    ],
    "TODO.md": [
        "P0 - Remote-First Safety",
        "P1 - Pilot Readiness Without Service Changes",
        "check_handoff_docs.sh",
        "P4 - Needs Explicit Operator Approval",
    ],
    "codex_handoff/03_TODO.md": [
        "check_handoff_docs.sh",
        "Run a remote smoke workflow against the current main branch when the operator approves service startup",
    ],
    "docs/progress_log.md": [
        "## 2026-06-13",
        "Verification completed",
    ],
    "docs/representative_paper_review.md": [
        "Representative Paper Human Review Protocol",
        "Workbench-first",
        "Exit Criteria",
        "PRODUCT_EFFECT_SMOKE_PAPER_FILE",
    ],
}

errors = []
for file_name, required_terms in checks.items():
    path = Path(file_name)
    if not path.exists():
        errors.append(f"{file_name} is missing")
        continue
    text = path.read_text(encoding="utf-8")
    for term in required_terms:
        if term not in text:
            errors.append(f"{file_name} is missing `{term}`")

if errors:
    print("Handoff document consistency violations:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("Handoff documents are synchronized.")
PYIN
