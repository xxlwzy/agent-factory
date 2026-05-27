from __future__ import annotations

from pathlib import Path

from agent_factory.config.schema import AgentFactoryConfig, McpConfig, ToolConfig
from agent_factory.mcp.adapter import McpHandler, McpTool
from agent_factory.tools.base import ToolAdapter, ToolResult
from agent_factory.tools.browser import BrowserFetcher, BrowserTool
from agent_factory.tools.filesystem import FilesystemTool
from agent_factory.tools.http import HttpFetcher, HttpTool
from agent_factory.tools.terminal import CommandRunner, TerminalTool


class ToolRegistry:
    def __init__(
        self,
        adapters: dict[str, ToolAdapter],
        enabled_tools: dict[str, ToolConfig],
    ) -> None:
        self._adapters = adapters
        self._enabled_tools = enabled_tools

    def execute(self, tool: str, operation: str, target: str, *, content: str = "") -> ToolResult:
        tool_config = self._enabled_tools.get(tool)
        if tool_config is None or not tool_config.enabled:
            return ToolResult(success=False, error=f"Tool '{tool}' is not enabled.")

        adapter = self._adapters.get(tool)
        if adapter is None:
            return ToolResult(success=False, error=f"No adapter registered for tool '{tool}'.")

        return adapter.execute(operation, target, content=content)


def build_default_registry(
    config: AgentFactoryConfig,
    workspace_root: str | Path,
    *,
    http_fetcher: HttpFetcher | None = None,
    browser_fetcher: BrowserFetcher | None = None,
    terminal_runner: CommandRunner | None = None,
    mcp_handlers: dict[str, McpHandler] | None = None,
) -> ToolRegistry:
    adapters: dict[str, ToolAdapter] = {
        "filesystem": FilesystemTool(workspace_root=workspace_root),
        "http": HttpTool(fetcher=http_fetcher),
        "terminal": TerminalTool(workspace_root=workspace_root, command_runner=terminal_runner),
        "browser": BrowserTool(fetcher=browser_fetcher),
    }
    if config.mcp.tools:
        adapters["mcp"] = McpTool(handlers=build_mcp_handlers(config.mcp, mcp_handlers))
    return ToolRegistry(adapters=adapters, enabled_tools=config.tools)


def build_mcp_handlers(
    mcp_config: McpConfig,
    overrides: dict[str, McpHandler] | None = None,
) -> dict[str, McpHandler]:
    handlers: dict[str, McpHandler] = {}
    for descriptor in mcp_config.tools:
        if overrides and descriptor.name in overrides:
            handlers[descriptor.name] = overrides[descriptor.name]
        else:
            handlers[descriptor.name] = _missing_mcp_handler(descriptor.name)
    return handlers


def _missing_mcp_handler(name: str) -> McpHandler:
    def handler(operation: str, target: str, content: str) -> ToolResult:
        return ToolResult(success=False, error=f"MCP tool '{name}' has no runtime handler configured.")

    return handler
