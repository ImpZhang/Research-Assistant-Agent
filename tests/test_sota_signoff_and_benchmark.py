from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.research.db import SessionLocal
from backend.research.models import Evidence, ExperimentPlan, Idea, Paper, ResearchGap


def test_benchmark_run_packet_can_anchor_sota_signoff() -> None:
    marker = f"sota-signoff-{uuid4().hex}"
    paper_id = f"{marker}-paper"
    evidence_id = f"{marker}-evidence"
    gap_id = f"{marker}-gap"
    idea_id = f"{marker}-idea"
    plan_id = f"{marker}-plan"

    with SessionLocal() as session:
        session.add(
            Paper(
                id=paper_id,
                title="Geo-localization Benchmark Signoff Seed",
                status="processed",
            )
        )
        session.add(
            Evidence(
                id=evidence_id,
                paper_id=paper_id,
                evidence_type="result",
                summary="A geolocalization benchmark needs nearest-work comparison.",
                text=(
                    "Worldwide image geolocalization benchmark records country accuracy, "
                    f"geodesic error, and nearest-work comparison for marker {marker}."
                ),
                confidence=0.88,
            )
        )
        session.add(
            ResearchGap(
                id=gap_id,
                title="Nearest-work SOTA signoff for geolocalization",
                description="Generated ideas need explicit nearest-work and benchmark closure.",
                gap_type="validation_gap",
                source_paper_ids_json=[paper_id],
                evidence_ids_json=[evidence_id],
                why_important="SOTA claims need traceable external and benchmark evidence.",
                why_unsolved="Demo flows often stop at novelty prompts.",
                possible_approaches_json=["manual signoff", "benchmark packet"],
                feasibility_score=0.76,
                risk_level="medium",
            )
        )
        session.add(
            Idea(
                id=idea_id,
                title="Region-Calibrated Geo-localization Reranking",
                research_question="Can calibrated regional reranking improve country accuracy?",
                core_hypothesis="Region calibration improves image geolocalization reranking.",
                motivation="Aggregate country accuracy misses rare-region failures.",
                related_gap_ids_json=[gap_id],
                related_paper_ids_json=[paper_id],
                evidence_ids_json=[evidence_id],
                method_sketch="Calibrate reranker scores by region and uncertainty.",
                expected_contribution="A reproducible reranking intervention for geolocalization.",
                novelty_argument="Combines regional calibration with nearest-work signoff.",
                datasets_json=["GWS15k"],
                baselines_json=["GeoToken nearest baseline"],
                metrics_json=["country_accuracy"],
                risks_json=["nearest work may already calibrate by region"],
            )
        )
        session.add(
            ExperimentPlan(
                id=plan_id,
                idea_id=idea_id,
                objective="Validate region-calibrated reranking against nearest work.",
                hypothesis="Country accuracy improves over the nearest baseline.",
                datasets_json=["GWS15k"],
                baselines_json=["GeoToken nearest baseline"],
                metrics_json=["country_accuracy"],
            )
        )
        session.commit()

    client = TestClient(create_app())
    benchmark = client.post(
        f"/research/experiment-plans/{plan_id}/benchmark-run",
        json={
            "title": "GWS15k nearest-work benchmark",
            "benchmark_name": "GWS15k country accuracy",
            "dataset": "GWS15k",
            "split": "validation",
            "baseline_name": "GeoToken nearest baseline",
            "primary_metric": "country_accuracy",
            "metric_direction": "higher_is_better",
            "candidate_result": 0.721,
            "baseline_result": 0.684,
            "command": "python eval.py --dataset GWS15k --split validation",
            "artifact_links": [{"label": "results", "path": "outputs/eval/gws15k.json"}],
            "dry_run": False,
            "reproducibility_notes": "Seed 7, validation split.",
            "created_by": "pytest",
        },
    )

    assert benchmark.status_code == 200
    run = benchmark.json()
    assert run["status"] == "completed"
    assert run["parameters"]["execution_kind"] == "benchmark"
    assert run["parameters"]["dry_run"] is False
    assert run["metric_results"]["country_accuracy"]["improved"] is True
    assert "improved on country_accuracy" in run["conclusion"]

    package = client.post(
        f"/research/ideas/{idea_id}/sota-review-package",
        json={"include_external": False, "limit": 5, "created_by": "pytest"},
    )

    assert package.status_code == 200

    signoff = client.post(
        f"/research/ideas/{idea_id}/sota-signoffs",
        json={
            "review_package_id": package.json()["id"],
            "decision": "confirmed_novel",
            "reviewer": "pytest reviewer",
            "external_searches_completed": True,
            "nearest_work": [
                {
                    "title": "GeoToken",
                    "year": 2025,
                    "relationship": "nearest hierarchical geolocalization baseline",
                }
            ],
            "evidence_links": [{"label": "benchmark", "id": run["id"]}],
            "benchmark_run_ids": [run["id"]],
            "final_novelty_claim": (
                "Region-calibrated reranking is novel relative to the nearest recorded "
                "hierarchical geolocalization baseline in this local review packet."
            ),
            "limitations": ["Requires live external literature review before publication."],
            "created_by": "pytest",
        },
    )

    assert signoff.status_code == 200
    body = signoff.json()
    assert body["scope"] == "sota_signoff_record"
    assert body["summary"]["signoff_status"] == "sota_confirmed"
    assert body["summary"]["manual_gate_summary"]["ready_for_sota_claim"] is True
    assert body["summary"]["benchmark_run_ids"] == [run["id"]]
    assert "# SOTA Signoff Record" in body["markdown_export"]

    listed = client.get(f"/research/ideas/{idea_id}/sota-signoffs")
    detail = client.get(f"/research/ideas/{idea_id}/sota-signoffs/{body['id']}")
    markdown = client.get(f"/research/ideas/{idea_id}/sota-signoffs/{body['id']}/export/markdown")

    assert listed.status_code == 200
    assert listed.json()[0]["id"] == body["id"]
    assert detail.status_code == 200
    assert detail.json()["summary"]["decision"] == "confirmed_novel"
    assert markdown.status_code == 200
    assert "Ready For SOTA Claim: `True`" in markdown.text
