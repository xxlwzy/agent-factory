from __future__ import annotations

import uuid
from pathlib import Path

from agent_factory.config.schema import AgentFactoryConfig, ScheduleConfig
from agent_factory.llm.base import LLMAdapter
from agent_factory.runtime.runner import AgentRunner
from agent_factory.runtime.states import RunResult
from agent_factory.runtime.trace import RunTrace


def run_scheduled_task(
    schedule: ScheduleConfig,
    config: AgentFactoryConfig,
    llm: LLMAdapter,
    *,
    workspace_root: str | Path,
    run_id: str | None = None,
) -> tuple[Path, RunResult]:
    workspace = Path(workspace_root).resolve()
    resolved_run_id = run_id or f"schedule-{schedule.name}-{uuid.uuid4().hex[:8]}"
    output_root = _resolve_output_root(config, workspace)
    run_dir = output_root / resolved_run_id
    trace = RunTrace(run_dir)

    trace.append(
        "schedule_triggered",
        {
            "schedule": schedule.name,
            "interval_seconds": schedule.interval_seconds,
            "task": schedule.task,
        },
    )

    runner = AgentRunner(config=config, llm=llm, trace=trace, workspace_root=workspace)
    result = runner.run(schedule.task)
    trace.write_summary(_schedule_summary(schedule, result))
    return run_dir, result


def _resolve_output_root(config: AgentFactoryConfig, workspace: Path) -> Path:
    output_dir = Path(config.runtime.output_dir)
    if not output_dir.is_absolute():
        output_dir = workspace / output_dir
    return output_dir.resolve()


def _schedule_summary(schedule: ScheduleConfig, result: RunResult) -> str:
    return (
        f"# Scheduled Run\n\n"
        f"- Schedule: {schedule.name}\n"
        f"- Interval seconds: {schedule.interval_seconds}\n"
        f"- Status: {result.status.value}\n"
        f"- Output: {result.output or ''}\n"
    )
