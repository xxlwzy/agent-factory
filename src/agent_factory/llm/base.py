from __future__ import annotations

from typing import Protocol

from agent_factory.llm.messages import LLMRequest, LLMResponse


class LLMAdapter(Protocol):
    def next_response(self, request: LLMRequest) -> LLMResponse:
        """Return the next model response for a runtime turn."""
