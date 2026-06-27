import json

from fastapi.testclient import TestClient
import pytest

from backend.app import create_app
import backend.research.routes as routes_module
from backend.research.services.evaluation_report_service import EvaluationReportService
from scripts import evaluate_real_papers


def test_evaluation_report_service_lists_latest_and_summarizes(tmp_path) -> None:
    _write_report(
        tmp_path,
        "real_paper_eval_20260625_080000",
        completed=1,
        readiness=0.4,
        quality=0.5,
    )
    _write_report(
        tmp_path,
        "real_paper_eval_20260625_082124",
        completed=2,
        readiness=0.7,
        quality=0.6,
    )

    service = EvaluationReportService(tmp_path)
    reports = service.list_real_paper_reports()
    latest = service.load_latest_real_paper_report()

    assert [report["report_id"] for report in reports] == [
        "real_paper_eval_20260625_082124",
        "real_paper_eval_20260625_080000",
    ]
    assert latest["report_id"] == "real_paper_eval_20260625_082124"
    assert latest["completed_paper_count"] == 2
    assert latest["average_readiness"] == 0.7
    assert latest["average_quality_gate"] == 0.6
    assert latest["markdown_export"].startswith("# Report real_paper_eval_20260625_082124")


def test_evaluation_report_service_rejects_unsafe_report_ids(tmp_path) -> None:
    service = EvaluationReportService(tmp_path)

    with pytest.raises(ValueError):
        service.load_real_paper_report("../.env")


def test_real_paper_evaluation_report_routes(monkeypatch) -> None:
    class FakeEvaluationReportService:
        def list_real_paper_reports(self, limit: int = 20):
            assert limit == 3
            return [_fake_report_summary()]

        def load_latest_real_paper_report(self):
            return _fake_report_detail()

        def load_real_paper_report_detail(self, report_id: str):
            if report_id == "not_a_report":
                raise ValueError("Invalid real-paper evaluation report id.")
            if report_id == "real_paper_eval_20260625_082124":
                return _fake_report_detail()
            raise FileNotFoundError("not found")

    monkeypatch.setattr(
        routes_module,
        "EvaluationReportService",
        FakeEvaluationReportService,
    )

    client = TestClient(create_app())

    listed = client.get("/research/evaluations/real-paper/reports?limit=3")
    latest = client.get("/research/evaluations/real-paper/reports/latest")
    detail = client.get("/research/evaluations/real-paper/reports/real_paper_eval_20260625_082124")
    missing = client.get("/research/evaluations/real-paper/reports/real_paper_eval_20260625_000000")
    invalid = client.get("/research/evaluations/real-paper/reports/not_a_report")
    status = client.get("/research/status")

    assert listed.status_code == 200
    assert listed.json()[0]["report_id"] == "real_paper_eval_20260625_082124"
    assert latest.status_code == 200
    assert latest.json()["markdown_export"] == "# Real eval"
    assert detail.status_code == 200
    assert missing.status_code == 404
    assert invalid.status_code == 400
    assert "real_paper_evaluation_reports" in status.json()["implemented_capabilities"]


def test_real_paper_evaluator_renders_retrieval_comparison_summary() -> None:
    report = {
        "started_at": "2026-06-25T00:00:00+00:00",
        "finished_at": "2026-06-25T00:01:00+00:00",
        "papers": [
            {
                "filename": "paper.pdf",
                "status": "completed",
                "workflow": {"idea_titles": ["Specific geolocalization idea"]},
                "metrics": {
                    "sections": 1,
                    "chunks": 2,
                    "evidence": 3,
                    "gaps": 1,
                    "ideas": 1,
                    "reviews": 1,
                    "experiment_plans": 1,
                    "embedding_model": "qwen3-vl-embedding",
                    "embedding_dimension": 2560,
                    "embedding_indexed": 3,
                    "context_searches_with_evidence": 3,
                    "context_searches_with_graph": 3,
                    "retrieval_top_evidence_overlap": 2,
                    "retrieval_comparison_queries": 3,
                    "local_retrieval_embedding_indexed": 3,
                },
            }
        ],
    }
    report["summary"] = evaluate_real_papers._build_summary(report["papers"])

    markdown = evaluate_real_papers._render_markdown(report)

    assert report["summary"]["retrieval_top_evidence_overlap"] == 2
    assert report["summary"]["retrieval_comparison_queries"] == 3
    assert "Retrieval comparison: `2` / `3` top evidence overlap" in markdown


