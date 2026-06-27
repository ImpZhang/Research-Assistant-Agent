#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


FILE_REQUIREMENTS = [
    {
        "name": "dockerfile_runtime",
        "path": "Dockerfile",
        "tokens": [
            "FROM python:3.12-slim",
            "WORKDIR /app",
            "COPY pyproject.toml README.md ./",
            "python -m pip install --no-cache-dir .",
            "COPY backend ./backend",
            "COPY scripts ./scripts",
            "COPY docs ./docs",
            "mkdir -p /app/data/research /app/data/papers",
            "EXPOSE 8000",
            "uvicorn backend.app:app",
        ],
    },
    {
        "name": "compose_single_user_contract",
        "path": "docker-compose.yml",
        "tokens": [
            "name: research-assistant-agent-local",
            "research-assistant-agent:",
            "env_file:",
            "- .env",
            "APP_ENV: production",
            "APP_COMMIT_SHA: ${APP_COMMIT_SHA:-local}",
            "RESEARCH_DB_URL: sqlite:////app/data/research/research_assistant.db",
            "PAPER_UPLOAD_DIR: /app/data/papers",
            'API_KEY_AUTH_ENABLED: "true"',
            "API_KEY: ${API_KEY:?Set API_KEY in .env before starting production compose}",
            "API_KEY_HEADER_NAME: X-Research-Assistant-Key",
            '"8000:8000"',
            "research_assistant_data:/app/data",
            "healthcheck:",
            "/health/ready",
            "volumes:",
            "research_assistant_data:",
        ],
    },
    {
        "name": "dockerignore_secret_and_artifact_boundary",
        "path": ".dockerignore",
        "tokens": [
            ".git",
            ".venv",
            "data",
            "logs",
            ".env",
            ".env.*",
            "!.env.example",
            "dist",
            "build",
        ],
    },
    {
        "name": "env_template_compose_placeholders",
        "path": ".env.example",
        "tokens": [
            "APP_ENV=",
            "APP_COMMIT_SHA=local",
            "API_KEY_AUTH_ENABLED=",
            "API_KEY=",
            "RESEARCH_DB_URL=",
            "PAPER_UPLOAD_DIR=",
            "MAIN_MODEL=",
            "EMBEDDER=",
            "RERANK_MODEL=",
        ],
    },
    {
        "name": "deployment_docs_operator_boundaries",
        "path": "docs/deployment.md",
        "tokens": [
            "Single-container Docker remains optional for one operator.",
            "docker compose up --build",
            "only after explicit operator approval",
            "The compose file mounts a named volume at `/app/data`",
            "API_KEY_AUTH_ENABLED=true",
            "Keep `.env`, API keys, cookies, private keys, and provider credentials",
            "Restore should never write over a live service volume.",
        ],
    },
]


def main() -> int:
    args = parse_args()
    root = args.project_root.resolve()
    report = build_report(root)

    if args.write_json:
        output_path = resolve_project_path(root, args.write_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        report["written_to"] = relative_path(output_path, root)

    if args.write_markdown:
        output_path = resolve_project_path(root, args.write_markdown)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(render_markdown(report), encoding="utf-8")
        report["markdown_written_to"] = relative_path(output_path, root)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    elif args.markdown:
        print(render_markdown(report), end="")
    else:
        print_human_report(report)
    return 0 if report["ok"] else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Check the optional single-user Docker deployment contract without "
            "starting Docker, reading .env, installing dependencies, or touching data."
        )
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--markdown", action="store_true", help="Print a Markdown report.")
    parser.add_argument("--write-json", type=Path, default=None)
    parser.add_argument("--write-markdown", type=Path, default=None)
    return parser.parse_args()


def build_report(root: Path) -> dict[str, Any]:
    checks = [run_file_requirement(root, requirement) for requirement in FILE_REQUIREMENTS]
    failures = [
        {
            "name": check["name"],
            "path": check["path"],
            "missing_tokens": check["missing_tokens"],
            "missing_file": check["missing_file"],
        }
        for check in checks
        if not check["ok"]
    ]
    return {
        "ok": not failures,
        "project_root": str(root),
        "check_count": len(checks),
        "checks": checks,
        "failures": failures,
        "notes": [
            "This is a static contract check; it does not run Docker or start services.",
            "It does not read .env values, API keys, cookies, private keys, or provider credentials.",
            "Docker compose startup, rebuilds, volume operations, and service restarts require explicit operator approval.",
        ],
    }


def run_file_requirement(root: Path, requirement: dict[str, Any]) -> dict[str, Any]:
    path = root / requirement["path"]
    if not path.exists():
        return {
            "name": requirement["name"],
            "path": requirement["path"],
            "ok": False,
            "missing_file": True,
            "missing_tokens": list(requirement["tokens"]),
        }
    text = path.read_text(encoding="utf-8")
    missing = [token for token in requirement["tokens"] if token not in text]
    return {
        "name": requirement["name"],
        "path": requirement["path"],
        "ok": not missing,
        "missing_file": False,
        "missing_tokens": missing,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Single User Docker Deployment Check",
        "",
        "## Summary",
        "",
        f"- OK: {report['ok']}",
        f"- Checks: {report['check_count']}",
        f"- Failures: {len(report['failures'])}",
        "",
        "## Checks",
        "",
    ]
    for check in report["checks"]:
        status = "pass" if check["ok"] else "fail"
        lines.append(f"- {check['name']} ({check['path']}): {status}")
    lines.extend(["", "## Failures", ""])
    if report["failures"]:
        for failure in report["failures"]:
            lines.append(
                f"- {failure['name']} ({failure['path']}): "
                f"missing_file={failure['missing_file']} "
                f"missing_tokens={len(failure['missing_tokens'])}"
            )
    else:
        lines.append("- None")
    lines.extend(["", "## Notes", ""])
    for note in report["notes"]:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def print_human_report(report: dict[str, Any]) -> None:
    print("Single-user Docker deployment check")
    print(f"Project root: {report['project_root']}")
    print(f"OK: {'yes' if report['ok'] else 'no'}")
    print(f"Checks: {report['check_count']}")
    if report["failures"]:
        print("Failures:")
        for failure in report["failures"]:
            print(
                f"- {failure['name']} ({failure['path']}): "
                f"{len(failure['missing_tokens'])} missing tokens"
            )
    print("Notes:")
    for note in report["notes"]:
        print(f"- {note}")


def resolve_project_path(root: Path, value: Path) -> Path:
    resolved = value.resolve() if value.is_absolute() else (root / value).resolve()
    if not is_relative_to(resolved, root):
        raise SystemExit(f"output path must stay inside project root: {value}")
    return resolved


def relative_path(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except OSError as exc:
        print(f"Single-user Docker deployment check failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
