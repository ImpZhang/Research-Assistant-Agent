import json
import subprocess
import sys


def test_migration_baseline_matches_current_models() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_migration_baseline.py",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["ok"] is True
    assert payload["expected_revision"] == "0001_baseline_schema"
    assert payload["current_table_count"] == 35
    assert payload["expected_schema_hash"] == payload["current_schema_hash"]


def test_migration_baseline_reports_drift(tmp_path) -> None:
    baseline = tmp_path / "migrations/baseline_schema.json"
    baseline.parent.mkdir()
    baseline.write_text(
        json.dumps(
            {
                "revision": "0001_baseline_schema",
                "schema_hash": "wrong",
                "table_count": 0,
                "tables": [],
            }
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_migration_baseline.py",
            "--project-root",
            str(tmp_path),
            "--baseline",
            "migrations/baseline_schema.json",
            "--json",
        ],
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert completed.returncode == 1
    assert payload["ok"] is False
    assert "SQLAlchemy metadata hash differs" in payload["errors"][0]
