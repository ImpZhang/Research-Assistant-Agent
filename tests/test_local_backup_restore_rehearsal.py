import json
from pathlib import Path
import subprocess
import sys


def test_local_backup_restore_rehearsal_uses_synthetic_data_only(tmp_path) -> None:
    completed = run_rehearsal("--project-root", str(tmp_path), "--json")
    payload = json.loads(completed.stdout)

    assert payload["ok"] is True
    assert payload["mode"] == "synthetic_only"
    assert payload["archive"]["entry_count"] > 0
    assert ".env" in payload["archive"]["skipped_secret_paths"]
    assert payload["comparison"]["ok"] is True
    assert (
        payload["comparison"]["source_file_count"] == payload["comparison"]["restored_file_count"]
    )
    assert payload["secret_copy_violations"] == []
    assert "synthetic-secret-never-copy" not in completed.stdout
    assert "live local papers" in " ".join(payload["notes"])


def test_local_backup_restore_rehearsal_can_write_project_reports(tmp_path) -> None:
    json_path = "outputs/restore-rehearsals/rehearsal.json"
    markdown_path = "outputs/restore-rehearsals/rehearsal.md"
    completed = run_rehearsal(
        "--project-root",
        str(tmp_path),
        "--write-json",
        json_path,
        "--write-markdown",
        markdown_path,
        "--markdown",
    )

    assert "# Local Backup Restore Rehearsal" in completed.stdout
    assert (tmp_path / json_path).exists()
    assert (tmp_path / markdown_path).exists()
    payload = json.loads((tmp_path / json_path).read_text(encoding="utf-8"))
    assert payload["ok"] is True


def test_local_backup_restore_rehearsal_rejects_outputs_outside_project(tmp_path) -> None:
    completed = run_rehearsal(
        "--project-root",
        str(tmp_path),
        "--write-json",
        str(tmp_path.parent / "outside-rehearsal.json"),
        "--json",
        check=False,
    )

    assert completed.returncode == 1
    assert "output path must stay inside project root" in completed.stderr


def run_rehearsal(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(Path("scripts/rehearse_local_backup_restore.py")), *args],
        capture_output=True,
        text=True,
        check=check,
    )
