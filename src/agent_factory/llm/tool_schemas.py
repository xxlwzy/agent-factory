from __future__ import annotations

from typing import Any

from agent_factory.config.schema import AgentFactoryConfig, ToolConfig


def openai_tools_for_config(config: AgentFactoryConfig) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    if _enabled(config.tools, "http"):
        tools.append(_HTTP_GET_TOOL)
    if _enabled(config.tools, "filesystem"):
        tools.extend([_FILESYSTEM_READ_TOOL, _FILESYSTEM_WRITE_TOOL])
    return tools


def _enabled(tools: dict[str, ToolConfig], name: str) -> bool:
    tool = tools.get(name)
    return tool is not None and tool.enabled


_HTTP_GET_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "http_get",
        "description": "Fetch a web page with HTTP GET.",
        "parameters": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
}

_FILESYSTEM_READ_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "filesystem_read",
        "description": "Read a UTF-8 text file inside the sandbox.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
}

_FILESYSTEM_WRITE_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "filesystem_write",
        "description": "Write UTF-8 text to a sandbox file path.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
}
