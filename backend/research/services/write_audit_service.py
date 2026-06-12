from __future__ import annotations

from collections import Counter, deque
from datetime import UTC, datetime
import json
import os
from pathlib import Path
from typing import Any, Mapping

from backend.research.config import settings


WRITE_AUDIT_FILENAME = "write-operations.jsonl"
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
TRUTHY = {"1", "true", "yes", "on"}
SENSITIVE_METADATA_TERMS = (
    "api_key",
    "token",
    "cookie",
    "secret",
    "password",
    "credential",
    "private_key",
    "request_body",
    "body",
    "payload",
    "content",
    "prompt",
    "model_response",
)
METADATA_KEY_ALLOWLIST = {"api_key_fingerprint", "query_keys"}


def write_audit_enabled() -> bool:
    raw = os.getenv("WRITE_AUDIT_ENABLED")
    if raw is None:
        return settings.write_audit_enabled
    return raw.strip().lower() in TRUTHY


def write_audit_dir() -> Path:
    return Path(os.getenv("WRITE_AUDIT_DIR") or settings.write_audit_dir)


def write_audit_path() -> Path:
    return write_audit_dir() / WRITE_AUDIT_FILENAME


def export_write_audit_events(
    *,
    max_records: int = 100,
    start_created_at: str = "",
    end_created_at: str = "",
) -> list[dict[str, Any]]:
    path = write_audit_path()
    if not path.exists() or max_records < 1:
        return []

    records: list[dict[str, Any]] = []
    bounded_max = min(max_records, 1000)
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            event = _load_audit_event(line)
            if event is None or not _event_in_created_at_range(
                event,
                start_created_at=start_created_at,
                end_created_at=end_created_at,
            ):
                continue
            records.append(_sanitize_event(event))
            if len(records) >= bounded_max:
                break
    return records


def render_write_audit_export_jsonl(records: list[dict[str, Any]]) -> str:
    if not records:
        return ""
    return (
        "\n".join(json.dumps(record, ensure_ascii=True, sort_keys=True) for record in records)
        + "\n"
    )


def summarize_write_audit_events(max_events: int = 1000) -> dict[str, Any]:
    path = write_audit_path()
    summary = {
        "generated_at": datetime.now(UTC),
        "source": "jsonl",
        "audit_file_present": path.exists(),
        "event_count": 0,
        "total_line_count": 0,
        "lines_scanned": 0,
        "invalid_line_count": 0,
        "truncated": False,
        "max_events_scanned": max_events,
        "latest_created_at": "",
        "counts_by_operation": {},
        "counts_by_entity_type": {},
        "counts_by_status": {},
        "counts_by_http_status": {},
        "counts_by_actor_type": {},
        "counts_by_route": {},
        "counts_by_error_type": {},
        "recent_request_ids": [],
        "message": "No write-operation audit file found.",
    }
    if not path.exists():
        return summary

    recent_lines: deque[str] = deque(maxlen=max_events)
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            summary["total_line_count"] += 1
            recent_lines.append(line)

    summary["truncated"] = summary["total_line_count"] > max_events
    summary["lines_scanned"] = len(recent_lines)

    counts_by_operation: Counter[str] = Counter()
    counts_by_entity_type: Counter[str] = Counter()
    counts_by_status: Counter[str] = Counter()
    counts_by_http_status: Counter[str] = Counter()
    counts_by_actor_type: Counter[str] = Counter()
    counts_by_route: Counter[str] = Counter()
    counts_by_error_type: Counter[str] = Counter()
    recent_request_ids: list[str] = []

    for line in recent_lines:
        event = _load_audit_event(line)
        if event is None:
            if line.strip():
                summary["invalid_line_count"] += 1
            continue

        summary["event_count"] += 1
        _count_string(event, "operation", counts_by_operation)
        _count_string(event, "entity_type", counts_by_entity_type)
        _count_string(event, "status", counts_by_status)
        _count_string(event, "actor_type", counts_by_actor_type)
        _count_string(event, "path_template", counts_by_route)
        _count_string(event, "error_type", counts_by_error_type)
        http_status = event.get("http_status")
        if isinstance(http_status, int):
            counts_by_http_status[str(http_status)] += 1
        request_id = event.get("request_id")
        if isinstance(request_id, str) and request_id:
            recent_request_ids.append(request_id)
        created_at = event.get("created_at")
        if isinstance(created_at, str) and created_at:
            summary["latest_created_at"] = created_at

    summary.update(
        {
            "counts_by_operation": _sorted_counts(counts_by_operation),
            "counts_by_entity_type": _sorted_counts(counts_by_entity_type),
            "counts_by_status": _sorted_counts(counts_by_status),
            "counts_by_http_status": _sorted_counts(counts_by_http_status),
            "counts_by_actor_type": _sorted_counts(counts_by_actor_type),
            "counts_by_route": _sorted_counts(counts_by_route),
            "counts_by_error_type": _sorted_counts(counts_by_error_type),
            "recent_request_ids": recent_request_ids[-20:],
            "message": "Generated sanitized write-operation audit summary.",
        }
    )
    return summary


