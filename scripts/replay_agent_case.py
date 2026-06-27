#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.research.db import SessionLocal
from backend.research.models import AgentRun, ReplayCase, ToolCallRecord
from backend.research.schemas import AgentRunCreate, ToolCallRecordCreate
from backend.research.services.agent_trace_service import AgentTraceService
from backend.research.services.embedding_service import EmbeddingService
from backend.research.services.retrieval_service import RetrievalService


SECRET_VALUE_PATTERN = re.compile(r"(sk-[A-Za-z0-9_\-]{8,}|Bearer\s+[A-Za-z0-9._\-]{8,})")
SENSITIVE_KEY_PARTS = {
    "api_key",
    "apikey",
    "authorization",
    "auth",
    "cookie",
    "credential",
    "password",
    "secret",
    "token",
}


@dataclass(frozen=True)
class ReplayEvaluation:
    case_id: str
    case_type: str
    source_agent_run_id: str | None
    stored_verdict: str
    replay_verdict: str
    reasons: list[str]
    query: str
    expected: dict[str, Any]
    observed: dict[str, Any]
    tool_names: list[str]
    run_status: str

    def to_json(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "case_type": self.case_type,
            "source_agent_run_id": self.source_agent_run_id,
            "stored_verdict": self.stored_verdict,
            "replay_verdict": self.replay_verdict,
            "reasons": self.reasons,
            "query": self.query,
            "expected": _redact_json(self.expected),
            "observed": _redact_json(self.observed),
            "tool_names": self.tool_names,
            "run_status": self.run_status,
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Replay saved local agent bad cases. By default this is deterministic log "
            "evaluation; --live-executors enables bounded local executors."
        ),
    )
    parser.add_argument("--case-id", default="", help="Replay one specific ReplayCase id.")
    parser.add_argument("--case-type", default="", help="Filter replay cases by case_type.")
    parser.add_argument("--verdict", default="", help="Filter replay cases by stored verdict.")
    parser.add_argument("--limit", type=int, default=20, help="Maximum cases to replay.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--write-markdown", default="", help="Write a Markdown replay report.")
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="Exit with status 1 when any replay case evaluates to fail.",
    )
    parser.add_argument(
        "--live-executors",
        action="store_true",
        help=(
            "Run supported local executors such as context_search_miss. "
            "Executors use local embedding/rerank modes and do not call model providers."
        ),
    )
    parser.add_argument(
        "--record-run",
        action="store_true",
        help="Persist this replay invocation as an agent_replay AgentRun for local audit.",
    )
    args = parser.parse_args()

    started = time.perf_counter()
    with SessionLocal() as session:
        trace_service = AgentTraceService(session)
        replay_run = _start_replay_run(trace_service, args) if args.record_run else None
        cases = _load_cases(
            session,
            case_id=args.case_id,
            case_type=args.case_type,
            verdict=args.verdict,
            limit=args.limit,
        )
        evaluations = [
            _evaluate_case(session, replay_case, live_executors=args.live_executors)
            for replay_case in cases
        ]
        payload = _build_report_payload(evaluations)
        if replay_run:
            _record_replay_tool_calls(trace_service, replay_run.id, evaluations)
            _finish_replay_run(trace_service, replay_run.id, payload, args, started)

    if args.write_markdown:
        Path(args.write_markdown).parent.mkdir(parents=True, exist_ok=True)
        Path(args.write_markdown).write_text(_render_markdown(payload), encoding="utf-8")

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(_render_console_summary(payload))

    if args.fail_on_regression and payload["summary"]["failed"] > 0:
        return 1
    return 0


def _load_cases(
    session,
    *,
    case_id: str,
    case_type: str,
    verdict: str,
    limit: int,
) -> list[ReplayCase]:
    query = session.query(ReplayCase).order_by(ReplayCase.created_at.desc())
    if case_id:
        query = query.filter(ReplayCase.id == case_id)
    if case_type:
        query = query.filter(ReplayCase.case_type == case_type)
    if verdict:
        query = query.filter(ReplayCase.verdict == verdict)
    return query.limit(max(1, min(limit, 200))).all()


def _start_replay_run(trace_service: AgentTraceService, args: argparse.Namespace) -> AgentRun:
    return trace_service.create_run(
        AgentRunCreate(
            run_type="agent_replay",
            status="running",
            question=_replay_question(args),
            input=_replay_input(args),
            metadata={
                "script": "scripts/replay_agent_case.py",
                "live_executors": bool(args.live_executors),
                "json": bool(args.json),
                "write_markdown": bool(args.write_markdown),
                "fail_on_regression": bool(args.fail_on_regression),
            },
            created_by="replay_script",
        )
    )


