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


def test_replay_agent_case_live_context_search_executor(tmp_path: Path) -> None:
    database_path = tmp_path / "replay-live.db"
    env = {
        **os.environ,
        "RESEARCH_DB_URL": f"sqlite:///{database_path}",
        "PYTHONPATH": str(Path.cwd()),
        "RETRIEVAL_EMBEDDING_PROVIDER": "local",
        "RETRIEVAL_RERANK_PROVIDER": "disabled",
    }
    fixture = subprocess.run(
        [
            sys.executable,
            "-c",
            """
from backend.research.db import SessionLocal, init_db
from backend.research.models import Chunk, Evidence, Paper
from backend.research.schemas import ReplayCaseCreate
from backend.research.services.agent_trace_service import AgentTraceService

init_db()
with SessionLocal() as session:
    paper = Paper(
        title="Fixture geolocalization paper",
        authors_json=["Pytest"],
        year=2026,
        domain="image geolocalization",
        task="context search replay",
        status="parsed",
    )
    session.add(paper)
    session.flush()
    chunk = Chunk(
        paper_id=paper.id,
        chunk_id="fixture-chunk-001",
        text=(
            "Hydrograph satellite replay sentinel evidence explains "
            "geolocalization retrieval failures."
        ),
        token_count=9,
    )
    evidence = Evidence(
        paper_id=paper.id,
        chunk_id=chunk.chunk_id,
        evidence_type="failure_mode",
        text=(
            "The hydrograph satellite replay sentinel evidence is required "
            "for this context-search bad case."
        ),
        summary="Hydrograph satellite sentinel evidence.",
        supports="context_search_miss replay",
        confidence=0.9,
    )
    session.add_all([chunk, evidence])
    session.flush()
    replay_case = AgentTraceService(session).create_replay_case(
        ReplayCaseCreate(
            case_type="context_search_miss",
            query="hydrograph satellite replay sentinel evidence",
            expected={
                "query": "hydrograph satellite replay sentinel evidence",
                "paper_ids": [paper.id],
                "required_chunk_ids": [chunk.id],
                "required_evidence_ids": [evidence.id],
                "min_chunk_count": 1,
                "min_evidence_count": 1,
                "live_status": "completed",
            },
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
            "--live-executors",
            "--record-run",
            "--json",
            "--fail-on-regression",
        ],
        check=True,
        env=env,
        text=True,
        capture_output=True,
    )
    payload = json.loads(replay.stdout)
    case = payload["cases"][0]

    assert payload["summary"]["case_count"] == 1
    assert payload["summary"]["passed"] == 1
    assert payload["summary"]["failed"] == 0
    assert case["replay_verdict"] == "pass"
    assert case["observed"]["live_executor"] == "context_search"
    assert case["observed"]["live_status"] == "completed"
    assert case["observed"]["context_counts"]["chunks"] >= 1
    assert case["observed"]["context_counts"]["evidences"] >= 1

    trace_probe = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import json

from backend.research.db import SessionLocal
from backend.research.models import AgentRun, ToolCallRecord

with SessionLocal() as session:
    run = (
        session.query(AgentRun)
        .filter(AgentRun.run_type == "agent_replay")
        .order_by(AgentRun.created_at.desc())
        .first()
    )
    records = (
        session.query(ToolCallRecord)
        .filter(ToolCallRecord.agent_run_id == run.id)
        .order_by(ToolCallRecord.created_at.asc())
        .all()
    )
    print(
        json.dumps(
            {
                "run_type": run.run_type,
                "run_status": run.status,
                "summary": run.output_json.get("summary"),
                "tool_names": [record.tool_name for record in records],
                "tool_statuses": [record.status for record in records],
                "side_effects": [record.side_effect for record in records],
            },
            sort_keys=True,
        )
    )
""",
        ],
        check=True,
        env=env,
        text=True,
        capture_output=True,
    )
    trace_payload = json.loads(trace_probe.stdout)

    assert trace_payload["run_type"] == "agent_replay"
    assert trace_payload["run_status"] == "completed"
    assert trace_payload["summary"]["passed"] == 1
    assert trace_payload["tool_names"] == ["replay.context_search"]
    assert trace_payload["tool_statuses"] == ["completed"]
    assert trace_payload["side_effects"] == [False]


