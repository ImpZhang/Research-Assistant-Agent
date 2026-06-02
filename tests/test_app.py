import io
import json
import time
import zipfile
from xml.etree import ElementTree

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.research.db import SessionLocal
from backend.research.services.literature_search_service import LiteratureSearchService
from backend.research.services.workflow_service import WorkflowService


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
    assert "advisor_brief_execution_context" in body["implemented_capabilities"]
    assert "advisor_brief_triage_context" in body["implemented_capabilities"]
    assert "mcp_stdio_http_bridge" in body["implemented_capabilities"]
    assert "mcp_bridge_policy_controls" in body["implemented_capabilities"]
    assert "mcp_tool_bridge_spec" in body["implemented_capabilities"]
    assert "idea_decision_memos" in body["implemented_capabilities"]
    assert "idea_assumption_audits" in body["implemented_capabilities"]
    assert "project_triage_brief" in body["implemented_capabilities"]
    assert "project_triage_task_generation" in body["implemented_capabilities"]
    assert "project_triage_snapshots" in body["implemented_capabilities"]
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
    assert "get_research_profile" in names
    assert "update_research_profile" in names
    assert "create_research_plan" in names
    assert "create_tasks_from_research_plan" in names
    assert "get_research_plan_progress" in names
    assert "get_project_progress_overview" in names
    assert "get_project_triage_brief" in names
    assert "export_project_triage_brief_markdown" in names
    assert "create_tasks_from_project_triage_brief" in names
    assert "create_project_triage_snapshot" in names
    assert "list_project_triage_snapshots" in names
    assert "get_project_triage_snapshot" in names
    assert "export_project_triage_snapshot_markdown" in names
    assert "get_mcp_tool_spec" in names
    assert "get_idea_research_packet" in names
    assert "get_idea_timeline" in names
    assert "export_idea_bundle" in names
    assert "export_project_bundle" in names
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

    cancel = tools["cancel_job"]
    assert cancel["side_effect"] is True
    assert cancel["annotations"]["destructiveHint"] is True

    update_profile = tools["update_research_profile"]
    assert update_profile["http"]["method"] == "PUT"
    assert update_profile["input_schema"]["required"] == ["body"]
    assert update_profile["annotations"]["sideEffectHint"] is True


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
    assert "timelineButton" in response.text
    assert "projectBundleButton" in response.text

    script = client.get("/workbench-assets/app.js")
    assert script.status_code == 200
    assert "/research/profile" in script.text
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
    assert "/research/experiment-plans/${state.latestExperimentPlanId}/runs" in script.text
    assert "/research/experiment-runs/${state.latestExperimentRunId}/analysis" in script.text
    assert "/research/experiment-analyses/${state.latestExperimentAnalysisId}/tasks" in script.text
    assert "/research/ideas/${state.latestIdeaId}/lineage" in script.text
    assert "/research/ideas/${state.latestIdeaId}/timeline" in script.text
    assert "/research/ideas/${state.latestIdeaId}/progress" in script.text
    assert "/research/ideas/${state.latestIdeaId}/research-packet" in script.text
    assert "/research/ideas/${encodeURIComponent(state.latestIdeaId)}/export/bundle" in script.text
    assert "/research/export/project-bundle" in script.text
    assert "/research/ideas/${state.latestIdeaId}/readiness" in script.text
    assert "/research/ideas/${state.latestIdeaId}/quality-gate" in script.text
    assert "/research/ideas/${state.latestIdeaId}/quality-gate/tasks" in script.text
    assert "/research/ideas/${state.latestIdeaId}/readiness/tasks" in script.text
    assert "/research/ideas/${state.latestIdeaId}/decision-memo" in script.text
    assert (
        "/research/ideas/${state.latestIdeaId}/decision-memos/${state.latestDecisionMemoId}/tasks"
    ) in script.text
    assert "/research/ideas/${state.latestIdeaId}/assumption-audit" in script.text
    assert "/research/progress/overview" in script.text
    assert "/research/triage/brief" in script.text
    assert "/research/triage/brief/export/markdown" in script.text
    assert "/research/triage/snapshots" in script.text
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
    assert any(task["id"] == task_id for task in lineage_body["research_tasks"])
    assert any(task["id"] == analysis_task_id for task in lineage_body["research_tasks"])
    assert any(task["id"] == decision_task_id for task in lineage_body["research_tasks"])
    assert lineage_body["task_board_snapshots"][0]["id"] == snapshot_body["id"]
    assert lineage_body["graph_edge_summary"]["proposal_revision_creates_task"] > 0
    assert lineage_body["graph_edge_summary"]["experiment_plan_has_run"] > 0
    assert lineage_body["graph_edge_summary"]["experiment_run_has_analysis"] > 0
    assert lineage_body["graph_edge_summary"]["experiment_analysis_creates_task"] > 0
    assert lineage_body["graph_edge_summary"]["idea_has_decision_memo"] > 0
    assert lineage_body["graph_edge_summary"]["decision_memo_creates_task"] > 0
    assert lineage_body["graph_edge_summary"]["idea_has_assumption_audit"] > 0
    assert "# Idea Lineage:" in lineage_body["markdown_export"]
    assert "## Experiment Runs" in lineage_body["markdown_export"]
    assert "## Experiment Analyses" in lineage_body["markdown_export"]
    assert "## Decision Memos" in lineage_body["markdown_export"]
    assert "## Assumption Audits" in lineage_body["markdown_export"]

    timeline = client.get(f"/research/ideas/{idea_id}/timeline")
    assert timeline.status_code == 200
    timeline_body = timeline.json()
    assert timeline_body["idea"]["id"] == idea_id
    event_types = {event["event_type"] for event in timeline_body["events"]}
    assert "idea_created" in event_types
    assert "experiment_analysis_created" in event_types
    assert "decision_memo_created" in event_types
    assert "# Idea Timeline:" in timeline_body["markdown_export"]

    progress = client.get(f"/research/ideas/{idea_id}/progress")
    assert progress.status_code == 200
    progress_body = progress.json()
    assert progress_body["idea"]["id"] == idea_id
    assert progress_body["artifact_counts"]["experiment_runs"] >= 1
    assert progress_body["artifact_counts"]["experiment_analyses"] >= 1
    assert progress_body["artifact_counts"]["decision_memos"] >= 1
    assert progress_body["artifact_counts"]["assumption_audits"] >= 1
    assert progress_body["artifact_counts"]["analysis_follow_up_tasks"] >= 1
    assert progress_body["artifact_counts"]["decision_follow_up_tasks"] >= 1
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
    assert any(task["id"] == decision_task_id for task in packet_body["open_tasks"])
    assert "idea_has_assumption_audit" in packet_body["graph_edge_summary"]
    assert "# Idea Research Packet:" in packet_body["markdown_export"]
    assert "## Packet Use" in packet_body["markdown_export"]

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
        manifest = json.loads(archive.read("metadata/manifest.json"))
        assert manifest["idea_id"] == idea_id
        assert manifest["artifact_counts"]["proposal_drafts"] >= 1
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
    assert overview_body["recent_experiment_analyses"]
    assert overview_body["recommended_actions"]
    assert "# Research Progress Overview" in overview_body["markdown_export"]

    radar = client.get("/research/opportunities/radar?limit=5")
    assert radar.status_code == 200
    radar_body = radar.json()
    assert radar_body["idea_count"] >= 1
    assert radar_body["top_opportunities"]
    assert radar_body["top_opportunities"][0]["idea_id"]
    assert radar_body["top_opportunities"][0]["next_actions"]
    assert radar_body["recommended_sequence"]
    assert "# Research Opportunity Radar" in radar_body["markdown_export"]

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
    assert "# Pytest Advisor Brief" in brief_body["markdown_export"]
    assert "## Triage Signals" in brief_body["markdown_export"]
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
        assert "metadata/manifest.json" in names
        assert "metadata/triage-brief.json" in names
        assert "metadata/triage-snapshots.json" in names
        assert "metadata/quality-gate-overview.json" in names
        assert "metadata/opportunity-radar.json" in names
        assert (
            f"artifacts/triage/project-triage-snapshot-{triage_snapshot_body['id']}.md"
        ) in names
        project_manifest = json.loads(archive.read("metadata/manifest.json"))
        assert project_manifest["idea_count"] >= 1
        assert project_manifest["quality_gate_idea_count"] >= 1
        assert project_manifest["average_quality_gate_score"] >= 0
        assert project_manifest["quality_gate_decision_counts"]
        assert project_manifest["triage_next_action_count"] >= 1
        assert project_manifest["triage_snapshot_count"] >= 1
        assert project_manifest["latest_triage_snapshot_id"] == triage_snapshot_body["id"]
        assert project_manifest["opportunity_count"] >= 1
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
