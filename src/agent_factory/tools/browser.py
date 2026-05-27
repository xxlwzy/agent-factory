from __future__ import annotations

from collections.abc import Callable

from agent_factory.tools.base import ToolResult
from agent_factory.tools.http import HttpFetcher, _default_fetch

BrowserFetcher = HttpFetcher


class BrowserTool:
    name = "browser"

    def __init__(self, fetcher: BrowserFetcher | None = None) -> None:
        self._fetcher = fetcher or _default_fetch

    def execute(self, operation: str, target: str, *, content: str = "") -> ToolResult:
        normalized = operation.lower()
        if normalized == "submit":
            return ToolResult(success=False, error="browser.submit is not implemented in MVP.")
        if normalized not in {"read", "navigate"}:
            return ToolResult(success=False, error=f"Unsupported browser operation '{operation}'.")

        url = target.strip()
        if not url:
            return ToolResult(success=False, error="URL is required.")

        try:
            body = self._fetcher(url)
        except OSError as error:
            return ToolResult(success=False, error=str(error))
        return ToolResult(success=True, output=body)
