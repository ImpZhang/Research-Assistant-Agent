import json
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.research.db import SessionLocal
from backend.research.models import (
    Evidence,
    ExperimentPlan,
    Idea,
    Paper,
    ResearchBrief,
    ResearchGap,
)
from backend.research.schemas import LiteratureSearchItem, LiteratureSearchResponse
from backend.research.services.literature_search_service import LiteratureSearchService


def test_benchmark_command_runner_executes_local_command(monkeypatch) -> None:
    marker = f"benchmark-exec-{uuid4().hex}"
    idea_id = f"{marker}-idea"
    plan_id = f"{marker}-plan"
    output_dir = f"outputs/benchmark-runs/{marker}"
    monkeypatch.setenv("BENCHMARK_RUNNER_ENABLED", "true")
    monkeypatch.setenv("BENCHMARK_RUNNER_OUTPUT_DIR", output_dir)
    monkeypatch.setenv("BENCHMARK_RUNNER_ALLOWED_COMMANDS", sys.executable)
    monkeypatch.setenv("BENCHMARK_RUNNER_TIMEOUT_SECONDS", "30")

    with SessionLocal() as session:
        session.add(
            Idea(
                id=idea_id,
                title="Executable Geo-localization Benchmark",
                research_question="Can a local benchmark runner capture metric evidence?",
                core_hypothesis="Executed benchmark metrics improve evidence traceability.",
                method_sketch="Run a small command that emits benchmark JSON.",
                novelty_argument="Requires measured benchmark artifacts.",
                datasets_json=["local-smoke"],
                metrics_json=["country_accuracy"],
            )
        )
        session.add(
            ExperimentPlan(
                id=plan_id,
                idea_id=idea_id,
                objective="Execute a local benchmark command.",
                hypothesis="The runner captures metrics and artifacts.",
                datasets_json=["local-smoke"],
                baselines_json=["baseline"],
                metrics_json=["country_accuracy"],
            )
        )
        session.commit()

    client = TestClient(create_app())
    response = client.post(
        f"/research/experiment-plans/{plan_id}/benchmark-run/execute",
        json={
            "title": "Executable benchmark smoke",
            "benchmark_name": "Local command benchmark",
            "dataset": "local-smoke",
            "split": "validation",
            "baseline_name": "baseline",
            "primary_metric": "country_accuracy",
            "metric_direction": "higher_is_better",
            "candidate_result": 0.74,
            "baseline_result": 0.7,
            "command_args": [
                sys.executable,
                "-c",
                ("import json; print(json.dumps({'metrics': {'latency_ms': {'value': 12.5}}}))"),
            ],
            "working_directory": ".",
            "parse_stdout_json": True,
            "timeout_seconds": 30,
            "created_by": "pytest",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["parameters"]["execution_kind"] == "benchmark_command"
    assert body["parameters"]["runner"]["exit_code"] == 0
    assert body["parameters"]["runner"]["timed_out"] is False
    assert body["metric_results"]["latency_ms"]["value"] == 12.5
    assert body["metric_results"]["country_accuracy"]["improved"] is True
    assert any(item["label"] == "benchmark_stdout" for item in body["artifact_links"])
    assert any(item["label"] == "benchmark_metrics" for item in body["artifact_links"])
    assert body["parameters"]["runner_output_dir"].startswith(output_dir)


def test_benchmark_command_runner_executes_builtin_profile(monkeypatch) -> None:
    marker = f"benchmark-profile-{uuid4().hex}"
    idea_id = f"{marker}-idea"
    plan_id = f"{marker}-plan"
    output_dir = f"outputs/benchmark-runs/{marker}"
    monkeypatch.setenv("BENCHMARK_RUNNER_ENABLED", "true")
    monkeypatch.setenv("BENCHMARK_RUNNER_OUTPUT_DIR", output_dir)
    monkeypatch.setenv("BENCHMARK_RUNNER_ALLOWED_COMMANDS", "python3")

    with SessionLocal() as session:
        session.add(
            Idea(
                id=idea_id,
                title="Profile-backed Benchmark Idea",
                research_question="Can benchmark profiles execute reproducible metric commands?",
                core_hypothesis="Profile defaults reduce ad hoc benchmark execution.",
            )
        )
        session.add(
            ExperimentPlan(
                id=plan_id,
                idea_id=idea_id,
                objective="Execute the built-in JSON metrics smoke profile.",
                hypothesis="The runner resolves profile defaults and captures metrics.",
            )
        )
        session.commit()

    client = TestClient(create_app())
    response = client.post(
        f"/research/experiment-plans/{plan_id}/benchmark-run/execute",
        json={
            "profile_id": "json-metrics-smoke",
            "created_by": "pytest",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["parameters"]["benchmark_profile"]["id"] == "json-metrics-smoke"
    assert body["parameters"]["config"]["benchmark_profile_id"] == "json-metrics-smoke"
    assert body["parameters"]["benchmark_name"] == "Workbench benchmark smoke"
    assert body["metric_results"]["primary_metric"]["value"] == 0.0
    assert body["parameters"]["runner_output_dir"].startswith(output_dir)


def test_geoloc_prediction_benchmark_harness_outputs_metrics(tmp_path) -> None:
    ground_truth = tmp_path / "ground_truth.jsonl"
    predictions = tmp_path / "predictions.jsonl"
    ground_truth.write_text(
        "\n".join(
            [
                json.dumps({"id": "a", "country": "US", "lat": 40.0, "lon": -74.0}),
                json.dumps({"id": "b", "country": "FR", "lat": 48.8566, "lon": 2.3522}),
            ]
        ),
        encoding="utf-8",
    )
    predictions.write_text(
        "\n".join(
            [
                json.dumps({"id": "a", "country": "US", "lat": 40.0, "lon": -74.0}),
                json.dumps({"id": "b", "country": "DE", "lat": 52.52, "lon": 13.405}),
            ]
        ),
        encoding="utf-8",
    )

    script = Path("scripts/benchmark_geoloc_predictions.py")
    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--ground-truth",
            str(ground_truth),
            "--predictions",
            str(predictions),
            "--baseline-country-accuracy",
            "0.4",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["metrics"]["country_accuracy"]["value"] == 0.5
    assert payload["metrics"]["country_accuracy"]["baseline"] == 0.4
    assert payload["metrics"]["country_accuracy"]["improved"] is True
    assert payload["metrics"]["mean_geodesic_km"]["direction"] == "lower_is_better"
    assert payload["summary"]["matched_predictions"] == 2


def test_benchmark_command_runner_is_disabled_by_default(monkeypatch) -> None:
    marker = f"benchmark-disabled-{uuid4().hex}"
    idea_id = f"{marker}-idea"
    plan_id = f"{marker}-plan"
    monkeypatch.setenv("BENCHMARK_RUNNER_ENABLED", "false")

    with SessionLocal() as session:
        session.add(
            Idea(
                id=idea_id,
                title="Disabled Benchmark Runner Idea",
                research_question="Should disabled runner reject execution?",
                core_hypothesis="Disabled runner prevents accidental execution.",
            )
        )
        session.add(
            ExperimentPlan(
                id=plan_id,
                idea_id=idea_id,
                objective="Attempt execution while disabled.",
                hypothesis="The route returns a policy error.",
            )
        )
        session.commit()

    client = TestClient(create_app())
    response = client.post(
        f"/research/experiment-plans/{plan_id}/benchmark-run/execute",
        json={
            "benchmark_name": "Disabled command benchmark",
            "command_args": [sys.executable, "-c", "print('{}')"],
            "created_by": "pytest",
        },
    )

    assert response.status_code == 403
    assert "disabled" in response.json()["detail"].lower()


def test_benchmark_run_comparison_persists_brief() -> None:
    marker = f"benchmark-compare-{uuid4().hex}"
    idea_id = f"{marker}-idea"
    plan_id = f"{marker}-plan"

    with SessionLocal() as session:
        session.add(
            Idea(
                id=idea_id,
                title="Benchmark Comparison Idea",
                research_question="Can repeated benchmark runs be compared?",
                core_hypothesis="Metric deltas should become auditable comparison evidence.",
            )
        )
        session.add(
            ExperimentPlan(
                id=plan_id,
                idea_id=idea_id,
                objective="Compare baseline and candidate benchmark runs.",
                hypothesis="Candidate country accuracy improves over baseline run.",
            )
        )
        session.commit()

    client = TestClient(create_app())
    baseline = client.post(
        f"/research/experiment-plans/{plan_id}/benchmark-run",
        json={
            "title": "Baseline benchmark run",
            "benchmark_name": "Country accuracy",
            "dataset": "local-geoloc",
            "split": "validation",
            "primary_metric": "country_accuracy",
            "metric_direction": "higher_is_better",
            "candidate_result": 0.68,
            "baseline_result": 0.65,
            "dry_run": False,
            "created_by": "pytest",
        },
    )
    candidate = client.post(
        f"/research/experiment-plans/{plan_id}/benchmark-run",
        json={
            "title": "Candidate benchmark run",
            "benchmark_name": "Country accuracy",
            "dataset": "local-geoloc",
            "split": "validation",
            "primary_metric": "country_accuracy",
            "metric_direction": "higher_is_better",
            "candidate_result": 0.72,
            "baseline_result": 0.68,
            "dry_run": False,
            "created_by": "pytest",
        },
    )

    assert baseline.status_code == 200
    assert candidate.status_code == 200

    comparison = client.post(
        "/research/experiment-runs/compare",
        json={
            "baseline_run_id": baseline.json()["id"],
            "candidate_run_id": candidate.json()["id"],
            "primary_metric": "country_accuracy",
            "created_by": "pytest",
        },
    )

    assert comparison.status_code == 200
    body = comparison.json()
    assert body["status"] == "improved"
    assert body["primary_metric"] == "country_accuracy"
    assert body["metric_deltas"][0]["baseline_value"] == 0.68
    assert body["metric_deltas"][0]["candidate_value"] == 0.72
    assert body["metric_deltas"][0]["delta"] == 0.04
    assert body["metric_deltas"][0]["improved"] is True
    assert "Benchmark Comparison" in body["markdown_export"]

    with SessionLocal() as session:
        brief = session.get(ResearchBrief, body["brief_id"])
        assert brief is not None
        assert brief.scope == "benchmark_run_comparison"
        assert brief.summary_json["comparison_status"] == "improved"


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


def test_sota_external_search_evidence_records_provider_completion(monkeypatch) -> None:
    marker = f"sota-search-{uuid4().hex}"
    idea_id = f"{marker}-idea"

    with SessionLocal() as session:
        session.add(
            Idea(
                id=idea_id,
                title="Geo-localization External SOTA Evidence",
                research_question="Can external search close the nearest-work review?",
                core_hypothesis="External search evidence improves SOTA signoff confidence.",
                method_sketch="Compare generated idea against current external literature.",
                novelty_argument="Requires live nearest-work review.",
                datasets_json=["GWS15k"],
                metrics_json=["country_accuracy"],
            )
        )
        session.commit()

    def fake_search(
        self: LiteratureSearchService,
        query: str,
        limit: int = 8,
        include_external: bool = False,
    ) -> LiteratureSearchResponse:
        return LiteratureSearchResponse(
            query=query,
            local_status="completed",
            external_status="completed",
            items=[
                LiteratureSearchItem(
                    provider="semantic_scholar",
                    source_id="paper-1",
                    title="Current Geo-localization Nearest Work",
                    authors=["A. Reviewer"],
                    year=2026,
                    venue="SOTA Conf",
                    url="https://example.test/paper",
                    abstract="Nearest external work for geolocalization SOTA review.",
                    score=0.93,
                )
            ],
            message="Returned mocked external search results.",
        )

    monkeypatch.setattr(LiteratureSearchService, "search", fake_search)

    client = TestClient(create_app())
    response = client.post(
        f"/research/ideas/{idea_id}/sota-external-search-evidence",
        json={
            "queries": ["geo-localization external nearest work"],
            "include_external": True,
            "limit": 5,
            "created_by": "pytest",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["scope"] == "sota_external_search_evidence"
    assert body["summary"]["search_status"] == "external_completed"
    assert body["summary"]["ready_for_signoff"] is True
    assert body["summary"]["external_result_count"] == 1
    assert body["summary"]["missing_searches"] == []
    assert "# SOTA External Search Evidence" in body["markdown_export"]

    listed = client.get(f"/research/ideas/{idea_id}/sota-external-search-evidence")
    detail = client.get(f"/research/ideas/{idea_id}/sota-external-search-evidence/{body['id']}")
    markdown = client.get(
        f"/research/ideas/{idea_id}/sota-external-search-evidence/{body['id']}/export/markdown"
    )

    assert listed.status_code == 200
    assert listed.json()[0]["id"] == body["id"]
    assert detail.status_code == 200
    assert detail.json()["summary"]["searches"][0]["external_status"] == "completed"
    assert markdown.status_code == 200
    assert "Ready For Signoff: `True`" in markdown.text

    signoff = client.post(
        f"/research/ideas/{idea_id}/sota-signoffs",
        json={
            "external_search_evidence_id": body["id"],
            "decision": "confirmed_novel",
            "reviewer": "pytest reviewer",
            "external_searches_completed": False,
            "nearest_work": [
                {
                    "title": "Current Geo-localization Nearest Work",
                    "year": 2026,
                    "relationship": "external nearest-work baseline",
                }
            ],
            "final_novelty_claim": (
                "External search evidence supports the local nearest-work novelty review."
            ),
            "created_by": "pytest",
        },
    )

    assert signoff.status_code == 200
    signoff_body = signoff.json()
    assert signoff_body["summary"]["external_search_evidence_id"] == body["id"]
    assert signoff_body["summary"]["external_searches_completed"] is False
    assert signoff_body["summary"]["effective_external_search_completed"] is True
    assert signoff_body["summary"]["external_search_status"] == "external_completed"
    assert signoff_body["summary"]["signoff_status"] == "sota_confirmed"
