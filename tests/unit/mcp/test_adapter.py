from agent_factory.mcp.adapter import McpTool
from agent_factory.tools.base import ToolResult


def test_mcp_tool_dispatches_to_handler() -> None:
    tool = McpTool(
        handlers={
            "search": lambda operation, target, content: ToolResult(
                success=True,
                output=f"hits:{target}",
            )
        }
    )

    result = tool.execute("search", "query-text")

    assert result.success is True
    assert result.output == "hits:query-text"


def test_mcp_tool_unknown_operation_errors() -> None:
    tool = McpTool(handlers={})

    result = tool.execute("missing", "x")

    assert result.success is False
    assert "Unknown MCP" in result.error
