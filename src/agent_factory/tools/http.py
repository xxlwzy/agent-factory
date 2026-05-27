from __future__ import annotations

from collections.abc import Callable
from urllib.request import urlopen

from agent_factory.tools.base import ToolResult

HttpFetcher = Callable[[str], str]


class HttpTool:
    name = "http"

    def __init__(self, fetcher: HttpFetcher | None = None) -> None:
        self._fetcher = fetcher or _default_fetch

    def execute(self, operation: str, target: str, *, content: str = "") -> ToolResult:
        if operation.upper() != "GET":
            return ToolResult(success=False, error="HttpTool only supports GET in Phase 2.")
        try:
            body = self._fetcher(target)
        except OSError as error:
            return ToolResult(success=False, error=str(error))
        return ToolResult(success=True, output=body)


def _default_fetch(url: str) -> str:
    with urlopen(url) as response:
        return response.read().decode("utf-8", errors="replace")
