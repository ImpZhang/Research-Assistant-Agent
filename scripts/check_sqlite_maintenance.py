#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys
from typing import Any


DEFAULT_DATABASE_URL = "sqlite:///./data/research/research_assistant.db"
IMPORTANT_TABLES = [
    "research_profiles",
    "papers",
    "chunks",
    "evidences",
    "paper_cards",
    "research_gaps",
    "ideas",
    "reviews",
    "novelty_checks",
    "experiment_plans",
    "experiment_runs",
    "research_nodes",
    "research_edges",
    "research_embeddings",
    "agent_runs",
    "tool_call_records",
    "replay_cases",
    "jobs",
]


def main() -> int:
    args = parse_args()
    root = args.project_root.resolve()
    database_url = args.database_url or os.getenv("RESEARCH_DB_URL", DEFAULT_DATABASE_URL)
    report = build_report(
        root=root,
        database_url=database_url,
        run_quick_check=not args.skip_quick_check,
        allow_outside_project=args.allow_outside_project,
    )

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
            "Build a read-only SQLite maintenance report for the local research "
            "database. It reports aggregate table counts, vector-index counts, "
            "sidecar sizes, and maintenance recommendations without reading .env "
            "files or private paper content."
        )
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--database-url",
        default="",
        help=(
            "SQLite database URL to inspect. Defaults to RESEARCH_DB_URL from the "
            "current environment, then the local project default."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--markdown", action="store_true", help="Print a Markdown report.")
    parser.add_argument(
        "--write-json",
        type=Path,
        default=None,
        help="Write the report to a project-local JSON path.",
    )
    parser.add_argument(
        "--write-markdown",
        type=Path,
        default=None,
        help="Write the report to a project-local Markdown path.",
    )
    parser.add_argument(
        "--skip-quick-check",
        action="store_true",
        help="Skip SQLite PRAGMA quick_check.",
    )
    parser.add_argument(
        "--allow-outside-project",
        action="store_true",
        help="Allow read-only inspection of a SQLite file outside the project root.",
    )
    return parser.parse_args()


def build_report(
    *,
    root: Path,
    database_url: str,
    run_quick_check: bool,
    allow_outside_project: bool,
) -> dict[str, Any]:
    report = empty_report(root)
    parsed = parse_sqlite_path(database_url, root)
    report["database"].update(parsed)

    if parsed["status"] in {"unsupported", "memory"}:
        add_database_recommendations(report)
        return report

    database_path = parsed["absolute_path"]
    if not parsed["inside_project_root"] and not allow_outside_project:
        report["database"]["status"] = "outside_project_root"
        report["recommendations"].append(
            "Database URL points outside the project root; move it under data/research "
            "or rerun with --allow-outside-project only after confirming the data is safe."
        )
        return report

    path = Path(database_path)
    if not path.exists():
        report["database"]["status"] = "missing"
        report["recommendations"].append(
            "SQLite file is missing; start the app once or run a workflow to create local data."
        )
        add_database_recommendations(report)
        return report

    report["database"]["status"] = "readable_candidate"
    report["database"]["exists"] = True
    report["storage"] = build_storage_report(path)
    report["sidecars"] = build_sidecar_reports(path, root)

    try:
        with connect_read_only(path) as connection:
            report["database"]["status"] = "readable"
            existing_tables = list_tables(connection)
            report["tables"] = build_table_reports(connection, existing_tables)
            report["embedding_index"] = build_embedding_report(connection, existing_tables)
            report["agent_trace"] = build_agent_trace_report(connection, existing_tables)
            report["integrity"] = build_integrity_report(connection, run_quick_check)
    except sqlite3.Error as exc:
        report["ok"] = False
        report["database"]["status"] = "error"
        report["database"]["error"] = str(exc)
        report["recommendations"].append(
            "SQLite read-only inspection failed; verify the file is a SQLite database "
            "and that local permissions allow reading it."
        )
        return report

    add_database_recommendations(report)
    return report


def empty_report(root: Path) -> dict[str, Any]:
    return {
        "ok": True,
        "project_root": str(root),
        "database": {
            "status": "unknown",
            "type": "sqlite",
            "path": "",
            "absolute_path": "",
            "exists": False,
            "inside_project_root": False,
        },
        "storage": {
            "database_bytes": 0,
            "database_megabytes": 0.0,
            "page_count": 0,
            "page_size": 0,
            "page_bytes": 0,
            "freelist_count": 0,
            "free_bytes": 0,
            "freelist_ratio": 0.0,
            "sidecar_bytes": 0,
            "total_bytes": 0,
            "total_megabytes": 0.0,
        },
        "sidecars": [],
        "tables": [],
        "embedding_index": {
            "row_count": 0,
            "owner_type_counts": {},
            "model_dimension_counts": [],
            "has_vectors": False,
        },
        "agent_trace": {
            "agent_runs": 0,
            "tool_call_records": 0,
            "replay_cases": 0,
            "run_status_counts": {},
            "tool_status_counts": {},
            "replay_verdict_counts": {},
        },
        "integrity": {
            "quick_check_run": False,
            "quick_check_ok": None,
            "quick_check_messages": [],
        },
        "recommendations": [],
        "notes": [
            "Report is read-only and aggregate-only.",
            "It does not read .env files, API keys, provider credentials, or private paper content.",
            "Maintenance actions such as VACUUM, checkpoint, cleanup, restore, or migrations require explicit operator approval.",
        ],
    }


def parse_sqlite_path(database_url: str, root: Path) -> dict[str, Any]:
    if not database_url.startswith("sqlite:///"):
        return {
            "status": "unsupported",
            "type": "unsupported",
            "path": "",
            "absolute_path": "",
            "exists": False,
            "inside_project_root": False,
        }

    raw_path = database_url.replace("sqlite:///", "", 1).split("?", 1)[0]
    if raw_path == ":memory:":
        return {
            "status": "memory",
            "type": "sqlite",
            "path": ":memory:",
            "absolute_path": ":memory:",
            "exists": False,
            "inside_project_root": False,
        }

    path = Path(raw_path)
    if not path.is_absolute():
        path = root / path
    path = path.resolve()
    return {
        "status": "candidate",
        "type": "sqlite",
        "path": relative_or_absolute_path(path, root),
        "absolute_path": str(path),
        "exists": path.exists(),
        "inside_project_root": is_relative_to(path, root),
    }


def build_storage_report(path: Path) -> dict[str, Any]:
    database_bytes = safe_size(path)
    page_count = 0
    page_size = 0
    freelist_count = 0
    try:
        with connect_read_only(path) as connection:
            page_count = int(fetch_pragma(connection, "page_count") or 0)
            page_size = int(fetch_pragma(connection, "page_size") or 0)
            freelist_count = int(fetch_pragma(connection, "freelist_count") or 0)
    except sqlite3.Error:
        pass

    free_bytes = freelist_count * page_size
    page_bytes = page_count * page_size
    sidecar_bytes = sum(safe_size(sidecar_path) for sidecar_path in sidecar_paths(path))
    total_bytes = database_bytes + sidecar_bytes
    freelist_ratio = round(freelist_count / page_count, 4) if page_count else 0.0
    return {
        "database_bytes": database_bytes,
        "database_megabytes": round(database_bytes / 1024 / 1024, 3),
        "page_count": page_count,
        "page_size": page_size,
        "page_bytes": page_bytes,
        "freelist_count": freelist_count,
        "free_bytes": free_bytes,
        "freelist_ratio": freelist_ratio,
        "sidecar_bytes": sidecar_bytes,
        "total_bytes": total_bytes,
        "total_megabytes": round(total_bytes / 1024 / 1024, 3),
    }


def build_sidecar_reports(path: Path, root: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": relative_or_absolute_path(sidecar_path, root),
            "exists": sidecar_path.exists(),
            "bytes": safe_size(sidecar_path),
        }
        for sidecar_path in sidecar_paths(path)
    ]


