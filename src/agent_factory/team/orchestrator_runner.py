from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from agent_factory.config.loader import load_agent_config
from agent_factory.config.role_templates import AgentRole, apply_role_tool_template
from agent_factory.config.scenario_schema import ScenarioEntry, ScenarioMemberEntry
from agent_factory.config.schema import AgentFactoryConfig
from agent_factory.llm.base import LLMAdapter
from agent_factory.runtime.runner import AgentRunner
from agent_factory.runtime.states import RunStatus
from agent_factory.runtime.trace import RunTrace
from agent_factory.team.bus import MessageBus
from agent_factory.tools.base import ToolAdapter, ToolResult
from agent_factory.tools.registry import ToolRegistry
from agent_factory.tools.team_delegate import TeamDelegateTool


@dataclass(frozen=True)
class DelegationStep:
    receiver: str
    task: str
    message_id: str
    member_run_id: str
    member_run_dir: Path
    member_output: str
    member_status: RunStatus


@dataclass(frozen=True)
class OrchestratorRunResult:
    scenario_id: str
    run_id: str
    run_dir: Path
    output: str
    status: RunStatus
    delegations: tuple[DelegationStep, ...]
    bus: MessageBus


LLMFactory = Callable[[str, Path], LLMAdapter]


@dataclass
class _DelegateGuard:
    max_delegations: int
    _count: int = 0
    _seen: set[str] = field(default_factory=set)

    def check(self, receiver: str, task: str) -> str | None:
        if self._count >= self.max_delegations:
            return f"Max delegations ({self.max_delegations}) exceeded."
        key = _task_key(receiver, task)
        if key in self._seen:
            return f"Duplicate delegate for receiver '{receiver}' and task."
        self._seen.add(key)
        self._count += 1
        return None


class _OrchestratedTeamDelegateTool(TeamDelegateTool):
    def __init__(
        self,
        bus: MessageBus,
        *,
        scenario_id: str,
        sender: str,
        guard: _DelegateGuard,
        orchestrator_trace: RunTrace,
        execute_teammate: Callable[[str, str, str], str],
    ) -> None:
        super().__init__(bus, scenario_id=scenario_id, sender=sender)
        self._guard = guard
        self._orchestrator_trace = orchestrator_trace
        self._execute_teammate = execute_teammate

    def execute(self, operation: str, target: str, *, content: str = "") -> ToolResult:
        if operation.lower() != "delegate":
            return super().execute(operation, target, content=content)

        try:
            payload = json.loads(target)
        except json.JSONDecodeError as error:
            return ToolResult(success=False, error=f"Invalid delegate JSON: {error}")

        receiver = str(payload.get("receiver", "")).strip()
        task = str(payload.get("task", "")).strip()
        guard_error = self._guard.check(receiver, task)
        if guard_error is not None:
            self._orchestrator_trace.append(
                "delegate_guard_triggered",
                {
                    "scenario_id": self._scenario_id,
                    "receiver": receiver,
                    "task": task,
                    "reason": guard_error,
                },
            )
            return ToolResult(success=False, error=guard_error)

        result = super().execute(operation, target, content=content)
        if not result.success:
            return result

        data = json.loads(result.output)
        message_id = data["message_id"]
        self._orchestrator_trace.append(
            "team_delegate",
            {
                "scenario_id": data.get("scenario_id", self._scenario_id),
                "message_id": message_id,
                "receiver": receiver,
                "task": task,
            },
        )
        teammate_output = self._execute_teammate(receiver, task, message_id)
        enriched = {**data, "member_output": teammate_output}
        return ToolResult(success=True, output=json.dumps(enriched, ensure_ascii=True))


def run_scenario_orchestrator(
    scenario: ScenarioEntry,
    task: str,
    *,
    workspace_root: str | Path,
    llm_factory: LLMFactory | None = None,
    bus: MessageBus | None = None,
    max_delegations: int = 8,
) -> OrchestratorRunResult:
    workspace = Path(workspace_root).resolve()
    message_bus = bus or MessageBus()
    members_by_id = {member.member_id: member for member in scenario.members}

    orchestrator_config = _load_orchestrator_config(scenario.orchestrator_path)
    run_id = f"scenario-{scenario.scenario_id}-{uuid.uuid4().hex[:8]}"
    run_dir = workspace / ".agent-factory" / "runs" / run_id
    trace = RunTrace(run_dir)
    trace.append(
        "scenario_run_started",
        {"scenario_id": scenario.scenario_id, "task": task, "run_id": run_id},
    )

    guard = _DelegateGuard(max_delegations=max_delegations)
    delegation_steps: list[DelegationStep] = []

    def execute_teammate(receiver: str, member_task: str, message_id: str) -> str:
        member = members_by_id.get(receiver)
        if member is None:
            trace.append(
                "delegate_teammate_missing",
                {"scenario_id": scenario.scenario_id, "receiver": receiver, "message_id": message_id},
            )
            return f"Unknown teammate '{receiver}'."

        step = _run_teammate(
            member,
            member_task,
            scenario_id=scenario.scenario_id,
            workspace=workspace,
            llm_factory=llm_factory,
            bus=message_bus,
            inbound_message_id=message_id,
        )
        delegation_steps.append(step)
        trace.append(
            "delegate_teammate_completed",
            {
                "scenario_id": scenario.scenario_id,
                "message_id": message_id,
                "receiver": receiver,
                "member_run_id": step.member_run_id,
                "member_status": step.member_status.value,
            },
        )
        return step.member_output

    registry = _build_orchestrator_registry(
        orchestrator_config,
        workspace,
        message_bus=message_bus,
        scenario_id=scenario.scenario_id,
        guard=guard,
        orchestrator_trace=trace,
        execute_teammate=execute_teammate,
    )

    llm = (
        llm_factory("orchestrator", scenario.orchestrator_path)
        if llm_factory is not None
        else _default_orchestrator_llm()
    )
    runner = AgentRunner(
        config=orchestrator_config,
        llm=llm,
        trace=trace,
        workspace_root=workspace,
        tool_registry=registry,
    )
    result = runner.run(task)

    trace.write_summary(
        f"# Scenario Orchestrator\n\n"
        f"- Scenario: {scenario.scenario_id}\n"
        f"- Status: {result.status.value}\n"
        f"- Delegations: {len(delegation_steps)}\n"
    )
    if result.status == RunStatus.COMPLETED:
        trace.append("run_completed", {"scenario_id": scenario.scenario_id, "output": result.output})

    return OrchestratorRunResult(
        scenario_id=scenario.scenario_id,
        run_id=run_id,
        run_dir=run_dir,
        output=result.output,
        status=result.status,
        delegations=tuple(delegation_steps),
        bus=message_bus,
    )


