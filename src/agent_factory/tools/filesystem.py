from __future__ import annotations

from pathlib import Path

from agent_factory.permissions.sandbox import resolve_workspace_path
from agent_factory.tools.base import ToolResult


class FilesystemTool:
    name = "filesystem"

    def __init__(self, workspace_root: str | Path) -> None:
        self._workspace_root = Path(workspace_root).resolve()

    def execute(self, operation: str, target: str, *, content: str = "") -> ToolResult:
        path = resolve_workspace_path(target, self._workspace_root)
        normalized = operation.lower()

        if normalized == "read":
            return self._read(path)
        if normalized == "write":
            return self._write(path, content)
        return ToolResult(success=False, error=f"Unsupported filesystem operation '{operation}'.")

    def _read(self, path: Path) -> ToolResult:
        if not path.is_file():
            return ToolResult(success=False, error=f"File not found: {path}")
        return ToolResult(success=True, output=path.read_text(encoding="utf-8"))

    def _write(self, path: Path, content: str) -> ToolResult:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return ToolResult(success=True, output=f"Wrote {len(content)} bytes to {path}")
