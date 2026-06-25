from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.research.db import SessionLocal
from backend.research.models import Evidence, Idea, Paper, ResearchGap


def test_sota_review_package_creates_manual_review_brief() -> None:
    marker = f"sota-{uuid4().hex}"
    paper_id = f"{marker}-paper"
    evidence_id = f"{marker}-evidence"
    gap_id = f"{marker}-gap"
    idea_id = f"{marker}-idea"

    with SessionLocal() as session:
        paper = Paper(
            id=paper_id,
            title="Region Balance Geo-localization SOTA Seed",
            status="processed",
        )
        evidence = Evidence(
            id=evidence_id,
            paper_id=paper_id,
            evidence_type="claim",
            summary="Region-balanced hard negative mining improves geo-localization retrieval.",
            text=(
                "Region-balanced hard negative mining improves worldwide image "
                f"geo-localization retrieval for marker {marker}."
            ),
            confidence=0.9,
        )
        gap = ResearchGap(
            id=gap_id,
            title="Region-balanced hard negatives for geo-localization",
            description=(
                "Existing geo-localization systems under-test rare regions and hard negatives."
            ),
            gap_type="evaluation_gap",
            source_paper_ids_json=[paper_id],
            evidence_ids_json=[evidence_id],
            why_important="Worldwide benchmarks need region-balanced failure coverage.",
            why_unsolved="Nearest baselines often optimize aggregate accuracy.",
            possible_approaches_json=["hard negative mining", "regional stratification"],
            feasibility_score=0.7,
            risk_level="medium",
        )
        idea = Idea(
            id=idea_id,
            title="Region-Balanced Hard Negative Mining for Geo-localization",
            research_question="Can region-balanced hard negatives reduce worldwide geodesic error?",
            core_hypothesis=(
                "Balancing hard negatives by region improves image geo-localization robustness."
            ),
            motivation="Aggregate metrics hide rare-region failures.",
            related_gap_ids_json=[gap_id],
            related_paper_ids_json=[paper_id],
            evidence_ids_json=[evidence_id],
            method_sketch="Mine region-balanced hard negatives before retrieval reranking.",
            expected_contribution="A targeted robustness intervention for worldwide geolocation.",
            novelty_argument="Focuses the negative mining policy on geographic imbalance.",
            datasets_json=["GeoGuessr", "GWS15k"],
            baselines_json=["retrieval geolocalization", "vision-language geolocation"],
            metrics_json=["geodesic error", "country accuracy"],
            risks_json=["nearest work may already cover regional hard negatives"],
        )
        nearby = Idea(
            id=f"{marker}-nearby",
            title="Regional Hard Negative Mining for Geo-localization Retrieval",
            research_question="Does regional negative sampling improve geolocation retrieval?",
            core_hypothesis="Regional negatives improve retrieval robustness.",
            related_paper_ids_json=[paper_id],
            evidence_ids_json=[evidence_id],
            method_sketch="Use regional negative sampling.",
            datasets_json=["GeoGuessr"],
            metrics_json=["geodesic error"],
        )
        session.add_all([paper, evidence, gap, idea, nearby])
        session.commit()

    client = TestClient(create_app())
    response = client.post(
        f"/research/ideas/{idea_id}/sota-review-package",
        json={"include_external": False, "limit": 5, "created_by": "pytest"},
    )

    assert response.status_code == 200
    body = response.json()
    summary = body["summary"]
    assert body["scope"] == "sota_review_package"
    assert body["idea_ids"] == [idea_id]
    assert summary["review_status"] == "manual_sota_review_required"
    assert summary["novelty_check_id"]
    assert summary["related_work_matrix_id"]
    assert "external_literature_search_not_requested" in summary["missing_searches"]
    assert "Run external literature search before claiming novelty." in body["markdown_export"]

    listed = client.get(f"/research/ideas/{idea_id}/sota-review-packages")
    detail = client.get(f"/research/ideas/{idea_id}/sota-review-packages/{body['id']}")
    markdown = client.get(
        f"/research/ideas/{idea_id}/sota-review-packages/{body['id']}/export/markdown"
    )

    assert listed.status_code == 200
    assert listed.json()[0]["id"] == body["id"]
    assert detail.status_code == 200
    assert detail.json()["summary"]["review_queries"]
    assert markdown.status_code == 200
    assert "# SOTA Review Package" in markdown.text
