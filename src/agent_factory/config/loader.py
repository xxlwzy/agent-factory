from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from agent_factory.config.schema import (
    AgentConfig,
    AgentFactoryConfig,
    MemoryConfig,
    MetaConfig,
    PermissionsConfig,
    RuntimeConfig,
    SandboxConfig,
    SkillsConfig,
    ToolConfig,
)
from agent_factory.config.unsupported import collect_unsupported_warnings


def load_agent_config(path: str | Path) -> AgentFactoryConfig:
    config_path = Path(path)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("Agent config must be a YAML mapping.")

    _require_sections(raw, ("meta", "agent", "tools", "permissions"))

    return AgentFactoryConfig(
        meta=_parse_meta(_mapping(raw["meta"], "meta")),
        agent=_parse_agent(_mapping(raw["agent"], "agent")),
        runtime=_parse_runtime(_mapping(raw.get("runtime", {}), "runtime")),
        tools=_parse_tools(_mapping(raw["tools"], "tools")),
        permissions=_parse_permissions(_mapping(raw["permissions"], "permissions")),
        memory=_parse_memory(_mapping(raw.get("memory", {}), "memory")),
        skills=_parse_skills(_mapping(raw.get("skills", {}), "skills")),
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


def _parse_permissions(raw: dict[str, Any]) -> PermissionsConfig:
    sandbox_raw = _mapping(raw.get("sandbox", {}), "permissions.sandbox")
    return PermissionsConfig(
        sandbox=SandboxConfig(
            paths=tuple(str(path) for path in sandbox_raw.get("paths", ())),
            domains=tuple(str(domain) for domain in sandbox_raw.get("domains", ())),
        ),
        confirm=tuple(str(rule) for rule in raw.get("confirm", ())),
        deny=tuple(str(rule) for rule in raw.get("deny", ())),
    )


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
