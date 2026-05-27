from __future__ import annotations

import json
from typing import Any

from agent_factory.llm.messages import ToolCallResponse


def tool_call_from_openai(function_name: str, arguments_json: str) -> ToolCallResponse:
    try:
        arguments = json.loads(arguments_json or "{}")
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Invalid tool arguments: {arguments_json!r}") from error

    if function_name == "http_get":
        return ToolCallResponse(tool="http", operation="GET", target=str(arguments.get("url", "")).strip())

    if function_name == "filesystem_read":
        return ToolCallResponse(
            tool="filesystem",
            operation="read",
            target=str(arguments.get("path", "")).strip(),
        )

    if function_name == "filesystem_write":
        return ToolCallResponse(
            tool="filesystem",
            operation="write",
            target=str(arguments.get("path", "")).strip(),
            content=str(arguments.get("content", "")),
        )

    raise RuntimeError(f"Unsupported tool call from model: {function_name}")


def tool_call_from_openai_message(tool_call: dict[str, Any]) -> ToolCallResponse:
    function = tool_call.get("function") or {}
    return tool_call_from_openai(function.get("name", ""), function.get("arguments") or "{}")
