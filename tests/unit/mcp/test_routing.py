from agent_factory.config.schema import McpToolDescriptor
from agent_factory.mcp.routing import mcp_rule_name, to_tool_request


def test_to_tool_request_maps_descriptor() -> None:
    descriptor = McpToolDescriptor(name="search", operation="invoke")

    request = to_tool_request(descriptor, target='{"q":"test"}')

    assert request.tool == "mcp"
    assert request.operation == "search"
    assert request.target == '{"q":"test"}'


def test_mcp_rule_name() -> None:
    descriptor = McpToolDescriptor(name="search", operation="invoke")

    assert mcp_rule_name(descriptor) == "mcp.invoke"
