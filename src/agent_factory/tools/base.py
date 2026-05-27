from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ToolResult:
    success: bool
    output: str = ""
    error: str = ""


class ToolAdapter(Protocol):
    name: str

    def execute(self, operation: str, target: str, *, content: str = "") -> ToolResult: ...
