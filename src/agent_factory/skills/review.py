from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_factory.skills.index import parse_skill_markdown

REVIEW_STATUS_PENDING = "pending"
REVIEW_STATUS_REVIEWED = "reviewed"
REVIEW_STATUS_ENABLED = "enabled"


def write_review_status(draft_dir: Path, status: str = REVIEW_STATUS_PENDING) -> Path:
    draft_dir.mkdir(parents=True, exist_ok=True)
    review_path = draft_dir / "review.json"
    review_path.write_text(
        json.dumps({"status": status}, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return review_path


def read_review_status(draft_dir: Path) -> str:
    review_path = draft_dir / "review.json"
    data = json.loads(review_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("review.json must be a JSON object.")
    status = data.get("status")
    if not isinstance(status, str):
        raise ValueError("review.json must include string field 'status'.")
    return status


def enable_skill_draft(
    draft_dir: Path,
    skills_root: Path,
    *,
    skill_name: str | None = None,
) -> Path:
    skill_path = draft_dir / "SKILL.md"
    if not skill_path.is_file():
        raise FileNotFoundError(f"Draft SKILL.md not found in {draft_dir}")

    raw = skill_path.read_text(encoding="utf-8")
    parsed = parse_skill_markdown(raw)
    resolved_name = _slug(skill_name or parsed.name or draft_dir.name)
    if not resolved_name:
        raise ValueError("Could not determine skill name for enable.")

    if parsed.name:
        content = raw
    else:
        description = parsed.description or "Enabled from skill draft."
        body = parsed.body or raw
        content = _skill_markdown_with_frontmatter(resolved_name, description, body)

    dest_dir = skills_root / resolved_name
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / "SKILL.md"
    dest_path.write_text(content, encoding="utf-8")
    write_review_status(draft_dir, REVIEW_STATUS_ENABLED)
    return dest_path


def _skill_markdown_with_frontmatter(name: str, description: str, body: str) -> str:
    return (
        "---\n"
        f"name: {name}\n"
        f"description: {description}\n"
        "---\n\n"
        f"{body.strip()}\n"
    )


def _slug(value: str) -> str:
    slug = "".join(char if char.isalnum() else "-" for char in value.lower()).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "skill"