def _finish_replay_run(
    trace_service: AgentTraceService,
    run_id: str,
    payload: dict[str, Any],
    args: argparse.Namespace,
    started: float,
) -> AgentRun:
    summary = payload["summary"]
    status = "failed" if summary["failed"] > 0 else "completed"
    case_rollup = [
        {
            "case_id": item["case_id"],
            "case_type": item["case_type"],
            "replay_verdict": item["replay_verdict"],
        }
        for item in payload["cases"]
    ]
    return trace_service.finish_run(
        run_id,
        status=status,
        output={
            "summary": summary,
            "cases": case_rollup,
        },
        latency_ms=int((time.perf_counter() - started) * 1000),
        metadata={
            "script": "scripts/replay_agent_case.py",
            "record_run": True,
            "live_executors": bool(args.live_executors),
            "write_markdown": bool(args.write_markdown),
        },
    )


def _record_replay_tool_calls(
    trace_service: AgentTraceService,
    run_id: str,
    evaluations: list[ReplayEvaluation],
) -> None:
    for evaluation in evaluations:
        live_executor = str(evaluation.observed.get("live_executor") or "")
        if not live_executor:
            continue
        live_status = str(evaluation.observed.get("live_status") or "")
        context_counts = evaluation.observed.get("context_counts") or {}
        trace_service.create_tool_call(
            run_id,
            ToolCallRecordCreate(
                tool_name=f"replay.{live_executor}",
                tool_arguments={
                    "case_id": evaluation.case_id,
                    "case_type": evaluation.case_type,
                    "query": evaluation.query,
                    "paper_ids": evaluation.observed.get("paper_ids") or [],
                    "limit": evaluation.expected.get("limit", ""),
                    "include_graph": evaluation.expected.get("include_graph", False),
                },
                tool_result_summary=_replay_tool_summary(live_status, context_counts),
                status=_tool_status_from_live_status(live_status),
                error=str(evaluation.observed.get("live_error") or ""),
                side_effect=False,
                metadata={
                    "replay_verdict": evaluation.replay_verdict,
                    "stored_verdict": evaluation.stored_verdict,
                },
            ),
        )


def _replay_question(args: argparse.Namespace) -> str:
    filters = []
    if args.case_id:
        filters.append(f"case_id={args.case_id}")
    if args.case_type:
        filters.append(f"case_type={args.case_type}")
    if args.verdict:
        filters.append(f"verdict={args.verdict}")
    return "Replay agent cases" + (": " + ", ".join(filters) if filters else "")


def _replay_input(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "case_id": args.case_id,
        "case_type": args.case_type,
        "verdict": args.verdict,
        "limit": args.limit,
        "json": bool(args.json),
        "write_markdown": bool(args.write_markdown),
        "fail_on_regression": bool(args.fail_on_regression),
        "live_executors": bool(args.live_executors),
    }


def _replay_tool_summary(live_status: str, context_counts: dict[str, Any]) -> str:
    return (
        f"live_status={live_status or 'unknown'} "
        f"chunks={context_counts.get('chunks', 0)} "
        f"evidences={context_counts.get('evidences', 0)} "
        f"gaps={context_counts.get('gaps', 0)} "
        f"ideas={context_counts.get('ideas', 0)}"
    )


def _tool_status_from_live_status(live_status: str) -> str:
    if live_status == "completed":
        return "completed"
    if live_status == "failed":
        return "failed"
    return "blocked"


def _evaluate_case(
    session,
    replay_case: ReplayCase,
    *,
    live_executors: bool = False,
) -> ReplayEvaluation:
    source_run = (
        session.get(AgentRun, replay_case.source_agent_run_id)
        if replay_case.source_agent_run_id
        else None
    )
    tool_calls = (
        session.query(ToolCallRecord)
        .filter(ToolCallRecord.agent_run_id == replay_case.source_agent_run_id)
        .order_by(ToolCallRecord.created_at.asc())
        .all()
        if replay_case.source_agent_run_id
        else []
    )
    expected = replay_case.expected_json or {}
    observed = replay_case.observed_json or {}
    derived = _derived_observed(source_run, tool_calls)
    live_observed = _execute_live_replay(session, replay_case, expected) if live_executors else {}
    observed_for_eval = _merge_observed(derived, observed, live_observed)
    reasons = _evaluate_expectations(expected, observed_for_eval, derived, tool_calls)
    replay_verdict = _verdict_from_reasons(expected, reasons)
    return ReplayEvaluation(
        case_id=replay_case.id,
        case_type=replay_case.case_type,
        source_agent_run_id=replay_case.source_agent_run_id,
        stored_verdict=replay_case.verdict,
        replay_verdict=replay_verdict,
        reasons=reasons,
        query=_redact_text(replay_case.query),
        expected=_redact_json(expected),
        observed=_redact_json(observed_for_eval),
        tool_names=[tool_call.tool_name for tool_call in tool_calls],
        run_status=source_run.status if source_run else "",
    )


