"""Minimal stdio MCP-to-HTTP bridge for Research Assistant Agent.

This script intentionally avoids MCP SDK dependencies. It implements the small
JSON-RPC surface needed by tool-capable clients: initialize, tools/list, and
tools/call. Tool definitions are loaded from /research/tools/mcp-spec so the
FastAPI manifest remains the single source of truth.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


JSON = dict[str, Any]


@dataclass(frozen=True)
class BridgePolicy:
    allow_tools: frozenset[str] = frozenset()
    deny_tools: frozenset[str] = frozenset()
    read_only: bool = False


@dataclass(frozen=True)
class BridgeAuth:
    api_key: str = ""
    header_name: str = "X-Research-Assistant-Key"


@dataclass(frozen=True)
class BridgeScope:
    project_id: str = ""
    header_name: str = "X-Research-Assistant-Project"


def load_tool_spec(
    base_url: str,
    timeout: float = 30.0,
    auth: BridgeAuth | None = None,
    scope: BridgeScope | None = None,
) -> JSON:
    request = urllib.request.Request(
        _join_url(base_url, "/research/tools/mcp-spec"),
        headers={"Accept": "application/json", **_auth_headers(auth), **_scope_headers(scope)},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def index_tools(spec: JSON) -> dict[str, JSON]:
    return {tool["name"]: tool for tool in spec.get("tools", [])}


def filter_spec_tools(spec: JSON, policy: BridgePolicy) -> JSON:
    filtered = dict(spec)
    filtered["tools"] = [tool for tool in spec.get("tools", []) if tool_allowed(tool, policy)]
    return filtered


def tool_allowed(tool: JSON, policy: BridgePolicy) -> bool:
    name = tool.get("name", "")
    if policy.allow_tools and name not in policy.allow_tools:
        return False
    if name in policy.deny_tools:
        return False
    if policy.read_only and not tool.get("annotations", {}).get("readOnlyHint", False):
        return False
    return True


def bridge_health(
    spec: JSON,
    policy: BridgePolicy,
    auth: BridgeAuth | None = None,
    scope: BridgeScope | None = None,
) -> JSON:
    filtered = filter_spec_tools(spec, policy)
    all_names = sorted(tool.get("name", "") for tool in spec.get("tools", []) if tool.get("name"))
    exposed_names = sorted(
        tool.get("name", "") for tool in filtered.get("tools", []) if tool.get("name")
    )
    blocked_names = sorted(set(all_names) - set(exposed_names))
    return {
        "status": "ok",
        "total_tools": len(all_names),
        "exposed_tools": len(exposed_names),
        "blocked_tools": len(blocked_names),
        "policy": {
            "read_only": policy.read_only,
            "allow_tools": sorted(policy.allow_tools),
            "deny_tools": sorted(policy.deny_tools),
        },
        "auth": {
            "api_key_configured": bool(auth and auth.api_key),
            "header_name": auth.header_name if auth else "X-Research-Assistant-Key",
        },
        "scope": {
            "project_id_configured": bool(scope and scope.project_id),
            "project_id": scope.project_id if scope else "",
            "header_name": scope.header_name if scope else "X-Research-Assistant-Project",
        },
        "tools": exposed_names,
        "blocked": blocked_names,
    }


def tool_list_result(spec: JSON) -> JSON:
    return {
        "tools": [
            {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "inputSchema": tool.get("input_schema", {"type": "object"}),
                "annotations": tool.get("annotations", {}),
            }
            for tool in spec.get("tools", [])
        ]
    }


def call_tool(
    base_url: str,
    tool: JSON,
    arguments: JSON,
    timeout: float = 60.0,
    auth: BridgeAuth | None = None,
    scope: BridgeScope | None = None,
) -> JSON:
    method = tool.get("http", {}).get("method", "GET")
    path = fill_path_parameters(tool.get("http", {}).get("path", ""), arguments)
    url = _join_url(base_url, path)
    content_type = tool.get("http", {}).get("content_type", "")
    body = arguments.get("body", {})
    headers = {
        "Accept": "application/json, text/plain, application/zip",
        **_auth_headers(auth),
        **_scope_headers(scope),
    }
    data: bytes | None = None

    if content_type == "multipart/form-data":
        data, boundary = _multipart_file_body(arguments["file_path"])
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    elif method in {"POST", "PATCH", "PUT"}:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read()
            return _tool_content(payload, response.headers.get("content-type", ""))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {tool['name']}: {detail}") from exc


def fill_path_parameters(path: str, arguments: JSON) -> str:
    rendered = path
    for key, value in arguments.items():
        if key == "body":
            continue
        rendered = rendered.replace("{" + key + "}", urllib.parse.quote(str(value), safe=""))
    if "{" in rendered or "}" in rendered:
        raise ValueError(f"Missing path parameter for {path}")
    return rendered


def handle_request(
    message: JSON,
    *,
    base_url: str,
    spec: JSON,
    timeout: float,
    auth: BridgeAuth | None = None,
    scope: BridgeScope | None = None,
) -> JSON | None:
    method = message.get("method")
    request_id = message.get("id")
    try:
        if method == "initialize":
            return _response(
                request_id,
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {
                        "name": "research-assistant-agent-http-bridge",
                        "version": "0.1.0",
                    },
                },
            )
        if method == "notifications/initialized":
            return None
        if method == "tools/list":
            return _response(request_id, tool_list_result(spec))
        if method == "tools/call":
            params = message.get("params", {})
            tools = index_tools(spec)
            name = params.get("name")
            if name not in tools:
                raise ValueError(f"Unknown tool: {name}")
            result = call_tool(
                base_url,
                tools[name],
                params.get("arguments", {}),
                timeout,
                auth=auth,
                scope=scope,
            )
            return _response(request_id, result)
        raise ValueError(f"Unsupported method: {method}")
    except Exception as exc:  # MCP transports expect errors as JSON-RPC payloads.
        return _error(request_id, str(exc))


def serve_stdio(
    base_url: str,
    timeout: float,
    policy: BridgePolicy,
    auth: BridgeAuth,
    scope: BridgeScope,
) -> None:
    spec = filter_spec_tools(
        load_tool_spec(base_url, timeout=timeout, auth=auth, scope=scope), policy
    )
    for line in sys.stdin:
        if not line.strip():
            continue
        response = handle_request(
            json.loads(line),
            base_url=base_url,
            spec=spec,
            timeout=timeout,
            auth=auth,
            scope=scope,
        )
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()


def _tool_content(payload: bytes, content_type: str) -> JSON:
    if "application/zip" in content_type:
        text = json.dumps(
            {
                "content_type": "application/zip",
                "base64": base64.b64encode(payload).decode("ascii"),
            }
        )
    else:
        text = payload.decode("utf-8", errors="replace")
    return {"content": [{"type": "text", "text": text}]}


def _multipart_file_body(file_path: str) -> tuple[bytes, str]:
    path = Path(file_path)
    if not path.is_file():
        raise ValueError(f"Upload file not found: {file_path}")
    boundary = f"----research-assistant-{uuid.uuid4().hex}"
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
        f"Content-Type: {mime_type}\r\n\r\n"
    ).encode("utf-8")
    tail = f"\r\n--{boundary}--\r\n".encode("utf-8")
    return head + path.read_bytes() + tail, boundary


def _join_url(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + "/" + path.lstrip("/")


def _response(request_id: Any, result: JSON) -> JSON:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, message: str) -> JSON:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32000, "message": message}}


def _auth_headers(auth: BridgeAuth | None) -> dict[str, str]:
    if not auth or not auth.api_key:
        return {}
    return {auth.header_name: auth.api_key}


def _scope_headers(scope: BridgeScope | None) -> dict[str, str]:
    if not scope or not scope.project_id:
        return {}
    return {scope.header_name: scope.project_id}


def _build_policy(args: argparse.Namespace) -> BridgePolicy:
    return BridgePolicy(
        allow_tools=_parse_tool_names(args.allow_tool, os.environ.get("MCP_BRIDGE_ALLOW_TOOLS")),
        deny_tools=_parse_tool_names(args.deny_tool, os.environ.get("MCP_BRIDGE_DENY_TOOLS")),
        read_only=args.read_only or _env_flag("MCP_BRIDGE_READ_ONLY"),
    )


def _build_auth(args: argparse.Namespace) -> BridgeAuth:
    api_key = (
        args.api_key
        or os.environ.get("MCP_BRIDGE_API_KEY", "")
        or os.environ.get("RESEARCH_ASSISTANT_API_KEY", "")
        or os.environ.get("API_KEY", "")
    )
    header_name = (
        args.api_key_header
        or os.environ.get("MCP_BRIDGE_API_KEY_HEADER", "")
        or os.environ.get("API_KEY_HEADER_NAME", "")
        or "X-Research-Assistant-Key"
    )
    return BridgeAuth(api_key=api_key, header_name=header_name)


def _build_scope(args: argparse.Namespace) -> BridgeScope:
    project_id = (
        args.project_id
        or os.environ.get("MCP_BRIDGE_PROJECT_ID", "")
        or os.environ.get("RESEARCH_ASSISTANT_PROJECT_ID", "")
    )
    header_name = (
        args.project_header
        or os.environ.get("MCP_BRIDGE_PROJECT_HEADER", "")
        or os.environ.get("RESEARCH_ASSISTANT_PROJECT_HEADER", "")
        or "X-Research-Assistant-Project"
    )
    return BridgeScope(project_id=project_id, header_name=header_name)


def _parse_tool_names(values: list[str], env_value: str | None) -> frozenset[str]:
    names: list[str] = []
    for raw in [*(values or []), env_value or ""]:
        names.extend(part.strip() for part in raw.split(",") if part.strip())
    return frozenset(names)


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Research Assistant MCP HTTP bridge.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument(
        "--allow-tool",
        action="append",
        default=[],
        help="Expose only this tool name. Repeat or pass comma-separated names.",
    )
    parser.add_argument(
        "--deny-tool",
        action="append",
        default=[],
        help="Hide this tool name. Repeat or pass comma-separated names.",
    )
    parser.add_argument(
        "--read-only",
        action="store_true",
        help="Expose only tools marked with readOnlyHint in the bridge spec.",
    )
    parser.add_argument(
        "--health-check",
        action="store_true",
        help="Load the bridge spec, print filtered tool counts as JSON, and exit.",
    )
    parser.add_argument(
        "--api-key",
        default="",
        help="API key forwarded to protected Research Assistant HTTP routes.",
    )
    parser.add_argument(
        "--api-key-header",
        default="",
        help="Header name used for API key forwarding.",
    )
    parser.add_argument(
        "--project-id",
        default="",
        help="Non-secret project id forwarded with Research Assistant tool calls.",
    )
    parser.add_argument(
        "--project-header",
        default="",
        help="Header name used for project id forwarding.",
    )
    args = parser.parse_args()
    policy = _build_policy(args)
    auth = _build_auth(args)
    scope = _build_scope(args)
    if args.health_check:
        spec = load_tool_spec(args.base_url, timeout=args.timeout, auth=auth, scope=scope)
        sys.stdout.write(
            json.dumps(bridge_health(spec, policy, auth, scope), ensure_ascii=False, indent=2)
            + "\n"
        )
        return
    serve_stdio(args.base_url, args.timeout, policy, auth, scope)


if __name__ == "__main__":
    main()
