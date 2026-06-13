#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

python3 - <<'PYIN'
from pathlib import Path
import subprocess
import sys

tracked = subprocess.check_output(["git", "ls-files"], text=True).splitlines()
forbidden_suffixes = (".pyc", ".pyo", ".pyd")
forbidden_parts = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "htmlcov",
}
forbidden_egg_info_suffix = ".egg-info"
violations = []
for path in tracked:
    parts = Path(path).parts
    name = Path(path).name
    if name.endswith(forbidden_suffixes):
        violations.append(path)
        continue
    if any(part in forbidden_parts for part in parts):
        violations.append(path)
        continue
    if any(part.endswith(forbidden_egg_info_suffix) for part in parts):
        violations.append(path)

required_gitignore = [
    "__pycache__/",
    "*.py[cod]",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    ".venv/",
    "venv/",
    "node_modules/",
    "dist/",
    "build/",
    "*.egg-info/",
    ".coverage",
    "coverage.xml",
    "htmlcov/",
    ".DS_Store",
    "Thumbs.db",
]
gitignore_lines = set(Path(".gitignore").read_text(encoding="utf-8").splitlines())
missing_gitignore = [line for line in required_gitignore if line not in gitignore_lines]

if violations or missing_gitignore:
    if violations:
        print("Generated artifacts must not be tracked:")
        for path in violations:
            print(f"- {path}")
    if missing_gitignore:
        print(".gitignore is missing generated-artifact patterns:")
        for line in missing_gitignore:
            print(f"- {line}")
    sys.exit(1)

print("Generated file guard passed.")
PYIN
