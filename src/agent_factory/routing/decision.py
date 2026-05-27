from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RoutingDecision:
    target_agent: str
    delegated_task: str
    reason: str