def _load_orchestrator_config(path: Path) -> AgentFactoryConfig:
    config = load_agent_config(path)
    tools = apply_role_tool_template(config.tools, AgentRole.ORCHESTRATOR)
    return AgentFactoryConfig(
        meta=config.meta,
        agent=config.agent,
        runtime=config.runtime,
        tools=tools,
        permissions=config.permissions,
        memory=config.memory,
        skills=config.skills,
        hooks=config.hooks,
        automation=config.automation,
        mcp=config.mcp,
    )


def _build_orchestrator_registry(
    config: AgentFactoryConfig,
    workspace: Path,
    *,
    message_bus: MessageBus,
    scenario_id: str,
    guard: _DelegateGuard,
    orchestrator_trace: RunTrace,
    execute_teammate: Callable[[str, str, str], str],
) -> ToolRegistry:
    adapters: dict[str, ToolAdapter] = {}
    team_config = config.tools.get("team")
    if team_config is not None and team_config.enabled:
        adapters["team"] = _OrchestratedTeamDelegateTool(
            message_bus,
            scenario_id=scenario_id,
            sender="orchestrator",
            guard=guard,
            orchestrator_trace=orchestrator_trace,
            execute_teammate=execute_teammate,
        )
    return ToolRegistry(adapters=adapters, enabled_tools=config.tools)


def _run_teammate(
    member: ScenarioMemberEntry,
    member_task: str,
    *,
    scenario_id: str,
    workspace: Path,
    llm_factory: LLMFactory | None,
    bus: MessageBus,
    inbound_message_id: str,
) -> DelegationStep:
    config = load_agent_config(member.path)
    run_id = f"member-{member.member_id}-{uuid.uuid4().hex[:8]}"
    run_dir = workspace / ".agent-factory" / "runs" / run_id
    trace = RunTrace(run_dir)
    trace.append(
        "teammate_run_started",
        {
            "scenario_id": scenario_id,
            "member_id": member.member_id,
            "inbound_message_id": inbound_message_id,
        },
    )
    inbound = bus.get(inbound_message_id)
    if inbound is not None:
        trace.append(
            "team_message_received",
            {
                "scenario_id": scenario_id,
                "message_id": inbound.message_id,
                "sender": inbound.sender,
                "receiver": inbound.receiver,
            },
        )
        bus.mark_processed(inbound_message_id)

    llm = llm_factory(member.member_id, member.path) if llm_factory is not None else _default_teammate_llm(member.member_id)
    runner = AgentRunner(config=config, llm=llm, trace=trace, workspace_root=workspace)
    result = runner.run(member_task)

    if result.status == RunStatus.COMPLETED and result.output:
        outbound = bus.send(
            sender=member.member_id,
            receiver="orchestrator",
            task_ref=run_id,
            payload=result.output,
            scenario_id=scenario_id,
        )
        trace.append(
            "team_message_sent",
            {
                "scenario_id": scenario_id,
                "message_id": outbound.message_id,
                "sender": outbound.sender,
                "receiver": outbound.receiver,
            },
        )

    trace.write_summary(
        f"# Teammate\n\n- Member: {member.member_id}\n- Status: {result.status.value}\n"
    )
    return DelegationStep(
        receiver=member.member_id,
        task=member_task,
        message_id=inbound_message_id,
        member_run_id=run_id,
        member_run_dir=run_dir,
        member_output=result.output,
        member_status=result.status,
    )


def _task_key(receiver: str, task: str) -> str:
    digest = hashlib.sha256(f"{receiver}\0{task}".encode()).hexdigest()
    return digest


def _default_orchestrator_llm() -> LLMAdapter:
    from agent_factory.llm.fake import FakeLLMAdapter
    from agent_factory.llm.messages import FinalResponse

    return FakeLLMAdapter([FinalResponse(content="Orchestrator complete.")])


def _default_teammate_llm(member_id: str) -> LLMAdapter:
    from agent_factory.llm.fake import FakeLLMAdapter
    from agent_factory.llm.messages import FinalResponse

    return FakeLLMAdapter([FinalResponse(content=f"output from {member_id}")])
