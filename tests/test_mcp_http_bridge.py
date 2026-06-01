import json

from scripts import mcp_http_bridge


def test_tool_list_result_maps_mcp_tool_shape() -> None:
    spec = {
        "tools": [
            {
                "name": "get_idea_progress",
                "description": "Load idea progress.",
                "input_schema": {
                    "type": "object",
                    "properties": {"idea_id": {"type": "string"}},
                    "required": ["idea_id"],
                },
                "annotations": {"readOnlyHint": True},
            }
        ]
    }

    result = mcp_http_bridge.tool_list_result(spec)

    assert result["tools"][0]["name"] == "get_idea_progress"
    assert result["tools"][0]["inputSchema"]["required"] == ["idea_id"]
    assert result["tools"][0]["annotations"]["readOnlyHint"] is True


def test_fill_path_parameters_encodes_arguments() -> None:
    path = mcp_http_bridge.fill_path_parameters(
        "/research/ideas/{idea_id}/timeline",
        {"idea_id": "idea with/slash"},
    )

    assert path == "/research/ideas/idea%20with%2Fslash/timeline"


def test_handle_initialize_and_unknown_tool() -> None:
    spec = {"tools": []}

    init = mcp_http_bridge.handle_request(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize"},
        base_url="http://localhost:8000",
        spec=spec,
        timeout=1,
    )
    missing = mcp_http_bridge.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "missing", "arguments": {}},
        },
        base_url="http://localhost:8000",
        spec=spec,
        timeout=1,
    )

    assert init is not None
    assert init["result"]["capabilities"]["tools"]["listChanged"] is False
    assert missing is not None
    assert missing["error"]["code"] == -32000
    assert "Unknown tool" in missing["error"]["message"]


def test_zip_tool_content_is_base64_text() -> None:
    result = mcp_http_bridge._tool_content(b"zip-bytes", "application/zip")
    payload = json.loads(result["content"][0]["text"])

    assert payload["content_type"] == "application/zip"
    assert payload["base64"]
