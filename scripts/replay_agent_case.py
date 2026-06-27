#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.research.db import SessionLocal
from backend.research.models import AgentRun, ReplayCase, ToolCallRecord


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
        description="Replay saved local agent bad cases without calling model providers or tools.",
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
    args = parser.parse_args()

    with SessionLocal() as session:
        cases = _load_cases(
            session,
            case_id=args.case_id,
            case_type=args.case_type,
            verdict=args.verdict,
            limit=args.limit,
        )
        evaluations = [_evaluate_case(session, replay_case) for replay_case in cases]

    payload = _build_report_payload(evaluations)
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


def _evaluate_case(session, replay_case: ReplayCase) -> ReplayEvaluation:
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
    reasons = _evaluate_expectations(expected, observed, derived, tool_calls)
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
        observed=_redact_json(observed or derived),
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
        "must_contain",
        "must_not_contain",
        "forbidden_terms",
    }
    for key, expected_value in expected.items():
        if key in special_keys:
            continue
        observed_value = observed.get(key, derived.get(key))
        if observed_value != expected_value:
            failures.append(
                f"Expected `{key}` to equal `{expected_value}` but observed `{observed_value}`."
            )

    return failures or ["All deterministic expectations matched."]


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
