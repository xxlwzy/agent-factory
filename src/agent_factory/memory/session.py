from __future__ import annotations

import shutil
from pathlib import Path


def archive_session_summary(session_root: Path, run_id: str, run_dir: Path) -> Path | None:
    summary_path = run_dir / "summary.md"
    if not summary_path.is_file():
        return None

    session_root.mkdir(parents=True, exist_ok=True)
    archive_path = session_root / f"{run_id}.md"
    shutil.copyfile(summary_path, archive_path)
    return archive_path
