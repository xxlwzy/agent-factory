from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_factory.config.loader import load_agent_config
from agent_factory.memory.promote import (
    MemoryLayer,
    list_memory_candidates,
    promote_memory_candidate,
    resolve_memory_root,
)


def list_candidates_api(
    workspace_root: str | Path,
    layer: MemoryLayer,
    *,
    agents_dir: str | Path | None = None,
) -> list[dict[str, str]]:
    memory_root = _memory_root_for_layer(workspace_root, layer, agents_dir=agents_dir)
    promoted_ids = {path.stem for path in memory_root.glob("*.md") if path.is_file()}
    candidates = list_memory_candidates(memory_root)
    return [
        {
            **item,
            "layer": layer,
            "promoted": item["candidate_id"] in promoted_ids,
        }
        for item in candidates
    ]


def promote_candidate_api(
    workspace_root: str | Path,
    layer: MemoryLayer,
    candidate_id: str,
    *,
    agents_dir: str | Path | None = None,
) -> dict[str, Any]:
    memory_root = _memory_root_for_layer(workspace_root, layer, agents_dir=agents_dir)
    destination = promote_memory_candidate(memory_root, candidate_id)
    workspace = Path(workspace_root).resolve()
    return {
        "layer": layer,
        "candidate_id": candidate_id,
        "path": str(destination.relative_to(workspace)),
    }


def _memory_root_for_layer(
    workspace_root: str | Path,
    layer: MemoryLayer,
    *,
    agents_dir: str | Path | None = None,
) -> Path:
    workspace = Path(workspace_root).resolve()
    agents_path = Path(agents_dir) if agents_dir is not None else workspace / "configs" / "agents"
    agent_files = sorted(agents_path.glob("*.yaml"))
    if not agent_files:
        base = ".agent-factory/memory/project" if layer == "project" else ".agent-factory/memory/user"
        return resolve_memory_root(workspace, layer, base_path=base)

    config = load_agent_config(agent_files[0])
    base_path = config.memory.project_path if layer == "project" else config.memory.user_path
    return resolve_memory_root(workspace, layer, base_path=base_path)
