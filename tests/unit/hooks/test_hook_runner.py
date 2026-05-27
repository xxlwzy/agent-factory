from pathlib import Path

from agent_factory.config.schema import HookEntry, HooksConfig
from agent_factory.hooks.runner import HookRunner


def test_pre_tool_use_hook_failure_blocks() -> None:
    hooks = HooksConfig(pre_tool_use=(HookEntry(command=("false",)),))

    def failing_runner(command: tuple[str, ...], env: dict[str, str]):
        from agent_factory.hooks.runner import HookResult

        return HookResult(success=False, error="hook denied")

    runner = HookRunner(hooks, workspace_root=Path("/tmp"), command_runner=failing_runner)

    result = runner.run_pre_tool_use(tool="filesystem", operation="read", target=".")

    assert result.success is False
    assert "hook denied" in result.error


def test_run_completed_hook_success() -> None:
    captured: list[str] = []

    def ok_runner(command: tuple[str, ...], env: dict[str, str]):
        from agent_factory.hooks.runner import HookResult

        captured.append(env["AGENT_FACTORY_EVENT"])
        return HookResult(success=True)

    hooks = HooksConfig(run_completed=(HookEntry(command=("true",)),))
    runner = HookRunner(hooks, workspace_root=Path("/tmp"), command_runner=ok_runner)

    result = runner.run_run_completed(task="t", output="done")

    assert result.success is True
    assert captured == ["RunCompleted"]
