from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class TeamMember:
    member_id: str
    agent: str


@dataclass(frozen=True)
class TeamPipelineStep:
    member_id: str
    task_template: str


@dataclass(frozen=True)
class TeamConfig:
    name: str
    members: tuple[TeamMember, ...]
    pipeline: tuple[TeamPipelineStep, ...]


def load_team_config(path: str | Path) -> TeamConfig:
    config_path = Path(path)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("Team config must be a YAML mapping.")

    team_raw = _mapping(raw.get("team", {}), "team")
    meta_raw = raw.get("meta", {})
    name = str(meta_raw.get("name", "")).strip() if isinstance(meta_raw, dict) else ""
    if not name:
        name = config_path.stem

    members = _parse_members(team_raw.get("members"))
    pipeline = _parse_pipeline(team_raw.get("pipeline"), members)
    return TeamConfig(name=name, members=members, pipeline=pipeline)


def resolve_member_agent_path(team_config_path: Path, agent_filename: str, agents_dir: Path) -> Path:
    agent_path = Path(agent_filename)
    if agent_path.is_absolute():
        return agent_path.resolve()
    if agent_path.parent != Path("."):
        candidate = (team_config_path.parent / agent_path).resolve()
        if candidate.is_file():
            return candidate
    return (agents_dir / agent_path.name).resolve()


def _parse_members(value: Any) -> tuple[TeamMember, ...]:
    if value is None:
        raise ValueError("team.members is required.")
    if not isinstance(value, list) or not value:
        raise ValueError("team.members must be a non-empty list.")

    members: list[TeamMember] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        item_raw = _mapping(item, f"team.members[{index}]")
        member_id = str(item_raw.get("id", "")).strip()
        agent = str(item_raw.get("agent", "")).strip()
        if not member_id:
            raise ValueError(f"team.members[{index}].id is required.")
        if not agent:
            raise ValueError(f"team.members[{index}].agent is required.")
        if member_id in seen:
            raise ValueError(f"Duplicate team member id '{member_id}'.")
        seen.add(member_id)
        members.append(TeamMember(member_id=member_id, agent=agent))
    return tuple(members)


def _parse_pipeline(value: Any, members: tuple[TeamMember, ...]) -> tuple[TeamPipelineStep, ...]:
    if value is None:
        raise ValueError("team.pipeline is required.")
    if not isinstance(value, list) or not value:
        raise ValueError("team.pipeline must be a non-empty list.")

    member_ids = {member.member_id for member in members}
    steps: list[TeamPipelineStep] = []
    for index, item in enumerate(value):
        item_raw = _mapping(item, f"team.pipeline[{index}]")
        member_id = str(item_raw.get("member", "")).strip()
        task_template = str(item_raw.get("task", "")).strip()
        if not member_id:
            raise ValueError(f"team.pipeline[{index}].member is required.")
        if member_id not in member_ids:
            raise ValueError(f"team.pipeline[{index}] references unknown member '{member_id}'.")
        if not task_template:
            raise ValueError(f"team.pipeline[{index}].task is required.")
        steps.append(TeamPipelineStep(member_id=member_id, task_template=task_template))
    return tuple(steps)


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"Section '{name}' must be a mapping.")
    return value
