from __future__ import annotations

import uuid
from typing import Protocol

from agent_factory.config.catalog import FALLBACK_AGENT, AgentCatalog
from agent_factory.config.scenario_catalog import ScenarioCatalog
from agent_factory.routing.decision import RoutingDecision, ScenarioSubtask


class ScenarioRoutingResolver(Protocol):
    def resolve(
        self,
        message: str,
        *,
        agent_catalog: AgentCatalog,
        scenario_catalog: ScenarioCatalog,
    ) -> RoutingDecision: ...


class RuleBasedScenarioRoutingResolver:
    """Deterministic scenario-aware router for tests and offline use."""

    def resolve(
        self,
        message: str,
        *,
        agent_catalog: AgentCatalog,
        scenario_catalog: ScenarioCatalog,
    ) -> RoutingDecision:
        lowered = message.lower()
        known_scenarios = {entry.scenario_id for entry in scenario_catalog.list_scenarios()}

        if "parallel:" in lowered:
            subtasks = _parse_parallel_subtasks(message, known_scenarios)
            if len(subtasks) >= 2:
                return RoutingDecision(
                    target_agent="",
                    delegated_task=message,
                    reason="Parallel multi-scenario request.",
                    decision_kind="multi_scenario",
                    subtasks=subtasks,
                    correlation_id=uuid.uuid4().hex[:12],
                )

        for scenario_id in known_scenarios:
            token = f"scenario:{scenario_id}"
            if token in lowered or scenario_id in lowered:
                return RoutingDecision(
                    target_agent="",
                    delegated_task=message,
                    reason=f"Matched scenario '{scenario_id}'.",
                    decision_kind="scenario",
                    scenario_id=scenario_id,
                )

        for entry in agent_catalog.list_routable():
            if entry.name == "web_researcher" and any(
                token in lowered for token in ("http://", "https://", "example.com", "网页", "总结", "research")
            ):
                return RoutingDecision(
                    target_agent=entry.name,
                    delegated_task=message,
                    reason="Matched web research keywords.",
                    decision_kind="single_agent",
                )

        return RoutingDecision(
            target_agent=FALLBACK_AGENT,
            delegated_task=message,
            reason="No specialist or scenario match; using general assistant.",
            decision_kind="fallback",
        )


def _parse_parallel_subtasks(message: str, known_scenarios: set[str]) -> tuple[ScenarioSubtask, ...]:
    subtasks: list[ScenarioSubtask] = []
    for line in message.splitlines():
        stripped = line.strip()
        if not stripped.lower().startswith("parallel:"):
            continue
        payload = stripped.split(":", 1)[1].strip()
        if "|" not in payload:
            continue
        scenario_id, task = (part.strip() for part in payload.split("|", 1))
        if scenario_id in known_scenarios and task:
            subtasks.append(ScenarioSubtask(scenario_id=scenario_id, task=task))
    return tuple(subtasks)
