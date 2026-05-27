from __future__ import annotations

from agent_factory.config.schema import McpToolDescriptor
from agent_factory.permissions.guard import ToolRequest


def to_tool_request(descriptor: McpToolDescriptor, *, target: str) -> ToolRequest:
    return ToolRequest(
        tool="mcp",
        operation=descriptor.name,
        target=target,
    )


def mcp_rule_name(descriptor: McpToolDescriptor) -> str:
    return f"mcp.{descriptor.operation}"
