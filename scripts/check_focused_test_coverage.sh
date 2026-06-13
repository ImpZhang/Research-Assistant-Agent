#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

python3 - <<'PYIN'
from pathlib import Path
import ast
import shlex
import sys

pytest_tokens = set()
for script_path in sorted(Path("scripts").glob("check_*.sh")):
    lines = script_path.read_text(encoding="utf-8").splitlines()
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        starts_pytest = (
            stripped.startswith(".venv/bin/pytest")
            or stripped.startswith("uv run pytest")
            or stripped.startswith("pytest ")
        )
        if not starts_pytest:
            index += 1
            continue
        block = [stripped.rstrip("\\").strip()]
        while stripped.endswith("\\") and index + 1 < len(lines):
            index += 1
            stripped = lines[index].strip()
            block.append(stripped.rstrip("\\").strip())
        try:
            tokens = shlex.split(" ".join(block))
        except ValueError:
            tokens = " ".join(block).split()
        pytest_tokens.update(tokens)
        index += 1

missing = []
for test_path in sorted(Path("tests").glob("test*.py")):
    rel_path = test_path.as_posix()
    tree = ast.parse(test_path.read_text(encoding="utf-8"), filename=rel_path)
    test_names = sorted(
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    file_targeted = rel_path in pytest_tokens
    for test_name in test_names:
        if file_targeted or f"{rel_path}::{test_name}" in pytest_tokens:
            continue
        missing.append(f"{rel_path}::{test_name}")

if missing:
    print("Missing focused check coverage for pytest targets:")
    for target in missing:
        print(f"- {target}")
    sys.exit(1)

print("All pytest tests are covered by focused check scripts.")
PYIN
