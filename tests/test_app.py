import time

from fastapi.testclient import TestClient

from backend.app import create_app


def test_health() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_research_status() -> None:
    client = TestClient(create_app())
    response = client.get("/research/status")
    assert response.status_code == 200
    body = response.json()
    assert body["phase"] == "phase_0_foundation"
    assert "sqlalchemy_models" in body["implemented_capabilities"]


def test_workbench_static_assets_are_served() -> None:
    client = TestClient(create_app())
    response = client.get("/workbench")
    assert response.status_code == 200
    assert "Research Assistant Workbench" in response.text
    assert "/workbench-assets/app.js" in response.text

    script = client.get("/workbench-assets/app.js")
    assert script.status_code == 200
    assert "/research/workflows/literature-to-ideas/async" in script.text
    assert "/research/jobs/${jobId}/artifacts" in script.text
    assert "/research/ideas/${state.latestIdeaId}/refine" in script.text
    assert "/research/ideas/${state.latestIdeaId}/feedback" in script.text
    assert "/research/ideas/${state.latestIdeaId}/related-work-matrix" in script.text
    assert "/research/ideas/${state.latestIdeaId}/proposal-draft" in script.text
    assert "/proposal-drafts/${state.latestProposalDraftId}/review" in script.text
    assert "/proposal-drafts/${state.latestProposalDraftId}/revise" in script.text
    assert "/revisions/${state.latestProposalRevisionId}/tasks" in script.text
    assert "/research/ideas/rank" in script.text
    assert "/research/ideas/rank/export/markdown" in script.text
    assert "/research/ideas/portfolios" in script.text


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


def test_proposal_draft_bundles_idea_related_work_and_experiment_plan() -> None:
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
        json={"status": "doing", "priority": "critical"},
    )
    assert updated_task.status_code == 200
    assert updated_task.json()["status"] == "doing"
    assert updated_task.json()["priority"] == "critical"


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
    assert any("vector" in item["matched_terms"] for item in body["evidences"])
    assert body["graph_nodes"]
    assert body["graph_edges"]
    assert "Matched" in body["answer_brief"]


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
