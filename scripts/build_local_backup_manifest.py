#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


BACKUP_SETS = [
    {
        "name": "research_database",
        "path": "data/research",
        "description": "SQLite database and sidecar files.",
    },
    {
        "name": "uploaded_papers",
        "path": "data/papers",
        "description": "Locally uploaded source papers.",
    },
    {
        "name": "write_audit",
        "path": "data/audit",
        "description": "Optional local write-audit JSONL metadata.",
    },
    {
        "name": "benchmark_ground_truth",
        "path": "data/benchmarks",
        "description": "Local benchmark datasets and labels.",
    },
    {
        "name": "outputs",
        "path": "outputs",
        "description": "Generated reports, predictions, benchmark runs, and exported dossiers.",
    },
    {
        "name": "local_benchmark_profiles",
        "path": "configs/benchmark_profiles.json",
        "description": "Ignored machine-local benchmark profile overrides.",
    },
]

SECRET_PATHS = [
    ".env",
    ".env.local",
    ".env.production",
]
SECRET_SUFFIXES = (".key", ".pem", ".p12", ".pfx")


def main() -> int:
    args = parse_args()
    root = args.project_root.resolve()
    manifest = build_manifest(root)
    if args.write_json:
        output_path = resolve_project_path(root, args.write_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        manifest["written_to"] = relative_path(output_path, root)

    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    else:
        print_human_manifest(manifest)
    return 0 if manifest["ok"] else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a read-only local backup manifest with aggregate counts and sizes. "
            "This does not copy data, read file contents, or include secret files."
        )
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--write-json",
        type=Path,
        default=None,
        help="Write the manifest to a project-local JSON file such as outputs/backups/manifest.json.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    return parser.parse_args()


def build_manifest(root: Path) -> dict[str, Any]:
    backup_sets = [scan_backup_set(root, item) for item in BACKUP_SETS]
    secret_files_excluded = detect_secret_files(root)
    warnings: list[str] = []
    if secret_files_excluded:
        warnings.append(
            "Secret-like files are present and intentionally excluded from backup sets."
        )

    total_bytes = sum(item["total_bytes"] for item in backup_sets)
    total_files = sum(item["file_count"] for item in backup_sets)
    return {
        "ok": True,
        "project_root": str(root),
        "backup_sets": backup_sets,
        "totals": {
            "file_count": total_files,
            "total_bytes": total_bytes,
            "total_megabytes": round(total_bytes / 1024 / 1024, 3),
        },
        "secret_files_excluded": secret_files_excluded,
        "notes": [
            "Manifest is aggregate-only: it does not list private paper filenames.",
            "Copy or archive data only after reviewing docs/deployment.md backup notes.",
            "Keep .env, API keys, cookies, private keys, and provider credentials outside git and public bundles.",
        ],
        "warnings": warnings,
    }


def scan_backup_set(root: Path, item: dict[str, str]) -> dict[str, Any]:
    path = root / item["path"]
    report = {
        "name": item["name"],
        "path": item["path"],
        "description": item["description"],
        "exists": path.exists(),
        "kind": "missing",
        "file_count": 0,
        "directory_count": 0,
        "total_bytes": 0,
        "skipped_symlink_count": 0,
    }
    if not path.exists():
        return report
    if path.is_symlink():
        report["kind"] = "symlink"
        report["skipped_symlink_count"] = 1
        return report
    if path.is_file():
        report["kind"] = "file"
        report["file_count"] = 1
        report["total_bytes"] = safe_size(path)
        return report

    report["kind"] = "directory"
    report["directory_count"] = 1
    for child in path.rglob("*"):
        if child.is_symlink():
            report["skipped_symlink_count"] += 1
            continue
        if child.is_dir():
            report["directory_count"] += 1
            continue
        if child.is_file():
            report["file_count"] += 1
            report["total_bytes"] += safe_size(child)
    return report


def safe_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def detect_secret_files(root: Path) -> list[str]:
    detected: set[str] = set()
    for value in SECRET_PATHS:
        path = root / value
        if path.exists():
            detected.add(relative_path(path, root))
    for path in root.glob("*"):
        if path.is_file() and path.name.endswith(SECRET_SUFFIXES):
            detected.add(relative_path(path, root))
    return sorted(detected)


def resolve_project_path(root: Path, value: Path) -> Path:
    resolved = value.resolve() if value.is_absolute() else (root / value).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise SystemExit(f"output path must stay inside project root: {value}") from exc
    return resolved


def relative_path(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root).as_posix()


def print_human_manifest(manifest: dict[str, Any]) -> None:
    print("Local backup manifest")
    print(f"Project root: {manifest['project_root']}")
    print(
        "Totals: "
        f"{manifest['totals']['file_count']} files, "
        f"{manifest['totals']['total_megabytes']} MB"
    )
    for item in manifest["backup_sets"]:
        print(
            f"{item['name']}: exists={'yes' if item['exists'] else 'no'} "
            f"files={item['file_count']} bytes={item['total_bytes']} path={item['path']}"
        )
    if manifest["secret_files_excluded"]:
        print(f"Secret files excluded: {', '.join(manifest['secret_files_excluded'])}")
    for warning in manifest["warnings"]:
        print(f"Warning: {warning}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except OSError as exc:
        print(f"Local backup manifest failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
