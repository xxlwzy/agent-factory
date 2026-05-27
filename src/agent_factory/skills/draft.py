from __future__ import annotations

from pathlib import Path


def write_skill_draft(
    draft_root: Path,
    *,
    draft_id: str,
    agent_name: str,
    task: str,
    source_url: str | None,
    report_excerpt: str,
) -> Path:
    draft_dir = draft_root / draft_id
    draft_dir.mkdir(parents=True, exist_ok=True)
    skill_path = draft_dir / "SKILL.md"
    lines = [
        f"# Skill Draft: {agent_name}",
        "",
        "> Status: pending human review. Do not auto-enable.",
        "",
        "## When to use",
        "",
        f"- Task pattern similar to: {task}",
    ]
    if source_url:
        lines.append(f"- Source URL example: {source_url}")
    lines.extend(
        [
            "",
            "## Steps",
            "",
            "1. Fetch the source page with HTTP GET inside the domain allowlist.",
            "2. Summarize the content into a Markdown report.",
            "3. Write the report to the run artifact path under `.agent-factory/runs/<run_id>/artifact/`.",
            "",
            "## Reference output excerpt",
            "",
            report_excerpt.strip() or "(no report excerpt available)",
            "",
        ]
    )
    skill_path.write_text("\n".join(lines), encoding="utf-8")
    return draft_dir
