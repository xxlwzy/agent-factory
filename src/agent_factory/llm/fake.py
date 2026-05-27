from __future__ import annotations

from collections import deque

from agent_factory.llm.messages import LLMRequest, LLMResponse


class FakeLLMAdapter:
    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = deque(responses)

    def next_response(self, request: LLMRequest) -> LLMResponse:
        if not self._responses:
            raise RuntimeError("FakeLLMAdapter has no scripted responses left.")
        return self._responses.popleft()
