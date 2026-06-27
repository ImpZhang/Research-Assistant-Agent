import json
import os
from pathlib import Path
import subprocess
import sys


def test_replay_agent_case_script_evaluates_saved_case(tmp_path: Path) -> None:
    database_path = tmp_path / "replay.db"
    report_path = tmp_path / "replay.md"
    env = {
        **os.environ,
        "RESEARCH_DB_URL": f"sqlite:///{database_path}",
        "PYTHONPATH": str(Path.cwd()),
    }
    fixture = subprocess.run(
        [
            sys.executable,
            "-c",
            """
from backend.research.db import SessionLocal, init_db
from backend.research.schemas import AgentRunCreate, ReplayCaseCreate, ToolCallRecordCreate
from backend.research.services.agent_trace_service import AgentTraceService

init_db()
with SessionLocal() as session:
    service = AgentTraceService(session)
    run = service.create_run(
        AgentRunCreate(
            run_type="advisor_chat",
            status="completed",
            question="Which evidence risk matters most?",
            output={"answer": "Use evidence from context search."},
            created_by="pytest",
        )
    )
    service.create_tool_call(
        run.id,
        ToolCallRecordCreate(
            tool_name="search_research_context",
            tool_result_summary="Returned evidence chunks.",
            status="completed",
        ),
    )
    replay_case = service.create_replay_case(
        ReplayCaseCreate(
            source_agent_run_id=run.id,
            case_type="bad_tool_selection",
            query="Which evidence risk matters most?",
            expected={
                "required_tool_names": ["search_research_context"],
                "status": "completed",
                "must_contain": "evidence",
            },
            observed={"status": "completed", "answer": "Use evidence from context search."},
            verdict="needs_review",
        )
    )
    print(replay_case.id)
""",
        ],
        check=True,
        env=env,
        text=True,
        capture_output=True,
    )
    case_id = fixture.stdout.strip()

    replay = subprocess.run(
        [
            sys.executable,
            "scripts/replay_agent_case.py",
            "--case-id",
            case_id,
            "--json",
            "--write-markdown",
            str(report_path),
            "--fail-on-regression",
        ],
        check=True,
        env=env,
        text=True,
        capture_output=True,
    )
    payload = json.loads(replay.stdout)

    assert payload["summary"]["case_count"] == 1
    assert payload["summary"]["passed"] == 1
    assert payload["summary"]["failed"] == 0
    assert payload["cases"][0]["replay_verdict"] == "pass"
    assert payload["cases"][0]["tool_names"] == ["search_research_context"]
    assert "# Agent Replay Evaluation" in report_path.read_text(encoding="utf-8")
