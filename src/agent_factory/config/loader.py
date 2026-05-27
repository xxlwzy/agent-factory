from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from agent_factory.config.schema import (
    AgentConfig,
    AgentFactoryConfig,
    AutomationConfig,
    HookEntry,
    HooksConfig,
    McpConfig,
    McpToolDescriptor,
    MemoryConfig,
    MetaConfig,
    RuntimeConfig,
    ScheduleConfig,
    SkillsConfig,
    ToolConfig,
)
from agent_factory.config.policy_loader import resolve_agent_permissions
from agent_factory.config.unsupported import collect_unsupported_warnings


def load_agent_config(path: str | Path) -> AgentFactoryConfig:
    config_path = Path(path)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("Agent config must be a YAML mapping.")

    _require_sections(raw, ("meta", "agent", "tools", "permissions"))

    policy_name = _optional_policy_name(raw.get("policy"))
    permissions_raw = _mapping(raw["permissions"], "permissions")

    return AgentFactoryConfig(
        meta=_parse_meta(_mapping(raw["meta"], "meta")),
        agent=_parse_agent(_mapping(raw["agent"], "agent")),
        runtime=_parse_runtime(_mapping(raw.get("runtime", {}), "runtime")),
        tools=_parse_tools(_mapping(raw["tools"], "tools")),
        permissions=resolve_agent_permissions(config_path, permissions_raw, policy_name),
        memory=_parse_memory(_mapping(raw.get("memory", {}), "memory")),
        skills=_parse_skills(_mapping(raw.get("skills", {}), "skills")),
        hooks=_parse_hooks(_mapping(raw.get("hooks", {}), "hooks") if "hooks" in raw else {}),
        automation=_parse_automation(
            _mapping(raw.get("automation", {}), "automation") if "automation" in raw else {}
        ),
        mcp=_parse_mcp(_mapping(raw.get("mcp", {}), "mcp") if "mcp" in raw else {}),
        unsupported_warnings=collect_unsupported_warnings(raw),
    )


def _require_sections(raw: dict[str, Any], sections: tuple[str, ...]) -> None:
    for section in sections:
        if section not in raw:
            raise ValueError(f"Missing required section: {section}")


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"Section '{name}' must be a mapping.")
    return value


def _parse_meta(raw: dict[str, Any]) -> MetaConfig:
    name = str(raw.get("name", "")).strip()
    if not name:
        raise ValueError("meta.name is required.")
    return MetaConfig(
        name=name,
        version=str(raw.get("version", "0.1")),
        description=str(raw.get("description", "")),
        owner=str(raw.get("owner", "")),
    )


def _parse_agent(raw: dict[str, Any]) -> AgentConfig:
    role = str(raw.get("role", "")).strip()
    model = str(raw.get("model", "")).strip()
    system_prompt = str(raw.get("system_prompt", "")).strip()
    if not role:
        raise ValueError("agent.role is required.")
    if not model:
        raise ValueError("agent.model is required.")
    if not system_prompt:
        raise ValueError("agent.system_prompt is required.")
    return AgentConfig(role=role, model=model, system_prompt=system_prompt)


def _parse_runtime(raw: dict[str, Any]) -> RuntimeConfig:
    return RuntimeConfig(
        max_turns=int(raw.get("max_turns", 20)),
        working_dir=str(raw.get("working_dir", ".")),
        output_dir=str(raw.get("output_dir", ".agent-factory/runs")),
        trace_level=str(raw.get("trace_level", "standard")),
    )


def _parse_tools(raw: dict[str, Any]) -> dict[str, ToolConfig]:
    tools: dict[str, ToolConfig] = {}
    for name, value in raw.items():
        tool_raw = _mapping(value, f"tools.{name}")
        tools[str(name)] = ToolConfig(enabled=bool(tool_raw.get("enabled", False)))
    return tools


def _optional_policy_name(value: object) -> str | None:
    if value is None:
        return None
    name = str(value).strip()
    if not name:
        raise ValueError("policy must be a non-empty string when set.")
    return name


def _parse_memory(raw: dict[str, Any]) -> MemoryConfig:
    return MemoryConfig(
        session_path=str(raw.get("session_path", ".agent-factory/memory/session")),
        project_path=str(raw.get("project_path", ".agent-factory/memory/project")),
        user_path=str(raw.get("user_path", ".agent-factory/memory/user")),
    )


def _parse_skills(raw: dict[str, Any]) -> SkillsConfig:
    return SkillsConfig(
        enabled=tuple(str(skill) for skill in raw.get("enabled", ())),
        draft_output_dir=str(raw.get("draft_output_dir", ".agent-factory/skills/drafts")),
    )


def _parse_hooks(raw: dict[str, Any]) -> HooksConfig:
    return HooksConfig(
        pre_tool_use=_parse_hook_entries(raw.get("PreToolUse"), "hooks.PreToolUse"),
        post_tool_use=_parse_hook_entries(raw.get("PostToolUse"), "hooks.PostToolUse"),
        run_completed=_parse_hook_entries(raw.get("RunCompleted"), "hooks.RunCompleted"),
    )


def _parse_hook_entries(value: Any, name: str) -> tuple[HookEntry, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list.")
    entries: list[HookEntry] = []
    for index, item in enumerate(value):
        item_raw = _mapping(item, f"{name}[{index}]")
        command_raw = item_raw.get("command")
        if not isinstance(command_raw, list) or not command_raw:
            raise ValueError(f"{name}[{index}].command must be a non-empty list.")
        entries.append(HookEntry(command=tuple(str(part) for part in command_raw)))
    return tuple(entries)


def _parse_automation(raw: dict[str, Any]) -> AutomationConfig:
    schedules_raw = raw.get("schedules")
    if schedules_raw is None:
        return AutomationConfig()
    if not isinstance(schedules_raw, list):
        raise ValueError("automation.schedules must be a list.")
    schedules: list[ScheduleConfig] = []
    for index, item in enumerate(schedules_raw):
        item_raw = _mapping(item, f"automation.schedules[{index}]")
        name = str(item_raw.get("name", "")).strip()
        task = str(item_raw.get("task", "")).strip()
        if not name:
            raise ValueError(f"automation.schedules[{index}].name is required.")
        if not task:
            raise ValueError(f"automation.schedules[{index}].task is required.")
        schedules.append(
            ScheduleConfig(
                name=name,
                interval_seconds=int(item_raw.get("interval_seconds", 0)),
                task=task,
            )
        )
    return AutomationConfig(schedules=tuple(schedules))


def _parse_mcp(raw: dict[str, Any]) -> McpConfig:
    tools_raw = raw.get("tools")
    if tools_raw is None:
        return McpConfig()
    if not isinstance(tools_raw, list):
        raise ValueError("mcp.tools must be a list.")
    tools: list[McpToolDescriptor] = []
    for index, item in enumerate(tools_raw):
        item_raw = _mapping(item, f"mcp.tools[{index}]")
        name = str(item_raw.get("name", "")).strip()
        if not name:
            raise ValueError(f"mcp.tools[{index}].name is required.")
        tools.append(
            McpToolDescriptor(
                name=name,
                description=str(item_raw.get("description", "")),
                operation=str(item_raw.get("operation", "invoke")),
            )
        )
    return McpConfig(tools=tuple(tools))
