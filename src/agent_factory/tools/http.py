from __future__ import annotations

import ssl
from collections.abc import Callable
from urllib.request import Request, urlopen

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
    request = Request(url, headers={"User-Agent": "AgentFactory/0.1"})
    with urlopen(request, timeout=60, context=_ssl_context()) as response:
        return response.read().decode("utf-8", errors="replace")


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()