def test_real_paper_evaluator_summarizes_recovered_workflow_artifacts() -> None:
    workflow = evaluate_real_papers._workflow_from_artifacts(
        {
            "job": {"id": "job-1", "status": "running", "progress": 0.55},
            "paper": {"id": "paper-1"},
            "card": {"id": "card-1"},
            "gaps": [{"id": "gap-1", "title": "Recovered gap"}],
            "ideas": [{"id": "idea-1", "title": "Recovered idea"}],
            "reviews": [],
            "novelty_checks": [],
            "experiment_plans": [],
            "markdown_export": "# Recovered",
            "message": "Recovered artifacts.",
        }
    )
    workflow["_workflow_execution_mode"] = "recovered_from_job_artifacts"
    workflow["_workflow_warning"] = "WorkflowTimeoutError: timed out"

    summary = evaluate_real_papers._summarize_workflow(workflow)

    assert summary["job_id"] == "job-1"
    assert summary["job_status"] == "running"
    assert summary["job_progress"] == 0.55
    assert summary["execution_mode"] == "recovered_from_job_artifacts"
    assert summary["recovered_from_job_artifacts"] is True
    assert summary["gap_count"] == 1
    assert summary["idea_count"] == 1
    assert summary["warning"].startswith("WorkflowTimeoutError")


def _write_report(
    tmp_path,
    report_id: str,
    *,
    completed: int,
    readiness: float,
    quality: float,
) -> None:
    papers = [
        {
            "filename": f"paper-{idx}.pdf",
            "status": "completed",
            "metrics": {
                "readiness_score": readiness,
                "quality_score": quality,
            },
        }
        for idx in range(completed)
    ]
    payload = {
        "started_at": "2026-06-25T00:00:00+00:00",
        "finished_at": "2026-06-25T00:01:00+00:00",
        "summary": {
            "paper_count": completed,
            "completed_paper_count": completed,
            "failed_paper_count": 0,
            "total_gaps": completed,
            "total_ideas": completed,
            "total_embedding_indexed": completed * 10,
            "embedding_models": ["qwen3-vl-embedding"],
        },
        "papers": papers,
    }
    (tmp_path / f"{report_id}.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )
    (tmp_path / f"{report_id}.md").write_text(
        f"# Report {report_id}",
        encoding="utf-8",
    )


def _fake_report_summary() -> dict:
    return {
        "report_id": "real_paper_eval_20260625_082124",
        "filename": "real_paper_eval_20260625_082124.json",
        "started_at": "2026-06-25T00:00:00+00:00",
        "finished_at": "2026-06-25T00:01:00+00:00",
        "paper_count": 1,
        "completed_paper_count": 1,
        "failed_paper_count": 0,
        "total_gaps": 1,
        "total_ideas": 1,
        "total_embedding_indexed": 8,
        "embedding_models": ["qwen3-vl-embedding"],
        "average_readiness": 0.7,
        "average_quality_gate": 0.6,
        "json_available": True,
        "markdown_available": True,
    }


def _fake_report_detail() -> dict:
    payload = _fake_report_summary()
    payload.update(
        {
            "summary": {"paper_count": 1},
            "papers": [{"filename": "paper.pdf", "status": "completed", "metrics": {}}],
            "markdown_export": "# Real eval",
            "message": "Loaded report.",
        }
    )
    return payload