def is_write_operation(method: str, path: str) -> bool:
    return method.upper() in WRITE_METHODS and (
        path == "/research" or path.startswith("/research/")
    )


def operation_for_request(method: str, path: str) -> str:
    normalized = path.rstrip("/").lower()
    method = method.upper()
    if "upload" in normalized:
        return "upload"
    if normalized.endswith("/cancel"):
        return "cancel"
    if normalized.endswith("/retry"):
        return "retry"
    if "export" in normalized:
        return "export" if method == "GET" else "create"
    if method == "POST":
        return "create"
    if method in {"PUT", "PATCH"}:
        return "update"
    if method == "DELETE":
        return "delete"
    return "write"


def entity_type_for_path(path_template: str) -> str:
    segments = [segment for segment in path_template.strip("/").split("/") if segment]
    if segments and segments[0] == "research":
        segments = segments[1:]
    if not segments:
        return "research"
    if segments[:2] == ["export", "project-bundle"]:
        return "project_bundle"
    if segments[0] == "papers":
        return "paper"
    if segments[0] == "tasks":
        return "task"
    if segments[0] == "jobs":
        return "job"
    if segments[0] == "ideas":
        return "idea"
    return segments[0].replace("-", "_")


def append_write_audit_event(event: Mapping[str, Any]) -> Path:
    path = write_audit_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _sanitize_event(event)
    payload.setdefault("created_at", datetime.now(UTC).isoformat())
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n")
    return path


def _load_audit_event(line: str) -> Mapping[str, Any] | None:
    if not line.strip():
        return None
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(event, Mapping):
        return None
    return event


def _event_in_created_at_range(
    event: Mapping[str, Any],
    *,
    start_created_at: str,
    end_created_at: str,
) -> bool:
    created_at = event.get("created_at")
    if not isinstance(created_at, str) or not created_at:
        return not start_created_at and not end_created_at
    if start_created_at and created_at < start_created_at:
        return False
    return not (end_created_at and created_at > end_created_at)


def _count_string(event: Mapping[str, Any], key: str, counter: Counter[str]) -> None:
    value = event.get(key)
    if isinstance(value, str) and value:
        counter[value] += 1


def _sorted_counts(counter: Counter[str]) -> dict[str, int]:
    return dict(sorted(counter.items()))


def _sanitize_event(event: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {
        "id",
        "created_at",
        "request_id",
        "actor_type",
        "actor_label",
        "method",
        "path_template",
        "tool_name",
        "operation",
        "entity_type",
        "entity_id",
        "status",
        "http_status",
        "error_type",
        "policy",
        "duration_ms",
        "commit_sha",
        "metadata",
    }
    sanitized: dict[str, Any] = {}
    for key, value in event.items():
        if key not in allowed or value is None:
            continue
        if key == "metadata" and isinstance(value, Mapping):
            sanitized[key] = _sanitize_metadata(value)
        elif isinstance(value, (str, int, float, bool)):
            sanitized[key] = value
    return sanitized


def _sanitize_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in metadata.items():
        normalized_key = str(key)
        if value is None or _metadata_key_is_sensitive(normalized_key):
            continue
        if isinstance(value, (str, int, float, bool)):
            sanitized[normalized_key] = value
        elif isinstance(value, list) and all(isinstance(item, str) for item in value):
            sanitized[normalized_key] = value[:20]
    return sanitized


def _metadata_key_is_sensitive(key: str) -> bool:
    normalized = key.strip().lower()
    if normalized in METADATA_KEY_ALLOWLIST:
        return False
    return any(term in normalized for term in SENSITIVE_METADATA_TERMS)
