"""Run an end-to-end API smoke test for the research workflow.

By default this uses FastAPI's in-process TestClient, so it does not require a
running server. Pass --base-url to test an already running HTTP service.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
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

    def json(self) -> Any:
        return self.body


class InProcessClient:
    def __init__(self) -> None:
        from fastapi.testclient import TestClient

        from backend.app import create_app

        self.client = TestClient(create_app())

    def get(self, path: str) -> ResponseAdapter:
        response = self.client.get(path)
        return ResponseAdapter(response.status_code, decode_response_body(response))

    def post(
        self, path: str, *, json_body: dict | None = None, files: dict | None = None
    ) -> ResponseAdapter:
        response = self.client.post(path, json=json_body, files=files)
        return ResponseAdapter(response.status_code, decode_response_body(response))

    def patch(self, path: str, *, json_body: dict | None = None) -> ResponseAdapter:
        response = self.client.patch(path, json=json_body)
        return ResponseAdapter(response.status_code, decode_response_body(response))


class HttpClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def get(self, path: str) -> ResponseAdapter:
        response = requests.get(f"{self.base_url}{path}", timeout=20)
        return ResponseAdapter(response.status_code, decode_response_body(response))

    def post(
        self, path: str, *, json_body: dict | None = None, files: dict | None = None
    ) -> ResponseAdapter:
        response = requests.post(f"{self.base_url}{path}", json=json_body, files=files, timeout=30)
        return ResponseAdapter(response.status_code, decode_response_body(response))

    def patch(self, path: str, *, json_body: dict | None = None) -> ResponseAdapter:
        response = requests.patch(f"{self.base_url}{path}", json=json_body, timeout=20)
        return ResponseAdapter(response.status_code, decode_response_body(response))


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
    workbench = require_ok(client.get("/workbench"), "workbench")

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
            json_body={"status": "doing", "priority": "critical"},
        ),
        "research task update",
    )
    if updated_task["status"] != "doing":
        raise RuntimeError("research task update did not persist status")
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
        "task_snapshot_id": task_snapshot["id"],
        "task_snapshot_task_count": task_snapshot["summary"]["task_count"],
        "task_snapshot_markdown_chars": len(task_snapshot_markdown),
        "proposal_task_graph_edge_count": len(proposal_graph_edges),
        "lineage_task_count": len(lineage["research_tasks"]),
        "lineage_graph_edge_types": len(lineage["graph_edge_summary"]),
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
