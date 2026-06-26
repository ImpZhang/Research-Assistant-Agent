import json
from pathlib import Path
import subprocess
import sys


def test_local_backup_manifest_reports_aggregate_backup_sets(tmp_path) -> None:
    (tmp_path / "data/research").mkdir(parents=True)
    (tmp_path / "data/research/research_assistant.db").write_text("sqlite-data", encoding="utf-8")
    (tmp_path / "data/papers").mkdir(parents=True)
    (tmp_path / "data/papers/private-paper-title.txt").write_text("private paper", encoding="utf-8")
    (tmp_path / "outputs/evaluations").mkdir(parents=True)
    (tmp_path / "outputs/evaluations/report.json").write_text("{}", encoding="utf-8")
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs/benchmark_profiles.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".env").write_text("API_KEY=secret-never-print", encoding="utf-8")

    completed = run_manifest("--project-root", str(tmp_path), "--json")
    payload = json.loads(completed.stdout)
    sets = {item["name"]: item for item in payload["backup_sets"]}

    assert payload["ok"] is True
    assert sets["research_database"]["file_count"] == 1
    assert sets["uploaded_papers"]["file_count"] == 1
    assert sets["outputs"]["file_count"] == 1
    assert sets["local_benchmark_profiles"]["kind"] == "file"
    assert ".env" in payload["secret_files_excluded"]
    assert "secret-never-print" not in completed.stdout
    assert "private-paper-title" not in completed.stdout


def test_local_backup_manifest_can_write_project_local_json(tmp_path) -> None:
    output_path = "outputs/backups/local-backup-manifest.json"
    completed = run_manifest(
        "--project-root",
        str(tmp_path),
        "--write-json",
        output_path,
        "--json",
    )
    payload = json.loads(completed.stdout)
    written_path = tmp_path / output_path

    assert payload["written_to"] == output_path
    assert written_path.exists()
    written_payload = json.loads(written_path.read_text(encoding="utf-8"))
    assert written_payload["totals"]["file_count"] == 0
    assert "aggregate-only" in " ".join(written_payload["notes"])


def test_local_backup_manifest_rejects_output_outside_project(tmp_path) -> None:
    completed = run_manifest(
        "--project-root",
        str(tmp_path),
        "--write-json",
        str(tmp_path.parent / "outside.json"),
        "--json",
        check=False,
    )

    assert completed.returncode == 1
    assert "output path must stay inside project root" in completed.stderr


def run_manifest(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(Path("scripts/build_local_backup_manifest.py")), *args],
        capture_output=True,
        text=True,
        check=check,
    )
