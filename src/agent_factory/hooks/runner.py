from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from agent_factory.config.schema import HookEntry, HooksConfig

EVENT_PRE_TOOL_USE = "PreToolUse"
EVENT_POST_TOOL_USE = "PostToolUse"
EVENT_RUN_COMPLETED = "RunCompleted"


@dataclass(frozen=True)
class HookResult:
    success: bool
    output: str = ""
    error: str = ""


HookCommandRunner = Callable[[tuple[str, ...], dict[str, str]], HookResult]


class HookRunner:
    def __init__(
        self,
        hooks: HooksConfig,
        *,
        workspace_root: str | Path,
        command_runner: HookCommandRunner | None = None,
    ) -> None:
        self._hooks = hooks
        self._workspace_root = Path(workspace_root).resolve()
        self._command_runner = command_runner or _default_command_runner

    def has_hooks(self) -> bool:
        return bool(
            self._hooks.pre_tool_use or self._hooks.post_tool_use or self._hooks.run_completed
        )

    def run_pre_tool_use(self, *, tool: str, operation: str, target: str, run_id: str = "") -> HookResult:
        return self._run_event(
            EVENT_PRE_TOOL_USE,
            self._hooks.pre_tool_use,
            tool=tool,
            operation=operation,
            target=target,
            run_id=run_id,
        )

    def run_post_tool_use(self, *, tool: str, operation: str, target: str, run_id: str = "") -> HookResult:
        return self._run_event(
            EVENT_POST_TOOL_USE,
            self._hooks.post_tool_use,
            tool=tool,
            operation=operation,
            target=target,
            run_id=run_id,
        )

    def run_run_completed(self, *, task: str, output: str, run_id: str = "") -> HookResult:
        return self._run_event(
            EVENT_RUN_COMPLETED,
            self._hooks.run_completed,
            task=task,
            output=output,
            run_id=run_id,
        )

    def _run_event(
        self,
        event: str,
        entries: tuple[HookEntry, ...],
        **context: str,
    ) -> HookResult:
        if not entries:
            return HookResult(success=True)

        env = {
            "AGENT_FACTORY_EVENT": event,
            "AGENT_FACTORY_WORKSPACE": str(self._workspace_root),
            **{f"AGENT_FACTORY_{key.upper()}": value for key, value in context.items()},
        }
        for entry in entries:
            result = self._command_runner(entry.command, env)
            if not result.success:
                return HookResult(
                    success=False,
                    error=result.error or f"Hook command failed for event '{event}'.",
                )
        return HookResult(success=True)


def _default_command_runner(command: tuple[str, ...], env: dict[str, str]) -> HookResult:
    try:
        completed = subprocess.run(
            list(command),
            cwd=env.get("AGENT_FACTORY_WORKSPACE"),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env={**_base_env(), **env},
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return HookResult(success=False, error=str(error))

    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        return HookResult(
            success=False,
            error=stderr or f"Hook exited with code {completed.returncode}",
        )
    return HookResult(success=True, output=completed.stdout)


def _base_env() -> dict[str, str]:
    import os

    return dict(os.environ)
