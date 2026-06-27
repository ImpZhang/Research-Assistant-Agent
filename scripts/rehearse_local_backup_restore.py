#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import sys
import tarfile
import tempfile
from typing import Any

from build_local_backup_manifest import BACKUP_SETS, SECRET_PATHS, SECRET_SUFFIXES, build_manifest


def main() -> int:
    args = parse_args()
    root = args.project_root.resolve()
    scratch_parent = resolve_scratch_parent(root, args.scratch_dir)
    scratch_parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="backup-restore-", dir=scratch_parent) as temp_dir:
        temp_root = Path(temp_dir)
        source_root = temp_root / "source"
        restored_root = temp_root / "restored"
        archive_path = temp_root / "synthetic-local-backup.tar.gz"

        create_synthetic_project(source_root)
        archive_report = create_archive(source_root, archive_path)
        extract_archive(archive_path, restored_root)
        source_manifest = build_manifest(source_root)
        restored_manifest = build_manifest(restored_root)
        comparison = compare_manifests(source_manifest, restored_manifest)
        secret_copy_violations = detect_secret_copy_violations(restored_root)
        report = build_report(
            root=root,
            archive_report=archive_report,
            comparison=comparison,
            secret_copy_violations=secret_copy_violations,
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
            "Run a synthetic local backup/restore rehearsal. The rehearsal creates "
            "temporary sample data, archives the project backup sets, restores into "
            "a temporary project root, and compares aggregate manifests. It does not "
            "copy live local papers, live SQLite data, or .env files."
        )
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--scratch-dir",
        type=Path,
        default=Path(".cache/backup-restore-rehearsal"),
        help="Project-local scratch directory for temporary synthetic data.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--markdown", action="store_true", help="Print a Markdown report.")
    parser.add_argument("--write-json", type=Path, default=None)
    parser.add_argument("--write-markdown", type=Path, default=None)
    return parser.parse_args()


def create_synthetic_project(root: Path) -> None:
    (root / "data/research").mkdir(parents=True)
    (root / "data/papers").mkdir(parents=True)
    (root / "data/audit").mkdir(parents=True)
    (root / "data/benchmarks/geoloc").mkdir(parents=True)
    (root / "outputs/evaluations").mkdir(parents=True)
    (root / "configs").mkdir(parents=True)

    create_sqlite_fixture(root / "data/research/research_assistant.db")
    (root / "data/papers/synthetic-paper.txt").write_text(
        "Synthetic paper fixture for backup rehearsal.\n",
        encoding="utf-8",
    )
    (root / "data/audit/write-audit.jsonl").write_text(
        '{"event":"synthetic_write"}\n',
        encoding="utf-8",
    )
    (root / "data/benchmarks/geoloc/validation.jsonl").write_text(
        '{"id":"synthetic","country":"JP"}\n',
        encoding="utf-8",
    )
    (root / "outputs/evaluations/report.json").write_text(
        '{"summary":"synthetic"}\n',
        encoding="utf-8",
    )
    (root / "configs/benchmark_profiles.json").write_text(
        '{"profiles":[]}\n',
        encoding="utf-8",
    )
    (root / ".env").write_text("API_KEY=synthetic-secret-never-copy\n", encoding="utf-8")