def _derived_observed(
    source_run: AgentRun | None,
    tool_calls: list[ToolCallRecord],
) -> dict[str, Any]:
    return {
        "run_status": source_run.status if source_run else "",
        "output": source_run.output_json if source_run else {},
        "error": source_run.error if source_run else "",
        "tool_names": [tool_call.tool_name for tool_call in tool_calls],
        "tool_statuses": {tool_call.tool_name: tool_call.status for tool_call in tool_calls},
        "tool_summaries": [tool_call.tool_result_summary for tool_call in tool_calls],
    }


def _merge_observed(
    derived: dict[str, Any],
    observed: dict[str, Any],
    live_observed: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(derived)
    merged.update(observed)
    merged.update(live_observed)
    return merged


def _execute_live_replay(
    session,
    replay_case: ReplayCase,
    expected: dict[str, Any],
) -> dict[str, Any]:
    if replay_case.case_type in {"context_search", "context_search_miss"}:
        return _execute_context_search_replay(session, replay_case, expected)
    return {}


def _execute_context_search_replay(
    session,
    replay_case: ReplayCase,
    expected: dict[str, Any],
) -> dict[str, Any]:
    metadata = replay_case.metadata_json or {}
    query = str(expected.get("query") or metadata.get("query") or replay_case.query or "").strip()
    if not query:
        return {
            "live_executor": "context_search",
            "live_status": "skipped",
            "live_error": "query missing",
        }

    paper_ids = [
        str(item)
        for item in _as_list(expected.get("paper_ids") or metadata.get("paper_ids"))
        if str(item).strip()
    ]
    graph_edge_types = [
        str(item)
        for item in _as_list(expected.get("graph_edge_types") or metadata.get("graph_edge_types"))
        if str(item).strip()
    ]
    limit = _bounded_int(expected.get("limit") or metadata.get("limit"), default=8, max_value=25)
    include_graph = _as_bool(expected.get("include_graph", metadata.get("include_graph", False)))

    try:
        embedding_service = EmbeddingService(session, embedding_provider_mode="local")
        result = RetrievalService(
            session,
            embedding_service=embedding_service,
            rerank_provider_mode="disabled",
        ).search_context(
            query=query,
            paper_ids=paper_ids,
            limit=limit,
            include_graph=include_graph,
            graph_edge_types=graph_edge_types,
        )
    except Exception as exc:
        return {
            "live_executor": "context_search",
            "live_status": "failed",
            "live_error": _redact_text(str(exc)),
            "query": _redact_text(query),
            "paper_ids": paper_ids,
        }

    chunk_ids = [item.item.id for item in result.chunks]
    evidence_ids = [item.item.id for item in result.evidences]
    gap_ids = [item.item.id for item in result.gaps]
    idea_ids = [item.item.id for item in result.ideas]
    return {
        "live_executor": "context_search",
        "live_status": "completed",
        "query": _redact_text(query),
        "paper_ids": paper_ids,
        "chunk_ids": chunk_ids,
        "evidence_ids": evidence_ids,
        "gap_ids": gap_ids,
        "idea_ids": idea_ids,
        "graph_node_ids": [node.id for node in result.graph_nodes],
        "graph_edge_ids": [edge.id for edge in result.graph_edges],
        "context_counts": {
            "chunks": len(chunk_ids),
            "evidences": len(evidence_ids),
            "gaps": len(gap_ids),
            "ideas": len(idea_ids),
            "graph_nodes": len(result.graph_nodes),
            "graph_edges": len(result.graph_edges),
        },
        "top_context": {
            "chunk_id": chunk_ids[0] if chunk_ids else "",
            "evidence_id": evidence_ids[0] if evidence_ids else "",
            "gap_id": gap_ids[0] if gap_ids else "",
            "idea_id": idea_ids[0] if idea_ids else "",
        },
        "answer_brief": _redact_text(result.answer_brief),
    }


def _evaluate_expectations(
    expected: dict[str, Any],
    observed: dict[str, Any],
    derived: dict[str, Any],
    tool_calls: list[ToolCallRecord],
) -> list[str]:
    if not expected:
        return ["No expected behavior was stored; manual review required."]

    failures: list[str] = []
    available_tools = set(_as_list(observed.get("tool_names"))) | {
        tool_call.tool_name for tool_call in tool_calls
    }
    observed_status = (
        observed.get("status") or observed.get("run_status") or derived.get("run_status")
    )
    text_blob = _flatten_text([observed, derived])

    required_tool = expected.get("tool") or expected.get("tool_name")
    if required_tool and required_tool not in available_tools:
        failures.append(f"Expected tool `{required_tool}` was not observed.")

    required_tools = set(_as_list(expected.get("required_tool_names")))
    missing_required_tools = sorted(required_tools - available_tools)
    if missing_required_tools:
        failures.append(f"Missing required tools: {', '.join(missing_required_tools)}.")

    forbidden_tools = set(_as_list(expected.get("forbidden_tool_names")))
    used_forbidden_tools = sorted(forbidden_tools & available_tools)
    if used_forbidden_tools:
        failures.append(f"Forbidden tools were observed: {', '.join(used_forbidden_tools)}.")

    expected_status = expected.get("status") or expected.get("run_status")
    if expected_status and observed_status != expected_status:
        failures.append(f"Expected status `{expected_status}` but observed `{observed_status}`.")

    expected_live_status = expected.get("live_status")
    if expected_live_status and observed.get("live_status") != expected_live_status:
        failures.append(
            "Expected live_status "
            f"`{expected_live_status}` but observed `{observed.get('live_status')}`."
        )

    _append_missing_ids(
        failures,
        "chunk",
        expected.get("required_chunk_ids"),
        observed.get("chunk_ids"),
    )
    _append_missing_ids(
        failures,
        "evidence",
        expected.get("required_evidence_ids"),
        observed.get("evidence_ids"),
    )
    _append_missing_ids(
        failures,
        "gap",
        expected.get("required_gap_ids"),
        observed.get("gap_ids"),
    )
    _append_missing_ids(
        failures,
        "idea",
        expected.get("required_idea_ids"),
        observed.get("idea_ids"),
    )

    context_counts = observed.get("context_counts") or {}
    _append_min_count_failure(
        failures,
        "chunk",
        expected.get("min_chunk_count"),
        context_counts.get("chunks", len(_as_list(observed.get("chunk_ids")))),
    )
    _append_min_count_failure(
        failures,
        "evidence",
        expected.get("min_evidence_count"),
        context_counts.get("evidences", len(_as_list(observed.get("evidence_ids")))),
    )
    _append_min_count_failure(
        failures,
        "gap",
        expected.get("min_gap_count"),
        context_counts.get("gaps", len(_as_list(observed.get("gap_ids")))),
    )
    _append_min_count_failure(
        failures,
        "idea",
        expected.get("min_idea_count"),
        context_counts.get("ideas", len(_as_list(observed.get("idea_ids")))),
    )

    for required_text in _as_list(expected.get("must_contain")):
        if str(required_text).lower() not in text_blob:
            failures.append(f"Expected text `{required_text}` was not found.")

    forbidden_terms = _as_list(expected.get("must_not_contain")) + _as_list(
        expected.get("forbidden_terms")
    )
    for forbidden_text in forbidden_terms:
        if str(forbidden_text).lower() in text_blob:
            failures.append(f"Forbidden text `{forbidden_text}` was found.")

    special_keys = {
        "tool",
        "tool_name",
        "required_tool_names",
        "forbidden_tool_names",
        "status",
        "run_status",
        "live_status",
        "must_contain",
        "must_not_contain",
        "forbidden_terms",
        "query",
        "paper_ids",
        "graph_edge_types",
        "include_graph",
        "limit",
        "required_chunk_ids",
        "required_evidence_ids",
        "required_gap_ids",
        "required_idea_ids",
        "min_chunk_count",
        "min_evidence_count",
        "min_gap_count",
        "min_idea_count",
    }
    for key, expected_value in expected.items():
        if key in special_keys:
            continue
        observed_value = observed.get(key, derived.get(key))
        if observed_value != expected_value:
            failures.append(
                f"Expected `{key}` to equal `{expected_value}` but observed `{observed_value}`."
            )

    return failures or ["All replay expectations matched."]


def _append_missing_ids(
    failures: list[str],
    label: str,
    expected_ids: Any,
    observed_ids: Any,
) -> None:
    required = {str(item) for item in _as_list(expected_ids)}
    if not required:
        return
    observed = {str(item) for item in _as_list(observed_ids)}
    missing = sorted(required - observed)
    if missing:
        failures.append(f"Missing required {label} ids: {', '.join(missing)}.")


def _append_min_count_failure(
    failures: list[str],
    label: str,
    expected_count: Any,
    observed_count: Any,
) -> None:
    if expected_count is None:
        return
    minimum = _bounded_int(expected_count, default=0, max_value=10_000, min_value=0)
    try:
        observed_int = int(observed_count)
    except (TypeError, ValueError):
        observed_int = 0
    if observed_int < minimum:
        failures.append(f"Expected at least {minimum} {label} results but observed {observed_int}.")


def _verdict_from_reasons(expected: dict[str, Any], reasons: list[str]) -> str:
    if not expected:
        return "needs_review"
    return "fail" if any(not reason.startswith("All ") for reason in reasons) else "pass"


def _build_report_payload(evaluations: list[ReplayEvaluation]) -> dict[str, Any]:
    passed = sum(1 for item in evaluations if item.replay_verdict == "pass")
    failed = sum(1 for item in evaluations if item.replay_verdict == "fail")
    needs_review = sum(1 for item in evaluations if item.replay_verdict == "needs_review")
    return {
        "summary": {
            "case_count": len(evaluations),
            "passed": passed,
            "failed": failed,
            "needs_review": needs_review,
            "pass_rate": round(passed / len(evaluations), 4) if evaluations else 0.0,
        },
        "cases": [item.to_json() for item in evaluations],
    }


def _render_console_summary(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "Agent replay evaluation complete.",
        (
            f"cases={summary['case_count']} pass={summary['passed']} "
            f"fail={summary['failed']} needs_review={summary['needs_review']} "
            f"pass_rate={summary['pass_rate']}"
        ),
    ]
    for item in payload["cases"]:
        lines.append(f"- {item['case_id']} [{item['case_type']}]: {item['replay_verdict']}")
    return "\n".join(lines)


def _render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Agent Replay Evaluation",
        "",
        "## Summary",
        "",
        f"- Case count: {summary['case_count']}",
        f"- Passed: {summary['passed']}",
        f"- Failed: {summary['failed']}",
        f"- Needs review: {summary['needs_review']}",
        f"- Pass rate: {summary['pass_rate']}",
        "",
        "## Cases",
        "",
        "| Case | Type | Stored Verdict | Replay Verdict | Tools |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in payload["cases"]:
        tools = ", ".join(item["tool_names"]) or "none"
        lines.append(
            f"| `{item['case_id']}` | `{item['case_type']}` | "
            f"`{item['stored_verdict']}` | `{item['replay_verdict']}` | {tools} |"
        )
    for item in payload["cases"]:
        lines.extend(
            [
                "",
                f"### Case `{item['case_id']}`",
                "",
                f"- Query: {_escape_markdown(item['query'])}",
                f"- Source agent run: `{item['source_agent_run_id'] or ''}`",
                "",
                "Reasons:",
            ]
        )
        for reason in item["reasons"]:
            lines.append(f"- {_escape_markdown(reason)}")
    lines.append("")
    return "\n".join(lines)


def _as_list(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    return [value]


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _bounded_int(value: Any, *, default: int, max_value: int, min_value: int = 1) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(min_value, min(number, max_value))


def _flatten_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten_text(item) for item in value.values()).lower()
    if isinstance(value, list):
        return " ".join(_flatten_text(item) for item in value).lower()
    return _redact_text(str(value)).lower()


def _redact_json(value: Any) -> Any:
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            if any(part in str(key).lower() for part in SENSITIVE_KEY_PARTS):
                redacted[key] = "[redacted]"
            else:
                redacted[key] = _redact_json(item)
        return redacted
    if isinstance(value, list):
        return [_redact_json(item) for item in value]
    if isinstance(value, str):
        return _redact_text(value)
    return value


def _redact_text(value: str) -> str:
    return SECRET_VALUE_PATTERN.sub("[redacted]", value or "")


def _escape_markdown(value: str) -> str:
    return value.replace("|", "\\|")


if __name__ == "__main__":
    raise SystemExit(main())
