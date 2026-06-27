import json
from pathlib import Path
import sqlite3
import subprocess
import sys


def test_sqlite_maintenance_reports_aggregate_vector_and_trace_counts(tmp_path) -> None:
    db_path = tmp_path / "data/research/research_assistant.db"
    db_path.parent.mkdir(parents=True)
    with sqlite3.connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE papers (id TEXT PRIMARY KEY, title TEXT);
            CREATE TABLE chunks (id TEXT PRIMARY KEY, text TEXT);
            CREATE TABLE research_embeddings (
                id TEXT PRIMARY KEY,
                owner_type TEXT,
                owner_id TEXT,
                embedding_model TEXT,
                dimension INTEGER,
                text_hash TEXT,
                vector_json TEXT,
                payload_json TEXT
            );
            CREATE TABLE agent_runs (
                id TEXT PRIMARY KEY,
                status TEXT,
                run_type TEXT
            );
            CREATE TABLE tool_call_records (
                id TEXT PRIMARY KEY,
                agent_run_id TEXT,
                status TEXT
            );
            CREATE TABLE replay_cases (
                id TEXT PRIMARY KEY,
                verdict TEXT
            );
            INSERT INTO papers VALUES ('p1', 'private paper title should not print');
            INSERT INTO chunks VALUES ('c1', 'private chunk should not print');
            INSERT INTO research_embeddings VALUES (
                'e1', 'chunk', 'c1', 'local_hash_embedding_v0', 128, 'hash', '[0.1]', '{}'
            );
            INSERT INTO agent_runs VALUES ('r1', 'succeeded', 'advisor_chat');
            INSERT INTO tool_call_records VALUES ('t1', 'r1', 'succeeded');
            INSERT INTO replay_cases VALUES ('case1', 'passed');
            """
        )

    completed = run_sqlite_maintenance(
        "--project-root",
        str(tmp_path),
        "--database-url",
        f"sqlite:///{db_path}",
        "--json",
    )
    payload = json.loads(completed.stdout)

    assert payload["ok"] is True
    assert payload["database"]["status"] == "readable"
    assert payload["database"]["inside_project_root"] is True
    assert payload["embedding_index"]["row_count"] == 1
    assert payload["embedding_index"]["owner_type_counts"]["chunk"] == 1
    assert payload["agent_trace"]["agent_runs"] == 1
    assert payload["agent_trace"]["tool_call_records"] == 1
    assert payload["agent_trace"]["replay_cases"] == 1
    assert payload["integrity"]["quick_check_ok"] is True
    assert "private paper title" not in completed.stdout
    assert "private chunk" not in completed.stdout


def test_sqlite_maintenance_handles_missing_database_as_fresh_clone(tmp_path) -> None:
    completed = run_sqlite_maintenance(
        "--project-root",
        str(tmp_path),
        "--database-url",
        "sqlite:///./data/research/research_assistant.db",
        "--json",
    )
    payload = json.loads(completed.stdout)

    assert completed.returncode == 0
    assert payload["ok"] is True
    assert payload["database"]["status"] == "missing"
    assert "SQLite file is missing" in " ".join(payload["recommendations"])


def test_sqlite_maintenance_refuses_outside_project_database_by_default(tmp_path) -> None:
    outside_db = tmp_path.parent / f"{tmp_path.name}-outside-maintenance.db"
    with sqlite3.connect(outside_db) as connection:
        connection.execute("CREATE TABLE papers (id TEXT PRIMARY KEY, title TEXT)")

    completed = run_sqlite_maintenance(
        "--project-root",
        str(tmp_path),
        "--database-url",
        f"sqlite:///{outside_db}",
        "--json",
    )
    payload = json.loads(completed.stdout)

    assert completed.returncode == 0
    assert payload["ok"] is True
    assert payload["database"]["status"] == "outside_project_root"
    assert "confirming the data is safe" in " ".join(payload["recommendations"])


def test_sqlite_maintenance_can_write_project_local_reports(tmp_path) -> None:
    db_path = tmp_path / "data/research/research_assistant.db"
    db_path.parent.mkdir(parents=True)
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE papers (id TEXT PRIMARY KEY)")

    json_path = "outputs/maintenance/sqlite-report.json"
    markdown_path = "outputs/maintenance/sqlite-report.md"
    completed = run_sqlite_maintenance(
        "--project-root",
        str(tmp_path),
        "--database-url",
        f"sqlite:///{db_path}",
        "--write-json",
        json_path,
        "--write-markdown",
        markdown_path,
        "--markdown",
    )

    assert "# SQLite Maintenance Report" in completed.stdout
    assert "Embedding rows" in completed.stdout
    assert (tmp_path / json_path).exists()
    assert (tmp_path / markdown_path).exists()
    written = json.loads((tmp_path / json_path).read_text(encoding="utf-8"))
    assert written["database"]["status"] == "readable"


def run_sqlite_maintenance(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(Path("scripts/check_sqlite_maintenance.py")), *args],
        capture_output=True,
        text=True,
        check=True,
    )
