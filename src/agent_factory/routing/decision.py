from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScenarioSubtask:
    scenario_id: str
    task: str


@dataclass(frozen=True)
class RoutingDecision:
    target_agent: str
    delegated_task: str
    reason: str
    decision_kind: str = "single_agent"
    scenario_id: str | None = None
    subtasks: tuple[ScenarioSubtask, ...] = ()
    correlation_id: str | None = None
