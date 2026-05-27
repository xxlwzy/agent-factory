from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_factory.config.schema import AgentFactoryConfig
from agent_factory.memory.candidates import write_project_memory_candidate, write_user_memory_candidate
from agent_factory.memory.session import archive_session_summary
from agent_factory.runtime.states import RunStatus
from agent_factory.skills.draft import write_skill_draft
from agent_factory.skills.review import write_review_status


@dataclass(frozen=True)
class LearningArtifactsResult:
    session_archive: Path | None = None
    project_candidate: Path | None = None
    user_candidate: Path | None = None
    skill_draft_dir: Path | None = None


def generate_learning_artifacts(
    config: AgentFactoryConfig,
    *,
    workspace_root: str | Path,
    run_id: str,
    run_dir: Path,
    report_path: Path | None,
    agent_name: str,
    task: str,
    source_url: str | None = None,
    status: RunStatus,
) -> LearningArtifactsResult:
    if status != RunStatus.COMPLETED:
        return LearningArtifactsResult()

    workspace = Path(workspace_root).resolve()
    report_excerpt = _read_report_excerpt(report_path)
    session_root = _resolve_workspace_path(config.memory.session_path, workspace)
    project_root = _resolve_workspace_path(config.memory.project_path, workspace)
    user_root = _resolve_workspace_path(config.memory.user_path, workspace)
    draft_root = _resolve_workspace_path(config.skills.draft_output_dir, workspace)

    session_archive = archive_session_summary(session_root, run_id, run_dir)
    project_candidate = write_project_memory_candidate(
        project_root,
        run_id=run_id,
        agent_name=agent_name,
        task=task,
        source_url=source_url,
        report_excerpt=report_excerpt,
    )
    user_candidate = write_user_memory_candidate(
        user_root,
        run_id=run_id,
        agent_name=agent_name,
        task=task,
    )
    draft_id = f"{_slug(agent_name)}-{run_id}"
    skill_draft_dir = write_skill_draft(
        draft_root,
        draft_id=draft_id,
        agent_name=agent_name,
        task=task,
        source_url=source_url,
        report_excerpt=report_excerpt,
    )
    write_review_status(skill_draft_dir)

    return LearningArtifactsResult(
        session_archive=session_archive,
        project_candidate=project_candidate,
        user_candidate=user_candidate,
        skill_draft_dir=skill_draft_dir,
    )


def _read_report_excerpt(report_path: Path | None, limit: int = 1500) -> str:
    if report_path is None or not report_path.is_file():
        return ""
    text = report_path.read_text(encoding="utf-8").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _resolve_workspace_path(path: str, workspace: Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = workspace / candidate
    return candidate.resolve()


def _slug(value: str) -> str:
    slug = "".join(char if char.isalnum() else "-" for char in value.lower()).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "agent"
