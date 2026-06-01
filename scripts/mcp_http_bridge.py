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
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any


JSON = dict[str, Any]


def load_tool_spec(base_url: str, timeout: float = 30.0) -> JSON:
    request = urllib.request.Request(
        _join_url(base_url, "/research/tools/mcp-spec"),
        headers={"Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def index_tools(spec: JSON) -> dict[str, JSON]:
    return {tool["name"]: tool for tool in spec.get("tools", [])}


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


def call_tool(base_url: str, tool: JSON, arguments: JSON, timeout: float = 60.0) -> JSON:
    method = tool.get("http", {}).get("method", "GET")
    path = fill_path_parameters(tool.get("http", {}).get("path", ""), arguments)
    url = _join_url(base_url, path)
    content_type = tool.get("http", {}).get("content_type", "")
    body = arguments.get("body", {})
    headers = {"Accept": "application/json, text/plain, application/zip"}
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


def handle_request(message: JSON, *, base_url: str, spec: JSON, timeout: float) -> JSON | None:
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
            result = call_tool(base_url, tools[name], params.get("arguments", {}), timeout)
            return _response(request_id, result)
        raise ValueError(f"Unsupported method: {method}")
    except Exception as exc:  # MCP transports expect errors as JSON-RPC payloads.
        return _error(request_id, str(exc))


def serve_stdio(base_url: str, timeout: float) -> None:
    spec = load_tool_spec(base_url, timeout=timeout)
    for line in sys.stdin:
        if not line.strip():
            continue
        response = handle_request(
            json.loads(line),
            base_url=base_url,
            spec=spec,
            timeout=timeout,
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Research Assistant MCP HTTP bridge.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()
    serve_stdio(args.base_url, args.timeout)


if __name__ == "__main__":
    main()