def sidecar_paths(path: Path) -> list[Path]:
    return [Path(f"{path}-wal"), Path(f"{path}-shm")]


def connect_read_only(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)


def fetch_pragma(connection: sqlite3.Connection, name: str) -> Any:
    cursor = connection.execute(f"PRAGMA {name}")
    row = cursor.fetchone()
    return row[0] if row else None


def list_tables(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
    ).fetchall()
    return {str(row[0]) for row in rows}


def build_table_reports(
    connection: sqlite3.Connection,
    existing_tables: set[str],
) -> list[dict[str, Any]]:
    reports = []
    for table in IMPORTANT_TABLES:
        if table not in existing_tables:
            reports.append({"name": table, "exists": False, "row_count": 0})
            continue
        reports.append({"name": table, "exists": True, "row_count": count_rows(connection, table)})
    return reports


def build_embedding_report(
    connection: sqlite3.Connection,
    existing_tables: set[str],
) -> dict[str, Any]:
    if "research_embeddings" not in existing_tables:
        return {
            "row_count": 0,
            "owner_type_counts": {},
            "model_dimension_counts": [],
            "has_vectors": False,
        }

    owner_counts = {
        str(owner_type): int(count)
        for owner_type, count in connection.execute(
            """
            SELECT owner_type, COUNT(*)
            FROM research_embeddings
            GROUP BY owner_type
            ORDER BY owner_type
            """
        ).fetchall()
    }
    model_counts = [
        {
            "embedding_model": str(model),
            "dimension": int(dimension or 0),
            "row_count": int(count),
        }
        for model, dimension, count in connection.execute(
            """
            SELECT embedding_model, dimension, COUNT(*)
            FROM research_embeddings
            GROUP BY embedding_model, dimension
            ORDER BY embedding_model, dimension
            """
        ).fetchall()
    ]
    row_count = sum(owner_counts.values())
    return {
        "row_count": row_count,
        "owner_type_counts": owner_counts,
        "model_dimension_counts": model_counts,
        "has_vectors": row_count > 0,
    }


