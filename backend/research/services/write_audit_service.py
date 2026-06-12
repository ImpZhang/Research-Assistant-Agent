from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path
from typing import Any, Mapping

from backend.research.config import settings


WRITE_AUDIT_FILENAME = "write-operations.jsonl"
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
TRUTHY = {"1", "true", "yes", "on"}


def write_audit_enabled() -> bool:
    raw = os.getenv("WRITE_AUDIT_ENABLED")
    if raw is None:
        return settings.write_audit_enabled
    return raw.strip().lower() in TRUTHY


def write_audit_dir() -> Path:
    return Path(os.getenv("WRITE_AUDIT_DIR") or settings.write_audit_dir)


def write_audit_path() -> Path:
    return write_audit_dir() / WRITE_AUDIT_FILENAME


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
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            sanitized[str(key)] = value
        elif isinstance(value, list) and all(isinstance(item, str) for item in value):
            sanitized[str(key)] = value[:20]
    return sanitized
