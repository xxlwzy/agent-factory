from __future__ import annotations

from collections.abc import Callable

from agent_factory.tools.base import ToolResult

McpHandler = Callable[[str, str, str], ToolResult]


class McpTool:
    name = "mcp"

    def __init__(self, handlers: dict[str, McpHandler]) -> None:
        self._handlers = handlers

    def execute(self, operation: str, target: str, *, content: str = "") -> ToolResult:
        handler = self._handlers.get(operation)
        if handler is None:
            return ToolResult(success=False, error=f"Unknown MCP operation '{operation}'.")
        return handler(operation, target, content)
