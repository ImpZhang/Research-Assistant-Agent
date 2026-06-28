#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.research import models  # noqa: E402,F401
from backend.research.db import Base  # noqa: E402


DEFAULT_BASELINE = "migrations/baseline_schema.json"


def main() -> int:
    args = parse_args()
    root = args.project_root.resolve()
    baseline_path = resolve_project_path(root, args.baseline)
    expected = json.loads(baseline_path.read_text(encoding="utf-8"))
    current_payload = current_schema_payload()
    current_hash = schema_hash(current_payload)
    current_tables = [table["table"] for table in current_payload]
    errors = []
    if expected.get("schema_hash") != current_hash:
        errors.append("SQLAlchemy metadata hash differs from migration baseline.")
    if int(expected.get("table_count") or 0) != len(current_tables):
        errors.append("SQLAlchemy table count differs from migration baseline.")
    if expected.get("tables") != current_tables:
        errors.append("SQLAlchemy table list differs from migration baseline.")

    report = {
        "ok": not errors,
        "baseline": relative_path(baseline_path, root),
        "expected_revision": expected.get("revision", ""),
        "expected_schema_hash": expected.get("schema_hash", ""),
        "current_schema_hash": current_hash,
        "expected_table_count": expected.get("table_count", 0),
        "current_table_count": len(current_tables),
        "errors": errors,
        "message": (
            "Migration baseline matches current SQLAlchemy metadata."
            if not errors
            else "Migration baseline drift detected."
        ),
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        print(report["message"])
        for error in errors:
            print(f"- {error}")
    return 0 if report["ok"] else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check SQLAlchemy metadata against the committed migration baseline."
    )
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--baseline", default=DEFAULT_BASELINE)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def current_schema_payload() -> list[dict[str, Any]]:
    payload = []
    for table in sorted(Base.metadata.sorted_tables, key=lambda item: item.name):
        columns = []
        for column in table.columns:
            columns.append(
                {
                    "name": column.name,
                    "type": str(column.type),
                    "nullable": bool(column.nullable),
                    "primary_key": bool(column.primary_key),
                    "foreign_keys": sorted(
                        str(foreign_key.column) for foreign_key in column.foreign_keys
                    ),
                }
            )
        payload.append({"table": table.name, "columns": columns})
    return payload


def schema_hash(payload: list[dict[str, Any]]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def resolve_project_path(root: Path, value: str | Path) -> Path:
    path = Path(value)
    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise SystemExit(f"path must stay inside project root: {path}") from exc
    return resolved


def relative_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
