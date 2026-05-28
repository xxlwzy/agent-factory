from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ScenarioMemberEntry:
    member_id: str
    path: Path


@dataclass(frozen=True)
class ScenarioEntry:
    scenario_id: str
    display_name: str
    description: str
    root: Path
    orchestrator_path: Path
    members: tuple[ScenarioMemberEntry, ...]
    single_agent_fallback: str | None = None


def load_scenario_entry(scenario_root: str | Path) -> ScenarioEntry:
    root = Path(scenario_root).resolve()
    scenario_path = root / "scenario.yaml"
    if not scenario_path.is_file():
        raise FileNotFoundError(f"Missing scenario.yaml under {root}")

    raw = yaml.safe_load(scenario_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"scenario.yaml must be a mapping: {scenario_path}")

    scenario_id = str(raw.get("id", "")).strip()
    if not scenario_id:
        raise ValueError(f"scenario.yaml id is required: {scenario_path}")

    display_name = str(raw.get("display_name", "")).strip() or scenario_id
    description = str(raw.get("description", "")).strip()
    entry = str(raw.get("entry", "orchestrator.yaml")).strip() or "orchestrator.yaml"
    orchestrator_path = (root / entry).resolve()
    if not orchestrator_path.is_file():
        raise FileNotFoundError(f"Orchestrator config not found: {orchestrator_path}")

    fallback_raw = raw.get("single_agent_fallback")
    single_agent_fallback = str(fallback_raw).strip() if fallback_raw else None

    members = _discover_members(root, raw.get("members"))
    return ScenarioEntry(
        scenario_id=scenario_id,
        display_name=display_name,
        description=description,
        root=root,
        orchestrator_path=orchestrator_path,
        members=members,
        single_agent_fallback=single_agent_fallback,
    )


def _discover_members(root: Path, members_raw: Any) -> tuple[ScenarioMemberEntry, ...]:
    if members_raw is not None:
        if not isinstance(members_raw, list):
            raise ValueError("scenario.yaml members must be a list when set.")
        entries: list[ScenarioMemberEntry] = []
        seen: set[str] = set()
        for index, item in enumerate(members_raw):
            if not isinstance(item, dict):
                raise ValueError(f"scenario.yaml members[{index}] must be a mapping.")
            member_id = str(item.get("id", "")).strip()
            agent = str(item.get("agent", "")).strip()
            if not member_id:
                raise ValueError(f"scenario.yaml members[{index}].id is required.")
            if not agent:
                raise ValueError(f"scenario.yaml members[{index}].agent is required.")
            if member_id in seen:
                raise ValueError(f"Duplicate scenario member id '{member_id}'.")
            seen.add(member_id)
            member_path = (root / agent).resolve()
            if not member_path.is_file():
                raise FileNotFoundError(f"Member config not found: {member_path}")
            entries.append(ScenarioMemberEntry(member_id=member_id, path=member_path))
        return tuple(entries)

    members_dir = root / "members"
    if not members_dir.is_dir():
        return ()
    entries = [
        ScenarioMemberEntry(member_id=path.stem, path=path.resolve())
        for path in sorted(members_dir.glob("*.yaml"))
        if path.is_file()
    ]
    return tuple(entries)
