from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import time
from types import SimpleNamespace
import zipfile
from xml.etree import ElementTree

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.research.db import SessionLocal
from backend.research.models import (
    Evidence,
    RelatedWorkMatrix,
    ProposalReview,
    ProposalDraft,
    ExperimentPlan,
    Idea,
    Paper,
    ResearchEdge,
    ResearchEmbedding,
    ResearchGap,
    ResearchNode,
)
from backend.research.services.experiment_service import ExperimentService
from backend.research.services.gap_service import GapService
from backend.research.services.graph_service import GraphService
from backend.research.services.idea_service import IdeaService
from backend.research.schemas import LiteratureSearchItem, LiteratureSearchResponse
from backend.research.services.literature_search_service import LiteratureSearchService
from backend.research.services.novelty_service import NoveltyService
from backend.research.services.paper_card_service import PaperCardService
from backend.research.services.proposal_service import ProposalDraftService
from backend.research.services.proposal_review_service import ProposalReviewService
from backend.research.services.proposal_revision_service import ProposalRevisionService
from backend.research.services.related_work_service import RelatedWorkService
from backend.research.services.retrieval_service import RetrievalService, ScoredItem
from backend.research.services.review_service import ReviewService
from backend.research.services.structured_extraction_service import StructuredExtractionService
from backend.research.services.workflow_service import WorkflowService


def test_health() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_ready_checks_database_and_storage() -> None:
    client = TestClient(create_app())
    response = client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["checks"]["database"]["ok"] is True
    assert body["checks"]["paper_upload_dir"]["ok"] is True
    assert body["checks"]["write_audit_dir"]["ok"] is True
    assert body["checks"]["write_audit_dir"]["enabled"] is False


def test_product_effect_scorecard_separates_quality_from_completion() -> None:
    from scripts.smoke_api import build_product_effect_scorecard

    summary = {
        "health": {"status": "ok"},
        "service_readiness": {"status": "ready"},
        "workbench_available": True,
        "tool_manifest_count": 119,
        "tool_bridge_count": 119,
        "gap_count": 3,
        "idea_count": 6,
        "novelty_check_count": 6,
        "proposal_review_decision": "ready_for_advisor_review",
        "proposal_review_score": 0.92,
        "experiment_analysis_decision": "supports_hypothesis",
        "experiment_plan_count": 6,
        "readiness_score": 0.6534,
        "quality_gate_score": 0.6574,
        "evidence_ledger_coverage_score": 0.24,
        "readiness_claim_validation_score": 0.35,
        "quality_gate_claim_validation_score": 0.35,
        "claim_validation_result_status": "needs_more_evidence",
        "project_bundle_file_count": 71,
        "project_bundle_readiness_level": "delivery_ready",
        "project_bundle_readiness_score": 1.0,
        "research_plan_item_count": 3,
        "research_plan_task_count": 9,
        "graph_node_count": 100,
        "graph_edge_count": 100,
    }

    scorecard = build_product_effect_scorecard(summary)

    assert 0.85 <= scorecard["overall_score"] < 0.9
    assert scorecard["band"] == "pilot_effective"
    assert scorecard["dimension_scores"]["foundation"] == 1.0
    assert scorecard["dimension_scores"]["delivery_loop"] == 1.0
    assert scorecard["dimension_scores"]["quality_signal"] < 0.6
    assert scorecard["failed_checks"] == []

    weak_summary = dict(summary)
    weak_summary["service_readiness"] = {"status": "not_ready"}
    weak_summary["workbench_available"] = False
    weak_summary["gap_count"] = 1

    weak_scorecard = build_product_effect_scorecard(weak_summary)

    assert weak_scorecard["overall_score"] < scorecard["overall_score"]
    assert "service_ready" in weak_scorecard["failed_checks"]
    assert "workbench_available" in weak_scorecard["failed_checks"]
    assert "minimum_gaps_met" in weak_scorecard["failed_checks"]


def test_graph_service_reuses_duplicate_edges() -> None:
    client = TestClient(create_app())
    assert client.get("/health").status_code == 200

    session = SessionLocal()
    try:
        service = GraphService(session)
        source = service.get_or_create_node(
            node_type="pytest_graph_edge_reuse_source",
            label="Pytest graph edge reuse source",
            canonical_key="pytest-graph-edge-reuse-source",
        )
        target = service.get_or_create_node(
            node_type="pytest_graph_edge_reuse_target",
            label="Pytest graph edge reuse target",
            canonical_key="pytest-graph-edge-reuse-target",
        )
        first = service.create_edge(
            source_node=source,
            target_node=target,
            edge_type="pytest_reuses_duplicate_edge",
            evidence_ids=["evidence-a"],
            weight=0.25,
            payload={"first": True},
        )
        second = service.create_edge(
            source_node=source,
            target_node=target,
            edge_type="pytest_reuses_duplicate_edge",
            evidence_ids=["evidence-b", "evidence-a"],
            weight=0.75,
            payload={"second": True},
        )
        session.commit()

        assert second.id == first.id
        edge = session.get(ResearchEdge, first.id)
        assert edge is not None
        assert edge.weight == 0.75
        assert edge.evidence_ids_json == ["evidence-a", "evidence-b"]
        assert edge.payload_json == {"first": True, "second": True}
        duplicate_count = (
            session.query(ResearchEdge)
            .filter(
                ResearchEdge.source_node_id == source.id,
                ResearchEdge.target_node_id == target.id,
                ResearchEdge.edge_type == "pytest_reuses_duplicate_edge",
            )
            .count()
        )
        assert duplicate_count == 1
    finally:
        session.close()


def test_graph_stats_reports_duplicate_edge_groups() -> None:
    client = TestClient(create_app())
    assert client.get("/health").status_code == 200
    marker = f"pytest-graph-duplicate-stats-{time.time_ns()}"

    session = SessionLocal()
    try:
        source = ResearchNode(
            node_type="pytest_duplicate_stats_source",
            label=f"Pytest duplicate stats source {marker}",
            canonical_key=f"{marker}-source",
            payload_json={"fixture": "duplicate_stats"},
        )
        target = ResearchNode(
            node_type="pytest_duplicate_stats_target",
            label=f"Pytest duplicate stats target {marker}",
            canonical_key=f"{marker}-target",
            payload_json={"fixture": "duplicate_stats"},
        )
        session.add_all([source, target])
        session.flush()
        edge_type = f"pytest_duplicate_stats_{time.time_ns()}"
        session.add_all(
            [
                ResearchEdge(
                    source_node_id=source.id,
                    target_node_id=target.id,
                    edge_type=edge_type,
                    weight=0.4,
                    evidence_ids_json=["evidence-a"],
                    payload_json={"fixture": "duplicate_stats", "index": 1},
                ),
                ResearchEdge(
                    source_node_id=source.id,
                    target_node_id=target.id,
                    edge_type=edge_type,
                    weight=0.6,
                    evidence_ids_json=["evidence-b"],
                    payload_json={"fixture": "duplicate_stats", "index": 2},
                ),
            ]
        )
        session.commit()
    finally:
        session.close()

    stats = client.get("/research/graph/stats")
    assert stats.status_code == 200
    body = stats.json()
    assert body["node_type_counts"]["pytest_duplicate_stats_source"] >= 1
    assert body["node_type_counts"]["pytest_duplicate_stats_target"] >= 1
    assert body["edge_type_counts"][edge_type] == 2
    assert body["duplicate_edge_group_count"] >= 1
    assert body["orphan_edge_count"] == 0


def test_graph_stats_reports_orphan_edges_without_persisting_fixture() -> None:
    client = TestClient(create_app())
    assert client.get("/health").status_code == 200
    marker = f"pytest-graph-orphan-stats-{time.time_ns()}"
    source_id: str | None = None
    edge_id: str | None = None

    session = SessionLocal()
    try:
        source = ResearchNode(
            node_type="pytest_orphan_stats_source",
            label=f"Pytest orphan stats source {marker}",
            canonical_key=f"{marker}-source",
            payload_json={"fixture": "orphan_stats"},
        )
        session.add(source)
        session.flush()
        source_id = source.id
        missing_target_id = f"{marker}-missing-target"
        edge = ResearchEdge(
            source_node_id=source_id,
            target_node_id=missing_target_id,
            edge_type=f"pytest_orphan_stats_{time.time_ns()}",
            weight=0.5,
            evidence_ids_json=[],
            payload_json={"fixture": "orphan_stats"},
        )
        session.add(edge)
        session.commit()
        edge_id = edge.id
    finally:
        session.close()

    try:
        stats = client.get("/research/graph/stats")
        assert stats.status_code == 200
        body = stats.json()
    finally:
        cleanup = SessionLocal()
        try:
            if edge_id is not None:
                cleanup.query(ResearchEdge).filter(ResearchEdge.id == edge_id).delete()
            if source_id is not None:
                cleanup.query(ResearchNode).filter(ResearchNode.id == source_id).delete()
            cleanup.commit()
        finally:
            cleanup.close()

    assert body["orphan_edge_count"] >= 1


def test_context_search_ranking_tie_breaks_by_matched_terms_and_recency() -> None:
    old_item = SimpleNamespace(
        id="old-item",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    new_item = SimpleNamespace(
        id="new-item",
        created_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    more_terms_item = SimpleNamespace(
        id="more-terms-item",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    ranked = RetrievalService(None)._top(
        [
            ScoredItem(item=old_item, score=3.0, matched_terms=["metric"]),
            ScoredItem(item=new_item, score=3.0, matched_terms=["metric"]),
            ScoredItem(
                item=more_terms_item,
                score=3.0,
                matched_terms=["metric", "evidence"],
            ),
        ],
        3,
    )

    assert [scored.item.id for scored in ranked] == [
        "more-terms-item",
        "new-item",
        "old-item",
    ]


def test_health_ready_checks_write_audit_dir_when_enabled(tmp_path, monkeypatch) -> None:
    audit_dir = tmp_path / "audit"
    monkeypatch.setenv("WRITE_AUDIT_ENABLED", "true")
    monkeypatch.setenv("WRITE_AUDIT_DIR", str(audit_dir))

    client = TestClient(create_app())
    response = client.get("/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["checks"]["write_audit_dir"] == {
        "ok": True,
        "enabled": True,
        "path": str(audit_dir),
    }
    assert audit_dir.is_dir()


def test_optional_api_key_guard_protects_research_routes(monkeypatch) -> None:
    monkeypatch.setenv("API_KEY_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_KEY", "pytest-secret")

    client = TestClient(create_app())

    health = client.get("/health")
    missing = client.get("/research/status")
    wrong = client.get("/research/status", headers={"X-Research-Assistant-Key": "wrong"})
    header_ok = client.get(
        "/research/status",
        headers={"X-Research-Assistant-Key": "pytest-secret"},
    )
    bearer_ok = client.get(
        "/research/status",
        headers={"Authorization": "Bearer pytest-secret"},
    )

    assert health.status_code == 200
    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert header_ok.status_code == 200
    assert bearer_ok.status_code == 200


def test_write_operation_audit_jsonl_records_sanitized_metadata(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("WRITE_AUDIT_ENABLED", "true")
    monkeypatch.setenv("WRITE_AUDIT_DIR", str(tmp_path))
    monkeypatch.setenv("API_KEY_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_KEY", "pytest-secret")

    client = TestClient(create_app())
    response = client.put(
        "/research/profile?preview=true",
        headers={
            "X-Research-Assistant-Key": "pytest-secret",
            "X-Research-Assistant-Client": "pytest-workbench",
            "X-Request-ID": "req-audit-1",
        },
        json={"name": "Audit Test Profile", "notes": "do-not-log-body"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-audit-1"

    audit_path = tmp_path / "write-operations.jsonl"
    records = [json.loads(line) for line in audit_path.read_text().splitlines()]
    assert len(records) == 1
    event = records[0]
    assert event["request_id"] == "req-audit-1"
    assert event["actor_type"] == "workbench"
    assert event["actor_label"] == "pytest-workbench"
    assert event["method"] == "PUT"
    assert event["path_template"] == "/research/profile"
    assert event["operation"] == "update"
    assert event["entity_type"] == "profile"
    assert event["status"] == "success"
    assert event["http_status"] == 200
    assert event["policy"] == "direct_api"
    assert event["metadata"]["query_keys"] == ["preview"]
    assert event["metadata"]["api_key_fingerprint"] == (
        "sha256:" + hashlib.sha256(b"pytest-secret").hexdigest()[:12]
    )

    raw_audit = audit_path.read_text()
    assert "pytest-secret" not in raw_audit
    assert "do-not-log-body" not in raw_audit


def test_write_operation_audit_records_failed_api_key_fingerprint(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("WRITE_AUDIT_ENABLED", "true")
    monkeypatch.setenv("WRITE_AUDIT_DIR", str(tmp_path))
    monkeypatch.setenv("API_KEY_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_KEY", "pytest-secret")

    client = TestClient(create_app())
    response = client.put(
        "/research/profile",
        headers={
            "X-Research-Assistant-Key": "wrong-secret",
            "X-Research-Assistant-Client": "pytest-script",
            "X-Request-ID": "req-audit-denied",
        },
        json={"name": "Denied Audit Profile"},
    )

    assert response.status_code == 401

    audit_path = tmp_path / "write-operations.jsonl"
    records = [json.loads(line) for line in audit_path.read_text().splitlines()]
    assert len(records) == 1
    event = records[0]
    assert event["request_id"] == "req-audit-denied"
    assert event["actor_type"] == "api_client"
    assert event["actor_label"] == "pytest-script"
    assert event["method"] == "PUT"
    assert event["status"] == "failure"
    assert event["http_status"] == 401
    assert event["metadata"]["api_key_fingerprint"] == (
        "sha256:" + hashlib.sha256(b"wrong-secret").hexdigest()[:12]
    )

    raw_audit = audit_path.read_text()
    assert "wrong-secret" not in raw_audit
    assert "pytest-secret" not in raw_audit
    assert "Denied Audit Profile" not in raw_audit


def test_write_operation_audit_disabled_by_default(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("WRITE_AUDIT_ENABLED", raising=False)
    monkeypatch.setenv("WRITE_AUDIT_DIR", str(tmp_path))

    client = TestClient(create_app())
    response = client.put(
        "/research/profile",
        json={"name": "No Audit Profile"},
    )

    assert response.status_code == 200
    assert not (tmp_path / "write-operations.jsonl").exists()


def test_write_audit_admin_summary_disabled_by_default(monkeypatch) -> None:
    monkeypatch.setenv("AUDIT_ADMIN_EXPORT_ENABLED", "false")
    monkeypatch.delenv("AUDIT_ADMIN_KEY", raising=False)

    client = TestClient(create_app())
    summary = client.get("/research/admin/write-audit/summary")
    export = client.get("/research/admin/write-audit/export")

    assert summary.status_code == 404
    assert export.status_code == 404


def test_write_audit_admin_summary_requires_separate_admin_key(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AUDIT_ADMIN_EXPORT_ENABLED", "true")
    monkeypatch.setenv("AUDIT_ADMIN_KEY", "pytest-admin")
    monkeypatch.setenv("API_KEY_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_KEY", "pytest-secret")
    monkeypatch.setenv("WRITE_AUDIT_DIR", str(tmp_path))

    client = TestClient(create_app())
    admin_paths = (
        "/research/admin/write-audit/summary",
        "/research/admin/write-audit/export",
    )

    for admin_path in admin_paths:
        admin_only = client.get(
            admin_path,
            headers={"X-Research-Assistant-Admin-Key": "pytest-admin"},
        )
        pilot_only = client.get(
            admin_path,
            headers={"X-Research-Assistant-Key": "pytest-secret"},
        )
        wrong_admin = client.get(
            admin_path,
            headers={
                "X-Research-Assistant-Key": "pytest-secret",
                "X-Research-Assistant-Admin-Key": "wrong-admin",
            },
        )
        ok = client.get(
            admin_path,
            headers={
                "X-Research-Assistant-Key": "pytest-secret",
                "X-Research-Assistant-Admin-Key": "pytest-admin",
            },
        )

        assert admin_only.status_code == 401
        assert pilot_only.status_code == 401
        assert wrong_admin.status_code == 403
        assert ok.status_code == 200

    summary = client.get(
        "/research/admin/write-audit/summary",
        headers={
            "X-Research-Assistant-Key": "pytest-secret",
            "X-Research-Assistant-Admin-Key": "pytest-admin",
        },
    )
    assert summary.json()["audit_file_present"] is False


def test_write_audit_admin_summary_returns_sanitized_aggregates(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AUDIT_ADMIN_EXPORT_ENABLED", "true")
    monkeypatch.setenv("AUDIT_ADMIN_KEY", "pytest-admin")
    monkeypatch.setenv("WRITE_AUDIT_DIR", str(tmp_path))

    audit_path = tmp_path / "write-operations.jsonl"
    audit_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "created_at": "2026-06-12T01:00:00+00:00",
                        "request_id": "req-one",
                        "actor_type": "workbench",
                        "actor_label": "do-not-expose-label",
                        "method": "PUT",
                        "path_template": "/research/profile",
                        "operation": "update",
                        "entity_type": "profile",
                        "status": "success",
                        "http_status": 200,
                        "metadata": {"api_key_fingerprint": "sha256:do-not-expose"},
                    }
                ),
                "not-json",
                json.dumps(
                    {
                        "created_at": "2026-06-12T01:01:00+00:00",
                        "request_id": "req-two",
                        "actor_type": "api_client",
                        "method": "POST",
                        "path_template": "/research/papers/upload",
                        "operation": "upload",
                        "entity_type": "paper",
                        "status": "failure",
                        "http_status": 422,
                        "error_type": "ValidationError",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    client = TestClient(create_app())
    response = client.get(
        "/research/admin/write-audit/summary",
        headers={"X-Research-Assistant-Admin-Key": "pytest-admin"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["audit_file_present"] is True
    assert body["event_count"] == 2
    assert body["total_line_count"] == 3
    assert body["invalid_line_count"] == 1
    assert body["counts_by_operation"] == {"update": 1, "upload": 1}
    assert body["counts_by_entity_type"] == {"paper": 1, "profile": 1}
    assert body["counts_by_status"] == {"failure": 1, "success": 1}
    assert body["counts_by_http_status"] == {"200": 1, "422": 1}
    assert body["counts_by_actor_type"] == {"api_client": 1, "workbench": 1}
    assert body["counts_by_route"] == {
        "/research/papers/upload": 1,
        "/research/profile": 1,
    }
    assert body["counts_by_error_type"] == {"ValidationError": 1}
    assert body["recent_request_ids"] == ["req-one", "req-two"]

    raw_response = response.text
    assert "pytest-admin" not in raw_response
    assert "do-not-expose-label" not in raw_response
    assert "sha256:do-not-expose" not in raw_response


def test_write_audit_admin_export_returns_bounded_sanitized_jsonl(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AUDIT_ADMIN_EXPORT_ENABLED", "true")
    monkeypatch.setenv("AUDIT_ADMIN_KEY", "pytest-admin")
    monkeypatch.setenv("WRITE_AUDIT_DIR", str(tmp_path))

    audit_path = tmp_path / "write-operations.jsonl"
    audit_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "created_at": "2026-06-12T01:00:00+00:00",
                        "request_id": "req-before-window",
                        "operation": "update",
                        "entity_type": "profile",
                        "status": "success",
                        "http_status": 200,
                    }
                ),
                json.dumps(
                    {
                        "created_at": "2026-06-12T01:01:00+00:00",
                        "request_id": "req-export-one",
                        "actor_type": "workbench",
                        "actor_label": "pytest-workbench",
                        "method": "PUT",
                        "path_template": "/research/profile",
                        "operation": "update",
                        "entity_type": "profile",
                        "status": "success",
                        "http_status": 200,
                        "request_body": "do-not-export-body",
                        "api_key": "raw-secret-key",
                        "metadata": {
                            "api_key": "raw-secret-metadata",
                            "api_key_fingerprint": "sha256:abcdef123456",
                            "query_keys": ["preview"],
                            "prompt_text": "do-not-export-prompt",
                        },
                    }
                ),
                json.dumps(
                    {
                        "created_at": "2026-06-12T01:02:00+00:00",
                        "request_id": "req-export-two",
                        "actor_type": "api_client",
                        "method": "POST",
                        "path_template": "/research/papers/upload",
                        "operation": "upload",
                        "entity_type": "paper",
                        "status": "failure",
                        "http_status": 422,
                        "error_type": "ValidationError",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    client = TestClient(create_app())
    response = client.get(
        "/research/admin/write-audit/export",
        params={
            "start_created_at": "2026-06-12T01:01:00+00:00",
            "end_created_at": "2026-06-12T01:02:00+00:00",
            "max_records": "1",
        },
        headers={"X-Research-Assistant-Admin-Key": "pytest-admin"},
    )

    assert response.status_code == 200
    assert response.headers["X-Research-Assistant-Export-Records"] == "1"
    exported = [json.loads(line) for line in response.text.splitlines()]
    assert len(exported) == 1
    assert exported[0]["request_id"] == "req-export-one"
    assert exported[0]["metadata"] == {
        "api_key_fingerprint": "sha256:abcdef123456",
        "query_keys": ["preview"],
    }

    raw_response = response.text
    assert "raw-secret-key" not in raw_response
    assert "raw-secret-metadata" not in raw_response
    assert "do-not-export-body" not in raw_response
    assert "do-not-export-prompt" not in raw_response
    assert "req-before-window" not in raw_response
    assert "req-export-two" not in raw_response


def test_deployment_artifacts_document_customer_runtime() -> None:
    root = Path(__file__).resolve().parents[1]
    dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
    compose = (root / "docker-compose.yml").read_text(encoding="utf-8")
    deployment = (root / "docs" / "deployment.md").read_text(encoding="utf-8")
    migration = (root / "docs" / "database_migration_strategy.md").read_text(encoding="utf-8")
    admin_policy = (root / "docs" / "admin_authorization_policy.md").read_text(encoding="utf-8")
    env_example = (root / ".env.example").read_text(encoding="utf-8")

    assert "uvicorn backend.app:app" in dockerfile
    assert "API_KEY_AUTH_ENABLED" in compose
    assert "/health/ready" in compose
    assert "X-Research-Assistant-Key" in deployment
    assert "WRITE_AUDIT_ENABLED" in deployment
    assert "admin_authorization_policy.md" in deployment
    assert "database_migration_strategy.md" in deployment
    assert "MCP bridge" in deployment
    assert "No automatic migration execution" in migration
    assert "AUDIT_ADMIN_EXPORT_ENABLED" in env_example
    assert "regular pilot API key is not admin authorization" in admin_policy


def test_research_status() -> None:
    client = TestClient(create_app())
    response = client.get("/research/status")
    assert response.status_code == 200
    body = response.json()
    assert body["phase"] == "phase_0_foundation"
    assert "sqlalchemy_models" in body["implemented_capabilities"]
    assert "upload_size_extension_guard" in body["implemented_capabilities"]
    assert "upload_content_sniffing_guard" in body["implemented_capabilities"]
    assert "research_profile_constraints" in body["implemented_capabilities"]
    assert "research_plan_snapshots" in body["implemented_capabilities"]
    assert "research_plan_task_generation" in body["implemented_capabilities"]
    assert "research_plan_progress_integration" in body["implemented_capabilities"]
    assert "research_plan_progress_tracking" in body["implemented_capabilities"]
    assert "tool_manifest" in body["implemented_capabilities"]
    assert "workflow_job_cancel_retry_controls" in body["implemented_capabilities"]
    assert "task_execution_controls" in body["implemented_capabilities"]
    assert "workbench_task_board_controls" in body["implemented_capabilities"]
    assert "idea_activity_timeline" in body["implemented_capabilities"]
    assert "idea_research_packet" in body["implemented_capabilities"]
    assert "idea_readiness_scoring" in body["implemented_capabilities"]
    assert "idea_quality_gate" in body["implemented_capabilities"]
    assert "idea_quality_gate_task_generation" in body["implemented_capabilities"]
    assert "idea_readiness_task_generation" in body["implemented_capabilities"]
    assert "project_readiness_overview" in body["implemented_capabilities"]
    assert "project_quality_gate_overview" in body["implemented_capabilities"]
    assert "project_quality_gate_task_generation" in body["implemented_capabilities"]
    assert "research_opportunity_radar" in body["implemented_capabilities"]
    assert "opportunity_radar_task_generation" in body["implemented_capabilities"]
    assert "idea_artifact_bundle_export" in body["implemented_capabilities"]
    assert "project_handoff_bundle_export" in body["implemented_capabilities"]
    assert "project_bundle_readiness" in body["implemented_capabilities"]
    assert "project_bundle_readiness_task_generation" in body["implemented_capabilities"]
    assert "project_bundle_readiness_snapshots" in body["implemented_capabilities"]
    assert "project_bundle_readiness_snapshot_comparison" in body["implemented_capabilities"]
    assert (
        "project_bundle_readiness_snapshot_comparison_task_generation"
        in body["implemented_capabilities"]
    )
    assert "project_bundle_release_notes" in body["implemented_capabilities"]
    assert "project_bundle_release_task_generation" in body["implemented_capabilities"]
    assert "project_bundle_release_progress_tracking" in body["implemented_capabilities"]
    assert "project_bundle_release_feedback_tracking" in body["implemented_capabilities"]
    assert "project_bundle_release_feedback_task_generation" in body["implemented_capabilities"]
    assert "project_bundle_release_closeout_tracking" in body["implemented_capabilities"]
    assert "project_bundle_release_closeout_task_generation" in body["implemented_capabilities"]
    assert "project_bundle_release_acceptance_packets" in body["implemented_capabilities"]
    assert "project_bundle_release_acceptance_packet_snapshots" in body["implemented_capabilities"]
    assert (
        "project_bundle_release_acceptance_packet_snapshot_comparison"
        in body["implemented_capabilities"]
    )
    assert (
        "project_bundle_release_acceptance_packet_snapshot_comparison_task_generation"
        in body["implemented_capabilities"]
    )
    assert "project_bundle_release_review_sessions" in body["implemented_capabilities"]
    assert (
        "project_bundle_release_review_session_task_generation" in body["implemented_capabilities"]
    )
    assert "project_bundle_release_review_outcomes" in body["implemented_capabilities"]
    assert (
        "project_bundle_release_review_outcome_task_generation" in body["implemented_capabilities"]
    )
    assert (
        "project_bundle_release_review_outcome_progress_tracking"
        in body["implemented_capabilities"]
    )
    assert "project_bundle_release_review_outcome_signoffs" in body["implemented_capabilities"]
    assert "advisor_brief_execution_context" in body["implemented_capabilities"]
    assert "advisor_brief_triage_context" in body["implemented_capabilities"]
    assert "advisor_brief_triage_snapshot_comparison_context" in body["implemented_capabilities"]
    assert "mcp_stdio_http_bridge" in body["implemented_capabilities"]
    assert "mcp_bridge_policy_controls" in body["implemented_capabilities"]
    assert "write_operation_audit_jsonl" in body["implemented_capabilities"]
    assert "write_operation_audit_admin_summary" in body["implemented_capabilities"]
    assert "write_operation_audit_admin_export" in body["implemented_capabilities"]
    assert "write_operation_audit_readiness_check" in body["implemented_capabilities"]
    assert "mcp_tool_bridge_spec" in body["implemented_capabilities"]
    assert "idea_decision_memos" in body["implemented_capabilities"]
    assert "idea_assumption_audits" in body["implemented_capabilities"]
    assert "idea_evidence_ledgers" in body["implemented_capabilities"]
    assert "idea_evidence_task_generation" in body["implemented_capabilities"]
    assert "claim_evidence_graph_links" in body["implemented_capabilities"]
    assert "claim_validation_packets" in body["implemented_capabilities"]
    assert "claim_validation_queue" in body["implemented_capabilities"]
    assert "claim_validation_queue_task_generation" in body["implemented_capabilities"]
    assert "claim_validation_result_tracking" in body["implemented_capabilities"]
    assert "claim_validation_result_decision_signals" in body["implemented_capabilities"]
    assert "claim_validation_result_ranking_adjustments" in body["implemented_capabilities"]
    assert "project_onboarding_readiness" in body["implemented_capabilities"]
    assert "project_onboarding_setup_wizard" in body["implemented_capabilities"]
    assert "project_onboarding_task_generation" in body["implemented_capabilities"]
    assert "project_onboarding_progress_tracking" in body["implemented_capabilities"]
    assert "project_pilot_status_report" in body["implemented_capabilities"]
    assert "project_pilot_report_snapshots" in body["implemented_capabilities"]
    assert "project_pilot_report_snapshot_comparison" in body["implemented_capabilities"]
    assert (
        "project_pilot_report_snapshot_comparison_task_generation"
        in body["implemented_capabilities"]
    )
    assert "project_pilot_report_snapshot_task_generation" in body["implemented_capabilities"]
    assert "project_cockpit_dashboard" in body["implemented_capabilities"]
    assert "project_cockpit_task_generation" in body["implemented_capabilities"]
    assert "project_advisor_chat" in body["implemented_capabilities"]
    assert "project_advisor_chat_task_generation" in body["implemented_capabilities"]
    assert "project_advisor_action_sessions" in body["implemented_capabilities"]
    assert "advisor_brief_evidence_context" in body["implemented_capabilities"]
    assert "advisor_brief_claim_validation_context" in body["implemented_capabilities"]
    assert "project_triage_brief" in body["implemented_capabilities"]
    assert "project_triage_task_generation" in body["implemented_capabilities"]
    assert "project_triage_snapshots" in body["implemented_capabilities"]
    assert "project_triage_snapshot_comparison" in body["implemented_capabilities"]
    assert "project_triage_snapshot_comparison_task_generation" in body["implemented_capabilities"]
    assert "external_novelty_refresh" in body["implemented_capabilities"]
    assert "novelty_check_task_generation" in body["implemented_capabilities"]


def test_tool_manifest_lists_mcp_ready_research_tools() -> None:
    client = TestClient(create_app())
    response = client.get("/research/tools/manifest")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "Research Assistant Agent"
    assert isinstance(body["mcp_enabled"], bool)
    names = {tool["name"] for tool in body["tools"]}
    assert "upload_paper" in names
    assert "search_research_context" in names
    assert "get_graph_stats" in names
    assert "get_research_profile" in names
    assert "update_research_profile" in names
    assert "create_research_plan" in names
    assert "create_tasks_from_research_plan" in names
    assert "get_research_plan_progress" in names
    assert "get_project_progress_overview" in names
    assert "get_project_onboarding_readiness" in names
    assert "run_project_setup_wizard" in names
    assert "create_tasks_from_project_onboarding" in names
    assert "get_project_onboarding_progress" in names
    assert "get_project_pilot_report" in names
    assert "create_project_pilot_report_snapshot" in names
    assert "list_project_pilot_report_snapshots" in names
    assert "get_project_pilot_report_snapshot" in names
    assert "export_project_pilot_report_snapshot_markdown" in names
    assert "compare_project_pilot_report_snapshots" in names
    assert "export_project_pilot_report_snapshot_comparison_markdown" in names
    assert "create_tasks_from_project_pilot_report_snapshot_comparison" in names
    assert "create_tasks_from_project_pilot_report_snapshot" in names
    assert "get_project_cockpit" in names
    assert "export_project_cockpit_markdown" in names
    assert "create_tasks_from_project_cockpit" in names
    assert "ask_project_advisor" in names
    assert "create_tasks_from_project_advisor_chat" in names
    assert "run_project_advisor_action_session" in names
    assert "get_project_triage_brief" in names
    assert "export_project_triage_brief_markdown" in names
    assert "create_tasks_from_project_triage_brief" in names
    assert "create_project_triage_snapshot" in names
    assert "list_project_triage_snapshots" in names
    assert "compare_project_triage_snapshots" in names
    assert "export_project_triage_snapshot_comparison_markdown" in names
    assert "create_tasks_from_project_triage_snapshot_comparison" in names
    assert "get_project_triage_snapshot" in names
    assert "export_project_triage_snapshot_markdown" in names
    assert "get_mcp_tool_spec" in names
    assert "get_idea_research_packet" in names
    assert "get_idea_timeline" in names
    assert "export_idea_bundle" in names
    assert "export_project_bundle" in names
    assert "get_project_bundle_readiness" in names
    assert "create_tasks_from_project_bundle_readiness" in names
    assert "create_project_bundle_readiness_snapshot" in names
    assert "list_project_bundle_readiness_snapshots" in names
    assert "get_project_bundle_readiness_snapshot" in names
    assert "export_project_bundle_readiness_snapshot_markdown" in names
    assert "compare_project_bundle_readiness_snapshots" in names
    assert "export_project_bundle_readiness_snapshot_comparison_markdown" in names
    assert "create_tasks_from_project_bundle_readiness_snapshot_comparison" in names
    assert "create_project_bundle_release_note" in names
    assert "list_project_bundle_release_notes" in names
    assert "get_project_bundle_release_note" in names
    assert "export_project_bundle_release_note_markdown" in names
    assert "create_tasks_from_project_bundle_release_note" in names
    assert "get_project_bundle_release_progress" in names
    assert "record_project_bundle_release_feedback" in names
    assert "list_project_bundle_release_feedback" in names
    assert "get_project_bundle_release_feedback" in names
    assert "export_project_bundle_release_feedback_markdown" in names
    assert "create_tasks_from_project_bundle_release_feedback" in names
    assert "get_project_bundle_release_closeout" in names
    assert "create_tasks_from_project_bundle_release_closeout" in names
    assert "get_project_bundle_release_acceptance_packet" in names
    assert "create_project_bundle_release_acceptance_packet_snapshot" in names
    assert "list_project_bundle_release_acceptance_packet_snapshots" in names
    assert "get_project_bundle_release_acceptance_packet_snapshot" in names
    assert "export_project_bundle_release_acceptance_packet_snapshot_markdown" in names
    assert "compare_project_bundle_release_acceptance_packet_snapshots" in names
    assert "export_project_bundle_release_acceptance_packet_snapshot_comparison_markdown" in names
    assert "create_tasks_from_project_bundle_release_acceptance_packet_snapshot_comparison" in names
    assert "get_project_bundle_release_review_session" in names
    assert "create_tasks_from_project_bundle_release_review_session" in names
    assert "record_project_bundle_release_review_outcome" in names
    assert "list_project_bundle_release_review_outcomes" in names
    assert "get_project_bundle_release_review_outcome" in names
    assert "export_project_bundle_release_review_outcome_markdown" in names
    assert "create_tasks_from_project_bundle_release_review_outcome" in names
    assert "get_project_bundle_release_review_outcome_progress" in names
    assert "record_project_bundle_release_review_outcome_signoff" in names
    assert "list_project_bundle_release_review_outcome_signoffs" in names
    assert "get_project_bundle_release_review_outcome_signoff" in names
    assert "export_project_bundle_release_review_outcome_signoff_markdown" in names
    assert "get_idea_readiness" in names
    assert "get_idea_quality_gate" in names
    assert "create_tasks_from_idea_quality_gate" in names
    assert "create_tasks_from_idea_readiness" in names
    assert "list_research_tasks" in names
    assert "update_research_task" in names
    assert "get_project_readiness_overview" in names
    assert "get_project_quality_gate_overview" in names
    assert "create_tasks_from_project_quality_gate" in names
    assert "get_research_opportunity_radar" in names
    assert "create_tasks_from_research_opportunity_radar" in names
    assert "create_idea_decision_memo" in names
    assert "create_tasks_from_idea_decision_memo" in names
    assert "create_idea_assumption_audit" in names
    assert "create_idea_evidence_ledger" in names
    assert "list_idea_evidence_ledgers" in names
    assert "create_tasks_from_idea_evidence_ledger" in names
    assert "get_idea_claim_validation_packet" in names
    assert "get_claim_validation_queue" in names
    assert "create_tasks_from_claim_validation_queue" in names
    assert "record_claim_validation_result" in names
    assert "refresh_idea_novelty_search" in names
    assert "create_tasks_from_idea_novelty_check" in names
    assert "create_advisor_brief" in names
    assert "analyze_experiment_run" in names
    assert "cancel_job" in names
    assert "retry_job" in names
    assert any(tool["side_effect"] for tool in body["tools"])


def test_tool_bridge_spec_maps_manifest_to_http_tool_schemas() -> None:
    client = TestClient(create_app())
    response = client.get("/research/tools/mcp-spec")
    assert response.status_code == 200
    body = response.json()
    assert body["protocol"] == "research-assistant-http-tool-bridge.v1"
    tools = {tool["name"]: tool for tool in body["tools"]}
    assert "run_literature_to_ideas_workflow" in tools
    assert "export_idea_bundle" in tools

    upload = tools["upload_paper"]
    assert upload["input_schema"]["properties"]["file_path"]["type"] == "string"
    assert upload["http"]["content_type"] == "multipart/form-data"

    bundle = tools["export_idea_bundle"]
    assert bundle["input_schema"]["required"] == ["idea_id"]
    assert bundle["input_schema"]["properties"]["idea_id"]["type"] == "string"
    assert bundle["annotations"]["readOnlyHint"] is True
    assert bundle["http"]["path"] == "/research/ideas/{idea_id}/export/bundle"

    project_bundle_readiness = tools["get_project_bundle_readiness"]
    assert project_bundle_readiness["http"]["method"] == "GET"
    assert project_bundle_readiness["http"]["path"] == "/research/export/project-bundle/readiness"
    assert project_bundle_readiness["annotations"]["readOnlyHint"] is True

    project_bundle_release = tools["create_project_bundle_release_note"]
    assert project_bundle_release["http"]["method"] == "POST"
    assert project_bundle_release["http"]["path"] == "/research/export/project-bundle/releases"
    assert project_bundle_release["input_schema"]["required"] == ["body"]
    assert project_bundle_release["annotations"]["sideEffectHint"] is True

    project_bundle_release_list = tools["list_project_bundle_release_notes"]
    assert project_bundle_release_list["http"]["method"] == "GET"
    assert project_bundle_release_list["http"]["path"] == "/research/export/project-bundle/releases"
    assert project_bundle_release_list["annotations"]["readOnlyHint"] is True

    project_bundle_release_tasks = tools["create_tasks_from_project_bundle_release_note"]
    assert project_bundle_release_tasks["http"]["method"] == "POST"
    assert (
        project_bundle_release_tasks["http"]["path"]
        == "/research/export/project-bundle/releases/{release_id}/tasks"
    )
    assert project_bundle_release_tasks["input_schema"]["required"] == ["release_id", "body"]
    assert project_bundle_release_tasks["annotations"]["sideEffectHint"] is True

    project_bundle_release_progress = tools["get_project_bundle_release_progress"]
    assert project_bundle_release_progress["http"]["method"] == "GET"
    assert (
        project_bundle_release_progress["http"]["path"]
        == "/research/export/project-bundle/releases/{release_id}/progress"
    )
    assert project_bundle_release_progress["input_schema"]["required"] == ["release_id"]
    assert project_bundle_release_progress["annotations"]["readOnlyHint"] is True

    project_bundle_release_feedback = tools["record_project_bundle_release_feedback"]
    assert project_bundle_release_feedback["http"]["method"] == "POST"
    assert (
        project_bundle_release_feedback["http"]["path"]
        == "/research/export/project-bundle/releases/{release_id}/feedback"
    )
    assert project_bundle_release_feedback["input_schema"]["required"] == ["release_id", "body"]
    assert project_bundle_release_feedback["annotations"]["sideEffectHint"] is True

    project_bundle_release_feedback_list = tools["list_project_bundle_release_feedback"]
    assert project_bundle_release_feedback_list["http"]["method"] == "GET"
    assert (
        project_bundle_release_feedback_list["http"]["path"]
        == "/research/export/project-bundle/releases/{release_id}/feedback"
    )
    assert project_bundle_release_feedback_list["input_schema"]["required"] == ["release_id"]
    assert project_bundle_release_feedback_list["annotations"]["readOnlyHint"] is True

    project_bundle_release_feedback_tasks = tools[
        "create_tasks_from_project_bundle_release_feedback"
    ]
    assert project_bundle_release_feedback_tasks["http"]["method"] == "POST"
    assert (
        project_bundle_release_feedback_tasks["http"]["path"]
        == "/research/export/project-bundle/releases/{release_id}/feedback/{feedback_id}/tasks"
    )
    assert project_bundle_release_feedback_tasks["input_schema"]["required"] == [
        "release_id",
        "feedback_id",
        "body",
    ]
    assert project_bundle_release_feedback_tasks["annotations"]["sideEffectHint"] is True

    project_bundle_release_closeout = tools["get_project_bundle_release_closeout"]
    assert project_bundle_release_closeout["http"]["method"] == "GET"
    assert (
        project_bundle_release_closeout["http"]["path"]
        == "/research/export/project-bundle/releases/{release_id}/closeout"
    )
    assert project_bundle_release_closeout["input_schema"]["required"] == ["release_id"]
    assert project_bundle_release_closeout["annotations"]["readOnlyHint"] is True

    project_bundle_release_closeout_tasks = tools[
        "create_tasks_from_project_bundle_release_closeout"
    ]
    assert project_bundle_release_closeout_tasks["http"]["method"] == "POST"
    assert (
        project_bundle_release_closeout_tasks["http"]["path"]
        == "/research/export/project-bundle/releases/{release_id}/closeout/tasks"
    )
    assert project_bundle_release_closeout_tasks["input_schema"]["required"] == [
        "release_id",
        "body",
    ]
    assert project_bundle_release_closeout_tasks["annotations"]["sideEffectHint"] is True

    project_bundle_release_acceptance_packet = tools["get_project_bundle_release_acceptance_packet"]
    assert project_bundle_release_acceptance_packet["http"]["method"] == "GET"
    assert (
        project_bundle_release_acceptance_packet["http"]["path"]
        == "/research/export/project-bundle/releases/{release_id}/acceptance-packet"
    )
    assert project_bundle_release_acceptance_packet["input_schema"]["required"] == ["release_id"]
    assert project_bundle_release_acceptance_packet["annotations"]["readOnlyHint"] is True

    project_bundle_release_acceptance_snapshot = tools[
        "create_project_bundle_release_acceptance_packet_snapshot"
    ]
    assert project_bundle_release_acceptance_snapshot["http"]["method"] == "POST"
    assert (
        project_bundle_release_acceptance_snapshot["http"]["path"]
        == "/research/export/project-bundle/releases/{release_id}/acceptance-packet/snapshots"
    )
    assert project_bundle_release_acceptance_snapshot["input_schema"]["required"] == [
        "release_id",
        "body",
    ]
    assert project_bundle_release_acceptance_snapshot["annotations"]["sideEffectHint"] is True

    project_bundle_release_acceptance_snapshot_list = tools[
        "list_project_bundle_release_acceptance_packet_snapshots"
    ]
    assert project_bundle_release_acceptance_snapshot_list["http"]["method"] == "GET"
    assert (
        project_bundle_release_acceptance_snapshot_list["http"]["path"]
        == "/research/export/project-bundle/releases/{release_id}/acceptance-packet/snapshots"
    )
    assert project_bundle_release_acceptance_snapshot_list["input_schema"]["required"] == [
        "release_id"
    ]
    assert project_bundle_release_acceptance_snapshot_list["annotations"]["readOnlyHint"] is True

    project_bundle_release_acceptance_snapshot_detail = tools[
        "get_project_bundle_release_acceptance_packet_snapshot"
    ]
    assert project_bundle_release_acceptance_snapshot_detail["http"]["method"] == "GET"
    assert (
        project_bundle_release_acceptance_snapshot_detail["http"]["path"]
        == "/research/export/project-bundle/releases/{release_id}/acceptance-packet/"
        "snapshots/{snapshot_id}"
    )
    assert project_bundle_release_acceptance_snapshot_detail["input_schema"]["required"] == [
        "release_id",
        "snapshot_id",
    ]
    assert project_bundle_release_acceptance_snapshot_detail["annotations"]["readOnlyHint"] is True

    project_bundle_release_acceptance_snapshot_markdown = tools[
        "export_project_bundle_release_acceptance_packet_snapshot_markdown"
    ]
    assert project_bundle_release_acceptance_snapshot_markdown["http"]["method"] == "GET"
    assert (
        project_bundle_release_acceptance_snapshot_markdown["http"]["path"]
        == "/research/export/project-bundle/releases/{release_id}/acceptance-packet/"
        "snapshots/{snapshot_id}/export/markdown"
    )
    assert project_bundle_release_acceptance_snapshot_markdown["input_schema"]["required"] == [
        "release_id",
        "snapshot_id",
    ]
    assert (
        project_bundle_release_acceptance_snapshot_markdown["annotations"]["readOnlyHint"] is True
    )

    project_bundle_release_acceptance_snapshot_compare = tools[
        "compare_project_bundle_release_acceptance_packet_snapshots"
    ]
    assert project_bundle_release_acceptance_snapshot_compare["http"]["method"] == "POST"
    assert (
        project_bundle_release_acceptance_snapshot_compare["http"]["path"]
        == "/research/export/project-bundle/releases/{release_id}/acceptance-packet/"
        "snapshots/compare"
    )
    assert project_bundle_release_acceptance_snapshot_compare["input_schema"]["required"] == [
        "release_id",
        "body",
    ]
    assert (
        project_bundle_release_acceptance_snapshot_compare["annotations"]["sideEffectHint"] is False
    )

    project_bundle_release_acceptance_snapshot_compare_markdown = tools[
        "export_project_bundle_release_acceptance_packet_snapshot_comparison_markdown"
    ]
    assert project_bundle_release_acceptance_snapshot_compare_markdown["http"]["method"] == "POST"
    assert (
        project_bundle_release_acceptance_snapshot_compare_markdown["http"]["path"]
        == "/research/export/project-bundle/releases/{release_id}/acceptance-packet/"
        "snapshots/compare/export/markdown"
    )
    assert project_bundle_release_acceptance_snapshot_compare_markdown["input_schema"][
        "required"
    ] == ["release_id", "body"]
    assert (
        project_bundle_release_acceptance_snapshot_compare_markdown["annotations"]["sideEffectHint"]
        is False
    )

    project_bundle_release_acceptance_snapshot_compare_tasks = tools[
        "create_tasks_from_project_bundle_release_acceptance_packet_snapshot_comparison"
    ]
    assert project_bundle_release_acceptance_snapshot_compare_tasks["http"]["method"] == "POST"
    assert (
        project_bundle_release_acceptance_snapshot_compare_tasks["http"]["path"]
        == "/research/export/project-bundle/releases/{release_id}/acceptance-packet/"
        "snapshots/compare/tasks"
    )
    assert project_bundle_release_acceptance_snapshot_compare_tasks["input_schema"]["required"] == [
        "release_id",
        "body",
    ]
    assert (
        project_bundle_release_acceptance_snapshot_compare_tasks["annotations"]["sideEffectHint"]
        is True
    )

    project_bundle_release_review_session = tools["get_project_bundle_release_review_session"]
    assert project_bundle_release_review_session["http"]["method"] == "GET"
    assert (
        project_bundle_release_review_session["http"]["path"]
        == "/research/export/project-bundle/releases/{release_id}/review-session"
    )
    assert project_bundle_release_review_session["input_schema"]["required"] == ["release_id"]
    assert project_bundle_release_review_session["annotations"]["readOnlyHint"] is True

    project_bundle_release_review_session_tasks = tools[
        "create_tasks_from_project_bundle_release_review_session"
    ]
    assert project_bundle_release_review_session_tasks["http"]["method"] == "POST"
    assert (
        project_bundle_release_review_session_tasks["http"]["path"]
        == "/research/export/project-bundle/releases/{release_id}/review-session/tasks"
    )
    assert project_bundle_release_review_session_tasks["input_schema"]["required"] == [
        "release_id",
        "body",
    ]
    assert project_bundle_release_review_session_tasks["annotations"]["sideEffectHint"] is True

    project_bundle_release_review_outcome = tools["record_project_bundle_release_review_outcome"]
    assert project_bundle_release_review_outcome["http"]["method"] == "POST"
    assert (
        project_bundle_release_review_outcome["http"]["path"]
        == "/research/export/project-bundle/releases/{release_id}/review-session/outcomes"
    )
    assert project_bundle_release_review_outcome["input_schema"]["required"] == [
        "release_id",
        "body",
    ]
    assert project_bundle_release_review_outcome["annotations"]["sideEffectHint"] is True

    project_bundle_release_review_outcome_list = tools[
        "list_project_bundle_release_review_outcomes"
    ]
    assert project_bundle_release_review_outcome_list["http"]["method"] == "GET"
    assert (
        project_bundle_release_review_outcome_list["http"]["path"]
        == "/research/export/project-bundle/releases/{release_id}/review-session/outcomes"
    )
    assert project_bundle_release_review_outcome_list["input_schema"]["required"] == ["release_id"]
    assert project_bundle_release_review_outcome_list["annotations"]["readOnlyHint"] is True

    project_bundle_release_review_outcome_detail = tools[
        "get_project_bundle_release_review_outcome"
    ]
    assert project_bundle_release_review_outcome_detail["http"]["method"] == "GET"
    assert (
        project_bundle_release_review_outcome_detail["http"]["path"]
        == "/research/export/project-bundle/releases/{release_id}/review-session/"
        "outcomes/{outcome_id}"
    )
    assert project_bundle_release_review_outcome_detail["input_schema"]["required"] == [
        "release_id",
        "outcome_id",
    ]
    assert project_bundle_release_review_outcome_detail["annotations"]["readOnlyHint"] is True

    project_bundle_release_review_outcome_markdown = tools[
        "export_project_bundle_release_review_outcome_markdown"
    ]
    assert project_bundle_release_review_outcome_markdown["http"]["method"] == "GET"
    assert (
        project_bundle_release_review_outcome_markdown["http"]["path"]
        == "/research/export/project-bundle/releases/{release_id}/review-session/"
        "outcomes/{outcome_id}/export/markdown"
    )
    assert project_bundle_release_review_outcome_markdown["input_schema"]["required"] == [
        "release_id",
        "outcome_id",
    ]
    assert project_bundle_release_review_outcome_markdown["annotations"]["readOnlyHint"] is True

    project_bundle_release_review_outcome_tasks = tools[
        "create_tasks_from_project_bundle_release_review_outcome"
    ]
    assert project_bundle_release_review_outcome_tasks["http"]["method"] == "POST"
    assert (
        project_bundle_release_review_outcome_tasks["http"]["path"]
        == "/research/export/project-bundle/releases/{release_id}/review-session/"
        "outcomes/{outcome_id}/tasks"
    )
    assert project_bundle_release_review_outcome_tasks["input_schema"]["required"] == [
        "release_id",
        "outcome_id",
        "body",
    ]
    assert project_bundle_release_review_outcome_tasks["annotations"]["sideEffectHint"] is True

    project_bundle_release_review_outcome_progress = tools[
        "get_project_bundle_release_review_outcome_progress"
    ]
    assert project_bundle_release_review_outcome_progress["http"]["method"] == "GET"
    assert (
        project_bundle_release_review_outcome_progress["http"]["path"]
        == "/research/export/project-bundle/releases/{release_id}/review-session/"
        "outcomes/{outcome_id}/progress"
    )
    assert project_bundle_release_review_outcome_progress["input_schema"]["required"] == [
        "release_id",
        "outcome_id",
    ]
    assert project_bundle_release_review_outcome_progress["annotations"]["readOnlyHint"] is True

    project_bundle_release_review_outcome_signoff = tools[
        "record_project_bundle_release_review_outcome_signoff"
    ]
    assert project_bundle_release_review_outcome_signoff["http"]["method"] == "POST"
    assert (
        project_bundle_release_review_outcome_signoff["http"]["path"]
        == "/research/export/project-bundle/releases/{release_id}/review-session/"
        "outcomes/{outcome_id}/signoffs"
    )
    assert project_bundle_release_review_outcome_signoff["input_schema"]["required"] == [
        "release_id",
        "outcome_id",
        "body",
    ]
    assert project_bundle_release_review_outcome_signoff["annotations"]["sideEffectHint"] is True

    project_bundle_release_review_outcome_signoff_list = tools[
        "list_project_bundle_release_review_outcome_signoffs"
    ]
    assert project_bundle_release_review_outcome_signoff_list["http"]["method"] == "GET"
    assert (
        project_bundle_release_review_outcome_signoff_list["http"]["path"]
        == "/research/export/project-bundle/releases/{release_id}/review-session/"
        "outcomes/{outcome_id}/signoffs"
    )
    assert project_bundle_release_review_outcome_signoff_list["input_schema"]["required"] == [
        "release_id",
        "outcome_id",
    ]
    assert project_bundle_release_review_outcome_signoff_list["annotations"]["readOnlyHint"] is True

    project_bundle_release_review_outcome_signoff_detail = tools[
        "get_project_bundle_release_review_outcome_signoff"
    ]
    assert project_bundle_release_review_outcome_signoff_detail["http"]["method"] == "GET"
    assert (
        project_bundle_release_review_outcome_signoff_detail["http"]["path"]
        == "/research/export/project-bundle/releases/{release_id}/review-session/"
        "outcomes/{outcome_id}/signoffs/{signoff_id}"
    )
    assert project_bundle_release_review_outcome_signoff_detail["input_schema"]["required"] == [
        "release_id",
        "outcome_id",
        "signoff_id",
    ]
    assert (
        project_bundle_release_review_outcome_signoff_detail["annotations"]["readOnlyHint"] is True
    )

    project_bundle_release_review_outcome_signoff_markdown = tools[
        "export_project_bundle_release_review_outcome_signoff_markdown"
    ]
    assert project_bundle_release_review_outcome_signoff_markdown["http"]["method"] == "GET"
    assert (
        project_bundle_release_review_outcome_signoff_markdown["http"]["path"]
        == "/research/export/project-bundle/releases/{release_id}/review-session/"
        "outcomes/{outcome_id}/signoffs/{signoff_id}/export/markdown"
    )
    assert project_bundle_release_review_outcome_signoff_markdown["input_schema"]["required"] == [
        "release_id",
        "outcome_id",
        "signoff_id",
    ]
    assert (
        project_bundle_release_review_outcome_signoff_markdown["annotations"]["readOnlyHint"]
        is True
    )

    project_bundle_readiness_tasks = tools["create_tasks_from_project_bundle_readiness"]
    assert project_bundle_readiness_tasks["http"]["method"] == "POST"
    assert (
        project_bundle_readiness_tasks["http"]["path"]
        == "/research/export/project-bundle/readiness/tasks"
    )
    assert project_bundle_readiness_tasks["input_schema"]["required"] == ["body"]
    assert project_bundle_readiness_tasks["annotations"]["sideEffectHint"] is True

    project_bundle_readiness_snapshot = tools["create_project_bundle_readiness_snapshot"]
    assert project_bundle_readiness_snapshot["http"]["method"] == "POST"
    assert (
        project_bundle_readiness_snapshot["http"]["path"]
        == "/research/export/project-bundle/readiness/snapshots"
    )
    assert project_bundle_readiness_snapshot["input_schema"]["required"] == ["body"]
    assert project_bundle_readiness_snapshot["annotations"]["sideEffectHint"] is True

    project_bundle_readiness_snapshot_list = tools["list_project_bundle_readiness_snapshots"]
    assert project_bundle_readiness_snapshot_list["http"]["method"] == "GET"
    assert (
        project_bundle_readiness_snapshot_list["http"]["path"]
        == "/research/export/project-bundle/readiness/snapshots"
    )
    assert project_bundle_readiness_snapshot_list["annotations"]["readOnlyHint"] is True

    project_bundle_readiness_snapshot_compare = tools["compare_project_bundle_readiness_snapshots"]
    assert project_bundle_readiness_snapshot_compare["http"]["method"] == "POST"
    assert (
        project_bundle_readiness_snapshot_compare["http"]["path"]
        == "/research/export/project-bundle/readiness/snapshots/compare"
    )
    assert project_bundle_readiness_snapshot_compare["input_schema"]["required"] == ["body"]
    assert project_bundle_readiness_snapshot_compare["annotations"]["sideEffectHint"] is False

    project_bundle_readiness_snapshot_compare_export = tools[
        "export_project_bundle_readiness_snapshot_comparison_markdown"
    ]
    assert project_bundle_readiness_snapshot_compare_export["http"]["method"] == "POST"
    assert (
        project_bundle_readiness_snapshot_compare_export["http"]["path"]
        == "/research/export/project-bundle/readiness/snapshots/compare/export/markdown"
    )
    assert (
        project_bundle_readiness_snapshot_compare_export["annotations"]["sideEffectHint"] is False
    )

    project_bundle_readiness_snapshot_compare_tasks = tools[
        "create_tasks_from_project_bundle_readiness_snapshot_comparison"
    ]
    assert project_bundle_readiness_snapshot_compare_tasks["http"]["method"] == "POST"
    assert (
        project_bundle_readiness_snapshot_compare_tasks["http"]["path"]
        == "/research/export/project-bundle/readiness/snapshots/compare/tasks"
    )
    assert project_bundle_readiness_snapshot_compare_tasks["input_schema"]["required"] == ["body"]
    assert project_bundle_readiness_snapshot_compare_tasks["annotations"]["sideEffectHint"] is True

    cancel = tools["cancel_job"]
    assert cancel["side_effect"] is True
    assert cancel["annotations"]["destructiveHint"] is True

    update_profile = tools["update_research_profile"]
    assert update_profile["http"]["method"] == "PUT"
    assert update_profile["input_schema"]["required"] == ["body"]
    assert update_profile["annotations"]["sideEffectHint"] is True

    setup_wizard = tools["run_project_setup_wizard"]
    assert setup_wizard["http"]["method"] == "POST"
    assert setup_wizard["http"]["path"] == "/research/onboarding/setup"
    assert setup_wizard["input_schema"]["required"] == ["body"]
    assert setup_wizard["annotations"]["sideEffectHint"] is True

    onboarding_tasks = tools["create_tasks_from_project_onboarding"]
    assert onboarding_tasks["http"]["method"] == "POST"
    assert onboarding_tasks["http"]["path"] == "/research/onboarding/tasks"
    assert onboarding_tasks["input_schema"]["required"] == ["body"]
    assert onboarding_tasks["annotations"]["sideEffectHint"] is True

    onboarding_progress = tools["get_project_onboarding_progress"]
    assert onboarding_progress["http"]["method"] == "GET"
    assert onboarding_progress["http"]["path"] == "/research/onboarding/progress"
    assert onboarding_progress["annotations"]["readOnlyHint"] is True

    pilot_report = tools["get_project_pilot_report"]
    assert pilot_report["http"]["method"] == "GET"
    assert pilot_report["http"]["path"] == "/research/pilot/report"
    assert pilot_report["annotations"]["readOnlyHint"] is True

    pilot_snapshot = tools["create_project_pilot_report_snapshot"]
    assert pilot_snapshot["http"]["method"] == "POST"
    assert pilot_snapshot["http"]["path"] == "/research/pilot/report/snapshots"
    assert pilot_snapshot["input_schema"]["required"] == ["body"]
    assert pilot_snapshot["annotations"]["sideEffectHint"] is True

    pilot_snapshot_list = tools["list_project_pilot_report_snapshots"]
    assert pilot_snapshot_list["http"]["method"] == "GET"
    assert pilot_snapshot_list["http"]["path"] == "/research/pilot/report/snapshots"
    assert pilot_snapshot_list["annotations"]["readOnlyHint"] is True

    pilot_snapshot_compare = tools["compare_project_pilot_report_snapshots"]
    assert pilot_snapshot_compare["http"]["method"] == "POST"
    assert pilot_snapshot_compare["http"]["path"] == "/research/pilot/report/snapshots/compare"
    assert pilot_snapshot_compare["input_schema"]["required"] == ["body"]
    assert pilot_snapshot_compare["annotations"]["sideEffectHint"] is False

    pilot_snapshot_compare_export = tools[
        "export_project_pilot_report_snapshot_comparison_markdown"
    ]
    assert pilot_snapshot_compare_export["http"]["method"] == "POST"
    assert (
        pilot_snapshot_compare_export["http"]["path"]
        == "/research/pilot/report/snapshots/compare/export/markdown"
    )
    assert pilot_snapshot_compare_export["input_schema"]["required"] == ["body"]
    assert pilot_snapshot_compare_export["annotations"]["sideEffectHint"] is False

    pilot_snapshot_comparison_tasks = tools[
        "create_tasks_from_project_pilot_report_snapshot_comparison"
    ]
    assert pilot_snapshot_comparison_tasks["http"]["method"] == "POST"
    assert (
        pilot_snapshot_comparison_tasks["http"]["path"]
        == "/research/pilot/report/snapshots/compare/tasks"
    )
    assert pilot_snapshot_comparison_tasks["input_schema"]["required"] == ["body"]
    assert pilot_snapshot_comparison_tasks["annotations"]["sideEffectHint"] is True

    pilot_snapshot_tasks = tools["create_tasks_from_project_pilot_report_snapshot"]
    assert pilot_snapshot_tasks["http"]["method"] == "POST"
    assert (
        pilot_snapshot_tasks["http"]["path"]
        == "/research/pilot/report/snapshots/{snapshot_id}/tasks"
    )
    assert pilot_snapshot_tasks["input_schema"]["required"] == ["snapshot_id", "body"]
    assert pilot_snapshot_tasks["annotations"]["sideEffectHint"] is True


def test_research_profile_guides_ranking_and_advisor_briefs() -> None:
    client = TestClient(create_app())
    default_profile = client.get("/research/profile")
    assert default_profile.status_code == 200
    assert default_profile.json()["id"] == "default"

    updated = client.put(
        "/research/profile",
        json={
            "name": "Pytest Research Profile",
            "primary_domains": ["geolocation"],
            "active_questions": ["research", "evidence grounded workflow"],
            "target_venues": ["NeurIPS"],
            "methodological_preferences": ["diagnostic benchmark"],
            "resource_constraints": ["limited GPU budget"],
            "risk_tolerance": "low",
            "timeline_horizon": "90 days",
            "negative_preferences": ["large proprietary dataset"],
            "evaluation_weights": {"publication_potential": 0.5, "resource_efficiency": 0.4},
            "notes": "Prefer publishable, evidence-backed MVPs.",
            "created_by": "pytest",
        },
    )
    assert updated.status_code == 200
    profile = updated.json()
    assert profile["name"] == "Pytest Research Profile"
    assert profile["primary_domains"] == ["geolocation"]
    assert profile["evaluation_weights"]["publication_potential"] == 0.5
    assert "# Research Profile: Pytest Research Profile" in profile["markdown_export"]

    profile_export = client.get("/research/profile/export/markdown")
    assert profile_export.status_code == 200
    assert "## Resource Constraints" in profile_export.text

    content = b"""Research Profile Ranking Test Paper

Abstract
This paper checks whether researcher constraints can shape idea ranking and brief context.

Introduction
Geolocation researchers need evidence grounded workflow tools and diagnostic benchmark ideas.

Method
The assistant should prefer publishable experiments that fit limited GPU budgets.

Conclusion
Future work should preserve researcher goals as durable project context.
"""
    upload = client.post(
        "/research/papers/upload",
        files={"file": ("research_profile_test.txt", content, "text/plain")},
    )
    assert upload.status_code == 200
    paper_id = upload.json()["paper"]["id"]
    gaps = client.post("/research/gaps/mine", json={"paper_ids": [paper_id], "max_gaps": 1})
    assert gaps.status_code == 200
    ideas = client.post(f"/research/gaps/{gaps.json()['gaps'][0]['id']}/ideas")
    assert ideas.status_code == 200
    idea_id = ideas.json()["ideas"][0]["id"]

    ranking = client.post(
        "/research/ideas/rank",
        json={"idea_ids": [idea_id], "deduplicate_lineage": False},
    )
    assert ranking.status_code == 200
    ranked = ranking.json()["ranked_ideas"][0]
    assert ranked["idea"]["id"] == idea_id
    assert any("research profile" in item.lower() for item in ranked["rationale"])

    brief = client.post(
        "/research/briefs",
        json={
            "title": "Profile-Aware Brief",
            "scope": "idea_set",
            "idea_ids": [idea_id],
            "created_by": "pytest",
        },
    )
    assert brief.status_code == 200
    brief_body = brief.json()
    assert brief_body["summary"]["profile_name"] == "Pytest Research Profile"
    assert "## Research Profile" in brief_body["markdown_export"]
    assert "## Triage Signals" in brief_body["markdown_export"]
    assert "limited GPU budget" in brief_body["markdown_export"]

    plan = client.post(
        "/research/plans",
        json={
            "title": "Profile-Aware Execution Plan",
            "horizon_days": 14,
            "idea_ids": [idea_id],
            "created_by": "pytest",
        },
    )
    assert plan.status_code == 200
    plan_body = plan.json()
    assert plan_body["title"] == "Profile-Aware Execution Plan"
    assert plan_body["profile_summary"]["name"] == "Pytest Research Profile"
    assert idea_id in plan_body["idea_ids"]
    assert plan_body["plan_items"]
    assert "# Profile-Aware Execution Plan" in plan_body["markdown_export"]
    assert "## Plan Items" in plan_body["markdown_export"]

    listed_plans = client.get("/research/plans?limit=5")
    assert listed_plans.status_code == 200
    assert listed_plans.json()[0]["id"] == plan_body["id"]

    fetched_plan = client.get(f"/research/plans/{plan_body['id']}")
    assert fetched_plan.status_code == 200
    assert fetched_plan.json()["id"] == plan_body["id"]

    plan_export = client.get(f"/research/plans/{plan_body['id']}/export/markdown")
    assert plan_export.status_code == 200
    assert "## Source IDs" in plan_export.text

    plan_tasks = client.post(
        f"/research/plans/{plan_body['id']}/tasks",
        json={"created_by": "pytest"},
    )
    assert plan_tasks.status_code == 200
    plan_task_body = plan_tasks.json()
    assert plan_task_body["tasks"]
    assert plan_task_body["tasks"][0]["owner_type"] == "research_plan"
    assert plan_task_body["tasks"][0]["owner_id"] == plan_body["id"]

    plan_progress = client.get(f"/research/plans/{plan_body['id']}/progress")
    assert plan_progress.status_code == 200
    plan_progress_body = plan_progress.json()
    assert plan_progress_body["plan"]["id"] == plan_body["id"]
    assert plan_progress_body["task_summary"]["task_count"] == len(plan_task_body["tasks"])
    assert plan_progress_body["task_summary"]["open_task_count"] >= 1
    assert "# Research Plan Progress:" in plan_progress_body["markdown_export"]

    plan_task_edges = client.get("/research/graph/edges?edge_type=research_plan_creates_task")
    assert plan_task_edges.status_code == 200
    assert plan_task_edges.json()

    plan_brief = client.post(
        "/research/briefs",
        json={
            "title": "Plan-Aware Brief",
            "scope": "idea_set",
            "idea_ids": [idea_id],
            "created_by": "pytest",
        },
    )
    assert plan_brief.status_code == 200
    plan_brief_body = plan_brief.json()
    assert plan_brief_body["summary"]["research_plan_count"] >= 1
    assert plan_brief_body["summary"]["research_plan_open_task_count"] >= 1
    assert "## Execution Plans" in plan_brief_body["markdown_export"]
    assert "## Readiness Signals" in plan_brief_body["markdown_export"]

    progress = client.get(f"/research/ideas/{idea_id}/progress")
    assert progress.status_code == 200
    progress_body = progress.json()
    assert progress_body["artifact_counts"]["research_plans"] >= 1
    assert progress_body["artifact_counts"]["research_plan_tasks"] >= 1
    assert progress_body["latest_artifacts"]["research_plan"]["id"] == plan_body["id"]
    assert progress_body["task_summary"]["by_owner_type"]["research_plan"] >= 1

    packet = client.get(f"/research/ideas/{idea_id}/research-packet")
    assert packet.status_code == 200
    packet_body = packet.json()
    assert packet_body["latest_artifacts"]["research_plan"]["id"] == plan_body["id"]
    assert packet_body["graph_edge_summary"]["research_plan_creates_task"] >= 1

    lineage = client.get(f"/research/ideas/{idea_id}/lineage")
    assert lineage.status_code == 200
    lineage_body = lineage.json()
    assert lineage_body["research_plans"][0]["id"] == plan_body["id"]
    assert lineage_body["graph_edge_summary"]["research_plan_creates_task"] >= 1
    assert "## Research Plans" in lineage_body["markdown_export"]

    bundle = client.get(f"/research/ideas/{idea_id}/export/bundle")
    assert bundle.status_code == 200
    with zipfile.ZipFile(io.BytesIO(bundle.content)) as archive:
        names = set(archive.namelist())
    assert f"artifacts/plans/research-plan-{plan_body['id']}.md" in names

    reset = client.put(
        "/research/profile",
        json={
            "name": "Default Research Profile",
            "primary_domains": [],
            "active_questions": [],
            "target_venues": [],
            "methodological_preferences": [],
            "resource_constraints": [],
            "risk_tolerance": "medium",
            "timeline_horizon": "",
            "negative_preferences": [],
            "evaluation_weights": {},
            "notes": "",
            "created_by": "pytest",
        },
    )
    assert reset.status_code == 200
    assert reset.json()["name"] == "Default Research Profile"


def test_workbench_static_assets_are_served() -> None:
    client = TestClient(create_app())
    response = client.get("/workbench")
    assert response.status_code == 200
    assert "Research Assistant Workbench" in response.text
    assert "/workbench-assets/app.js" in response.text
    assert "ideaBundleButton" in response.text
    assert "profileForm" in response.text
    assert "profileRisk" in response.text
    assert "researchPlanButton" in response.text
    assert "researchPlanProgressButton" in response.text
    assert "researchPlanTasksButton" in response.text
    assert "readinessTasksButton" in response.text
    assert "taskBoardButton" in response.text
    assert "taskSelect" in response.text
    assert "claimResultButton" in response.text
    assert "timelineButton" in response.text
    assert "projectBundleButton" in response.text
    assert "projectBundleReleaseButton" in response.text
    assert "projectBundleReleasesButton" in response.text
    assert "projectBundleReleaseTasksButton" in response.text
    assert "projectBundleReleaseProgressButton" in response.text
    assert "projectBundleReleaseFeedbackButton" in response.text
    assert "projectBundleReleaseFeedbackListButton" in response.text
    assert "projectBundleReleaseFeedbackTasksButton" in response.text
    assert "projectBundleReleaseCloseoutButton" in response.text
    assert "projectBundleReleaseCloseoutTasksButton" in response.text
    assert "projectBundleReleaseAcceptancePacketButton" in response.text
    assert "projectBundleReleaseAcceptancePacketSnapshotButton" in response.text
    assert "projectBundleReleaseAcceptancePacketSnapshotsButton" in response.text
    assert "projectBundleReleaseAcceptancePacketSnapshotCompareButton" in response.text
    assert "projectBundleReleaseAcceptancePacketSnapshotTasksButton" in response.text
    assert "projectBundleReleaseReviewSessionButton" in response.text
    assert "projectBundleReleaseReviewSessionTasksButton" in response.text
    assert "projectBundleReleaseReviewOutcomeButton" in response.text
    assert "projectBundleReleaseReviewOutcomesButton" in response.text
    assert "projectBundleReleaseReviewOutcomeTasksButton" in response.text
    assert "projectBundleReleaseReviewOutcomeProgressButton" in response.text
    assert "projectBundleReleaseReviewOutcomeSignoffButton" in response.text
    assert "projectBundleReleaseReviewOutcomeSignoffsButton" in response.text
    assert "projectBundleReadinessButton" in response.text
    assert "projectBundleReadinessTasksButton" in response.text
    assert "projectBundleReadinessSnapshotButton" in response.text
    assert "projectBundleReadinessSnapshotsButton" in response.text
    assert "projectBundleReadinessSnapshotCompareButton" in response.text
    assert "projectBundleReadinessComparisonTasksButton" in response.text
    assert "evidenceLedgerButton" in response.text
    assert "evidenceLedgerTasksButton" in response.text
    assert "claimPacketButton" in response.text
    assert "claimQueueButton" in response.text
    assert "claimQueueTasksButton" in response.text
    assert "cockpitButton" in response.text
    assert "cockpitTasksButton" in response.text
    assert "advisorChatForm" in response.text
    assert "advisorChatTasksButton" in response.text
    assert "advisorActionSessionButton" in response.text
    assert "apiKeyInput" in response.text
    assert "saveApiKeyButton" in response.text
    assert "clearApiKeyButton" in response.text
    assert "pilot-launch" in response.text
    assert "pilotLaunchRefreshButton" in response.text
    assert "pilotLaunchMetrics" in response.text
    assert "pilotLaunchResult" in response.text
    assert "onboardingButton" in response.text
    assert "onboardingMarkdownButton" in response.text
    assert "onboardingTasksButton" in response.text
    assert "onboardingProgressButton" in response.text
    assert "pilotReportButton" in response.text
    assert "pilotReportSnapshotButton" in response.text
    assert "pilotReportSnapshotCompareButton" in response.text
    assert "pilotReportSnapshotComparisonTasksButton" in response.text
    assert "pilotReportSnapshotTasksButton" in response.text
    assert "setupWizardForm" in response.text
    assert "setupWizardButton" in response.text
    assert "action-group-title" in response.text
    assert "Idea Loop" in response.text
    assert "Task Board" in response.text
    assert "Project Delivery" in response.text
    assert "Project Operations" in response.text
    expected_sections = {
        "pilot-launch": "Pilot Launch",
        "onboarding": "Onboarding",
        "ingest": "Ingest",
        "workflow": "Workflow",
        "profile": "Profile",
        "search": "Search",
        "advisor": "Advisor",
        "jobs": "Jobs",
        "dossier": "Dossier",
    }
    for section_id, label in expected_sections.items():
        assert f'href="#{section_id}"' in response.text
        assert f'id="{section_id}"' in response.text
        assert label in response.text

    styles = client.get("/workbench-assets/styles.css")
    assert styles.status_code == 200
    assert ".app-shell" in styles.text
    assert "grid-template-columns" in styles.text
    assert ".controls-grid" in styles.text
    assert "@media" in styles.text
    assert "max-width: 920px" in styles.text

    script = client.get("/workbench-assets/app.js")
    assert script.status_code == 200
    assert "/research/profile" in script.text
    assert "researchAssistantApiKey" in script.text
    assert "X-Research-Assistant-Key" in script.text
    assert "withAuthHeaders" in script.text
    assert "downloadWithAuth" in script.text
    assert "workbenchErrorMessage" in script.text
    assert "renderWorkbenchError" in script.text
    assert "renderWorkbenchEmpty" in script.text
    assert "Save a valid API key in the top bar" in script.text
    assert "Check that the API server is reachable" in script.text
    assert "Save a project bundle release note before creating release tasks" in script.text
    assert "Record a release review outcome before recording signoff evidence" in script.text
    assert "/research/onboarding/readiness" in script.text
    assert "/research/onboarding/progress?limit=100" in script.text
    assert "/research/cockpit" in script.text
    assert "loadPilotLaunch" in script.text
    assert "renderPilotMetric" in script.text
    assert "/research/onboarding/setup" in script.text
    assert "/research/onboarding/tasks" in script.text
    assert "/research/onboarding/progress" in script.text
    assert "/research/pilot/report" in script.text
    assert "/research/pilot/report/snapshots" in script.text
    assert "/research/pilot/report/snapshots/compare" in script.text
    assert "/research/pilot/report/snapshots/compare/tasks" in script.text
    assert (
        "/research/pilot/report/snapshots/${state.latestPilotReportSnapshotId}/tasks" in script.text
    )
    assert "loadOnboardingReadiness" in script.text
    assert "runProjectSetupWizard" in script.text
    assert "createOnboardingTasks" in script.text
    assert "loadOnboardingProgress" in script.text
    assert "loadPilotReport" in script.text
    assert "savePilotReportSnapshot" in script.text
    assert "comparePilotReportSnapshots" in script.text
    assert "createPilotReportSnapshotComparisonTasks" in script.text
    assert "createPilotReportSnapshotTasks" in script.text
    assert "/research/profile/export/markdown" in script.text
    assert "saveResearchProfile" in script.text
    assert "/research/plans" in script.text
    assert "/research/plans/${state.latestResearchPlanId}/tasks" in script.text
    assert "/research/plans/${state.latestResearchPlanId}/progress" in script.text
    assert "/research/workflows/literature-to-ideas/async" in script.text
    assert "/research/jobs/${jobId}/artifacts" in script.text
    assert "/research/jobs/${jobId}/${action}" in script.text
    assert 'data-job-action="cancel"' in script.text
    assert 'data-job-action="retry"' in script.text
    assert "/research/ideas/${state.latestIdeaId}/refine" in script.text
    assert "/research/ideas/${state.latestIdeaId}/feedback" in script.text
    assert "/research/ideas/${state.latestIdeaId}/novelty-refresh" in script.text
    assert (
        "/research/ideas/${state.latestIdeaId}/novelty-checks/${state.latestNoveltyCheckId}/tasks"
    ) in script.text
    assert "/research/ideas/${state.latestIdeaId}/related-work-matrix" in script.text
    assert "/research/ideas/${state.latestIdeaId}/proposal-draft" in script.text
    assert "/proposal-drafts/${state.latestProposalDraftId}/review" in script.text
    assert "/proposal-drafts/${state.latestProposalDraftId}/revise" in script.text
    assert "/revisions/${state.latestProposalRevisionId}/tasks" in script.text
    assert "/research/tasks/snapshots" in script.text
    assert "/research/tasks?${params.toString()}" in script.text
    assert "/research/tasks/${taskId}" in script.text
    assert "/research/tasks/${taskId}/claim-validation-result" in script.text
    assert "/research/experiment-plans/${state.latestExperimentPlanId}/runs" in script.text
    assert "/research/experiment-runs/${state.latestExperimentRunId}/analysis" in script.text
    assert "/research/experiment-analyses/${state.latestExperimentAnalysisId}/tasks" in script.text
    assert "/research/ideas/${state.latestIdeaId}/lineage" in script.text
    assert "/research/ideas/${state.latestIdeaId}/timeline" in script.text
    assert "/research/ideas/${state.latestIdeaId}/progress" in script.text
    assert "/research/ideas/${state.latestIdeaId}/research-packet" in script.text
    assert "/research/ideas/${encodeURIComponent(state.latestIdeaId)}/export/bundle" in script.text
    assert "/research/export/project-bundle" in script.text
    assert "/research/export/project-bundle/releases" in script.text
    assert "/research/export/project-bundle/releases/${releaseId}/tasks" in script.text
    assert "/research/export/project-bundle/releases/${releaseId}/progress" in script.text
    assert "/research/export/project-bundle/releases/${releaseId}/feedback" in script.text
    assert (
        "/research/export/project-bundle/releases/${releaseId}/feedback/${feedbackId}/tasks"
        in script.text
    )
    assert "/research/export/project-bundle/releases/${releaseId}/closeout" in script.text
    assert "/research/export/project-bundle/releases/${releaseId}/closeout/tasks" in script.text
    assert "/research/export/project-bundle/releases/${releaseId}/acceptance-packet" in script.text
    assert (
        "/research/export/project-bundle/releases/${releaseId}/acceptance-packet/snapshots"
        in script.text
    )
    assert (
        "/research/export/project-bundle/releases/${releaseId}/acceptance-packet/snapshots/compare"
        in script.text
    )
    assert (
        "/research/export/project-bundle/releases/${releaseId}/acceptance-packet/snapshots/compare/tasks"
        in script.text
    )
    assert "/research/export/project-bundle/releases/${releaseId}/review-session" in script.text
    assert (
        "/research/export/project-bundle/releases/${releaseId}/review-session/tasks" in script.text
    )
    assert (
        "/research/export/project-bundle/releases/${releaseId}/review-session/outcomes"
        in script.text
    )
    assert (
        "/research/export/project-bundle/releases/${releaseId}/review-session/outcomes/${outcomeId}/tasks"
        in script.text
    )
    assert (
        "/research/export/project-bundle/releases/${releaseId}/review-session/outcomes/${outcomeId}/progress"
        in script.text
    )
    assert (
        "/research/export/project-bundle/releases/${releaseId}/review-session/outcomes/${outcomeId}/signoffs"
        in script.text
    )
    assert "/research/export/project-bundle/readiness" in script.text
    assert "/research/export/project-bundle/readiness/tasks" in script.text
    assert "/research/export/project-bundle/readiness/snapshots" in script.text
    assert "/research/export/project-bundle/readiness/snapshots/compare" in script.text
    assert "/research/export/project-bundle/readiness/snapshots/compare/tasks" in script.text
    assert "saveProjectBundleReleaseNote" in script.text
    assert "listProjectBundleReleaseNotes" in script.text
    assert "createProjectBundleReleaseTasks" in script.text
    assert "loadProjectBundleReleaseProgress" in script.text
    assert "recordProjectBundleReleaseFeedback" in script.text
    assert "listProjectBundleReleaseFeedback" in script.text
    assert "createProjectBundleReleaseFeedbackTasks" in script.text
    assert "loadProjectBundleReleaseCloseout" in script.text
    assert "createProjectBundleReleaseCloseoutTasks" in script.text
    assert "loadProjectBundleReleaseAcceptancePacket" in script.text
    assert "saveProjectBundleReleaseAcceptancePacketSnapshot" in script.text
    assert "listProjectBundleReleaseAcceptancePacketSnapshots" in script.text
    assert "compareProjectBundleReleaseAcceptancePacketSnapshots" in script.text
    assert "createProjectBundleReleaseAcceptancePacketSnapshotComparisonTasks" in script.text
    assert "loadProjectBundleReleaseReviewSession" in script.text
    assert "createProjectBundleReleaseReviewSessionTasks" in script.text
    assert "recordProjectBundleReleaseReviewOutcome" in script.text
    assert "listProjectBundleReleaseReviewOutcomes" in script.text
    assert "createProjectBundleReleaseReviewOutcomeTasks" in script.text
    assert "loadProjectBundleReleaseReviewOutcomeProgress" in script.text
    assert "loadProjectBundleReadiness" in script.text
    assert "createProjectBundleReadinessTasks" in script.text
    assert "saveProjectBundleReadinessSnapshot" in script.text
    assert "listProjectBundleReadinessSnapshots" in script.text
    assert "compareProjectBundleReadinessSnapshots" in script.text
    assert "createProjectBundleReadinessComparisonTasks" in script.text
    assert "/research/ideas/${state.latestIdeaId}/readiness" in script.text
    assert "/research/ideas/${state.latestIdeaId}/quality-gate" in script.text
    assert "/research/ideas/${state.latestIdeaId}/quality-gate/tasks" in script.text
    assert "/research/ideas/${state.latestIdeaId}/readiness/tasks" in script.text
    assert "/research/ideas/${state.latestIdeaId}/decision-memo" in script.text
    assert (
        "/research/ideas/${state.latestIdeaId}/decision-memos/${state.latestDecisionMemoId}/tasks"
    ) in script.text
    assert "/research/ideas/${state.latestIdeaId}/assumption-audit" in script.text
    assert "/research/ideas/${state.latestIdeaId}/evidence-ledger" in script.text
    assert (
        "/research/ideas/${state.latestIdeaId}/evidence-ledgers/${state.latestEvidenceLedgerId}/tasks"
    ) in script.text
    assert (
        "/research/ideas/${state.latestIdeaId}/evidence-ledgers/${state.latestEvidenceLedgerId}/claims/${claimId}/validation-packet"
    ) in script.text
    assert "/research/claims/validation-queue?${params.toString()}" in script.text
    assert "/research/claims/validation-queue/tasks" in script.text
    assert "/research/cockpit" in script.text
    assert "/research/cockpit/tasks" in script.text
    assert "/research/advisor/chat" in script.text
    assert "/research/advisor/chat/tasks" in script.text
    assert "/research/advisor/action-session" in script.text
    assert "/research/progress/overview" in script.text
    assert "/research/triage/brief" in script.text
    assert "/research/triage/brief/export/markdown" in script.text
    assert "/research/triage/snapshots" in script.text
    assert "/research/triage/snapshots/compare" in script.text
    assert "/research/triage/snapshots/compare/tasks" in script.text
    assert "/research/triage/brief/tasks" in script.text
    assert "/research/readiness/overview" in script.text
    assert "/research/quality/overview" in script.text
    assert "/research/quality/overview/tasks" in script.text
    assert "/research/opportunities/radar?limit=8" in script.text
    assert "/research/opportunities/radar/tasks" in script.text
    assert "/research/briefs" in script.text
    assert "/research/ideas/rank" in script.text
    assert "/research/ideas/rank/export/markdown" in script.text
    assert "/research/ideas/portfolios" in script.text


def test_project_onboarding_readiness_tracks_first_run_and_upload() -> None:
    client = TestClient(create_app())
    initial = client.get("/research/onboarding/readiness")
    assert initial.status_code == 200
    initial_body = initial.json()
    assert "# Project Onboarding Readiness" in initial_body["markdown_export"]
    assert initial_body["required_total"] >= 5
    assert 0 <= initial_body["readiness_score"] <= 1
    assert {item["id"] for item in initial_body["checklist"]} >= {
        "profile",
        "paper_ingest",
        "workflow",
        "task_board",
        "bundle_export",
        "pilot_security",
        "mcp_bridge",
    }

    marker = f"onboarding-readiness-{time.time_ns()}"
    content = f"""Onboarding Readiness Test {marker}

Abstract
This paper gives the customer onboarding readiness endpoint evidence to count.

Method
The assistant indexes sections, chunks, and evidence records for pilot setup.

Conclusion
Future work should run the first literature-to-ideas workflow.
""".encode()
    upload = client.post(
        "/research/papers/upload",
        files={"file": ("onboarding_readiness.txt", content, "text/plain")},
    )
    assert upload.status_code == 200

    after = client.get("/research/onboarding/readiness")
    assert after.status_code == 200
    after_body = after.json()
    checklist = {item["id"]: item for item in after_body["checklist"]}
    assert checklist["paper_ingest"]["status"] == "done"
    assert (
        after_body["project_metrics"]["paper_count"]
        >= initial_body["project_metrics"]["paper_count"]
    )
    assert after_body["quick_actions"]
    assert any(action["id"] == "workflow" for action in after_body["quick_actions"])


def test_project_setup_wizard_saves_profile_and_returns_readiness() -> None:
    client = TestClient(create_app())
    marker = f"Setup Wizard {time.time_ns()}"
    response = client.post(
        "/research/onboarding/setup",
        json={
            "name": marker,
            "primary_domains": ["research agents", "graph rag"],
            "active_questions": ["How should an assistant propose testable research ideas?"],
            "target_venues": ["ACL"],
            "methodological_preferences": ["evidence-grounded ideation"],
            "resource_constraints": ["single workstation"],
            "risk_tolerance": "medium",
            "timeline_horizon": "30 days",
            "success_criteria": ["advisor-ready report", "first executable experiment"],
            "first_milestone": "Upload seed papers and run the first workflow.",
            "created_by": "pytest",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["name"] == marker
    assert "Project Setup Wizard" in body["markdown_export"]
    assert body["readiness"]["readiness_score"] >= 0
    assert body["recommended_next_steps"]
    checklist = {item["id"]: item for item in body["readiness"]["checklist"]}
    assert checklist["profile"]["status"] == "done"

    profile = client.get("/research/profile")
    assert profile.status_code == 200
    profile_body = profile.json()
    assert profile_body["name"] == marker
    assert "advisor-ready report" in profile_body["notes"]


def test_project_onboarding_tasks_create_task_board_items_and_graph_edges() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/research/onboarding/tasks",
        json={"limit": 6, "include_optional": True, "created_by": "pytest"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["tasks"]
    assert all(task["owner_type"] == "project_onboarding" for task in body["tasks"])
    assert all(task["due_phase"] == "onboarding_follow_up" for task in body["tasks"])
    assert any(task["metadata"]["readiness_level"] for task in body["tasks"])

    edges = client.get("/research/graph/edges?edge_type=project_onboarding_creates_task")
    assert edges.status_code == 200
    assert edges.json()


def test_project_onboarding_progress_tracks_task_completion() -> None:
    client = TestClient(create_app())
    created = client.post(
        "/research/onboarding/tasks",
        json={"limit": 4, "include_optional": True, "created_by": "pytest"},
    )
    assert created.status_code == 200
    tasks = created.json()["tasks"]
    assert tasks

    initial = client.get("/research/onboarding/progress")
    assert initial.status_code == 200
    initial_body = initial.json()
    assert "Project Onboarding Progress" in initial_body["markdown_export"]
    assert initial_body["task_summary"]["task_count"] >= len(tasks)
    assert initial_body["next_action"]

    update = client.patch(
        f"/research/tasks/{tasks[0]['id']}",
        json={"status": "done", "note": "pytest completed onboarding task"},
    )
    assert update.status_code == 200

    after = client.get("/research/onboarding/progress")
    assert after.status_code == 200
    after_body = after.json()
    assert after_body["task_summary"]["done_task_count"] >= 1
    assert (
        after_body["task_summary"]["completion_ratio"]
        >= initial_body["task_summary"]["completion_ratio"]
    )


def test_project_pilot_report_combines_onboarding_and_cockpit_state() -> None:
    client = TestClient(create_app())
    setup = client.post(
        "/research/onboarding/setup",
        json={
            "name": f"Pilot Report {time.time_ns()}",
            "primary_domains": ["research assistants"],
            "active_questions": ["How can the system report pilot readiness?"],
            "target_venues": ["ACL"],
            "methodological_preferences": ["evidence-grounded reporting"],
            "resource_constraints": ["small pilot"],
            "success_criteria": ["customer-readable report"],
            "first_milestone": "Generate pilot status report.",
            "created_by": "pytest",
        },
    )
    assert setup.status_code == 200
    tasks = client.post(
        "/research/onboarding/tasks",
        json={"limit": 4, "include_optional": True, "created_by": "pytest"},
    )
    assert tasks.status_code == 200

    report = client.get("/research/pilot/report")
    assert report.status_code == 200
    body = report.json()
    assert "Project Pilot Status Report" in body["markdown_export"]
    assert body["executive_summary"]
    assert body["onboarding"]["task_summary"]["task_count"] >= len(tasks.json()["tasks"])
    assert body["cockpit"]["project_metrics"]
    assert body["key_metrics"]["readiness_level"] == body["readiness_level"]
    assert body["next_actions"]


def test_project_pilot_report_snapshots_persist_and_export_markdown() -> None:
    client = TestClient(create_app())
    title = f"Pilot Snapshot {time.time_ns()}"
    created = client.post(
        "/research/pilot/report/snapshots",
        json={"title": title, "created_by": "pytest"},
    )
    assert created.status_code == 200
    body = created.json()
    assert body["title"] == title
    assert body["scope"] == "pilot_report"
    assert "Project Pilot Status Report" in body["markdown_export"]
    assert body["summary"]["report_status"]

    listed = client.get("/research/pilot/report/snapshots")
    assert listed.status_code == 200
    assert any(item["id"] == body["id"] for item in listed.json())

    fetched = client.get(f"/research/pilot/report/snapshots/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["markdown_export"] == body["markdown_export"]

    exported = client.get(f"/research/pilot/report/snapshots/{body['id']}/export/markdown")
    assert exported.status_code == 200
    assert "Project Pilot Status Report" in exported.text

    tasks = client.post(
        f"/research/pilot/report/snapshots/{body['id']}/tasks",
        json={
            "limit": 6,
            "include_risks": True,
            "include_next_actions": True,
            "include_quick_actions": True,
            "created_by": "pytest",
        },
    )
    assert tasks.status_code == 200
    task_body = tasks.json()
    assert task_body["tasks"]
    assert "pilot report snapshot" in task_body["message"]
    first_task = task_body["tasks"][0]
    assert first_task["owner_type"] == "project_pilot_report_snapshot"
    assert first_task["owner_id"] == body["id"]
    assert first_task["metadata"]["snapshot_id"] == body["id"]
    assert first_task["source_type"] in {
        "pilot_report_risk",
        "pilot_report_next_action",
        "pilot_report_quick_action",
        "pilot_report_review",
    }

    candidate = client.post(
        "/research/pilot/report/snapshots",
        json={"title": f"{title} Candidate", "created_by": "pytest"},
    )
    assert candidate.status_code == 200
    candidate_body = candidate.json()

    comparison = client.post(
        "/research/pilot/report/snapshots/compare",
        json={
            "baseline_snapshot_id": body["id"],
            "candidate_snapshot_id": candidate_body["id"],
        },
    )
    assert comparison.status_code == 200
    comparison_body = comparison.json()
    assert comparison_body["baseline_snapshot_id"] == body["id"]
    assert comparison_body["candidate_snapshot_id"] == candidate_body["id"]
    assert "Compared pilot report snapshots" in comparison_body["summary"]
    assert "Project Pilot Report Snapshot Comparison" in comparison_body["markdown_export"]
    assert comparison_body["kept_next_actions"]

    comparison_markdown = client.post(
        "/research/pilot/report/snapshots/compare/export/markdown",
        json={
            "baseline_snapshot_id": body["id"],
            "candidate_snapshot_id": candidate_body["id"],
        },
    )
    assert comparison_markdown.status_code == 200
    assert comparison_markdown.headers["content-type"].startswith("text/markdown")
    assert "## Next Action Changes" in comparison_markdown.text

    comparison_tasks = client.post(
        "/research/pilot/report/snapshots/compare/tasks",
        json={
            "baseline_snapshot_id": body["id"],
            "candidate_snapshot_id": candidate_body["id"],
            "limit": 6,
            "include_risks": True,
            "include_next_actions": True,
            "include_quick_actions": True,
            "created_by": "pytest",
        },
    )
    assert comparison_tasks.status_code == 200
    comparison_task_body = comparison_tasks.json()
    assert comparison_task_body["tasks"]
    assert "pilot report comparison tasks" in comparison_task_body["message"]
    first_comparison_task = comparison_task_body["tasks"][0]
    assert first_comparison_task["owner_type"] == "project_pilot_report_snapshot_comparison"
    assert first_comparison_task["owner_id"] == candidate_body["id"]
    assert first_comparison_task["metadata"]["baseline_snapshot_id"] == body["id"]
    assert first_comparison_task["metadata"]["candidate_snapshot_id"] == candidate_body["id"]
    assert first_comparison_task["source_type"] in {
        "pilot_report_comparison_added_risk",
        "pilot_report_comparison_added_next_action",
        "pilot_report_comparison_added_quick_action",
        "pilot_report_comparison_review",
    }


def test_upload_rejects_unsupported_file_type(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PAPER_UPLOAD_DIR", str(tmp_path))
    client = TestClient(create_app())

    response = client.post(
        "/research/papers/upload",
        files={"file": ("malware.exe", b"not a paper", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]
    assert not (tmp_path / "malware.exe").exists()


def test_upload_respects_allowed_extensions_override_before_writing(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PAPER_UPLOAD_DIR", str(tmp_path))
    monkeypatch.setenv("PAPER_UPLOAD_ALLOWED_EXTENSIONS", "txt")
    client = TestClient(create_app())

    response = client.post(
        "/research/papers/upload",
        files={"file": ("blocked_markdown.md", b"# Blocked", "text/markdown")},
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]
    assert ".txt" in response.json()["detail"]
    assert not (tmp_path / "blocked_markdown.md").exists()


def test_upload_allowed_extensions_override_normalizes_values(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PAPER_UPLOAD_DIR", str(tmp_path))
    monkeypatch.setenv("PAPER_UPLOAD_ALLOWED_EXTENSIONS", " txt, .MD , PDF ")
    client = TestClient(create_app())
    content = b"""Allowed Extension Normalization Upload Paper

Abstract
This markdown upload validates whitespace, dot, and case normalization for allowed extensions.

Conclusion
Configured extension lists should be operator-friendly during pilot setup.
"""

    response = client.post(
        "/research/papers/upload",
        files={"file": ("normalized_extension.md", content, "text/markdown")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["paper"]["filename"] == "normalized_extension.md"
    assert body["paper"]["status"] == "indexed"
    assert body["evidence_count"] >= 2
    assert (tmp_path / "normalized_extension.md").exists()


def test_upload_accepts_uppercase_allowed_extension(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PAPER_UPLOAD_DIR", str(tmp_path))
    client = TestClient(create_app())
    content = b"""Uppercase Extension Upload Paper

Abstract
This paper validates case-insensitive upload extension handling.

Conclusion
Uppercase text file extensions should be accepted and indexed.
"""

    response = client.post(
        "/research/papers/upload",
        files={"file": ("UPPERCASE_PAPER.TXT", content, "text/plain")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["paper"]["filename"] == "UPPERCASE_PAPER.TXT"
    assert body["paper"]["status"] == "indexed"
    assert body["section_count"] >= 2
    assert body["evidence_count"] >= 2
    assert (tmp_path / "UPPERCASE_PAPER.TXT").exists()


def test_upload_rejects_empty_file_before_writing(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PAPER_UPLOAD_DIR", str(tmp_path))
    client = TestClient(create_app())

    response = client.post(
        "/research/papers/upload",
        files={"file": ("empty.txt", b"", "text/plain")},
    )

    assert response.status_code == 400
    assert "Uploaded file is empty" in response.json()["detail"]
    assert not (tmp_path / "empty.txt").exists()


def test_upload_rejects_file_larger_than_limit(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PAPER_UPLOAD_DIR", str(tmp_path))
    monkeypatch.setenv("PAPER_UPLOAD_MAX_BYTES", "8")
    client = TestClient(create_app())

    response = client.post(
        "/research/papers/upload",
        files={"file": ("too_large.txt", b"0123456789", "text/plain")},
    )

    assert response.status_code == 400
    assert "too large" in response.json()["detail"]
    assert not (tmp_path / "too_large.txt").exists()


def test_upload_invalid_max_bytes_falls_back_to_default_limit(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PAPER_UPLOAD_DIR", str(tmp_path))
    monkeypatch.setenv("PAPER_UPLOAD_MAX_BYTES", "not-an-integer")
    client = TestClient(create_app())
    content = b"""Invalid Upload Limit Fallback Paper

Abstract
This markdown upload validates that an invalid max-byte setting falls back safely.

Conclusion
Pilot uploads should not fail just because an operator mistyped the byte limit.
"""

    response = client.post(
        "/research/papers/upload",
        files={"file": ("invalid_limit_fallback.md", content, "text/markdown")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["paper"]["filename"] == "invalid_limit_fallback.md"
    assert body["paper"]["status"] == "indexed"
    assert body["evidence_count"] >= 2
    assert (tmp_path / "invalid_limit_fallback.md").exists()


def test_upload_non_positive_max_bytes_falls_back_to_default_limit(tmp_path, monkeypatch) -> None:
    from backend.research.services import document_ingestion

    monkeypatch.setenv("PAPER_UPLOAD_DIR", str(tmp_path))
    monkeypatch.setenv("PAPER_UPLOAD_MAX_BYTES", "-1")
    default_max_bytes = document_ingestion.settings.paper_upload_max_bytes
    object.__setattr__(document_ingestion.settings, "paper_upload_max_bytes", 8)
    try:
        client = TestClient(create_app())
        response = client.post(
            "/research/papers/upload",
            files={"file": ("negative_limit.txt", b"0123456789", "text/plain")},
        )
    finally:
        object.__setattr__(
            document_ingestion.settings,
            "paper_upload_max_bytes",
            default_max_bytes,
        )

    assert response.status_code == 400
    assert "too large" in response.json()["detail"]
    assert "Max allowed size is 8 bytes" in response.json()["detail"]
    assert not (tmp_path / "negative_limit.txt").exists()


def test_upload_rejects_binary_text_file_before_writing(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PAPER_UPLOAD_DIR", str(tmp_path))
    client = TestClient(create_app())

    response = client.post(
        "/research/papers/upload",
        files={"file": ("fake_text.txt", b"Title\x00binary payload", "text/plain")},
    )

    assert response.status_code == 400
    assert "appears to be binary" in response.json()["detail"]
    assert not (tmp_path / "fake_text.txt").exists()


def test_upload_rejects_non_utf8_text_before_writing(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PAPER_UPLOAD_DIR", str(tmp_path))
    client = TestClient(create_app())

    response = client.post(
        "/research/papers/upload",
        files={"file": ("latin1_text.txt", b"Title: caf\xe9", "text/plain")},
    )

    assert response.status_code == 400
    assert "must be UTF-8 encoded text" in response.json()["detail"]
    assert not (tmp_path / "latin1_text.txt").exists()


def test_upload_rejects_pdf_without_pdf_header_before_writing(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PAPER_UPLOAD_DIR", str(tmp_path))
    client = TestClient(create_app())

    response = client.post(
        "/research/papers/upload",
        files={"file": ("fake.pdf", b"not actually a pdf", "application/pdf")},
    )

    assert response.status_code == 400
    assert "does not appear to be a PDF document" in response.json()["detail"]
    assert not (tmp_path / "fake.pdf").exists()


def test_upload_sanitizes_path_traversal_filename(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PAPER_UPLOAD_DIR", str(tmp_path / "papers"))
    client = TestClient(create_app())
    content = b"""Path Sanitization Upload Paper

Abstract
This upload validates that file names cannot escape the configured paper directory.

Conclusion
The stored file should use only the submitted basename.
"""

    response = client.post(
        "/research/papers/upload",
        files={"file": ("../escape_attempt.txt", content, "text/plain")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["paper"]["filename"] == "escape_attempt.txt"
    assert (tmp_path / "papers" / "escape_attempt.txt").exists()
    assert not (tmp_path / "escape_attempt.txt").exists()

    session = SessionLocal()
    try:
        stored_paper = session.get(Paper, body["paper"]["id"])
        assert stored_paper is not None
        assert (
            Path(stored_paper.file_path).resolve()
            == (tmp_path / "papers" / "escape_attempt.txt").resolve()
        )
    finally:
        session.close()


def test_upload_text_paper() -> None:
    client = TestClient(create_app())
    content = b"""Research Assistant Agent Test Paper

Abstract
This paper proposes a small evidence-grounded research assistant test fixture.

Introduction
Research assistants need structured evidence rather than only raw chunks.

Method
The method extracts sections, chunks, and evidence records.

Conclusion
Future work should add structured paper-card extraction.
"""
    response = client.post(
        "/research/papers/upload",
        files={"file": ("test_paper.txt", content, "text/plain")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["paper"]["status"] == "indexed"
    assert body["section_count"] >= 3
    assert body["chunk_count"] >= body["section_count"]
    assert body["evidence_count"] >= 3

    evidence_response = client.get(f"/research/papers/{body['paper']['id']}/evidence")
    assert evidence_response.status_code == 200
    assert len(evidence_response.json()) == body["evidence_count"]


def test_upload_markdown_paper_uses_default_allowed_extension(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PAPER_UPLOAD_DIR", str(tmp_path))
    client = TestClient(create_app())
    content = b"""Markdown Upload Paper

Abstract
This Markdown fixture validates the documented default upload extension set.

Method
The Markdown upload path should reuse text ingestion, section detection, and evidence extraction.

Conclusion
Markdown papers should be indexed without requiring service startup.
"""

    response = client.post(
        "/research/papers/upload",
        files={"file": ("markdown_paper.md", content, "text/markdown")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["paper"]["filename"] == "markdown_paper.md"
    assert body["paper"]["status"] == "indexed"
    assert body["section_count"] >= 3
    assert body["chunk_count"] >= body["section_count"]
    assert body["evidence_count"] >= 3
    assert (tmp_path / "markdown_paper.md").exists()

    evidence_response = client.get(f"/research/papers/{body['paper']['id']}/evidence")
    assert evidence_response.status_code == 200
    assert len(evidence_response.json()) == body["evidence_count"]


def test_markdown_gap_sections_are_mined_from_headings(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PAPER_UPLOAD_DIR", str(tmp_path))
    client = TestClient(create_app())
    content = b"""# Markdown Gap Mining Paper

## Abstract
This fixture validates Markdown heading ingestion for research gap mining.

## Introduction
Research assistants need robust parsing of representative paper fixtures.

## Limitations
The current workflow cannot reliably evaluate scarce evidence slices across specialized domains.

## Future Work
Future work should add cross-domain ablation studies and stronger reviewer simulation.
"""

    upload = client.post(
        "/research/papers/upload",
        files={"file": ("markdown_gap_paper.md", content, "text/markdown")},
    )

    assert upload.status_code == 200
    paper_id = upload.json()["paper"]["id"]

    evidence_response = client.get(f"/research/papers/{paper_id}/evidence")
    assert evidence_response.status_code == 200
    evidence_types = {item["evidence_type"] for item in evidence_response.json()}
    assert "limitation" in evidence_types
    assert "future_work" in evidence_types

    mined = client.post("/research/gaps/mine", json={"paper_ids": [paper_id], "max_gaps": 5})

    assert mined.status_code == 200
    gap_types = {item["gap_type"] for item in mined.json()["gaps"]}
    assert "method_gap" in gap_types
    assert "application_gap" in gap_types


def test_literature_search_returns_local_results_with_external_disabled() -> None:
    client = TestClient(create_app())
    marker = f"literaturesearchmarker{time.time_ns()}"
    content = f"""Literature Search Test Paper {marker}

Abstract
This paper validates local literature search for research assistant projects with marker {marker}.

Introduction
Literature search should find local papers before optional external search is enabled.

Conclusion
Future work should connect OpenAlex and arXiv providers.
""".encode()
    upload = client.post(
        "/research/papers/upload",
        files={"file": ("literature_search_test.txt", content, "text/plain")},
    )
    assert upload.status_code == 200
    paper_id = upload.json()["paper"]["id"]

    response = client.post(
        "/research/literature/search",
        json={
            "query": marker,
            "limit": 10,
            "include_external": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["external_status"] == "disabled"
    assert body["items"]
    assert body["items"][0]["provider"] == "local"
    assert any(item["source_id"] == paper_id for item in body["items"])


def test_literature_search_rejects_empty_query() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/research/literature/search",
        json={"query": " !! ", "limit": 5, "include_external": False},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Query must contain at least one searchable term"


def test_literature_search_clamps_limit_and_sorts_combined_results(monkeypatch) -> None:
    from backend.research.schemas import LiteratureSearchItem
    from backend.research.services import literature_search_service

    default_enabled = literature_search_service.settings.external_literature_search_enabled
    captured = {}
    object.__setattr__(
        literature_search_service.settings,
        "external_literature_search_enabled",
        True,
    )

    def search_item(provider, source_id, score):
        return LiteratureSearchItem(
            provider=provider,
            source_id=source_id,
            title=source_id,
            authors=[],
            year=None,
            venue="",
            url="",
            abstract="",
            score=score,
            metadata={},
        )

    def local_items(self, terms, limit):
        captured["terms"] = terms
        captured["local_limit"] = limit
        return [
            search_item("local", "local-low", 1.0),
            search_item("local", "local-high", 8.0),
        ]

    def external_items(self, query, limit):
        captured["query"] = query
        captured["external_limit"] = limit
        return (
            [
                search_item("openalex", "external-top", 9.0),
                search_item("arxiv", "external-mid", 5.0),
            ],
            "completed",
        )

    monkeypatch.setattr(LiteratureSearchService, "_search_local", local_items)
    monkeypatch.setattr(LiteratureSearchService, "_search_external", external_items)

    try:
        response = LiteratureSearchService(None).search(
            "Agent Evidence agent",
            limit=100,
            include_external=True,
        )
    finally:
        object.__setattr__(
            literature_search_service.settings,
            "external_literature_search_enabled",
            default_enabled,
        )

    assert captured == {
        "terms": ["agent", "evidence"],
        "local_limit": 25,
        "query": "Agent Evidence agent",
        "external_limit": 25,
    }
    assert response.external_status == "completed"
    assert [item.source_id for item in response.items] == [
        "external-top",
        "local-high",
        "external-mid",
        "local-low",
    ]


def test_literature_search_clamps_low_limit_and_truncates_results(monkeypatch) -> None:
    from backend.research.schemas import LiteratureSearchItem

    captured = {}

    def search_item(source_id, score):
        return LiteratureSearchItem(
            provider="local",
            source_id=source_id,
            title=source_id,
            authors=[],
            year=None,
            venue="",
            url="",
            abstract="",
            score=score,
            metadata={},
        )

    def local_items(self, terms, limit):
        captured["terms"] = terms
        captured["local_limit"] = limit
        return [
            search_item("local-low", 2.0),
            search_item("local-high", 7.0),
        ]

    def external_items(self, query, limit):
        raise AssertionError("external search should not run")

    monkeypatch.setattr(LiteratureSearchService, "_search_local", local_items)
    monkeypatch.setattr(LiteratureSearchService, "_search_external", external_items)

    response = LiteratureSearchService(None).search(
        "Agent Evidence",
        limit=0,
        include_external=False,
    )

    assert captured == {"terms": ["agent", "evidence"], "local_limit": 1}
    assert response.external_status == "not_requested"
    assert [item.source_id for item in response.items] == ["local-high"]


def test_external_literature_provider_config_normalization() -> None:
    from backend.research.services import literature_search_service

    default_providers = literature_search_service.settings.external_literature_providers
    object.__setattr__(
        literature_search_service.settings,
        "external_literature_providers",
        " OpenAlex, arxiv, semantic-scholar, semanticscholar, unknown, openalex ",
    )
    try:
        providers = LiteratureSearchService(None)._external_providers()
    finally:
        object.__setattr__(
            literature_search_service.settings,
            "external_literature_providers",
            default_providers,
        )

    assert providers == ["openalex", "arxiv", "semantic_scholar"]


def test_external_literature_search_reports_not_configured_status() -> None:
    from backend.research.services import literature_search_service

    default_providers = literature_search_service.settings.external_literature_providers
    object.__setattr__(
        literature_search_service.settings,
        "external_literature_providers",
        " unknown, , unsupported ",
    )
    try:
        items, status = LiteratureSearchService(None)._search_external("agent", 5)
    finally:
        object.__setattr__(
            literature_search_service.settings,
            "external_literature_providers",
            default_providers,
        )

    assert items == []
    assert status == "not_configured"


def test_external_literature_search_reports_completed_status(monkeypatch) -> None:
    from backend.research.schemas import LiteratureSearchItem
    from backend.research.services import literature_search_service

    default_providers = literature_search_service.settings.external_literature_providers
    object.__setattr__(
        literature_search_service.settings,
        "external_literature_providers",
        "openalex,arxiv,semantic_scholar",
    )

    def provider_item(provider, score):
        return LiteratureSearchItem(
            provider=provider,
            source_id=f"{provider}-result",
            title=f"{provider} Result",
            authors=[],
            year=None,
            venue="",
            url="",
            abstract="",
            score=score,
            metadata={},
        )

    def openalex_items(self, query, limit):
        return [provider_item("openalex", 10.0)]

    def arxiv_items(self, query, limit):
        return [provider_item("arxiv", 9.5)]

    def semantic_scholar_items(self, query, limit):
        return [provider_item("semantic_scholar", 9.0)]

    monkeypatch.setattr(LiteratureSearchService, "_search_openalex", openalex_items)
    monkeypatch.setattr(LiteratureSearchService, "_search_arxiv", arxiv_items)
    monkeypatch.setattr(
        LiteratureSearchService,
        "_search_semantic_scholar",
        semantic_scholar_items,
    )

    try:
        items, status = LiteratureSearchService(None)._search_external("agent", 5)
    finally:
        object.__setattr__(
            literature_search_service.settings,
            "external_literature_providers",
            default_providers,
        )

    assert [item.provider for item in items] == [
        "openalex",
        "arxiv",
        "semantic_scholar",
    ]
    assert status == "completed"


def test_external_literature_search_returns_partial_status(monkeypatch) -> None:
    import requests

    from backend.research.schemas import LiteratureSearchItem
    from backend.research.services import literature_search_service

    default_providers = literature_search_service.settings.external_literature_providers
    object.__setattr__(
        literature_search_service.settings,
        "external_literature_providers",
        "openalex,arxiv,semantic_scholar",
    )

    def openalex_items(self, query, limit):
        return [
            LiteratureSearchItem(
                provider="openalex",
                source_id="openalex-result",
                title="OpenAlex Result",
                authors=[],
                year=None,
                venue="",
                url="",
                abstract="",
                score=10.0,
                metadata={},
            )
        ]

    def arxiv_failure(self, query, limit):
        raise requests.Timeout("arxiv unavailable")

    def semantic_scholar_items(self, query, limit):
        return [
            LiteratureSearchItem(
                provider="semantic_scholar",
                source_id="semantic-scholar-result",
                title="Semantic Scholar Result",
                authors=[],
                year=None,
                venue="",
                url="",
                abstract="",
                score=9.0,
                metadata={},
            )
        ]

    monkeypatch.setattr(LiteratureSearchService, "_search_openalex", openalex_items)
    monkeypatch.setattr(LiteratureSearchService, "_search_arxiv", arxiv_failure)
    monkeypatch.setattr(
        LiteratureSearchService,
        "_search_semantic_scholar",
        semantic_scholar_items,
    )

    try:
        items, status = LiteratureSearchService(None)._search_external("agent", 5)
    finally:
        object.__setattr__(
            literature_search_service.settings,
            "external_literature_providers",
            default_providers,
        )

    assert [item.provider for item in items] == ["openalex", "semantic_scholar"]
    assert status == ("partial:openalex:completed,arxiv:failed:Timeout,semantic_scholar:completed")


def test_external_literature_search_reports_failed_status(monkeypatch) -> None:
    import requests

    from backend.research.services import literature_search_service

    default_providers = literature_search_service.settings.external_literature_providers
    object.__setattr__(
        literature_search_service.settings,
        "external_literature_providers",
        "openalex,arxiv",
    )

    def openalex_failure(self, query, limit):
        raise requests.ConnectionError("openalex unavailable")

    def arxiv_parse_failure(self, query, limit):
        raise ElementTree.ParseError("invalid arxiv feed")

    monkeypatch.setattr(LiteratureSearchService, "_search_openalex", openalex_failure)
    monkeypatch.setattr(LiteratureSearchService, "_search_arxiv", arxiv_parse_failure)

    try:
        items, status = LiteratureSearchService(None)._search_external("agent", 5)
    finally:
        object.__setattr__(
            literature_search_service.settings,
            "external_literature_providers",
            default_providers,
        )

    assert items == []
    assert status == "failed:openalex:failed:ConnectionError,arxiv:failed:ParseError"


def test_openalex_literature_item_parser() -> None:
    payload = {
        "id": "https://openalex.org/W2601012345",
        "doi": "https://doi.org/10.0000/openalex-example",
        "title": "Evidence Grounded Research Assistants",
        "publication_year": 2026,
        "primary_location": {"source": {"display_name": "OpenAlex Venue"}},
        "cited_by_count": 17,
        "authorships": [
            {"author": {"display_name": "Ada Lovelace"}},
            {"author": {"display_name": "Grace Hopper"}},
            {"author": {"display_name": ""}},
        ],
        "abstract_inverted_index": {
            "Evidence": [0],
            "grounded": [1],
            "agents": [2],
        },
    }

    item = LiteratureSearchService(None)._openalex_item(payload, 1)

    assert item.provider == "openalex"
    assert item.source_id == "https://openalex.org/W2601012345"
    assert item.title == "Evidence Grounded Research Assistants"
    assert item.authors == ["Ada Lovelace", "Grace Hopper"]
    assert item.year == 2026
    assert item.venue == "OpenAlex Venue"
    assert item.url == "https://doi.org/10.0000/openalex-example"
    assert item.abstract == "Evidence grounded agents"
    assert item.score == 9.0
    assert item.metadata == {
        "cited_by_count": 17,
        "openalex_id": "https://openalex.org/W2601012345",
    }


def test_openalex_literature_item_parser_fallbacks() -> None:
    payload = {
        "id": "https://openalex.org/W9999999999",
        "display_name": "Fallback OpenAlex Work",
        "primary_location": {},
        "authorships": [
            {"author": {"display_name": ""}},
            {"author": {"display_name": "Ada Lovelace"}},
        ],
        "cited_by_count": None,
    }

    item = LiteratureSearchService(None)._openalex_item(payload, 15)

    assert item.provider == "openalex"
    assert item.source_id == "https://openalex.org/W9999999999"
    assert item.title == "Fallback OpenAlex Work"
    assert item.authors == ["Ada Lovelace"]
    assert item.year is None
    assert item.venue == ""
    assert item.url == "https://openalex.org/W9999999999"
    assert item.abstract == ""
    assert item.score == 1.0
    assert item.metadata == {
        "cited_by_count": None,
        "openalex_id": "https://openalex.org/W9999999999",
    }


def test_openalex_inverted_index_abstract_reconstruction_edges() -> None:
    inverted_index = {
        "zeta": [2],
        "alpha": [0],
        "override": [1],
        "beta": [1],
        "x" * 1300: [2000],
    }

    abstract = LiteratureSearchService(None)._abstract_from_inverted_index(inverted_index)

    assert abstract.startswith("alpha beta zeta")
    assert "override" not in abstract
    assert len(abstract) == 1200


def test_arxiv_literature_item_parser() -> None:
    namespace = {"atom": "http://www.w3.org/2005/Atom"}
    entry = ElementTree.fromstring(
        """<entry xmlns="http://www.w3.org/2005/Atom">
          <id>http://arxiv.org/abs/2601.01234v1</id>
          <published>2026-01-02T00:00:00Z</published>
          <title> Evidence Grounded Research Assistants </title>
          <summary> A short abstract about research agents. </summary>
          <author><name>Ada Lovelace</name></author>
          <author><name>Grace Hopper</name></author>
          <category term="cs.AI" />
        </entry>"""
    )
    item = LiteratureSearchService(None)._arxiv_item(entry, 0, namespace)
    assert item.provider == "arxiv"
    assert item.source_id.endswith("2601.01234v1")
    assert item.title == "Evidence Grounded Research Assistants"
    assert item.authors == ["Ada Lovelace", "Grace Hopper"]
    assert item.year == 2026
    assert item.metadata["categories"] == ["cs.AI"]


def test_arxiv_literature_item_parser_fallbacks() -> None:
    namespace = {"atom": "http://www.w3.org/2005/Atom"}
    long_summary = " ".join(["evidence"] * 300)
    entry = ElementTree.fromstring(
        f"""<entry xmlns="http://www.w3.org/2005/Atom">
          <id>http://arxiv.org/abs/2601.09999v2</id>
          <published>not-a-date</published>
          <title>    </title>
          <summary>{long_summary}</summary>
          <author><name>   </name></author>
          <category />
        </entry>"""
    )

    item = LiteratureSearchService(None)._arxiv_item(entry, 20, namespace)

    assert item.provider == "arxiv"
    assert item.source_id.endswith("2601.09999v2")
    assert item.title == "Untitled arXiv preprint"
    assert item.authors == []
    assert item.year is None
    assert item.venue == "arXiv"
    assert item.url == "http://arxiv.org/abs/2601.09999v2"
    assert len(item.abstract) == 1200
    assert item.score == 1.0
    assert item.metadata == {
        "published": "not-a-date",
        "categories": [],
    }


def test_semantic_scholar_literature_item_parser() -> None:
    payload = {
        "paperId": "s2-paper-id",
        "title": "Research Agents with Evidence",
        "authors": [{"name": "Alan Turing"}, {"name": "Katherine Johnson"}],
        "year": 2026,
        "venue": "ACL",
        "url": "https://www.semanticscholar.org/paper/s2-paper-id",
        "abstract": "A semantic scholar fixture.",
        "citationCount": 42,
        "externalIds": {"DOI": "10.0000/example"},
    }
    item = LiteratureSearchService(None)._semantic_scholar_item(payload, 0)
    assert item.provider == "semantic_scholar"
    assert item.source_id == "s2-paper-id"
    assert item.title == "Research Agents with Evidence"
    assert item.authors == ["Alan Turing", "Katherine Johnson"]
    assert item.year == 2026
    assert item.metadata["citation_count"] == 42


def test_semantic_scholar_literature_item_parser_fallbacks() -> None:
    payload = {
        "title": "",
        "authors": [{"name": ""}, {"name": "Ada Lovelace"}],
        "abstract": "A" * 1300,
        "citationCount": None,
        "externalIds": {"DOI": "10.0000/fallback"},
    }

    item = LiteratureSearchService(None)._semantic_scholar_item(payload, 2)

    assert item.provider == "semantic_scholar"
    assert item.source_id == "10.0000/fallback"
    assert item.title == "Untitled Semantic Scholar paper"
    assert item.authors == ["Ada Lovelace"]
    assert item.year is None
    assert item.venue == ""
    assert item.url == ""
    assert len(item.abstract) == 1200
    assert item.score == 7.0
    assert item.metadata == {
        "citation_count": None,
        "external_ids": {"DOI": "10.0000/fallback"},
    }


def test_paper_card_service_maps_evidence_and_fills_problem_fallback() -> None:
    client = TestClient(create_app())
    assert client.get("/health").status_code == 200
    marker = f"pytest-paper-card-{time.time_ns()}"

    session = SessionLocal()
    try:
        paper = Paper(
            id=marker,
            title="Paper Card Heuristic Contract",
            filename=f"{marker}.txt",
            status="processed",
        )
        session.add(paper)
        session.add_all(
            [
                Evidence(
                    id=f"{marker}-method",
                    paper_id=paper.id,
                    evidence_type="method",
                    text="M" * 520,
                    summary="",
                    confidence=0.3,
                ),
                Evidence(
                    id=f"{marker}-claim",
                    paper_id=paper.id,
                    evidence_type="claim",
                    text="claim text",
                    summary="Main contribution summary",
                    confidence=0.9,
                ),
                Evidence(
                    id=f"{marker}-future",
                    paper_id=paper.id,
                    evidence_type="future_work",
                    text="future work text",
                    summary="Future work summary",
                    confidence=0.7,
                ),
                Evidence(
                    id=f"{marker}-unknown",
                    paper_id=paper.id,
                    evidence_type="custom_signal",
                    text="custom text",
                    summary="Custom signal summary",
                    confidence=0.5,
                ),
            ]
        )
        session.commit()

        card = PaperCardService(session).extract_heuristic_card(paper.id)

        assert card.extraction_model == "heuristic_v0"
        assert card.extraction_status == "completed"
        assert card.problem_json["items"] == [
            {
                "text": "M" * 500,
                "evidence_ids": [f"{marker}-method"],
                "confidence": 0.19999999999999998,
            }
        ]
        assert card.method_json["items"][0]["evidence_ids"] == [f"{marker}-method"]
        assert card.contributions_json["items"] == [
            {
                "text": "Main contribution summary",
                "evidence_ids": [f"{marker}-claim"],
                "confidence": 0.9,
            }
        ]
        assert card.future_work_json["items"][0]["text"] == "Future work summary"
        assert card.motivation_json == {"items": []}
        assert card.keywords_json == {"items": ["claim", "custom_signal", "future_work", "method"]}
    finally:
        session.close()


def test_paper_card_service_reports_missing_inputs() -> None:
    client = TestClient(create_app())
    assert client.get("/health").status_code == 200
    marker = f"pytest-paper-card-empty-{time.time_ns()}"

    session = SessionLocal()
    try:
        service = PaperCardService(session)
        try:
            service.extract_heuristic_card(f"{marker}-missing")
        except ValueError as exc:
            assert str(exc) == "Paper not found"
        else:
            raise AssertionError("missing paper should raise")

        session.add(Paper(id=marker, title="No Evidence Paper", status="processed"))
        session.commit()
        try:
            service.extract_heuristic_card(marker)
        except ValueError as exc:
            assert str(exc) == "Paper has no evidence records. Ingest or reprocess it first."
        else:
            raise AssertionError("paper without evidence should raise")
    finally:
        session.close()


def test_extract_paper_card_from_evidence() -> None:
    client = TestClient(create_app())
    content = b"""Paper Card Extraction Test

Abstract
This paper proposes a research assistant that turns evidence into paper cards.

Introduction
The problem is that raw chunks are too low-level for idea generation.

Method
The system maps evidence records into structured paper-card fields.

Conclusion
Future work should replace heuristic extraction with LLM structured extraction.
"""
    upload = client.post(
        "/research/papers/upload",
        files={"file": ("paper_card_test.txt", content, "text/plain")},
    )
    assert upload.status_code == 200
    paper_id = upload.json()["paper"]["id"]

    extract = client.post(f"/research/papers/{paper_id}/card/extract")
    assert extract.status_code == 200
    card = extract.json()
    assert card["paper_id"] == paper_id
    assert card["extraction_status"] == "completed"
    assert card["payload"]["problem"]
    assert card["payload"]["method"]
    assert card["payload"]["future_work"]

    fetched = client.get(f"/research/papers/{paper_id}/card")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == card["id"]


def test_gap_service_builds_titles_reasons_and_approaches() -> None:
    service = GapService(None)
    paper = Paper(title="Evidence Grounded Agents")
    long_summary = " ".join(["limitation"] * 20)
    limitation = Evidence(
        id="evidence-limitation",
        evidence_type="limitation",
        text="raw limitation text",
        summary=long_summary,
    )
    future_work = Evidence(
        id="evidence-future",
        evidence_type="future_work",
        text="future work text",
        summary="extend the agent to citations",
    )
    problem = Evidence(
        id="evidence-problem",
        evidence_type="problem",
        text="problem framing text",
        summary="agents miss grounding",
    )

    title = service._build_title(limitation)

    assert title.startswith("Address limitation: limitation limitation")
    assert title.endswith("...")
    assert len(title) <= len("Address limitation: ") + 80
    assert "Evidence Grounded Agents" in service._why_important(limitation, paper)
    assert service._why_unsolved(future_work).startswith("The source frames this as future work")
    assert service._why_unsolved(problem).startswith("The source motivates the problem")
    assert service._possible_approaches(limitation) == [
        "Design a method variant that targets the stated limitation.",
        "Build an evaluation slice that isolates the limitation.",
    ]
    assert service._possible_approaches(future_work)[0].startswith("Turn the future-work direction")
    assert service._possible_approaches(problem)[0].startswith("Formalize the problem")


def test_idea_service_builds_variants_and_preserves_lineage() -> None:
    service = IdeaService(None)
    gap = ResearchGap(
        id="gap-lineage",
        title="Address limitation: " + "retrieval grounding " * 10,
        description="Current agents do not preserve evidence-grounded claims.",
        why_important="This gap matters for trustworthy research drafting.",
        source_paper_ids_json=["paper-a"],
        evidence_ids_json=["evidence-a", "evidence-b"],
    )

    method_idea = service._build_idea(gap, 0)
    evaluation_idea = service._build_idea(gap, 1)

    assert service._shorten("  one\n two\t three  ", 20) == "one two three"
    assert service._shorten("x" * 80, 10) == "xxxxxxx..."
    assert method_idea.title.startswith("Evidence-Guided Study for Address limitation")
    assert evaluation_idea.title.startswith("Evaluation-Centered Study for Address limitation")
    assert len(method_idea.title) <= len("Evidence-Guided Study for ") + 72
    assert method_idea.related_gap_ids_json == ["gap-lineage"]
    assert method_idea.related_paper_ids_json == ["paper-a"]
    assert method_idea.evidence_ids_json == ["evidence-a", "evidence-b"]
    assert "targeted method improvement" in method_idea.research_question
    assert "evaluation protocol" in evaluation_idea.research_question
    assert method_idea.score_json["overall_score"] == 3.4
    assert method_idea.status == "draft"
    assert method_idea.version == 1


def test_mine_research_gaps_from_evidence() -> None:
    client = TestClient(create_app())
    content = b"""Gap Mining Test Paper

Introduction
Current research assistants still struggle to convert raw literature into testable research gaps.

Method
The system stores evidence as first-class records.

Limitations
This preliminary version does not yet check novelty against external literature.

Conclusion
Future work should connect gap mining to idea generation and reviewer simulation.
"""
    upload = client.post(
        "/research/papers/upload",
        files={"file": ("gap_mining_test.txt", content, "text/plain")},
    )
    assert upload.status_code == 200
    paper_id = upload.json()["paper"]["id"]

    response = client.post("/research/gaps/mine", json={"paper_ids": [paper_id], "max_gaps": 5})
    assert response.status_code == 200
    body = response.json()
    assert body["gaps"]
    assert any(gap["gap_type"] in {"method_gap", "application_gap"} for gap in body["gaps"])
    assert all(gap["evidence_ids"] for gap in body["gaps"])

    gap_id = body["gaps"][0]["id"]
    fetched = client.get(f"/research/gaps/{gap_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == gap_id


def test_generate_ideas_from_gap() -> None:
    client = TestClient(create_app())
    content = b"""Idea Generation Test Paper

Introduction
Research assistants need a way to turn literature gaps into testable hypotheses.

Limitations
The current pipeline does not yet create executable experiments from generated ideas.

Conclusion
Future work should connect idea generation to reviewer criticism.
"""
    upload = client.post(
        "/research/papers/upload",
        files={"file": ("idea_generation_test.txt", content, "text/plain")},
    )
    assert upload.status_code == 200
    paper_id = upload.json()["paper"]["id"]

    gaps = client.post("/research/gaps/mine", json={"paper_ids": [paper_id], "max_gaps": 2})
    assert gaps.status_code == 200
    gap_id = gaps.json()["gaps"][0]["id"]

    generated = client.post(f"/research/gaps/{gap_id}/ideas")
    assert generated.status_code == 200
    body = generated.json()
    assert "structured adapter" in body["message"]
    assert len(body["ideas"]) == 2
    assert all(idea["related_gap_ids"] == [gap_id] for idea in body["ideas"])
    assert all(idea["evidence_ids"] for idea in body["ideas"])
    assert all(idea["score"]["overall_score"] for idea in body["ideas"])

    idea_id = body["ideas"][0]["id"]
    fetched = client.get(f"/research/ideas/{idea_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == idea_id


def test_review_and_experiment_services_create_traceable_outputs() -> None:
    client = TestClient(create_app())
    assert client.get("/health").status_code == 200
    marker = f"pytest-review-experiment-{time.time_ns()}"

    session = SessionLocal()
    try:
        idea = Idea(
            id=marker,
            title="Traceable Review Idea",
            research_question="Can evidence-grounded agents improve proposal trust?",
            core_hypothesis="Evidence-grounded planning improves trust.",
            method_sketch="Retrieve evidence before drafting each claim.",
            datasets_json=["ScholarBench"],
            baselines_json=["Source paper baseline"],
            metrics_json=["citation precision"],
            resource_requirements="Small benchmark slice",
            status="draft",
        )
        session.add(idea)
        session.commit()

        review_service = ReviewService(session)
        experiment_service = ExperimentService(session)
        for service in [review_service, experiment_service]:
            try:
                (
                    service.create_review(f"{marker}-missing")
                    if isinstance(service, ReviewService)
                    else service.create_plan(f"{marker}-missing")
                )
            except ValueError as exc:
                assert str(exc) == "Idea not found"
            else:
                raise AssertionError("missing idea should raise")

        review = review_service.create_review(idea.id)
        plan = experiment_service.create_plan(idea.id)

        refreshed_idea = session.get(Idea, idea.id)
        assert refreshed_idea is not None
        assert refreshed_idea.status == "experiment_planned"
        assert review.reviewer_type == "skeptical_area_chair_v0"
        assert review.decision == "revise"
        assert review.major_concerns_json
        assert review.action_items_json[0] == "Add a related-work collision check."
        assert plan.objective.endswith(idea.research_question)
        assert plan.hypothesis == idea.core_hypothesis
        assert plan.datasets_json == ["ScholarBench"]
        assert plan.main_experiment_json["name"] == "MVP gap-targeted experiment"
        assert plan.ablation_studies_json[0]["name"] == "Remove gap-targeted component"
        assert plan.timeline_json["week_1"] == "Build dataset slice and baseline harness."
        assert review_service.list_reviews_for_idea(idea.id)[0].id == review.id
        assert experiment_service.list_plans_for_idea(idea.id)[0].id == plan.id
    finally:
        session.close()


def test_review_and_experiment_plan_for_idea() -> None:
    client = TestClient(create_app())
    content = b"""Review Experiment Test Paper

Introduction
Research idea systems need evidence-backed review and experiment planning.

Limitations
The current assistant has not yet validated whether generated ideas are experimentally testable.

Conclusion
Future work should produce reviewer critiques and experiment plans.
"""
    upload = client.post(
        "/research/papers/upload",
        files={"file": ("review_experiment_test.txt", content, "text/plain")},
    )
    assert upload.status_code == 200
    paper_id = upload.json()["paper"]["id"]
    gaps = client.post("/research/gaps/mine", json={"paper_ids": [paper_id], "max_gaps": 2})
    gap_id = gaps.json()["gaps"][0]["id"]
    ideas = client.post(f"/research/gaps/{gap_id}/ideas")
    idea_id = ideas.json()["ideas"][0]["id"]

    review = client.post(f"/research/ideas/{idea_id}/review")
    assert review.status_code == 200
    review_body = review.json()
    assert review_body["decision"] == "revise"
    assert review_body["major_concerns"]
    assert review_body["required_experiments"]

    plan = client.post(f"/research/ideas/{idea_id}/experiment-plan")
    assert plan.status_code == 200
    plan_body = plan.json()
    assert plan_body["idea_id"] == idea_id
    assert plan_body["main_experiment"]
    assert plan_body["ablation_studies"]
    assert plan_body["expected_tables"]


def test_novelty_check_records_local_collision_screening() -> None:
    client = TestClient(create_app())
    content = b"""Novelty Check Test Paper

Introduction
Research ideas need collision screening against local evidence before claiming novelty.

Limitations
The assistant currently lacks external literature search for novelty validation.

Conclusion
Future work should compare generated ideas against recent preprints.
"""
    upload = client.post(
        "/research/papers/upload",
        files={"file": ("novelty_check_test.txt", content, "text/plain")},
    )
    assert upload.status_code == 200
    paper_id = upload.json()["paper"]["id"]
    gaps = client.post("/research/gaps/mine", json={"paper_ids": [paper_id], "max_gaps": 2})
    assert gaps.status_code == 200
    gap_id = gaps.json()["gaps"][0]["id"]
    ideas = client.post(f"/research/gaps/{gap_id}/ideas")
    assert ideas.status_code == 200
    idea_id = ideas.json()["ideas"][0]["id"]

    check = client.post(f"/research/ideas/{idea_id}/novelty-check?include_external=true")
    assert check.status_code == 200
    body = check.json()
    assert body["idea_id"] == idea_id
    assert body["status"] == "completed_literature_screening"
    assert body["risk_level"] in {"unknown", "low", "medium", "high"}
    assert "local_literature_search" in body["checked_sources"]
    assert "external_literature_search:disabled" in body["checked_sources"]
    assert "external_literature_search_disabled" in body["missing_searches"]
    assert body["recommended_actions"]
    assert any(signal["source_type"] == "literature" for signal in body["collision_signals"])

    checks = client.get(f"/research/ideas/{idea_id}/novelty-checks")
    assert checks.status_code == 200
    assert checks.json()[0]["id"] == body["id"]

    refresh = client.post(
        f"/research/ideas/{idea_id}/novelty-refresh",
        json={
            "include_external": True,
            "limit": 5,
            "query_override": "recent preprint novelty collision screening",
        },
    )
    assert refresh.status_code == 200
    refresh_body = refresh.json()
    assert refresh_body["status"] == "completed_external_novelty_refresh"
    assert "query_override:True" in refresh_body["checked_sources"]
    assert "novelty_mode:external_refresh" in refresh_body["checked_sources"]
    assert "external_literature_search_disabled" in refresh_body["missing_searches"]

    novelty_tasks = client.post(
        f"/research/ideas/{idea_id}/novelty-checks/{refresh_body['id']}/tasks",
        json={"created_by": "pytest"},
    )
    assert novelty_tasks.status_code == 200
    novelty_task_body = novelty_tasks.json()
    assert novelty_task_body["tasks"]
    assert novelty_task_body["tasks"][0]["owner_type"] == "novelty_check"
    assert novelty_task_body["tasks"][0]["due_phase"] == "novelty_follow_up"
    novelty_task_edges = client.get("/research/graph/edges?edge_type=novelty_check_creates_task")
    assert novelty_task_edges.status_code == 200
    assert novelty_task_edges.json()

    progress = client.get(f"/research/ideas/{idea_id}/progress")
    assert progress.status_code == 200
    progress_body = progress.json()
    assert progress_body["artifact_counts"]["novelty_follow_up_tasks"] >= 1
    assert progress_body["task_summary"]["by_owner_type"]["novelty_check"] >= 1


def test_novelty_service_scores_overlap_with_caps_and_weights() -> None:
    service = NoveltyService(None)

    assert service._score_overlap([]) == 0.0
    assert (
        service._score_overlap(
            [
                {"source_type": "evidence", "score": 99.0},
                {"source_type": "idea", "score": 9.0},
                {"source_type": "literature", "score": 4.0},
                {"source_type": "gap", "score": 2.0},
            ]
        )
        == 0.7314
    )
    assert (
        service._score_overlap([{"source_type": "literature", "score": 99.0} for _ in range(5)])
        == 1.0
    )


def test_novelty_service_external_overlap_score_respects_statuses() -> None:
    service = NoveltyService(None)

    def response(status: str, items: list[LiteratureSearchItem]) -> LiteratureSearchResponse:
        return LiteratureSearchResponse(
            query="agent novelty",
            local_status="completed",
            external_status=status,
            items=items,
            message="fixture",
        )

    assert service._external_overlap_score(response("not_requested", [])) is None
    assert service._external_overlap_score(response("disabled", [])) is None
    assert (
        service._external_overlap_score(
            response(
                "completed",
                [
                    LiteratureSearchItem(
                        provider="local", source_id="local", title="Local result", score=99.0
                    ),
                ],
            )
        )
        == 0.0
    )
    assert (
        service._external_overlap_score(
            response(
                "completed",
                [
                    LiteratureSearchItem(
                        provider="local", source_id="local", title="Local result", score=99.0
                    ),
                    LiteratureSearchItem(
                        provider="openalex",
                        source_id="openalex",
                        title="OpenAlex result",
                        score=12.0,
                    ),
                    LiteratureSearchItem(
                        provider="semantic_scholar",
                        source_id="s2",
                        title="Semantic Scholar result",
                        score=8.0,
                    ),
                ],
            )
        )
        == 0.45
    )


def test_novelty_service_missing_searches_risk_and_actions() -> None:
    service = NoveltyService(None)

    def response(status: str) -> LiteratureSearchResponse:
        return LiteratureSearchResponse(
            query="agent novelty",
            local_status="completed",
            external_status=status,
            items=[],
            message="fixture",
        )

    assert service._missing_searches(response("not_requested"), False)[0] == (
        "external_literature_search_not_requested"
    )
    assert service._missing_searches(response("disabled"), True)[0] == (
        "external_literature_search_disabled"
    )
    assert service._missing_searches(response("failed_timeout"), True)[0] == (
        "external_literature_search_failed_timeout"
    )
    assert service._missing_searches(response("completed"), True)[-1] == (
        "external_literature_search_needs_manual_review"
    )

    nearby_ideas = [ScoredItem(item=Idea(id="nearby-idea"), score=0.9, matched_terms=["agent"])]
    assert service._risk_level(0.0, []) == "unknown"
    assert service._risk_level(0.1, []) == "low"
    assert service._risk_level(0.36, []) == "medium"
    assert service._risk_level(0.46, nearby_ideas) == "high"
    assert service._recommended_actions("high")[0].startswith("Narrow the method")
    assert service._recommended_actions("unknown")[-1].startswith("Add more source papers")


def test_related_work_matrix_persists_overlap_rows_and_markdown() -> None:
    client = TestClient(create_app())
    content = b"""Related Work Matrix Test Paper

Abstract
Research assistants need a related work matrix that compares generated ideas with local evidence.

Introduction
The matrix should connect novelty claims, evidence grounded gaps, and literature search results.

Limitations
Current systems rarely preserve checked sources and missing search actions as durable artifacts.

Conclusion
Future research should export a traceable related work table for proposal writing.
"""
    upload = client.post(
        "/research/papers/upload",
        files={"file": ("related_work_matrix_test.txt", content, "text/plain")},
    )
    assert upload.status_code == 200
    paper_id = upload.json()["paper"]["id"]
    gaps = client.post("/research/gaps/mine", json={"paper_ids": [paper_id], "max_gaps": 1})
    assert gaps.status_code == 200
    gap_id = gaps.json()["gaps"][0]["id"]
    ideas = client.post(f"/research/gaps/{gap_id}/ideas")
    assert ideas.status_code == 200
    idea_id = ideas.json()["ideas"][0]["id"]

    matrix = client.post(
        f"/research/ideas/{idea_id}/related-work-matrix",
        json={"include_external": True, "limit": 5, "created_by": "pytest"},
    )
    assert matrix.status_code == 200
    body = matrix.json()
    assert body["idea_id"] == idea_id
    assert body["status"] == "completed_related_work_screening"
    assert body["items"]
    assert body["differentiators"]
    assert "local_literature_search" in body["checked_sources"]
    assert "external_literature_search:disabled" in body["checked_sources"]
    assert "external_literature_search_disabled" in body["missing_searches"]
    assert "# Related Work Matrix:" in body["markdown_export"]
    assert any(item["source_type"] == "literature" for item in body["items"])

    matrices = client.get(f"/research/ideas/{idea_id}/related-work-matrices")
    assert matrices.status_code == 200
    assert matrices.json()[0]["id"] == body["id"]

    fetched = client.get(f"/research/ideas/{idea_id}/related-work-matrices/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["summary"] == body["summary"]

    export = client.get(
        f"/research/ideas/{idea_id}/related-work-matrices/{body['id']}/export/markdown"
    )
    assert export.status_code == 200
    assert f"- Idea ID: `{idea_id}`" in export.text
    assert "## Missing Searches" in export.text


def test_related_work_service_build_query_cleans_defaults_and_clamps() -> None:
    service = RelatedWorkService(None)
    blank_idea = Idea(
        title="  ",
        research_question="\n\t",
        core_hypothesis="",
        method_sketch="",
        expected_contribution="",
        novelty_argument="",
        datasets_json=[],
        baselines_json=[],
        metrics_json=[],
    )

    assert service._build_query(blank_idea) == "research idea novelty evidence experiment"

    long_idea = Idea(
        title="  Evidence\nGrounded\tAgent  ",
        research_question="How can agents cite evidence?",
        core_hypothesis="traceable claim " * 200,
        method_sketch="retrieve then draft",
        expected_contribution="auditable related work",
        novelty_argument="evidence-first planning",
        datasets_json=["ScholarBench"],
        baselines_json=["vanilla agents"],
        metrics_json=["citation precision"],
    )

    query = service._build_query(long_idea)

    assert query.startswith("Evidence Grounded Agent How can agents cite evidence?")
    assert "\n" not in query
    assert "\t" not in query
    assert len(query) == 1600


def test_related_work_service_missing_searches_cover_external_statuses() -> None:
    service = RelatedWorkService(None)

    def response(status: str) -> LiteratureSearchResponse:
        return LiteratureSearchResponse(
            query="agent related work",
            local_status="completed",
            external_status=status,
            items=[],
            message="fixture",
        )

    assert service._missing_searches(response("not_requested"), include_external=False)[0] == (
        "external_literature_search_not_requested"
    )
    assert service._missing_searches(response("disabled"), include_external=True)[0] == (
        "external_literature_search_disabled"
    )
    assert service._missing_searches(response("failed_timeout"), include_external=True)[0] == (
        "external_literature_search_failed_timeout"
    )
    completed = service._missing_searches(response("completed"), include_external=True)
    assert completed[-1] == "external_literature_search_manual_review"


def test_related_work_service_rows_sort_truncate_and_preserve_metadata() -> None:
    service = RelatedWorkService(None)
    idea = Idea(
        id="idea-main",
        title="Evidence Grounded Agent",
        research_question="How can agents cite evidence?",
        core_hypothesis="Evidence grounded agents improve proposal trust.",
        method_sketch="Retrieve evidence before drafting claims.",
        expected_contribution="Traceable related work screening.",
        novelty_argument="citation faithful planning",
        datasets_json=["ScholarBench"],
        baselines_json=["vanilla agents"],
        metrics_json=["citation precision"],
    )
    evidences = [
        ScoredItem(
            item=Evidence(
                id=f"evidence-{index}",
                paper_id="paper-a",
                evidence_type="finding",
                text=f"Evidence text {index}",
                summary=f"Evidence summary {index}",
                confidence=0.8,
            ),
            score=score,
            matched_terms=["evidence", "agent"],
        )
        for index, score in enumerate([2.5, 9.5, 5.0, 10.0])
    ]
    gaps = [
        ScoredItem(
            item=ResearchGap(
                id=f"gap-{index}",
                title=f"Gap title {index}",
                gap_type="method_gap",
                risk_level="medium",
                source_paper_ids_json=["paper-a"],
            ),
            score=score,
            matched_terms=["gap", "agent"],
        )
        for index, score in enumerate([3.5, 6.5, 1.0, 8.5])
    ]
    ideas = [
        ScoredItem(
            item=Idea(
                id=f"other-idea-{index}",
                title=f"Other idea {index}",
                status="draft",
                version=index + 1,
                parent_idea_id="seed" if index else None,
            ),
            score=score,
            matched_terms=["idea", "agent"],
        )
        for index, score in enumerate([4.0, 7.0, 0.5, 9.0])
    ]
    literature_items = [
        LiteratureSearchItem(
            provider="openalex",
            source_id=f"paper-{index}",
            title=f"Evidence grounded agent paper {index}",
            authors=["Ada Lovelace"],
            year=2020 + index,
            venue="ACL",
            url=f"https://example.test/paper-{index}",
            abstract="Agents cite evidence before drafting related work.",
            score=score,
            metadata={"citation_count": index},
        )
        for index, score in enumerate([8.0, 12.0, 2.0, 11.0])
    ]

    rows = service._build_rows(
        idea=idea,
        evidences=evidences,
        gaps=gaps,
        ideas=ideas,
        literature_items=literature_items,
        limit=3,
    )

    assert len(rows) == 8
    assert [row["overlap_score"] for row in rows] == sorted(row["overlap_score"] for row in rows)[
        ::-1
    ]
    assert {row["source_id"] for row in rows}.isdisjoint(
        {"evidence-3", "gap-3", "other-idea-3", "paper-3"}
    )
    literature_row = next(row for row in rows if row["source_id"] == "paper-1")
    assert literature_row["source_type"] == "literature"
    assert literature_row["metadata"]["provider"] == "openalex"
    assert literature_row["metadata"]["citation_count"] == 1
    assert "evidence" in literature_row["shared_terms"]


def test_proposal_draft_service_summarizes_attached_artifacts() -> None:
    service = ProposalDraftService(None)
    idea = Idea(
        id="idea-proposal",
        title=" Evidence Grounded Proposal ",
        research_question="Can evidence-grounded agents improve proposal trust?",
        core_hypothesis="Evidence-grounded planning improves trust.",
        motivation="Researchers need auditable proposal drafts.",
        method_sketch="Retrieve evidence before drafting each claim.",
        expected_contribution="Traceable proposal generation.",
        novelty_argument="Evidence-first drafting changes the review assumption.",
        datasets_json=["ScholarBench"],
        baselines_json=["Source paper baseline"],
        metrics_json=["citation precision"],
        risks_json=["Nearest-work collision risk"],
        evidence_ids_json=["evidence-a", "evidence-b"],
    )
    matrix = RelatedWorkMatrix(
        id="matrix-proposal",
        idea_id=idea.id,
        items_json=[
            {"source_type": "literature", "title": "Nearest Paper", "overlap_score": 8.5},
            {"source_type": "gap", "title": "Nearby Gap", "overlap_score": 6.0},
        ],
        differentiators_json=["Change the assumption", "Measure citation precision"],
        missing_searches_json=["semantic_scholar_citation_chaining"],
        summary="Two nearest works were found.",
    )
    plan = ExperimentPlan(
        id="plan-proposal",
        idea_id=idea.id,
        objective="Test evidence-grounded planning.",
        hypothesis="Evidence grounding improves trust.",
        main_experiment_json={
            "name": "Trust MVP",
            "success_criterion": "citation precision improves without lowering task score",
        },
        failure_modes_json=["Baseline already solves the task"],
        timeline_json={"week_1": "Build trust harness", "week_2": "Run trust MVP"},
    )

    assert service._title(idea) == "Proposal Draft: Evidence Grounded Proposal"
    assert "2 overlap rows" in service._abstract(idea, matrix, plan)
    assert "citation precision improves" in service._experiment_summary(idea, plan)
    assert "Nearest rows: literature:Nearest Paper" in service._related_work_summary(matrix)
    assert "Differentiation checkpoints" in service._novelty_statement(idea, matrix)
    risk_mitigation = service._risk_mitigation(idea, matrix, plan)
    assert "semantic_scholar_citation_chaining" in risk_mitigation
    assert "Baseline already solves the task" in risk_mitigation
    milestones = service._milestone_plan(idea, matrix, plan)
    assert milestones[0]["deliverable"].startswith("Resolve missing related-work searches")
    assert milestones[1]["deliverable"] == "Build trust harness"


def test_proposal_review_service_scores_decisions_and_missing_evidence() -> None:
    service = ProposalReviewService(None)
    incomplete = ProposalDraft(
        id="draft-incomplete",
        idea_id="idea-proposal",
        title="Proposal Draft",
        abstract="Abstract",
        problem_statement="Problem",
        novelty_statement="Novelty",
        method_summary="Not specified.",
        experiment_summary="Not specified.",
        milestone_plan_json=[],
        evidence_ids_json=[],
        risk_mitigation="",
    )
    matrix = RelatedWorkMatrix(
        id="matrix-review",
        idea_id="idea-proposal",
        items_json=[{"title": "Nearest Paper"}],
        missing_searches_json=["arxiv_recent_preprints"],
    )
    complete = ProposalDraft(
        id="draft-complete",
        idea_id="idea-proposal",
        title="Proposal Draft",
        abstract="Abstract",
        problem_statement="Problem",
        novelty_statement="Novelty",
        related_work_matrix_id=matrix.id,
        experiment_plan_id="plan-proposal",
        method_summary="Method",
        experiment_summary="Experiment",
        milestone_plan_json=[{"window": "0-30 days"}],
        evidence_ids_json=["evidence-a"],
        risk_mitigation="- Risk is tracked",
    )

    assert service._readiness_score(incomplete, None) == 0.2
    assert service._decision(0.2, service._concerns(incomplete, None)) == "not_ready"
    assert service._missing_evidence(incomplete, None) == [
        "supporting_evidence_ids",
        "related_work_matrix",
        "experiment_plan",
    ]
    assert service._readiness_score(complete, matrix) == 0.92
    concerns = service._concerns(complete, matrix)
    assert concerns == ["Related-work screening still has missing searches: arxiv_recent_preprints"]
    assert service._decision(0.92, concerns) == "ready_for_advisor_review"
    required = service._required_revisions(complete, matrix)
    assert required[0] == "Resolve missing related-work searches before claiming novelty."
    assert service._missing_evidence(complete, matrix) == ["arxiv_recent_preprints"]


def test_proposal_revision_service_applies_review_actions_and_fallbacks() -> None:
    service = ProposalRevisionService(None)
    draft = ProposalDraft(
        id="draft-revision",
        idea_id="idea-proposal",
        title="Proposal Draft",
        abstract="Draft abstract",
        novelty_statement="Draft novelty",
        related_work_summary="Draft related work",
        experiment_summary="Draft experiment",
        risk_mitigation="- Draft risk",
        milestone_plan_json=[{"window": "0-30 days", "goal": "Validate", "deliverable": "Run"}],
    )
    review = ProposalReview(
        id="review-revision",
        proposal_draft_id=draft.id,
        idea_id=draft.idea_id,
        decision="revise",
        readiness_score=0.6,
        required_revisions_json=["Name the nearest paper", "Define a failure threshold"],
        missing_evidence_json=["related_work_matrix", "experiment_plan"],
    )

    assert service._applied_revisions(None)[0] == "Sharpened the proposal into falsifiable claims."
    assert service._missing_evidence_actions(None) == [
        "No missing evidence was flagged by the selected review."
    ]
    applied = service._applied_revisions(review)
    assert applied == [
        "Addressed review action: Name the nearest paper",
        "Addressed review action: Define a failure threshold",
    ]
    missing_actions = service._missing_evidence_actions(review)
    assert missing_actions == [
        "Resolve missing evidence item `related_work_matrix` before the next readiness review.",
        "Resolve missing evidence item `experiment_plan` before the next readiness review.",
    ]
    sections = service._revised_sections(draft, review, applied)
    assert "Reviewer decision `revise` with readiness score 0.6." in sections["abstract"]
    assert sections["milestone_plan"] == draft.milestone_plan_json
    assert service._summary(draft, review, applied, missing_actions).startswith(
        "Created a revised proposal artifact for draft draft-revision using review review-revision."
    )
    assert "without an attached review" in service._summary(draft, None, applied, missing_actions)


def test_project_delivery_loop_bundles_proposal_to_pilot_handoff() -> None:
    client = TestClient(create_app())
    content = b"""Proposal Draft Test Paper

Abstract
Research assistants should turn promising ideas into proposal drafts.

Introduction
Proposal writing needs a clear novelty claim, related work positioning, and executable experiments.

Method
The assistant should combine related work matrices with experiment plans and evidence ids.

Conclusion
Future work should preserve proposal drafts as reviewable artifacts.
"""
    upload = client.post(
        "/research/papers/upload",
        files={"file": ("proposal_draft_test.txt", content, "text/plain")},
    )
    assert upload.status_code == 200
    paper_id = upload.json()["paper"]["id"]
    workflow = client.post(
        "/research/workflows/literature-to-ideas",
        json={
            "paper_id": paper_id,
            "max_gaps": 1,
            "max_ideas_per_gap": 1,
            "include_markdown_export": False,
        },
    )
    assert workflow.status_code == 200
    idea_id = workflow.json()["ideas"][0]["id"]
    plan_id = workflow.json()["experiment_plans"][0]["id"]
    matrix = client.post(
        f"/research/ideas/{idea_id}/related-work-matrix",
        json={"include_external": True, "limit": 5, "created_by": "pytest"},
    )
    assert matrix.status_code == 200
    matrix_id = matrix.json()["id"]

    draft = client.post(
        f"/research/ideas/{idea_id}/proposal-draft",
        json={
            "related_work_matrix_id": matrix_id,
            "experiment_plan_id": plan_id,
            "created_by": "pytest",
        },
    )
    assert draft.status_code == 200
    body = draft.json()
    assert body["idea_id"] == idea_id
    assert body["related_work_matrix_id"] == matrix_id
    assert body["experiment_plan_id"] == plan_id
    assert body["milestone_plan"]
    assert "# Proposal Draft:" in body["markdown_export"]
    assert "## Related Work Positioning" in body["markdown_export"]
    assert "## Milestones" in body["markdown_export"]

    drafts = client.get(f"/research/ideas/{idea_id}/proposal-drafts")
    assert drafts.status_code == 200
    assert drafts.json()[0]["id"] == body["id"]

    fetched = client.get(f"/research/ideas/{idea_id}/proposal-drafts/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["title"] == body["title"]

    export = client.get(f"/research/ideas/{idea_id}/proposal-drafts/{body['id']}/export/markdown")
    assert export.status_code == 200
    assert f"- Idea ID: `{idea_id}`" in export.text
    assert "## Risks And Mitigation" in export.text

    review = client.post(
        f"/research/ideas/{idea_id}/proposal-drafts/{body['id']}/review",
        json={"reviewer_type": "advisor", "created_by": "pytest"},
    )
    assert review.status_code == 200
    review_body = review.json()
    assert review_body["proposal_draft_id"] == body["id"]
    assert review_body["idea_id"] == idea_id
    assert review_body["decision"] in {"ready_for_advisor_review", "revise", "not_ready"}
    assert review_body["readiness_score"] > 0
    assert review_body["strengths"]
    assert review_body["required_revisions"]
    assert "# Proposal Readiness Review:" in review_body["markdown_export"]

    reviews = client.get(f"/research/ideas/{idea_id}/proposal-drafts/{body['id']}/reviews")
    assert reviews.status_code == 200
    assert reviews.json()[0]["id"] == review_body["id"]

    review_export = client.get(
        f"/research/ideas/{idea_id}/proposal-drafts/{body['id']}/reviews/"
        f"{review_body['id']}/export/markdown"
    )
    assert review_export.status_code == 200
    assert "## Required Revisions" in review_export.text

    revision = client.post(
        f"/research/ideas/{idea_id}/proposal-drafts/{body['id']}/revise",
        json={"proposal_review_id": review_body["id"], "created_by": "pytest"},
    )
    assert revision.status_code == 200
    revision_body = revision.json()
    assert revision_body["proposal_draft_id"] == body["id"]
    assert revision_body["proposal_review_id"] == review_body["id"]
    assert revision_body["status"] == "revised_from_review"
    assert revision_body["applied_revisions"]
    assert revision_body["missing_evidence_actions"]
    assert "novelty_statement" in revision_body["revised_sections"]
    assert "# Proposal Revision:" in revision_body["markdown_export"]

    revisions = client.get(f"/research/ideas/{idea_id}/proposal-drafts/{body['id']}/revisions")
    assert revisions.status_code == 200
    assert revisions.json()[0]["id"] == revision_body["id"]

    revision_export = client.get(
        f"/research/ideas/{idea_id}/proposal-drafts/{body['id']}/revisions/"
        f"{revision_body['id']}/export/markdown"
    )
    assert revision_export.status_code == 200
    assert "## Applied Revisions" in revision_export.text

    task_generation = client.post(
        f"/research/ideas/{idea_id}/proposal-drafts/{body['id']}/revisions/"
        f"{revision_body['id']}/tasks",
        json={"created_by": "pytest"},
    )
    assert task_generation.status_code == 200
    task_body = task_generation.json()
    assert task_body["tasks"]
    assert task_body["tasks"][0]["owner_type"] == "proposal_revision"
    assert task_body["tasks"][0]["owner_id"] == revision_body["id"]

    task_id = task_body["tasks"][0]["id"]
    listed_tasks = client.get(f"/research/tasks?idea_id={idea_id}&owner_type=proposal_revision")
    assert listed_tasks.status_code == 200
    assert any(task["id"] == task_id for task in listed_tasks.json())

    fetched_task = client.get(f"/research/tasks/{task_id}")
    assert fetched_task.status_code == 200
    assert fetched_task.json()["status"] == "todo"

    updated_task = client.patch(
        f"/research/tasks/{task_id}",
        json={
            "status": "doing",
            "priority": "critical",
            "note": "Started the first execution pass.",
            "created_by": "pytest",
        },
    )
    assert updated_task.status_code == 200
    assert updated_task.json()["status"] == "doing"
    assert updated_task.json()["priority"] == "critical"

    manual_event = client.post(
        f"/research/tasks/{task_id}/events",
        json={
            "event_type": "progress",
            "note": "Collected baseline notes for the task.",
            "metadata": {"source": "pytest"},
            "created_by": "pytest",
        },
    )
    assert manual_event.status_code == 200
    assert manual_event.json()["event_type"] == "progress"

    task_events = client.get(f"/research/tasks/{task_id}/events")
    assert task_events.status_code == 200
    event_types = [event["event_type"] for event in task_events.json()]
    assert "created" in event_types
    assert "task_updated" in event_types
    assert "progress" in event_types

    experiment_run = client.post(
        f"/research/experiment-plans/{plan_id}/runs",
        json={
            "title": "Pytest MVP execution",
            "task_id": task_id,
            "status": "running",
            "dataset_snapshot": "pytest proposal draft fixture",
            "parameters": {"seed": 13, "runner": "pytest"},
            "metric_results": {"primary_metric": {"value": 0.71, "direction": "higher"}},
            "artifact_links": [{"label": "pytest log", "path": "tests/test_app.py"}],
            "notes": "Started the first reproducible experiment run.",
            "created_by": "pytest",
        },
    )
    assert experiment_run.status_code == 200
    run_body = experiment_run.json()
    assert run_body["experiment_plan_id"] == plan_id
    assert run_body["idea_id"] == idea_id
    assert run_body["task_id"] == task_id
    assert run_body["status"] == "running"
    assert "# Experiment Run:" in run_body["markdown_export"]

    updated_run = client.patch(
        f"/research/experiment-runs/{run_body['id']}",
        json={
            "status": "completed",
            "metric_results": {
                "primary_metric": {"value": 0.78, "direction": "higher"},
                "cost": {"value": 1.2, "unit": "gpu_hours"},
            },
            "conclusion": "The first run supports a small but measurable improvement.",
            "notes": "Completed the pytest execution loop.",
            "created_by": "pytest",
        },
    )
    assert updated_run.status_code == 200
    assert updated_run.json()["status"] == "completed"
    assert updated_run.json()["completed_at"] is not None

    plan_runs = client.get(f"/research/experiment-plans/{plan_id}/runs")
    assert plan_runs.status_code == 200
    assert plan_runs.json()[0]["id"] == run_body["id"]

    idea_runs = client.get(f"/research/ideas/{idea_id}/experiment-runs")
    assert idea_runs.status_code == 200
    assert idea_runs.json()[0]["id"] == run_body["id"]

    fetched_run = client.get(f"/research/experiment-runs/{run_body['id']}")
    assert fetched_run.status_code == 200
    assert fetched_run.json()["conclusion"]

    run_export = client.get(f"/research/experiment-runs/{run_body['id']}/export/markdown")
    assert run_export.status_code == 200
    assert "## Metrics" in run_export.text
    assert "## Conclusion" in run_export.text

    analysis = client.post(
        f"/research/experiment-runs/{run_body['id']}/analysis",
        json={"created_by": "pytest"},
    )
    assert analysis.status_code == 200
    analysis_body = analysis.json()
    assert analysis_body["experiment_run_id"] == run_body["id"]
    assert analysis_body["idea_id"] == idea_id
    assert analysis_body["decision"] == "supports_hypothesis"
    assert analysis_body["next_actions"]
    assert "# Experiment Analysis:" in analysis_body["markdown_export"]

    run_analyses = client.get(f"/research/experiment-runs/{run_body['id']}/analyses")
    assert run_analyses.status_code == 200
    assert run_analyses.json()[0]["id"] == analysis_body["id"]

    idea_analyses = client.get(f"/research/ideas/{idea_id}/experiment-analyses")
    assert idea_analyses.status_code == 200
    assert idea_analyses.json()[0]["id"] == analysis_body["id"]

    fetched_analysis = client.get(f"/research/experiment-analyses/{analysis_body['id']}")
    assert fetched_analysis.status_code == 200
    assert fetched_analysis.json()["confidence"] > 0

    analysis_export = client.get(
        f"/research/experiment-analyses/{analysis_body['id']}/export/markdown"
    )
    assert analysis_export.status_code == 200
    assert "## Next Actions" in analysis_export.text

    analysis_task_generation = client.post(
        f"/research/experiment-analyses/{analysis_body['id']}/tasks",
        json={"created_by": "pytest"},
    )
    assert analysis_task_generation.status_code == 200
    analysis_task_body = analysis_task_generation.json()
    assert analysis_task_body["tasks"]
    analysis_task_id = analysis_task_body["tasks"][0]["id"]
    assert analysis_task_body["tasks"][0]["owner_type"] == "experiment_analysis"
    assert analysis_task_body["tasks"][0]["owner_id"] == analysis_body["id"]

    analysis_task_events = client.get(f"/research/tasks/{analysis_task_id}/events")
    assert analysis_task_events.status_code == 200
    assert analysis_task_events.json()[0]["event_type"] == "created"

    task_events_after_run = client.get(f"/research/tasks/{task_id}/events")
    assert task_events_after_run.status_code == 200
    event_types_after_run = [event["event_type"] for event in task_events_after_run.json()]
    assert "experiment_run_created" in event_types_after_run
    assert "experiment_run_updated" in event_types_after_run
    assert "experiment_analysis_created" in event_types_after_run

    snapshot = client.post(
        "/research/tasks/snapshots",
        json={
            "title": "Pytest Research Task Board",
            "idea_id": idea_id,
            "owner_type": "proposal_revision",
            "created_by": "pytest",
        },
    )
    assert snapshot.status_code == 200
    snapshot_body = snapshot.json()
    assert task_id in snapshot_body["task_ids"]
    assert snapshot_body["summary"]["task_count"] >= len(task_body["tasks"])
    assert "# Pytest Research Task Board" in snapshot_body["markdown_export"]

    fetched_snapshot = client.get(f"/research/tasks/snapshots/{snapshot_body['id']}")
    assert fetched_snapshot.status_code == 200
    assert fetched_snapshot.json()["id"] == snapshot_body["id"]

    snapshot_export = client.get(f"/research/tasks/snapshots/{snapshot_body['id']}/export/markdown")
    assert snapshot_export.status_code == 200
    assert "## Next Actions" in snapshot_export.text

    decision_memo = client.post(
        f"/research/ideas/{idea_id}/decision-memo",
        json={"decision": "pursue", "created_by": "pytest"},
    )
    assert decision_memo.status_code == 200
    decision_memo_body = decision_memo.json()
    assert decision_memo_body["idea_id"] == idea_id
    assert decision_memo_body["decision"] == "pursue"
    assert decision_memo_body["rationale"]
    assert decision_memo_body["next_commitments"]
    assert "# Idea Decision Memo:" in decision_memo_body["markdown_export"]

    decision_memos = client.get(f"/research/ideas/{idea_id}/decision-memos")
    assert decision_memos.status_code == 200
    assert decision_memos.json()[0]["id"] == decision_memo_body["id"]

    decision_memo_export = client.get(
        f"/research/ideas/{idea_id}/decision-memos/{decision_memo_body['id']}/export/markdown"
    )
    assert decision_memo_export.status_code == 200
    assert "## Risk Register" in decision_memo_export.text

    decision_task_response = client.post(
        f"/research/ideas/{idea_id}/decision-memos/{decision_memo_body['id']}/tasks",
        json={"created_by": "pytest"},
    )
    assert decision_task_response.status_code == 200
    decision_task_body = decision_task_response.json()
    assert decision_task_body["tasks"]
    decision_task_id = decision_task_body["tasks"][0]["id"]
    assert decision_task_body["tasks"][0]["owner_type"] == "idea_decision_memo"

    assumption_audit = client.post(
        f"/research/ideas/{idea_id}/assumption-audit",
        json={"created_by": "pytest"},
    )
    assert assumption_audit.status_code == 200
    assumption_audit_body = assumption_audit.json()
    assert assumption_audit_body["idea_id"] == idea_id
    assert assumption_audit_body["assumptions"]
    assert "# Idea Assumption Audit:" in assumption_audit_body["markdown_export"]

    assumption_audit_export = client.get(
        f"/research/ideas/{idea_id}/assumption-audits/{assumption_audit_body['id']}/export/markdown"
    )
    assert assumption_audit_export.status_code == 200
    assert "## Assumptions" in assumption_audit_export.text

    evidence_ledger = client.post(
        f"/research/ideas/{idea_id}/evidence-ledger",
        json={"created_by": "pytest"},
    )
    assert evidence_ledger.status_code == 200
    evidence_ledger_body = evidence_ledger.json()
    assert evidence_ledger_body["idea_id"] == idea_id
    assert evidence_ledger_body["claims"]
    assert evidence_ledger_body["summary"]["claim_count"] >= 1
    assert evidence_ledger_body["coverage_score"] >= 0
    assert "# Evidence Ledger:" in evidence_ledger_body["markdown_export"]

    evidence_ledgers = client.get(f"/research/ideas/{idea_id}/evidence-ledgers")
    assert evidence_ledgers.status_code == 200
    assert evidence_ledgers.json()[0]["id"] == evidence_ledger_body["id"]

    fetched_ledger = client.get(
        f"/research/ideas/{idea_id}/evidence-ledgers/{evidence_ledger_body['id']}"
    )
    assert fetched_ledger.status_code == 200
    assert (
        fetched_ledger.json()["summary"]["claim_count"]
        == evidence_ledger_body["summary"]["claim_count"]
    )

    evidence_ledger_export = client.get(
        f"/research/ideas/{idea_id}/evidence-ledgers/{evidence_ledger_body['id']}/export/markdown"
    )
    assert evidence_ledger_export.status_code == 200
    assert "## Claims" in evidence_ledger_export.text

    evidence_task_generation = client.post(
        f"/research/ideas/{idea_id}/evidence-ledgers/{evidence_ledger_body['id']}/tasks",
        json={"created_by": "pytest"},
    )
    assert evidence_task_generation.status_code == 200
    evidence_task_body = evidence_task_generation.json()
    assert evidence_task_body["tasks"]
    evidence_task_id = evidence_task_body["tasks"][0]["id"]
    assert evidence_task_body["tasks"][0]["owner_type"] == "idea_evidence_ledger"
    assert evidence_task_body["tasks"][0]["owner_id"] == evidence_ledger_body["id"]
    assert evidence_task_body["tasks"][0]["due_phase"] == "evidence_follow_up"
    assert "coverage_score" in evidence_task_body["tasks"][0]["metadata"]

    evidence_tasks = client.get(
        f"/research/tasks?idea_id={idea_id}&owner_type=idea_evidence_ledger"
    )
    assert evidence_tasks.status_code == 200
    assert any(task["id"] == evidence_task_id for task in evidence_tasks.json())

    evidence_task_events = client.get(f"/research/tasks/{evidence_task_id}/events")
    assert evidence_task_events.status_code == 200
    assert evidence_task_events.json()[0]["event_type"] == "created"

    claim_id = evidence_ledger_body["claims"][0]["claim_id"]
    claim_packet = client.get(
        f"/research/ideas/{idea_id}/evidence-ledgers/{evidence_ledger_body['id']}"
        f"/claims/{claim_id}/validation-packet"
    )
    assert claim_packet.status_code == 200
    claim_packet_body = claim_packet.json()
    assert claim_packet_body["idea"]["id"] == idea_id
    assert claim_packet_body["ledger"]["id"] == evidence_ledger_body["id"]
    assert claim_packet_body["claim"]["claim_id"] == claim_id
    assert claim_packet_body["supporting_evidence"]
    assert claim_packet_body["validation_actions"]
    assert "evidence_ledger_tracks_claim" in claim_packet_body["graph_edge_summary"]
    assert "# Claim Validation Packet:" in claim_packet_body["markdown_export"]

    claim_queue = client.get(f"/research/claims/validation-queue?idea_id={idea_id}&limit=20")
    assert claim_queue.status_code == 200
    claim_queue_body = claim_queue.json()
    assert claim_queue_body["items"]
    assert claim_queue_body["summary"]["item_count"] == len(claim_queue_body["items"])
    assert any(
        item["ledger_id"] == evidence_ledger_body["id"] and item["claim_id"] == claim_id
        for item in claim_queue_body["items"]
    )
    assert "# Claim Validation Queue" in claim_queue_body["markdown_export"]

    claim_queue_tasks = client.post(
        "/research/claims/validation-queue/tasks",
        json={
            "idea_id": idea_id,
            "limit": 3,
            "priority_filter": ["critical", "high"],
            "created_by": "pytest",
        },
    )
    assert claim_queue_tasks.status_code == 200
    claim_queue_task_body = claim_queue_tasks.json()
    assert claim_queue_task_body["tasks"]
    claim_queue_task_id = claim_queue_task_body["tasks"][0]["id"]
    assert claim_queue_task_body["tasks"][0]["owner_type"] == "claim_validation_queue"
    assert claim_queue_task_body["tasks"][0]["owner_id"] == evidence_ledger_body["id"]
    assert claim_queue_task_body["tasks"][0]["due_phase"] == "claim_validation_follow_up"
    assert claim_queue_task_body["tasks"][0]["metadata"]["claim_id"]

    claim_queue_task_list = client.get(
        f"/research/tasks?idea_id={idea_id}&owner_type=claim_validation_queue"
    )
    assert claim_queue_task_list.status_code == 200
    assert any(task["id"] == claim_queue_task_id for task in claim_queue_task_list.json())

    graph_edge_types = [
        "idea_has_proposal_draft",
        "proposal_review_reviews_draft",
        "proposal_revision_addresses_review",
        "proposal_revision_creates_task",
        "task_board_snapshot_tracks_task",
        "experiment_plan_has_run",
        "task_records_experiment_run",
        "experiment_run_has_analysis",
        "task_records_experiment_analysis",
        "experiment_analysis_creates_task",
        "idea_has_decision_memo",
        "decision_memo_creates_task",
        "idea_has_assumption_audit",
        "idea_has_evidence_ledger",
        "evidence_ledger_tracks_claim",
        "evidence_supports_claim",
        "evidence_ledger_creates_task",
        "idea_has_claim_validation_queue",
        "claim_validation_queue_prioritizes_claim",
        "claim_validation_queue_creates_task",
    ]
    for edge_type in graph_edge_types:
        edges = client.get(f"/research/graph/edges?edge_type={edge_type}")
        assert edges.status_code == 200
        assert edges.json()

    lineage = client.get(f"/research/ideas/{idea_id}/lineage")
    assert lineage.status_code == 200
    lineage_body = lineage.json()
    assert lineage_body["idea"]["id"] == idea_id
    assert lineage_body["related_work_matrices"][0]["id"] == matrix_id
    assert lineage_body["proposal_drafts"][0]["id"] == body["id"]
    assert lineage_body["proposal_reviews"][0]["id"] == review_body["id"]
    assert lineage_body["proposal_revisions"][0]["id"] == revision_body["id"]
    assert lineage_body["experiment_runs"][0]["id"] == run_body["id"]
    assert lineage_body["experiment_analyses"][0]["id"] == analysis_body["id"]
    assert lineage_body["decision_memos"][0]["id"] == decision_memo_body["id"]
    assert lineage_body["assumption_audits"][0]["id"] == assumption_audit_body["id"]
    assert lineage_body["evidence_ledgers"][0]["id"] == evidence_ledger_body["id"]
    assert any(task["id"] == task_id for task in lineage_body["research_tasks"])
    assert any(task["id"] == analysis_task_id for task in lineage_body["research_tasks"])
    assert any(task["id"] == decision_task_id for task in lineage_body["research_tasks"])
    assert any(task["id"] == evidence_task_id for task in lineage_body["research_tasks"])
    assert any(task["id"] == claim_queue_task_id for task in lineage_body["research_tasks"])
    assert lineage_body["task_board_snapshots"][0]["id"] == snapshot_body["id"]
    assert lineage_body["graph_edge_summary"]["proposal_revision_creates_task"] > 0
    assert lineage_body["graph_edge_summary"]["experiment_plan_has_run"] > 0
    assert lineage_body["graph_edge_summary"]["experiment_run_has_analysis"] > 0
    assert lineage_body["graph_edge_summary"]["experiment_analysis_creates_task"] > 0
    assert lineage_body["graph_edge_summary"]["idea_has_decision_memo"] > 0
    assert lineage_body["graph_edge_summary"]["decision_memo_creates_task"] > 0
    assert lineage_body["graph_edge_summary"]["idea_has_assumption_audit"] > 0
    assert lineage_body["graph_edge_summary"]["idea_has_evidence_ledger"] > 0
    assert lineage_body["graph_edge_summary"]["evidence_ledger_tracks_claim"] > 0
    assert lineage_body["graph_edge_summary"]["evidence_ledger_creates_task"] > 0
    assert lineage_body["graph_edge_summary"]["claim_validation_queue_creates_task"] > 0
    assert "# Idea Lineage:" in lineage_body["markdown_export"]
    assert "## Experiment Runs" in lineage_body["markdown_export"]
    assert "## Experiment Analyses" in lineage_body["markdown_export"]
    assert "## Decision Memos" in lineage_body["markdown_export"]
    assert "## Assumption Audits" in lineage_body["markdown_export"]
    assert "## Evidence Ledgers" in lineage_body["markdown_export"]

    timeline = client.get(f"/research/ideas/{idea_id}/timeline")
    assert timeline.status_code == 200
    timeline_body = timeline.json()
    assert timeline_body["idea"]["id"] == idea_id
    event_types = {event["event_type"] for event in timeline_body["events"]}
    assert "idea_created" in event_types
    assert "experiment_analysis_created" in event_types
    assert "decision_memo_created" in event_types
    assert "evidence_ledger_created" in event_types
    assert "# Idea Timeline:" in timeline_body["markdown_export"]

    progress = client.get(f"/research/ideas/{idea_id}/progress")
    assert progress.status_code == 200
    progress_body = progress.json()
    assert progress_body["idea"]["id"] == idea_id
    assert progress_body["artifact_counts"]["experiment_runs"] >= 1
    assert progress_body["artifact_counts"]["experiment_analyses"] >= 1
    assert progress_body["artifact_counts"]["decision_memos"] >= 1
    assert progress_body["artifact_counts"]["assumption_audits"] >= 1
    assert progress_body["artifact_counts"]["evidence_ledgers"] >= 1
    assert progress_body["latest_artifacts"]["evidence_ledger"]["id"] == evidence_ledger_body["id"]
    assert progress_body["artifact_counts"]["analysis_follow_up_tasks"] >= 1
    assert progress_body["artifact_counts"]["decision_follow_up_tasks"] >= 1
    assert progress_body["artifact_counts"]["evidence_follow_up_tasks"] >= 1
    assert progress_body["artifact_counts"]["claim_validation_follow_up_tasks"] >= 1
    assert progress_body["task_summary"]["by_owner_type"]["claim_validation_queue"] >= 1
    assert progress_body["task_summary"]["next_tasks"]
    assert progress_body["experiment_summary"]["latest_analysis_decision"] == "supports_hypothesis"
    assert progress_body["recommended_next_step"]
    assert "# Idea Progress:" in progress_body["markdown_export"]

    research_packet = client.get(f"/research/ideas/{idea_id}/research-packet")
    assert research_packet.status_code == 200
    packet_body = research_packet.json()
    assert packet_body["idea"]["id"] == idea_id
    assert packet_body["latest_artifacts"]["decision_memo"]["id"] == decision_memo_body["id"]
    assert packet_body["latest_artifacts"]["assumption_audit"]["id"] == assumption_audit_body["id"]
    assert packet_body["latest_artifacts"]["evidence_ledger"]["id"] == evidence_ledger_body["id"]
    assert any(task["id"] == decision_task_id for task in packet_body["open_tasks"])
    assert any(task["id"] == evidence_task_id for task in packet_body["open_tasks"])
    assert any(task["id"] == claim_queue_task_id for task in packet_body["open_tasks"])
    assert "idea_has_assumption_audit" in packet_body["graph_edge_summary"]
    assert "idea_has_evidence_ledger" in packet_body["graph_edge_summary"]
    assert "evidence_ledger_creates_task" in packet_body["graph_edge_summary"]
    assert "claim_validation_queue_creates_task" in packet_body["graph_edge_summary"]
    assert "# Idea Research Packet:" in packet_body["markdown_export"]
    assert "## Packet Use" in packet_body["markdown_export"]

    claim_validation_result = client.post(
        f"/research/tasks/{claim_queue_task_id}/claim-validation-result",
        json={
            "validation_status": "needs_more_evidence",
            "evidence_ids": [claim_packet_body["supporting_evidence"][0]["id"]],
            "notes": "Need one more independent support source before advisor discussion.",
            "next_action": "Run a targeted literature search for an independent validation.",
            "created_by": "pytest",
        },
    )
    assert claim_validation_result.status_code == 200
    claim_validation_result_body = claim_validation_result.json()
    assert claim_validation_result_body["event_type"] == "claim_validation_result"
    assert claim_validation_result_body["metadata"]["validation_status"] == "needs_more_evidence"
    assert claim_validation_result_body["metadata"]["claim_id"]

    updated_claim_task = client.get(f"/research/tasks/{claim_queue_task_id}")
    assert updated_claim_task.status_code == 200
    assert updated_claim_task.json()["status"] == "done"

    claim_task_events = client.get(f"/research/tasks/{claim_queue_task_id}/events")
    assert claim_task_events.status_code == 200
    claim_task_event_types = {event["event_type"] for event in claim_task_events.json()}
    assert "claim_validation_result" in claim_task_event_types
    assert "task_updated" in claim_task_event_types

    progress_after_claim_result = client.get(f"/research/ideas/{idea_id}/progress")
    assert progress_after_claim_result.status_code == 200
    assert (
        progress_after_claim_result.json()["artifact_counts"]["claim_validation_result_events"] >= 1
    )

    ranking_after_claim_result = client.post(
        "/research/ideas/rank",
        json={"idea_ids": [idea_id], "deduplicate_lineage": False},
    )
    assert ranking_after_claim_result.status_code == 200
    ranked_after_claim = ranking_after_claim_result.json()["ranked_ideas"][0]
    assert ranked_after_claim["score_breakdown"]["claim_validation_needs_more_evidence"] >= 1
    assert ranked_after_claim["score_breakdown"]["claim_validation_adjustment"] < 0
    assert any(
        "Claim validation found evidence gaps" in item for item in ranked_after_claim["rationale"]
    )

    readiness = client.get(f"/research/ideas/{idea_id}/readiness")
    assert readiness.status_code == 200
    readiness_body = readiness.json()
    assert readiness_body["idea"]["id"] == idea_id
    assert readiness_body["readiness_score"] > 0
    assert readiness_body["decision"] in {
        "ready_for_execution",
        "needs_targeted_work",
        "needs_work",
        "park",
        "reject",
    }
    assert "proposal" in readiness_body["score_breakdown"]
    assert "claim_validation" in readiness_body["score_breakdown"]
    assert (
        readiness_body["score_breakdown"]["claim_validation"]["by_status"]["needs_more_evidence"]
        >= 1
    )
    assert any(
        "Claim validation found evidence gaps" in item for item in readiness_body["blockers"]
    )
    assert "# Idea Readiness:" in readiness_body["markdown_export"]

    quality_gate = client.get(f"/research/ideas/{idea_id}/quality-gate")
    assert quality_gate.status_code == 200
    quality_gate_body = quality_gate.json()
    assert quality_gate_body["idea"]["id"] == idea_id
    assert quality_gate_body["gate_score"] >= 0
    assert quality_gate_body["decision"] in {
        "advance_to_execution",
        "needs_targeted_revision",
        "de_risk_novelty",
        "revise_before_investment",
        "park",
        "reject",
    }
    assert "novelty" in quality_gate_body["score_breakdown"]
    assert "claim_validation" in quality_gate_body["score_breakdown"]
    assert (
        quality_gate_body["score_breakdown"]["claim_validation"]["by_status"]["needs_more_evidence"]
        >= 1
    )
    assert any(
        item["name"] == "claim_validation_result" and item["satisfied"]
        for item in quality_gate_body["required_evidence"]
    )
    assert any(
        "Claim validation found evidence gaps" in item
        for item in quality_gate_body["blocking_risks"]
    )
    assert any(
        "targeted literature search" in item.lower()
        for item in quality_gate_body["recommended_actions"]
    )
    assert quality_gate_body["required_evidence"]
    assert quality_gate_body["recommended_actions"]
    assert "# Idea Quality Gate:" in quality_gate_body["markdown_export"]

    quality_overview = client.get("/research/quality/overview?limit=20")
    assert quality_overview.status_code == 200
    quality_overview_body = quality_overview.json()
    assert quality_overview_body["idea_count"] >= 1
    assert quality_overview_body["average_gate_score"] >= 0
    assert quality_overview_body["decision_counts"]
    assert "# Project Quality Gate Overview" in quality_overview_body["markdown_export"]

    triage_brief = client.get("/research/triage/brief?idea_limit=20&opportunity_limit=5")
    assert triage_brief.status_code == 200
    triage_body = triage_brief.json()
    assert triage_body["idea_count"] >= 1
    assert triage_body["next_actions"]
    assert "# Project Triage Brief" in triage_body["markdown_export"]

    triage_markdown = client.get("/research/triage/brief/export/markdown")
    assert triage_markdown.status_code == 200
    assert "text/markdown" in triage_markdown.headers["content-type"]
    assert "# Project Triage Brief" in triage_markdown.text

    baseline_triage_snapshot = client.post(
        "/research/triage/snapshots",
        json={
            "title": "Pytest Baseline Project Triage Snapshot",
            "idea_limit": 20,
            "opportunity_limit": 5,
            "created_by": "pytest",
        },
    )
    assert baseline_triage_snapshot.status_code == 200
    baseline_triage_snapshot_body = baseline_triage_snapshot.json()
    assert baseline_triage_snapshot_body["summary"]["idea_count"] >= 1

    triage_tasks = client.post(
        "/research/triage/brief/tasks",
        json={"limit": 4, "include_risks": True, "created_by": "pytest"},
    )
    assert triage_tasks.status_code == 200
    triage_task_body = triage_tasks.json()
    assert triage_task_body["tasks"]
    assert all(task["owner_type"] == "project_triage" for task in triage_task_body["tasks"])

    triage_task_edges = client.get("/research/graph/edges?edge_type=project_triage_creates_task")
    assert triage_task_edges.status_code == 200
    assert triage_task_edges.json()

    listed_triage_tasks = client.get("/research/tasks?owner_type=project_triage")
    assert listed_triage_tasks.status_code == 200
    assert listed_triage_tasks.json()

    triage_snapshot = client.post(
        "/research/triage/snapshots",
        json={
            "title": "Pytest Project Triage Snapshot",
            "idea_limit": 20,
            "opportunity_limit": 5,
            "created_by": "pytest",
        },
    )
    assert triage_snapshot.status_code == 200
    triage_snapshot_body = triage_snapshot.json()
    assert triage_snapshot_body["title"] == "Pytest Project Triage Snapshot"
    assert triage_snapshot_body["summary"]["idea_count"] >= 1
    assert triage_snapshot_body["summary"]["next_action_count"] >= 1
    assert triage_snapshot_body["source_ids"]["project_triage_task_ids"]
    assert (
        "# Project Triage Snapshot: Pytest Project Triage Snapshot"
        in (triage_snapshot_body["markdown_export"])
    )

    listed_triage_snapshots = client.get("/research/triage/snapshots?limit=5")
    assert listed_triage_snapshots.status_code == 200
    assert any(item["id"] == triage_snapshot_body["id"] for item in listed_triage_snapshots.json())

    fetched_triage_snapshot = client.get(f"/research/triage/snapshots/{triage_snapshot_body['id']}")
    assert fetched_triage_snapshot.status_code == 200
    assert fetched_triage_snapshot.json()["id"] == triage_snapshot_body["id"]

    triage_snapshot_markdown = client.get(
        f"/research/triage/snapshots/{triage_snapshot_body['id']}/export/markdown"
    )
    assert triage_snapshot_markdown.status_code == 200
    assert triage_snapshot_markdown.headers["content-type"].startswith("text/markdown")
    assert "## Source IDs" in triage_snapshot_markdown.text

    triage_snapshot_comparison = client.post(
        "/research/triage/snapshots/compare",
        json={
            "baseline_snapshot_id": baseline_triage_snapshot_body["id"],
            "candidate_snapshot_id": triage_snapshot_body["id"],
        },
    )
    assert triage_snapshot_comparison.status_code == 200
    comparison_body = triage_snapshot_comparison.json()
    assert comparison_body["baseline_snapshot_id"] == baseline_triage_snapshot_body["id"]
    assert comparison_body["candidate_snapshot_id"] == triage_snapshot_body["id"]
    assert "open_task_count" in comparison_body["metric_delta"]
    assert "Compared project triage snapshots" in comparison_body["summary"]
    assert "# Project Triage Snapshot Comparison" in comparison_body["markdown_export"]

    triage_snapshot_comparison_markdown = client.post(
        "/research/triage/snapshots/compare/export/markdown",
        json={
            "baseline_snapshot_id": baseline_triage_snapshot_body["id"],
            "candidate_snapshot_id": triage_snapshot_body["id"],
        },
    )
    assert triage_snapshot_comparison_markdown.status_code == 200
    assert triage_snapshot_comparison_markdown.headers["content-type"].startswith("text/markdown")
    assert "## Metric Delta" in triage_snapshot_comparison_markdown.text

    triage_comparison_tasks = client.post(
        "/research/triage/snapshots/compare/tasks",
        json={
            "baseline_snapshot_id": baseline_triage_snapshot_body["id"],
            "candidate_snapshot_id": triage_snapshot_body["id"],
            "limit": 4,
            "include_focus": True,
            "include_risks": True,
            "created_by": "pytest",
        },
    )
    assert triage_comparison_tasks.status_code == 200
    triage_comparison_task_body = triage_comparison_tasks.json()
    assert triage_comparison_task_body["tasks"]
    assert all(
        task["owner_type"] == "project_triage_comparison"
        for task in triage_comparison_task_body["tasks"]
    )
    assert all(
        task["due_phase"] == "triage_change_follow_up"
        for task in triage_comparison_task_body["tasks"]
    )

    triage_comparison_task_edges = client.get(
        "/research/graph/edges?edge_type=project_triage_comparison_creates_task"
    )
    assert triage_comparison_task_edges.status_code == 200
    assert triage_comparison_task_edges.json()

    quality_gate_tasks = client.post(
        f"/research/ideas/{idea_id}/quality-gate/tasks",
        json={"created_by": "pytest"},
    )
    assert quality_gate_tasks.status_code == 200
    quality_gate_task_body = quality_gate_tasks.json()
    assert quality_gate_task_body["tasks"]
    assert quality_gate_task_body["tasks"][0]["owner_type"] == "idea_quality_gate"
    assert quality_gate_task_body["tasks"][0]["owner_id"] == idea_id

    quality_gate_task_edges = client.get(
        "/research/graph/edges?edge_type=quality_gate_creates_task"
    )
    assert quality_gate_task_edges.status_code == 200
    assert quality_gate_task_edges.json()

    progress_after_quality_gate_tasks = client.get(f"/research/ideas/{idea_id}/progress")
    assert progress_after_quality_gate_tasks.status_code == 200
    progress_after_quality_body = progress_after_quality_gate_tasks.json()
    assert progress_after_quality_body["artifact_counts"]["quality_gate_follow_up_tasks"] >= 1
    assert progress_after_quality_body["task_summary"]["by_owner_type"]["idea_quality_gate"] >= 1

    packet_after_quality_gate_tasks = client.get(f"/research/ideas/{idea_id}/research-packet")
    assert packet_after_quality_gate_tasks.status_code == 200
    packet_after_quality_body = packet_after_quality_gate_tasks.json()
    assert packet_after_quality_body["graph_edge_summary"]["quality_gate_creates_task"] >= 1

    project_quality_tasks = client.post(
        "/research/quality/overview/tasks",
        json={"limit": 3, "actions_per_idea": 1, "created_by": "pytest"},
    )
    assert project_quality_tasks.status_code == 200
    project_quality_task_body = project_quality_tasks.json()
    assert project_quality_task_body["tasks"]
    assert all(
        task["owner_type"] == "idea_quality_gate" for task in project_quality_task_body["tasks"]
    )

    readiness_tasks = client.post(
        f"/research/ideas/{idea_id}/readiness/tasks",
        json={"created_by": "pytest"},
    )
    assert readiness_tasks.status_code == 200
    readiness_task_body = readiness_tasks.json()
    assert readiness_task_body["tasks"]
    assert readiness_task_body["tasks"][0]["owner_type"] == "idea_readiness"
    assert readiness_task_body["tasks"][0]["owner_id"] == idea_id

    readiness_task_edges = client.get("/research/graph/edges?edge_type=idea_readiness_creates_task")
    assert readiness_task_edges.status_code == 200
    assert readiness_task_edges.json()

    progress_after_readiness_tasks = client.get(f"/research/ideas/{idea_id}/progress")
    assert progress_after_readiness_tasks.status_code == 200
    progress_after_body = progress_after_readiness_tasks.json()
    assert progress_after_body["artifact_counts"]["readiness_follow_up_tasks"] >= 1
    assert progress_after_body["task_summary"]["by_owner_type"]["idea_readiness"] >= 1

    packet_after_readiness_tasks = client.get(f"/research/ideas/{idea_id}/research-packet")
    assert packet_after_readiness_tasks.status_code == 200
    packet_after_body = packet_after_readiness_tasks.json()
    assert packet_after_body["graph_edge_summary"]["idea_readiness_creates_task"] >= 1

    bundle = client.get(f"/research/ideas/{idea_id}/export/bundle")
    assert bundle.status_code == 200
    assert bundle.headers["content-type"] == "application/zip"
    assert "idea-" in bundle.headers["content-disposition"]
    with zipfile.ZipFile(io.BytesIO(bundle.content)) as archive:
        names = set(archive.namelist())
        assert "README.md" in names
        assert "01-idea-dossier.md" in names
        assert "02-lineage.md" in names
        assert "03-progress.md" in names
        assert "04-research-packet.md" in names
        assert "05-readiness.md" in names
        assert "06-timeline.md" in names
        assert "metadata/timeline.json" in names
        assert f"artifacts/proposals/drafts/proposal-draft-{body['id']}.md" in names
        assert (f"artifacts/proposals/reviews/proposal-review-{review_body['id']}.md") in names
        assert f"artifacts/decisions/decision-memo-{decision_memo_body['id']}.md" in names
        assert (f"artifacts/assumptions/assumption-audit-{assumption_audit_body['id']}.md") in names
        assert (
            f"artifacts/evidence-ledgers/evidence-ledger-{evidence_ledger_body['id']}.md" in names
        )
        manifest = json.loads(archive.read("metadata/manifest.json"))
        assert manifest["idea_id"] == idea_id
        assert manifest["artifact_counts"]["proposal_drafts"] >= 1
        assert manifest["artifact_counts"]["evidence_ledgers"] >= 1
        assert manifest["readiness"]["score"] == readiness_body["readiness_score"]
        assert manifest["timeline_event_count"] >= len(timeline_body["events"])

    readiness_overview = client.get("/research/readiness/overview?limit=20")
    assert readiness_overview.status_code == 200
    readiness_overview_body = readiness_overview.json()
    assert readiness_overview_body["idea_count"] >= 1
    assert readiness_overview_body["average_readiness"] >= 0
    assert readiness_overview_body["decision_counts"]
    assert "# Project Readiness Overview" in readiness_overview_body["markdown_export"]

    overview = client.get("/research/progress/overview")
    assert overview.status_code == 200
    overview_body = overview.json()
    assert overview_body["idea_count"] >= 1
    assert overview_body["task_summary"]["open_task_count"] >= 1
    assert overview_body["task_summary"]["claim_validation_task_count"] >= 1
    assert overview_body["task_summary"]["claim_validation_result_count"] >= 1
    assert (
        overview_body["task_summary"]["claim_validation_results"]["by_status"][
            "needs_more_evidence"
        ]
        >= 1
    )
    assert overview_body["recent_experiment_analyses"]
    assert overview_body["recommended_actions"]
    assert "# Research Progress Overview" in overview_body["markdown_export"]
    assert "## Recent Claim Validation Results" in overview_body["markdown_export"]

    radar = client.get("/research/opportunities/radar?limit=5")
    assert radar.status_code == 200
    radar_body = radar.json()
    assert radar_body["idea_count"] >= 1
    assert radar_body["top_opportunities"]
    assert radar_body["top_opportunities"][0]["idea_id"]
    assert radar_body["top_opportunities"][0]["next_actions"]
    assert radar_body["recommended_sequence"]
    assert "# Research Opportunity Radar" in radar_body["markdown_export"]

    cockpit = client.get("/research/cockpit?idea_limit=20&opportunity_limit=5")
    assert cockpit.status_code == 200
    cockpit_body = cockpit.json()
    assert cockpit_body["project_metrics"]["paper_count"] >= 1
    assert cockpit_body["project_metrics"]["idea_count"] >= 1
    assert cockpit_body["project_metrics"]["claim_validation_result_count"] >= 1
    assert cockpit_body["primary_next_action"]["label"]
    assert cockpit_body["quick_actions"]
    assert cockpit_body["workflow_stages"]
    assert cockpit_body["setup_status"]
    assert cockpit_body["source_summaries"]["quality"]["decision_counts"]
    assert "# Project Cockpit" in cockpit_body["markdown_export"]

    cockpit_markdown = client.get("/research/cockpit/export/markdown")
    assert cockpit_markdown.status_code == 200
    assert "text/markdown" in cockpit_markdown.headers["content-type"]
    assert "# Project Cockpit" in cockpit_markdown.text

    advisor_chat = client.post(
        "/research/advisor/chat",
        json={
            "question": "What should I do next, and which evidence risk matters most?",
            "idea_id": idea_id,
            "paper_ids": [paper_id],
            "include_cockpit": True,
            "include_context": True,
            "context_limit": 5,
            "created_by": "pytest",
        },
    )
    assert advisor_chat.status_code == 200
    advisor_chat_body = advisor_chat.json()
    assert advisor_chat_body["intent"] in {
        "next_actions",
        "risk_review",
        "evidence_review",
        "project_status",
    }
    assert advisor_chat_body["answer"]
    assert advisor_chat_body["recommended_actions"]
    assert advisor_chat_body["tool_suggestions"]
    assert advisor_chat_body["cockpit_phase"]
    assert advisor_chat_body["readiness_level"]
    assert "# Advisor Chat Answer" in advisor_chat_body["answer_markdown"]
    assert (
        advisor_chat_body["cited_evidences"]
        or advisor_chat_body["cited_gaps"]
        or advisor_chat_body["cited_ideas"]
    )

    advisor_chat_tasks = client.post(
        "/research/advisor/chat/tasks",
        json={
            "question": "What should I do next, and which evidence risk matters most?",
            "idea_id": idea_id,
            "paper_ids": [paper_id],
            "include_cockpit": True,
            "include_context": True,
            "context_limit": 5,
            "limit": 5,
            "include_recommendations": True,
            "include_risks": True,
            "created_by": "pytest",
        },
    )
    assert advisor_chat_tasks.status_code == 200
    advisor_chat_task_body = advisor_chat_tasks.json()
    assert advisor_chat_task_body["tasks"]
    assert all(
        task["owner_type"] == "project_advisor_chat" for task in advisor_chat_task_body["tasks"]
    )
    assert all(
        task["due_phase"] == "advisor_chat_follow_up" for task in advisor_chat_task_body["tasks"]
    )

    advisor_chat_task_edges = client.get(
        "/research/graph/edges?edge_type=project_advisor_chat_creates_task"
    )
    assert advisor_chat_task_edges.status_code == 200
    assert advisor_chat_task_edges.json()

    advisor_action_session = client.post(
        "/research/advisor/action-session",
        json={
            "question": "Create an execution session for the highest evidence risk.",
            "idea_id": idea_id,
            "paper_ids": [paper_id],
            "include_cockpit": True,
            "include_context": True,
            "context_limit": 5,
            "limit": 5,
            "include_recommendations": True,
            "include_risks": True,
            "include_tool_suggestions": False,
            "snapshot_title": "Pytest Advisor Action Session",
            "include_snapshot": True,
            "created_by": "pytest",
        },
    )
    assert advisor_action_session.status_code == 200
    advisor_action_body = advisor_action_session.json()
    assert advisor_action_body["chat"]["answer"]
    assert advisor_action_body["tasks"]
    assert advisor_action_body["snapshot"]["id"]
    assert advisor_action_body["snapshot"]["owner_type"] == "project_advisor_chat"
    assert set(task["id"] for task in advisor_action_body["tasks"]).issubset(
        set(advisor_action_body["snapshot"]["task_ids"])
    )
    assert advisor_action_body["progress_summary"]["task_count"] == len(
        advisor_action_body["tasks"]
    )
    assert (
        advisor_action_body["progress_summary"]["snapshot_id"]
        == advisor_action_body["snapshot"]["id"]
    )
    assert "# Advisor Action Session" in advisor_action_body["markdown_export"]

    cockpit_tasks = client.post(
        "/research/cockpit/tasks",
        json={
            "limit": 5,
            "include_primary_action": True,
            "include_next_actions": True,
            "include_risks": True,
            "created_by": "pytest",
        },
    )
    assert cockpit_tasks.status_code == 200
    cockpit_task_body = cockpit_tasks.json()
    assert cockpit_task_body["tasks"]
    assert all(task["owner_type"] == "project_cockpit" for task in cockpit_task_body["tasks"])
    assert all(task["due_phase"] == "cockpit_follow_up" for task in cockpit_task_body["tasks"])

    cockpit_task_edges = client.get("/research/graph/edges?edge_type=project_cockpit_creates_task")
    assert cockpit_task_edges.status_code == 200
    assert cockpit_task_edges.json()

    radar_tasks = client.post(
        "/research/opportunities/radar/tasks",
        json={"limit": 3, "actions_per_opportunity": 1, "created_by": "pytest"},
    )
    assert radar_tasks.status_code == 200
    radar_task_body = radar_tasks.json()
    assert radar_task_body["tasks"]
    assert radar_task_body["tasks"][0]["owner_type"] == "opportunity_radar"
    assert radar_task_body["tasks"][0]["due_phase"] == "opportunity_follow_up"
    radar_task_idea_id = radar_task_body["tasks"][0]["idea_id"]
    radar_task_edges = client.get("/research/graph/edges?edge_type=opportunity_radar_creates_task")
    assert radar_task_edges.status_code == 200
    assert radar_task_edges.json()

    progress_after_radar_tasks = client.get(f"/research/ideas/{radar_task_idea_id}/progress")
    assert progress_after_radar_tasks.status_code == 200
    progress_after_radar_body = progress_after_radar_tasks.json()
    assert progress_after_radar_body["artifact_counts"]["opportunity_follow_up_tasks"] >= 1
    assert progress_after_radar_body["task_summary"]["by_owner_type"]["opportunity_radar"] >= 1

    brief = client.post(
        "/research/briefs",
        json={
            "title": "Pytest Advisor Brief",
            "scope": "idea_set",
            "idea_ids": [idea_id],
            "created_by": "pytest",
        },
    )
    assert brief.status_code == 200
    brief_body = brief.json()
    assert brief_body["idea_ids"] == [idea_id]
    assert brief_body["summary"]["idea_count"] == 1
    assert brief_body["summary"]["evidence_signals"][0]["ledger_id"] == evidence_ledger_body["id"]
    assert brief_body["summary"]["evidence_signals"][0]["claim_count"] >= 1
    assert brief_body["summary"]["claim_validation_queue"]["summary"]["item_count"] >= 1
    assert brief_body["summary"]["claim_validation_results"]["event_count"] >= 1
    assert (
        brief_body["summary"]["claim_validation_results"]["by_status"]["needs_more_evidence"] >= 1
    )
    assert any(
        item["ledger_id"] == evidence_ledger_body["id"] and item["claim_id"] == claim_id
        for item in brief_body["summary"]["claim_validation_queue"]["items"]
    )
    assert brief_body["summary"]["triage_signals"]["comparison_task_count"] >= 1
    assert brief_body["summary"]["triage_signals"]["claim_validation_task_count"] >= 1
    assert (
        brief_body["summary"]["triage_snapshot_comparison"]["candidate_snapshot_id"]
        == triage_snapshot_body["id"]
    )
    assert "# Pytest Advisor Brief" in brief_body["markdown_export"]
    assert "## Evidence Signals" in brief_body["markdown_export"]
    assert "## Claim Validation Queue" in brief_body["markdown_export"]
    assert "## Claim Validation Results" in brief_body["markdown_export"]
    assert "## Triage Signals" in brief_body["markdown_export"]
    assert "Claim Validation Tasks" in brief_body["markdown_export"]
    assert "## Triage Snapshot Changes" in brief_body["markdown_export"]
    assert "## Discussion Prompts" in brief_body["markdown_export"]

    briefs = client.get("/research/briefs")
    assert briefs.status_code == 200
    assert briefs.json()[0]["id"] == brief_body["id"]

    fetched_brief = client.get(f"/research/briefs/{brief_body['id']}")
    assert fetched_brief.status_code == 200
    assert fetched_brief.json()["id"] == brief_body["id"]

    brief_export = client.get(f"/research/briefs/{brief_body['id']}/export/markdown")
    assert brief_export.status_code == 200
    assert "## Highest Priority Open Tasks" in brief_export.text
    assert "## Evidence Signals" in brief_export.text
    assert "## Claim Validation Queue" in brief_export.text
    assert "## Claim Validation Results" in brief_export.text
    assert "Claim Validation Tasks" in brief_export.text
    assert "## Triage Snapshot Changes" in brief_export.text

    baseline_pilot_snapshot = client.post(
        "/research/pilot/report/snapshots",
        json={"title": "Pytest Pilot Report Baseline", "created_by": "pytest"},
    )
    assert baseline_pilot_snapshot.status_code == 200
    baseline_pilot_snapshot_body = baseline_pilot_snapshot.json()

    pilot_snapshot = client.post(
        "/research/pilot/report/snapshots",
        json={"title": "Pytest Pilot Report Candidate", "created_by": "pytest"},
    )
    assert pilot_snapshot.status_code == 200
    pilot_snapshot_body = pilot_snapshot.json()

    readiness_before_plan = client.get("/research/export/project-bundle/readiness")
    assert readiness_before_plan.status_code == 200
    readiness_before_plan_body = readiness_before_plan.json()
    assert readiness_before_plan_body["readiness_level"] == "nearly_ready"
    assert readiness_before_plan_body["readiness_score"] < 1.0
    assert "Research execution plan" in readiness_before_plan_body["missing_required"]
    assert "research_plan" in {
        action["id"] for action in readiness_before_plan_body["quick_actions"]
    }

    research_plan = client.post(
        "/research/plans",
        json={
            "title": "Pytest Research Execution Plan",
            "horizon_days": 14,
            "idea_ids": [idea_id],
            "created_by": "pytest",
        },
    )
    assert research_plan.status_code == 200
    research_plan_body = research_plan.json()
    assert research_plan_body["idea_ids"] == [idea_id]
    assert research_plan_body["plan_items"]

    research_plan_tasks = client.post(
        f"/research/plans/{research_plan_body['id']}/tasks",
        json={"created_by": "pytest"},
    )
    assert research_plan_tasks.status_code == 200
    assert research_plan_tasks.json()["tasks"]

    project_bundle_readiness = client.get("/research/export/project-bundle/readiness")
    assert project_bundle_readiness.status_code == 200
    project_bundle_readiness_body = project_bundle_readiness.json()
    assert project_bundle_readiness_body["readiness_level"] == "delivery_ready"
    assert project_bundle_readiness_body["readiness_score"] == 1.0
    assert project_bundle_readiness_body["missing_required"] == []
    assert "# Project Bundle Readiness" in project_bundle_readiness_body["markdown_export"]
    assert "Saved pilot report history" in project_bundle_readiness_body["markdown_export"]
    assert "export_project_bundle" in {
        action["id"] for action in project_bundle_readiness_body["quick_actions"]
    }
    readiness_manifest = project_bundle_readiness_body["manifest_summary"]
    assert readiness_manifest["triage_snapshot_count"] >= 2
    assert readiness_manifest["triage_snapshot_comparison_available"] is True
    assert readiness_manifest["pilot_report_snapshot_count"] >= 2
    assert readiness_manifest["pilot_report_snapshot_comparison_available"] is True
    assert readiness_manifest["claim_validation_queue_count"] >= 1
    assert readiness_manifest["research_plan_count"] >= 1

    project_bundle_readiness_tasks = client.post(
        "/research/export/project-bundle/readiness/tasks",
        json={"limit": 6, "include_optional": True, "created_by": "pytest"},
    )
    assert project_bundle_readiness_tasks.status_code == 200
    project_bundle_readiness_task_body = project_bundle_readiness_tasks.json()
    assert project_bundle_readiness_task_body["tasks"]
    first_bundle_task = project_bundle_readiness_task_body["tasks"][0]
    assert first_bundle_task["owner_type"] == "project_bundle_readiness"
    assert first_bundle_task["due_phase"] == "bundle_handoff_follow_up"
    assert first_bundle_task["metadata"]["readiness_level"] == "delivery_ready"
    assert first_bundle_task["metadata"]["action_path"]
    project_bundle_readiness_task_edges = client.get(
        "/research/graph/edges?edge_type=project_bundle_readiness_creates_task"
    )
    assert project_bundle_readiness_task_edges.status_code == 200
    assert project_bundle_readiness_task_edges.json()

    baseline_bundle_readiness_snapshot = client.post(
        "/research/export/project-bundle/readiness/snapshots",
        json={"title": "Pytest Bundle Readiness Baseline", "created_by": "pytest"},
    )
    assert baseline_bundle_readiness_snapshot.status_code == 200
    baseline_bundle_readiness_snapshot_body = baseline_bundle_readiness_snapshot.json()

    project_bundle_readiness_snapshot = client.post(
        "/research/export/project-bundle/readiness/snapshots",
        json={"title": "Pytest Bundle Readiness Candidate", "created_by": "pytest"},
    )
    assert project_bundle_readiness_snapshot.status_code == 200
    project_bundle_readiness_snapshot_body = project_bundle_readiness_snapshot.json()
    assert project_bundle_readiness_snapshot_body["scope"] == "bundle_readiness"
    assert project_bundle_readiness_snapshot_body["summary"]["readiness_level"] == "delivery_ready"
    assert project_bundle_readiness_snapshot_body["summary"]["readiness_score"] == 1.0
    assert "# Project Bundle Readiness" in project_bundle_readiness_snapshot_body["markdown_export"]

    listed_bundle_readiness_snapshots = client.get(
        "/research/export/project-bundle/readiness/snapshots"
    )
    assert listed_bundle_readiness_snapshots.status_code == 200
    assert (
        listed_bundle_readiness_snapshots.json()[0]["id"]
        == (project_bundle_readiness_snapshot_body["id"])
    )

    fetched_bundle_readiness_snapshot = client.get(
        "/research/export/project-bundle/readiness/snapshots/"
        f"{project_bundle_readiness_snapshot_body['id']}"
    )
    assert fetched_bundle_readiness_snapshot.status_code == 200
    assert (
        fetched_bundle_readiness_snapshot.json()["id"]
        == (project_bundle_readiness_snapshot_body["id"])
    )

    exported_bundle_readiness_snapshot = client.get(
        "/research/export/project-bundle/readiness/snapshots/"
        f"{project_bundle_readiness_snapshot_body['id']}/export/markdown"
    )
    assert exported_bundle_readiness_snapshot.status_code == 200
    assert "# Project Bundle Readiness" in exported_bundle_readiness_snapshot.text

    bundle_readiness_snapshot_comparison = client.post(
        "/research/export/project-bundle/readiness/snapshots/compare",
        json={
            "baseline_snapshot_id": baseline_bundle_readiness_snapshot_body["id"],
            "candidate_snapshot_id": project_bundle_readiness_snapshot_body["id"],
        },
    )
    assert bundle_readiness_snapshot_comparison.status_code == 200
    bundle_readiness_snapshot_comparison_body = bundle_readiness_snapshot_comparison.json()
    assert (
        bundle_readiness_snapshot_comparison_body["baseline_snapshot_id"]
        == baseline_bundle_readiness_snapshot_body["id"]
    )
    assert (
        bundle_readiness_snapshot_comparison_body["candidate_snapshot_id"]
        == project_bundle_readiness_snapshot_body["id"]
    )
    assert "readiness_score" in bundle_readiness_snapshot_comparison_body["readiness_delta"]
    assert (
        "# Project Bundle Readiness Snapshot Comparison"
        in bundle_readiness_snapshot_comparison_body["markdown_export"]
    )

    exported_bundle_readiness_snapshot_comparison = client.post(
        "/research/export/project-bundle/readiness/snapshots/compare/export/markdown",
        json={
            "baseline_snapshot_id": baseline_bundle_readiness_snapshot_body["id"],
            "candidate_snapshot_id": project_bundle_readiness_snapshot_body["id"],
        },
    )
    assert exported_bundle_readiness_snapshot_comparison.status_code == 200
    assert (
        "# Project Bundle Readiness Snapshot Comparison"
        in exported_bundle_readiness_snapshot_comparison.text
    )

    bundle_readiness_comparison_tasks = client.post(
        "/research/export/project-bundle/readiness/snapshots/compare/tasks",
        json={
            "baseline_snapshot_id": baseline_bundle_readiness_snapshot_body["id"],
            "candidate_snapshot_id": project_bundle_readiness_snapshot_body["id"],
            "limit": 6,
            "include_missing_required": True,
            "include_recommended_actions": True,
            "include_quick_actions": True,
            "created_by": "pytest",
        },
    )
    assert bundle_readiness_comparison_tasks.status_code == 200
    bundle_readiness_comparison_task_body = bundle_readiness_comparison_tasks.json()
    assert bundle_readiness_comparison_task_body["tasks"]
    first_bundle_comparison_task = bundle_readiness_comparison_task_body["tasks"][0]
    assert (
        first_bundle_comparison_task["owner_type"] == "project_bundle_readiness_snapshot_comparison"
    )
    assert first_bundle_comparison_task["due_phase"] == "bundle_readiness_change_follow_up"
    assert (
        first_bundle_comparison_task["metadata"]["baseline_snapshot_id"]
        == baseline_bundle_readiness_snapshot_body["id"]
    )
    assert (
        first_bundle_comparison_task["metadata"]["candidate_snapshot_id"]
        == project_bundle_readiness_snapshot_body["id"]
    )
    bundle_readiness_comparison_task_edges = client.get(
        "/research/graph/edges?edge_type=project_bundle_readiness_comparison_creates_task"
    )
    assert bundle_readiness_comparison_task_edges.status_code == 200
    assert bundle_readiness_comparison_task_edges.json()

    project_bundle_release = client.post(
        "/research/export/project-bundle/releases",
        json={
            "title": "Pytest Project Bundle Release",
            "recipient": "pytest advisor",
            "release_notes": "Release note for pytest handoff bundle.",
            "created_by": "pytest",
        },
    )
    assert project_bundle_release.status_code == 200
    project_bundle_release_body = project_bundle_release.json()
    assert project_bundle_release_body["scope"] == "project_bundle_release"
    assert project_bundle_release_body["summary"]["recipient"] == "pytest advisor"
    assert project_bundle_release_body["summary"]["readiness_level"] == "delivery_ready"
    assert "# Project Bundle Release Note" in project_bundle_release_body["markdown_export"]

    listed_project_bundle_releases = client.get("/research/export/project-bundle/releases")
    assert listed_project_bundle_releases.status_code == 200
    assert listed_project_bundle_releases.json()[0]["id"] == project_bundle_release_body["id"]

    fetched_project_bundle_release = client.get(
        f"/research/export/project-bundle/releases/{project_bundle_release_body['id']}"
    )
    assert fetched_project_bundle_release.status_code == 200
    assert fetched_project_bundle_release.json()["id"] == project_bundle_release_body["id"]

    exported_project_bundle_release = client.get(
        "/research/export/project-bundle/releases/"
        f"{project_bundle_release_body['id']}/export/markdown"
    )
    assert exported_project_bundle_release.status_code == 200
    assert "# Project Bundle Release Note" in exported_project_bundle_release.text

    project_bundle_release_tasks = client.post(
        f"/research/export/project-bundle/releases/{project_bundle_release_body['id']}/tasks",
        json={
            "limit": 6,
            "include_missing_required": True,
            "include_handoff_checks": True,
            "created_by": "pytest",
        },
    )
    assert project_bundle_release_tasks.status_code == 200
    project_bundle_release_task_body = project_bundle_release_tasks.json()
    assert project_bundle_release_task_body["tasks"]
    first_release_task = project_bundle_release_task_body["tasks"][0]
    assert first_release_task["owner_type"] == "project_bundle_release"
    assert first_release_task["owner_id"] == project_bundle_release_body["id"]
    assert first_release_task["due_phase"] == "project_bundle_release_follow_up"
    assert first_release_task["metadata"]["release_id"] == project_bundle_release_body["id"]
    assert first_release_task["metadata"]["recipient"] == "pytest advisor"
    project_bundle_release_task_edges = client.get(
        "/research/graph/edges?edge_type=project_bundle_release_creates_task"
    )
    assert project_bundle_release_task_edges.status_code == 200
    assert project_bundle_release_task_edges.json()

    project_bundle_release_progress = client.get(
        f"/research/export/project-bundle/releases/{project_bundle_release_body['id']}/progress"
    )
    assert project_bundle_release_progress.status_code == 200
    project_bundle_release_progress_body = project_bundle_release_progress.json()
    assert project_bundle_release_progress_body["release_id"] == project_bundle_release_body["id"]
    assert project_bundle_release_progress_body["recipient"] == "pytest advisor"
    assert project_bundle_release_progress_body["task_summary"]["task_count"] >= len(
        project_bundle_release_task_body["tasks"]
    )
    assert project_bundle_release_progress_body["task_summary"]["open_task_count"] >= 1
    assert project_bundle_release_progress_body["completion_ratio"] == 0.0
    assert (
        "# Project Bundle Release Progress"
        in project_bundle_release_progress_body["markdown_export"]
    )

    project_bundle_release_feedback = client.post(
        f"/research/export/project-bundle/releases/{project_bundle_release_body['id']}/feedback",
        json={
            "title": "Pytest Project Bundle Feedback",
            "recipient": "pytest advisor",
            "feedback_status": "changes_requested",
            "signoff_confirmed": False,
            "feedback_notes": "Feedback after pytest handoff.",
            "requested_changes": [
                "Clarify owner for release closeout.",
                "Summarize unresolved claim risks.",
            ],
            "blockers": ["Advisor signoff is pending until changes are addressed."],
            "accepted_artifacts": ["README.md", "metadata/manifest.json"],
            "created_by": "pytest",
        },
    )
    assert project_bundle_release_feedback.status_code == 200
    project_bundle_release_feedback_body = project_bundle_release_feedback.json()
    assert project_bundle_release_feedback_body["scope"] == "project_bundle_release_feedback"
    assert (
        project_bundle_release_feedback_body["summary"]["release_id"]
        == project_bundle_release_body["id"]
    )
    assert project_bundle_release_feedback_body["summary"]["feedback_status"] == (
        "changes_requested"
    )
    assert project_bundle_release_feedback_body["summary"]["requested_changes"]
    assert (
        "# Project Bundle Release Feedback"
        in project_bundle_release_feedback_body["markdown_export"]
    )

    listed_project_bundle_release_feedback = client.get(
        f"/research/export/project-bundle/releases/{project_bundle_release_body['id']}/feedback"
    )
    assert listed_project_bundle_release_feedback.status_code == 200
    assert (
        listed_project_bundle_release_feedback.json()[0]["id"]
        == project_bundle_release_feedback_body["id"]
    )

    fetched_project_bundle_release_feedback = client.get(
        "/research/export/project-bundle/releases/"
        f"{project_bundle_release_body['id']}/feedback/{project_bundle_release_feedback_body['id']}"
    )
    assert fetched_project_bundle_release_feedback.status_code == 200
    assert (
        fetched_project_bundle_release_feedback.json()["id"]
        == (project_bundle_release_feedback_body["id"])
    )

    exported_project_bundle_release_feedback = client.get(
        "/research/export/project-bundle/releases/"
        f"{project_bundle_release_body['id']}/feedback/"
        f"{project_bundle_release_feedback_body['id']}/export/markdown"
    )
    assert exported_project_bundle_release_feedback.status_code == 200
    assert "# Project Bundle Release Feedback" in exported_project_bundle_release_feedback.text

    project_bundle_release_feedback_tasks = client.post(
        "/research/export/project-bundle/releases/"
        f"{project_bundle_release_body['id']}/feedback/"
        f"{project_bundle_release_feedback_body['id']}/tasks",
        json={
            "limit": 6,
            "include_requested_changes": True,
            "include_blockers": True,
            "include_signoff_check": True,
            "created_by": "pytest",
        },
    )
    assert project_bundle_release_feedback_tasks.status_code == 200
    project_bundle_release_feedback_task_body = project_bundle_release_feedback_tasks.json()
    assert project_bundle_release_feedback_task_body["tasks"]
    first_feedback_task = project_bundle_release_feedback_task_body["tasks"][0]
    assert first_feedback_task["owner_type"] == "project_bundle_release_feedback"
    assert first_feedback_task["owner_id"] == project_bundle_release_feedback_body["id"]
    assert first_feedback_task["due_phase"] == "project_bundle_release_feedback_follow_up"
    assert first_feedback_task["metadata"]["release_id"] == project_bundle_release_body["id"]
    assert (
        first_feedback_task["metadata"]["feedback_id"]
        == (project_bundle_release_feedback_body["id"])
    )

    project_bundle_release_feedback_edges = client.get(
        "/research/graph/edges?edge_type=project_bundle_release_has_feedback"
    )
    assert project_bundle_release_feedback_edges.status_code == 200
    assert project_bundle_release_feedback_edges.json()
    project_bundle_release_feedback_task_edges = client.get(
        "/research/graph/edges?edge_type=project_bundle_release_feedback_creates_task"
    )
    assert project_bundle_release_feedback_task_edges.status_code == 200
    assert project_bundle_release_feedback_task_edges.json()

    project_bundle_release_closeout = client.get(
        f"/research/export/project-bundle/releases/{project_bundle_release_body['id']}/closeout"
    )
    assert project_bundle_release_closeout.status_code == 200
    project_bundle_release_closeout_body = project_bundle_release_closeout.json()
    assert project_bundle_release_closeout_body["release_id"] == project_bundle_release_body["id"]
    assert project_bundle_release_closeout_body["closeout_status"] == "blocked"
    assert project_bundle_release_closeout_body["ready_to_close"] is False
    assert project_bundle_release_closeout_body["signoff_confirmed"] is False
    assert (
        project_bundle_release_closeout_body["latest_feedback"]["id"]
        == project_bundle_release_feedback_body["id"]
    )
    assert project_bundle_release_closeout_body["feedback_task_summary"]["task_count"] >= len(
        project_bundle_release_feedback_task_body["tasks"]
    )
    assert project_bundle_release_closeout_body["blocking_reasons"]
    assert project_bundle_release_closeout_body["next_actions"]
    assert (
        "# Project Bundle Release Closeout"
        in project_bundle_release_closeout_body["markdown_export"]
    )

    project_bundle_release_closeout_tasks = client.post(
        "/research/export/project-bundle/releases/"
        f"{project_bundle_release_body['id']}/closeout/tasks",
        json={
            "limit": 6,
            "include_blockers": True,
            "include_next_actions": True,
            "include_signoff_check": True,
            "created_by": "pytest",
        },
    )
    assert project_bundle_release_closeout_tasks.status_code == 200
    project_bundle_release_closeout_task_body = project_bundle_release_closeout_tasks.json()
    assert project_bundle_release_closeout_task_body["tasks"]
    first_closeout_task = project_bundle_release_closeout_task_body["tasks"][0]
    assert first_closeout_task["owner_type"] == "project_bundle_release_closeout"
    assert first_closeout_task["owner_id"] == project_bundle_release_body["id"]
    assert first_closeout_task["due_phase"] == "project_bundle_release_closeout_follow_up"
    assert first_closeout_task["metadata"]["release_id"] == project_bundle_release_body["id"]
    assert first_closeout_task["metadata"]["closeout_status"] == "blocked"
    assert first_closeout_task["metadata"]["signoff_confirmed"] is False
    project_bundle_release_closeout_edges = client.get(
        "/research/graph/edges?edge_type=project_bundle_release_has_closeout"
    )
    assert project_bundle_release_closeout_edges.status_code == 200
    assert project_bundle_release_closeout_edges.json()
    project_bundle_release_closeout_task_edges = client.get(
        "/research/graph/edges?edge_type=project_bundle_release_closeout_creates_task"
    )
    assert project_bundle_release_closeout_task_edges.status_code == 200
    assert project_bundle_release_closeout_task_edges.json()

    project_bundle_release_acceptance_packet = client.get(
        "/research/export/project-bundle/releases/"
        f"{project_bundle_release_body['id']}/acceptance-packet"
    )
    assert project_bundle_release_acceptance_packet.status_code == 200
    project_bundle_release_acceptance_packet_body = project_bundle_release_acceptance_packet.json()
    assert (
        project_bundle_release_acceptance_packet_body["release_id"]
        == project_bundle_release_body["id"]
    )
    assert project_bundle_release_acceptance_packet_body["acceptance_status"] == "blocked"
    assert project_bundle_release_acceptance_packet_body["ready_for_signoff"] is False
    assert project_bundle_release_acceptance_packet_body["closeout"]["closeout_status"] == "blocked"
    assert project_bundle_release_acceptance_packet_body["closeout_task_summary"][
        "task_count"
    ] >= len(project_bundle_release_closeout_task_body["tasks"])
    assert project_bundle_release_acceptance_packet_body["open_closeout_tasks"]
    assert project_bundle_release_acceptance_packet_body["checklist"]
    assert project_bundle_release_acceptance_packet_body["remaining_actions"]
    assert (
        "# Project Bundle Release Acceptance Packet"
        in project_bundle_release_acceptance_packet_body["markdown_export"]
    )

    baseline_project_bundle_release_acceptance_snapshot = client.post(
        "/research/export/project-bundle/releases/"
        f"{project_bundle_release_body['id']}/acceptance-packet/snapshots",
        json={
            "title": "Pytest Baseline Project Bundle Release Acceptance Snapshot",
            "created_by": "pytest",
        },
    )
    assert baseline_project_bundle_release_acceptance_snapshot.status_code == 200
    baseline_project_bundle_release_acceptance_snapshot_body = (
        baseline_project_bundle_release_acceptance_snapshot.json()
    )

    project_bundle_release_acceptance_snapshot = client.post(
        "/research/export/project-bundle/releases/"
        f"{project_bundle_release_body['id']}/acceptance-packet/snapshots",
        json={
            "title": "Pytest Project Bundle Release Acceptance Snapshot",
            "created_by": "pytest",
        },
    )
    assert project_bundle_release_acceptance_snapshot.status_code == 200
    project_bundle_release_acceptance_snapshot_body = (
        project_bundle_release_acceptance_snapshot.json()
    )
    assert (
        project_bundle_release_acceptance_snapshot_body["scope"]
        == "project_bundle_release_acceptance_packet"
    )
    assert (
        project_bundle_release_acceptance_snapshot_body["summary"]["release_id"]
        == project_bundle_release_body["id"]
    )
    assert (
        project_bundle_release_acceptance_snapshot_body["summary"]["acceptance_status"] == "blocked"
    )
    assert project_bundle_release_acceptance_snapshot_body["summary"]["ready_for_signoff"] is False
    assert (
        "# Project Bundle Release Acceptance Packet"
        in project_bundle_release_acceptance_snapshot_body["markdown_export"]
    )

    project_bundle_release_acceptance_snapshots = client.get(
        "/research/export/project-bundle/releases/"
        f"{project_bundle_release_body['id']}/acceptance-packet/snapshots?limit=5"
    )
    assert project_bundle_release_acceptance_snapshots.status_code == 200
    assert (
        project_bundle_release_acceptance_snapshots.json()[0]["id"]
        == project_bundle_release_acceptance_snapshot_body["id"]
    )

    project_bundle_release_acceptance_snapshot_detail = client.get(
        "/research/export/project-bundle/releases/"
        f"{project_bundle_release_body['id']}/acceptance-packet/snapshots/"
        f"{project_bundle_release_acceptance_snapshot_body['id']}"
    )
    assert project_bundle_release_acceptance_snapshot_detail.status_code == 200
    assert (
        project_bundle_release_acceptance_snapshot_detail.json()["id"]
        == project_bundle_release_acceptance_snapshot_body["id"]
    )

    project_bundle_release_acceptance_snapshot_markdown = client.get(
        "/research/export/project-bundle/releases/"
        f"{project_bundle_release_body['id']}/acceptance-packet/snapshots/"
        f"{project_bundle_release_acceptance_snapshot_body['id']}/export/markdown"
    )
    assert project_bundle_release_acceptance_snapshot_markdown.status_code == 200
    assert (
        "# Project Bundle Release Acceptance Packet"
        in project_bundle_release_acceptance_snapshot_markdown.text
    )

    project_bundle_release_acceptance_snapshot_edges = client.get(
        "/research/graph/edges?edge_type=project_bundle_release_has_acceptance_packet"
    )
    assert project_bundle_release_acceptance_snapshot_edges.status_code == 200
    assert project_bundle_release_acceptance_snapshot_edges.json()

    project_bundle_release_acceptance_snapshot_comparison = client.post(
        "/research/export/project-bundle/releases/"
        f"{project_bundle_release_body['id']}/acceptance-packet/snapshots/compare",
        json={
            "baseline_snapshot_id": baseline_project_bundle_release_acceptance_snapshot_body["id"],
            "candidate_snapshot_id": project_bundle_release_acceptance_snapshot_body["id"],
        },
    )
    assert project_bundle_release_acceptance_snapshot_comparison.status_code == 200
    project_bundle_release_acceptance_snapshot_comparison_body = (
        project_bundle_release_acceptance_snapshot_comparison.json()
    )
    assert (
        project_bundle_release_acceptance_snapshot_comparison_body["baseline_snapshot_id"]
        == baseline_project_bundle_release_acceptance_snapshot_body["id"]
    )
    assert (
        project_bundle_release_acceptance_snapshot_comparison_body["candidate_snapshot_id"]
        == project_bundle_release_acceptance_snapshot_body["id"]
    )
    assert (
        project_bundle_release_acceptance_snapshot_comparison_body["release_id"]
        == project_bundle_release_body["id"]
    )
    assert (
        project_bundle_release_acceptance_snapshot_comparison_body["status_delta"]["candidate"]
        == "blocked"
    )
    assert (
        "# Project Bundle Release Acceptance Snapshot Comparison"
        in project_bundle_release_acceptance_snapshot_comparison_body["markdown_export"]
    )

    project_bundle_release_acceptance_snapshot_comparison_markdown = client.post(
        "/research/export/project-bundle/releases/"
        f"{project_bundle_release_body['id']}/acceptance-packet/snapshots/compare/export/markdown",
        json={
            "baseline_snapshot_id": baseline_project_bundle_release_acceptance_snapshot_body["id"],
            "candidate_snapshot_id": project_bundle_release_acceptance_snapshot_body["id"],
        },
    )
    assert project_bundle_release_acceptance_snapshot_comparison_markdown.status_code == 200
    assert (
        "# Project Bundle Release Acceptance Snapshot Comparison"
        in project_bundle_release_acceptance_snapshot_comparison_markdown.text
    )

    project_bundle_release_acceptance_snapshot_comparison_tasks = client.post(
        "/research/export/project-bundle/releases/"
        f"{project_bundle_release_body['id']}/acceptance-packet/snapshots/compare/tasks",
        json={
            "baseline_snapshot_id": baseline_project_bundle_release_acceptance_snapshot_body["id"],
            "candidate_snapshot_id": project_bundle_release_acceptance_snapshot_body["id"],
            "limit": 6,
            "include_remaining_actions": True,
            "include_checklist_regressions": True,
            "include_status_regression": True,
            "created_by": "pytest",
        },
    )
    assert project_bundle_release_acceptance_snapshot_comparison_tasks.status_code == 200
    project_bundle_release_acceptance_snapshot_comparison_task_body = (
        project_bundle_release_acceptance_snapshot_comparison_tasks.json()
    )
    assert project_bundle_release_acceptance_snapshot_comparison_task_body["tasks"]
    first_acceptance_comparison_task = (
        project_bundle_release_acceptance_snapshot_comparison_task_body["tasks"][0]
    )
    assert (
        first_acceptance_comparison_task["owner_type"]
        == "project_bundle_release_acceptance_packet_snapshot_comparison"
    )
    assert (
        first_acceptance_comparison_task["owner_id"]
        == project_bundle_release_acceptance_snapshot_body["id"]
    )
    assert (
        first_acceptance_comparison_task["due_phase"]
        == "project_bundle_release_acceptance_change_follow_up"
    )
    assert (
        first_acceptance_comparison_task["metadata"]["release_id"]
        == project_bundle_release_body["id"]
    )
    assert (
        first_acceptance_comparison_task["metadata"]["baseline_snapshot_id"]
        == baseline_project_bundle_release_acceptance_snapshot_body["id"]
    )
    assert (
        first_acceptance_comparison_task["metadata"]["candidate_snapshot_id"]
        == project_bundle_release_acceptance_snapshot_body["id"]
    )

    project_bundle_release_acceptance_snapshot_comparison_edges = client.get(
        "/research/graph/edges?edge_type=project_bundle_release_acceptance_comparison_creates_task"
    )
    assert project_bundle_release_acceptance_snapshot_comparison_edges.status_code == 200
    assert project_bundle_release_acceptance_snapshot_comparison_edges.json()

    project_bundle_release_review_session = client.get(
        "/research/export/project-bundle/releases/"
        f"{project_bundle_release_body['id']}/review-session"
    )
    assert project_bundle_release_review_session.status_code == 200
    project_bundle_release_review_session_body = project_bundle_release_review_session.json()
    assert (
        project_bundle_release_review_session_body["release_id"]
        == project_bundle_release_body["id"]
    )
    assert project_bundle_release_review_session_body["recipient"] == "pytest advisor"
    assert project_bundle_release_review_session_body["acceptance_status"] == "blocked"
    assert project_bundle_release_review_session_body["review_status"] == "blocked_review"
    assert project_bundle_release_review_session_body["ready_for_review"] is True
    assert project_bundle_release_review_session_body["agenda"]
    assert project_bundle_release_review_session_body["decisions_needed"]
    assert project_bundle_release_review_session_body["risk_items"]
    assert project_bundle_release_review_session_body["follow_up_actions"]
    assert project_bundle_release_review_session_body["artifact_links"]
    assert (
        project_bundle_release_review_session_body["latest_acceptance_snapshot"]["id"]
        == project_bundle_release_acceptance_snapshot_body["id"]
    )
    assert (
        project_bundle_release_review_session_body["acceptance_snapshot_comparison"][
            "candidate_snapshot_id"
        ]
        == project_bundle_release_acceptance_snapshot_body["id"]
    )
    assert (
        "# Project Bundle Release Review Session"
        in project_bundle_release_review_session_body["markdown_export"]
    )

    project_bundle_release_review_session_tasks = client.post(
        "/research/export/project-bundle/releases/"
        f"{project_bundle_release_body['id']}/review-session/tasks",
        json={
            "limit": 8,
            "include_decisions": True,
            "include_risks": True,
            "include_follow_up_actions": True,
            "created_by": "pytest",
        },
    )
    assert project_bundle_release_review_session_tasks.status_code == 200
    project_bundle_release_review_session_task_body = (
        project_bundle_release_review_session_tasks.json()
    )
    assert project_bundle_release_review_session_task_body["tasks"]
    first_release_review_task = project_bundle_release_review_session_task_body["tasks"][0]
    assert first_release_review_task["owner_type"] == "project_bundle_release_review_session"
    assert first_release_review_task["owner_id"] == project_bundle_release_body["id"]
    assert first_release_review_task["due_phase"] == "project_bundle_release_review_follow_up"
    assert first_release_review_task["metadata"]["release_id"] == project_bundle_release_body["id"]
    assert first_release_review_task["metadata"]["review_status"] == "blocked_review"
    assert first_release_review_task["metadata"]["acceptance_status"] == "blocked"

    project_bundle_release_review_edges = client.get(
        "/research/graph/edges?edge_type=project_bundle_release_review_creates_task"
    )
    assert project_bundle_release_review_edges.status_code == 200
    assert project_bundle_release_review_edges.json()

    project_bundle_release_review_outcome = client.post(
        "/research/export/project-bundle/releases/"
        f"{project_bundle_release_body['id']}/review-session/outcomes",
        json={
            "title": "Pytest Project Bundle Release Review Outcome",
            "review_decision": "follow_up_needed",
            "participants": ["pytest researcher", "pytest advisor"],
            "outcome_notes": "Pytest review outcome captured after the release session.",
            "decisions": ["Assign an owner for unresolved acceptance follow-up."],
            "accepted_artifacts": ["Project bundle", "Release review session"],
            "follow_up_actions": ["Work remaining release review follow-up tasks."],
            "risks": ["Acceptance remains blocked until follow-up work is complete."],
            "signoff_confirmed": False,
            "created_by": "pytest",
        },
    )
    assert project_bundle_release_review_outcome.status_code == 200
    project_bundle_release_review_outcome_body = project_bundle_release_review_outcome.json()
    assert (
        project_bundle_release_review_outcome_body["scope"]
        == "project_bundle_release_review_outcome"
    )
    assert (
        project_bundle_release_review_outcome_body["summary"]["release_id"]
        == project_bundle_release_body["id"]
    )
    assert (
        project_bundle_release_review_outcome_body["summary"]["review_decision"]
        == "follow_up_needed"
    )
    assert project_bundle_release_review_outcome_body["summary"]["signoff_confirmed"] is False
    assert (
        "# Project Bundle Release Review Outcome"
        in project_bundle_release_review_outcome_body["markdown_export"]
    )

    listed_project_bundle_release_review_outcomes = client.get(
        "/research/export/project-bundle/releases/"
        f"{project_bundle_release_body['id']}/review-session/outcomes?limit=5"
    )
    assert listed_project_bundle_release_review_outcomes.status_code == 200
    assert (
        listed_project_bundle_release_review_outcomes.json()[0]["id"]
        == project_bundle_release_review_outcome_body["id"]
    )

    fetched_project_bundle_release_review_outcome = client.get(
        "/research/export/project-bundle/releases/"
        f"{project_bundle_release_body['id']}/review-session/outcomes/"
        f"{project_bundle_release_review_outcome_body['id']}"
    )
    assert fetched_project_bundle_release_review_outcome.status_code == 200
    assert (
        fetched_project_bundle_release_review_outcome.json()["id"]
        == project_bundle_release_review_outcome_body["id"]
    )

    exported_project_bundle_release_review_outcome = client.get(
        "/research/export/project-bundle/releases/"
        f"{project_bundle_release_body['id']}/review-session/outcomes/"
        f"{project_bundle_release_review_outcome_body['id']}/export/markdown"
    )
    assert exported_project_bundle_release_review_outcome.status_code == 200
    assert (
        "# Project Bundle Release Review Outcome"
        in exported_project_bundle_release_review_outcome.text
    )

    project_bundle_release_review_outcome_edges = client.get(
        "/research/graph/edges?edge_type=project_bundle_release_has_review_outcome"
    )
    assert project_bundle_release_review_outcome_edges.status_code == 200
    assert project_bundle_release_review_outcome_edges.json()

    project_bundle_release_review_outcome_tasks = client.post(
        "/research/export/project-bundle/releases/"
        f"{project_bundle_release_body['id']}/review-session/outcomes/"
        f"{project_bundle_release_review_outcome_body['id']}/tasks",
        json={
            "limit": 8,
            "include_decisions": True,
            "include_risks": True,
            "include_follow_up_actions": True,
            "include_signoff_check": True,
            "created_by": "pytest",
        },
    )
    assert project_bundle_release_review_outcome_tasks.status_code == 200
    project_bundle_release_review_outcome_task_body = (
        project_bundle_release_review_outcome_tasks.json()
    )
    assert project_bundle_release_review_outcome_task_body["tasks"]
    first_release_review_outcome_task = project_bundle_release_review_outcome_task_body["tasks"][0]
    assert (
        first_release_review_outcome_task["owner_type"] == "project_bundle_release_review_outcome"
    )
    assert (
        first_release_review_outcome_task["owner_id"]
        == project_bundle_release_review_outcome_body["id"]
    )
    assert (
        first_release_review_outcome_task["due_phase"]
        == "project_bundle_release_review_outcome_follow_up"
    )
    assert (
        first_release_review_outcome_task["metadata"]["release_id"]
        == project_bundle_release_body["id"]
    )
    assert first_release_review_outcome_task["metadata"]["review_decision"] == "follow_up_needed"
    assert first_release_review_outcome_task["metadata"]["signoff_confirmed"] is False

    project_bundle_release_review_outcome_task_edges = client.get(
        "/research/graph/edges?edge_type=project_bundle_release_review_outcome_creates_task"
    )
    assert project_bundle_release_review_outcome_task_edges.status_code == 200
    assert project_bundle_release_review_outcome_task_edges.json()

    project_bundle_release_review_outcome_progress = client.get(
        "/research/export/project-bundle/releases/"
        f"{project_bundle_release_body['id']}/review-session/outcomes/"
        f"{project_bundle_release_review_outcome_body['id']}/progress"
    )
    assert project_bundle_release_review_outcome_progress.status_code == 200
    project_bundle_release_review_outcome_progress_body = (
        project_bundle_release_review_outcome_progress.json()
    )
    assert (
        project_bundle_release_review_outcome_progress_body["release_id"]
        == project_bundle_release_body["id"]
    )
    assert (
        project_bundle_release_review_outcome_progress_body["outcome_id"]
        == project_bundle_release_review_outcome_body["id"]
    )
    assert project_bundle_release_review_outcome_progress_body["task_summary"]["task_count"] >= len(
        project_bundle_release_review_outcome_task_body["tasks"]
    )
    assert project_bundle_release_review_outcome_progress_body["completion_ratio"] == 0.0
    assert (
        project_bundle_release_review_outcome_progress_body["task_summary"]["open_task_count"] >= 1
    )
    assert (
        "# Project Bundle Release Review Outcome Progress"
        in project_bundle_release_review_outcome_progress_body["markdown_export"]
    )

    project_bundle_release_review_outcome_signoff = client.post(
        "/research/export/project-bundle/releases/"
        f"{project_bundle_release_body['id']}/review-session/outcomes/"
        f"{project_bundle_release_review_outcome_body['id']}/signoffs",
        json={
            "title": "Pytest Project Bundle Release Review Outcome Signoff",
            "signoff_decision": "deferred",
            "approver": "pytest advisor",
            "signoff_notes": "Pytest signoff evidence captured before final approval.",
            "accepted_artifacts": [
                "Project bundle",
                "Release review outcome",
                "Outcome progress report",
            ],
            "conditions": ["Complete remaining release review outcome tasks."],
            "evidence_links": [
                "artifacts/releases/latest-project-bundle-release-review-outcome-progress.md"
            ],
            "created_by": "pytest",
        },
    )
    assert project_bundle_release_review_outcome_signoff.status_code == 200
    project_bundle_release_review_outcome_signoff_body = (
        project_bundle_release_review_outcome_signoff.json()
    )
    assert (
        project_bundle_release_review_outcome_signoff_body["scope"]
        == "project_bundle_release_review_outcome_signoff"
    )
    assert (
        project_bundle_release_review_outcome_signoff_body["summary"]["release_id"]
        == project_bundle_release_body["id"]
    )
    assert (
        project_bundle_release_review_outcome_signoff_body["summary"]["outcome_id"]
        == project_bundle_release_review_outcome_body["id"]
    )
    assert (
        project_bundle_release_review_outcome_signoff_body["summary"]["signoff_decision"]
        == "deferred"
    )
    assert (
        project_bundle_release_review_outcome_signoff_body["summary"]["signoff_confirmed"] is False
    )
    assert (
        project_bundle_release_review_outcome_signoff_body["summary"]["progress_open_task_count"]
        >= 1
    )
    assert (
        "# Project Bundle Release Review Outcome Signoff"
        in project_bundle_release_review_outcome_signoff_body["markdown_export"]
    )

    listed_project_bundle_release_review_outcome_signoffs = client.get(
        "/research/export/project-bundle/releases/"
        f"{project_bundle_release_body['id']}/review-session/outcomes/"
        f"{project_bundle_release_review_outcome_body['id']}/signoffs?limit=5"
    )
    assert listed_project_bundle_release_review_outcome_signoffs.status_code == 200
    assert (
        listed_project_bundle_release_review_outcome_signoffs.json()[0]["id"]
        == project_bundle_release_review_outcome_signoff_body["id"]
    )

    fetched_project_bundle_release_review_outcome_signoff = client.get(
        "/research/export/project-bundle/releases/"
        f"{project_bundle_release_body['id']}/review-session/outcomes/"
        f"{project_bundle_release_review_outcome_body['id']}/signoffs/"
        f"{project_bundle_release_review_outcome_signoff_body['id']}"
    )
    assert fetched_project_bundle_release_review_outcome_signoff.status_code == 200
    assert (
        fetched_project_bundle_release_review_outcome_signoff.json()["id"]
        == project_bundle_release_review_outcome_signoff_body["id"]
    )

    exported_project_bundle_release_review_outcome_signoff = client.get(
        "/research/export/project-bundle/releases/"
        f"{project_bundle_release_body['id']}/review-session/outcomes/"
        f"{project_bundle_release_review_outcome_body['id']}/signoffs/"
        f"{project_bundle_release_review_outcome_signoff_body['id']}/export/markdown"
    )
    assert exported_project_bundle_release_review_outcome_signoff.status_code == 200
    assert (
        "# Project Bundle Release Review Outcome Signoff"
        in exported_project_bundle_release_review_outcome_signoff.text
    )

    project_bundle_release_review_outcome_signoff_edges = client.get(
        "/research/graph/edges?edge_type=project_bundle_release_review_outcome_has_signoff"
    )
    assert project_bundle_release_review_outcome_signoff_edges.status_code == 200
    assert project_bundle_release_review_outcome_signoff_edges.json()

    project_bundle = client.get("/research/export/project-bundle")
    assert project_bundle.status_code == 200
    assert project_bundle.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(project_bundle.content)) as archive:
        names = set(archive.namelist())
        assert "README.md" in names
        assert "00-project-triage-brief.md" in names
        assert "01-progress-overview.md" in names
        assert "02-readiness-overview.md" in names
        assert "03-task-board.md" in names
        assert "04-opportunity-radar.md" in names
        assert "05-quality-gate-overview.md" in names
        assert "06-claim-validation-queue.md" in names
        assert "metadata/manifest.json" in names
        assert "metadata/triage-brief.json" in names
        assert "metadata/triage-snapshots.json" in names
        assert "metadata/triage-snapshot-comparison.json" in names
        assert "metadata/pilot-report-snapshots.json" in names
        assert "metadata/pilot-report-snapshot-comparison.json" in names
        assert "metadata/bundle-readiness-snapshots.json" in names
        assert "metadata/bundle-readiness-snapshot-comparison.json" in names
        assert "metadata/project-bundle-releases.json" in names
        assert "metadata/project-bundle-release-progress.json" in names
        assert "metadata/project-bundle-release-feedback.json" in names
        assert "metadata/project-bundle-release-closeout.json" in names
        assert "metadata/project-bundle-release-acceptance-packet.json" in names
        assert "metadata/project-bundle-release-acceptance-packet-snapshots.json" in names
        assert "metadata/project-bundle-release-acceptance-packet-snapshot-comparison.json" in names
        assert "metadata/project-bundle-release-review-session.json" in names
        assert "metadata/project-bundle-release-review-outcomes.json" in names
        assert "metadata/project-bundle-release-review-outcome-progress.json" in names
        assert "metadata/project-bundle-release-review-outcome-signoffs.json" in names
        assert "metadata/quality-gate-overview.json" in names
        assert "metadata/opportunity-radar.json" in names
        assert "metadata/claim-validation-queue.json" in names
        assert (
            f"artifacts/triage/project-triage-snapshot-{triage_snapshot_body['id']}.md"
        ) in names
        assert "artifacts/triage/latest-triage-snapshot-comparison.md" in names
        assert (f"artifacts/pilot/pilot-report-snapshot-{pilot_snapshot_body['id']}.md") in names
        assert "artifacts/pilot/latest-pilot-report-snapshot-comparison.md" in names
        assert (
            "artifacts/readiness/project-bundle-readiness-snapshot-"
            f"{project_bundle_readiness_snapshot_body['id']}.md"
        ) in names
        assert "artifacts/readiness/latest-bundle-readiness-snapshot-comparison.md" in names
        assert (
            f"artifacts/releases/project-bundle-release-{project_bundle_release_body['id']}.md"
        ) in names
        assert (
            "artifacts/releases/project-bundle-release-feedback-"
            f"{project_bundle_release_feedback_body['id']}.md"
        ) in names
        assert "artifacts/releases/latest-project-bundle-release-progress.md" in names
        assert "artifacts/releases/latest-project-bundle-release-feedback.md" in names
        assert "artifacts/releases/latest-project-bundle-release-closeout.md" in names
        assert "artifacts/releases/latest-project-bundle-release-acceptance-packet.md" in names
        assert (
            "artifacts/releases/project-bundle-release-acceptance-packet-snapshot-"
            f"{project_bundle_release_acceptance_snapshot_body['id']}.md"
        ) in names
        assert (
            "artifacts/releases/latest-project-bundle-release-acceptance-packet-snapshot.md"
            in names
        )
        assert (
            "artifacts/releases/"
            "latest-project-bundle-release-acceptance-packet-snapshot-comparison.md" in names
        )
        assert "artifacts/releases/latest-project-bundle-release-review-session.md" in names
        assert (
            "artifacts/releases/project-bundle-release-review-outcome-"
            f"{project_bundle_release_review_outcome_body['id']}.md"
        ) in names
        assert "artifacts/releases/latest-project-bundle-release-review-outcome.md" in names
        assert (
            "artifacts/releases/latest-project-bundle-release-review-outcome-progress.md" in names
        )
        assert (
            "artifacts/releases/project-bundle-release-review-outcome-signoff-"
            f"{project_bundle_release_review_outcome_signoff_body['id']}.md"
        ) in names
        assert "artifacts/releases/latest-project-bundle-release-review-outcome-signoff.md" in names
        project_manifest = json.loads(archive.read("metadata/manifest.json"))
        bundled_claim_queue = json.loads(archive.read("metadata/claim-validation-queue.json"))
        bundled_triage_comparison = json.loads(
            archive.read("metadata/triage-snapshot-comparison.json")
        )
        bundled_pilot_snapshots = json.loads(archive.read("metadata/pilot-report-snapshots.json"))
        bundled_pilot_comparison = json.loads(
            archive.read("metadata/pilot-report-snapshot-comparison.json")
        )
        bundled_bundle_readiness_snapshots = json.loads(
            archive.read("metadata/bundle-readiness-snapshots.json")
        )
        bundled_bundle_readiness_comparison = json.loads(
            archive.read("metadata/bundle-readiness-snapshot-comparison.json")
        )
        bundled_project_bundle_releases = json.loads(
            archive.read("metadata/project-bundle-releases.json")
        )
        bundled_project_bundle_release_progress = json.loads(
            archive.read("metadata/project-bundle-release-progress.json")
        )
        bundled_project_bundle_release_feedback = json.loads(
            archive.read("metadata/project-bundle-release-feedback.json")
        )
        bundled_project_bundle_release_closeout = json.loads(
            archive.read("metadata/project-bundle-release-closeout.json")
        )
        bundled_project_bundle_release_acceptance_packet = json.loads(
            archive.read("metadata/project-bundle-release-acceptance-packet.json")
        )
        bundled_project_bundle_release_acceptance_packet_snapshots = json.loads(
            archive.read("metadata/project-bundle-release-acceptance-packet-snapshots.json")
        )
        bundled_project_bundle_release_acceptance_packet_snapshot_comparison = json.loads(
            archive.read(
                "metadata/project-bundle-release-acceptance-packet-snapshot-comparison.json"
            )
        )
        bundled_project_bundle_release_review_session = json.loads(
            archive.read("metadata/project-bundle-release-review-session.json")
        )
        bundled_project_bundle_release_review_outcomes = json.loads(
            archive.read("metadata/project-bundle-release-review-outcomes.json")
        )
        bundled_project_bundle_release_review_outcome_progress = json.loads(
            archive.read("metadata/project-bundle-release-review-outcome-progress.json")
        )
        bundled_project_bundle_release_review_outcome_signoffs = json.loads(
            archive.read("metadata/project-bundle-release-review-outcome-signoffs.json")
        )
        assert project_manifest["idea_count"] >= 1
        assert readiness_manifest["bundle_type"] == "research_project_bundle"
        assert (
            project_manifest["triage_snapshot_count"] == readiness_manifest["triage_snapshot_count"]
        )
        assert (
            project_manifest["pilot_report_snapshot_count"]
            == readiness_manifest["pilot_report_snapshot_count"]
        )
        assert (
            project_manifest["claim_validation_queue_count"]
            == readiness_manifest["claim_validation_queue_count"]
        )
        assert project_manifest["quality_gate_idea_count"] >= 1
        assert project_manifest["average_quality_gate_score"] >= 0
        assert project_manifest["quality_gate_decision_counts"]
        assert project_manifest["triage_next_action_count"] >= 1
        assert project_manifest["triage_snapshot_count"] >= 2
        assert project_manifest["latest_triage_snapshot_id"] == triage_snapshot_body["id"]
        assert project_manifest["triage_snapshot_comparison_available"] is True
        assert (
            project_manifest["latest_triage_snapshot_comparison_baseline_id"]
            == baseline_triage_snapshot_body["id"]
        )
        assert (
            project_manifest["latest_triage_snapshot_comparison_candidate_id"]
            == triage_snapshot_body["id"]
        )
        assert bundled_triage_comparison["candidate_snapshot_id"] == triage_snapshot_body["id"]
        assert project_manifest["pilot_report_snapshot_count"] >= 2
        assert project_manifest["latest_pilot_report_snapshot_id"] == pilot_snapshot_body["id"]
        assert project_manifest["pilot_report_snapshot_comparison_available"] is True
        assert (
            project_manifest["latest_pilot_report_snapshot_comparison_baseline_id"]
            == baseline_pilot_snapshot_body["id"]
        )
        assert (
            project_manifest["latest_pilot_report_snapshot_comparison_candidate_id"]
            == pilot_snapshot_body["id"]
        )
        assert bundled_pilot_snapshots[0]["id"] == pilot_snapshot_body["id"]
        assert bundled_pilot_comparison["candidate_snapshot_id"] == pilot_snapshot_body["id"]
        assert project_manifest["bundle_readiness_snapshot_count"] >= 2
        assert (
            project_manifest["latest_bundle_readiness_snapshot_id"]
            == project_bundle_readiness_snapshot_body["id"]
        )
        assert project_manifest["latest_bundle_readiness_snapshot_level"] == "delivery_ready"
        assert project_manifest["latest_bundle_readiness_snapshot_score"] == 1.0
        assert project_manifest["bundle_readiness_snapshot_comparison_available"] is True
        assert (
            project_manifest["latest_bundle_readiness_snapshot_comparison_baseline_id"]
            == baseline_bundle_readiness_snapshot_body["id"]
        )
        assert (
            project_manifest["latest_bundle_readiness_snapshot_comparison_candidate_id"]
            == project_bundle_readiness_snapshot_body["id"]
        )
        assert (
            bundled_bundle_readiness_snapshots[0]["id"]
            == (project_bundle_readiness_snapshot_body["id"])
        )
        assert (
            bundled_bundle_readiness_comparison["candidate_snapshot_id"]
            == project_bundle_readiness_snapshot_body["id"]
        )
        assert project_manifest["project_bundle_release_count"] >= 1
        assert (
            project_manifest["latest_project_bundle_release_id"]
            == project_bundle_release_body["id"]
        )
        assert project_manifest["latest_project_bundle_release_recipient"] == "pytest advisor"
        assert project_manifest["latest_project_bundle_release_progress_available"] is True
        assert project_manifest["latest_project_bundle_release_progress_completion_ratio"] == 0.0
        assert project_manifest["latest_project_bundle_release_progress_open_task_count"] >= 1
        assert project_manifest["latest_project_bundle_release_progress_blocked_task_count"] >= 0
        assert bundled_project_bundle_releases[0]["id"] == project_bundle_release_body["id"]
        assert (
            bundled_project_bundle_release_progress["release_id"]
            == project_bundle_release_body["id"]
        )
        assert bundled_project_bundle_release_progress["task_summary"]["open_task_count"] >= 1
        assert project_manifest["project_bundle_release_feedback_count"] >= 1
        assert (
            project_manifest["latest_project_bundle_release_feedback_id"]
            == project_bundle_release_feedback_body["id"]
        )
        assert (
            project_manifest["latest_project_bundle_release_feedback_release_id"]
            == project_bundle_release_body["id"]
        )
        assert (
            project_manifest["latest_project_bundle_release_feedback_status"] == "changes_requested"
        )
        assert project_manifest["latest_project_bundle_release_feedback_signoff_confirmed"] is False
        assert (
            bundled_project_bundle_release_feedback[0]["id"]
            == (project_bundle_release_feedback_body["id"])
        )
        assert project_manifest["latest_project_bundle_release_closeout_available"] is True
        assert project_manifest["latest_project_bundle_release_closeout_status"] == "blocked"
        assert project_manifest["latest_project_bundle_release_closeout_ready"] is False
        assert project_manifest["latest_project_bundle_release_closeout_next_action_count"] >= 1
        assert project_manifest["latest_project_bundle_release_closeout_blocker_count"] >= 1
        assert (
            bundled_project_bundle_release_closeout["release_id"]
            == project_bundle_release_body["id"]
        )
        assert bundled_project_bundle_release_closeout["closeout_status"] == "blocked"
        assert project_manifest["latest_project_bundle_release_acceptance_packet_available"] is True
        assert project_manifest["latest_project_bundle_release_acceptance_status"] == "blocked"
        assert (
            project_manifest["latest_project_bundle_release_acceptance_ready_for_signoff"] is False
        )
        assert (
            project_manifest["latest_project_bundle_release_acceptance_remaining_action_count"] >= 1
        )
        assert (
            project_manifest["latest_project_bundle_release_acceptance_open_closeout_task_count"]
            >= 1
        )
        assert (
            bundled_project_bundle_release_acceptance_packet["release_id"]
            == project_bundle_release_body["id"]
        )
        assert bundled_project_bundle_release_acceptance_packet["acceptance_status"] == "blocked"
        assert project_manifest["project_bundle_release_acceptance_packet_snapshot_count"] >= 1
        assert (
            project_manifest["latest_project_bundle_release_acceptance_packet_snapshot_id"]
            == project_bundle_release_acceptance_snapshot_body["id"]
        )
        assert (
            project_manifest["latest_project_bundle_release_acceptance_packet_snapshot_release_id"]
            == project_bundle_release_body["id"]
        )
        assert (
            project_manifest["latest_project_bundle_release_acceptance_packet_snapshot_status"]
            == "blocked"
        )
        assert (
            project_manifest[
                "latest_project_bundle_release_acceptance_packet_snapshot_ready_for_signoff"
            ]
            is False
        )
        assert (
            bundled_project_bundle_release_acceptance_packet_snapshots[0]["id"]
            == project_bundle_release_acceptance_snapshot_body["id"]
        )
        assert (
            project_manifest[
                "project_bundle_release_acceptance_packet_snapshot_comparison_available"
            ]
            is True
        )
        assert (
            project_manifest[
                "latest_project_bundle_release_acceptance_packet_snapshot_comparison_baseline_id"
            ]
            == baseline_project_bundle_release_acceptance_snapshot_body["id"]
        )
        assert (
            project_manifest[
                "latest_project_bundle_release_acceptance_packet_snapshot_comparison_candidate_id"
            ]
            == project_bundle_release_acceptance_snapshot_body["id"]
        )
        assert project_manifest[
            "latest_project_bundle_release_acceptance_packet_snapshot_comparison_added_action_count"
        ] == len(
            project_bundle_release_acceptance_snapshot_comparison_body["added_remaining_actions"]
        )
        assert project_manifest[
            "latest_project_bundle_release_acceptance_packet_snapshot_comparison_new_checklist_count"
        ] == len(
            project_bundle_release_acceptance_snapshot_comparison_body[
                "newly_blocked_checklist_items"
            ]
        )
        assert (
            bundled_project_bundle_release_acceptance_packet_snapshot_comparison[
                "candidate_snapshot_id"
            ]
            == project_bundle_release_acceptance_snapshot_body["id"]
        )
        assert project_manifest["latest_project_bundle_release_review_session_available"] is True
        assert (
            project_manifest["latest_project_bundle_release_review_session_status"]
            == "blocked_review"
        )
        assert project_manifest["latest_project_bundle_release_review_session_ready"] is True
        assert project_manifest[
            "latest_project_bundle_release_review_session_decision_count"
        ] == len(project_bundle_release_review_session_body["decisions_needed"])
        assert project_manifest["latest_project_bundle_release_review_session_risk_count"] == len(
            project_bundle_release_review_session_body["risk_items"]
        )
        assert project_manifest[
            "latest_project_bundle_release_review_session_follow_up_count"
        ] == len(project_bundle_release_review_session_body["follow_up_actions"])
        assert (
            bundled_project_bundle_release_review_session["release_id"]
            == project_bundle_release_body["id"]
        )
        assert bundled_project_bundle_release_review_session["review_status"] == "blocked_review"
        assert project_manifest["project_bundle_release_review_outcome_count"] >= 1
        assert (
            project_manifest["latest_project_bundle_release_review_outcome_id"]
            == project_bundle_release_review_outcome_body["id"]
        )
        assert (
            project_manifest["latest_project_bundle_release_review_outcome_release_id"]
            == project_bundle_release_body["id"]
        )
        assert (
            project_manifest["latest_project_bundle_release_review_outcome_decision"]
            == "follow_up_needed"
        )
        assert (
            project_manifest["latest_project_bundle_release_review_outcome_signoff_confirmed"]
            is False
        )
        assert project_manifest[
            "latest_project_bundle_release_review_outcome_follow_up_count"
        ] == len(project_bundle_release_review_outcome_body["summary"]["follow_up_actions"])
        assert project_manifest["latest_project_bundle_release_review_outcome_risk_count"] == len(
            project_bundle_release_review_outcome_body["summary"]["risks"]
        )
        assert (
            bundled_project_bundle_release_review_outcomes[0]["id"]
            == project_bundle_release_review_outcome_body["id"]
        )
        assert (
            project_manifest["latest_project_bundle_release_review_outcome_progress_available"]
            is True
        )
        assert (
            project_manifest[
                "latest_project_bundle_release_review_outcome_progress_completion_ratio"
            ]
            == project_bundle_release_review_outcome_progress_body["completion_ratio"]
        )
        assert (
            project_manifest[
                "latest_project_bundle_release_review_outcome_progress_open_task_count"
            ]
            >= 1
        )
        assert (
            project_manifest[
                "latest_project_bundle_release_review_outcome_progress_blocked_task_count"
            ]
            >= 0
        )
        assert (
            bundled_project_bundle_release_review_outcome_progress["outcome_id"]
            == project_bundle_release_review_outcome_body["id"]
        )
        assert project_manifest["project_bundle_release_review_outcome_signoff_count"] >= 1
        assert (
            project_manifest["latest_project_bundle_release_review_outcome_signoff_id"]
            == project_bundle_release_review_outcome_signoff_body["id"]
        )
        assert (
            project_manifest["latest_project_bundle_release_review_outcome_signoff_release_id"]
            == project_bundle_release_body["id"]
        )
        assert (
            project_manifest["latest_project_bundle_release_review_outcome_signoff_outcome_id"]
            == project_bundle_release_review_outcome_body["id"]
        )
        assert (
            project_manifest["latest_project_bundle_release_review_outcome_signoff_decision"]
            == "deferred"
        )
        assert (
            project_manifest[
                "latest_project_bundle_release_review_outcome_signoff_record_confirmed"
            ]
            is False
        )
        assert (
            project_manifest[
                "latest_project_bundle_release_review_outcome_signoff_progress_completion_ratio"
            ]
            == project_bundle_release_review_outcome_signoff_body["summary"][
                "progress_completion_ratio"
            ]
        )
        assert (
            project_manifest[
                "latest_project_bundle_release_review_outcome_signoff_progress_open_task_count"
            ]
            >= 1
        )
        assert (
            bundled_project_bundle_release_review_outcome_signoffs[0]["id"]
            == project_bundle_release_review_outcome_signoff_body["id"]
        )
        assert project_manifest["opportunity_count"] >= 1
        assert project_manifest["claim_validation_queue_count"] >= 1
        assert project_manifest["claim_validation_queue_idea_count"] >= 1
        assert project_manifest["claim_validation_queue_by_priority"]
        assert bundled_claim_queue["summary"]["item_count"] >= 1
        assert (
            bundled_claim_queue["summary"]["item_count"]
            == project_manifest["claim_validation_queue_count"]
        )
        assert bundled_claim_queue["items"][0]["ledger_id"]
        assert bundled_claim_queue["items"][0]["claim_id"]
        assert "# Claim Validation Queue" in archive.read("06-claim-validation-queue.md").decode()
        assert project_manifest["recent_task_count"] >= 1


def test_refine_idea_creates_traceable_revision() -> None:
    client = TestClient(create_app())
    content = b"""Idea Refinement Test Paper

Introduction
Research assistants need to revise generated ideas after reviewer criticism and novelty screening.

Limitations
Initial ideas often lack a sharp novelty claim and first executable experiment.

Conclusion
Future work should keep parent-child idea lineage for proposal iteration.
"""
    upload = client.post(
        "/research/papers/upload",
        files={"file": ("idea_refinement_test.txt", content, "text/plain")},
    )
    assert upload.status_code == 200
    paper_id = upload.json()["paper"]["id"]
    gaps = client.post("/research/gaps/mine", json={"paper_ids": [paper_id], "max_gaps": 1})
    assert gaps.status_code == 200
    gap_id = gaps.json()["gaps"][0]["id"]
    ideas = client.post(f"/research/gaps/{gap_id}/ideas")
    assert ideas.status_code == 200
    source_idea = ideas.json()["ideas"][0]
    idea_id = source_idea["id"]

    assert client.post(f"/research/ideas/{idea_id}/novelty-check").status_code == 200
    assert client.post(f"/research/ideas/{idea_id}/review").status_code == 200
    assert client.post(f"/research/ideas/{idea_id}/experiment-plan").status_code == 200

    refined = client.post(
        f"/research/ideas/{idea_id}/refine",
        json={"focus": "sharpen novelty and first executable experiment"},
    )
    assert refined.status_code == 200
    body = refined.json()
    refined_idea = body["refined_idea"]
    assert body["source_idea"]["id"] == idea_id
    assert refined_idea["parent_idea_id"] == idea_id
    assert refined_idea["version"] == source_idea["version"] + 1
    assert refined_idea["status"] == "refined"
    assert refined_idea["evidence_ids"] == source_idea["evidence_ids"]
    assert "sharpen novelty" in refined_idea["title"]
    assert body["applied_actions"]

    fetched = client.get(f"/research/ideas/{refined_idea['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["parent_idea_id"] == idea_id

    dossier = client.get(f"/research/ideas/{refined_idea['id']}/export/markdown")
    assert dossier.status_code == 200
    assert f"- Parent Idea ID: `{idea_id}`" in dossier.text

    edges = client.get("/research/graph/edges?edge_type=idea_refines_idea")
    assert edges.status_code == 200
    assert edges.json()


def test_rank_ideas_deduplicates_lineage_and_returns_breakdown() -> None:
    client = TestClient(create_app())
    content = b"""Idea Ranking Test Paper

Abstract
This paper checks whether research ideas can be ranked for portfolio review.

Introduction
Researchers need to choose among several generated and revised ideas.

Method
The assistant should combine idea scores with novelty risk, evidence, and experiment readiness.

Conclusion
Future work should learn ranking weights from researcher feedback.
"""
    upload = client.post(
        "/research/papers/upload",
        files={"file": ("idea_ranking_test.txt", content, "text/plain")},
    )
    assert upload.status_code == 200
    paper_id = upload.json()["paper"]["id"]

    workflow = client.post(
        "/research/workflows/literature-to-ideas",
        json={
            "paper_id": paper_id,
            "max_gaps": 2,
            "max_ideas_per_gap": 1,
            "include_markdown_export": False,
        },
    )
    assert workflow.status_code == 200
    source_idea_id = workflow.json()["ideas"][0]["id"]

    refined = client.post(
        f"/research/ideas/{source_idea_id}/refine",
        json={"focus": "rank the most publishable experiment-first variant"},
    )
    assert refined.status_code == 200
    refined_idea_id = refined.json()["refined_idea"]["id"]

    ranking = client.post(
        "/research/ideas/rank",
        json={
            "paper_ids": [paper_id],
            "limit": 5,
            "deduplicate_lineage": True,
        },
    )
    assert ranking.status_code == 200
    body = ranking.json()
    assert body["ranked_ideas"]
    assert "Ranked" in body["message"]
    scores = [item["weighted_score"] for item in body["ranked_ideas"]]
    assert scores == sorted(scores, reverse=True)
    ids = [item["idea"]["id"] for item in body["ranked_ideas"]]
    assert refined_idea_id in ids
    assert source_idea_id not in ids
    assert body["ranked_ideas"][0]["rank"] == 1
    assert "resource_efficiency" in body["ranked_ideas"][0]["score_breakdown"]
    assert body["ranked_ideas"][0]["rationale"]

    feedback = client.post(
        f"/research/ideas/{refined_idea_id}/feedback",
        json={
            "decision": "shortlist",
            "rating": 4.8,
            "comment": "Promising because the first experiment is clear.",
            "tags": ["publishable", "experiment-first"],
        },
    )
    assert feedback.status_code == 200
    feedback_body = feedback.json()
    assert feedback_body["idea_id"] == refined_idea_id
    assert feedback_body["decision"] == "shortlist"
    assert feedback_body["rating"] == 4.8
    assert feedback_body["tags"] == ["publishable", "experiment-first"]

    listed_feedback = client.get(f"/research/ideas/{refined_idea_id}/feedback")
    assert listed_feedback.status_code == 200
    assert listed_feedback.json()[0]["id"] == feedback_body["id"]

    reranked = client.post(
        "/research/ideas/rank",
        json={"idea_ids": [source_idea_id, refined_idea_id], "deduplicate_lineage": True},
    )
    assert reranked.status_code == 200
    top = reranked.json()["ranked_ideas"][0]
    assert top["idea"]["id"] == refined_idea_id
    assert any("Human feedback" in item for item in top["rationale"])

    export = client.post(
        "/research/ideas/rank/export/markdown",
        json={
            "idea_ids": [source_idea_id, refined_idea_id],
            "deduplicate_lineage": True,
            "title": "Ranking Test Portfolio",
        },
    )
    assert export.status_code == 200
    assert export.headers["content-type"].startswith("text/markdown")
    assert "# Ranking Test Portfolio" in export.text
    assert f"- Idea ID: `{refined_idea_id}`" in export.text
    assert f"- Idea ID: `{source_idea_id}`" not in export.text
    assert "### Score Breakdown" in export.text
    assert "Human feedback decision is shortlist" in export.text

    snapshot = client.post(
        "/research/ideas/portfolios",
        json={
            "idea_ids": [source_idea_id, refined_idea_id],
            "deduplicate_lineage": True,
            "title": "Saved Ranking Test Portfolio",
            "description": "Portfolio saved for regression testing.",
            "created_by": "pytest",
        },
    )
    assert snapshot.status_code == 200
    snapshot_body = snapshot.json()
    assert snapshot_body["title"] == "Saved Ranking Test Portfolio"
    assert snapshot_body["description"] == "Portfolio saved for regression testing."
    assert snapshot_body["created_by"] == "pytest"
    assert refined_idea_id in snapshot_body["idea_ids"]
    assert source_idea_id not in snapshot_body["idea_ids"]
    assert "Saved Ranking Test Portfolio" in snapshot_body["markdown_export"]
    assert snapshot_body["markdown_export_chars"] == len(snapshot_body["markdown_export"])

    fetched_snapshot = client.get(f"/research/ideas/portfolios/{snapshot_body['id']}")
    assert fetched_snapshot.status_code == 200
    assert fetched_snapshot.json()["id"] == snapshot_body["id"]

    snapshot_export = client.get(
        f"/research/ideas/portfolios/{snapshot_body['id']}/export/markdown"
    )
    assert snapshot_export.status_code == 200
    assert snapshot_export.headers["content-type"].startswith("text/markdown")
    assert "# Saved Ranking Test Portfolio" in snapshot_export.text

    agenda_export = client.get(f"/research/ideas/portfolios/{snapshot_body['id']}/agenda/markdown")
    assert agenda_export.status_code == 200
    assert agenda_export.headers["content-type"].startswith("text/markdown")
    assert "# Research Execution Agenda: Saved Ranking Test Portfolio" in agenda_export.text
    assert "## 30/60/90 Day Plan" in agenda_export.text
    assert refined_idea_id in agenda_export.text

    snapshots = client.get("/research/ideas/portfolios?limit=5")
    assert snapshots.status_code == 200
    assert any(item["id"] == snapshot_body["id"] for item in snapshots.json())

    baseline_snapshot = client.post(
        "/research/ideas/portfolios",
        json={
            "idea_ids": [source_idea_id],
            "deduplicate_lineage": False,
            "title": "Baseline Ranking Test Portfolio",
        },
    )
    assert baseline_snapshot.status_code == 200
    baseline_body = baseline_snapshot.json()

    comparison = client.post(
        "/research/ideas/portfolios/compare",
        json={
            "baseline_snapshot_id": baseline_body["id"],
            "candidate_snapshot_id": snapshot_body["id"],
        },
    )
    assert comparison.status_code == 200
    comparison_body = comparison.json()
    assert refined_idea_id in comparison_body["added_idea_ids"]
    assert source_idea_id in comparison_body["removed_idea_ids"]
    assert "Compared portfolio snapshots" in comparison_body["summary"]
    assert "# Research Idea Portfolio Comparison" in comparison_body["markdown_export"]

    comparison_export = client.post(
        "/research/ideas/portfolios/compare/export/markdown",
        json={
            "baseline_snapshot_id": baseline_body["id"],
            "candidate_snapshot_id": snapshot_body["id"],
        },
    )
    assert comparison_export.status_code == 200
    assert comparison_export.headers["content-type"].startswith("text/markdown")
    assert "`" + refined_idea_id + "`" in comparison_export.text


def test_markdown_exports_for_card_and_idea_dossier() -> None:
    client = TestClient(create_app())
    content = b"""Markdown Export Test Paper

Introduction
Research assistants should turn evidence-backed ideas into portable proposal notes.

Method
The system links papers, evidence, gaps, ideas, reviewer critiques, and experiment plans.

Limitations
The current workflow still needs exportable dossiers for researcher review.

Conclusion
Future work should make generated ideas easy to share and revise.
"""
    upload = client.post(
        "/research/papers/upload",
        files={"file": ("markdown_export_test.txt", content, "text/plain")},
    )
    assert upload.status_code == 200
    paper_id = upload.json()["paper"]["id"]

    extract = client.post(f"/research/papers/{paper_id}/card/extract-structured")
    assert extract.status_code == 200

    card_export = client.get(f"/research/papers/{paper_id}/card/export/markdown")
    assert card_export.status_code == 200
    assert card_export.headers["content-type"].startswith("text/markdown")
    assert "# Paper Card:" in card_export.text
    assert "## Method" in card_export.text
    assert "Evidence IDs" not in card_export.text

    gaps = client.post("/research/gaps/mine", json={"paper_ids": [paper_id], "max_gaps": 2})
    assert gaps.status_code == 200
    gap_id = gaps.json()["gaps"][0]["id"]
    ideas = client.post(f"/research/gaps/{gap_id}/ideas")
    assert ideas.status_code == 200
    idea_id = ideas.json()["ideas"][0]["id"]

    review = client.post(f"/research/ideas/{idea_id}/review")
    assert review.status_code == 200
    plan = client.post(f"/research/ideas/{idea_id}/experiment-plan")
    assert plan.status_code == 200

    idea_export = client.get(f"/research/ideas/{idea_id}/export/markdown")
    assert idea_export.status_code == 200
    assert idea_export.headers["content-type"].startswith("text/markdown")
    markdown = idea_export.text
    assert "# Research Idea Dossier:" in markdown
    assert "## Related Research Gaps" in markdown
    assert "## Evidence" in markdown
    assert "## Reviewer Simulation" in markdown
    assert "## Experiment Plan" in markdown
    assert f"`{gap_id}`" in markdown


def test_literature_to_ideas_workflow_runs_full_pipeline() -> None:
    client = TestClient(create_app())
    content = b"""Workflow Test Paper

Abstract
This paper checks whether the research assistant can run a full workflow.

Introduction
Researchers need a single operation that moves from literature evidence to idea dossiers.

Method
The workflow should extract a card, mine gaps, generate ideas, review them, plan experiments, and export markdown.

Limitations
The workflow is deterministic in the MVP and still needs external novelty checks.

Conclusion
Future work should connect the workflow to front-end actions and MCP tools.
"""
    upload = client.post(
        "/research/papers/upload",
        files={"file": ("workflow_test.txt", content, "text/plain")},
    )
    assert upload.status_code == 200
    paper_id = upload.json()["paper"]["id"]

    response = client.post(
        "/research/workflows/literature-to-ideas",
        json={
            "paper_id": paper_id,
            "max_gaps": 2,
            "max_ideas_per_gap": 1,
            "include_markdown_export": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["job_id"]
    assert body["paper"]["id"] == paper_id
    assert body["card"]["payload"]["method"]
    assert len(body["gaps"]) >= 1
    assert len(body["ideas"]) == len(body["gaps"])
    assert len(body["novelty_checks"]) == len(body["ideas"])
    assert len(body["reviews"]) == len(body["ideas"])
    assert len(body["experiment_plans"]) == len(body["ideas"])
    assert "# Research Idea Dossier:" in body["markdown_export"]
    assert "Completed literature-to-ideas workflow" in body["message"]

    job = client.get(f"/research/jobs/{body['job_id']}")
    assert job.status_code == 200
    job_body = job.json()
    assert job_body["status"] == "completed"
    assert job_body["progress"] == 1.0
    assert job_body["output"]["paper_id"] == paper_id
    assert len(job_body["output"]["idea_ids"]) == len(body["ideas"])

    artifacts = client.get(f"/research/jobs/{body['job_id']}/artifacts")
    assert artifacts.status_code == 200
    artifact_body = artifacts.json()
    assert artifact_body["job"]["id"] == body["job_id"]
    assert artifact_body["paper"]["id"] == paper_id
    assert artifact_body["card"]["id"] == body["card"]["id"]
    assert len(artifact_body["gaps"]) == len(body["gaps"])
    assert len(artifact_body["ideas"]) == len(body["ideas"])
    assert len(artifact_body["novelty_checks"]) == len(body["novelty_checks"])
    assert len(artifact_body["reviews"]) == len(body["reviews"])
    assert len(artifact_body["experiment_plans"]) == len(body["experiment_plans"])
    assert "# Research Idea Dossier:" in artifact_body["markdown_export"]
    assert "Loaded artifact snapshot" in artifact_body["message"]

    jobs = client.get("/research/jobs?limit=5")
    assert jobs.status_code == 200
    assert any(item["id"] == body["job_id"] for item in jobs.json())


def test_async_literature_to_ideas_workflow_completes_job_trace() -> None:
    client = TestClient(create_app())
    content = b"""Async Workflow Test Paper

Abstract
This paper checks whether long research workflows can be queued as jobs.

Introduction
Research workbench users need a fast response with a trackable workflow job id.

Method
The async endpoint should queue a job and run the literature-to-ideas pipeline in the background.

Conclusion
Future work should connect async jobs to a frontend progress view and MCP tools.
"""
    upload = client.post(
        "/research/papers/upload",
        files={"file": ("async_workflow_test.txt", content, "text/plain")},
    )
    assert upload.status_code == 200
    paper_id = upload.json()["paper"]["id"]

    queued = client.post(
        "/research/workflows/literature-to-ideas/async",
        json={
            "paper_id": paper_id,
            "max_gaps": 1,
            "max_ideas_per_gap": 1,
            "include_markdown_export": False,
        },
    )
    assert queued.status_code == 200
    queued_body = queued.json()
    assert queued_body["job_type"] == "literature_to_ideas_workflow"
    assert queued_body["status"] in {"pending", "running", "completed"}
    assert queued_body["input"]["paper_id"] == paper_id

    job_body = queued_body
    for _ in range(30):
        job = client.get(f"/research/jobs/{queued_body['id']}")
        assert job.status_code == 200
        job_body = job.json()
        if job_body["status"] in {"completed", "failed"}:
            break
        time.sleep(0.05)

    assert job_body["status"] == "completed"
    assert job_body["progress"] == 1.0
    assert job_body["output"]["paper_id"] == paper_id
    assert job_body["output"]["card_id"]
    assert len(job_body["output"]["idea_ids"]) >= 1


def _hit_at_k(ordered_ids: list[str], expected_ids: set[str], k: int) -> float:
    return 1.0 if any(item_id in expected_ids for item_id in ordered_ids[:k]) else 0.0


def _mean_reciprocal_rank(ordered_ids: list[str], expected_ids: set[str]) -> float:
    for index, item_id in enumerate(ordered_ids, start=1):
        if item_id in expected_ids:
            return round(1.0 / index, 4)
    return 0.0


def _score_breakdown_coverage(items: list[dict]) -> float:
    if not items:
        return 1.0
    required_keys = {"lexical", "bonus", "phrase", "vector"}
    covered = [item for item in items if required_keys.issubset(item.get("score_breakdown", {}))]
    return round(len(covered) / len(items), 4)


def _score_breakdown_total_match_rate(items: list[dict]) -> float:
    if not items:
        return 1.0

    matched = []
    for item in items:
        breakdown = item.get("score_breakdown", {})
        breakdown_total = round(sum(float(value) for value in breakdown.values()), 4)
        visible_score = round(float(item["score"]), 4)
        matched.append(abs(breakdown_total - visible_score) <= 0.0001)
    return round(sum(matched) / len(items), 4)


def _graph_edge_hit_rate(edges: list[dict], expected_edge_types: set[str]) -> float:
    if not expected_edge_types:
        return 1.0
    returned_edge_types = {edge["edge_type"] for edge in edges}
    hits = expected_edge_types.intersection(returned_edge_types)
    return round(len(hits) / len(expected_edge_types), 4)


def _graph_noise_rate(edges: list[dict], allowed_edge_types: set[str]) -> float:
    if not edges:
        return 0.0
    noisy = [edge for edge in edges if edge["edge_type"] not in allowed_edge_types]
    return round(len(noisy) / len(edges), 4)


def _evidence_paper_filter_leak_rate(items: list[dict], allowed_paper_ids: set[str]) -> float:
    if not items:
        return 0.0

    leaked = [item for item in items if item["evidence"]["paper_id"] not in allowed_paper_ids]
    return round(len(leaked) / len(items), 4)


def _gap_paper_filter_leak_rate(items: list[dict], allowed_paper_ids: set[str]) -> float:
    if not items:
        return 0.0

    leaked = [
        item
        for item in items
        if not set(item["gap"]["source_paper_ids"]).intersection(allowed_paper_ids)
    ]
    return round(len(leaked) / len(items), 4)


def _idea_paper_filter_leak_rate(items: list[dict], allowed_paper_ids: set[str]) -> float:
    if not items:
        return 0.0

    leaked = [
        item
        for item in items
        if not set(item["idea"]["related_paper_ids"]).intersection(allowed_paper_ids)
    ]
    return round(len(leaked) / len(items), 4)


def _hash_embedding_bucket(token: str) -> tuple[int, float]:
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    index = int.from_bytes(digest[:4], "big") % 128
    sign = 1.0 if digest[4] % 2 == 0 else -1.0
    return index, sign


def _find_hash_vector_collision(query_token: str) -> str:
    target = _hash_embedding_bucket(query_token)
    for index in range(50_000):
        candidate = f"vectoronly{index}"
        if query_token not in candidate and _hash_embedding_bucket(candidate) == target:
            return candidate
    raise AssertionError("Could not find deterministic hash-vector collision token")


def _empty_query_guard_rate(client: TestClient, queries: list[str]) -> float:
    guarded = []
    for query in queries:
        response = client.post(
            "/research/search/context",
            json={"query": query, "limit": 5, "include_graph": True},
        )
        guarded.append(response.status_code == 400)
        if response.status_code == 400:
            assert response.json()["detail"] == ("Query must contain at least one searchable term")
    return round(sum(guarded) / len(queries), 4)


def test_context_search_empty_query_guard_fixture() -> None:
    client = TestClient(create_app())
    assert _empty_query_guard_rate(client, ["", "to be", "??"]) == 1.0


def test_context_search_no_match_fixture() -> None:
    client = TestClient(create_app())
    marker = f"nomatch{time.time_ns()}"

    session = SessionLocal()
    try:
        paper = Paper(
            title=f"Context Search No Match Paper {marker}",
            filename="context_no_match.txt",
            source_type="pytest",
            status="indexed",
        )
        session.add(paper)
        session.commit()
        paper_id = paper.id
    finally:
        session.close()

    response = client.post(
        "/research/search/context",
        json={
            "query": marker,
            "paper_ids": [paper_id],
            "limit": 5,
            "include_graph": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["retrieval_method"] == "lexical_vector_graph_rag_lite_v0"
    assert body["evidences"] == []
    assert body["gaps"] == []
    assert body["ideas"] == []
    assert body["graph_nodes"] == []
    assert body["graph_edges"] == []
    assert body["answer_brief"] == f"No context matched the query: {marker}"


def test_context_search_idea_overall_score_bonus_breakdown() -> None:
    client = TestClient(create_app())
    first_term = f"ideabonusalpha{time.time_ns()}"
    second_term = f"ideabonusbeta{time.time_ns()}"

    session = SessionLocal()
    try:
        paper = Paper(
            title=f"Context Search Idea Bonus Paper {first_term}",
            filename="context_idea_bonus.txt",
            source_type="pytest",
            status="indexed",
        )
        session.add(paper)
        session.flush()
        idea = Idea(
            title=f"{first_term} idea bonus fixture",
            research_question=f"How should {first_term} support explainable retrieval?",
            core_hypothesis=f"The fixture mentions {second_term} after unrelated words.",
            motivation=f"{first_term} makes idea bonus scoring visible.",
            related_gap_ids_json=[],
            related_paper_ids_json=[paper.id],
            evidence_ids_json=[],
            method_sketch="Use a controlled pytest fixture.",
            expected_contribution="Stable idea score breakdown coverage.",
            novelty_argument="The fixture is synthetic and deterministic.",
            datasets_json=[],
            baselines_json=[],
            metrics_json=[],
            risks_json=[],
            resource_requirements="none",
            target_venues_json=[],
            score_json={"overall_score": 7.6},
            status="draft",
        )
        session.add(idea)
        session.commit()
        paper_id = paper.id
        idea_id = idea.id
    finally:
        session.close()

    response = client.post(
        "/research/search/context",
        json={
            "query": f"{first_term} {second_term}",
            "paper_ids": [paper_id],
            "limit": 3,
            "include_graph": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ideas"]
    assert body["graph_nodes"] == []
    assert body["graph_edges"] == []
    top_idea = body["ideas"][0]
    assert top_idea["idea"]["id"] == idea_id
    assert top_idea["matched_terms"][:2] == [first_term, second_term]
    assert top_idea["score_breakdown"]["lexical"] == 2.0
    assert top_idea["score_breakdown"]["bonus"] == 0.76
    assert top_idea["score_breakdown"]["phrase"] == 0.0
    assert top_idea["score_breakdown"]["vector"] > 0.0
    assert _score_breakdown_total_match_rate(body["ideas"]) == 1.0


def test_context_search_gap_feasibility_bonus_breakdown() -> None:
    client = TestClient(create_app())
    first_term = f"gapbonusalpha{time.time_ns()}"
    second_term = f"gapbonusbeta{time.time_ns()}"

    session = SessionLocal()
    try:
        paper = Paper(
            title=f"Context Search Gap Bonus Paper {first_term}",
            filename="context_gap_bonus.txt",
            source_type="pytest",
            status="indexed",
        )
        session.add(paper)
        session.flush()
        gap = ResearchGap(
            title=f"{first_term} feasibility gap",
            description=f"The gap fixture studies {first_term} retrieval scoring.",
            gap_type="evaluation",
            source_paper_ids_json=[paper.id],
            evidence_ids_json=[],
            why_important=f"{first_term} makes gap bonus scoring visible.",
            why_unsolved=f"The fixture mentions {second_term} after unrelated words.",
            possible_approaches_json=["controlled pytest fixture"],
            feasibility_score=8.4,
            novelty_score=0.0,
            risk_level="low",
            status="generated",
        )
        session.add(gap)
        session.commit()
        paper_id = paper.id
        gap_id = gap.id
    finally:
        session.close()

    response = client.post(
        "/research/search/context",
        json={
            "query": f"{first_term} {second_term}",
            "paper_ids": [paper_id],
            "limit": 3,
            "include_graph": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["gaps"]
    assert body["graph_nodes"] == []
    assert body["graph_edges"] == []
    top_gap = body["gaps"][0]
    assert top_gap["gap"]["id"] == gap_id
    assert top_gap["matched_terms"][:2] == [first_term, second_term]
    assert top_gap["score_breakdown"]["lexical"] == 2.0
    assert top_gap["score_breakdown"]["bonus"] == 0.84
    assert top_gap["score_breakdown"]["phrase"] == 0.0
    assert top_gap["score_breakdown"]["vector"] > 0.0
    assert _score_breakdown_total_match_rate(body["gaps"]) == 1.0


def test_context_search_evidence_confidence_bonus_breakdown() -> None:
    client = TestClient(create_app())
    first_term = f"bonusalpha{time.time_ns()}"
    second_term = f"bonusbeta{time.time_ns()}"

    session = SessionLocal()
    try:
        paper = Paper(
            title=f"Context Search Evidence Bonus Paper {first_term}",
            filename="context_evidence_bonus.txt",
            source_type="pytest",
            status="indexed",
        )
        session.add(paper)
        session.flush()
        evidence = Evidence(
            paper_id=paper.id,
            evidence_type="confidence_bonus",
            text=f"{first_term} appears before a separator while {second_term} appears later.",
            summary=f"The summary keeps {first_term} away from the other bonus marker.",
            supports=f"The support sentence mentions {second_term} after unrelated words.",
            confidence=0.73,
            metadata_json={"fixture": "context_search_evidence_confidence_bonus"},
        )
        session.add(evidence)
        session.commit()
        paper_id = paper.id
        evidence_id = evidence.id
    finally:
        session.close()

    response = client.post(
        "/research/search/context",
        json={
            "query": f"{first_term} {second_term}",
            "paper_ids": [paper_id],
            "limit": 3,
            "include_graph": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["evidences"]
    assert body["graph_nodes"] == []
    assert body["graph_edges"] == []
    top_evidence = body["evidences"][0]
    assert top_evidence["evidence"]["id"] == evidence_id
    assert top_evidence["matched_terms"][:2] == [first_term, second_term]
    assert top_evidence["score_breakdown"]["lexical"] == 2.0
    assert top_evidence["score_breakdown"]["bonus"] == 0.73
    assert top_evidence["score_breakdown"]["phrase"] == 0.0
    assert top_evidence["score_breakdown"]["vector"] > 0.0
    assert _score_breakdown_total_match_rate(body["evidences"]) == 1.0


def test_context_search_exact_phrase_bonus_breakdown() -> None:
    client = TestClient(create_app())
    first_term = f"phrasealpha{time.time_ns()}"
    second_term = f"phrasebeta{time.time_ns()}"
    exact_phrase = f"{first_term} {second_term}"

    session = SessionLocal()
    try:
        paper = Paper(
            title=f"Context Search Phrase Bonus Paper {first_term}",
            filename="context_phrase_bonus.txt",
            source_type="pytest",
            status="indexed",
        )
        session.add(paper)
        session.flush()
        evidence = Evidence(
            paper_id=paper.id,
            evidence_type="phrase_bonus",
            text=f"The phrase bonus fixture contains {exact_phrase} once.",
            summary=f"Summary keeps the exact ordered phrase {exact_phrase}.",
            supports=f"Supports deterministic phrase scoring for {exact_phrase}.",
            confidence=0.0,
            metadata_json={"fixture": "context_search_exact_phrase_bonus"},
        )
        session.add(evidence)
        session.commit()
        paper_id = paper.id
        evidence_id = evidence.id
    finally:
        session.close()

    response = client.post(
        "/research/search/context",
        json={
            "query": exact_phrase,
            "paper_ids": [paper_id],
            "limit": 3,
            "include_graph": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["evidences"]
    assert body["graph_nodes"] == []
    assert body["graph_edges"] == []
    top_evidence = body["evidences"][0]
    assert top_evidence["evidence"]["id"] == evidence_id
    assert top_evidence["matched_terms"][:2] == [first_term, second_term]
    assert top_evidence["score_breakdown"]["lexical"] == 2.0
    assert top_evidence["score_breakdown"]["bonus"] == 0.0
    assert top_evidence["score_breakdown"]["phrase"] == 2.0
    assert top_evidence["score_breakdown"]["vector"] > 0.0
    assert _score_breakdown_total_match_rate(body["evidences"]) == 1.0


def test_context_search_vector_hit_rescues_lexical_miss() -> None:
    client = TestClient(create_app())
    query_token = f"semanticmiss{time.time_ns()}"
    vector_token = _find_hash_vector_collision(query_token)

    session = SessionLocal()
    try:
        paper = Paper(
            title=f"Context Search Vector Miss Paper {query_token}",
            filename="context_vector_miss.txt",
            source_type="pytest",
            status="indexed",
        )
        session.add(paper)
        session.flush()
        evidence = Evidence(
            paper_id=paper.id,
            evidence_type="x",
            text=vector_token,
            summary=vector_token,
            supports=vector_token,
            confidence=0.0,
            metadata_json={"fixture": "context_search_vector_lexical_miss"},
        )
        session.add(evidence)
        session.commit()
        paper_id = paper.id
        evidence_id = evidence.id
    finally:
        session.close()

    response = client.post(
        "/research/search/context",
        json={
            "query": query_token,
            "paper_ids": [paper_id],
            "limit": 3,
            "include_graph": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["evidences"]
    assert body["graph_nodes"] == []
    assert body["graph_edges"] == []
    top_evidence = body["evidences"][0]
    assert top_evidence["evidence"]["id"] == evidence_id
    assert top_evidence["matched_terms"] == ["vector"]
    assert top_evidence["score_breakdown"] == {
        "lexical": 0.0,
        "bonus": 0.0,
        "phrase": 0.0,
        "vector": 3.0,
    }
    assert _score_breakdown_total_match_rate(body["evidences"]) == 1.0


def test_context_search_deduplicates_repeated_query_terms() -> None:
    client = TestClient(create_app())
    marker = f"dedupterm{time.time_ns()}"
    content = f"""Repeated Query Term Test Paper {marker}

Abstract
This paper repeats {marker} so context search can verify query term deduplication.

Method
The retrieval query should not inflate matched terms when {marker} appears repeatedly.

Conclusion
Repeated query terms should be counted once for deterministic ranking fixtures.
""".encode()

    upload = client.post(
        "/research/papers/upload",
        files={"file": ("context_dedup_query.txt", content, "text/plain")},
    )
    assert upload.status_code == 200
    paper_id = upload.json()["paper"]["id"]

    response = client.post(
        "/research/search/context",
        json={
            "query": f"{marker} {marker} {marker}",
            "paper_ids": [paper_id],
            "limit": 3,
            "include_graph": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["evidences"]
    assert body["graph_nodes"] == []
    assert body["graph_edges"] == []
    top_evidence = body["evidences"][0]
    assert top_evidence["matched_terms"].count(marker) == 1
    assert top_evidence["score_breakdown"]["lexical"] == 1.0
    assert _score_breakdown_total_match_rate(body["evidences"]) == 1.0


def test_context_search_clamps_non_positive_limit() -> None:
    client = TestClient(create_app())
    marker = f"limitclamp{time.time_ns()}"
    content = f"""Context Search Limit Clamp Paper {marker}

Abstract
This paper repeats {marker} in one evidence-bearing section for context search limits.

Method
The method repeats {marker} so a non-positive request limit still returns one bounded result.

Results
The result keeps {marker} available while the response stays within the minimum limit.
""".encode()

    upload = client.post(
        "/research/papers/upload",
        files={"file": ("context_limit_clamp.txt", content, "text/plain")},
    )
    assert upload.status_code == 200
    paper_id = upload.json()["paper"]["id"]

    response = client.post(
        "/research/search/context",
        json={
            "query": marker,
            "paper_ids": [paper_id],
            "limit": 0,
            "include_graph": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["evidences"]) == 1
    assert len(body["gaps"]) <= 1
    assert len(body["ideas"]) <= 1
    assert body["graph_nodes"] == []
    assert body["graph_edges"] == []
    top_evidence = body["evidences"][0]
    assert top_evidence["evidence"]["paper_id"] == paper_id
    assert marker in top_evidence["matched_terms"]
    assert _score_breakdown_total_match_rate(body["evidences"]) == 1.0


def test_context_search_clamps_large_limit() -> None:
    client = TestClient(create_app())
    marker = f"largeclamp{time.time_ns()}"

    session = SessionLocal()
    try:
        paper = Paper(
            title=f"Context Search Large Limit Clamp Paper {marker}",
            filename="context_large_limit_clamp.txt",
            source_type="pytest",
            status="indexed",
        )
        session.add(paper)
        session.flush()
        paper_id = paper.id
        for index in range(30):
            session.add(
                Evidence(
                    paper_id=paper_id,
                    evidence_type="limit_clamp",
                    text=f"{marker} upper clamp evidence row {index}",
                    summary=f"{marker} upper clamp summary {index}",
                    supports=f"{marker} upper clamp support {index}",
                    confidence=1.0,
                    metadata_json={"fixture": "context_search_large_limit_clamp"},
                )
            )
        session.commit()
    finally:
        session.close()

    response = client.post(
        "/research/search/context",
        json={
            "query": marker,
            "paper_ids": [paper_id],
            "limit": 99,
            "include_graph": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["evidences"]) == 25
    assert len(body["gaps"]) <= 25
    assert len(body["ideas"]) <= 25
    assert {item["evidence"]["paper_id"] for item in body["evidences"]} == {paper_id}
    assert all(marker in item["matched_terms"] for item in body["evidences"])
    assert _score_breakdown_total_match_rate(body["evidences"]) == 1.0
    assert body["graph_nodes"] == []
    assert body["graph_edges"] == []


def test_context_search_paper_filter_evaluation_fixture() -> None:
    client = TestClient(create_app())
    marker = f"paperfilter{time.time_ns()}"
    paper_a_marker = f"{marker}alpha"
    paper_b_marker = f"{marker}beta"

    upload_a = client.post(
        "/research/papers/upload",
        files={
            "file": (
                "paper_filter_a.txt",
                f"""Paper Filter A {paper_a_marker}

Abstract
This paper studies {paper_a_marker} metric retrieval isolation.

Method
The method repeats {paper_a_marker} so unfiltered search can find paper A.
""".encode(),
                "text/plain",
            )
        },
    )
    assert upload_a.status_code == 200
    paper_a_id = upload_a.json()["paper"]["id"]

    upload_b = client.post(
        "/research/papers/upload",
        files={
            "file": (
                "paper_filter_b.txt",
                f"""Paper Filter B {paper_b_marker}

Abstract
This paper studies {paper_b_marker} metric retrieval isolation.

Method
The method keeps metric evidence available for filtered search.

Limitations
The current paper still lacks cross-paper isolation checks for metric retrieval.

Future Work
Future work should add scoped gap and idea filters for metric retrieval.
""".encode(),
                "text/plain",
            )
        },
    )
    assert upload_b.status_code == 200
    paper_b_id = upload_b.json()["paper"]["id"]

    gaps_b = client.post("/research/gaps/mine", json={"paper_ids": [paper_b_id], "max_gaps": 1})
    assert gaps_b.status_code == 200
    assert gaps_b.json()["gaps"]
    gap_b_id = gaps_b.json()["gaps"][0]["id"]

    ideas_b = client.post(f"/research/gaps/{gap_b_id}/ideas")
    assert ideas_b.status_code == 200
    assert ideas_b.json()["ideas"]

    unfiltered = client.post(
        "/research/search/context",
        json={
            "query": f"{paper_a_marker} metric",
            "limit": 5,
            "include_graph": False,
        },
    )
    assert unfiltered.status_code == 200
    assert any(
        item["evidence"]["paper_id"] == paper_a_id for item in unfiltered.json()["evidences"]
    )

    filtered = client.post(
        "/research/search/context",
        json={
            "query": f"{paper_a_marker} metric",
            "paper_ids": [paper_b_id],
            "limit": 5,
            "include_graph": False,
        },
    )
    assert filtered.status_code == 200
    filtered_body = filtered.json()
    assert filtered_body["evidences"]
    assert filtered_body["gaps"] or filtered_body["ideas"]
    assert paper_a_id not in {item["evidence"]["paper_id"] for item in filtered_body["evidences"]}
    assert _evidence_paper_filter_leak_rate(filtered_body["evidences"], {paper_b_id}) == 0.0
    assert _gap_paper_filter_leak_rate(filtered_body["gaps"], {paper_b_id}) == 0.0
    assert _idea_paper_filter_leak_rate(filtered_body["ideas"], {paper_b_id}) == 0.0
    assert filtered_body["graph_nodes"] == []
    assert filtered_body["graph_edges"] == []


def test_context_search_graph_context_respects_paper_filter() -> None:
    client = TestClient(create_app())
    marker = f"graphpaperfilter{time.time_ns()}"
    shared_term = f"{marker}metric"
    paper_a_marker = f"{marker}alpha"
    paper_b_marker = f"{marker}beta"

    def upload_fixture(filename: str, title_marker: str) -> str:
        upload = client.post(
            "/research/papers/upload",
            files={
                "file": (
                    filename,
                    f"""Graph Paper Filter {title_marker}

Abstract
This paper studies {shared_term} while carrying private marker {title_marker}.

Method
The method repeats {shared_term} so scoped graph search has evidence to seed.

Conclusion
Graph context for {title_marker} should stay inside its selected paper scope.
""".encode(),
                    "text/plain",
                )
            },
        )
        assert upload.status_code == 200
        return upload.json()["paper"]["id"]

    paper_a_id = upload_fixture("graph_paper_filter_a.txt", paper_a_marker)
    paper_b_id = upload_fixture("graph_paper_filter_b.txt", paper_b_marker)

    evidence_a_response = client.get(f"/research/papers/{paper_a_id}/evidence")
    assert evidence_a_response.status_code == 200
    evidence_a_ids = {evidence["id"] for evidence in evidence_a_response.json()}
    assert evidence_a_ids

    evidence_b_response = client.get(f"/research/papers/{paper_b_id}/evidence")
    assert evidence_b_response.status_code == 200
    evidence_b_ids = {evidence["id"] for evidence in evidence_b_response.json()}
    assert evidence_b_ids

    response = client.post(
        "/research/search/context",
        json={
            "query": shared_term,
            "paper_ids": [paper_b_id],
            "limit": 5,
            "include_graph": True,
            "graph_edge_types": ["paper_has_evidence"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["evidences"]
    assert {item["evidence"]["paper_id"] for item in body["evidences"]} == {paper_b_id}
    assert _evidence_paper_filter_leak_rate(body["evidences"], {paper_b_id}) == 0.0
    assert body["graph_nodes"]
    assert body["graph_edges"]

    graph_node_keys = {node["canonical_key"] for node in body["graph_nodes"]}
    assert paper_b_id in graph_node_keys
    assert graph_node_keys.intersection(evidence_b_ids)
    assert paper_a_id not in graph_node_keys
    assert graph_node_keys.isdisjoint(evidence_a_ids)

    assert {edge["edge_type"] for edge in body["graph_edges"]} == {"paper_has_evidence"}
    assert all(set(edge["evidence_ids"]).isdisjoint(evidence_a_ids) for edge in body["graph_edges"])
    assert any(
        set(edge["evidence_ids"]).intersection(evidence_b_ids) for edge in body["graph_edges"]
    )


def test_context_search_graph_expansion_keeps_relevant_edge_after_recent_noise() -> None:
    client = TestClient(create_app())
    assert client.get("/health").status_code == 200
    marker = f"graphrecall{time.time_ns()}"
    old_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    new_time = datetime(2026, 1, 2, tzinfo=timezone.utc)
    paper_id: str | None = None
    evidence_id: str | None = None
    node_ids: list[str] = []
    edge_ids: list[str] = []

    session = SessionLocal()
    try:
        paper = Paper(
            title=f"Graph Recall Paper {marker}",
            filename="graph_recall_window.txt",
            source_type="pytest",
            status="indexed",
            created_at=old_time,
            updated_at=old_time,
        )
        session.add(paper)
        session.flush()
        paper_id = paper.id
        evidence = Evidence(
            paper_id=paper_id,
            evidence_type="graph_recall",
            text=f"{marker} should keep graph expansion connected to scoped evidence.",
            summary=f"{marker} graph expansion recall fixture.",
            supports="Graph expansion should filter by seed nodes before the recent-edge window.",
            confidence=0.9,
            metadata_json={"fixture": "context_search_graph_recall_window"},
            created_at=old_time,
            updated_at=old_time,
        )
        session.add(evidence)
        session.flush()
        evidence_id = evidence.id

        paper_node = ResearchNode(
            node_type="paper",
            label=paper.title,
            canonical_key=paper_id,
            payload_json={"fixture": "graph_recall_window"},
            created_at=old_time,
            updated_at=old_time,
        )
        evidence_node = ResearchNode(
            node_type="evidence",
            label=f"Graph recall evidence {marker}",
            canonical_key=evidence_id,
            payload_json={"paper_id": paper_id, "fixture": "graph_recall_window"},
            created_at=old_time,
            updated_at=old_time,
        )
        noise_source = ResearchNode(
            node_type="pytest_graph_noise_source",
            label=f"Graph recall noise source {marker}",
            canonical_key=f"{marker}-noise-source",
            payload_json={"fixture": "graph_recall_window"},
            created_at=new_time,
            updated_at=new_time,
        )
        noise_target = ResearchNode(
            node_type="pytest_graph_noise_target",
            label=f"Graph recall noise target {marker}",
            canonical_key=f"{marker}-noise-target",
            payload_json={"fixture": "graph_recall_window"},
            created_at=new_time,
            updated_at=new_time,
        )
        session.add_all([paper_node, evidence_node, noise_source, noise_target])
        session.flush()
        node_ids = [paper_node.id, evidence_node.id, noise_source.id, noise_target.id]

        relevant_edge = ResearchEdge(
            source_node_id=paper_node.id,
            target_node_id=evidence_node.id,
            edge_type="paper_has_evidence",
            evidence_ids_json=[evidence_id],
            payload_json={"fixture": "graph_recall_window"},
            created_at=old_time,
            updated_at=old_time,
        )
        noise_edges = [
            ResearchEdge(
                source_node_id=noise_source.id,
                target_node_id=noise_target.id,
                edge_type="paper_has_evidence",
                evidence_ids_json=[f"{marker}-noise-{index}"],
                payload_json={"fixture": "graph_recall_window", "index": index},
                created_at=new_time,
                updated_at=new_time,
            )
            for index in range(805)
        ]
        session.add(relevant_edge)
        session.add_all(noise_edges)
        session.flush()
        edge_ids = [relevant_edge.id, *[edge.id for edge in noise_edges]]
        session.commit()
    finally:
        session.close()

    try:
        response = client.post(
            "/research/search/context",
            json={
                "query": marker,
                "paper_ids": [paper_id],
                "limit": 1,
                "include_graph": True,
                "graph_edge_types": ["paper_has_evidence"],
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["evidences"][0]["evidence"]["id"] == evidence_id
        assert any(evidence_id in edge["evidence_ids"] for edge in body["graph_edges"])
        assert any(node["canonical_key"] == paper_id for node in body["graph_nodes"])
    finally:
        cleanup = SessionLocal()
        try:
            if edge_ids:
                cleanup.query(ResearchEdge).filter(ResearchEdge.id.in_(edge_ids)).delete(
                    synchronize_session=False
                )
            if node_ids:
                cleanup.query(ResearchNode).filter(ResearchNode.id.in_(node_ids)).delete(
                    synchronize_session=False
                )
            owner_ids = [item_id for item_id in [paper_id, evidence_id] if item_id is not None]
            if owner_ids:
                cleanup.query(ResearchEmbedding).filter(
                    ResearchEmbedding.owner_id.in_(owner_ids)
                ).delete(synchronize_session=False)
            if evidence_id is not None:
                cleanup.query(Evidence).filter(Evidence.id == evidence_id).delete()
            if paper_id is not None:
                cleanup.query(Paper).filter(Paper.id == paper_id).delete()
            cleanup.commit()
        finally:
            cleanup.close()


def test_job_cancel_and_retry_controls() -> None:
    client = TestClient(create_app())
    content = b"""Job Controls Test Paper

Abstract
This paper checks whether queued research workflow jobs can be canceled and retried.

Method
The workflow should preserve the original input when a canceled job is retried.

Conclusion
Durable job controls make long-running research workflows easier to operate.
"""
    upload = client.post(
        "/research/papers/upload",
        files={"file": ("job_controls_test.txt", content, "text/plain")},
    )
    assert upload.status_code == 200
    paper_id = upload.json()["paper"]["id"]

    session = SessionLocal()
    try:
        queued_job = WorkflowService(session).queue_literature_to_ideas(
            paper_id=paper_id,
            max_gaps=1,
            max_ideas_per_gap=1,
            include_markdown_export=False,
        )
        queued_job_id = queued_job.id
    finally:
        session.close()

    canceled = client.post(f"/research/jobs/{queued_job_id}/cancel")
    assert canceled.status_code == 200
    canceled_body = canceled.json()
    assert canceled_body["status"] == "canceled"
    assert canceled_body["error"] == "Job canceled by user"

    retried = client.post(f"/research/jobs/{queued_job_id}/retry")
    assert retried.status_code == 200
    retried_body = retried.json()
    assert retried_body["id"] != queued_job_id
    assert retried_body["job_type"] == "literature_to_ideas_workflow"
    assert retried_body["input"]["paper_id"] == paper_id
    assert retried_body["status"] in {"pending", "running", "completed", "failed"}

    job = client.get(f"/research/jobs/{retried_body['id']}")
    assert job.status_code == 200
    job_body = job.json()
    assert job_body["status"] in {"pending", "running", "completed", "failed"}
    assert job_body["input"]["paper_id"] == paper_id


def test_context_search_returns_evidence_and_graph_context() -> None:
    client = TestClient(create_app())
    content = b"""Context Search Test Paper

Abstract
This paper studies diagnostic metrics for evidence-grounded research assistants.

Introduction
Research assistants need context retrieval that connects diagnostic metric evidence to research gaps.

Method
The system should retrieve evidence, gaps, ideas, and graph neighbors for a user query.

Limitations
The current retrieval is lexical and should later add embedding reranking.

Conclusion
Future work should make GraphRAG context retrieval stronger.
"""
    upload = client.post(
        "/research/papers/upload",
        files={"file": ("context_search_test.txt", content, "text/plain")},
    )
    assert upload.status_code == 200
    paper_id = upload.json()["paper"]["id"]

    workflow = client.post(
        "/research/workflows/literature-to-ideas",
        json={
            "paper_id": paper_id,
            "max_gaps": 2,
            "max_ideas_per_gap": 1,
            "include_markdown_export": False,
        },
    )
    assert workflow.status_code == 200

    embeddings = client.post(
        "/research/embeddings/rebuild",
        json={
            "paper_ids": [paper_id],
            "owner_types": ["evidence", "gap", "idea"],
            "limit": 50,
        },
    )
    assert embeddings.status_code == 200
    embedding_body = embeddings.json()
    evidence_response = client.get(f"/research/papers/{paper_id}/evidence")
    assert evidence_response.status_code == 200
    expected_evidence_ids = {
        evidence["id"]
        for evidence in evidence_response.json()
        if {"diagnostic", "metric", "retrieval"}.intersection(set(evidence["text"].lower().split()))
    }
    assert expected_evidence_ids
    assert embedding_body["model"] == "local_hash_embedding_v0"
    assert embedding_body["dimension"] == 128
    assert embedding_body["evidence_count"] >= 1
    assert embedding_body["gap_count"] >= 1
    assert embedding_body["idea_count"] >= 1

    response = client.post(
        "/research/search/context",
        json={
            "query": "diagnostic metric graph retrieval",
            "paper_ids": [paper_id],
            "limit": 5,
            "include_graph": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["retrieval_method"] == "lexical_vector_graph_rag_lite_v0"
    assert body["evidences"]
    assert body["gaps"] or body["ideas"]
    vector_evidence = next(item for item in body["evidences"] if "vector" in item["matched_terms"])
    assert set(vector_evidence["score_breakdown"]) == {
        "lexical",
        "bonus",
        "phrase",
        "vector",
    }
    assert vector_evidence["score_breakdown"]["vector"] > 0
    assert body["graph_nodes"]
    assert body["graph_edges"]
    assert "Matched" in body["answer_brief"]

    evidence_result_ids = [item["evidence"]["id"] for item in body["evidences"]]
    evidence_metrics = {
        "hit_at_1": _hit_at_k(evidence_result_ids, expected_evidence_ids, 1),
        "hit_at_3": _hit_at_k(evidence_result_ids, expected_evidence_ids, 3),
        "hit_at_5": _hit_at_k(evidence_result_ids, expected_evidence_ids, 5),
        "mrr": _mean_reciprocal_rank(evidence_result_ids, expected_evidence_ids),
    }
    assert evidence_metrics == {
        "hit_at_1": 1.0,
        "hit_at_3": 1.0,
        "hit_at_5": 1.0,
        "mrr": 1.0,
    }
    context_items = [*body["evidences"], *body["gaps"], *body["ideas"]]
    assert _score_breakdown_coverage(context_items) == 1.0
    assert _score_breakdown_total_match_rate(context_items) == 1.0
    assert _graph_edge_hit_rate(body["graph_edges"], {"paper_has_evidence"}) == 1.0

    filtered_response = client.post(
        "/research/search/context",
        json={
            "query": "diagnostic metric graph retrieval",
            "paper_ids": [paper_id],
            "limit": 5,
            "include_graph": True,
            "graph_edge_types": ["paper_has_evidence"],
        },
    )
    assert filtered_response.status_code == 200
    filtered_body = filtered_response.json()
    assert filtered_body["evidences"]
    assert filtered_body["graph_edges"]
    assert {edge["edge_type"] for edge in filtered_body["graph_edges"]} == {"paper_has_evidence"}
    assert _graph_noise_rate(filtered_body["graph_edges"], {"paper_has_evidence"}) == 0.0

    workflow_edge_types = {"paper_has_evidence", "gap_supported_by_evidence"}
    multi_filter_response = client.post(
        "/research/search/context",
        json={
            "query": "diagnostic metric graph retrieval",
            "paper_ids": [paper_id],
            "limit": 5,
            "include_graph": True,
            "graph_edge_types": sorted(workflow_edge_types),
        },
    )
    assert multi_filter_response.status_code == 200
    multi_filter_body = multi_filter_response.json()
    multi_filter_edge_types = {edge["edge_type"] for edge in multi_filter_body["graph_edges"]}
    assert workflow_edge_types.issubset(multi_filter_edge_types)
    assert multi_filter_edge_types.issubset(workflow_edge_types)
    assert _graph_noise_rate(multi_filter_body["graph_edges"], workflow_edge_types) == 0.0

    normalized_filter_response = client.post(
        "/research/search/context",
        json={
            "query": "diagnostic metric graph retrieval",
            "paper_ids": [paper_id],
            "limit": 5,
            "include_graph": True,
            "graph_edge_types": ["", " paper_has_evidence ", "\tpaper_has_evidence\t"],
        },
    )
    assert normalized_filter_response.status_code == 200
    normalized_filter_body = normalized_filter_response.json()
    assert normalized_filter_body["evidences"]
    assert normalized_filter_body["graph_edges"]
    assert {edge["edge_type"] for edge in normalized_filter_body["graph_edges"]} == {
        "paper_has_evidence"
    }
    assert _graph_noise_rate(normalized_filter_body["graph_edges"], {"paper_has_evidence"}) == 0.0

    unknown_filter_response = client.post(
        "/research/search/context",
        json={
            "query": "diagnostic metric graph retrieval",
            "paper_ids": [paper_id],
            "limit": 5,
            "include_graph": True,
            "graph_edge_types": ["pytest_unknown_context_edge"],
        },
    )
    assert unknown_filter_response.status_code == 200
    unknown_filter_body = unknown_filter_response.json()
    assert unknown_filter_body["evidences"]
    assert unknown_filter_body["graph_edges"] == []
    assert (
        _graph_noise_rate(unknown_filter_body["graph_edges"], {"pytest_unknown_context_edge"})
        == 0.0
    )


def test_graph_rag_lite_records_workflow_links() -> None:
    client = TestClient(create_app())
    content = b"""Graph Link Test Paper

Introduction
The assistant needs graph links between papers, evidence, gaps, and ideas.

Limitations
Without graph links, later retrieval cannot expand from an idea back to its evidence.

Conclusion
Future work should expose graph nodes and edges through the API.
"""
    upload = client.post(
        "/research/papers/upload",
        files={"file": ("graph_link_test.txt", content, "text/plain")},
    )
    assert upload.status_code == 200
    paper_id = upload.json()["paper"]["id"]
    gaps = client.post("/research/gaps/mine", json={"paper_ids": [paper_id], "max_gaps": 2})
    gap_id = gaps.json()["gaps"][0]["id"]
    ideas = client.post(f"/research/gaps/{gap_id}/ideas")
    assert ideas.status_code == 200

    nodes = client.get("/research/graph/nodes")
    assert nodes.status_code == 200
    node_types = {node["node_type"] for node in nodes.json()}
    assert {"paper", "evidence", "gap", "idea"}.issubset(node_types)

    edges = client.get("/research/graph/edges")
    assert edges.status_code == 200
    edge_types = {edge["edge_type"] for edge in edges.json()}
    assert "paper_has_evidence" in edge_types
    assert "gap_supported_by_evidence" in edge_types
    assert "idea_addresses_gap" in edge_types

    stats = client.get("/research/graph/stats")
    assert stats.status_code == 200
    stats_body = stats.json()
    assert stats_body["node_count"] >= len(nodes.json())
    assert stats_body["edge_count"] >= len(edges.json())
    assert stats_body["node_type_counts"]["paper"] >= 1
    assert stats_body["node_type_counts"]["evidence"] >= 1
    assert stats_body["edge_type_counts"]["paper_has_evidence"] >= 1
    assert stats_body["orphan_edge_count"] == 0
    assert stats_body["duplicate_edge_group_count"] >= 0


def test_structured_extraction_prompt_limits_evidence_payload() -> None:
    service = StructuredExtractionService.__new__(StructuredExtractionService)
    paper = Paper(id="paper-prompt", title="Prompt Safety Paper")
    evidences = [
        Evidence(
            id=f"evidence-{index}",
            evidence_type="method",
            supports=f"claim-{index}",
            text=f"Evidence {index} " + ("A" * 1300),
        )
        for index in range(30)
    ]

    prompt = service._build_prompt(paper, evidences)
    evidence_json = prompt.split("Evidence JSON:\n", 1)[1].split(
        "\n\nReturn JSON matching this shape:",
        1,
    )[0]
    evidence_payload = json.loads(evidence_json)
    schema_json = prompt.split("Return JSON matching this shape:\n", 1)[1]
    schema_hint = json.loads(schema_json)

    assert prompt.startswith("Paper title: Prompt Safety Paper")
    assert len(evidence_payload) == 24
    assert evidence_payload[0] == {
        "evidence_id": "evidence-0",
        "type": "method",
        "supports": "claim-0",
        "text": "Evidence 0 " + ("A" * 1189),
    }
    assert evidence_payload[-1]["evidence_id"] == "evidence-23"
    assert "evidence-24" not in {item["evidence_id"] for item in evidence_payload}
    assert len(evidence_payload[0]["text"]) == 1200
    assert schema_hint["problem"][0]["evidence_ids"] == ["..."]
    assert schema_hint["keywords"] == []


def test_structured_card_extraction_falls_back_without_model_config() -> None:
    client = TestClient(create_app())
    content = b"""Structured Extraction Fallback Test

Abstract
This paper validates the structured extraction endpoint.

Method
The endpoint should call a model when configured and otherwise fall back safely.

Conclusion
Future work should add stronger prompt evaluation.
"""
    upload = client.post(
        "/research/papers/upload",
        files={"file": ("structured_fallback_test.txt", content, "text/plain")},
    )
    assert upload.status_code == 200
    paper_id = upload.json()["paper"]["id"]

    response = client.post(f"/research/papers/{paper_id}/card/extract-structured")
    assert response.status_code == 200
    card = response.json()
    assert card["extraction_status"] == "completed"
    assert "heuristic" in card["extraction_model"]
    assert card["payload"]["method"]
