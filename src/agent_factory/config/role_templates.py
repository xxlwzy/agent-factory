from __future__ import annotations

from enum import StrEnum

from agent_factory.config.schema import ToolConfig


class AgentRole(StrEnum):
    ORCHESTRATOR = "orchestrator"
    TEAMMATE = "teammate"
    SINGLE = "single"


# Orchestrator: delegate + optional read-only paths; no direct side-effect tools.
ORCHESTRATOR_TOOL_ENABLED: dict[str, bool] = {
    "team": True,
    "filesystem": False,
    "terminal": False,
    "browser": False,
    "http": False,
    "mcp": False,
}


def apply_role_tool_template(
    tools: dict[str, ToolConfig],
    role: AgentRole,
) -> dict[str, ToolConfig]:
    if role != AgentRole.ORCHESTRATOR:
        return dict(tools)

    result: dict[str, ToolConfig] = {}
    for name, enabled in ORCHESTRATOR_TOOL_ENABLED.items():
        result[name] = ToolConfig(enabled=enabled)
    for name, config in tools.items():
        if name not in ORCHESTRATOR_TOOL_ENABLED:
            result[name] = ToolConfig(enabled=False)
        elif name == "team":
            result[name] = ToolConfig(enabled=config.enabled or ORCHESTRATOR_TOOL_ENABLED["team"])
    return result


def merge_scenario_member_tools(
    *,
    common: dict[str, ToolConfig],
    scenario: dict[str, ToolConfig],
    member: dict[str, ToolConfig],
    role: AgentRole,
) -> dict[str, ToolConfig]:
    merged = merge_layers(common, scenario, member)
    return apply_role_tool_template(merged, role)


def merge_layers(*layers: dict[str, ToolConfig]) -> dict[str, ToolConfig]:
    merged: dict[str, ToolConfig] = {}
    for layer in layers:
        for name, config in layer.items():
            merged[name] = ToolConfig(enabled=config.enabled)
    return merged
