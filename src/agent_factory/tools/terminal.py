from __future__ import annotations

import shlex
import subprocess
from collections.abc import Callable
from pathlib import Path

from agent_factory.tools.base import ToolResult

DEFAULT_DENY_SUBSTRINGS: tuple[str, ...] = (
    "rm -rf",
    "| bash",
    "curl|bash",
    "wget|bash",
    "&& rm",
    "; rm",
)

CommandRunner = Callable[[list[str], Path], ToolResult]


class TerminalTool:
    name = "terminal"

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        deny_substrings: tuple[str, ...] = DEFAULT_DENY_SUBSTRINGS,
        command_runner: CommandRunner | None = None,
    ) -> None:
        self._workspace_root = Path(workspace_root).resolve()
        self._deny_substrings = deny_substrings
        self._command_runner = command_runner or _default_command_runner

    def execute(self, operation: str, target: str, *, content: str = "") -> ToolResult:
        if operation.lower() != "run":
            return ToolResult(success=False, error=f"Unsupported terminal operation '{operation}'.")

        command = target.strip()
        if not command:
            return ToolResult(success=False, error="Empty command.")

        lowered = command.lower()
        for pattern in self._deny_substrings:
            if pattern.lower() in lowered:
                return ToolResult(success=False, error="Command denied by safety policy.")

        try:
            args = shlex.split(command)
        except ValueError as error:
            return ToolResult(success=False, error=str(error))

        if not args:
            return ToolResult(success=False, error="Empty command.")

        return self._command_runner(args, self._workspace_root)


def _default_command_runner(args: list[str], cwd: Path) -> ToolResult:
    try:
        completed = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return ToolResult(success=False, error=str(error))

    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        return ToolResult(
            success=False,
            error=stderr or f"Command exited with code {completed.returncode}",
        )

    return ToolResult(success=True, output=completed.stdout)
