from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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
