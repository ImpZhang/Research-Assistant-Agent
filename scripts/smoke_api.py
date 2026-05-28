"""Run an end-to-end API smoke test for the research workflow.

By default this uses FastAPI's in-process TestClient, so it does not require a
running server. Pass --base-url to test an already running HTTP service.
"""

from __future__ import annotations

import argparse
import json
import sys
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

    def post(self, path: str, *, json_body: dict | None = None, files: dict | None = None) -> ResponseAdapter:
        response = self.client.post(path, json=json_body, files=files)
        return ResponseAdapter(response.status_code, decode_response_body(response))


class HttpClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def get(self, path: str) -> ResponseAdapter:
        response = requests.get(f"{self.base_url}{path}", timeout=20)
        return ResponseAdapter(response.status_code, decode_response_body(response))

    def post(self, path: str, *, json_body: dict | None = None, files: dict | None = None) -> ResponseAdapter:
        response = requests.post(f"{self.base_url}{path}", json=json_body, files=files, timeout=30)
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

    upload = require_ok(
        client.post(
            "/research/papers/upload",
            files={"file": ("smoke_paper.txt", SMOKE_PAPER, "text/plain")},
        ),
        "paper upload",
    )
    paper_id = upload["paper"]["id"]

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
        "paper_id": paper_id,
        "card_id": workflow["card"]["id"],
        "gap_count": len(workflow["gaps"]),
        "idea_count": len(workflow["ideas"]),
        "review_count": len(workflow["reviews"]),
        "experiment_plan_count": len(workflow["experiment_plans"]),
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
