from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChatTurn:
    role: str
    content: str


@dataclass(frozen=True)
class LLMRequest:
    task: str
    messages: tuple[str, ...] = ()
    history: tuple[ChatTurn, ...] = ()
    skill_context: str = ""


@dataclass(frozen=True)
class ToolCallResponse:
    tool: str
    operation: str
    target: str
    content: str = ""


@dataclass(frozen=True)
class FinalResponse:
    content: str


LLMResponse = ToolCallResponse | FinalResponse
