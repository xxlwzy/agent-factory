from pathlib import Path

from agent_factory.tools.base import ToolResult
from agent_factory.tools.terminal import DEFAULT_DENY_SUBSTRINGS, TerminalTool


def test_terminal_run_returns_runner_output(tmp_path: Path) -> None:
    captured: list[tuple[list[str], Path]] = []

    def fake_runner(args: list[str], cwd: Path) -> ToolResult:
        captured.append((args, cwd))
        return ToolResult(success=True, output="ok")

    tool = TerminalTool(workspace_root=tmp_path, command_runner=fake_runner)

    result = tool.execute("run", "echo hello")

    assert result.success is True
    assert result.output == "ok"
    assert captured == [(["echo", "hello"], tmp_path.resolve())]


def test_terminal_rejects_unsupported_operation(tmp_path: Path) -> None:
    tool = TerminalTool(workspace_root=tmp_path)

    result = tool.execute("shell", "echo hi")

    assert result.success is False
    assert "Unsupported" in result.error


def test_terminal_rejects_empty_command(tmp_path: Path) -> None:
    tool = TerminalTool(workspace_root=tmp_path)

    result = tool.execute("run", "   ")

    assert result.success is False
    assert "Empty" in result.error


def test_terminal_rejects_deny_list_command(tmp_path: Path) -> None:
    tool = TerminalTool(workspace_root=tmp_path, deny_substrings=DEFAULT_DENY_SUBSTRINGS)

    result = tool.execute("run", "rm -rf /tmp/x")

    assert result.success is False
    assert "denied" in result.error.lower()


def test_terminal_propagates_runner_failure(tmp_path: Path) -> None:
    def failing_runner(args: list[str], cwd: Path) -> ToolResult:
        return ToolResult(success=False, error="boom")

    tool = TerminalTool(workspace_root=tmp_path, command_runner=failing_runner)

    result = tool.execute("run", "echo hi")

    assert result.success is False
    assert result.error == "boom"
