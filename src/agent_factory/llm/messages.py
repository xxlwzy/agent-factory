from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LLMRequest:
    task: str
    messages: tuple[str, ...] = ()


@dataclass(frozen=True)
class ToolCallResponse:
    tool: str
    operation: str
    target: str


@dataclass(frozen=True)
class FinalResponse:
    content: str


LLMResponse = ToolCallResponse | FinalResponse
