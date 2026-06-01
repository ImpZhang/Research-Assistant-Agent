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


def test_bridge_policy_filters_allow_deny_and_read_only_tools() -> None:
    spec = {
        "tools": [
            {
                "name": "get_idea_progress",
                "annotations": {"readOnlyHint": True},
            },
            {
                "name": "update_research_profile",
                "annotations": {"readOnlyHint": False, "sideEffectHint": True},
            },
            {
                "name": "cancel_job",
                "annotations": {"readOnlyHint": False, "destructiveHint": True},
            },
        ]
    }

    read_only = mcp_http_bridge.filter_spec_tools(
        spec,
        mcp_http_bridge.BridgePolicy(read_only=True),
    )
    allow_and_deny = mcp_http_bridge.filter_spec_tools(
        spec,
        mcp_http_bridge.BridgePolicy(
            allow_tools=frozenset({"get_idea_progress", "update_research_profile"}),
            deny_tools=frozenset({"update_research_profile"}),
        ),
    )

    assert [tool["name"] for tool in read_only["tools"]] == ["get_idea_progress"]
    assert [tool["name"] for tool in allow_and_deny["tools"]] == ["get_idea_progress"]


def test_bridge_health_reports_policy_counts() -> None:
    spec = {
        "tools": [
            {"name": "get_project_progress", "annotations": {"readOnlyHint": True}},
            {"name": "create_research_plan", "annotations": {"readOnlyHint": False}},
        ]
    }

    health = mcp_http_bridge.bridge_health(
        spec,
        mcp_http_bridge.BridgePolicy(read_only=True),
    )

    assert health["status"] == "ok"
    assert health["total_tools"] == 2
    assert health["exposed_tools"] == 1
    assert health["blocked_tools"] == 1
    assert health["policy"]["read_only"] is True
    assert health["tools"] == ["get_project_progress"]
    assert health["blocked"] == ["create_research_plan"]


def test_parse_tool_names_accepts_repeated_and_comma_values() -> None:
    parsed = mcp_http_bridge._parse_tool_names(
        ["get_project_progress,get_idea_progress", "get_research_profile"],
        "get_tool_manifest",
    )

    assert parsed == frozenset(
        {
            "get_project_progress",
            "get_idea_progress",
            "get_research_profile",
            "get_tool_manifest",
        }
    )


def test_zip_tool_content_is_base64_text() -> None:
    result = mcp_http_bridge._tool_content(b"zip-bytes", "application/zip")
    payload = json.loads(result["content"][0]["text"])

    assert payload["content_type"] == "application/zip"
    assert payload["base64"]
