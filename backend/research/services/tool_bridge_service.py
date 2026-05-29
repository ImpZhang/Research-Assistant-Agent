import re
from typing import Any

from backend.research.schemas import ToolBridgeSpecItem, ToolManifestItem


PATH_PARAMETER_PATTERN = re.compile(r"{([^}/]+)}")


def build_tool_bridge_items(tools: list[ToolManifestItem]) -> list[ToolBridgeSpecItem]:
    return [_build_tool_bridge_item(tool) for tool in tools]


def _build_tool_bridge_item(tool: ToolManifestItem) -> ToolBridgeSpecItem:
    return ToolBridgeSpecItem(
        name=tool.name,
        description=tool.description,
        input_schema=_build_input_schema(tool),
        http={
            "method": tool.method,
            "path": tool.path,
            "input_model": tool.input_model,
            "output_model": tool.output_model,
            "content_type": _content_type_for_tool(tool),
        },
        output_model=tool.output_model,
        side_effect=tool.side_effect,
        annotations=_build_annotations(tool),
    )


def _build_input_schema(tool: ToolManifestItem) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: list[str] = []
    for parameter in PATH_PARAMETER_PATTERN.findall(tool.path):
        properties[parameter] = {
            "type": "string",
            "description": f"Path parameter `{parameter}` for {tool.path}.",
        }
        required.append(parameter)

    if tool.input_model == "multipart/form-data":
        properties["file_path"] = {
            "type": "string",
            "description": "Local path to the file that the bridge should upload as multipart data.",
        }
        required.append("file_path")
    elif tool.input_model:
        properties["body"] = {
            "type": "object",
            "description": f"JSON request body matching `{tool.input_model}`.",
            "additionalProperties": True,
        }
        if tool.method in {"POST", "PATCH", "PUT"}:
            required.append("body")

    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": required,
    }


def _content_type_for_tool(tool: ToolManifestItem) -> str:
    if tool.input_model == "multipart/form-data":
        return "multipart/form-data"
    if tool.method in {"POST", "PATCH", "PUT"}:
        return "application/json"
    return ""


def _build_annotations(tool: ToolManifestItem) -> dict[str, Any]:
    read_only = tool.method == "GET" and not tool.side_effect
    destructive = tool.name in {"cancel_job"} or tool.name.startswith("delete_")
    return {
        "readOnlyHint": read_only,
        "destructiveHint": destructive,
        "idempotentHint": read_only,
        "sideEffectHint": tool.side_effect,
    }