def create_sqlite_fixture(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE restore_probe (id TEXT PRIMARY KEY, status TEXT)")
        connection.execute("INSERT INTO restore_probe VALUES ('probe-1', 'ok')")


def create_archive(source_root: Path, archive_path: Path) -> dict[str, Any]:
    added_paths: list[str] = []
    skipped_secret_paths: list[str] = detect_secret_copy_violations(source_root)
    with tarfile.open(archive_path, "w:gz") as archive:
        for backup_set in BACKUP_SETS:
            path = source_root / backup_set["path"]
            if not path.exists():
                continue
            for item in iter_backup_items(path):
                relative = relative_path(item, source_root)
                if is_secret_path(relative):
                    if relative not in skipped_secret_paths:
                        skipped_secret_paths.append(relative)
                    continue
                archive.add(item, arcname=relative, recursive=False)
                added_paths.append(relative)
    return {
        "archive_bytes": archive_path.stat().st_size,
        "entry_count": len(added_paths),
        "skipped_secret_paths": sorted(skipped_secret_paths),
    }


def iter_backup_items(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    items = [path]
    for child in sorted(path.rglob("*")):
        if child.is_symlink():
            continue
        items.append(child)
    return items


def extract_archive(archive_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive.getmembers():
            target = (destination / member.name).resolve()
            if not is_relative_to(target, destination):
                raise RuntimeError(f"unsafe archive member path: {member.name}")
            archive.extract(member, path=destination)


def compare_manifests(source: dict[str, Any], restored: dict[str, Any]) -> dict[str, Any]:
    source_sets = {item["name"]: item for item in source["backup_sets"]}
    restored_sets = {item["name"]: item for item in restored["backup_sets"]}
    mismatches = []
    for name in sorted(source_sets):
        source_item = source_sets[name]
        restored_item = restored_sets.get(name)
        if restored_item is None:
            mismatches.append({"name": name, "reason": "missing_restored_set"})
            continue
        for field in ["exists", "kind", "file_count", "directory_count", "total_bytes"]:
            if source_item[field] != restored_item[field]:
                mismatches.append(
                    {
                        "name": name,
                        "field": field,
                        "source": source_item[field],
                        "restored": restored_item[field],
                    }
                )
    return {
        "ok": not mismatches,
        "mismatches": mismatches,
        "source_total_bytes": source["totals"]["total_bytes"],
        "restored_total_bytes": restored["totals"]["total_bytes"],
        "source_file_count": source["totals"]["file_count"],
        "restored_file_count": restored["totals"]["file_count"],
    }


def detect_secret_copy_violations(root: Path) -> list[str]:
    violations = []
    for secret_path in SECRET_PATHS:
        path = root / secret_path
        if path.exists():
            violations.append(secret_path)
    for path in root.rglob("*"):
        if path.is_file() and path.name.endswith(SECRET_SUFFIXES):
            violations.append(relative_path(path, root))
    return sorted(set(violations))


def build_report(
    *,
    root: Path,
    archive_report: dict[str, Any],
    comparison: dict[str, Any],
    secret_copy_violations: list[str],
) -> dict[str, Any]:
    ok = comparison["ok"] and not secret_copy_violations and archive_report["entry_count"] > 0
    return {
        "ok": ok,
        "project_root": str(root),
        "mode": "synthetic_only",
        "archive": archive_report,
        "comparison": comparison,
        "secret_copy_violations": secret_copy_violations,
        "notes": [
            "Rehearsal uses temporary synthetic data only.",
            "It does not copy live local papers, live SQLite data, .env files, API keys, cookies, or provider credentials.",
            "Real backup, restore, Docker volume operations, migrations, and data rewrites still require explicit operator approval.",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Local Backup Restore Rehearsal",
        "",
        "## Summary",
        "",
        f"- OK: {report['ok']}",
        f"- Mode: {report['mode']}",
        f"- Archive entries: {report['archive']['entry_count']}",
        f"- Archive bytes: {report['archive']['archive_bytes']}",
        f"- Source files: {report['comparison']['source_file_count']}",
        f"- Restored files: {report['comparison']['restored_file_count']}",
        f"- Source bytes: {report['comparison']['source_total_bytes']}",
        f"- Restored bytes: {report['comparison']['restored_total_bytes']}",
        "",
        "## Mismatches",
        "",
    ]
    if report["comparison"]["mismatches"]:
        for mismatch in report["comparison"]["mismatches"]:
            lines.append(f"- {json.dumps(mismatch, sort_keys=True)}")
    else:
        lines.append("- None")
    lines.extend(["", "## Secret Copy Violations", ""])
    if report["secret_copy_violations"]:
        for violation in report["secret_copy_violations"]:
            lines.append(f"- {violation}")
    else:
        lines.append("- None")
    lines.extend(["", "## Notes", ""])
    for note in report["notes"]:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def print_human_report(report: dict[str, Any]) -> None:
    print("Local backup restore rehearsal")
    print(f"Project root: {report['project_root']}")
    print(f"Mode: {report['mode']}")
    print(f"OK: {'yes' if report['ok'] else 'no'}")
    print(
        "Archive: "
        f"{report['archive']['entry_count']} entries, "
        f"{report['archive']['archive_bytes']} bytes"
    )
    print(
        "Manifest comparison: "
        f"{report['comparison']['source_file_count']} source files, "
        f"{report['comparison']['restored_file_count']} restored files"
    )
    if report["comparison"]["mismatches"]:
        print("Mismatches:")
        for mismatch in report["comparison"]["mismatches"]:
            print(f"- {json.dumps(mismatch, sort_keys=True)}")
    if report["secret_copy_violations"]:
        print("Secret copy violations:")
        for violation in report["secret_copy_violations"]:
            print(f"- {violation}")
    print("Notes:")
    for note in report["notes"]:
        print(f"- {note}")


def resolve_scratch_parent(root: Path, value: Path) -> Path:
    resolved = resolve_project_path(root, value)
    return resolved


def resolve_project_path(root: Path, value: Path) -> Path:
    resolved = value.resolve() if value.is_absolute() else (root / value).resolve()
    if not is_relative_to(resolved, root):
        raise SystemExit(f"output path must stay inside project root: {value}")
    return resolved


def is_secret_path(relative: str) -> bool:
    if relative in SECRET_PATHS:
        return True
    return Path(relative).name.endswith(SECRET_SUFFIXES)


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
        print(f"Local backup restore rehearsal failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
