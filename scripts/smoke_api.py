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
    service_readiness = require_ok(client.get("/health/ready"), "readiness")
    if service_readiness["status"] != "ready":
        raise RuntimeError("readiness check did not report ready")
    status = require_ok(client.get("/research/status"), "research status")
    tool_manifest = require_ok(client.get("/research/tools/manifest"), "tool manifest")
    tool_bridge = require_ok(client.get("/research/tools/mcp-spec"), "tool bridge spec")
    research_profile = require_ok(client.get("/research/profile"), "research profile")
    workbench = require_ok(client.get("/workbench"), "workbench")
    if "workflow_job_cancel_retry_controls" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include job cancel/retry controls")
    if "task_execution_controls" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include task execution controls")
    if "workbench_task_board_controls" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include workbench task board controls")
    if "idea_research_packet" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include idea research packet")
    if "idea_activity_timeline" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include idea activity timeline")
    if "idea_readiness_scoring" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include idea readiness scoring")
    if "idea_quality_gate" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include idea quality gate")
    if "idea_quality_gate_task_generation" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include idea quality gate task generation")
    if "project_readiness_overview" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include project readiness overview")
    if "project_quality_gate_overview" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include project quality gate overview")
    if "project_quality_gate_task_generation" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include project quality gate task generation")
    if "project_onboarding_readiness" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include project onboarding readiness")
    if "project_onboarding_setup_wizard" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include project onboarding setup wizard")
    if "project_onboarding_task_generation" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include project onboarding task generation")
    if "project_onboarding_progress_tracking" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include project onboarding progress tracking")
    if "project_pilot_status_report" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include project pilot status report")
    if "project_pilot_report_snapshots" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include project pilot report snapshots")
    if "project_pilot_report_snapshot_comparison" not in status["implemented_capabilities"]:
        raise RuntimeError(
            "research status did not include project pilot report snapshot comparison"
        )
    if (
        "project_pilot_report_snapshot_comparison_task_generation"
        not in status["implemented_capabilities"]
    ):
        raise RuntimeError(
            "research status did not include project pilot report snapshot comparison task generation"
        )
    if "project_pilot_report_snapshot_task_generation" not in status["implemented_capabilities"]:
        raise RuntimeError(
            "research status did not include project pilot report snapshot task generation"
        )
    if "project_cockpit_dashboard" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include project cockpit dashboard")
    if "project_cockpit_task_generation" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include project cockpit task generation")
    if "project_advisor_chat" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include project advisor chat")
    if "project_advisor_chat_task_generation" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include project advisor chat task generation")
    if "project_advisor_action_sessions" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include project advisor action sessions")
    if "research_opportunity_radar" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include research opportunity radar")
    if "opportunity_radar_task_generation" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include opportunity radar task generation")
    if "idea_artifact_bundle_export" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include idea artifact bundle export")
    if "project_handoff_bundle_export" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include project handoff bundle export")
    if "project_bundle_readiness" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include project bundle readiness")
    if "project_bundle_readiness_task_generation" not in status["implemented_capabilities"]:
        raise RuntimeError(
            "research status did not include project bundle readiness task generation"
        )
    if "project_bundle_readiness_snapshots" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include project bundle readiness snapshots")
    if "project_bundle_readiness_snapshot_comparison" not in status["implemented_capabilities"]:
        raise RuntimeError(
            "research status did not include project bundle readiness snapshot comparison"
        )
    if (
        "project_bundle_readiness_snapshot_comparison_task_generation"
        not in status["implemented_capabilities"]
    ):
        raise RuntimeError(
            "research status did not include project bundle readiness comparison tasks"
        )
    if "project_bundle_release_notes" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include project bundle release notes")
    if "project_bundle_release_task_generation" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include project bundle release tasks")
    if "project_bundle_release_progress_tracking" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include project bundle release progress")
    if "project_bundle_release_feedback_tracking" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include project bundle release feedback")
    if "project_bundle_release_feedback_task_generation" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include project bundle release feedback tasks")
    if "project_bundle_release_closeout_tracking" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include project bundle release closeout")
    if "project_bundle_release_closeout_task_generation" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include project bundle release closeout tasks")
    if "project_bundle_release_acceptance_packets" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include project bundle release acceptance")
    if (
        "project_bundle_release_acceptance_packet_snapshots"
        not in status["implemented_capabilities"]
    ):
        raise RuntimeError(
            "research status did not include project bundle release acceptance snapshots"
        )
    if (
        "project_bundle_release_acceptance_packet_snapshot_comparison"
        not in status["implemented_capabilities"]
    ):
        raise RuntimeError("research status did not include release acceptance snapshot comparison")
    if (
        "project_bundle_release_acceptance_packet_snapshot_comparison_task_generation"
        not in status["implemented_capabilities"]
    ):
        raise RuntimeError("research status did not include release acceptance comparison tasks")
    if "project_bundle_release_review_sessions" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include project bundle release review sessions")
    if (
        "project_bundle_release_review_session_task_generation"
        not in status["implemented_capabilities"]
    ):
        raise RuntimeError(
            "research status did not include project bundle release review session tasks"
        )
    if "project_bundle_release_review_outcomes" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include project bundle release review outcomes")
    if (
        "project_bundle_release_review_outcome_task_generation"
        not in status["implemented_capabilities"]
    ):
        raise RuntimeError(
            "research status did not include project bundle release review outcome tasks"
        )
    if (
        "project_bundle_release_review_outcome_progress_tracking"
        not in status["implemented_capabilities"]
    ):
        raise RuntimeError(
            "research status did not include project bundle release review outcome progress"
        )
    if "advisor_brief_execution_context" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include advisor brief execution context")
    if "advisor_brief_triage_context" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include advisor brief triage context")
    if "advisor_brief_triage_snapshot_comparison_context" not in status["implemented_capabilities"]:
        raise RuntimeError(
            "research status did not include advisor brief triage snapshot comparison context"
        )
    if "mcp_tool_bridge_spec" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include MCP tool bridge spec")
    if "mcp_stdio_http_bridge" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include MCP stdio HTTP bridge")
    if "mcp_bridge_policy_controls" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include MCP bridge policy controls")
    if "research_profile_constraints" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include research profile constraints")
    if "research_plan_snapshots" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include research plan snapshots")
    if "research_plan_task_generation" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include research plan task generation")
    if "research_plan_progress_integration" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include research plan progress integration")
    if "research_plan_progress_tracking" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include research plan progress tracking")
    if "idea_decision_memos" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include idea decision memos")
    if "idea_decision_task_generation" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include idea decision task generation")
    if "idea_readiness_task_generation" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include idea readiness task generation")
    if "idea_assumption_audits" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include idea assumption audits")
    if "idea_evidence_ledgers" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include idea evidence ledgers")
    if "idea_evidence_task_generation" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include idea evidence task generation")
    if "claim_evidence_graph_links" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include claim evidence graph links")
    if "claim_validation_packets" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include claim validation packets")
    if "claim_validation_queue" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include claim validation queue")
    if "claim_validation_queue_task_generation" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include claim validation queue task generation")
    if "claim_validation_result_tracking" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include claim validation result tracking")
    if "claim_validation_result_decision_signals" not in status["implemented_capabilities"]:
        raise RuntimeError(
            "research status did not include claim validation result decision signals"
        )
    if "claim_validation_result_ranking_adjustments" not in status["implemented_capabilities"]:
        raise RuntimeError(
            "research status did not include claim validation result ranking adjustments"
        )
    if "advisor_brief_evidence_context" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include advisor brief evidence context")
    if "advisor_brief_claim_validation_context" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include advisor brief claim validation context")
    if "project_triage_brief" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include project triage brief")
    if "project_triage_task_generation" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include project triage task generation")
    if "project_triage_snapshots" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include project triage snapshots")
    if "project_triage_snapshot_comparison" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include project triage snapshot comparison")
    if (
        "project_triage_snapshot_comparison_task_generation"
        not in status["implemented_capabilities"]
    ):
        raise RuntimeError(
            "research status did not include project triage snapshot comparison task generation"
        )
    if "external_novelty_refresh" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include external novelty refresh")
    if "novelty_check_task_generation" not in status["implemented_capabilities"]:
        raise RuntimeError("research status did not include novelty check task generation")
    manifest_names = {tool["name"] for tool in tool_manifest["tools"]}
    if "create_advisor_brief" not in manifest_names:
        raise RuntimeError("tool manifest did not include advisor brief tool")
    if "get_mcp_tool_spec" not in manifest_names:
        raise RuntimeError("tool manifest did not include MCP tool bridge spec")
    if "get_research_profile" not in manifest_names:
        raise RuntimeError("tool manifest did not include research profile reader")
    if "update_research_profile" not in manifest_names:
        raise RuntimeError("tool manifest did not include research profile updater")
    if "create_research_plan" not in manifest_names:
        raise RuntimeError("tool manifest did not include research plan creator")
    if "create_tasks_from_research_plan" not in manifest_names:
        raise RuntimeError("tool manifest did not include research plan task creator")
    if "get_research_plan_progress" not in manifest_names:
        raise RuntimeError("tool manifest did not include research plan progress tool")
    if "get_project_progress_overview" not in manifest_names:
        raise RuntimeError("tool manifest did not include project progress overview tool")
    if "get_project_onboarding_readiness" not in manifest_names:
        raise RuntimeError("tool manifest did not include project onboarding readiness tool")
    if "run_project_setup_wizard" not in manifest_names:
        raise RuntimeError("tool manifest did not include project setup wizard tool")
    if "create_tasks_from_project_onboarding" not in manifest_names:
        raise RuntimeError("tool manifest did not include project onboarding task tool")
    if "get_project_onboarding_progress" not in manifest_names:
        raise RuntimeError("tool manifest did not include project onboarding progress tool")
    if "get_project_pilot_report" not in manifest_names:
        raise RuntimeError("tool manifest did not include project pilot report tool")
    if "create_project_pilot_report_snapshot" not in manifest_names:
        raise RuntimeError("tool manifest did not include project pilot report snapshot creator")
    if "list_project_pilot_report_snapshots" not in manifest_names:
        raise RuntimeError("tool manifest did not include project pilot report snapshot lister")
    if "compare_project_pilot_report_snapshots" not in manifest_names:
        raise RuntimeError("tool manifest did not include project pilot report snapshot comparison")
    if "export_project_pilot_report_snapshot_comparison_markdown" not in manifest_names:
        raise RuntimeError(
            "tool manifest did not include project pilot report snapshot comparison export"
        )
    if "create_tasks_from_project_pilot_report_snapshot_comparison" not in manifest_names:
        raise RuntimeError(
            "tool manifest did not include project pilot report snapshot comparison task tool"
        )
    if "create_tasks_from_project_pilot_report_snapshot" not in manifest_names:
        raise RuntimeError("tool manifest did not include project pilot report snapshot task tool")
    if "get_project_cockpit" not in manifest_names:
        raise RuntimeError("tool manifest did not include project cockpit tool")
    if "export_project_cockpit_markdown" not in manifest_names:
        raise RuntimeError("tool manifest did not include project cockpit markdown export")
    if "create_tasks_from_project_cockpit" not in manifest_names:
        raise RuntimeError("tool manifest did not include project cockpit task tool")
    if "ask_project_advisor" not in manifest_names:
        raise RuntimeError("tool manifest did not include project advisor chat tool")
    if "create_tasks_from_project_advisor_chat" not in manifest_names:
        raise RuntimeError("tool manifest did not include project advisor chat task tool")
    if "run_project_advisor_action_session" not in manifest_names:
        raise RuntimeError("tool manifest did not include project advisor action session tool")
    if "get_project_triage_brief" not in manifest_names:
        raise RuntimeError("tool manifest did not include project triage brief tool")
    if "export_project_triage_brief_markdown" not in manifest_names:
        raise RuntimeError("tool manifest did not include project triage brief markdown export")
    if "create_tasks_from_project_triage_brief" not in manifest_names:
        raise RuntimeError("tool manifest did not include project triage task tool")
    if "create_project_triage_snapshot" not in manifest_names:
        raise RuntimeError("tool manifest did not include project triage snapshot creator")
    if "list_project_triage_snapshots" not in manifest_names:
        raise RuntimeError("tool manifest did not include project triage snapshot lister")
    if "compare_project_triage_snapshots" not in manifest_names:
        raise RuntimeError("tool manifest did not include project triage snapshot comparison")
    if "export_project_triage_snapshot_comparison_markdown" not in manifest_names:
        raise RuntimeError(
            "tool manifest did not include project triage comparison markdown export"
        )
    if "create_tasks_from_project_triage_snapshot_comparison" not in manifest_names:
        raise RuntimeError("tool manifest did not include project triage comparison task tool")
    if "get_project_triage_snapshot" not in manifest_names:
        raise RuntimeError("tool manifest did not include project triage snapshot reader")
    if "export_project_triage_snapshot_markdown" not in manifest_names:
        raise RuntimeError("tool manifest did not include project triage snapshot markdown export")
    if "retry_job" not in manifest_names:
        raise RuntimeError("tool manifest did not include job retry tool")
    if "get_idea_research_packet" not in manifest_names:
        raise RuntimeError("tool manifest did not include idea research packet tool")
    if "get_idea_timeline" not in manifest_names:
        raise RuntimeError("tool manifest did not include idea timeline tool")
    if "export_idea_bundle" not in manifest_names:
        raise RuntimeError("tool manifest did not include idea bundle export tool")
    if "export_project_bundle" not in manifest_names:
        raise RuntimeError("tool manifest did not include project bundle export tool")
    if "get_project_bundle_readiness" not in manifest_names:
        raise RuntimeError("tool manifest did not include project bundle readiness tool")
    if "create_tasks_from_project_bundle_readiness" not in manifest_names:
        raise RuntimeError("tool manifest did not include project bundle readiness task tool")
    if "create_project_bundle_readiness_snapshot" not in manifest_names:
        raise RuntimeError("tool manifest did not include project bundle readiness snapshot tool")
    if "list_project_bundle_readiness_snapshots" not in manifest_names:
        raise RuntimeError("tool manifest did not include project bundle readiness snapshot lister")
    if "get_project_bundle_readiness_snapshot" not in manifest_names:
        raise RuntimeError("tool manifest did not include project bundle readiness snapshot reader")
    if "export_project_bundle_readiness_snapshot_markdown" not in manifest_names:
        raise RuntimeError("tool manifest did not include project bundle readiness snapshot export")
    if "compare_project_bundle_readiness_snapshots" not in manifest_names:
        raise RuntimeError(
            "tool manifest did not include project bundle readiness snapshot comparison"
        )
    if "export_project_bundle_readiness_snapshot_comparison_markdown" not in manifest_names:
        raise RuntimeError(
            "tool manifest did not include project bundle readiness comparison export"
        )
    if "create_tasks_from_project_bundle_readiness_snapshot_comparison" not in manifest_names:
        raise RuntimeError(
            "tool manifest did not include project bundle readiness comparison task tool"
        )
    if "create_project_bundle_release_note" not in manifest_names:
        raise RuntimeError("tool manifest did not include project bundle release note creator")
    if "list_project_bundle_release_notes" not in manifest_names:
        raise RuntimeError("tool manifest did not include project bundle release note lister")
    if "get_project_bundle_release_note" not in manifest_names:
        raise RuntimeError("tool manifest did not include project bundle release note reader")
    if "export_project_bundle_release_note_markdown" not in manifest_names:
        raise RuntimeError("tool manifest did not include project bundle release note export")
    if "create_tasks_from_project_bundle_release_note" not in manifest_names:
        raise RuntimeError("tool manifest did not include project bundle release task tool")
    if "get_project_bundle_release_progress" not in manifest_names:
        raise RuntimeError("tool manifest did not include project bundle release progress tool")
    if "record_project_bundle_release_feedback" not in manifest_names:
        raise RuntimeError("tool manifest did not include project bundle release feedback creator")
    if "list_project_bundle_release_feedback" not in manifest_names:
        raise RuntimeError("tool manifest did not include project bundle release feedback lister")
    if "get_project_bundle_release_feedback" not in manifest_names:
        raise RuntimeError("tool manifest did not include project bundle release feedback reader")
    if "export_project_bundle_release_feedback_markdown" not in manifest_names:
        raise RuntimeError("tool manifest did not include project bundle release feedback export")
    if "create_tasks_from_project_bundle_release_feedback" not in manifest_names:
        raise RuntimeError("tool manifest did not include project bundle release feedback tasks")
    if "get_project_bundle_release_closeout" not in manifest_names:
        raise RuntimeError("tool manifest did not include project bundle release closeout")
    if "create_tasks_from_project_bundle_release_closeout" not in manifest_names:
        raise RuntimeError("tool manifest did not include project bundle release closeout tasks")
    if "get_project_bundle_release_acceptance_packet" not in manifest_names:
        raise RuntimeError("tool manifest did not include project bundle release acceptance")
    if "create_project_bundle_release_acceptance_packet_snapshot" not in manifest_names:
        raise RuntimeError(
            "tool manifest did not include project bundle release acceptance snapshot creator"
        )
    if "list_project_bundle_release_acceptance_packet_snapshots" not in manifest_names:
        raise RuntimeError(
            "tool manifest did not include project bundle release acceptance snapshot lister"
        )
    if "get_project_bundle_release_acceptance_packet_snapshot" not in manifest_names:
        raise RuntimeError(
            "tool manifest did not include project bundle release acceptance snapshot reader"
        )
    if "export_project_bundle_release_acceptance_packet_snapshot_markdown" not in manifest_names:
        raise RuntimeError(
            "tool manifest did not include project bundle release acceptance snapshot export"
        )
    if "compare_project_bundle_release_acceptance_packet_snapshots" not in manifest_names:
        raise RuntimeError(
            "tool manifest did not include project bundle release acceptance snapshot comparison"
        )
    if (
        "export_project_bundle_release_acceptance_packet_snapshot_comparison_markdown"
        not in manifest_names
    ):
        raise RuntimeError(
            "tool manifest did not include project bundle release acceptance comparison export"
        )
    if (
        "create_tasks_from_project_bundle_release_acceptance_packet_snapshot_comparison"
        not in manifest_names
    ):
        raise RuntimeError(
            "tool manifest did not include project bundle release acceptance comparison tasks"
        )
    if "get_project_bundle_release_review_session" not in manifest_names:
        raise RuntimeError("tool manifest did not include project bundle release review session")
    if "create_tasks_from_project_bundle_release_review_session" not in manifest_names:
        raise RuntimeError(
            "tool manifest did not include project bundle release review session tasks"
        )
    if "record_project_bundle_release_review_outcome" not in manifest_names:
        raise RuntimeError("tool manifest did not include project bundle release review outcome")
    if "list_project_bundle_release_review_outcomes" not in manifest_names:
        raise RuntimeError(
            "tool manifest did not include project bundle release review outcome list"
        )
    if "get_project_bundle_release_review_outcome" not in manifest_names:
        raise RuntimeError(
            "tool manifest did not include project bundle release review outcome detail"
        )
    if "export_project_bundle_release_review_outcome_markdown" not in manifest_names:
        raise RuntimeError(
            "tool manifest did not include project bundle release review outcome markdown"
        )
    if "create_tasks_from_project_bundle_release_review_outcome" not in manifest_names:
        raise RuntimeError(
            "tool manifest did not include project bundle release review outcome tasks"
        )
    if "get_project_bundle_release_review_outcome_progress" not in manifest_names:
        raise RuntimeError(
            "tool manifest did not include project bundle release review outcome progress"
        )
    if "get_idea_readiness" not in manifest_names:
        raise RuntimeError("tool manifest did not include idea readiness tool")
    if "get_idea_quality_gate" not in manifest_names:
        raise RuntimeError("tool manifest did not include idea quality gate tool")
    if "create_tasks_from_idea_quality_gate" not in manifest_names:
        raise RuntimeError("tool manifest did not include idea quality gate task tool")
    if "get_project_readiness_overview" not in manifest_names:
        raise RuntimeError("tool manifest did not include project readiness overview tool")
    if "get_project_quality_gate_overview" not in manifest_names:
        raise RuntimeError("tool manifest did not include project quality gate overview tool")
    if "create_tasks_from_project_quality_gate" not in manifest_names:
        raise RuntimeError("tool manifest did not include project quality gate task tool")
    if "get_research_opportunity_radar" not in manifest_names:
        raise RuntimeError("tool manifest did not include research opportunity radar tool")
    if "create_tasks_from_research_opportunity_radar" not in manifest_names:
        raise RuntimeError("tool manifest did not include opportunity radar task tool")
    if "create_idea_decision_memo" not in manifest_names:
        raise RuntimeError("tool manifest did not include idea decision memo tool")
    if "create_tasks_from_idea_decision_memo" not in manifest_names:
        raise RuntimeError("tool manifest did not include idea decision task tool")
    if "create_tasks_from_idea_readiness" not in manifest_names:
        raise RuntimeError("tool manifest did not include idea readiness task tool")
    if "list_research_tasks" not in manifest_names:
        raise RuntimeError("tool manifest did not include task listing tool")
    if "update_research_task" not in manifest_names:
        raise RuntimeError("tool manifest did not include task update tool")
    if "create_idea_assumption_audit" not in manifest_names:
        raise RuntimeError("tool manifest did not include idea assumption audit tool")
    if "create_idea_evidence_ledger" not in manifest_names:
        raise RuntimeError("tool manifest did not include idea evidence ledger tool")
    if "list_idea_evidence_ledgers" not in manifest_names:
        raise RuntimeError("tool manifest did not include idea evidence ledger lister")
    if "create_tasks_from_idea_evidence_ledger" not in manifest_names:
        raise RuntimeError("tool manifest did not include evidence ledger task tool")
    if "get_idea_claim_validation_packet" not in manifest_names:
        raise RuntimeError("tool manifest did not include claim validation packet tool")
    if "get_claim_validation_queue" not in manifest_names:
        raise RuntimeError("tool manifest did not include claim validation queue tool")
    if "create_tasks_from_claim_validation_queue" not in manifest_names:
        raise RuntimeError("tool manifest did not include claim validation queue task tool")
    if "record_claim_validation_result" not in manifest_names:
        raise RuntimeError("tool manifest did not include claim validation result tool")
    if "refresh_idea_novelty_search" not in manifest_names:
        raise RuntimeError("tool manifest did not include novelty refresh tool")
    if "create_tasks_from_idea_novelty_check" not in manifest_names:
        raise RuntimeError("tool manifest did not include novelty check task tool")
    bridge_names = {tool["name"] for tool in tool_bridge["tools"]}
    if "export_idea_bundle" not in bridge_names:
        raise RuntimeError("tool bridge spec did not include idea bundle export")
    if research_profile["id"] != "default":
        raise RuntimeError("research profile endpoint did not return the default profile")
    if "onboardingButton" not in workbench:
        raise RuntimeError("workbench did not include the onboarding readiness button")
    if "onboardingMarkdownButton" not in workbench:
        raise RuntimeError("workbench did not include the onboarding markdown button")
    if "onboardingTasksButton" not in workbench:
        raise RuntimeError("workbench did not include the onboarding task button")
    if "onboardingProgressButton" not in workbench:
        raise RuntimeError("workbench did not include the onboarding progress button")
    if "pilotReportButton" not in workbench:
        raise RuntimeError("workbench did not include the pilot report button")
    if "pilotReportSnapshotButton" not in workbench:
        raise RuntimeError("workbench did not include the pilot report snapshot button")
    if "pilotReportSnapshotCompareButton" not in workbench:
        raise RuntimeError("workbench did not include the pilot report snapshot compare button")
    if "pilotReportSnapshotComparisonTasksButton" not in workbench:
        raise RuntimeError(
            "workbench did not include the pilot report snapshot comparison task button"
        )
    if "pilotReportSnapshotTasksButton" not in workbench:
        raise RuntimeError("workbench did not include the pilot report snapshot task button")
    if "setupWizardForm" not in workbench or "setupWizardButton" not in workbench:
        raise RuntimeError("workbench did not include the project setup wizard")
    if "cockpitButton" not in workbench:
        raise RuntimeError("workbench did not include the project cockpit button")
    if "advisorChatForm" not in workbench:
        raise RuntimeError("workbench did not include advisor chat form")
    if "advisorChatTasksButton" not in workbench:
        raise RuntimeError("workbench did not include advisor chat task button")
    if "advisorActionSessionButton" not in workbench:
        raise RuntimeError("workbench did not include advisor action session button")
    if "apiKeyInput" not in workbench or "saveApiKeyButton" not in workbench:
        raise RuntimeError("workbench did not include API key controls")
    bundle_bridge = next(
        tool for tool in tool_bridge["tools"] if tool["name"] == "export_idea_bundle"
    )
    if bundle_bridge["input_schema"]["required"] != ["idea_id"]:
        raise RuntimeError("tool bridge spec did not expose idea_id as the bundle input")
    setup_wizard = require_ok(
        client.post(
            "/research/onboarding/setup",
            json_body={
                "name": "Smoke Research Pilot",
                "primary_domains": ["research agents", "GraphRAG", "scientific ideation"],
                "active_questions": [
                    "How can an evidence-grounded assistant generate testable research ideas?"
                ],
                "target_venues": ["ACL", "NeurIPS"],
                "methodological_preferences": [
                    "literature-grounded ideation",
                    "lightweight evaluation",
                ],
                "resource_constraints": ["limited GPU budget", "local reproducible experiments"],
                "risk_tolerance": "medium",
                "timeline_horizon": "30 days",
                "success_criteria": [
                    "advisor-ready report",
                    "first executable experiment plan",
                ],
                "first_milestone": "Upload seed papers and run the first workflow.",
                "created_by": "smoke_api",
            },
        ),
        "project setup wizard",
    )
    if setup_wizard["profile"]["name"] != "Smoke Research Pilot":
        raise RuntimeError("project setup wizard did not save the profile")
    if "Project Setup Wizard" not in setup_wizard["markdown_export"]:
        raise RuntimeError("project setup wizard markdown did not include title")
    setup_checklist = {item["id"]: item for item in setup_wizard["readiness"]["checklist"]}
    if setup_checklist["profile"]["status"] != "done":
        raise RuntimeError("project setup wizard did not satisfy the profile readiness check")
    onboarding_tasks = require_ok(
        client.post(
            "/research/onboarding/tasks",
            json_body={"limit": 6, "include_optional": True, "created_by": "smoke_api"},
        ),
        "project onboarding tasks",
    )
    if not onboarding_tasks["tasks"]:
        raise RuntimeError("project onboarding task generation returned no tasks")
    if onboarding_tasks["tasks"][0]["owner_type"] != "project_onboarding":
        raise RuntimeError("project onboarding tasks used the wrong owner type")
    onboarding_task_edges = require_ok(
        client.get("/research/graph/edges?edge_type=project_onboarding_creates_task"),
        "project onboarding task graph edges",
    )
    if not onboarding_task_edges:
        raise RuntimeError("project onboarding task generation did not create graph edges")
    onboarding_progress = require_ok(
        client.get("/research/onboarding/progress"),
        "project onboarding progress",
    )
    if onboarding_progress["task_summary"]["task_count"] < len(onboarding_tasks["tasks"]):
        raise RuntimeError("project onboarding progress did not include onboarding tasks")
    if "Project Onboarding Progress" not in onboarding_progress["markdown_export"]:
        raise RuntimeError("project onboarding progress markdown did not include title")
    if not onboarding_progress["next_action"]:
        raise RuntimeError("project onboarding progress did not include a next action")
    pilot_report = require_ok(
        client.get("/research/pilot/report"),
        "project pilot report",
    )
    if "Project Pilot Status Report" not in pilot_report["markdown_export"]:
        raise RuntimeError("project pilot report markdown did not include title")
    if not pilot_report["executive_summary"]:
        raise RuntimeError("project pilot report did not include executive summary")
    if not pilot_report["next_actions"]:
        raise RuntimeError("project pilot report did not include next actions")
    if pilot_report["key_metrics"].get("readiness_level") != pilot_report["readiness_level"]:
        raise RuntimeError("project pilot report key metrics did not include readiness level")
    pilot_report_snapshot = require_ok(
        client.post(
            "/research/pilot/report/snapshots",
            json_body={
                "title": "Smoke Pilot Status Report",
                "created_by": "smoke_api",
            },
        ),
        "project pilot report snapshot",
    )
    if pilot_report_snapshot["scope"] != "pilot_report":
        raise RuntimeError("project pilot report snapshot used the wrong scope")
    if "Project Pilot Status Report" not in pilot_report_snapshot["markdown_export"]:
        raise RuntimeError("project pilot report snapshot markdown did not include title")
    pilot_report_snapshots = require_ok(
        client.get("/research/pilot/report/snapshots"),
        "project pilot report snapshot list",
    )
    if not any(item["id"] == pilot_report_snapshot["id"] for item in pilot_report_snapshots):
        raise RuntimeError("project pilot report snapshot list did not include new snapshot")
    fetched_pilot_report_snapshot = require_ok(
        client.get(f"/research/pilot/report/snapshots/{pilot_report_snapshot['id']}"),
        "project pilot report snapshot detail",
    )
    if fetched_pilot_report_snapshot["id"] != pilot_report_snapshot["id"]:
        raise RuntimeError("project pilot report snapshot detail returned the wrong snapshot")
    pilot_report_snapshot_markdown = require_ok(
        client.get(
            f"/research/pilot/report/snapshots/{pilot_report_snapshot['id']}/export/markdown"
        ),
        "project pilot report snapshot markdown export",
    )
    if "Project Pilot Status Report" not in pilot_report_snapshot_markdown:
        raise RuntimeError("project pilot report snapshot export did not include title")
    pilot_report_snapshot_tasks = require_ok(
        client.post(
            f"/research/pilot/report/snapshots/{pilot_report_snapshot['id']}/tasks",
            json_body={
                "limit": 6,
                "include_risks": True,
                "include_next_actions": True,
                "include_quick_actions": True,
                "created_by": "smoke_api",
            },
        ),
        "project pilot report snapshot tasks",
    )
    if not pilot_report_snapshot_tasks["tasks"]:
        raise RuntimeError("project pilot report snapshot task generation returned no tasks")
    if pilot_report_snapshot_tasks["tasks"][0]["owner_id"] != pilot_report_snapshot["id"]:
        raise RuntimeError("project pilot report snapshot task owner did not match snapshot")
    candidate_pilot_report_snapshot = require_ok(
        client.post(
            "/research/pilot/report/snapshots",
            json_body={
                "title": "Smoke Pilot Status Report Candidate",
                "created_by": "smoke_api",
            },
        ),
        "candidate project pilot report snapshot",
    )
    pilot_report_snapshot_comparison = require_ok(
        client.post(
            "/research/pilot/report/snapshots/compare",
            json_body={
                "baseline_snapshot_id": pilot_report_snapshot["id"],
                "candidate_snapshot_id": candidate_pilot_report_snapshot["id"],
            },
        ),
        "project pilot report snapshot comparison",
    )
    if "Compared pilot report snapshots" not in pilot_report_snapshot_comparison["summary"]:
        raise RuntimeError("project pilot report snapshot comparison summary was incomplete")
    pilot_report_snapshot_comparison_markdown = require_ok(
        client.post(
            "/research/pilot/report/snapshots/compare/export/markdown",
            json_body={
                "baseline_snapshot_id": pilot_report_snapshot["id"],
                "candidate_snapshot_id": candidate_pilot_report_snapshot["id"],
            },
        ),
        "project pilot report snapshot comparison markdown export",
    )
    if "Project Pilot Report Snapshot Comparison" not in pilot_report_snapshot_comparison_markdown:
        raise RuntimeError("project pilot report snapshot comparison export missing title")
    pilot_report_snapshot_comparison_tasks = require_ok(
        client.post(
            "/research/pilot/report/snapshots/compare/tasks",
            json_body={
                "baseline_snapshot_id": pilot_report_snapshot["id"],
                "candidate_snapshot_id": candidate_pilot_report_snapshot["id"],
                "limit": 6,
                "include_risks": True,
                "include_next_actions": True,
                "include_quick_actions": True,
                "created_by": "smoke_api",
            },
        ),
        "project pilot report snapshot comparison tasks",
    )
    if not pilot_report_snapshot_comparison_tasks["tasks"]:
        raise RuntimeError(
            "project pilot report snapshot comparison task generation returned no tasks"
        )
    if (
        pilot_report_snapshot_comparison_tasks["tasks"][0]["owner_id"]
        != candidate_pilot_report_snapshot["id"]
    ):
        raise RuntimeError(
            "project pilot report snapshot comparison task owner did not match candidate"
        )
    onboarding_start = require_ok(
        client.get("/research/onboarding/readiness"),
        "project onboarding readiness",
    )
    if "Project Onboarding Readiness" not in onboarding_start["markdown_export"]:
        raise RuntimeError("project onboarding readiness markdown did not include title")
    if not onboarding_start["checklist"]:
        raise RuntimeError("project onboarding readiness did not include checklist")

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
    novelty_refresh = require_ok(
        client.post(
            f"/research/ideas/{refined_idea['id']}/novelty-refresh",
            json_body={
                "include_external": True,
                "limit": 5,
                "query_override": "recent preprint collision search",
            },
        ),
        "idea novelty refresh",
    )
    if novelty_refresh["status"] != "completed_external_novelty_refresh":
        raise RuntimeError("novelty refresh did not use refresh status")
    if "novelty_mode:external_refresh" not in novelty_refresh["checked_sources"]:
        raise RuntimeError("novelty refresh did not record refresh mode")
    novelty_tasks = require_ok(
        client.post(
            f"/research/ideas/{refined_idea['id']}/novelty-checks/{novelty_refresh['id']}/tasks",
            json_body={"created_by": "smoke_api"},
        ),
        "novelty check tasks",
    )
    if not novelty_tasks["tasks"]:
        raise RuntimeError("novelty refresh did not create follow-up tasks")
    if novelty_tasks["tasks"][0]["owner_type"] != "novelty_check":
        raise RuntimeError("novelty task used the wrong owner type")
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
    evidence_ledger = require_ok(
        client.post(
            f"/research/ideas/{refined_idea['id']}/evidence-ledger",
            json_body={"created_by": "smoke_api"},
        ),
        "idea evidence ledger",
    )
    evidence_ledger_markdown = require_ok(
        client.get(
            f"/research/ideas/{refined_idea['id']}/evidence-ledgers/{evidence_ledger['id']}/export/markdown"
        ),
        "idea evidence ledger markdown",
    )
    if not evidence_ledger["claims"]:
        raise RuntimeError("idea evidence ledger returned no claims")
    if "## Missing Evidence" not in evidence_ledger_markdown:
        raise RuntimeError("idea evidence ledger markdown did not include missing evidence")
    evidence_tasks = require_ok(
        client.post(
            f"/research/ideas/{refined_idea['id']}/evidence-ledgers/{evidence_ledger['id']}/tasks",
            json_body={"created_by": "smoke_api"},
        ),
        "idea evidence ledger tasks",
    )
    if not evidence_tasks["tasks"]:
        raise RuntimeError("idea evidence ledger task generation returned no tasks")
    if evidence_tasks["tasks"][0]["owner_type"] != "idea_evidence_ledger":
        raise RuntimeError("idea evidence ledger tasks used the wrong owner type")
    if evidence_tasks["tasks"][0]["due_phase"] != "evidence_follow_up":
        raise RuntimeError("idea evidence ledger tasks used the wrong due phase")
    claim_id = evidence_ledger["claims"][0]["claim_id"]
    claim_packet = require_ok(
        client.get(
            f"/research/ideas/{refined_idea['id']}/evidence-ledgers/"
            f"{evidence_ledger['id']}/claims/{claim_id}/validation-packet"
        ),
        "claim validation packet",
    )
    if claim_packet["claim"]["claim_id"] != claim_id:
        raise RuntimeError("claim validation packet returned the wrong claim")
    if not claim_packet["supporting_evidence"]:
        raise RuntimeError("claim validation packet did not include supporting evidence")
    if not claim_packet["validation_actions"]:
        raise RuntimeError("claim validation packet did not include validation actions")
    if "Claim Validation Packet" not in claim_packet["markdown_export"]:
        raise RuntimeError("claim validation packet markdown did not include title")
    claim_queue = require_ok(
        client.get(f"/research/claims/validation-queue?idea_id={refined_idea['id']}&limit=20"),
        "claim validation queue",
    )
    if not claim_queue["items"]:
        raise RuntimeError("claim validation queue returned no items")
    if claim_queue["summary"]["item_count"] != len(claim_queue["items"]):
        raise RuntimeError("claim validation queue summary count did not match items")
    if not any(
        item["ledger_id"] == evidence_ledger["id"] and item["claim_id"] == claim_id
        for item in claim_queue["items"]
    ):
        raise RuntimeError("claim validation queue did not include the smoke ledger claim")
    if "Claim Validation Queue" not in claim_queue["markdown_export"]:
        raise RuntimeError("claim validation queue markdown did not include title")
    claim_queue_tasks = require_ok(
        client.post(
            "/research/claims/validation-queue/tasks",
            json_body={
                "idea_id": refined_idea["id"],
                "limit": 3,
                "priority_filter": ["critical", "high"],
                "created_by": "smoke_api",
            },
        ),
        "claim validation queue tasks",
    )
    if not claim_queue_tasks["tasks"]:
        raise RuntimeError("claim validation queue task generation returned no tasks")
    if claim_queue_tasks["tasks"][0]["owner_type"] != "claim_validation_queue":
        raise RuntimeError("claim validation queue tasks used the wrong owner type")
    if claim_queue_tasks["tasks"][0]["due_phase"] != "claim_validation_follow_up":
        raise RuntimeError("claim validation queue tasks used the wrong due phase")
    proposal_graph_edges = require_ok(
        client.get("/research/graph/edges?edge_type=proposal_revision_creates_task"),
        "proposal task graph edges",
    )
    if not proposal_graph_edges:
        raise RuntimeError("proposal revision task graph edges were not created")
    ledger_graph_edges = require_ok(
        client.get("/research/graph/edges?edge_type=idea_has_evidence_ledger"),
        "evidence ledger graph edges",
    )
    if not ledger_graph_edges:
        raise RuntimeError("idea evidence ledger graph edges were not created")
    claim_graph_edges = require_ok(
        client.get("/research/graph/edges?edge_type=evidence_ledger_tracks_claim"),
        "claim tracking graph edges",
    )
    if not claim_graph_edges:
        raise RuntimeError("evidence ledger claim graph edges were not created")
    ledger_task_edges = require_ok(
        client.get("/research/graph/edges?edge_type=evidence_ledger_creates_task"),
        "evidence ledger task graph edges",
    )
    if not ledger_task_edges:
        raise RuntimeError("evidence ledger task graph edges were not created")
    claim_queue_task_edges = require_ok(
        client.get("/research/graph/edges?edge_type=claim_validation_queue_creates_task"),
        "claim validation queue task graph edges",
    )
    if not claim_queue_task_edges:
        raise RuntimeError("claim validation queue task graph edges were not created")
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
    lineage_task_ids = {task["id"] for task in lineage["research_tasks"]}
    if analysis_tasks["tasks"][0]["id"] not in lineage_task_ids:
        raise RuntimeError("idea lineage did not include experiment analysis task")
    if decision_tasks["tasks"][0]["id"] not in lineage_task_ids:
        raise RuntimeError("idea lineage did not include decision memo task")
    if evidence_tasks["tasks"][0]["id"] not in lineage_task_ids:
        raise RuntimeError("idea lineage did not include evidence ledger task")
    if claim_queue_tasks["tasks"][0]["id"] not in lineage_task_ids:
        raise RuntimeError("idea lineage did not include claim validation queue task")
    if lineage["graph_edge_summary"].get("claim_validation_queue_creates_task", 0) < 1:
        raise RuntimeError("idea lineage did not summarize claim validation queue task edges")
    if assumption_audit["id"] not in lineage["markdown_export"]:
        raise RuntimeError("idea lineage markdown did not include assumption audit")
    if evidence_ledger["id"] not in lineage["markdown_export"]:
        raise RuntimeError("idea lineage markdown did not include evidence ledger")
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
    if progress["artifact_counts"]["evidence_ledgers"] < 1:
        raise RuntimeError("idea progress did not count evidence ledgers")
    if progress["artifact_counts"]["evidence_follow_up_tasks"] < 1:
        raise RuntimeError("idea progress did not count evidence follow-up tasks")
    if progress["artifact_counts"].get("claim_validation_follow_up_tasks", 0) < 1:
        raise RuntimeError("idea progress did not count claim validation follow-up tasks")
    if progress["latest_artifacts"]["evidence_ledger"]["id"] != evidence_ledger["id"]:
        raise RuntimeError("idea progress did not expose latest evidence ledger")
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
    if evidence_ledger["id"] not in research_packet["markdown_export"]:
        raise RuntimeError("idea research packet markdown did not include evidence ledger")
    if evidence_tasks["tasks"][0]["id"] not in research_packet["markdown_export"]:
        raise RuntimeError("idea research packet markdown did not include evidence ledger task")
    if claim_queue_tasks["tasks"][0]["id"] not in research_packet["markdown_export"]:
        raise RuntimeError("idea research packet markdown did not include claim queue task")
    claim_validation_result = require_ok(
        client.post(
            f"/research/tasks/{claim_queue_tasks['tasks'][0]['id']}/claim-validation-result",
            json_body={
                "validation_status": "needs_more_evidence",
                "evidence_ids": [claim_packet["supporting_evidence"][0]["id"]],
                "notes": "Smoke result: claim needs one more independent support source.",
                "next_action": "Run a targeted validation search for this claim.",
                "created_by": "smoke_api",
            },
        ),
        "claim validation result",
    )
    if claim_validation_result["event_type"] != "claim_validation_result":
        raise RuntimeError("claim validation result used the wrong event type")
    if claim_validation_result["metadata"]["validation_status"] != "needs_more_evidence":
        raise RuntimeError("claim validation result did not persist the validation status")
    claim_validation_task_after_result = require_ok(
        client.get(f"/research/tasks/{claim_queue_tasks['tasks'][0]['id']}"),
        "claim validation task after result",
    )
    if claim_validation_task_after_result["status"] != "done":
        raise RuntimeError("claim validation result did not mark the task done")
    claim_validation_task_events = require_ok(
        client.get(f"/research/tasks/{claim_queue_tasks['tasks'][0]['id']}/events"),
        "claim validation task events",
    )
    if "claim_validation_result" not in {
        event["event_type"] for event in claim_validation_task_events
    }:
        raise RuntimeError("claim validation task events did not include result event")
    progress_after_claim_result = require_ok(
        client.get(f"/research/ideas/{refined_idea['id']}/progress"),
        "idea progress after claim validation result",
    )
    if progress_after_claim_result["artifact_counts"].get("claim_validation_result_events", 0) < 1:
        raise RuntimeError("idea progress did not count claim validation result events")
    timeline = require_ok(
        client.get(f"/research/ideas/{refined_idea['id']}/timeline"),
        "idea timeline",
    )
    timeline_event_types = {event["event_type"] for event in timeline["events"]}
    if "experiment_analysis_created" not in timeline_event_types:
        raise RuntimeError("idea timeline did not include experiment analysis events")
    if "decision_memo_created" not in timeline_event_types:
        raise RuntimeError("idea timeline did not include decision memo events")
    if "evidence_ledger_created" not in timeline_event_types:
        raise RuntimeError("idea timeline did not include evidence ledger events")
    if "# Idea Timeline:" not in timeline["markdown_export"]:
        raise RuntimeError("idea timeline markdown did not include title")
    readiness = require_ok(
        client.get(f"/research/ideas/{refined_idea['id']}/readiness"),
        "idea readiness",
    )
    if readiness["readiness_score"] <= 0:
        raise RuntimeError("idea readiness did not return a positive score")
    if "claim_validation" not in readiness["score_breakdown"]:
        raise RuntimeError("idea readiness did not include claim validation signals")
    if (
        readiness["score_breakdown"]["claim_validation"]["by_status"].get("needs_more_evidence", 0)
        < 1
    ):
        raise RuntimeError("idea readiness did not summarize claim validation result statuses")
    if not any("Claim validation found evidence gaps" in item for item in readiness["blockers"]):
        raise RuntimeError("idea readiness did not expose claim validation blockers")
    if "## Score Breakdown" not in readiness["markdown_export"]:
        raise RuntimeError("idea readiness markdown did not include score breakdown")
    quality_gate = require_ok(
        client.get(f"/research/ideas/{refined_idea['id']}/quality-gate"),
        "idea quality gate",
    )
    if quality_gate["gate_score"] < 0:
        raise RuntimeError("idea quality gate returned an invalid score")
    if "claim_validation" not in quality_gate["score_breakdown"]:
        raise RuntimeError("idea quality gate did not include claim validation signals")
    if (
        quality_gate["score_breakdown"]["claim_validation"]["by_status"].get(
            "needs_more_evidence", 0
        )
        < 1
    ):
        raise RuntimeError("idea quality gate did not summarize validation statuses")
    if not any(
        item["name"] == "claim_validation_result" and item["satisfied"]
        for item in quality_gate["required_evidence"]
    ):
        raise RuntimeError("idea quality gate did not require claim validation results")
    if not any(
        "Claim validation found evidence gaps" in item for item in quality_gate["blocking_risks"]
    ):
        raise RuntimeError("idea quality gate did not expose claim validation risks")
    if not quality_gate["recommended_actions"]:
        raise RuntimeError("idea quality gate did not include recommended actions")
    if "Idea Quality Gate" not in quality_gate["markdown_export"]:
        raise RuntimeError("idea quality gate markdown did not include title")
    quality_gate_tasks = require_ok(
        client.post(
            f"/research/ideas/{refined_idea['id']}/quality-gate/tasks",
            json_body={"created_by": "smoke_api"},
        ),
        "idea quality gate tasks",
    )
    if not quality_gate_tasks["tasks"]:
        raise RuntimeError("idea quality gate task generation returned no tasks")
    if quality_gate_tasks["tasks"][0]["owner_type"] != "idea_quality_gate":
        raise RuntimeError("idea quality gate tasks used the wrong owner type")
    progress_after_quality_gate_tasks = require_ok(
        client.get(f"/research/ideas/{refined_idea['id']}/progress"),
        "idea progress after quality gate tasks",
    )
    if (
        progress_after_quality_gate_tasks["artifact_counts"].get(
            "quality_gate_follow_up_tasks",
            0,
        )
        < 1
    ):
        raise RuntimeError("idea progress did not count quality gate follow-up tasks")
    packet_after_quality_gate_tasks = require_ok(
        client.get(f"/research/ideas/{refined_idea['id']}/research-packet"),
        "idea research packet after quality gate tasks",
    )
    if (
        packet_after_quality_gate_tasks["graph_edge_summary"].get(
            "quality_gate_creates_task",
            0,
        )
        < 1
    ):
        raise RuntimeError("research packet did not summarize quality gate task edges")
    readiness_tasks = require_ok(
        client.post(
            f"/research/ideas/{refined_idea['id']}/readiness/tasks",
            json_body={"created_by": "smoke_api"},
        ),
        "idea readiness tasks",
    )
    if not readiness_tasks["tasks"]:
        raise RuntimeError("idea readiness task generation returned no tasks")
    if readiness_tasks["tasks"][0]["owner_type"] != "idea_readiness":
        raise RuntimeError("idea readiness tasks used the wrong owner type")
    progress_after_readiness_tasks = require_ok(
        client.get(f"/research/ideas/{refined_idea['id']}/progress"),
        "idea progress after readiness tasks",
    )
    if progress_after_readiness_tasks["artifact_counts"].get("readiness_follow_up_tasks", 0) < 1:
        raise RuntimeError("idea progress did not count readiness follow-up tasks")
    packet_after_readiness_tasks = require_ok(
        client.get(f"/research/ideas/{refined_idea['id']}/research-packet"),
        "idea research packet after readiness tasks",
    )
    if packet_after_readiness_tasks["graph_edge_summary"].get("idea_readiness_creates_task", 0) < 1:
        raise RuntimeError("research packet did not summarize readiness task edges")
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
            "06-timeline.md",
            "metadata/manifest.json",
            "metadata/timeline.json",
            f"artifacts/evidence-ledgers/evidence-ledger-{evidence_ledger['id']}.md",
        }
        missing_bundle_files = required_bundle_files - bundle_files
        if missing_bundle_files:
            raise RuntimeError(f"idea bundle export missed files: {missing_bundle_files}")
        bundle_manifest = json.loads(archive.read("metadata/manifest.json"))
    if bundle_manifest["idea_id"] != refined_idea["id"]:
        raise RuntimeError("idea bundle manifest returned the wrong idea id")
    if bundle_manifest["timeline_event_count"] < len(timeline["events"]):
        raise RuntimeError("idea bundle manifest did not count timeline events")
    if bundle_manifest["artifact_counts"].get("evidence_ledgers", 0) < 1:
        raise RuntimeError("idea bundle manifest did not count evidence ledgers")
    overview = require_ok(client.get("/research/progress/overview"), "research progress overview")
    if overview["idea_count"] < 1:
        raise RuntimeError("research overview did not include ideas")
    if overview["task_summary"].get("claim_validation_task_count", 0) < 1:
        raise RuntimeError("research overview did not count claim validation tasks")
    if overview["task_summary"].get("claim_validation_result_count", 0) < 1:
        raise RuntimeError("research overview did not count claim validation results")
    if (
        overview["task_summary"]["claim_validation_results"]["by_status"].get(
            "needs_more_evidence", 0
        )
        < 1
    ):
        raise RuntimeError("research overview did not summarize claim validation statuses")
    if "Recent Claim Validation Results" not in overview["markdown_export"]:
        raise RuntimeError("research overview markdown did not include claim validation results")
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
    quality_overview = require_ok(
        client.get("/research/quality/overview?limit=50"),
        "project quality gate overview",
    )
    if quality_overview["idea_count"] < 1:
        raise RuntimeError("project quality gate overview did not include ideas")
    if not quality_overview["decision_counts"]:
        raise RuntimeError("project quality gate overview did not include decision counts")
    if "Project Quality Gate Overview" not in quality_overview["markdown_export"]:
        raise RuntimeError("project quality gate overview markdown did not include title")
    cockpit = require_ok(
        client.get("/research/cockpit?idea_limit=50&opportunity_limit=5"),
        "project cockpit",
    )
    if cockpit["project_metrics"].get("paper_count", 0) < 1:
        raise RuntimeError("project cockpit did not include indexed papers")
    if cockpit["project_metrics"].get("idea_count", 0) < 1:
        raise RuntimeError("project cockpit did not include ideas")
    if cockpit["project_metrics"].get("claim_validation_result_count", 0) < 1:
        raise RuntimeError("project cockpit did not include claim validation results")
    if not cockpit["primary_next_action"].get("label"):
        raise RuntimeError("project cockpit did not include a primary next action")
    if not cockpit["quick_actions"]:
        raise RuntimeError("project cockpit did not include quick actions")
    if not cockpit["workflow_stages"]:
        raise RuntimeError("project cockpit did not include workflow stages")
    if not cockpit["source_summaries"]["quality"]["decision_counts"]:
        raise RuntimeError("project cockpit did not include quality source summary")
    if "Project Cockpit" not in cockpit["markdown_export"]:
        raise RuntimeError("project cockpit markdown did not include title")
    cockpit_markdown = require_ok(
        client.get("/research/cockpit/export/markdown"),
        "project cockpit markdown export",
    )
    if "Project Cockpit" not in cockpit_markdown:
        raise RuntimeError("project cockpit markdown export did not include title")
    onboarding_after_workflow = require_ok(
        client.get("/research/onboarding/readiness"),
        "project onboarding readiness after workflow",
    )
    if onboarding_after_workflow["project_metrics"].get("paper_count", 0) < 1:
        raise RuntimeError("project onboarding readiness did not include indexed papers")
    if onboarding_after_workflow["project_metrics"].get("idea_count", 0) < 1:
        raise RuntimeError("project onboarding readiness did not include ideas")
    if onboarding_after_workflow["required_total"] < 5:
        raise RuntimeError("project onboarding readiness did not include required checks")
    if not onboarding_after_workflow["quick_actions"]:
        raise RuntimeError("project onboarding readiness did not include quick actions")
    advisor_chat = require_ok(
        client.post(
            "/research/advisor/chat",
            json_body={
                "question": "What should I do next, and which evidence risk matters most?",
                "idea_id": refined_idea["id"],
                "paper_ids": [paper_id],
                "include_cockpit": True,
                "include_context": True,
                "context_limit": 5,
                "created_by": "smoke_api",
            },
        ),
        "project advisor chat",
    )
    if not advisor_chat["answer"]:
        raise RuntimeError("advisor chat did not return an answer")
    if not advisor_chat["recommended_actions"]:
        raise RuntimeError("advisor chat did not return recommended actions")
    if not advisor_chat["tool_suggestions"]:
        raise RuntimeError("advisor chat did not return tool suggestions")
    if "Advisor Chat Answer" not in advisor_chat["answer_markdown"]:
        raise RuntimeError("advisor chat markdown did not include title")
    advisor_citation_count = (
        len(advisor_chat["cited_evidences"])
        + len(advisor_chat["cited_gaps"])
        + len(advisor_chat["cited_ideas"])
    )
    if advisor_citation_count < 1:
        raise RuntimeError("advisor chat did not cite any retrieved context")
    advisor_chat_tasks = require_ok(
        client.post(
            "/research/advisor/chat/tasks",
            json_body={
                "question": "What should I do next, and which evidence risk matters most?",
                "idea_id": refined_idea["id"],
                "paper_ids": [paper_id],
                "include_cockpit": True,
                "include_context": True,
                "context_limit": 5,
                "limit": 5,
                "include_recommendations": True,
                "include_risks": True,
                "created_by": "smoke_api",
            },
        ),
        "project advisor chat tasks",
    )
    if not advisor_chat_tasks["tasks"]:
        raise RuntimeError("project advisor chat task generation returned no tasks")
    if advisor_chat_tasks["tasks"][0]["owner_type"] != "project_advisor_chat":
        raise RuntimeError("project advisor chat tasks used the wrong owner type")
    advisor_chat_task_edges = require_ok(
        client.get("/research/graph/edges?edge_type=project_advisor_chat_creates_task"),
        "project advisor chat task graph edges",
    )
    if not advisor_chat_task_edges:
        raise RuntimeError("project advisor chat task generation did not create graph edges")
    advisor_action_session = require_ok(
        client.post(
            "/research/advisor/action-session",
            json_body={
                "question": "Create an execution session for the highest evidence risk.",
                "idea_id": refined_idea["id"],
                "paper_ids": [paper_id],
                "include_cockpit": True,
                "include_context": True,
                "context_limit": 5,
                "limit": 5,
                "include_recommendations": True,
                "include_risks": True,
                "include_tool_suggestions": False,
                "snapshot_title": "Smoke Advisor Action Session",
                "include_snapshot": True,
                "created_by": "smoke_api",
            },
        ),
        "project advisor action session",
    )
    if not advisor_action_session["tasks"]:
        raise RuntimeError("project advisor action session returned no tasks")
    if not advisor_action_session["snapshot"] or not advisor_action_session["snapshot"]["id"]:
        raise RuntimeError("project advisor action session did not create a task snapshot")
    if advisor_action_session["progress_summary"]["task_count"] != len(
        advisor_action_session["tasks"]
    ):
        raise RuntimeError("project advisor action session progress did not match tasks")
    if "Advisor Action Session" not in advisor_action_session["markdown_export"]:
        raise RuntimeError("project advisor action session markdown did not include title")
    cockpit_tasks = require_ok(
        client.post(
            "/research/cockpit/tasks",
            json_body={
                "limit": 5,
                "include_primary_action": True,
                "include_next_actions": True,
                "include_risks": True,
                "created_by": "smoke_api",
            },
        ),
        "project cockpit tasks",
    )
    if not cockpit_tasks["tasks"]:
        raise RuntimeError("project cockpit task generation returned no tasks")
    if cockpit_tasks["tasks"][0]["owner_type"] != "project_cockpit":
        raise RuntimeError("project cockpit tasks used the wrong owner type")
    cockpit_task_edges = require_ok(
        client.get("/research/graph/edges?edge_type=project_cockpit_creates_task"),
        "project cockpit task graph edges",
    )
    if not cockpit_task_edges:
        raise RuntimeError("project cockpit task generation did not create graph edges")
    triage_brief = require_ok(
        client.get("/research/triage/brief?idea_limit=50&opportunity_limit=5"),
        "project triage brief",
    )
    if not triage_brief["next_actions"]:
        raise RuntimeError("project triage brief did not include next actions")
    if "Project Triage Brief" not in triage_brief["markdown_export"]:
        raise RuntimeError("project triage brief markdown did not include title")
    triage_markdown = require_ok(
        client.get("/research/triage/brief/export/markdown"),
        "project triage brief markdown export",
    )
    if "Project Triage Brief" not in triage_markdown:
        raise RuntimeError("project triage brief markdown export did not include title")
    baseline_triage_snapshot = require_ok(
        client.post(
            "/research/triage/snapshots",
            json_body={
                "title": "Smoke Baseline Project Triage Snapshot",
                "idea_limit": 50,
                "opportunity_limit": 5,
                "created_by": "smoke_api",
            },
        ),
        "baseline project triage snapshot",
    )
    if baseline_triage_snapshot["summary"].get("idea_count", 0) < 1:
        raise RuntimeError("baseline project triage snapshot did not include ideas")
    triage_tasks = require_ok(
        client.post(
            "/research/triage/brief/tasks",
            json_body={
                "limit": 5,
                "include_risks": True,
                "created_by": "smoke_api",
            },
        ),
        "project triage tasks",
    )
    if not triage_tasks["tasks"]:
        raise RuntimeError("project triage task generation returned no tasks")
    if triage_tasks["tasks"][0]["owner_type"] != "project_triage":
        raise RuntimeError("project triage tasks used the wrong owner type")
    triage_edges = require_ok(
        client.get("/research/graph/edges?edge_type=project_triage_creates_task"),
        "project triage task graph edges",
    )
    if not triage_edges:
        raise RuntimeError("project triage task generation did not create graph edges")
    triage_snapshot = require_ok(
        client.post(
            "/research/triage/snapshots",
            json_body={
                "title": "Smoke Project Triage Snapshot",
                "idea_limit": 50,
                "opportunity_limit": 5,
                "created_by": "smoke_api",
            },
        ),
        "project triage snapshot",
    )
    if "Project Triage Snapshot" not in triage_snapshot["markdown_export"]:
        raise RuntimeError("project triage snapshot markdown did not include title")
    if triage_snapshot["summary"].get("next_action_count", 0) < 1:
        raise RuntimeError("project triage snapshot did not retain next actions")
    if not triage_snapshot["source_ids"].get("project_triage_task_ids"):
        raise RuntimeError("project triage snapshot did not retain triage task source ids")
    triage_snapshots = require_ok(
        client.get("/research/triage/snapshots?limit=5"),
        "project triage snapshot list",
    )
    if not any(item["id"] == triage_snapshot["id"] for item in triage_snapshots):
        raise RuntimeError("project triage snapshot list did not include the saved snapshot")
    fetched_triage_snapshot = require_ok(
        client.get(f"/research/triage/snapshots/{triage_snapshot['id']}"),
        "project triage snapshot detail",
    )
    if fetched_triage_snapshot["id"] != triage_snapshot["id"]:
        raise RuntimeError("project triage snapshot detail returned the wrong snapshot")
    triage_snapshot_markdown = require_ok(
        client.get(f"/research/triage/snapshots/{triage_snapshot['id']}/export/markdown"),
        "project triage snapshot markdown export",
    )
    if "## Source IDs" not in triage_snapshot_markdown:
        raise RuntimeError("project triage snapshot markdown export missed source ids")
    triage_snapshot_comparison = require_ok(
        client.post(
            "/research/triage/snapshots/compare",
            json_body={
                "baseline_snapshot_id": baseline_triage_snapshot["id"],
                "candidate_snapshot_id": triage_snapshot["id"],
            },
        ),
        "project triage snapshot comparison",
    )
    if "open_task_count" not in triage_snapshot_comparison["metric_delta"]:
        raise RuntimeError("project triage snapshot comparison missed metric deltas")
    if "Compared project triage snapshots" not in triage_snapshot_comparison["summary"]:
        raise RuntimeError("project triage snapshot comparison summary was incomplete")
    triage_snapshot_comparison_markdown = require_ok(
        client.post(
            "/research/triage/snapshots/compare/export/markdown",
            json_body={
                "baseline_snapshot_id": baseline_triage_snapshot["id"],
                "candidate_snapshot_id": triage_snapshot["id"],
            },
        ),
        "project triage snapshot comparison markdown",
    )
    if "## Metric Delta" not in triage_snapshot_comparison_markdown:
        raise RuntimeError("project triage snapshot comparison markdown missed metric deltas")
    triage_comparison_tasks = require_ok(
        client.post(
            "/research/triage/snapshots/compare/tasks",
            json_body={
                "baseline_snapshot_id": baseline_triage_snapshot["id"],
                "candidate_snapshot_id": triage_snapshot["id"],
                "limit": 5,
                "include_focus": True,
                "include_risks": True,
                "created_by": "smoke_api",
            },
        ),
        "project triage snapshot comparison tasks",
    )
    if not triage_comparison_tasks["tasks"]:
        raise RuntimeError("project triage snapshot comparison task generation returned no tasks")
    if triage_comparison_tasks["tasks"][0]["owner_type"] != "project_triage_comparison":
        raise RuntimeError("project triage snapshot comparison tasks used the wrong owner type")
    triage_comparison_edges = require_ok(
        client.get("/research/graph/edges?edge_type=project_triage_comparison_creates_task"),
        "project triage snapshot comparison task graph edges",
    )
    if not triage_comparison_edges:
        raise RuntimeError("project triage snapshot comparison tasks did not create graph edges")
    project_quality_tasks = require_ok(
        client.post(
            "/research/quality/overview/tasks",
            json_body={
                "limit": 3,
                "actions_per_idea": 1,
                "decisions": [
                    "de_risk_novelty",
                    "needs_targeted_revision",
                    "revise_before_investment",
                    "advance_to_execution",
                    "park",
                    "reject",
                ],
                "created_by": "smoke_api",
            },
        ),
        "project quality gate tasks",
    )
    if not project_quality_tasks["tasks"]:
        raise RuntimeError("project quality gate task generation returned no tasks")
    if project_quality_tasks["tasks"][0]["owner_type"] != "idea_quality_gate":
        raise RuntimeError("project quality gate tasks used the wrong owner type")
    radar = require_ok(
        client.get("/research/opportunities/radar?limit=5"),
        "research opportunity radar",
    )
    if not radar["top_opportunities"]:
        raise RuntimeError("research opportunity radar did not include opportunities")
    if not radar["recommended_sequence"]:
        raise RuntimeError("research opportunity radar did not include recommended sequence")
    if "Research Opportunity Radar" not in radar["markdown_export"]:
        raise RuntimeError("research opportunity radar markdown did not include title")
    radar_tasks = require_ok(
        client.post(
            "/research/opportunities/radar/tasks",
            json_body={
                "limit": 3,
                "actions_per_opportunity": 1,
                "created_by": "smoke_api",
            },
        ),
        "research opportunity radar tasks",
    )
    if not radar_tasks["tasks"]:
        raise RuntimeError("research opportunity radar did not create tasks")
    if radar_tasks["tasks"][0]["owner_type"] != "opportunity_radar":
        raise RuntimeError("research opportunity radar task used the wrong owner type")
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
    if (
        advisor_brief["summary"]["triage_snapshot_comparison"]["candidate_snapshot_id"]
        != triage_snapshot["id"]
    ):
        raise RuntimeError("advisor brief did not include latest triage snapshot comparison")
    if advisor_brief["summary"]["triage_signals"].get("comparison_task_count", 0) < 1:
        raise RuntimeError("advisor brief did not include triage comparison task signals")
    if advisor_brief["summary"]["triage_signals"].get("claim_validation_task_count", 0) < 1:
        raise RuntimeError("advisor brief did not include claim validation task signals")
    if advisor_brief["summary"]["evidence_signals"][0]["ledger_id"] != evidence_ledger["id"]:
        raise RuntimeError("advisor brief did not include the latest evidence ledger signal")
    claim_queue_summary = advisor_brief["summary"]["claim_validation_queue"]["summary"]
    if claim_queue_summary["item_count"] < 1:
        raise RuntimeError("advisor brief did not include claim validation queue items")
    if advisor_brief["summary"]["claim_validation_results"].get("event_count", 0) < 1:
        raise RuntimeError("advisor brief did not include claim validation result signals")
    if (
        advisor_brief["summary"]["claim_validation_results"]["by_status"].get(
            "needs_more_evidence", 0
        )
        < 1
    ):
        raise RuntimeError("advisor brief did not summarize claim validation result statuses")
    if not any(
        item["ledger_id"] == evidence_ledger["id"] and item["claim_id"] == claim_id
        for item in advisor_brief["summary"]["claim_validation_queue"]["items"]
    ):
        raise RuntimeError("advisor brief claim validation queue missed the smoke ledger claim")
    if "## Triage Signals" not in advisor_brief_markdown:
        raise RuntimeError("advisor brief markdown did not include triage signals")
    if "## Evidence Signals" not in advisor_brief_markdown:
        raise RuntimeError("advisor brief markdown did not include evidence signals")
    if "## Claim Validation Queue" not in advisor_brief_markdown:
        raise RuntimeError("advisor brief markdown did not include claim validation queue")
    if "## Claim Validation Results" not in advisor_brief_markdown:
        raise RuntimeError("advisor brief markdown did not include claim validation results")
    if "Claim Validation Tasks" not in advisor_brief_markdown:
        raise RuntimeError("advisor brief markdown did not include claim validation task signals")
    if "## Triage Snapshot Changes" not in advisor_brief_markdown:
        raise RuntimeError("advisor brief markdown did not include triage snapshot changes")
    if "## Discussion Prompts" not in advisor_brief_markdown:
        raise RuntimeError("advisor brief markdown did not include discussion prompts")
    research_plan = require_ok(
        client.post(
            "/research/plans",
            json_body={
                "title": "Smoke Research Execution Plan",
                "horizon_days": 14,
                "idea_ids": [refined_idea["id"]],
                "created_by": "smoke_api",
            },
        ),
        "research execution plan",
    )
    research_plan_markdown = require_ok(
        client.get(f"/research/plans/{research_plan['id']}/export/markdown"),
        "research execution plan markdown",
    )
    if "## Plan Items" not in research_plan_markdown:
        raise RuntimeError("research execution plan markdown did not include plan items")
    research_plan_tasks = require_ok(
        client.post(
            f"/research/plans/{research_plan['id']}/tasks",
            json_body={"created_by": "smoke_api"},
        ),
        "research execution plan tasks",
    )
    if not research_plan_tasks["tasks"]:
        raise RuntimeError("research execution plan task generation returned no tasks")
    if research_plan_tasks["tasks"][0]["owner_type"] != "research_plan":
        raise RuntimeError("research execution plan tasks used the wrong owner type")
    research_plan_progress = require_ok(
        client.get(f"/research/plans/{research_plan['id']}/progress"),
        "research execution plan progress",
    )
    if research_plan_progress["task_summary"]["task_count"] != len(research_plan_tasks["tasks"]):
        raise RuntimeError("research plan progress did not count generated plan tasks")
    if "Research Plan Progress" not in research_plan_progress["markdown_export"]:
        raise RuntimeError("research plan progress markdown did not include title")
    plan_advisor_brief = require_ok(
        client.post(
            "/research/briefs",
            json_body={
                "title": "Smoke Plan-Aware Advisor Brief",
                "scope": "idea_set",
                "idea_ids": [refined_idea["id"]],
                "created_by": "smoke_api",
            },
        ),
        "plan-aware advisor research brief",
    )
    if plan_advisor_brief["summary"].get("research_plan_count", 0) < 1:
        raise RuntimeError("advisor brief did not include research plan count")
    if "## Execution Plans" not in plan_advisor_brief["markdown_export"]:
        raise RuntimeError("advisor brief markdown did not include execution plans")
    project_bundle_readiness = require_ok(
        client.get("/research/export/project-bundle/readiness"),
        "project bundle readiness",
    )
    if project_bundle_readiness["readiness_level"] != "delivery_ready":
        raise RuntimeError("project bundle readiness was not delivery-ready")
    if project_bundle_readiness["readiness_score"] != 1.0:
        raise RuntimeError("project bundle readiness score was not complete")
    if project_bundle_readiness["missing_required"]:
        raise RuntimeError("project bundle readiness still had missing required checks")
    if "# Project Bundle Readiness" not in project_bundle_readiness["markdown_export"]:
        raise RuntimeError("project bundle readiness markdown did not include title")
    if not any(
        action["id"] == "export_project_bundle"
        for action in project_bundle_readiness["quick_actions"]
    ):
        raise RuntimeError("project bundle readiness did not include export quick action")
    project_bundle_readiness_manifest = project_bundle_readiness["manifest_summary"]
    if project_bundle_readiness_manifest["triage_snapshot_count"] < 2:
        raise RuntimeError("project bundle readiness missed triage snapshot history")
    if not project_bundle_readiness_manifest["triage_snapshot_comparison_available"]:
        raise RuntimeError("project bundle readiness missed triage comparison")
    if project_bundle_readiness_manifest["pilot_report_snapshot_count"] < 2:
        raise RuntimeError("project bundle readiness missed pilot report history")
    if not project_bundle_readiness_manifest["pilot_report_snapshot_comparison_available"]:
        raise RuntimeError("project bundle readiness missed pilot report comparison")
    if project_bundle_readiness_manifest["claim_validation_queue_count"] < 1:
        raise RuntimeError("project bundle readiness missed claim validation queue")
    if project_bundle_readiness_manifest["research_plan_count"] < 1:
        raise RuntimeError("project bundle readiness missed research plan")
    project_bundle_readiness_tasks = require_ok(
        client.post(
            "/research/export/project-bundle/readiness/tasks",
            json_body={"limit": 6, "include_optional": True, "created_by": "smoke_api"},
        ),
        "project bundle readiness tasks",
    )
    if not project_bundle_readiness_tasks["tasks"]:
        raise RuntimeError("project bundle readiness task generation returned no tasks")
    first_bundle_readiness_task = project_bundle_readiness_tasks["tasks"][0]
    if first_bundle_readiness_task["owner_type"] != "project_bundle_readiness":
        raise RuntimeError("project bundle readiness task used the wrong owner type")
    if first_bundle_readiness_task["due_phase"] != "bundle_handoff_follow_up":
        raise RuntimeError("project bundle readiness task used the wrong due phase")
    if (
        first_bundle_readiness_task["metadata"].get("readiness_level")
        != project_bundle_readiness["readiness_level"]
    ):
        raise RuntimeError("project bundle readiness task missed readiness metadata")
    project_bundle_readiness_task_edges = require_ok(
        client.get("/research/graph/edges?edge_type=project_bundle_readiness_creates_task"),
        "project bundle readiness task graph edges",
    )
    if not project_bundle_readiness_task_edges:
        raise RuntimeError("project bundle readiness tasks did not create graph edges")
    baseline_project_bundle_readiness_snapshot = require_ok(
        client.post(
            "/research/export/project-bundle/readiness/snapshots",
            json_body={
                "title": "Smoke Bundle Readiness Baseline",
                "created_by": "smoke_api",
            },
        ),
        "project bundle readiness baseline snapshot",
    )
    project_bundle_readiness_snapshot = require_ok(
        client.post(
            "/research/export/project-bundle/readiness/snapshots",
            json_body={
                "title": "Smoke Bundle Readiness Candidate",
                "created_by": "smoke_api",
            },
        ),
        "project bundle readiness snapshot",
    )
    if project_bundle_readiness_snapshot["scope"] != "bundle_readiness":
        raise RuntimeError("project bundle readiness snapshot used the wrong scope")
    if (
        project_bundle_readiness_snapshot["summary"]["readiness_level"]
        != project_bundle_readiness["readiness_level"]
    ):
        raise RuntimeError("project bundle readiness snapshot missed readiness level")
    if "# Project Bundle Readiness" not in project_bundle_readiness_snapshot["markdown_export"]:
        raise RuntimeError("project bundle readiness snapshot markdown did not include title")
    bundle_readiness_snapshots = require_ok(
        client.get("/research/export/project-bundle/readiness/snapshots"),
        "project bundle readiness snapshot list",
    )
    if bundle_readiness_snapshots[0]["id"] != project_bundle_readiness_snapshot["id"]:
        raise RuntimeError("project bundle readiness snapshot list did not return latest snapshot")
    fetched_bundle_readiness_snapshot = require_ok(
        client.get(
            "/research/export/project-bundle/readiness/snapshots/"
            f"{project_bundle_readiness_snapshot['id']}"
        ),
        "project bundle readiness snapshot detail",
    )
    if fetched_bundle_readiness_snapshot["id"] != project_bundle_readiness_snapshot["id"]:
        raise RuntimeError("project bundle readiness snapshot detail returned wrong snapshot")
    bundle_readiness_snapshot_markdown = require_ok(
        client.get(
            "/research/export/project-bundle/readiness/snapshots/"
            f"{project_bundle_readiness_snapshot['id']}/export/markdown"
        ),
        "project bundle readiness snapshot markdown",
    )
    if "# Project Bundle Readiness" not in bundle_readiness_snapshot_markdown:
        raise RuntimeError("project bundle readiness snapshot markdown export missed title")
    project_bundle_readiness_snapshot_comparison = require_ok(
        client.post(
            "/research/export/project-bundle/readiness/snapshots/compare",
            json_body={
                "baseline_snapshot_id": baseline_project_bundle_readiness_snapshot["id"],
                "candidate_snapshot_id": project_bundle_readiness_snapshot["id"],
            },
        ),
        "project bundle readiness snapshot comparison",
    )
    if (
        project_bundle_readiness_snapshot_comparison["candidate_snapshot_id"]
        != project_bundle_readiness_snapshot["id"]
    ):
        raise RuntimeError("project bundle readiness snapshot comparison used wrong candidate")
    if (
        "# Project Bundle Readiness Snapshot Comparison"
        not in project_bundle_readiness_snapshot_comparison["markdown_export"]
    ):
        raise RuntimeError("project bundle readiness snapshot comparison markdown missed title")
    bundle_readiness_snapshot_comparison_markdown = require_ok(
        client.post(
            "/research/export/project-bundle/readiness/snapshots/compare/export/markdown",
            json_body={
                "baseline_snapshot_id": baseline_project_bundle_readiness_snapshot["id"],
                "candidate_snapshot_id": project_bundle_readiness_snapshot["id"],
            },
        ),
        "project bundle readiness snapshot comparison markdown",
    )
    if (
        "# Project Bundle Readiness Snapshot Comparison"
        not in bundle_readiness_snapshot_comparison_markdown
    ):
        raise RuntimeError("project bundle readiness comparison markdown export missed title")
    project_bundle_readiness_comparison_tasks = require_ok(
        client.post(
            "/research/export/project-bundle/readiness/snapshots/compare/tasks",
            json_body={
                "baseline_snapshot_id": baseline_project_bundle_readiness_snapshot["id"],
                "candidate_snapshot_id": project_bundle_readiness_snapshot["id"],
                "limit": 6,
                "include_missing_required": True,
                "include_recommended_actions": True,
                "include_quick_actions": True,
                "created_by": "smoke_api",
            },
        ),
        "project bundle readiness comparison tasks",
    )
    if not project_bundle_readiness_comparison_tasks["tasks"]:
        raise RuntimeError("project bundle readiness comparison did not create tasks")
    first_bundle_comparison_task = project_bundle_readiness_comparison_tasks["tasks"][0]
    if first_bundle_comparison_task["owner_type"] != "project_bundle_readiness_snapshot_comparison":
        raise RuntimeError("project bundle readiness comparison task used wrong owner type")
    if first_bundle_comparison_task["due_phase"] != "bundle_readiness_change_follow_up":
        raise RuntimeError("project bundle readiness comparison task used wrong due phase")
    project_bundle_readiness_comparison_task_edges = require_ok(
        client.get(
            "/research/graph/edges?edge_type=project_bundle_readiness_comparison_creates_task"
        ),
        "project bundle readiness comparison task graph edges",
    )
    if not project_bundle_readiness_comparison_task_edges:
        raise RuntimeError("project bundle readiness comparison tasks did not create graph edges")
    project_bundle_release = require_ok(
        client.post(
            "/research/export/project-bundle/releases",
            json_body={
                "title": "Smoke Project Bundle Release",
                "recipient": "smoke advisor",
                "release_notes": "Smoke release note for project bundle handoff.",
                "created_by": "smoke_api",
            },
        ),
        "project bundle release note",
    )
    if project_bundle_release["scope"] != "project_bundle_release":
        raise RuntimeError("project bundle release note used wrong scope")
    if project_bundle_release["summary"]["recipient"] != "smoke advisor":
        raise RuntimeError("project bundle release note missed recipient")
    if "# Project Bundle Release Note" not in project_bundle_release["markdown_export"]:
        raise RuntimeError("project bundle release note markdown missed title")
    project_bundle_releases = require_ok(
        client.get("/research/export/project-bundle/releases"),
        "project bundle release note list",
    )
    if project_bundle_releases[0]["id"] != project_bundle_release["id"]:
        raise RuntimeError("project bundle release note list did not return latest release")
    fetched_project_bundle_release = require_ok(
        client.get(f"/research/export/project-bundle/releases/{project_bundle_release['id']}"),
        "project bundle release note detail",
    )
    if fetched_project_bundle_release["id"] != project_bundle_release["id"]:
        raise RuntimeError("project bundle release note detail returned wrong note")
    project_bundle_release_markdown = require_ok(
        client.get(
            "/research/export/project-bundle/releases/"
            f"{project_bundle_release['id']}/export/markdown"
        ),
        "project bundle release note markdown",
    )
    if "# Project Bundle Release Note" not in project_bundle_release_markdown:
        raise RuntimeError("project bundle release note markdown export missed title")
    project_bundle_release_tasks = require_ok(
        client.post(
            f"/research/export/project-bundle/releases/{project_bundle_release['id']}/tasks",
            json_body={
                "limit": 6,
                "include_missing_required": True,
                "include_handoff_checks": True,
                "created_by": "smoke_api",
            },
        ),
        "project bundle release note tasks",
    )
    if not project_bundle_release_tasks["tasks"]:
        raise RuntimeError("project bundle release note did not create tasks")
    first_release_task = project_bundle_release_tasks["tasks"][0]
    if first_release_task["owner_type"] != "project_bundle_release":
        raise RuntimeError("project bundle release task used wrong owner type")
    if first_release_task["due_phase"] != "project_bundle_release_follow_up":
        raise RuntimeError("project bundle release task used wrong due phase")
    project_bundle_release_task_edges = require_ok(
        client.get("/research/graph/edges?edge_type=project_bundle_release_creates_task"),
        "project bundle release task graph edges",
    )
    if not project_bundle_release_task_edges:
        raise RuntimeError("project bundle release tasks did not create graph edges")
    project_bundle_release_progress = require_ok(
        client.get(
            f"/research/export/project-bundle/releases/{project_bundle_release['id']}/progress"
        ),
        "project bundle release progress",
    )
    if project_bundle_release_progress["release_id"] != project_bundle_release["id"]:
        raise RuntimeError("project bundle release progress used wrong release id")
    if project_bundle_release_progress["task_summary"]["task_count"] < len(
        project_bundle_release_tasks["tasks"]
    ):
        raise RuntimeError("project bundle release progress missed generated tasks")
    if project_bundle_release_progress["task_summary"]["open_task_count"] < 1:
        raise RuntimeError("project bundle release progress did not count open tasks")
    if (
        "# Project Bundle Release Progress"
        not in project_bundle_release_progress["markdown_export"]
    ):
        raise RuntimeError("project bundle release progress markdown missed title")
    project_bundle_release_feedback = require_ok(
        client.post(
            f"/research/export/project-bundle/releases/{project_bundle_release['id']}/feedback",
            json_body={
                "title": "Smoke Project Bundle Release Feedback",
                "recipient": "smoke advisor",
                "feedback_status": "changes_requested",
                "signoff_confirmed": False,
                "feedback_notes": "Smoke feedback captured after release handoff.",
                "requested_changes": [
                    "Clarify release closeout ownership.",
                    "Summarize unresolved claim risks.",
                ],
                "blockers": ["Smoke advisor signoff remains pending."],
                "accepted_artifacts": ["README.md", "metadata/manifest.json"],
                "created_by": "smoke_api",
            },
        ),
        "project bundle release feedback",
    )
    if project_bundle_release_feedback["scope"] != "project_bundle_release_feedback":
        raise RuntimeError("project bundle release feedback used wrong scope")
    if project_bundle_release_feedback["summary"]["release_id"] != project_bundle_release["id"]:
        raise RuntimeError("project bundle release feedback used wrong release id")
    if project_bundle_release_feedback["summary"]["feedback_status"] != "changes_requested":
        raise RuntimeError("project bundle release feedback missed status")
    if (
        "# Project Bundle Release Feedback"
        not in project_bundle_release_feedback["markdown_export"]
    ):
        raise RuntimeError("project bundle release feedback markdown missed title")
    project_bundle_release_feedback_list = require_ok(
        client.get(
            f"/research/export/project-bundle/releases/{project_bundle_release['id']}/feedback"
        ),
        "project bundle release feedback list",
    )
    if project_bundle_release_feedback_list[0]["id"] != project_bundle_release_feedback["id"]:
        raise RuntimeError("project bundle release feedback list did not return latest feedback")
    fetched_project_bundle_release_feedback = require_ok(
        client.get(
            "/research/export/project-bundle/releases/"
            f"{project_bundle_release['id']}/feedback/{project_bundle_release_feedback['id']}"
        ),
        "project bundle release feedback detail",
    )
    if fetched_project_bundle_release_feedback["id"] != project_bundle_release_feedback["id"]:
        raise RuntimeError("project bundle release feedback detail returned wrong record")
    project_bundle_release_feedback_markdown = require_ok(
        client.get(
            "/research/export/project-bundle/releases/"
            f"{project_bundle_release['id']}/feedback/"
            f"{project_bundle_release_feedback['id']}/export/markdown"
        ),
        "project bundle release feedback markdown",
    )
    if "# Project Bundle Release Feedback" not in project_bundle_release_feedback_markdown:
        raise RuntimeError("project bundle release feedback markdown export missed title")
    project_bundle_release_feedback_tasks = require_ok(
        client.post(
            "/research/export/project-bundle/releases/"
            f"{project_bundle_release['id']}/feedback/"
            f"{project_bundle_release_feedback['id']}/tasks",
            json_body={
                "limit": 6,
                "include_requested_changes": True,
                "include_blockers": True,
                "include_signoff_check": True,
                "created_by": "smoke_api",
            },
        ),
        "project bundle release feedback tasks",
    )
    if not project_bundle_release_feedback_tasks["tasks"]:
        raise RuntimeError("project bundle release feedback did not create tasks")
    first_feedback_task = project_bundle_release_feedback_tasks["tasks"][0]
    if first_feedback_task["owner_type"] != "project_bundle_release_feedback":
        raise RuntimeError("project bundle release feedback task used wrong owner type")
    if first_feedback_task["due_phase"] != "project_bundle_release_feedback_follow_up":
        raise RuntimeError("project bundle release feedback task used wrong due phase")
    project_bundle_release_feedback_edges = require_ok(
        client.get("/research/graph/edges?edge_type=project_bundle_release_has_feedback"),
        "project bundle release feedback graph edges",
    )
    if not project_bundle_release_feedback_edges:
        raise RuntimeError("project bundle release feedback did not create graph edge")
    project_bundle_release_feedback_task_edges = require_ok(
        client.get("/research/graph/edges?edge_type=project_bundle_release_feedback_creates_task"),
        "project bundle release feedback task graph edges",
    )
    if not project_bundle_release_feedback_task_edges:
        raise RuntimeError("project bundle release feedback tasks did not create graph edges")
    project_bundle_release_closeout = require_ok(
        client.get(
            f"/research/export/project-bundle/releases/{project_bundle_release['id']}/closeout"
        ),
        "project bundle release closeout",
    )
    if project_bundle_release_closeout["release_id"] != project_bundle_release["id"]:
        raise RuntimeError("project bundle release closeout used wrong release id")
    if project_bundle_release_closeout["closeout_status"] != "blocked":
        raise RuntimeError("project bundle release closeout missed blocked status")
    if project_bundle_release_closeout["ready_to_close"]:
        raise RuntimeError("project bundle release closeout should not be ready")
    if (
        project_bundle_release_closeout["latest_feedback"]["id"]
        != project_bundle_release_feedback["id"]
    ):
        raise RuntimeError("project bundle release closeout missed latest feedback")
    if project_bundle_release_closeout["feedback_task_summary"]["task_count"] < len(
        project_bundle_release_feedback_tasks["tasks"]
    ):
        raise RuntimeError("project bundle release closeout missed feedback tasks")
    if (
        "# Project Bundle Release Closeout"
        not in project_bundle_release_closeout["markdown_export"]
    ):
        raise RuntimeError("project bundle release closeout markdown missed title")
    project_bundle_release_closeout_tasks = require_ok(
        client.post(
            "/research/export/project-bundle/releases/"
            f"{project_bundle_release['id']}/closeout/tasks",
            json_body={
                "limit": 6,
                "include_blockers": True,
                "include_next_actions": True,
                "include_signoff_check": True,
                "created_by": "smoke_api",
            },
        ),
        "project bundle release closeout tasks",
    )
    if not project_bundle_release_closeout_tasks["tasks"]:
        raise RuntimeError("project bundle release closeout did not create tasks")
    first_closeout_task = project_bundle_release_closeout_tasks["tasks"][0]
    if first_closeout_task["owner_type"] != "project_bundle_release_closeout":
        raise RuntimeError("project bundle release closeout task used wrong owner type")
    if first_closeout_task["due_phase"] != "project_bundle_release_closeout_follow_up":
        raise RuntimeError("project bundle release closeout task used wrong due phase")
    project_bundle_release_closeout_edges = require_ok(
        client.get("/research/graph/edges?edge_type=project_bundle_release_has_closeout"),
        "project bundle release closeout graph edges",
    )
    if not project_bundle_release_closeout_edges:
        raise RuntimeError("project bundle release closeout did not create graph edge")
    project_bundle_release_closeout_task_edges = require_ok(
        client.get("/research/graph/edges?edge_type=project_bundle_release_closeout_creates_task"),
        "project bundle release closeout task graph edges",
    )
    if not project_bundle_release_closeout_task_edges:
        raise RuntimeError("project bundle release closeout tasks did not create graph edges")
    project_bundle_release_acceptance_packet = require_ok(
        client.get(
            "/research/export/project-bundle/releases/"
            f"{project_bundle_release['id']}/acceptance-packet"
        ),
        "project bundle release acceptance packet",
    )
    if project_bundle_release_acceptance_packet["release_id"] != project_bundle_release["id"]:
        raise RuntimeError("project bundle release acceptance packet used wrong release id")
    if project_bundle_release_acceptance_packet["acceptance_status"] != "blocked":
        raise RuntimeError("project bundle release acceptance packet missed blocked status")
    if project_bundle_release_acceptance_packet["ready_for_signoff"]:
        raise RuntimeError("project bundle release acceptance packet should not be ready")
    if not project_bundle_release_acceptance_packet["open_closeout_tasks"]:
        raise RuntimeError("project bundle release acceptance packet missed closeout tasks")
    if (
        "# Project Bundle Release Acceptance Packet"
        not in project_bundle_release_acceptance_packet["markdown_export"]
    ):
        raise RuntimeError("project bundle release acceptance markdown missed title")
    baseline_project_bundle_release_acceptance_snapshot = require_ok(
        client.post(
            "/research/export/project-bundle/releases/"
            f"{project_bundle_release['id']}/acceptance-packet/snapshots",
            json_body={
                "title": "Smoke Baseline Project Bundle Release Acceptance Snapshot",
                "created_by": "smoke",
            },
        ),
        "baseline project bundle release acceptance snapshot",
    )
    project_bundle_release_acceptance_snapshot = require_ok(
        client.post(
            "/research/export/project-bundle/releases/"
            f"{project_bundle_release['id']}/acceptance-packet/snapshots",
            json_body={
                "title": "Smoke Project Bundle Release Acceptance Snapshot",
                "created_by": "smoke",
            },
        ),
        "project bundle release acceptance snapshot",
    )
    if (
        project_bundle_release_acceptance_snapshot["scope"]
        != "project_bundle_release_acceptance_packet"
    ):
        raise RuntimeError("project bundle release acceptance snapshot used wrong scope")
    if (
        project_bundle_release_acceptance_snapshot["summary"]["release_id"]
        != project_bundle_release["id"]
    ):
        raise RuntimeError("project bundle release acceptance snapshot used wrong release id")
    if project_bundle_release_acceptance_snapshot["summary"]["acceptance_status"] != "blocked":
        raise RuntimeError("project bundle release acceptance snapshot missed blocked status")
    if project_bundle_release_acceptance_snapshot["summary"]["ready_for_signoff"]:
        raise RuntimeError("project bundle release acceptance snapshot should not be ready")
    if (
        "# Project Bundle Release Acceptance Packet"
        not in project_bundle_release_acceptance_snapshot["markdown_export"]
    ):
        raise RuntimeError("project bundle release acceptance snapshot markdown missed title")
    project_bundle_release_acceptance_snapshots = require_ok(
        client.get(
            "/research/export/project-bundle/releases/"
            f"{project_bundle_release['id']}/acceptance-packet/snapshots?limit=5"
        ),
        "project bundle release acceptance snapshot list",
    )
    if (
        not project_bundle_release_acceptance_snapshots
        or project_bundle_release_acceptance_snapshots[0]["id"]
        != project_bundle_release_acceptance_snapshot["id"]
    ):
        raise RuntimeError("project bundle release acceptance snapshot list order was wrong")
    project_bundle_release_acceptance_snapshot_detail = require_ok(
        client.get(
            "/research/export/project-bundle/releases/"
            f"{project_bundle_release['id']}/acceptance-packet/snapshots/"
            f"{project_bundle_release_acceptance_snapshot['id']}"
        ),
        "project bundle release acceptance snapshot detail",
    )
    if (
        project_bundle_release_acceptance_snapshot_detail["id"]
        != project_bundle_release_acceptance_snapshot["id"]
    ):
        raise RuntimeError("project bundle release acceptance snapshot detail used wrong id")
    project_bundle_release_acceptance_snapshot_markdown = client.get(
        "/research/export/project-bundle/releases/"
        f"{project_bundle_release['id']}/acceptance-packet/snapshots/"
        f"{project_bundle_release_acceptance_snapshot['id']}/export/markdown"
    )
    if project_bundle_release_acceptance_snapshot_markdown.status_code != 200:
        raise RuntimeError("project bundle release acceptance snapshot markdown export failed")
    if (
        "# Project Bundle Release Acceptance Packet"
        not in project_bundle_release_acceptance_snapshot_markdown.json()
    ):
        raise RuntimeError("project bundle release acceptance snapshot export missed title")
    project_bundle_release_acceptance_snapshot_edges = require_ok(
        client.get("/research/graph/edges?edge_type=project_bundle_release_has_acceptance_packet"),
        "project bundle release acceptance snapshot graph edges",
    )
    if not project_bundle_release_acceptance_snapshot_edges:
        raise RuntimeError("project bundle release acceptance snapshot did not create graph edge")
    project_bundle_release_acceptance_snapshot_comparison = require_ok(
        client.post(
            "/research/export/project-bundle/releases/"
            f"{project_bundle_release['id']}/acceptance-packet/snapshots/compare",
            json_body={
                "baseline_snapshot_id": baseline_project_bundle_release_acceptance_snapshot["id"],
                "candidate_snapshot_id": project_bundle_release_acceptance_snapshot["id"],
            },
        ),
        "project bundle release acceptance snapshot comparison",
    )
    if (
        project_bundle_release_acceptance_snapshot_comparison["baseline_snapshot_id"]
        != baseline_project_bundle_release_acceptance_snapshot["id"]
    ):
        raise RuntimeError("project bundle acceptance comparison used wrong baseline")
    if (
        project_bundle_release_acceptance_snapshot_comparison["candidate_snapshot_id"]
        != project_bundle_release_acceptance_snapshot["id"]
    ):
        raise RuntimeError("project bundle acceptance comparison used wrong candidate")
    if (
        project_bundle_release_acceptance_snapshot_comparison["release_id"]
        != project_bundle_release["id"]
    ):
        raise RuntimeError("project bundle acceptance comparison used wrong release id")
    if (
        project_bundle_release_acceptance_snapshot_comparison["status_delta"]["candidate"]
        != "blocked"
    ):
        raise RuntimeError("project bundle acceptance comparison missed candidate status")
    if (
        "# Project Bundle Release Acceptance Snapshot Comparison"
        not in project_bundle_release_acceptance_snapshot_comparison["markdown_export"]
    ):
        raise RuntimeError("project bundle acceptance comparison markdown missed title")
    project_bundle_release_acceptance_snapshot_comparison_markdown = client.post(
        "/research/export/project-bundle/releases/"
        f"{project_bundle_release['id']}/acceptance-packet/snapshots/compare/export/markdown",
        json_body={
            "baseline_snapshot_id": baseline_project_bundle_release_acceptance_snapshot["id"],
            "candidate_snapshot_id": project_bundle_release_acceptance_snapshot["id"],
        },
    )
    if project_bundle_release_acceptance_snapshot_comparison_markdown.status_code != 200:
        raise RuntimeError("project bundle acceptance comparison markdown export failed")
    if (
        "# Project Bundle Release Acceptance Snapshot Comparison"
        not in project_bundle_release_acceptance_snapshot_comparison_markdown.json()
    ):
        raise RuntimeError("project bundle acceptance comparison export missed title")
    project_bundle_release_acceptance_snapshot_comparison_tasks = require_ok(
        client.post(
            "/research/export/project-bundle/releases/"
            f"{project_bundle_release['id']}/acceptance-packet/snapshots/compare/tasks",
            json_body={
                "baseline_snapshot_id": baseline_project_bundle_release_acceptance_snapshot["id"],
                "candidate_snapshot_id": project_bundle_release_acceptance_snapshot["id"],
                "limit": 6,
                "include_remaining_actions": True,
                "include_checklist_regressions": True,
                "include_status_regression": True,
                "created_by": "smoke",
            },
        ),
        "project bundle release acceptance snapshot comparison tasks",
    )
    if not project_bundle_release_acceptance_snapshot_comparison_tasks["tasks"]:
        raise RuntimeError("project bundle acceptance comparison did not create tasks")
    first_acceptance_comparison_task = project_bundle_release_acceptance_snapshot_comparison_tasks[
        "tasks"
    ][0]
    if (
        first_acceptance_comparison_task["owner_type"]
        != "project_bundle_release_acceptance_packet_snapshot_comparison"
    ):
        raise RuntimeError("project bundle acceptance comparison task used wrong owner type")
    if (
        first_acceptance_comparison_task["due_phase"]
        != "project_bundle_release_acceptance_change_follow_up"
    ):
        raise RuntimeError("project bundle acceptance comparison task used wrong due phase")
    project_bundle_release_acceptance_snapshot_comparison_edges = require_ok(
        client.get(
            "/research/graph/edges?"
            "edge_type=project_bundle_release_acceptance_comparison_creates_task"
        ),
        "project bundle release acceptance snapshot comparison graph edges",
    )
    if not project_bundle_release_acceptance_snapshot_comparison_edges:
        raise RuntimeError(
            "project bundle release acceptance snapshot comparison did not create graph edge"
        )
    project_bundle_release_review_session = require_ok(
        client.get(
            "/research/export/project-bundle/releases/"
            f"{project_bundle_release['id']}/review-session"
        ),
        "project bundle release review session",
    )
    if project_bundle_release_review_session["release_id"] != project_bundle_release["id"]:
        raise RuntimeError("project bundle release review session used wrong release id")
    if project_bundle_release_review_session["review_status"] != "blocked_review":
        raise RuntimeError("project bundle release review session missed blocked status")
    if project_bundle_release_review_session["acceptance_status"] != "blocked":
        raise RuntimeError("project bundle release review session missed acceptance status")
    if not project_bundle_release_review_session["ready_for_review"]:
        raise RuntimeError("project bundle release review session should be ready")
    if not project_bundle_release_review_session["agenda"]:
        raise RuntimeError("project bundle release review session missed agenda")
    if not project_bundle_release_review_session["decisions_needed"]:
        raise RuntimeError("project bundle release review session missed decisions")
    if not project_bundle_release_review_session["risk_items"]:
        raise RuntimeError("project bundle release review session missed risks")
    if not project_bundle_release_review_session["follow_up_actions"]:
        raise RuntimeError("project bundle release review session missed follow-up actions")
    if (
        project_bundle_release_review_session["latest_acceptance_snapshot"]["id"]
        != project_bundle_release_acceptance_snapshot["id"]
    ):
        raise RuntimeError("project bundle release review session used wrong latest snapshot")
    if (
        "# Project Bundle Release Review Session"
        not in project_bundle_release_review_session["markdown_export"]
    ):
        raise RuntimeError("project bundle release review session markdown missed title")
    project_bundle_release_review_session_tasks = require_ok(
        client.post(
            "/research/export/project-bundle/releases/"
            f"{project_bundle_release['id']}/review-session/tasks",
            json_body={
                "limit": 8,
                "include_decisions": True,
                "include_risks": True,
                "include_follow_up_actions": True,
                "created_by": "smoke",
            },
        ),
        "project bundle release review session tasks",
    )
    if not project_bundle_release_review_session_tasks["tasks"]:
        raise RuntimeError("project bundle release review session did not create tasks")
    first_release_review_task = project_bundle_release_review_session_tasks["tasks"][0]
    if first_release_review_task["owner_type"] != "project_bundle_release_review_session":
        raise RuntimeError("project bundle release review task used wrong owner type")
    if first_release_review_task["due_phase"] != "project_bundle_release_review_follow_up":
        raise RuntimeError("project bundle release review task used wrong due phase")
    project_bundle_release_review_edges = require_ok(
        client.get("/research/graph/edges?edge_type=project_bundle_release_review_creates_task"),
        "project bundle release review graph edges",
    )
    if not project_bundle_release_review_edges:
        raise RuntimeError("project bundle release review did not create graph edge")
    project_bundle_release_review_outcome = require_ok(
        client.post(
            "/research/export/project-bundle/releases/"
            f"{project_bundle_release['id']}/review-session/outcomes",
            json_body={
                "title": "Smoke Project Bundle Release Review Outcome",
                "review_decision": "follow_up_needed",
                "participants": ["smoke researcher", "smoke advisor"],
                "outcome_notes": "Smoke review outcome captured after release review.",
                "decisions": ["Assign an owner for unresolved release review follow-up."],
                "accepted_artifacts": ["Project bundle", "Release review session"],
                "follow_up_actions": ["Complete remaining release review follow-up work."],
                "risks": ["Acceptance remains blocked until follow-up work is complete."],
                "signoff_confirmed": False,
                "created_by": "smoke",
            },
        ),
        "project bundle release review outcome",
    )
    if project_bundle_release_review_outcome["scope"] != "project_bundle_release_review_outcome":
        raise RuntimeError("project bundle release review outcome used wrong scope")
    if (
        project_bundle_release_review_outcome["summary"]["release_id"]
        != project_bundle_release["id"]
    ):
        raise RuntimeError("project bundle release review outcome used wrong release id")
    if project_bundle_release_review_outcome["summary"]["review_decision"] != "follow_up_needed":
        raise RuntimeError("project bundle release review outcome used wrong decision")
    if project_bundle_release_review_outcome["summary"]["signoff_confirmed"]:
        raise RuntimeError("project bundle release review outcome should not be signed off")
    if (
        "# Project Bundle Release Review Outcome"
        not in project_bundle_release_review_outcome["markdown_export"]
    ):
        raise RuntimeError("project bundle release review outcome markdown missed title")
    project_bundle_release_review_outcomes = require_ok(
        client.get(
            "/research/export/project-bundle/releases/"
            f"{project_bundle_release['id']}/review-session/outcomes?limit=5"
        ),
        "project bundle release review outcome list",
    )
    if (
        not project_bundle_release_review_outcomes
        or project_bundle_release_review_outcomes[0]["id"]
        != project_bundle_release_review_outcome["id"]
    ):
        raise RuntimeError("project bundle release review outcome list missed latest outcome")
    fetched_project_bundle_release_review_outcome = require_ok(
        client.get(
            "/research/export/project-bundle/releases/"
            f"{project_bundle_release['id']}/review-session/outcomes/"
            f"{project_bundle_release_review_outcome['id']}"
        ),
        "project bundle release review outcome detail",
    )
    if (
        fetched_project_bundle_release_review_outcome["id"]
        != project_bundle_release_review_outcome["id"]
    ):
        raise RuntimeError("project bundle release review outcome detail used wrong id")
    project_bundle_release_review_outcome_markdown = require_ok(
        client.get(
            "/research/export/project-bundle/releases/"
            f"{project_bundle_release['id']}/review-session/outcomes/"
            f"{project_bundle_release_review_outcome['id']}/export/markdown"
        ),
        "project bundle release review outcome markdown export",
    )
    if (
        "# Project Bundle Release Review Outcome"
        not in project_bundle_release_review_outcome_markdown
    ):
        raise RuntimeError("project bundle release review outcome export missed title")
    project_bundle_release_review_outcome_edges = require_ok(
        client.get("/research/graph/edges?edge_type=project_bundle_release_has_review_outcome"),
        "project bundle release review outcome graph edges",
    )
    if not project_bundle_release_review_outcome_edges:
        raise RuntimeError("project bundle release review outcome did not create graph edge")
    project_bundle_release_review_outcome_tasks = require_ok(
        client.post(
            "/research/export/project-bundle/releases/"
            f"{project_bundle_release['id']}/review-session/outcomes/"
            f"{project_bundle_release_review_outcome['id']}/tasks",
            json_body={
                "limit": 8,
                "include_decisions": True,
                "include_risks": True,
                "include_follow_up_actions": True,
                "include_signoff_check": True,
                "created_by": "smoke",
            },
        ),
        "project bundle release review outcome tasks",
    )
    if not project_bundle_release_review_outcome_tasks["tasks"]:
        raise RuntimeError("project bundle release review outcome did not create tasks")
    first_release_review_outcome_task = project_bundle_release_review_outcome_tasks["tasks"][0]
    if first_release_review_outcome_task["owner_type"] != "project_bundle_release_review_outcome":
        raise RuntimeError("project bundle release review outcome task used wrong owner type")
    if (
        first_release_review_outcome_task["due_phase"]
        != "project_bundle_release_review_outcome_follow_up"
    ):
        raise RuntimeError("project bundle release review outcome task used wrong due phase")
    project_bundle_release_review_outcome_task_edges = require_ok(
        client.get(
            "/research/graph/edges?edge_type=project_bundle_release_review_outcome_creates_task"
        ),
        "project bundle release review outcome task graph edges",
    )
    if not project_bundle_release_review_outcome_task_edges:
        raise RuntimeError("project bundle release review outcome task did not create graph edge")
    project_bundle_release_review_outcome_progress = require_ok(
        client.get(
            "/research/export/project-bundle/releases/"
            f"{project_bundle_release['id']}/review-session/outcomes/"
            f"{project_bundle_release_review_outcome['id']}/progress"
        ),
        "project bundle release review outcome progress",
    )
    if project_bundle_release_review_outcome_progress["release_id"] != project_bundle_release["id"]:
        raise RuntimeError("project bundle release review outcome progress used wrong release id")
    if (
        project_bundle_release_review_outcome_progress["outcome_id"]
        != project_bundle_release_review_outcome["id"]
    ):
        raise RuntimeError("project bundle release review outcome progress used wrong outcome id")
    if project_bundle_release_review_outcome_progress["task_summary"]["task_count"] < len(
        project_bundle_release_review_outcome_tasks["tasks"]
    ):
        raise RuntimeError("project bundle release review outcome progress missed tasks")
    if project_bundle_release_review_outcome_progress["completion_ratio"] != 0.0:
        raise RuntimeError("project bundle release review outcome progress should start at zero")
    if (
        "# Project Bundle Release Review Outcome Progress"
        not in project_bundle_release_review_outcome_progress["markdown_export"]
    ):
        raise RuntimeError("project bundle release review outcome progress markdown missed title")
    project_bundle_response = client.get("/research/export/project-bundle")
    if project_bundle_response.status_code != 200:
        raise RuntimeError(
            f"project bundle export failed: {project_bundle_response.status_code} "
            f"{project_bundle_response.json()}"
        )
    if project_bundle_response.headers.get("content-type") != "application/zip":
        raise RuntimeError("project bundle export did not return an application/zip response")
    with zipfile.ZipFile(io.BytesIO(project_bundle_response.content)) as archive:
        project_bundle_files = set(archive.namelist())
        required_project_files = {
            "README.md",
            "00-project-triage-brief.md",
            "01-progress-overview.md",
            "02-readiness-overview.md",
            "03-task-board.md",
            "04-opportunity-radar.md",
            "05-quality-gate-overview.md",
            "06-claim-validation-queue.md",
            "metadata/manifest.json",
            "metadata/triage-brief.json",
            "metadata/triage-snapshots.json",
            "metadata/triage-snapshot-comparison.json",
            "metadata/pilot-report-snapshots.json",
            "metadata/pilot-report-snapshot-comparison.json",
            "metadata/bundle-readiness-snapshots.json",
            "metadata/bundle-readiness-snapshot-comparison.json",
            "metadata/project-bundle-releases.json",
            "metadata/project-bundle-release-progress.json",
            "metadata/project-bundle-release-feedback.json",
            "metadata/project-bundle-release-closeout.json",
            "metadata/project-bundle-release-acceptance-packet.json",
            "metadata/project-bundle-release-acceptance-packet-snapshots.json",
            "metadata/project-bundle-release-acceptance-packet-snapshot-comparison.json",
            "metadata/project-bundle-release-review-session.json",
            "metadata/project-bundle-release-review-outcomes.json",
            "metadata/project-bundle-release-review-outcome-progress.json",
            "metadata/quality-gate-overview.json",
            "metadata/opportunity-radar.json",
            "metadata/claim-validation-queue.json",
            f"artifacts/triage/project-triage-snapshot-{triage_snapshot['id']}.md",
            "artifacts/triage/latest-triage-snapshot-comparison.md",
            f"artifacts/pilot/pilot-report-snapshot-{candidate_pilot_report_snapshot['id']}.md",
            "artifacts/pilot/latest-pilot-report-snapshot-comparison.md",
            (
                "artifacts/readiness/project-bundle-readiness-snapshot-"
                f"{project_bundle_readiness_snapshot['id']}.md"
            ),
            "artifacts/readiness/latest-bundle-readiness-snapshot-comparison.md",
            f"artifacts/releases/project-bundle-release-{project_bundle_release['id']}.md",
            "artifacts/releases/latest-project-bundle-release-progress.md",
            (
                "artifacts/releases/project-bundle-release-feedback-"
                f"{project_bundle_release_feedback['id']}.md"
            ),
            "artifacts/releases/latest-project-bundle-release-feedback.md",
            "artifacts/releases/latest-project-bundle-release-closeout.md",
            "artifacts/releases/latest-project-bundle-release-acceptance-packet.md",
            (
                "artifacts/releases/project-bundle-release-acceptance-packet-snapshot-"
                f"{project_bundle_release_acceptance_snapshot['id']}.md"
            ),
            "artifacts/releases/latest-project-bundle-release-acceptance-packet-snapshot.md",
            (
                "artifacts/releases/"
                "latest-project-bundle-release-acceptance-packet-snapshot-comparison.md"
            ),
            "artifacts/releases/latest-project-bundle-release-review-session.md",
            (
                "artifacts/releases/project-bundle-release-review-outcome-"
                f"{project_bundle_release_review_outcome['id']}.md"
            ),
            "artifacts/releases/latest-project-bundle-release-review-outcome.md",
            "artifacts/releases/latest-project-bundle-release-review-outcome-progress.md",
        }
        missing_project_files = required_project_files - project_bundle_files
        if missing_project_files:
            raise RuntimeError(f"project bundle export missed files: {missing_project_files}")
        project_bundle_manifest = json.loads(archive.read("metadata/manifest.json"))
        project_bundle_claim_queue = json.loads(
            archive.read("metadata/claim-validation-queue.json")
        )
        project_bundle_triage_comparison = json.loads(
            archive.read("metadata/triage-snapshot-comparison.json")
        )
        project_bundle_pilot_snapshots = json.loads(
            archive.read("metadata/pilot-report-snapshots.json")
        )
        project_bundle_pilot_comparison = json.loads(
            archive.read("metadata/pilot-report-snapshot-comparison.json")
        )
        project_bundle_readiness_snapshots = json.loads(
            archive.read("metadata/bundle-readiness-snapshots.json")
        )
        project_bundle_readiness_comparison = json.loads(
            archive.read("metadata/bundle-readiness-snapshot-comparison.json")
        )
        project_bundle_releases_metadata = json.loads(
            archive.read("metadata/project-bundle-releases.json")
        )
        project_bundle_release_progress_metadata = json.loads(
            archive.read("metadata/project-bundle-release-progress.json")
        )
        project_bundle_release_feedback_metadata = json.loads(
            archive.read("metadata/project-bundle-release-feedback.json")
        )
        project_bundle_release_closeout_metadata = json.loads(
            archive.read("metadata/project-bundle-release-closeout.json")
        )
        project_bundle_release_acceptance_metadata = json.loads(
            archive.read("metadata/project-bundle-release-acceptance-packet.json")
        )
        project_bundle_release_acceptance_snapshot_metadata = json.loads(
            archive.read("metadata/project-bundle-release-acceptance-packet-snapshots.json")
        )
        project_bundle_release_acceptance_snapshot_comparison_metadata = json.loads(
            archive.read(
                "metadata/project-bundle-release-acceptance-packet-snapshot-comparison.json"
            )
        )
        project_bundle_release_review_session_metadata = json.loads(
            archive.read("metadata/project-bundle-release-review-session.json")
        )
        project_bundle_release_review_outcome_metadata = json.loads(
            archive.read("metadata/project-bundle-release-review-outcomes.json")
        )
        project_bundle_release_review_outcome_progress_metadata = json.loads(
            archive.read("metadata/project-bundle-release-review-outcome-progress.json")
        )
    if project_bundle_manifest["idea_count"] < 1:
        raise RuntimeError("project bundle manifest did not include ideas")
    if (
        project_bundle_manifest["claim_validation_queue_count"]
        != project_bundle_readiness_manifest["claim_validation_queue_count"]
    ):
        raise RuntimeError("project bundle readiness and export queue counts diverged")
    if (
        project_bundle_manifest["pilot_report_snapshot_count"]
        != project_bundle_readiness_manifest["pilot_report_snapshot_count"]
    ):
        raise RuntimeError("project bundle readiness and export pilot counts diverged")
    if project_bundle_manifest["research_plan_count"] < 1:
        raise RuntimeError("project bundle manifest did not include research plans")
    if project_bundle_manifest["quality_gate_idea_count"] < 1:
        raise RuntimeError("project bundle manifest did not include quality gate ideas")
    if project_bundle_manifest["triage_next_action_count"] < 1:
        raise RuntimeError("project bundle manifest did not include triage next actions")
    if project_bundle_manifest["triage_snapshot_count"] < 2:
        raise RuntimeError("project bundle manifest did not include triage snapshots")
    if project_bundle_manifest["latest_triage_snapshot_id"] != triage_snapshot["id"]:
        raise RuntimeError("project bundle manifest did not point at the latest triage snapshot")
    if not project_bundle_manifest["triage_snapshot_comparison_available"]:
        raise RuntimeError("project bundle manifest did not expose triage comparison availability")
    if (
        project_bundle_manifest["latest_triage_snapshot_comparison_candidate_id"]
        != triage_snapshot["id"]
    ):
        raise RuntimeError("project bundle manifest did not point at the comparison candidate")
    if (
        project_bundle_manifest["latest_triage_snapshot_comparison_baseline_id"]
        != baseline_triage_snapshot["id"]
    ):
        raise RuntimeError("project bundle manifest did not point at the comparison baseline")
    if project_bundle_triage_comparison["candidate_snapshot_id"] != triage_snapshot["id"]:
        raise RuntimeError("project bundle comparison metadata used the wrong candidate")
    if project_bundle_manifest["pilot_report_snapshot_count"] < 2:
        raise RuntimeError("project bundle manifest did not include pilot report snapshots")
    if (
        project_bundle_manifest["latest_pilot_report_snapshot_id"]
        != candidate_pilot_report_snapshot["id"]
    ):
        raise RuntimeError("project bundle manifest did not point at latest pilot snapshot")
    if not project_bundle_manifest["pilot_report_snapshot_comparison_available"]:
        raise RuntimeError("project bundle manifest did not expose pilot report comparison")
    if (
        project_bundle_manifest["latest_pilot_report_snapshot_comparison_candidate_id"]
        != candidate_pilot_report_snapshot["id"]
    ):
        raise RuntimeError("project bundle pilot comparison candidate was wrong")
    if (
        project_bundle_manifest["latest_pilot_report_snapshot_comparison_baseline_id"]
        != pilot_report_snapshot["id"]
    ):
        raise RuntimeError("project bundle pilot comparison baseline was wrong")
    if project_bundle_pilot_snapshots[0]["id"] != candidate_pilot_report_snapshot["id"]:
        raise RuntimeError("project bundle pilot snapshot metadata order was wrong")
    if (
        project_bundle_pilot_comparison["candidate_snapshot_id"]
        != candidate_pilot_report_snapshot["id"]
    ):
        raise RuntimeError("project bundle pilot comparison metadata used the wrong candidate")
    if project_bundle_manifest["bundle_readiness_snapshot_count"] < 2:
        raise RuntimeError("project bundle manifest did not include bundle readiness snapshots")
    if (
        project_bundle_manifest["latest_bundle_readiness_snapshot_id"]
        != project_bundle_readiness_snapshot["id"]
    ):
        raise RuntimeError("project bundle manifest did not point at latest readiness snapshot")
    if project_bundle_manifest["latest_bundle_readiness_snapshot_level"] != "delivery_ready":
        raise RuntimeError("project bundle manifest missed latest readiness snapshot level")
    if project_bundle_readiness_snapshots[0]["id"] != project_bundle_readiness_snapshot["id"]:
        raise RuntimeError("project bundle readiness snapshot metadata order was wrong")
    if not project_bundle_manifest["bundle_readiness_snapshot_comparison_available"]:
        raise RuntimeError("project bundle manifest did not expose readiness comparison")
    if (
        project_bundle_manifest["latest_bundle_readiness_snapshot_comparison_candidate_id"]
        != project_bundle_readiness_snapshot["id"]
    ):
        raise RuntimeError("project bundle readiness comparison candidate was wrong")
    if (
        project_bundle_manifest["latest_bundle_readiness_snapshot_comparison_baseline_id"]
        != baseline_project_bundle_readiness_snapshot["id"]
    ):
        raise RuntimeError("project bundle readiness comparison baseline was wrong")
    if (
        project_bundle_readiness_comparison["candidate_snapshot_id"]
        != project_bundle_readiness_snapshot["id"]
    ):
        raise RuntimeError("project bundle readiness comparison metadata used wrong candidate")
    if project_bundle_manifest["project_bundle_release_count"] < 1:
        raise RuntimeError("project bundle manifest did not include release notes")
    if project_bundle_manifest["latest_project_bundle_release_id"] != project_bundle_release["id"]:
        raise RuntimeError("project bundle manifest did not point at latest release note")
    if project_bundle_manifest["latest_project_bundle_release_recipient"] != "smoke advisor":
        raise RuntimeError("project bundle manifest missed latest release recipient")
    if not project_bundle_manifest["latest_project_bundle_release_progress_available"]:
        raise RuntimeError("project bundle manifest did not expose release progress")
    if project_bundle_manifest["latest_project_bundle_release_progress_open_task_count"] < 1:
        raise RuntimeError("project bundle manifest did not count release progress open tasks")
    if (
        project_bundle_manifest["latest_project_bundle_release_progress_completion_ratio"]
        != project_bundle_release_progress["completion_ratio"]
    ):
        raise RuntimeError("project bundle manifest release progress completion diverged")
    if project_bundle_releases_metadata[0]["id"] != project_bundle_release["id"]:
        raise RuntimeError("project bundle release metadata order was wrong")
    if project_bundle_release_progress_metadata["release_id"] != project_bundle_release["id"]:
        raise RuntimeError("project bundle release progress metadata used wrong release id")
    if project_bundle_release_progress_metadata["task_summary"]["open_task_count"] < 1:
        raise RuntimeError("project bundle release progress metadata missed open tasks")
    if project_bundle_manifest["project_bundle_release_feedback_count"] < 1:
        raise RuntimeError("project bundle manifest did not include release feedback")
    if (
        project_bundle_manifest["latest_project_bundle_release_feedback_id"]
        != project_bundle_release_feedback["id"]
    ):
        raise RuntimeError("project bundle manifest did not point at latest release feedback")
    if (
        project_bundle_manifest["latest_project_bundle_release_feedback_release_id"]
        != project_bundle_release["id"]
    ):
        raise RuntimeError("project bundle manifest release feedback used wrong release id")
    if (
        project_bundle_manifest["latest_project_bundle_release_feedback_status"]
        != "changes_requested"
    ):
        raise RuntimeError("project bundle manifest release feedback missed status")
    if project_bundle_manifest["latest_project_bundle_release_feedback_signoff_confirmed"]:
        raise RuntimeError("project bundle manifest release feedback signoff should be pending")
    if project_bundle_release_feedback_metadata[0]["id"] != project_bundle_release_feedback["id"]:
        raise RuntimeError("project bundle release feedback metadata order was wrong")
    if not project_bundle_manifest["latest_project_bundle_release_closeout_available"]:
        raise RuntimeError("project bundle manifest did not expose release closeout")
    if project_bundle_manifest["latest_project_bundle_release_closeout_status"] != "blocked":
        raise RuntimeError("project bundle manifest release closeout missed blocked status")
    if project_bundle_manifest["latest_project_bundle_release_closeout_ready"]:
        raise RuntimeError("project bundle manifest release closeout should not be ready")
    if project_bundle_manifest["latest_project_bundle_release_closeout_next_action_count"] < 1:
        raise RuntimeError("project bundle manifest release closeout missed next actions")
    if project_bundle_manifest["latest_project_bundle_release_closeout_blocker_count"] < 1:
        raise RuntimeError("project bundle manifest release closeout missed blockers")
    if project_bundle_release_closeout_metadata["release_id"] != project_bundle_release["id"]:
        raise RuntimeError("project bundle release closeout metadata used wrong release id")
    if project_bundle_release_closeout_metadata["closeout_status"] != "blocked":
        raise RuntimeError("project bundle release closeout metadata missed blocked status")
    if not project_bundle_manifest["latest_project_bundle_release_acceptance_packet_available"]:
        raise RuntimeError("project bundle manifest did not expose release acceptance packet")
    if project_bundle_manifest["latest_project_bundle_release_acceptance_status"] != "blocked":
        raise RuntimeError("project bundle manifest release acceptance missed blocked status")
    if project_bundle_manifest["latest_project_bundle_release_acceptance_ready_for_signoff"]:
        raise RuntimeError("project bundle manifest release acceptance should not be ready")
    if (
        project_bundle_manifest["latest_project_bundle_release_acceptance_remaining_action_count"]
        < 1
    ):
        raise RuntimeError("project bundle manifest release acceptance missed remaining actions")
    if (
        project_bundle_manifest["latest_project_bundle_release_acceptance_open_closeout_task_count"]
        < 1
    ):
        raise RuntimeError("project bundle manifest release acceptance missed closeout tasks")
    if project_bundle_release_acceptance_metadata["release_id"] != project_bundle_release["id"]:
        raise RuntimeError("project bundle release acceptance metadata used wrong release id")
    if project_bundle_release_acceptance_metadata["acceptance_status"] != "blocked":
        raise RuntimeError("project bundle release acceptance metadata missed blocked status")
    if project_bundle_manifest["project_bundle_release_acceptance_packet_snapshot_count"] < 1:
        raise RuntimeError("project bundle manifest missed release acceptance snapshots")
    if (
        project_bundle_manifest["latest_project_bundle_release_acceptance_packet_snapshot_id"]
        != project_bundle_release_acceptance_snapshot["id"]
    ):
        raise RuntimeError(
            "project bundle manifest did not point at latest release acceptance snapshot"
        )
    if (
        project_bundle_manifest[
            "latest_project_bundle_release_acceptance_packet_snapshot_release_id"
        ]
        != project_bundle_release["id"]
    ):
        raise RuntimeError("project bundle manifest acceptance snapshot used wrong release id")
    if (
        project_bundle_manifest["latest_project_bundle_release_acceptance_packet_snapshot_status"]
        != "blocked"
    ):
        raise RuntimeError("project bundle manifest acceptance snapshot missed blocked status")
    if project_bundle_manifest[
        "latest_project_bundle_release_acceptance_packet_snapshot_ready_for_signoff"
    ]:
        raise RuntimeError("project bundle manifest acceptance snapshot should not be ready")
    if (
        project_bundle_release_acceptance_snapshot_metadata[0]["id"]
        != project_bundle_release_acceptance_snapshot["id"]
    ):
        raise RuntimeError("project bundle acceptance snapshot metadata order was wrong")
    if not project_bundle_manifest[
        "project_bundle_release_acceptance_packet_snapshot_comparison_available"
    ]:
        raise RuntimeError("project bundle manifest missed acceptance snapshot comparison")
    if (
        project_bundle_manifest[
            "latest_project_bundle_release_acceptance_packet_snapshot_comparison_baseline_id"
        ]
        != baseline_project_bundle_release_acceptance_snapshot["id"]
    ):
        raise RuntimeError("project bundle manifest acceptance comparison baseline was wrong")
    if (
        project_bundle_manifest[
            "latest_project_bundle_release_acceptance_packet_snapshot_comparison_candidate_id"
        ]
        != project_bundle_release_acceptance_snapshot["id"]
    ):
        raise RuntimeError("project bundle manifest acceptance comparison candidate was wrong")
    if project_bundle_manifest[
        "latest_project_bundle_release_acceptance_packet_snapshot_comparison_added_action_count"
    ] != len(project_bundle_release_acceptance_snapshot_comparison["added_remaining_actions"]):
        raise RuntimeError("project bundle manifest acceptance comparison action count diverged")
    if project_bundle_manifest[
        "latest_project_bundle_release_acceptance_packet_snapshot_comparison_new_checklist_count"
    ] != len(
        project_bundle_release_acceptance_snapshot_comparison["newly_blocked_checklist_items"]
    ):
        raise RuntimeError("project bundle manifest acceptance comparison checklist count diverged")
    if (
        project_bundle_release_acceptance_snapshot_comparison_metadata["candidate_snapshot_id"]
        != project_bundle_release_acceptance_snapshot["id"]
    ):
        raise RuntimeError("project bundle acceptance comparison metadata used wrong candidate")
    if not project_bundle_manifest["latest_project_bundle_release_review_session_available"]:
        raise RuntimeError("project bundle manifest missed release review session")
    if (
        project_bundle_manifest["latest_project_bundle_release_review_session_status"]
        != "blocked_review"
    ):
        raise RuntimeError("project bundle manifest release review missed blocked status")
    if not project_bundle_manifest["latest_project_bundle_release_review_session_ready"]:
        raise RuntimeError("project bundle manifest release review should be ready")
    if project_bundle_manifest[
        "latest_project_bundle_release_review_session_decision_count"
    ] != len(project_bundle_release_review_session["decisions_needed"]):
        raise RuntimeError("project bundle manifest release review decision count diverged")
    if project_bundle_manifest["latest_project_bundle_release_review_session_risk_count"] != len(
        project_bundle_release_review_session["risk_items"]
    ):
        raise RuntimeError("project bundle manifest release review risk count diverged")
    if project_bundle_manifest[
        "latest_project_bundle_release_review_session_follow_up_count"
    ] != len(project_bundle_release_review_session["follow_up_actions"]):
        raise RuntimeError("project bundle manifest release review follow-up count diverged")
    if project_bundle_release_review_session_metadata["release_id"] != project_bundle_release["id"]:
        raise RuntimeError("project bundle release review metadata used wrong release id")
    if project_bundle_release_review_session_metadata["review_status"] != "blocked_review":
        raise RuntimeError("project bundle release review metadata missed blocked status")
    if project_bundle_manifest["project_bundle_release_review_outcome_count"] < 1:
        raise RuntimeError("project bundle manifest missed release review outcomes")
    if (
        project_bundle_manifest["latest_project_bundle_release_review_outcome_id"]
        != project_bundle_release_review_outcome["id"]
    ):
        raise RuntimeError("project bundle manifest did not point at latest review outcome")
    if (
        project_bundle_manifest["latest_project_bundle_release_review_outcome_release_id"]
        != project_bundle_release["id"]
    ):
        raise RuntimeError("project bundle manifest review outcome used wrong release id")
    if (
        project_bundle_manifest["latest_project_bundle_release_review_outcome_decision"]
        != "follow_up_needed"
    ):
        raise RuntimeError("project bundle manifest review outcome missed decision")
    if project_bundle_manifest["latest_project_bundle_release_review_outcome_signoff_confirmed"]:
        raise RuntimeError("project bundle manifest review outcome should not be signed off")
    if project_bundle_manifest[
        "latest_project_bundle_release_review_outcome_follow_up_count"
    ] != len(project_bundle_release_review_outcome["summary"]["follow_up_actions"]):
        raise RuntimeError("project bundle manifest review outcome follow-up count diverged")
    if project_bundle_manifest["latest_project_bundle_release_review_outcome_risk_count"] != len(
        project_bundle_release_review_outcome["summary"]["risks"]
    ):
        raise RuntimeError("project bundle manifest review outcome risk count diverged")
    if (
        project_bundle_release_review_outcome_metadata[0]["id"]
        != (project_bundle_release_review_outcome["id"])
    ):
        raise RuntimeError("project bundle review outcome metadata order was wrong")
    if not project_bundle_manifest[
        "latest_project_bundle_release_review_outcome_progress_available"
    ]:
        raise RuntimeError("project bundle manifest missed review outcome progress")
    if (
        project_bundle_manifest[
            "latest_project_bundle_release_review_outcome_progress_completion_ratio"
        ]
        != project_bundle_release_review_outcome_progress["completion_ratio"]
    ):
        raise RuntimeError("project bundle manifest review outcome progress ratio diverged")
    if (
        project_bundle_manifest[
            "latest_project_bundle_release_review_outcome_progress_open_task_count"
        ]
        < 1
    ):
        raise RuntimeError("project bundle manifest review outcome progress missed open tasks")
    if (
        project_bundle_manifest[
            "latest_project_bundle_release_review_outcome_progress_blocked_task_count"
        ]
        < 0
    ):
        raise RuntimeError("project bundle manifest review outcome progress blockers diverged")
    if (
        project_bundle_release_review_outcome_progress_metadata["outcome_id"]
        != project_bundle_release_review_outcome["id"]
    ):
        raise RuntimeError("project bundle review outcome progress metadata used wrong outcome id")
    if project_bundle_manifest["opportunity_count"] < 1:
        raise RuntimeError("project bundle manifest did not include opportunities")
    if project_bundle_manifest["claim_validation_queue_count"] < 1:
        raise RuntimeError("project bundle manifest did not include claim validation queue items")
    if project_bundle_manifest["claim_validation_queue_idea_count"] < 1:
        raise RuntimeError("project bundle manifest did not include claim validation queue ideas")
    if project_bundle_claim_queue["summary"]["item_count"] < 1:
        raise RuntimeError("project bundle claim validation queue metadata was empty")
    if (
        project_bundle_claim_queue["summary"]["item_count"]
        != project_bundle_manifest["claim_validation_queue_count"]
    ):
        raise RuntimeError("project bundle claim validation queue count did not match manifest")
    if not project_bundle_claim_queue["items"][0].get(
        "ledger_id"
    ) or not project_bundle_claim_queue["items"][0].get("claim_id"):
        raise RuntimeError("project bundle claim validation queue item missed claim identity")
    post_plan_progress = require_ok(
        client.get(f"/research/ideas/{refined_idea['id']}/progress"),
        "idea progress after research plan tasks",
    )
    if post_plan_progress["artifact_counts"].get("research_plans", 0) < 1:
        raise RuntimeError("idea progress did not count research plans")
    if post_plan_progress["artifact_counts"].get("research_plan_tasks", 0) < 1:
        raise RuntimeError("idea progress did not count research plan tasks")
    if post_plan_progress["latest_artifacts"]["research_plan"]["id"] != research_plan["id"]:
        raise RuntimeError("idea progress did not expose latest research plan")
    post_plan_packet = require_ok(
        client.get(f"/research/ideas/{refined_idea['id']}/research-packet"),
        "idea research packet after research plan tasks",
    )
    if post_plan_packet["graph_edge_summary"].get("research_plan_creates_task", 0) < 1:
        raise RuntimeError("research packet did not summarize research plan task edges")
    post_plan_bundle_response = client.get(f"/research/ideas/{refined_idea['id']}/export/bundle")
    if post_plan_bundle_response.status_code != 200:
        raise RuntimeError(
            f"post-plan idea bundle failed: {post_plan_bundle_response.status_code} "
            f"{post_plan_bundle_response.json()}"
        )
    with zipfile.ZipFile(io.BytesIO(post_plan_bundle_response.content)) as archive:
        post_plan_bundle_files = set(archive.namelist())
    expected_plan_file = f"artifacts/plans/research-plan-{research_plan['id']}.md"
    if expected_plan_file not in post_plan_bundle_files:
        raise RuntimeError("idea bundle did not include research plan markdown")
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
    ranked_refined = next(
        item for item in ranking["ranked_ideas"] if item["idea"]["id"] == refined_idea["id"]
    )
    if ranked_refined["score_breakdown"].get("claim_validation_needs_more_evidence", 0) < 1:
        raise RuntimeError("idea ranking did not count claim validation evidence gaps")
    if ranked_refined["score_breakdown"].get("claim_validation_adjustment", 0) >= 0:
        raise RuntimeError("idea ranking did not penalize needs-more-evidence claim results")
    if not any(
        "Claim validation found evidence gaps" in item for item in ranked_refined["rationale"]
    ):
        raise RuntimeError("idea ranking did not explain claim validation impact")
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
        "service_readiness": service_readiness,
        "phase": status["phase"],
        "tool_manifest_count": len(tool_manifest["tools"]),
        "tool_bridge_count": len(tool_bridge["tools"]),
        "research_profile_name": setup_wizard["profile"]["name"],
        "workbench_available": "Research Assistant Workbench" in workbench,
        "setup_wizard_readiness_level": setup_wizard["readiness"]["readiness_level"],
        "setup_wizard_next_step_count": len(setup_wizard["recommended_next_steps"]),
        "onboarding_task_count": len(onboarding_tasks["tasks"]),
        "onboarding_progress_completion": onboarding_progress["task_summary"]["completion_ratio"],
        "onboarding_progress_open_count": onboarding_progress["task_summary"]["open_task_count"],
        "pilot_report_status": pilot_report["report_status"],
        "pilot_report_next_action_count": len(pilot_report["next_actions"]),
        "pilot_report_snapshot_id": pilot_report_snapshot["id"],
        "pilot_report_snapshot_markdown_chars": len(pilot_report_snapshot_markdown),
        "pilot_report_snapshot_task_count": len(pilot_report_snapshot_tasks["tasks"]),
        "pilot_report_snapshot_comparison_added_risks": len(
            pilot_report_snapshot_comparison["added_risks"]
        ),
        "pilot_report_snapshot_comparison_markdown_chars": len(
            pilot_report_snapshot_comparison_markdown
        ),
        "pilot_report_snapshot_comparison_task_count": len(
            pilot_report_snapshot_comparison_tasks["tasks"]
        ),
        "onboarding_start_level": onboarding_start["readiness_level"],
        "onboarding_readiness_level": onboarding_after_workflow["readiness_level"],
        "onboarding_score": onboarding_after_workflow["readiness_score"],
        "onboarding_missing_required_count": len(onboarding_after_workflow["missing_required"]),
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
        "evidence_ledger_id": evidence_ledger["id"],
        "evidence_ledger_claim_count": len(evidence_ledger["claims"]),
        "evidence_ledger_coverage_score": evidence_ledger["coverage_score"],
        "evidence_ledger_markdown_chars": len(evidence_ledger_markdown),
        "evidence_ledger_task_count": len(evidence_tasks["tasks"]),
        "claim_validation_claim_id": claim_packet["claim"]["claim_id"],
        "claim_validation_support_count": len(claim_packet["supporting_evidence"]),
        "claim_validation_action_count": len(claim_packet["validation_actions"]),
        "claim_validation_queue_count": len(claim_queue["items"]),
        "claim_validation_queue_critical": claim_queue["summary"]["critical_count"],
        "claim_validation_queue_task_count": len(claim_queue_tasks["tasks"]),
        "claim_validation_result_event_id": claim_validation_result["id"],
        "claim_validation_result_status": claim_validation_result["metadata"]["validation_status"],
        "claim_validation_task_status_after_result": claim_validation_task_after_result["status"],
        "proposal_task_graph_edge_count": len(proposal_graph_edges),
        "evidence_ledger_task_graph_edge_count": len(ledger_task_edges),
        "claim_queue_task_graph_edge_count": len(claim_queue_task_edges),
        "lineage_task_count": len(lineage["research_tasks"]),
        "lineage_graph_edge_types": len(lineage["graph_edge_summary"]),
        "progress_open_task_count": progress["artifact_counts"]["open_tasks"],
        "progress_claim_validation_result_count": progress_after_claim_result["artifact_counts"][
            "claim_validation_result_events"
        ],
        "progress_recommended_next_step": progress["recommended_next_step"],
        "research_packet_markdown_chars": len(research_packet["markdown_export"]),
        "timeline_event_count": len(timeline["events"]),
        "timeline_markdown_chars": len(timeline["markdown_export"]),
        "readiness_score": readiness["readiness_score"],
        "readiness_decision": readiness["decision"],
        "readiness_claim_validation_score": readiness["score_breakdown"]["claim_validation"][
            "score"
        ],
        "quality_gate_score": quality_gate["gate_score"],
        "quality_gate_decision": quality_gate["decision"],
        "quality_gate_claim_validation_score": quality_gate["score_breakdown"]["claim_validation"][
            "score"
        ],
        "quality_gate_task_count": len(quality_gate_tasks["tasks"]),
        "quality_gate_progress_task_count": progress_after_quality_gate_tasks["artifact_counts"][
            "quality_gate_follow_up_tasks"
        ],
        "quality_overview_idea_count": quality_overview["idea_count"],
        "quality_overview_average": quality_overview["average_gate_score"],
        "triage_next_action_count": len(triage_brief["next_actions"]),
        "triage_markdown_chars": len(triage_markdown),
        "triage_task_count": len(triage_tasks["tasks"]),
        "triage_snapshot_id": triage_snapshot["id"],
        "triage_snapshot_markdown_chars": len(triage_snapshot_markdown),
        "triage_snapshot_comparison_markdown_chars": len(triage_snapshot_comparison_markdown),
        "triage_comparison_task_count": len(triage_comparison_tasks["tasks"]),
        "project_quality_task_count": len(project_quality_tasks["tasks"]),
        "readiness_task_count": len(readiness_tasks["tasks"]),
        "readiness_progress_task_count": progress_after_readiness_tasks["artifact_counts"][
            "readiness_follow_up_tasks"
        ],
        "idea_bundle_file_count": len(bundle_files),
        "idea_bundle_manifest_decision": bundle_manifest["readiness"]["decision"],
        "overview_idea_count": overview["idea_count"],
        "overview_open_task_count": overview["task_summary"]["open_task_count"],
        "overview_claim_validation_task_count": overview["task_summary"][
            "claim_validation_task_count"
        ],
        "overview_claim_validation_result_count": overview["task_summary"][
            "claim_validation_result_count"
        ],
        "cockpit_phase": cockpit["phase"],
        "cockpit_readiness_level": cockpit["readiness_level"],
        "cockpit_primary_action": cockpit["primary_next_action"]["label"],
        "cockpit_quick_action_count": len(cockpit["quick_actions"]),
        "cockpit_task_count": len(cockpit_tasks["tasks"]),
        "advisor_chat_intent": advisor_chat["intent"],
        "advisor_chat_action_count": len(advisor_chat["recommended_actions"]),
        "advisor_chat_citation_count": advisor_citation_count,
        "advisor_chat_tool_suggestion_count": len(advisor_chat["tool_suggestions"]),
        "advisor_chat_task_count": len(advisor_chat_tasks["tasks"]),
        "advisor_action_session_task_count": len(advisor_action_session["tasks"]),
        "advisor_action_session_snapshot_id": advisor_action_session["snapshot"]["id"],
        "advisor_action_session_open_count": advisor_action_session["progress_summary"][
            "open_task_count"
        ],
        "readiness_overview_idea_count": readiness_overview["idea_count"],
        "readiness_overview_average": readiness_overview["average_readiness"],
        "opportunity_radar_count": len(radar["top_opportunities"]),
        "opportunity_radar_top_score": radar["top_opportunities"][0]["radar_score"],
        "opportunity_radar_sequence_count": len(radar["recommended_sequence"]),
        "opportunity_radar_task_count": len(radar_tasks["tasks"]),
        "advisor_brief_id": advisor_brief["id"],
        "advisor_brief_markdown_chars": len(advisor_brief_markdown),
        "advisor_brief_claim_queue_count": claim_queue_summary["item_count"],
        "advisor_brief_claim_validation_task_count": advisor_brief["summary"]["triage_signals"][
            "claim_validation_task_count"
        ],
        "advisor_brief_claim_validation_result_count": advisor_brief["summary"][
            "claim_validation_results"
        ]["event_count"],
        "advisor_brief_triage_snapshot_candidate": advisor_brief["summary"][
            "triage_snapshot_comparison"
        ]["candidate_snapshot_id"],
        "plan_advisor_brief_id": plan_advisor_brief["id"],
        "plan_advisor_brief_plan_count": plan_advisor_brief["summary"]["research_plan_count"],
        "project_bundle_file_count": len(project_bundle_files),
        "project_bundle_readiness_level": project_bundle_readiness["readiness_level"],
        "project_bundle_readiness_score": project_bundle_readiness["readiness_score"],
        "project_bundle_readiness_missing": len(project_bundle_readiness["missing_required"]),
        "project_bundle_readiness_task_count": len(project_bundle_readiness_tasks["tasks"]),
        "project_bundle_readiness_snapshot_id": project_bundle_readiness_snapshot["id"],
        "project_bundle_readiness_snapshot_count": project_bundle_manifest[
            "bundle_readiness_snapshot_count"
        ],
        "project_bundle_readiness_snapshot_comparison_available": project_bundle_manifest[
            "bundle_readiness_snapshot_comparison_available"
        ],
        "project_bundle_readiness_snapshot_comparison_delta": project_bundle_manifest[
            "latest_bundle_readiness_snapshot_comparison_score_delta"
        ],
        "project_bundle_readiness_comparison_task_count": len(
            project_bundle_readiness_comparison_tasks["tasks"]
        ),
        "project_bundle_release_id": project_bundle_release["id"],
        "project_bundle_release_count": project_bundle_manifest["project_bundle_release_count"],
        "project_bundle_release_task_count": len(project_bundle_release_tasks["tasks"]),
        "project_bundle_release_progress_completion": project_bundle_release_progress[
            "completion_ratio"
        ],
        "project_bundle_release_progress_open_count": project_bundle_release_progress[
            "task_summary"
        ]["open_task_count"],
        "project_bundle_release_feedback_id": project_bundle_release_feedback["id"],
        "project_bundle_release_feedback_count": project_bundle_manifest[
            "project_bundle_release_feedback_count"
        ],
        "project_bundle_release_feedback_status": project_bundle_manifest[
            "latest_project_bundle_release_feedback_status"
        ],
        "project_bundle_release_feedback_task_count": len(
            project_bundle_release_feedback_tasks["tasks"]
        ),
        "project_bundle_release_closeout_status": project_bundle_release_closeout[
            "closeout_status"
        ],
        "project_bundle_release_closeout_ready": project_bundle_release_closeout["ready_to_close"],
        "project_bundle_release_closeout_next_actions": len(
            project_bundle_release_closeout["next_actions"]
        ),
        "project_bundle_release_closeout_task_count": len(
            project_bundle_release_closeout_tasks["tasks"]
        ),
        "project_bundle_release_acceptance_status": project_bundle_release_acceptance_packet[
            "acceptance_status"
        ],
        "project_bundle_release_acceptance_remaining_actions": len(
            project_bundle_release_acceptance_packet["remaining_actions"]
        ),
        "project_bundle_release_acceptance_snapshot_id": (
            project_bundle_release_acceptance_snapshot["id"]
        ),
        "project_bundle_release_acceptance_snapshot_count": project_bundle_manifest[
            "project_bundle_release_acceptance_packet_snapshot_count"
        ],
        "project_bundle_release_acceptance_comparison_available": project_bundle_manifest[
            "project_bundle_release_acceptance_packet_snapshot_comparison_available"
        ],
        "project_bundle_release_acceptance_comparison_task_count": len(
            project_bundle_release_acceptance_snapshot_comparison_tasks["tasks"]
        ),
        "project_bundle_release_review_status": project_bundle_release_review_session[
            "review_status"
        ],
        "project_bundle_release_review_decision_count": len(
            project_bundle_release_review_session["decisions_needed"]
        ),
        "project_bundle_release_review_task_count": len(
            project_bundle_release_review_session_tasks["tasks"]
        ),
        "project_bundle_release_review_outcome_id": project_bundle_release_review_outcome["id"],
        "project_bundle_release_review_outcome_count": project_bundle_manifest[
            "project_bundle_release_review_outcome_count"
        ],
        "project_bundle_release_review_outcome_decision": project_bundle_manifest[
            "latest_project_bundle_release_review_outcome_decision"
        ],
        "project_bundle_release_review_outcome_task_count": len(
            project_bundle_release_review_outcome_tasks["tasks"]
        ),
        "project_bundle_release_review_outcome_progress_completion": (
            project_bundle_release_review_outcome_progress["completion_ratio"]
        ),
        "project_bundle_release_review_outcome_progress_open_count": (
            project_bundle_release_review_outcome_progress["task_summary"]["open_task_count"]
        ),
        "project_bundle_latest_release_recipient": project_bundle_manifest[
            "latest_project_bundle_release_recipient"
        ],
        "project_bundle_plan_count": project_bundle_manifest["research_plan_count"],
        "project_bundle_triage_snapshot_count": project_bundle_manifest["triage_snapshot_count"],
        "project_bundle_triage_comparison_available": project_bundle_manifest[
            "triage_snapshot_comparison_available"
        ],
        "project_bundle_pilot_snapshot_count": project_bundle_manifest[
            "pilot_report_snapshot_count"
        ],
        "project_bundle_pilot_comparison_available": project_bundle_manifest[
            "pilot_report_snapshot_comparison_available"
        ],
        "project_bundle_opportunity_count": project_bundle_manifest["opportunity_count"],
        "project_bundle_claim_queue_count": project_bundle_manifest["claim_validation_queue_count"],
        "project_bundle_claim_queue_critical": project_bundle_manifest[
            "claim_validation_queue_critical_count"
        ],
        "research_plan_id": research_plan["id"],
        "research_plan_item_count": len(research_plan["plan_items"]),
        "research_plan_task_count": len(research_plan_tasks["tasks"]),
        "research_plan_progress_completion": research_plan_progress["task_summary"][
            "completion_ratio"
        ],
        "post_plan_progress_plan_count": post_plan_progress["artifact_counts"]["research_plans"],
        "post_plan_bundle_file_count": len(post_plan_bundle_files),
        "research_plan_markdown_chars": len(research_plan_markdown),
        "feedback_decision": feedback["decision"],
        "feedback_rating": feedback["rating"],
        "ranked_idea_count": len(ranking["ranked_ideas"]),
        "top_ranked_idea_id": ranking["ranked_ideas"][0]["idea"]["id"],
        "top_ranked_idea_score": ranking["ranked_ideas"][0]["weighted_score"],
        "ranking_claim_validation_adjustment": ranked_refined["score_breakdown"][
            "claim_validation_adjustment"
        ],
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
        "novelty_refresh_status": novelty_refresh["status"],
        "novelty_refresh_signal_count": len(novelty_refresh["collision_signals"]),
        "novelty_task_count": len(novelty_tasks["tasks"]),
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
