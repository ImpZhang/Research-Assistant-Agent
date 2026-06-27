#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

python3 - <<'PYIN'
from pathlib import Path
import re
import sys

required_skills = [
    "paper-ingestion",
    "hybrid-context-search",
    "literature-to-ideas",
    "sota-review",
    "benchmark-evaluation",
    "advisor-action-session",
]
required_sections = [
    "## Purpose",
    "## Backing APIs And Tools",
    "## Workflow",
    "## Safety Boundaries",
    "## Failure Handling",
    "## Verification",
]

errors: list[str] = []
for skill_name in required_skills:
    path = Path("skills") / skill_name / "SKILL.md"
    if not path.exists():
        errors.append(f"{path} is missing")
        continue
    text = path.read_text(encoding="utf-8")
    match = re.match(
        r"^---\nname: ([a-z0-9-]+)\ndescription: (.+?)\n---\n",
        text,
        re.DOTALL,
    )
    if not match:
        errors.append(f"{path} has invalid frontmatter")
        continue
    name, description = match.groups()
    if name != skill_name:
        errors.append(f"{path} frontmatter name `{name}` must match folder `{skill_name}`")
    if len(description.strip()) < 80:
        errors.append(f"{path} description is too short to trigger reliably")
    for section in required_sections:
        if section not in text:
            errors.append(f"{path} is missing `{section}`")
    if "TODO" in text or "TBD" in text:
        errors.append(f"{path} contains unfinished placeholder text")
    if "```" in text and text.count("```") % 2 != 0:
        errors.append(f"{path} has an unclosed fenced code block")

registry = Path("docs/project_skill_registry.md")
if not registry.exists():
    errors.append(f"{registry} is missing")
else:
    registry_text = registry.read_text(encoding="utf-8")
    for skill_name in required_skills:
        expected = f"skills/{skill_name}/SKILL.md"
        if expected not in registry_text:
            errors.append(f"{registry} does not list `{expected}`")

if errors:
    print("Project skill registry violations:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("Project skill registry is valid.")
PYIN