def test_replay_agent_case_live_citation_audit_executor(tmp_path: Path) -> None:
    database_path = tmp_path / "replay-citation.db"
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
from backend.research.models import Evidence, Paper
from backend.research.schemas import ReplayCaseCreate
from backend.research.services.agent_trace_service import AgentTraceService

init_db()
with SessionLocal() as session:
    paper = Paper(
        title="Citation audit fixture",
        authors_json=["Pytest"],
        year=2026,
        domain="image geolocalization",
        task="citation audit",
        status="parsed",
    )
    session.add(paper)
    session.flush()
    evidence = Evidence(
        paper_id=paper.id,
        evidence_type="claim",
        text="Geo-localization benchmark evidence supports citation-faithful replay.",
        summary="Citation-faithful geolocalization evidence.",
        supports="citation audit replay",
        confidence=0.95,
    )
    session.add(evidence)
    session.flush()
    replay_case = AgentTraceService(session).create_replay_case(
        ReplayCaseCreate(
            case_type="citation_audit",
            query="Does the answer cite the right geolocalization evidence?",
            expected={
                "paper_ids": [paper.id],
                "required_cited_evidence_ids": [evidence.id],
                "required_citation_terms": ["geolocalization", "citation-faithful"],
                "min_citation_count": 1,
                "max_missing_citation_count": 0,
                "max_wrong_paper_citation_count": 0,
                "max_citation_term_miss_count": 0,
                "live_status": "completed",
            },
            observed={"cited_evidence_ids": [evidence.id]},
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
            "--live-executors",
            "--record-run",
            "--json",
            "--fail-on-regression",
        ],
        check=True,
        env=env,
        text=True,
        capture_output=True,
    )
    payload = json.loads(replay.stdout)
    case = payload["cases"][0]

    assert payload["summary"]["case_count"] == 1
    assert payload["summary"]["passed"] == 1
    assert payload["summary"]["failed"] == 0
    assert case["replay_verdict"] == "pass"
    assert case["observed"]["live_executor"] == "citation_audit"
    assert case["observed"]["citation_counts"]["cited"] == 1
    assert case["observed"]["citation_counts"]["missing"] == 0
    assert case["observed"]["citation_counts"]["wrong_paper"] == 0
    assert case["observed"]["citation_counts"]["term_miss"] == 0

    trace_probe = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import json

from backend.research.db import SessionLocal
from backend.research.models import AgentRun, ToolCallRecord

with SessionLocal() as session:
    run = (
        session.query(AgentRun)
        .filter(AgentRun.run_type == "agent_replay")
        .order_by(AgentRun.created_at.desc())
        .first()
    )
    records = (
        session.query(ToolCallRecord)
        .filter(ToolCallRecord.agent_run_id == run.id)
        .order_by(ToolCallRecord.created_at.asc())
        .all()
    )
    print(
        json.dumps(
            {
                "run_status": run.status,
                "tool_names": [record.tool_name for record in records],
                "tool_summaries": [record.tool_result_summary for record in records],
            },
            sort_keys=True,
        )
    )
