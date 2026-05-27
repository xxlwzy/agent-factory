from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_factory.skills.loader import default_skills_root
from agent_factory.skills.review import enable_skill_draft, read_review_status


def enable_skill_draft_api(
    workspace_root: str | Path,
    draft_id: str,
    *,
    skill_name: str | None = None,
) -> dict[str, Any]:
    if Path(draft_id).name != draft_id or draft_id in (".", ".."):
        raise ValueError("Invalid draft id.")

    workspace = Path(workspace_root).resolve()
    draft_dir = workspace / ".agent-factory" / "skills" / "drafts" / draft_id
    if not draft_dir.is_dir():
        raise FileNotFoundError(f"Skill draft not found: {draft_id}")

    dest_path = enable_skill_draft(
        draft_dir,
        default_skills_root(workspace),
        skill_name=skill_name,
    )
    return {
        "draft_id": draft_id,
        "status": read_review_status(draft_dir),
        "skill_name": dest_path.parent.name,
        "skill_path": str(dest_path.relative_to(workspace)),
    }
