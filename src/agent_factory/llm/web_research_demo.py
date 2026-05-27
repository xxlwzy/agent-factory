from __future__ import annotations

from agent_factory.llm.messages import FinalResponse, LLMRequest, LLMResponse, ToolCallResponse
from agent_factory.runtime.summarize import summarize_web_content


class WebResearchDemoLLM:
    def __init__(self, url: str, report_path: str) -> None:
        self._url = url
        self._report_path = report_path
        self._turn = 0

    def next_response(self, request: LLMRequest) -> LLMResponse:
        if self._turn == 0:
            self._turn += 1
            return ToolCallResponse(tool="http", operation="GET", target=self._url)
        if self._turn == 1:
            self._turn += 1
            body = _http_body_from_messages(request.messages)
            report = summarize_web_content(self._url, body)
            return ToolCallResponse(
                tool="filesystem",
                operation="write",
                target=self._report_path,
                content=report,
            )
        self._turn += 1
        return FinalResponse(content=f"Wrote report to {self._report_path}")


def _http_body_from_messages(messages: tuple[str, ...]) -> str:
    for message in reversed(messages):
        if message.startswith("http."):
            _, _, body = message.partition("=")
            return body
    return ""
