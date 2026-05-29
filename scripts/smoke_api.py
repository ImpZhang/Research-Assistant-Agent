"""Run an end-to-end API smoke test for the research workflow.

By default this uses FastAPI's in-process TestClient, so it does not require a
running server. Pass --base-url to test an already running HTTP service.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


SMOKE_PAPER = b"""Research Assistant Agent Smoke Paper

Abstract
This smoke paper validates an evidence-grounded research assistant workflow.

Introduction
Research assistants need to connect raw literature evidence to research gaps and ideas.

Method
The system ingests documents, creates evidence records, maps them into paper cards, and links workflow objects in a graph.

Limitations
The current smoke workflow uses deterministic extraction and still needs external novelty checks.

Conclusion
Future work should connect structured extraction, reviewer simulation, and experiment planning to stronger models.
"""


@dataclass
class ResponseAdapter:
    status_code: int
    body: Any
    headers: dict[str, str] = field(default_factory=dict)
    content: bytes = b""

    def json(self) -> Any:
        return self.body


class InProcessClient:
    def __init__(self) -> None:
        from fastapi.testclient import TestClient

        from backend.app import create_app

        self.client = TestClient(create_app())

    def get(self, path: str) -> ResponseAdapter:
        response = self.client.get(path)
        return ResponseAdapter(
            response.status_code,
            decode_response_body(response),
            dict(response.headers),
            response.content,
        )

    def post(
        self, path: str, *, json_body: dict | None = None, files: dict | None = None
    ) -> ResponseAdapter:
        response = self.client.post(path, json=json_body, files=files)
        return ResponseAdapter(
            response.status_code,
            decode_response_body(response),
            dict(response.headers),
            response.content,
        )

    def patch(self, path: str, *, json_body: dict | None = None) -> ResponseAdapter:
        response = self.client.patch(path, json=json_body)
        return ResponseAdapter(
            response.status_code,
            decode_response_body(response),
            dict(response.headers),
            response.content,
        )


class HttpClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def get(self, path: str) -> ResponseAdapter:
        response = requests.get(f"{self.base_url}{path}", timeout=20)
        return ResponseAdapter(
            response.status_code,
            decode_response_body(response),
            dict(response.headers),
            response.content,
        )

    def post(
        self, path: str, *, json_body: dict | None = None, files: dict | None = None
    ) -> ResponseAdapter:
        response = requests.post(f"{self.base_url}{path}", json=json_body, files=files, timeout=30)
        return ResponseAdapter(
            response.status_code,
            decode_response_body(response),
            dict(response.headers),
            response.content,
        )

    def patch(self, path: str, *, json_body: dict | None = None) -> ResponseAdapter:
        response = requests.patch(f"{self.base_url}{path}", json=json_body, timeout=20)
        return ResponseAdapter(
            response.status_code,
            decode_response_body(response),
            dict(response.headers),
            response.content,
        )


def decode_response_body(response: Any) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text


def require_ok(response: ResponseAdapter, label: str) -> Any:
    if response.status_code >= 400:
        raise RuntimeError(f"{label} failed with HTTP {response.status_code}: {response.json()}")
    return response.json()


def run_smoke(client: InProcessClient | HttpClient) -> dict:
    health = require_ok(client.get("/health"), "health")
    status = require_ok(client.get("/research/status"), "research status")
    tool_manifest = require_ok(client.get("/research/tools/manifest"), "tool manifest")
    tool_bridge = require_ok(client.get("/research/tools/mcp-spec"), "tool bridge spec")
    workbench = require_ok(client.get("/workbench"), "workbench")
    if "workflow_job_cancel_retry_controls" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include job cancel/retry controls")
    if "idea_research_packet" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include idea research packet")
    if "idea_readiness_scoring" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include idea readiness scoring")
    if "project_readiness_overview" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include project readiness overview")
    if "idea_artifact_bundle_export" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include idea artifact bundle export")
    if "mcp_tool_bridge_spec" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include MCP tool bridge spec")
    if "idea_decision_memos" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include idea decision memos")
    if "idea_decision_task_generation" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include idea decision task generation")
    if "idea_assumption_audits" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include idea assumption audits")
    manifest_names = {tool["name"] for tool in tool_manifest["tools"]}
    if "create_advisor_brief" not in manifest_names:
        raise RuntimeError("tool manifest did not include advisor brief tool")
    if "get_mcp_tool_spec" not in manifest_names:
        raise RuntimeError("tool manifest did not include MCP tool bridge spec")
    if "get_project_progress_overview" not in manifest_names:
        raise RuntimeError("tool manifest did not include project progress overview tool")
    if "retry_job" not in manifest_names:
        raise RuntimeError("tool manifest did not include job retry tool")
    if "get_idea_research_packet" not in manifest_names:
        raise RuntimeError("tool manifest did not include idea research packet tool")
    if "export_idea_bundle" not in manifest_names:
        raise RuntimeError("tool manifest did not include idea bundle export tool")
    if "get_idea_readiness" not in manifest_names:
        raise RuntimeError("tool manifest did not include idea readiness tool")
    if "get_project_readiness_overview" not in manifest_names:
        raise RuntimeError("tool manifest did not include project readiness overview tool")
    if "create_idea_decision_memo" not in manifest_names:
        raise RuntimeError("tool manifest did not include idea decision memo tool")
    if "create_tasks_from_idea_decision_memo" not in manifest_names:
        raise RuntimeError("tool manifest did not include idea decision task tool")
    if "create_idea_assumption_audit" not in manifest_names:
        raise RuntimeError("tool manifest did not include idea assumption audit tool")
    bridge_names = {tool["name"] for tool in tool_bridge["tools"]}
    if "export_idea_bundle" not in bridge_names:
        raise RuntimeError("tool bridge spec did not include idea bundle export")
    bundle_bridge = next(
        tool for tool in tool_bridge["tools"] if tool["name"] == "export_idea_bundle"
    )
    if bundle_bridge["input_schema"]["required"] != ["idea_id"]:
        raise RuntimeError("tool bridge spec did not expose idea_id as the bundle input")

    upload = require_ok(
        client.post(
            "/research/papers/upload",
            files={"file": ("smoke_paper.txt", SMOKE_PAPER, "text/plain")},
        ),
        "paper upload",
    )
    paper_id = upload["paper"]["id"]
    literature = require_ok(
        client.post(
            "/research/literature/search",
            json_body={
                "query": "evidence grounded research assistant workflow",
                "limit": 5,
                "include_external": True,
            },
        ),
        "literature search",
    )

    workflow = require_ok(
        client.post(
            "/research/workflows/literature-to-ideas",
            json_body={
                "paper_id": paper_id,
                "max_gaps": 4,
                "max_ideas_per_gap": 2,
                "include_markdown_export": True,
            },
        ),
        "literature-to-ideas workflow",
    )
    if not workflow["gaps"]:
        raise RuntimeError("workflow returned no gaps")
    if not workflow["ideas"]:
        raise RuntimeError("workflow returned no ideas")
    if not workflow["novelty_checks"]:
        raise RuntimeError("workflow returned no novelty checks")
    first_novelty_check = workflow["novelty_checks"][0]
    job = require_ok(client.get(f"/research/jobs/{workflow['job_id']}"), "workflow job trace")
    artifacts = require_ok(
        client.get(f"/research/jobs/{workflow['job_id']}/artifacts"),
        "workflow job artifacts",
    )
    if len(artifacts["ideas"]) != len(workflow["ideas"]):
        raise RuntimeError("job artifact snapshot did not include all workflow ideas")
    if "# Research Idea Dossier:" not in artifacts["markdown_export"]:
        raise RuntimeError("job artifact snapshot did not render dossier markdown")
    source_idea_id = workflow["ideas"][0]["id"]
    refinement = require_ok(
        client.post(
            f"/research/ideas/{source_idea_id}/refine",
            json_body={"focus": "sharpen novelty and first executable experiment"},
        ),
        "idea refinement",
    )
    refined_idea = refinement["refined_idea"]
    if refined_idea["parent_idea_id"] != source_idea_id:
        raise RuntimeError("refined idea did not preserve parent lineage")
    refined_markdown = require_ok(
        client.get(f"/research/ideas/{refined_idea['id']}/export/markdown"),
        "refined idea markdown",
    )
    if f"- Parent Idea ID: `{source_idea_id}`" not in refined_markdown:
        raise RuntimeError("refined idea markdown did not include parent lineage")
    related_work_matrix = require_ok(
        client.post(
            f"/research/ideas/{refined_idea['id']}/related-work-matrix",
            json_body={
                "include_external": True,
                "limit": 6,
                "created_by": "smoke_api",
            },
        ),
        "related work matrix",
    )
    related_work_markdown = require_ok(
        client.get(
            "/research/ideas/"
            f"{refined_idea['id']}/related-work-matrices/"
            f"{related_work_matrix['id']}/export/markdown"
        ),
        "related work matrix markdown",
    )
    if "# Related Work Matrix:" not in related_work_markdown:
        raise RuntimeError("related work matrix markdown did not include the report title")
    if not related_work_matrix["items"]:
        raise RuntimeError("related work matrix did not include overlap rows")
    refined_plan = require_ok(
        client.post(f"/research/ideas/{refined_idea['id']}/experiment-plan"),
        "refined idea experiment plan",
    )
    proposal_draft = require_ok(
        client.post(
            f"/research/ideas/{refined_idea['id']}/proposal-draft",
            json_body={
                "related_work_matrix_id": related_work_matrix["id"],
                "experiment_plan_id": refined_plan["id"],
                "created_by": "smoke_api",
            },
        ),
        "proposal draft",
    )
    proposal_markdown = require_ok(
        client.get(
            "/research/ideas/"
            f"{refined_idea['id']}/proposal-drafts/"
            f"{proposal_draft['id']}/export/markdown"
        ),
        "proposal draft markdown",
    )
    if "## Related Work Positioning" not in proposal_markdown:
        raise RuntimeError("proposal draft markdown did not include related work positioning")
    proposal_review = require_ok(
        client.post(
            f"/research/ideas/{refined_idea['id']}/proposal-drafts/{proposal_draft['id']}/review",
            json_body={"reviewer_type": "advisor", "created_by": "smoke_api"},
        ),
        "proposal readiness review",
    )
    proposal_review_markdown = require_ok(
        client.get(
            "/research/ideas/"
            f"{refined_idea['id']}/proposal-drafts/"
            f"{proposal_draft['id']}/reviews/"
            f"{proposal_review['id']}/export/markdown"
        ),
        "proposal readiness review markdown",
    )
    if "## Required Revisions" not in proposal_review_markdown:
        raise RuntimeError("proposal review markdown did not include required revisions")
    proposal_revision = require_ok(
        client.post(
            f"/research/ideas/{refined_idea['id']}/proposal-drafts/{proposal_draft['id']}/revise",
            json_body={
                "proposal_review_id": proposal_review["id"],
                "created_by": "smoke_api",
            },
        ),
        "proposal revision",
    )
    proposal_revision_markdown = require_ok(
        client.get(
            "/research/ideas/"
            f"{refined_idea['id']}/proposal-drafts/"
            f"{proposal_draft['id']}/revisions/"
            f"{proposal_revision['id']}/export/markdown"
        ),
        "proposal revision markdown",
    )
    if "## Applied Revisions" not in proposal_revision_markdown:
        raise RuntimeError("proposal revision markdown did not include applied revisions")
    task_backlog = require_ok(
        client.post(
            "/research/ideas/"
            f"{refined_idea['id']}/proposal-drafts/"
            f"{proposal_draft['id']}/revisions/"
            f"{proposal_revision['id']}/tasks",
            json_body={"created_by": "smoke_api"},
        ),
        "proposal revision task backlog",
    )
    if not task_backlog["tasks"]:
        raise RuntimeError("proposal revision task backlog returned no tasks")
    updated_task = require_ok(
        client.patch(
            f"/research/tasks/{task_backlog['tasks'][0]['id']}",
            json_body={
                "status": "doing",
                "priority": "critical",
                "note": "Smoke task execution started.",
                "created_by": "smoke_api",
            },
        ),
        "research task update",
    )
    if updated_task["status"] != "doing":
        raise RuntimeError("research task update did not persist status")
    manual_task_event = require_ok(
        client.post(
            f"/research/tasks/{updated_task['id']}/events",
            json_body={
                "event_type": "progress",
                "note": "Smoke progress event for task execution history.",
                "metadata": {"source": "smoke_api"},
                "created_by": "smoke_api",
            },
        ),
        "research task event",
    )
    task_events = require_ok(
        client.get(f"/research/tasks/{updated_task['id']}/events"),
        "research task events",
    )
    event_types = {event["event_type"] for event in task_events}
    if not {"created", "task_updated", "progress"}.issubset(event_types):
        raise RuntimeError(f"research task events were incomplete: {event_types}")
    experiment_run = require_ok(
        client.post(
            f"/research/experiment-plans/{refined_plan['id']}/runs",
            json_body={
                "title": "Smoke MVP experiment run",
                "task_id": updated_task["id"],
                "status": "running",
                "dataset_snapshot": "smoke paper fixture",
                "parameters": {"runner": "smoke_api", "seed": 7},
                "metric_results": {"primary_metric": {"value": 0.64, "direction": "higher"}},
                "artifact_links": [{"label": "smoke script", "path": "scripts/smoke_api.py"}],
                "notes": "Smoke registered the first execution run.",
                "created_by": "smoke_api",
            },
        ),
        "experiment run",
    )
    completed_run = require_ok(
        client.patch(
            f"/research/experiment-runs/{experiment_run['id']}",
            json_body={
                "status": "completed",
                "metric_results": {
                    "primary_metric": {"value": 0.71, "direction": "higher"},
                    "cost": {"value": 0.4, "unit": "gpu_hours"},
                },
                "conclusion": "Smoke run produced a measurable improvement signal.",
                "notes": "Smoke completed the experiment execution loop.",
                "created_by": "smoke_api",
            },
        ),
        "experiment run update",
    )
    run_markdown = require_ok(
        client.get(f"/research/experiment-runs/{experiment_run['id']}/export/markdown"),
        "experiment run markdown",
    )
    if "## Conclusion" not in run_markdown:
        raise RuntimeError("experiment run markdown did not include the conclusion section")
    experiment_analysis = require_ok(
        client.post(
            f"/research/experiment-runs/{experiment_run['id']}/analysis",
            json_body={"created_by": "smoke_api"},
        ),
        "experiment analysis",
    )
    analysis_markdown = require_ok(
        client.get(f"/research/experiment-analyses/{experiment_analysis['id']}/export/markdown"),
        "experiment analysis markdown",
    )
    if "## Next Actions" not in analysis_markdown:
        raise RuntimeError("experiment analysis markdown did not include next actions")
    run_analyses = require_ok(
        client.get(f"/research/experiment-runs/{experiment_run['id']}/analyses"),
        "experiment analyses for run",
    )
    if not run_analyses or run_analyses[0]["id"] != experiment_analysis["id"]:
        raise RuntimeError("experiment run did not list its analysis")
    analysis_tasks = require_ok(
        client.post(
            f"/research/experiment-analyses/{experiment_analysis['id']}/tasks",
            json_body={"created_by": "smoke_api"},
        ),
        "experiment analysis tasks",
    )
    if not analysis_tasks["tasks"]:
        raise RuntimeError("experiment analysis task generation returned no tasks")
    if analysis_tasks["tasks"][0]["owner_type"] != "experiment_analysis":
        raise RuntimeError("experiment analysis tasks used the wrong owner type")
    plan_runs = require_ok(
        client.get(f"/research/experiment-plans/{refined_plan['id']}/runs"),
        "experiment runs for plan",
    )
    if not plan_runs or plan_runs[0]["id"] != experiment_run["id"]:
        raise RuntimeError("experiment plan did not list the new run")
    task_events_after_run = require_ok(
        client.get(f"/research/tasks/{updated_task['id']}/events"),
        "research task events after experiment analysis",
    )
    run_event_types = {event["event_type"] for event in task_events_after_run}
    if not {
        "experiment_run_created",
        "experiment_run_updated",
        "experiment_analysis_created",
    }.issubset(run_event_types):
        raise RuntimeError(
            f"experiment run/analysis task events were incomplete: {run_event_types}"
        )
    task_snapshot = require_ok(
        client.post(
            "/research/tasks/snapshots",
            json_body={
                "title": "Smoke Research Task Board",
                "idea_id": refined_idea["id"],
                "owner_type": "proposal_revision",
                "created_by": "smoke_api",
            },
        ),
        "task board snapshot",
    )
    task_snapshot_markdown = require_ok(
        client.get(f"/research/tasks/snapshots/{task_snapshot['id']}/export/markdown"),
        "task board snapshot markdown",
    )
    if "## Next Actions" not in task_snapshot_markdown:
        raise RuntimeError("task board snapshot markdown did not include next actions")
    decision_memo = require_ok(
        client.post(
            f"/research/ideas/{refined_idea['id']}/decision-memo",
            json_body={
                "decision": "pursue",
                "created_by": "smoke_api",
            },
        ),
        "idea decision memo",
    )
    decision_memo_markdown = require_ok(
        client.get(
            f"/research/ideas/{refined_idea['id']}/decision-memos/{decision_memo['id']}/export/markdown"
        ),
        "idea decision memo markdown",
    )
    if "## Next Commitments" not in decision_memo_markdown:
        raise RuntimeError("idea decision memo markdown did not include next commitments")
    decision_tasks = require_ok(
        client.post(
            f"/research/ideas/{refined_idea['id']}/decision-memos/{decision_memo['id']}/tasks",
            json_body={"created_by": "smoke_api"},
        ),
        "idea decision memo tasks",
    )
    if not decision_tasks["tasks"]:
        raise RuntimeError("idea decision memo task generation returned no tasks")
    if decision_tasks["tasks"][0]["owner_type"] != "idea_decision_memo":
        raise RuntimeError("idea decision memo tasks used the wrong owner type")
    assumption_audit = require_ok(
        client.post(
            f"/research/ideas/{refined_idea['id']}/assumption-audit",
            json_body={"created_by": "smoke_api"},
        ),
        "idea assumption audit",
    )
    assumption_audit_markdown = require_ok(
        client.get(
            f"/research/ideas/{refined_idea['id']}/assumption-audits/{assumption_audit['id']}/export/markdown"
        ),
        "idea assumption audit markdown",
    )
    if "## Assumptions" not in assumption_audit_markdown:
        raise RuntimeError("idea assumption audit markdown did not include assumptions")
    proposal_graph_edges = require_ok(
        client.get("/research/graph/edges?edge_type=proposal_revision_creates_task"),
        "proposal task graph edges",
    )
    if not proposal_graph_edges:
        raise RuntimeError("proposal revision task graph edges were not created")
    lineage = require_ok(
        client.get(f"/research/ideas/{refined_idea['id']}/lineage"),
        "idea lineage",
    )
    if proposal_revision["id"] not in lineage["markdown_export"]:
        raise RuntimeError("idea lineage markdown did not include proposal revision")
    if experiment_run["id"] not in lineage["markdown_export"]:
        raise RuntimeError("idea lineage markdown did not include experiment run")
    if experiment_analysis["id"] not in lineage["markdown_export"]:
        raise RuntimeError("idea lineage markdown did not include experiment analysis")
    if decision_memo["id"] not in lineage["markdown_export"]:
        raise RuntimeError("idea lineage markdown did not include decision memo")
    if analysis_tasks["tasks"][0]["id"] not in lineage["markdown_export"]:
        raise RuntimeError("idea lineage markdown did not include experiment analysis task")
    if decision_tasks["tasks"][0]["id"] not in lineage["markdown_export"]:
        raise RuntimeError("idea lineage markdown did not include decision memo task")
    if assumption_audit["id"] not in lineage["markdown_export"]:
        raise RuntimeError("idea lineage markdown did not include assumption audit")
    progress = require_ok(
        client.get(f"/research/ideas/{refined_idea['id']}/progress"),
        "idea progress",
    )
    if progress["artifact_counts"]["analysis_follow_up_tasks"] < 1:
        raise RuntimeError("idea progress did not count analysis follow-up tasks")
    if progress["artifact_counts"]["decision_memos"] < 1:
        raise RuntimeError("idea progress did not count decision memos")
    if progress["artifact_counts"]["decision_follow_up_tasks"] < 1:
        raise RuntimeError("idea progress did not count decision follow-up tasks")
    if progress["artifact_counts"]["assumption_audits"] < 1:
        raise RuntimeError("idea progress did not count assumption audits")
    if "Idea Progress" not in progress["markdown_export"]:
        raise RuntimeError("idea progress markdown did not include the report title")
    research_packet = require_ok(
        client.get(f"/research/ideas/{refined_idea['id']}/research-packet"),
        "idea research packet",
    )
    if decision_memo["id"] not in research_packet["markdown_export"]:
        raise RuntimeError("idea research packet markdown did not include decision memo")
    if assumption_audit["id"] not in research_packet["markdown_export"]:
        raise RuntimeError("idea research packet markdown did not include assumption audit")
    readiness = require_ok(
        client.get(f"/research/ideas/{refined_idea['id']}/readiness"),
        "idea readiness",
    )
    if readiness["readiness_score"] <= 0:
        raise RuntimeError("idea readiness did not return a positive score")
    if "## Score Breakdown" not in readiness["markdown_export"]:
        raise RuntimeError("idea readiness markdown did not include score breakdown")
    bundle_response = client.get(f"/research/ideas/{refined_idea['id']}/export/bundle")
    if bundle_response.status_code != 200:
        raise RuntimeError(
            "idea bundle export failed with HTTP "
            f"{bundle_response.status_code}: {bundle_response.json()}"
        )
    if bundle_response.headers.get("content-type") != "application/zip":
        raise RuntimeError("idea bundle export did not return an application/zip response")
    with zipfile.ZipFile(io.BytesIO(bundle_response.content)) as archive:
        bundle_files = set(archive.namelist())
        required_bundle_files = {
            "README.md",
            "01-idea-dossier.md",
            "02-lineage.md",
            "03-progress.md",
            "04-research-packet.md",
            "05-readiness.md",
            "metadata/manifest.json",
        }
        missing_bundle_files = required_bundle_files - bundle_files
        if missing_bundle_files:
            raise RuntimeError(f"idea bundle export missed files: {missing_bundle_files}")
        bundle_manifest = json.loads(archive.read("metadata/manifest.json"))
    if bundle_manifest["idea_id"] != refined_idea["id"]:
        raise RuntimeError("idea bundle manifest returned the wrong idea id")
    overview = require_ok(client.get("/research/progress/overview"), "research progress overview")
    if overview["idea_count"] < 1:
        raise RuntimeError("research overview did not include ideas")
    if not overview["recommended_actions"]:
        raise RuntimeError("research overview did not include recommended actions")
    readiness_overview = require_ok(
        client.get("/research/readiness/overview?limit=50"),
        "project readiness overview",
    )
    if readiness_overview["idea_count"] < 1:
        raise RuntimeError("project readiness overview did not include ideas")
    if "Project Readiness Overview" not in readiness_overview["markdown_export"]:
        raise RuntimeError("project readiness overview markdown did not include title")
    advisor_brief = require_ok(
        client.post(
            "/research/briefs",
            json_body={
                "title": "Smoke Advisor Research Brief",
                "scope": "idea_set",
                "idea_ids": [refined_idea["id"]],
                "created_by": "smoke_api",
            },
        ),
        "advisor research brief",
    )
    advisor_brief_markdown = require_ok(
        client.get(f"/research/briefs/{advisor_brief['id']}/export/markdown"),
        "advisor research brief markdown",
    )
    if "## Discussion Prompts" not in advisor_brief_markdown:
        raise RuntimeError("advisor brief markdown did not include discussion prompts")
    feedback = require_ok(
        client.post(
            f"/research/ideas/{refined_idea['id']}/feedback",
            json_body={
                "decision": "shortlist",
                "rating": 4.7,
                "comment": "Smoke test shortlist for the refined experiment-first idea.",
                "tags": ["smoke", "shortlist"],
            },
        ),
        "idea feedback",
    )
    feedback_items = require_ok(
        client.get(f"/research/ideas/{refined_idea['id']}/feedback"),
        "idea feedback list",
    )
    if not feedback_items or feedback_items[0]["id"] != feedback["id"]:
        raise RuntimeError("idea feedback list did not include latest feedback")
    ranking = require_ok(
        client.post(
            "/research/ideas/rank",
            json_body={
                "paper_ids": [paper_id],
                "limit": 5,
                "deduplicate_lineage": True,
            },
        ),
        "idea ranking",
    )
    ranked_ids = [item["idea"]["id"] for item in ranking["ranked_ideas"]]
    if refined_idea["id"] not in ranked_ids:
        raise RuntimeError("idea ranking did not include the refined idea")
    if source_idea_id in ranked_ids:
        raise RuntimeError("idea ranking did not deduplicate the source idea lineage")
    portfolio_markdown = require_ok(
        client.post(
            "/research/ideas/rank/export/markdown",
            json_body={
                "paper_ids": [paper_id],
                "limit": 5,
                "deduplicate_lineage": True,
                "title": "Smoke Research Idea Portfolio",
            },
        ),
        "idea portfolio markdown export",
    )
    if "# Smoke Research Idea Portfolio" not in portfolio_markdown:
        raise RuntimeError("portfolio markdown export did not include the requested title")
    if refined_idea["id"] not in portfolio_markdown:
        raise RuntimeError("portfolio markdown export did not include the refined idea")
    portfolio_snapshot = require_ok(
        client.post(
            "/research/ideas/portfolios",
            json_body={
                "paper_ids": [paper_id],
                "limit": 5,
                "deduplicate_lineage": True,
                "title": "Smoke Saved Research Idea Portfolio",
                "description": "Saved by the end-to-end smoke workflow.",
                "created_by": "smoke_api",
            },
        ),
        "saved idea portfolio snapshot",
    )
    saved_portfolio = require_ok(
        client.get(f"/research/ideas/portfolios/{portfolio_snapshot['id']}"),
        "saved idea portfolio fetch",
    )
    saved_portfolio_markdown = require_ok(
        client.get(f"/research/ideas/portfolios/{portfolio_snapshot['id']}/export/markdown"),
        "saved idea portfolio markdown export",
    )
    portfolio_agenda_markdown = require_ok(
        client.get(f"/research/ideas/portfolios/{portfolio_snapshot['id']}/agenda/markdown"),
        "saved idea portfolio agenda markdown export",
    )
    if saved_portfolio["id"] != portfolio_snapshot["id"]:
        raise RuntimeError("saved portfolio fetch returned the wrong snapshot")
    if "Smoke Saved Research Idea Portfolio" not in saved_portfolio_markdown:
        raise RuntimeError("saved portfolio markdown did not include the saved title")
    if "Research Execution Agenda" not in portfolio_agenda_markdown:
        raise RuntimeError("portfolio agenda markdown did not include the agenda title")
    baseline_snapshot = require_ok(
        client.post(
            "/research/ideas/portfolios",
            json_body={
                "idea_ids": [source_idea_id],
                "limit": 1,
                "deduplicate_lineage": False,
                "title": "Smoke Baseline Portfolio",
                "created_by": "smoke_api",
            },
        ),
        "baseline idea portfolio snapshot",
    )
    portfolio_comparison = require_ok(
        client.post(
            "/research/ideas/portfolios/compare",
            json_body={
                "baseline_snapshot_id": baseline_snapshot["id"],
                "candidate_snapshot_id": portfolio_snapshot["id"],
            },
        ),
        "idea portfolio snapshot comparison",
    )
    portfolio_comparison_markdown = require_ok(
        client.post(
            "/research/ideas/portfolios/compare/export/markdown",
            json_body={
                "baseline_snapshot_id": baseline_snapshot["id"],
                "candidate_snapshot_id": portfolio_snapshot["id"],
            },
        ),
        "idea portfolio comparison markdown export",
    )
    if refined_idea["id"] not in portfolio_comparison["added_idea_ids"]:
        raise RuntimeError("portfolio comparison did not record the refined idea as added")
    if "# Research Idea Portfolio Comparison" not in portfolio_comparison_markdown:
        raise RuntimeError("portfolio comparison markdown did not include the report title")
    async_job = require_ok(
        client.post(
            "/research/workflows/literature-to-ideas/async",
            json_body={
                "paper_id": paper_id,
                "max_gaps": 1,
                "max_ideas_per_gap": 1,
                "include_markdown_export": False,
            },
        ),
        "async literature-to-ideas workflow",
    )
    async_job_status = async_job
    for _ in range(30):
        async_job_status = require_ok(
            client.get(f"/research/jobs/{async_job['id']}"),
            "async workflow job trace",
        )
        if async_job_status["status"] in {"completed", "failed"}:
            break
        time.sleep(0.2)
    if async_job_status["status"] != "completed":
        raise RuntimeError(f"async workflow did not complete: {async_job_status}")
    embeddings = require_ok(
        client.post(
            "/research/embeddings/rebuild",
            json_body={
                "paper_ids": [paper_id],
                "owner_types": ["evidence", "gap", "idea"],
                "limit": 100,
            },
        ),
        "embedding rebuild",
    )
    context = require_ok(
        client.post(
            "/research/search/context",
            json_body={
                "query": "evidence grounded diagnostic metric future work",
                "paper_ids": [paper_id],
                "limit": 5,
                "include_graph": True,
            },
        ),
        "context search",
    )
    nodes = require_ok(client.get("/research/graph/nodes"), "graph nodes")
    edges = require_ok(client.get("/research/graph/edges"), "graph edges")

    return {
        "health": health,
        "phase": status["phase"],
        "tool_manifest_count": len(tool_manifest["tools"]),
        "tool_bridge_count": len(tool_bridge["tools"]),
        "workbench_available": "Research Assistant Workbench" in workbench,
        "paper_id": paper_id,
        "literature_result_count": len(literature["items"]),
        "literature_external_status": literature["external_status"],
        "workflow_job_id": workflow["job_id"],
        "workflow_job_status": job["status"],
        "artifact_idea_count": len(artifacts["ideas"]),
        "artifact_markdown_chars": len(artifacts["markdown_export"]),
        "refined_idea_id": refined_idea["id"],
        "refined_idea_parent_id": refined_idea["parent_idea_id"],
        "related_work_matrix_id": related_work_matrix["id"],
        "related_work_item_count": len(related_work_matrix["items"]),
        "related_work_markdown_chars": len(related_work_markdown),
        "proposal_draft_id": proposal_draft["id"],
        "proposal_draft_markdown_chars": len(proposal_markdown),
        "proposal_review_id": proposal_review["id"],
        "proposal_review_decision": proposal_review["decision"],
        "proposal_review_score": proposal_review["readiness_score"],
        "proposal_revision_id": proposal_revision["id"],
        "proposal_revision_action_count": len(proposal_revision["applied_revisions"]),
        "proposal_revision_markdown_chars": len(proposal_revision_markdown),
        "task_backlog_count": len(task_backlog["tasks"]),
        "updated_task_status": updated_task["status"],
        "task_event_count": len(task_events),
        "task_event_count_after_analysis": len(task_events_after_run),
        "manual_task_event_id": manual_task_event["id"],
        "experiment_run_id": experiment_run["id"],
        "experiment_run_status": completed_run["status"],
        "experiment_run_markdown_chars": len(run_markdown),
        "experiment_analysis_id": experiment_analysis["id"],
        "experiment_analysis_decision": experiment_analysis["decision"],
        "experiment_analysis_markdown_chars": len(analysis_markdown),
        "experiment_analysis_task_count": len(analysis_tasks["tasks"]),
        "task_snapshot_id": task_snapshot["id"],
        "task_snapshot_task_count": task_snapshot["summary"]["task_count"],
        "task_snapshot_markdown_chars": len(task_snapshot_markdown),
        "decision_memo_id": decision_memo["id"],
        "decision_memo_markdown_chars": len(decision_memo_markdown),
        "decision_memo_task_count": len(decision_tasks["tasks"]),
        "assumption_audit_id": assumption_audit["id"],
        "assumption_audit_count": len(assumption_audit["assumptions"]),
        "assumption_audit_markdown_chars": len(assumption_audit_markdown),
        "proposal_task_graph_edge_count": len(proposal_graph_edges),
        "lineage_task_count": len(lineage["research_tasks"]),
        "lineage_graph_edge_types": len(lineage["graph_edge_summary"]),
        "progress_open_task_count": progress["artifact_counts"]["open_tasks"],
        "progress_recommended_next_step": progress["recommended_next_step"],
        "research_packet_markdown_chars": len(research_packet["markdown_export"]),
        "readiness_score": readiness["readiness_score"],
        "readiness_decision": readiness["decision"],
        "idea_bundle_file_count": len(bundle_files),
        "idea_bundle_manifest_decision": bundle_manifest["readiness"]["decision"],
        "overview_idea_count": overview["idea_count"],
        "overview_open_task_count": overview["task_summary"]["open_task_count"],
        "readiness_overview_idea_count": readiness_overview["idea_count"],
        "readiness_overview_average": readiness_overview["average_readiness"],
        "advisor_brief_id": advisor_brief["id"],
        "advisor_brief_markdown_chars": len(advisor_brief_markdown),
        "feedback_decision": feedback["decision"],
        "feedback_rating": feedback["rating"],
        "ranked_idea_count": len(ranking["ranked_ideas"]),
        "top_ranked_idea_id": ranking["ranked_ideas"][0]["idea"]["id"],
        "top_ranked_idea_score": ranking["ranked_ideas"][0]["weighted_score"],
        "portfolio_markdown_chars": len(portfolio_markdown),
        "portfolio_snapshot_id": portfolio_snapshot["id"],
        "portfolio_snapshot_idea_count": len(portfolio_snapshot["idea_ids"]),
        "portfolio_agenda_markdown_chars": len(portfolio_agenda_markdown),
        "portfolio_comparison_added_count": len(portfolio_comparison["added_idea_ids"]),
        "portfolio_comparison_markdown_chars": len(portfolio_comparison_markdown),
        "async_workflow_job_id": async_job["id"],
        "async_workflow_job_status": async_job_status["status"],
        "card_id": workflow["card"]["id"],
        "gap_count": len(workflow["gaps"]),
        "idea_count": len(workflow["ideas"]),
        "novelty_check_count": len(workflow["novelty_checks"]),
        "novelty_check_status": first_novelty_check["status"],
        "novelty_literature_signal_count": len(
            [
                signal
                for signal in first_novelty_check["collision_signals"]
                if signal["source_type"] == "literature"
            ]
        ),
        "review_count": len(workflow["reviews"]),
        "experiment_plan_count": len(workflow["experiment_plans"]),
        "embedding_indexed_count": embeddings["indexed_count"],
        "markdown_export_chars": len(workflow["markdown_export"]),
        "context_evidence_count": len(context["evidences"]),
        "context_graph_node_count": len(context["graph_nodes"]),
        "graph_node_count": len(nodes),
        "graph_edge_count": len(edges),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Research Assistant Agent API smoke test.")
    parser.add_argument(
        "--base-url",
        default="",
        help="Optional running service URL, e.g. http://127.0.0.1:8000. Omit for in-process mode.",
    )
    args = parser.parse_args()

    client = HttpClient(args.base_url) if args.base_url else InProcessClient()
    summary = run_smoke(client)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
