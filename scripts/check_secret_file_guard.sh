#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

python3 - <<'PYIN'
from pathlib import Path
import re
import subprocess
import sys

allowed_tracked = {".env.example"}
tracked = subprocess.check_output(["git", "ls-files"], text=True).splitlines()
violations = []
for path in tracked:
    name = Path(path).name.lower()
    if path in allowed_tracked:
        continue
    if name == ".env" or name.startswith(".env."):
        violations.append(path)
        continue
    if re.search(r"\.(pem|key|p12|pfx)$", name):
        violations.append(path)
        continue
    if re.search(r"(token|cookie|credential|secret)", name):
        violations.append(path)

required_gitignore = [
    ".env",
    ".env.*",
    "!.env.example",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
]
gitignore_lines = set(Path(".gitignore").read_text(encoding="utf-8").splitlines())
missing_gitignore = [line for line in required_gitignore if line not in gitignore_lines]

if violations or missing_gitignore:
    if violations:
        print("Sensitive-looking tracked filenames are not allowed:")
        for path in violations:
            print(f"- {path}")
    if missing_gitignore:
        print(".gitignore is missing sensitive-file patterns:")
        for line in missing_gitignore:
            print(f"- {line}")
    sys.exit(1)

print("Secret file guard passed.")
PYIN
