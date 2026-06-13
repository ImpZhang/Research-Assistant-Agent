#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

python3 - <<'PYIN'
from pathlib import Path
import sys

readme = Path("README.md").read_text(encoding="utf-8")
errors = []
for script_path in sorted(Path("scripts").glob("check_*.sh")):
    name = script_path.name
    text = script_path.read_text(encoding="utf-8")
    if name not in readme:
        errors.append(f"README.md does not list `{name}`")
    if not text.startswith("#!/usr/bin/env bash\n"):
        errors.append(f"{script_path} must start with the bash shebang")
    if "set -euo pipefail" not in text:
        errors.append(f"{script_path} must enable `set -euo pipefail`")
    if 'cd "$(dirname "${BASH_SOURCE[0]}")/.."' not in text:
        errors.append(f"{script_path} must cd to the repository root")

if errors:
    print("Check script catalog violations:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("Check script catalog is synchronized.")
PYIN
