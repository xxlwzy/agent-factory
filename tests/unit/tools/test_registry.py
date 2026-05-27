from agent_factory.config.schema import ToolConfig
from agent_factory.tools.base import ToolResult
from agent_factory.tools.registry import ToolRegistry


class _StubTool:
    name = "stub"

    def execute(self, operation: str, target: str, *, content: str = "") -> ToolResult:
        return ToolResult(success=True, output=f"{operation}:{target}:{content}")


def test_registry_dispatches_to_adapter() -> None:
    registry = ToolRegistry({"stub": _StubTool()}, enabled_tools={"stub": ToolConfig(enabled=True)})

    result = registry.execute("stub", "ping", "target", content="data")

    assert result.success is True
    assert result.output == "ping:target:data"


def test_registry_errors_for_unknown_tool() -> None:
    registry = ToolRegistry({}, enabled_tools={})

    result = registry.execute("missing", "read", "x")

    assert result.success is False
    assert "missing" in result.error


def test_registry_errors_for_disabled_tool() -> None:
    registry = ToolRegistry(
        {"stub": _StubTool()},
        enabled_tools={"stub": ToolConfig(enabled=False)},
    )

    result = registry.execute("stub", "read", "x")

    assert result.success is False
    assert "not enabled" in result.error.lower()
