from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from agent_factory.config.schema import ToolConfig


def load_tools_yaml(path: str | Path) -> dict[str, ToolConfig]:
    config_path = Path(path)
    if not config_path.is_file():
        return {}
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Tool config must be a mapping: {config_path}")
    tools_raw = raw.get("tools", raw)
    if not isinstance(tools_raw, dict):
        raise ValueError(f"tools section must be a mapping: {config_path}")
    return _parse_tools(tools_raw)


def merge_tool_configs(*layers: dict[str, ToolConfig]) -> dict[str, ToolConfig]:
    merged: dict[str, ToolConfig] = {}
    for layer in layers:
        for name, config in layer.items():
            if name in merged and merged[name].enabled != config.enabled:
                merged[name] = ToolConfig(enabled=config.enabled)
            else:
                merged[name] = ToolConfig(enabled=config.enabled)
    return merged


def validate_scenario_tool_scope(
    merged_tools: dict[str, ToolConfig],
    *,
    common_tools: dict[str, ToolConfig],
    scenario_tools: dict[str, ToolConfig],
) -> None:
    scenario_only = set(scenario_tools) - set(common_tools)
    for name in merged_tools:
        if name in scenario_only and name not in scenario_tools:
            raise ValueError(f"Tool '{name}' is scoped to another scenario and cannot be enabled.")


def _parse_tools(raw: dict[str, Any]) -> dict[str, ToolConfig]:
    tools: dict[str, ToolConfig] = {}
    for name, value in raw.items():
        if not isinstance(value, dict):
            raise ValueError(f"tools.{name} must be a mapping.")
        tools[str(name)] = ToolConfig(enabled=bool(value.get("enabled", False)))
    return tools