""",
        ],
        check=True,
        env=env,
        text=True,
        capture_output=True,
    )
    trace_payload = json.loads(trace_probe.stdout)

    assert trace_payload["run_status"] == "completed"
    assert trace_payload["tool_names"] == ["replay.citation_audit"]
    assert "cited=1" in trace_payload["tool_summaries"][0]


def test_replay_agent_case_sota_readiness_false_positive_fails(tmp_path: Path) -> None:
    database_path = tmp_path / "replay-sota.db"
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
from backend.research.models import Idea, ResearchBrief
from backend.research.schemas import ReplayCaseCreate
from backend.research.services.agent_trace_service import AgentTraceService

init_db()
with SessionLocal() as session:
    idea = Idea(
        title="SOTA readiness false positive fixture",
        research_question="Can replay catch premature SOTA signoff?",
        core_hypothesis="Manual gates should block unsupported SOTA claims.",
        method_sketch="Audit signoff evidence readiness.",
        novelty_argument="Requires benchmark and nearest-work closure.",
    )
    session.add(idea)
    session.flush()
    signoff = ResearchBrief(
        title="SOTA Signoff - false positive fixture",
        scope="sota_signoff_record",
        idea_ids_json=[idea.id],
        summary_json={
            "idea_id": idea.id,
            "decision": "confirmed_novel",
            "signoff_status": "sota_confirmed",
            "effective_external_search_completed": True,
            "external_search_status": "external_completed",
            "nearest_work": [{"title": "Nearest Work", "year": 2026}],
            "benchmark_run_ids": [],
            "benchmark_evidence_readiness": {
                "ready_for_sota_review": False,
                "readiness_status": "needs_benchmark_evidence",
            },
            "manual_gate_summary": {
                "ready_for_sota_claim": False,
                "requires_human_review": False,
                "blockers": ["benchmark_evidence_not_ready"],
                "nearest_work_count": 1,
                "benchmark_run_count": 0,
                "benchmark_evidence_ready_for_sota_review": False,
                "benchmark_evidence_readiness_status": "needs_benchmark_evidence",
            },
        },
        markdown_export="# SOTA Signoff Record",
        created_by="pytest",
    )
    session.add(signoff)
    session.flush()
    replay_case = AgentTraceService(session).create_replay_case(
        ReplayCaseCreate(
            case_type="sota_readiness_false_positive",
            query="Should this premature SOTA signoff be treated as ready?",
            expected={
                "idea_id": idea.id,
                "sota_signoff_id": signoff.id,
                "signoff_status": "sota_confirmed",
                "require_ready_for_sota_claim": True,
                "require_effective_external_search_completed": True,
                "require_benchmark_evidence_ready": True,
                "min_nearest_work_count": 1,
                "min_benchmark_run_count": 1,
                "max_sota_blocker_count": 0,
                "live_status": "completed",
            },
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
            "--live-executors",
            "--record-run",
            "--json",
            "--fail-on-regression",
        ],
        env=env,
        text=True,
        capture_output=True,
    )
    payload = json.loads(replay.stdout)
    case = payload["cases"][0]

    assert replay.returncode == 1
    assert payload["summary"]["case_count"] == 1
    assert payload["summary"]["passed"] == 0
    assert payload["summary"]["failed"] == 1
    assert case["replay_verdict"] == "fail"
    assert case["observed"]["live_executor"] == "sota_readiness_audit"
    assert case["observed"]["ready_for_sota_claim"] is False
    assert case["observed"]["sota_counts"]["blockers"] == 1
    assert any("ready_for_sota_claim" in reason for reason in case["reasons"])
    assert any("benchmark-run" in reason for reason in case["reasons"])

    trace_probe = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import json

from backend.research.db import SessionLocal
from backend.research.models import AgentRun, ToolCallRecord

with SessionLocal() as session:
    run = (
        session.query(AgentRun)
        .filter(AgentRun.run_type == "agent_replay")
        .order_by(AgentRun.created_at.desc())
        .first()
    )
    records = (
        session.query(ToolCallRecord)
        .filter(ToolCallRecord.agent_run_id == run.id)
        .order_by(ToolCallRecord.created_at.asc())
        .all()
    )
    print(
        json.dumps(
            {
                "run_status": run.status,
                "tool_names": [record.tool_name for record in records],
                "tool_summaries": [record.tool_result_summary for record in records],
            },
            sort_keys=True,
        )
    )
""",
        ],
        check=True,
        env=env,
        text=True,
        capture_output=True,
    )
    trace_payload = json.loads(trace_probe.stdout)

    assert trace_payload["run_status"] == "failed"
    assert trace_payload["tool_names"] == ["replay.sota_readiness_audit"]
    assert "ready=False" in trace_payload["tool_summaries"][0]