def build_agent_trace_report(
    connection: sqlite3.Connection,
    existing_tables: set[str],
) -> dict[str, Any]:
    return {
        "agent_runs": table_count(connection, existing_tables, "agent_runs"),
        "tool_call_records": table_count(connection, existing_tables, "tool_call_records"),
        "replay_cases": table_count(connection, existing_tables, "replay_cases"),
        "run_status_counts": grouped_counts(connection, existing_tables, "agent_runs", "status"),
        "tool_status_counts": grouped_counts(
            connection, existing_tables, "tool_call_records", "status"
        ),
        "replay_verdict_counts": grouped_counts(
            connection, existing_tables, "replay_cases", "verdict"
        ),
    }


def build_integrity_report(
    connection: sqlite3.Connection,
    run_quick_check: bool,
) -> dict[str, Any]:
    if not run_quick_check:
        return {
            "quick_check_run": False,
            "quick_check_ok": None,
            "quick_check_messages": [],
        }
    rows = connection.execute("PRAGMA quick_check").fetchall()
    messages = [str(row[0]) for row in rows]
    return {
        "quick_check_run": True,
        "quick_check_ok": messages == ["ok"],
        "quick_check_messages": messages,
    }


def add_database_recommendations(report: dict[str, Any]) -> None:
    recommendations = report["recommendations"]
    database = report["database"]
    if database["status"] == "unsupported":
        recommendations.append(
            "Only SQLite is covered by this local maintenance report; use provider-specific checks for other databases."
        )
        return
    if database["status"] == "memory":
        recommendations.append(
            "Use a file-backed SQLite database under data/research for persistent local agent runs."
        )
        return
    if database["status"] not in {"readable", "missing"}:
        return

    if database["status"] == "readable":
        storage = report["storage"]
        if storage["freelist_ratio"] >= 0.2 and storage["page_count"] >= 1000:
            recommendations.append(
                "Freelist ratio is high; after a cold backup, consider an approved VACUUM during maintenance."
            )
        wal = next((item for item in report["sidecars"] if item["path"].endswith("-wal")), None)
        if wal and wal["bytes"] >= 64 * 1024 * 1024:
            recommendations.append(
                "SQLite WAL sidecar is large; after stopping the service and backing up, consider an approved checkpoint."
            )
        table_counts = {item["name"]: item["row_count"] for item in report["tables"]}
        research_objects = sum(
            table_counts.get(name, 0) for name in ["chunks", "evidences", "research_gaps", "ideas"]
        )
        if research_objects and not report["embedding_index"]["row_count"]:
            recommendations.append(
                "Research objects exist but the embedding table is empty; run POST /research/embeddings/rebuild or the matching local workflow before relying on dense retrieval."
            )
        if report["agent_trace"]["agent_runs"] == 0:
            recommendations.append(
                "Agent trace tables are empty; run Advisor or replay flows before using observability metrics for a demo."
            )
        quick_check_ok = report["integrity"]["quick_check_ok"]
        if quick_check_ok is False:
            report["ok"] = False
            recommendations.append(
                "SQLite quick_check did not return ok; stop writes, make a cold backup, and inspect the database before continuing."
            )

    recommendations.append(
        "Before any approved maintenance, build a backup manifest with scripts/build_local_backup_manifest.py."
    )


