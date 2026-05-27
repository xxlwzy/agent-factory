from pathlib import Path

from agent_factory.config.schema import (
    AgentConfig,
    AgentFactoryConfig,
    AutomationConfig,
    MetaConfig,
    PermissionsConfig,
    RuntimeConfig,
    ScheduleConfig,
    ToolConfig,
)
from agent_factory.llm.fake import FakeLLMAdapter
from agent_factory.llm.messages import FinalResponse
from agent_factory.scheduler.trigger import run_scheduled_task


def test_run_scheduled_task_writes_run_artifacts(tmp_path: Path) -> None:
    config = AgentFactoryConfig(
        meta=MetaConfig(name="scheduler_agent"),
        agent=AgentConfig(role="bot", model="fake", system_prompt="test"),
        runtime=RuntimeConfig(output_dir=".agent-factory/runs"),
        tools={"filesystem": ToolConfig(enabled=True)},
        permissions=PermissionsConfig(),
        automation=AutomationConfig(
            schedules=(
                ScheduleConfig(name="heartbeat", interval_seconds=60, task="check workspace"),
            )
        ),
    )
    schedule = config.automation.schedules[0]

    run_dir, result = run_scheduled_task(
        schedule,
        config,
        FakeLLMAdapter([FinalResponse(content="ok")]),
        workspace_root=tmp_path,
        run_id="sched-1",
    )

    assert result.output == "ok"
    assert run_dir.is_dir()
    assert (run_dir / "trace.jsonl").is_file()
    assert (run_dir / "summary.md").is_file()
    trace = (run_dir / "trace.jsonl").read_text(encoding="utf-8")
    assert "schedule_triggered" in trace
