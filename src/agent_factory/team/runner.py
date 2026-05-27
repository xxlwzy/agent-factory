from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from agent_factory.config.loader import load_agent_config
from agent_factory.config.team_schema import TeamConfig, TeamMember, resolve_member_agent_path
from agent_factory.llm.base import LLMAdapter
from agent_factory.runtime.runner import AgentRunner
from agent_factory.runtime.states import RunStatus
from agent_factory.runtime.trace import RunTrace
from agent_factory.team.bus import MessageBus, TeamMessage


@dataclass(frozen=True)
class TeamStepResult:
    member_id: str
    run_id: str
    run_dir: Path
    output: str
    status: RunStatus
    inbound_message_id: str | None = None
    outbound_message_id: str | None = None


@dataclass(frozen=True)
class TeamRunResult:
    team_name: str
    team_task: str
    final_output: str
    steps: tuple[TeamStepResult, ...]
    bus: MessageBus


LLMFactory = Callable[[str, Path], LLMAdapter]


def run_team(
    team: TeamConfig,
    team_task: str,
    *,
    team_config_path: str | Path,
    workspace_root: str | Path,
    agents_dir: str | Path | None = None,
    llm_factory: LLMFactory | None = None,
    bus: MessageBus | None = None,
) -> TeamRunResult:
    workspace = Path(workspace_root).resolve()
    team_path = Path(team_config_path).resolve()
    resolved_agents_dir = Path(agents_dir) if agents_dir is not None else workspace / "configs" / "agents"
    members_by_id = {member.member_id: member for member in team.members}
    message_bus = bus or MessageBus()

    last_output = ""
    step_results: list[TeamStepResult] = []
    previous_member: str | None = None

    for step_index, pipeline_step in enumerate(team.pipeline):
        member = members_by_id[pipeline_step.member_id]
        formatted_task = _format_task(
            pipeline_step.task_template,
            team_task=team_task,
            last_output=last_output,
        )

        inbound_message_id: str | None = None
        if previous_member is not None:
            handoff = message_bus.send(
                sender=previous_member,
                receiver=member.member_id,
                task_ref=f"step-{step_index}",
                payload=last_output,
            )
            inbound_message_id = handoff.message_id

        step_result = _run_member_step(
            member,
            formatted_task,
            team_path=team_path,
            workspace=workspace,
            agents_dir=resolved_agents_dir,
            llm_factory=llm_factory,
            inbound_message_id=inbound_message_id,
            bus=message_bus,
        )
        step_results.append(step_result)
        last_output = step_result.output
        previous_member = member.member_id

        if step_result.status != RunStatus.COMPLETED:
            return TeamRunResult(
                team_name=team.name,
                team_task=team_task,
                final_output=last_output,
                steps=tuple(step_results),
                bus=message_bus,
            )

    return TeamRunResult(
        team_name=team.name,
        team_task=team_task,
        final_output=last_output,
        steps=tuple(step_results),
        bus=message_bus,
    )


def _run_member_step(
    member: TeamMember,
    task: str,
    *,
    team_path: Path,
    workspace: Path,
    agents_dir: Path,
    llm_factory: LLMFactory | None,
    inbound_message_id: str | None,
    bus: MessageBus,
) -> TeamStepResult:
    agent_path = resolve_member_agent_path(team_path, member.agent, agents_dir)
    config = load_agent_config(agent_path)
    run_id = f"team-{member.member_id}-{uuid.uuid4().hex[:8]}"
    run_dir = workspace / ".agent-factory" / "runs" / run_id
    trace = RunTrace(run_dir)
    trace.append(
        "team_step_started",
        {
            "team_member": member.member_id,
            "agent_config": str(agent_path),
            "inbound_message_id": inbound_message_id,
        },
    )
    if inbound_message_id:
        inbound = bus.get(inbound_message_id)
        if inbound is not None:
            trace.append(
                "team_message_received",
                {
                    "message_id": inbound.message_id,
                    "sender": inbound.sender,
                    "receiver": inbound.receiver,
                    "task_ref": inbound.task_ref,
                },
            )
            bus.mark_processed(inbound_message_id)

    llm = llm_factory(member.member_id, agent_path) if llm_factory is not None else _default_llm(member.member_id)
    runner = AgentRunner(config=config, llm=llm, trace=trace, workspace_root=workspace)
    result = runner.run(task)

    outbound_message_id: str | None = None
    if result.status == RunStatus.COMPLETED and result.output:
        outbound = bus.send(
            sender=member.member_id,
            receiver="team",
            task_ref=run_id,
            payload=result.output,
        )
        outbound_message_id = outbound.message_id
        trace.append(
            "team_message_sent",
            {
                "message_id": outbound.message_id,
                "sender": outbound.sender,
                "receiver": outbound.receiver,
                "task_ref": outbound.task_ref,
            },
        )

    trace.write_summary(
        f"# Team Step\n\n- Member: {member.member_id}\n- Status: {result.status.value}\n"
    )
    return TeamStepResult(
        member_id=member.member_id,
        run_id=run_id,
        run_dir=run_dir,
        output=result.output,
        status=result.status,
        inbound_message_id=inbound_message_id,
        outbound_message_id=outbound_message_id,
    )


def _format_task(template: str, *, team_task: str, last_output: str) -> str:
    return (
        template.replace("{team_task}", team_task)
        .replace("{last_output}", last_output)
        .strip()
    )


def _default_llm(member_id: str) -> LLMAdapter:
    from agent_factory.llm.fake import FakeLLMAdapter
    from agent_factory.llm.messages import FinalResponse

    return FakeLLMAdapter([FinalResponse(content=f"output from {member_id}")])