def table_count(connection: sqlite3.Connection, existing_tables: set[str], table: str) -> int:
    if table not in existing_tables:
        return 0
    return count_rows(connection, table)


def grouped_counts(
    connection: sqlite3.Connection,
    existing_tables: set[str],
    table: str,
    column: str,
) -> dict[str, int]:
    if table not in existing_tables:
        return {}
    rows = connection.execute(
        f"SELECT {column}, COUNT(*) FROM {table} GROUP BY {column} ORDER BY {column}"
    ).fetchall()
    return {str(key or ""): int(count) for key, count in rows}


def count_rows(connection: sqlite3.Connection, table: str) -> int:
    cursor = connection.execute(f"SELECT COUNT(*) FROM {table}")
    row = cursor.fetchone()
    return int(row[0]) if row else 0


def render_markdown(report: dict[str, Any]) -> str:
    database = report["database"]
    storage = report["storage"]
    lines = [
        "# SQLite Maintenance Report",
        "",
        "## Summary",
        "",
        f"- Status: {database['status']}",
        f"- Database: {database['path'] or database['type']}",
        f"- Inside project root: {database['inside_project_root']}",
        f"- Total storage MB: {storage['total_megabytes']}",
        f"- Freelist ratio: {storage['freelist_ratio']}",
        f"- Quick check: {format_quick_check(report['integrity'])}",
        "",
        "## Vector Index",
        "",
        f"- Embedding rows: {report['embedding_index']['row_count']}",
    ]
    lines.extend(render_counts(report["embedding_index"]["owner_type_counts"]))
    lines.extend(["", "## Agent Trace", ""])
    trace = report["agent_trace"]
    lines.extend(
        [
            f"- Agent runs: {trace['agent_runs']}",
            f"- Tool call records: {trace['tool_call_records']}",
            f"- Replay cases: {trace['replay_cases']}",
        ]
    )
    lines.extend(["", "## Important Tables", ""])
    for item in report["tables"]:
        if item["exists"]:
            lines.append(f"- {item['name']}: {item['row_count']}")
    if not any(item["exists"] for item in report["tables"]):
        lines.append("- None")
    lines.extend(["", "## Recommendations", ""])
    lines.extend(render_list(report["recommendations"]))
    lines.extend(["", "## Notes", ""])
    lines.extend(render_list(report["notes"]))
    lines.append("")
    return "\n".join(lines)


def render_counts(counts: dict[str, int]) -> list[str]:
    if not counts:
        return ["- Owner types: none"]
    return [f"- {key}: {counts[key]}" for key in sorted(counts)]


def render_list(items: list[str]) -> list[str]:
    if not items:
        return ["- None"]
    return [f"- {item}" for item in items]


def format_quick_check(integrity: dict[str, Any]) -> str:
    if not integrity["quick_check_run"]:
        return "skipped"
    return "ok" if integrity["quick_check_ok"] else "failed"


def print_human_report(report: dict[str, Any]) -> None:
    database = report["database"]
    storage = report["storage"]
    print("SQLite maintenance report")
    print(f"Project root: {report['project_root']}")
    print(f"Database status: {database['status']}")
    print(f"Database path: {database['path'] or database['type']}")
    print(f"Inside project root: {'yes' if database['inside_project_root'] else 'no'}")
    print(
        "Storage: "
        f"{storage['total_megabytes']} MB total, "
        f"{storage['freelist_ratio']} freelist ratio"
    )
    print(f"Quick check: {format_quick_check(report['integrity'])}")
    print(f"Embedding rows: {report['embedding_index']['row_count']}")
    print(
        "Agent trace: "
        f"{report['agent_trace']['agent_runs']} runs, "
        f"{report['agent_trace']['tool_call_records']} tool calls, "
        f"{report['agent_trace']['replay_cases']} replay cases"
    )
    if report["recommendations"]:
        print("Recommendations:")
        for item in report["recommendations"]:
            print(f"- {item}")


def resolve_project_path(root: Path, value: Path) -> Path:
    resolved = value.resolve() if value.is_absolute() else (root / value).resolve()
    if not is_relative_to(resolved, root):
        raise SystemExit(f"output path must stay inside project root: {value}")
    return resolved


def safe_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def relative_or_absolute_path(path: Path, root: Path) -> str:
    return relative_path(path, root) if is_relative_to(path, root) else str(path)


def relative_path(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root).as_posix()


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
        print(f"SQLite maintenance report failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
