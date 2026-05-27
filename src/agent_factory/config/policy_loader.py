from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from agent_factory.config.schema import PermissionsConfig, SandboxConfig


def policies_dir_for_agent(agent_config_path: Path) -> Path:
    return agent_config_path.parent.parent / "policies"


def policy_path_for_agent(agent_config_path: Path, policy_name: str) -> Path:
    return policies_dir_for_agent(agent_config_path) / f"{policy_name}.yaml"


def load_policy_permissions(policy_path: Path) -> PermissionsConfig:
    if not policy_path.is_file():
        raise ValueError(f"Policy file not found: {policy_path}")

    raw = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Policy file must be a YAML mapping: {policy_path}")

    permissions_raw = raw.get("permissions", raw)
    if not isinstance(permissions_raw, dict):
        raise ValueError(f"Policy permissions must be a mapping: {policy_path}")

    return _parse_permissions(permissions_raw)


def merge_permissions(base: PermissionsConfig, overlay: PermissionsConfig) -> PermissionsConfig:
    return PermissionsConfig(
        sandbox=SandboxConfig(
            paths=_union(base.sandbox.paths, overlay.sandbox.paths),
            domains=_union(base.sandbox.domains, overlay.sandbox.domains),
        ),
        confirm=_union(base.confirm, overlay.confirm),
        deny=_union(base.deny, overlay.deny),
    )


def resolve_agent_permissions(
    agent_config_path: Path,
    permissions_raw: dict[str, Any],
    policy_name: str | None,
) -> PermissionsConfig:
    agent_permissions = _parse_permissions(permissions_raw)
    if policy_name is None:
        return agent_permissions

    policy_path = policy_path_for_agent(agent_config_path, policy_name)
    policy_permissions = load_policy_permissions(policy_path)
    return merge_permissions(policy_permissions, agent_permissions)


def _parse_permissions(raw: dict[str, Any]) -> PermissionsConfig:
    sandbox_raw = raw.get("sandbox", {})
    if sandbox_raw is not None and not isinstance(sandbox_raw, dict):
        raise ValueError("permissions.sandbox must be a mapping.")

    sandbox_mapping = sandbox_raw if isinstance(sandbox_raw, dict) else {}
    return PermissionsConfig(
        sandbox=SandboxConfig(
            paths=tuple(str(path) for path in sandbox_mapping.get("paths", ())),
            domains=tuple(str(domain) for domain in sandbox_mapping.get("domains", ())),
        ),
        confirm=tuple(str(rule) for rule in raw.get("confirm", ())),
        deny=tuple(str(rule) for rule in raw.get("deny", ())),
    )


def _union(left: tuple[str, ...], right: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    merged: list[str] = []
    for value in left + right:
        if value in seen:
            continue
        seen.add(value)
        merged.append(value)
    return tuple(merged)
