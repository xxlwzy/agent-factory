from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from agent_factory.llm.messages import ToolCallResponse


class RunStatus(StrEnum):
    RUNNING = "running"
    BLOCKED = "blocked"
    FAILED = "failed"
    COMPLETED = "completed"
    AWAITING_CONFIRM = "awaiting_confirm"


@dataclass(frozen=True)
class RunResult:
    status: RunStatus
    output: str = ""
    reason: str = ""
    approval_id: str = ""
    pending_tool: ToolCallResponse | None = None
    tool_messages: tuple[str, ...] = ()
    paused_turn: int = 0
