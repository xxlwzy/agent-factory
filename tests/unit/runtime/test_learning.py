from pathlib import Path

from agent_factory.config.schema import (
    AgentConfig,
    AgentFactoryConfig,
    MemoryConfig,
    MetaConfig,
    PermissionsConfig,
    RuntimeConfig,
    SkillsConfig,
    ToolConfig,
)
from agent_factory.runtime.learning import generate_learning_artifacts
from agent_factory.runtime.states import RunStatus
from agent_factory.runtime.trace import RunTrace
from agent_factory.skills.review import REVIEW_STATUS_PENDING, read_review_status


def test_generate_learning_artifacts_on_completed_run(tmp_path: Path) -> None:
    run_id = "run-abc"
    run_dir = tmp_path / ".agent-factory" / "runs" / run_id
    run_dir.mkdir(parents=True)
    report_path = run_dir / "artifact" / "report.md"
    report_path.parent.mkdir(parents=True)
    report_path.write_text("# Demo Report\n\nKey fact.\n", encoding="utf-8")
    RunTrace(run_dir).write_summary("# Run Summary\n\n- Status: completed\n")

    config = _config(tmp_path)
    result = generate_learning_artifacts(
        config,
        workspace_root=tmp_path,
        run_id=run_id,
        run_dir=run_dir,
        report_path=report_path,
        agent_name="web_researcher",
        task="Research https://example.com",
        source_url="https://example.com",
        status=RunStatus.COMPLETED,
    )

    assert result.session_archive is not None
    assert result.session_archive.is_file()
    assert result.project_candidate is not None
    assert result.user_candidate is not None
    assert result.skill_draft_dir is not None
    assert (result.skill_draft_dir / "SKILL.md").is_file()
    assert read_review_status(result.skill_draft_dir) == REVIEW_STATUS_PENDING
    assert "Key fact" in result.project_candidate.read_text(encoding="utf-8")


def test_generate_learning_artifacts_skips_non_completed_run(tmp_path: Path) -> None:
    run_id = "run-failed"
    run_dir = tmp_path / ".agent-factory" / "runs" / run_id
    run_dir.mkdir(parents=True)

    result = generate_learning_artifacts(
        _config(tmp_path),
        workspace_root=tmp_path,
        run_id=run_id,
        run_dir=run_dir,
        report_path=None,
        agent_name="web_researcher",
        task="Research https://example.com",
        source_url="https://example.com",
        status=RunStatus.FAILED,
    )

    assert result.session_archive is None
    assert result.project_candidate is None
    assert result.user_candidate is None
    assert result.skill_draft_dir is None


def _config(workspace: Path) -> AgentFactoryConfig:
    return AgentFactoryConfig(
        meta=MetaConfig(name="web_researcher"),
        agent=AgentConfig(role="researcher", model="fake", system_prompt="test"),
        runtime=RuntimeConfig(),
        tools={"filesystem": ToolConfig(enabled=True)},
        permissions=PermissionsConfig(),
        memory=MemoryConfig(
            session_path=str(workspace / ".agent-factory/memory/session"),
            project_path=str(workspace / ".agent-factory/memory/project"),
            user_path=str(workspace / ".agent-factory/memory/user"),
        ),
        skills=SkillsConfig(draft_output_dir=str(workspace / ".agent-factory/skills/drafts")),
    )
