from __future__ import annotations

import shutil
from pathlib import Path
from typing import Literal

MemoryLayer = Literal["project", "user"]
VALID_LAYERS: frozenset[str] = frozenset({"project", "user"})


def resolve_memory_root(workspace_root: str | Path, layer: MemoryLayer, *, base_path: str) -> Path:
    if layer not in VALID_LAYERS:
        raise ValueError(f"Invalid memory layer '{layer}'.")
    root = Path(base_path)
    if not root.is_absolute():
        root = Path(workspace_root).resolve() / root
    return root.resolve()


def list_memory_candidates(memory_root: Path) -> list[dict[str, str]]:
    candidates_dir = memory_root / "candidates"
    if not candidates_dir.is_dir():
        return []
    items: list[dict[str, str]] = []
    for path in sorted(candidates_dir.glob("*.md")):
        if path.is_file():
            items.append({"candidate_id": path.stem, "path": str(path)})
    items.sort(key=lambda item: item["candidate_id"], reverse=True)
    return items


def promote_memory_candidate(memory_root: Path, candidate_id: str) -> Path:
    if Path(candidate_id).name != candidate_id or candidate_id in (".", ".."):
        raise ValueError("Invalid candidate id.")

    source = memory_root / "candidates" / f"{candidate_id}.md"
    if not source.is_file():
        raise FileNotFoundError(f"Memory candidate not found: {candidate_id}")

    memory_root.mkdir(parents=True, exist_ok=True)
    destination = memory_root / f"{candidate_id}.md"
    shutil.copyfile(source, destination)
    return destination
