from __future__ import annotations

from pathlib import Path


def write_project_memory_candidate(
    project_root: Path,
    *,
    run_id: str,
    agent_name: str,
    task: str,
    source_url: str | None,
    report_excerpt: str,
) -> Path:
    candidates_dir = project_root / "candidates"
    candidates_dir.mkdir(parents=True, exist_ok=True)
    path = candidates_dir / f"{run_id}.md"
    lines = [
        "# Project Memory Candidate",
        "",
        f"- Run ID: {run_id}",
        f"- Agent: {agent_name}",
        f"- Task: {task}",
    ]
    if source_url:
        lines.append(f"- Source URL: {source_url}")
    lines.extend(
        [
            "- Status: pending human review",
            "",
            "## Suggested project context",
            "",
            report_excerpt.strip() or "(no report excerpt available)",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_user_memory_candidate(
    user_root: Path,
    *,
    run_id: str,
    agent_name: str,
    task: str,
) -> Path:
    candidates_dir = user_root / "candidates"
    candidates_dir.mkdir(parents=True, exist_ok=True)
    path = candidates_dir / f"{run_id}.md"
    content = (
        "# User Memory Candidate\n\n"
        f"- Run ID: {run_id}\n"
        f"- Agent: {agent_name}\n"
        f"- Task: {task}\n"
        "- Status: pending human review\n\n"
        "## Suggested user preference\n\n"
        f"User completed a `{agent_name}` task successfully. "
        "Review whether to persist recurring preferences or sources.\n"
    )
    path.write_text(content, encoding="utf-8")
    return path
