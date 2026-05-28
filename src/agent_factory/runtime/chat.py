from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from agent_factory.config.catalog import FALLBACK_AGENT, AgentCatalog
from agent_factory.config.loader import load_agent_config
from agent_factory.config.scenario_catalog import ScenarioCatalog
from agent_factory.llm.base import LLMAdapter
from agent_factory.llm.config_litellm import ConfigDrivenLiteLLMAdapter, config_litellm_adapter_from_env
from agent_factory.llm.messages import ChatTurn
from agent_factory.runtime.approvals import ApprovalRecord, ApprovalStore
from agent_factory.runtime.learning import LearningArtifactsResult, generate_learning_artifacts
from agent_factory.runtime.multi_scenario import run_multi_scenario, run_single_scenario
from agent_factory.runtime.runner import AgentRunner
from agent_factory.runtime.session_store import ChatSession, ChatSessionStore
from agent_factory.runtime.states import RunResult, RunStatus
from agent_factory.runtime.trace import RunTrace
from agent_factory.routing.decision import RoutingDecision
from agent_factory.routing.resolver import (
    LiteLLMRoutingResolver,
    RoutingResolver,
    RuleBasedRoutingResolver,
    ScenarioAwareRoutingResolver,
)

LLMFactory = Callable[[str, Path], LLMAdapter]


@dataclass(frozen=True)
class ChatResult:
    reply: str
    status: RunStatus
    routed_agent: str
    route_reason: str
    run_id: str
    run_dir: Path
    routing_run_id: str
    session_id: str
    model_used: str | None = None
    learning: LearningArtifactsResult | None = None
    result: RunResult | None = None
    approval_id: str = ""
    pending_approval: dict[str, str] | None = None
    decision_kind: str = "single_agent"
    scenario_id: str | None = None
    correlation_id: str | None = None


def run_chat(
    message: str,
    *,
    workspace_root: str | Path,
    agents_dir: str | Path | None = None,
    scenarios_dir: str | Path | None = None,
    session_id: str | None = None,
    routing_resolver: RoutingResolver | None = None,
    specialist_llm: LLMAdapter | None = None,
    llm_factory: LLMFactory | None = None,
    use_litellm_proxy: bool = False,
) -> ChatResult:
    workspace = Path(workspace_root).resolve()
    resolved_agents_dir = Path(agents_dir) if agents_dir is not None else workspace / "configs" / "agents"
    scenario_catalog = _load_scenario_catalog(workspace, scenarios_dir)
    sessions = ChatSessionStore(workspace)
    session = sessions.load(session_id) if session_id else sessions.create()
    session.append("user", message)
    sessions.save(session)

    catalog = AgentCatalog(resolved_agents_dir)
    history = _history_from_session(session)

    routing_run_id = uuid.uuid4().hex[:12]
    routing_run_dir = workspace / ".agent-factory" / "runs" / routing_run_id
    routing_run_dir.mkdir(parents=True, exist_ok=True)
    routing_trace = RunTrace(routing_run_dir)

    resolver = routing_resolver or _default_routing_resolver(
        workspace,
        resolved_agents_dir,
        scenario_catalog,
        use_litellm_proxy=use_litellm_proxy,
    )
    decision = resolver.resolve(message, catalog)
    _append_routing_decision(routing_trace, decision, session.session_id)

    if decision.decision_kind == "multi_scenario":
        return _run_chat_multi_scenario(
            message=message,
            decision=decision,
            workspace=workspace,
            session=sessions,
            session_obj=session,
            scenario_catalog=scenario_catalog,
            routing_run_id=routing_run_id,
            llm_factory=llm_factory,
            specialist_llm=specialist_llm,
        )

    if decision.decision_kind == "scenario" and decision.scenario_id:
        return _run_chat_scenario(
            message=message,
            decision=decision,
            workspace=workspace,
            session=sessions,
            session_obj=session,
            scenario_catalog=scenario_catalog,
            routing_run_id=routing_run_id,
            llm_factory=llm_factory,
            specialist_llm=specialist_llm,
        )

    return _run_chat_single_agent(
        message=message,
        decision=decision,
        workspace=workspace,
        session=sessions,
        session_obj=session,
        catalog=catalog,
        history=history,
        routing_run_id=routing_run_id,
        specialist_llm=specialist_llm,
        use_litellm_proxy=use_litellm_proxy,
    )


def resolve_approval(
    approval_id: str,
    *,
    approved: bool,
    workspace_root: str | Path,
    agents_dir: str | Path | None = None,
    specialist_llm: LLMAdapter | None = None,
    use_litellm_proxy: bool = False,
) -> ChatResult:
    workspace = Path(workspace_root).resolve()
    resolved_agents_dir = Path(agents_dir) if agents_dir is not None else workspace / "configs" / "agents"
    catalog = AgentCatalog(resolved_agents_dir)
    approvals = ApprovalStore(workspace)
    record = approvals.load(approval_id)
    status = "approved" if approved else "denied"
    approvals.update_status(approval_id, status)

    sessions = ChatSessionStore(workspace)
    session = sessions.load(record.session_id)
    history = _history_from_session(session)

    config = load_agent_config(catalog.path_for(record.agent_name))
    run_dir = workspace / ".agent-factory" / "runs" / record.run_id
    trace = RunTrace(run_dir)
    llm = specialist_llm or _build_specialist_llm(config, use_litellm_proxy=use_litellm_proxy, history=history)

    runner = AgentRunner(config=config, llm=llm, trace=trace, workspace_root=workspace)
    result = runner.continue_from_approval(
        record.task,
        record.tool_messages,
        record.to_pending_tool(),
        approved=approved,
    )

    decision = RoutingDecision(
        target_agent=record.agent_name,
        delegated_task=record.task,
        reason=f"Resumed after approval ({status}).",
        decision_kind="single_agent",
    )
    reply_note = f"[审批{'通过' if approved else '拒绝'}] "
    chat_result = _finalize_chat_result(
        workspace=workspace,
        session=sessions,
        session_obj=session,
        message=reply_note + record.reason,
        decision=decision,
        config=config,
        result=result,
        run_id=record.run_id,
        run_dir=run_dir,
        routing_run_id="",
        llm=llm,
        approval_id=approval_id,
    )
    if not approved:
        session.append("assistant", chat_result.reply)
        sessions.save(session)
    return chat_result


def _run_chat_single_agent(
    *,
    message: str,
    decision: RoutingDecision,
    workspace: Path,
    session: ChatSessionStore,
    session_obj: ChatSession,
    catalog: AgentCatalog,
    history: tuple[ChatTurn, ...],
    routing_run_id: str,
    specialist_llm: LLMAdapter | None,
    use_litellm_proxy: bool,
) -> ChatResult:
    target_agent = decision.target_agent or FALLBACK_AGENT
    if decision.decision_kind == "fallback":
        target_agent = FALLBACK_AGENT

    run_id = uuid.uuid4().hex[:12]
    run_dir = workspace / ".agent-factory" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    trace = RunTrace(run_dir)

    config = load_agent_config(catalog.path_for(target_agent))
    llm = specialist_llm or _build_specialist_llm(config, use_litellm_proxy=use_litellm_proxy, history=history)

    runner = AgentRunner(config=config, llm=llm, trace=trace, workspace_root=workspace)
    result = runner.run(decision.delegated_task, history=history)

    routed = RoutingDecision(
        target_agent=target_agent,
        delegated_task=decision.delegated_task,
        reason=decision.reason,
        decision_kind=decision.decision_kind,
        scenario_id=decision.scenario_id,
        subtasks=decision.subtasks,
        correlation_id=decision.correlation_id,
    )
    return _finalize_chat_result(
        workspace=workspace,
        session=session,
        session_obj=session_obj,
        message=message,
        decision=routed,
        config=config,
        result=result,
        run_id=run_id,
        run_dir=run_dir,
        routing_run_id=routing_run_id,
        llm=llm,
    )


def _run_chat_scenario(
    *,
    message: str,
    decision: RoutingDecision,
    workspace: Path,
    session: ChatSessionStore,
    session_obj: ChatSession,
    scenario_catalog: ScenarioCatalog,
    routing_run_id: str,
    llm_factory: LLMFactory | None,
    specialist_llm: LLMAdapter | None,
) -> ChatResult:
    factory = llm_factory or _llm_factory_from_specialist(specialist_llm)
    orchestrator_result = run_single_scenario(
        decision,
        scenario_catalog=scenario_catalog,
        workspace_root=workspace,
        llm_factory=factory,
    )
    result = RunResult(
        status=orchestrator_result.status,
        output=orchestrator_result.output,
        reason="" if orchestrator_result.status == RunStatus.COMPLETED else orchestrator_result.output,
    )
    scenario_decision = RoutingDecision(
        target_agent=decision.scenario_id or "",
        delegated_task=decision.delegated_task,
        reason=decision.reason,
        decision_kind="scenario",
        scenario_id=decision.scenario_id,
    )
    config = load_agent_config(scenario_catalog.get(decision.scenario_id).orchestrator_path)
    llm = specialist_llm or _noop_llm()
    return _finalize_chat_result(
        workspace=workspace,
        session=session,
        session_obj=session_obj,
        message=message,
        decision=scenario_decision,
        config=config,
        result=result,
        run_id=orchestrator_result.run_id,
        run_dir=orchestrator_result.run_dir,
        routing_run_id=routing_run_id,
        llm=llm,
        generate_learning=False,
    )


def _run_chat_multi_scenario(
    *,
    message: str,
    decision: RoutingDecision,
    workspace: Path,
    session: ChatSessionStore,
    session_obj: ChatSession,
    scenario_catalog: ScenarioCatalog,
    routing_run_id: str,
    llm_factory: LLMFactory | None,
    specialist_llm: LLMAdapter | None,
) -> ChatResult:
    factory = llm_factory or _llm_factory_from_specialist(specialist_llm)
    multi_result = run_multi_scenario(
        decision,
        scenario_catalog=scenario_catalog,
        workspace_root=workspace,
        llm_factory=factory,
        merge_llm=specialist_llm,
        user_query=message,
    )
    statuses = {run.status for run in multi_result.runs}
    if statuses == {RunStatus.COMPLETED}:
        status = RunStatus.COMPLETED
    elif RunStatus.BLOCKED in statuses or RunStatus.AWAITING_CONFIRM in statuses:
        status = RunStatus.BLOCKED
    else:
        status = RunStatus.FAILED

    result = RunResult(
        status=status,
        output=multi_result.merged_output,
        reason="" if status == RunStatus.COMPLETED else multi_result.merged_output,
    )
    run_id = multi_result.correlation_id
    run_dir = workspace / ".agent-factory" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    trace = RunTrace(run_dir)
    trace.append(
        "multi_scenario_completed",
        {
            "correlation_id": multi_result.correlation_id,
            "scenario_runs": [
                {"scenario_id": run.scenario_id, "run_id": run.run_id, "status": run.status.value}
                for run in multi_result.runs
            ],
        },
    )

    multi_decision = RoutingDecision(
        target_agent="",
        delegated_task=decision.delegated_task,
        reason=decision.reason,
        decision_kind="multi_scenario",
        subtasks=decision.subtasks,
        correlation_id=multi_result.correlation_id,
    )
    config = load_agent_config(scenario_catalog.get(multi_result.runs[0].scenario_id).orchestrator_path)
    llm = specialist_llm or _noop_llm()
    return _finalize_chat_result(
        workspace=workspace,
        session=session,
        session_obj=session_obj,
        message=message,
        decision=multi_decision,
        config=config,
        result=result,
        run_id=run_id,
        run_dir=run_dir,
        routing_run_id=routing_run_id,
        llm=llm,
        generate_learning=False,
    )


def _finalize_chat_result(
    *,
    workspace: Path,
    session: ChatSessionStore,
    session_obj: ChatSession,
    message: str,
    decision: RoutingDecision,
    config,
    result: RunResult,
    run_id: str,
    run_dir: Path,
    routing_run_id: str,
    llm: LLMAdapter,
    approval_id: str = "",
    generate_learning: bool = True,
) -> ChatResult:
    approvals = ApprovalStore(workspace)
    pending_approval = None
    resolved_approval_id = approval_id

    if result.status == RunStatus.AWAITING_CONFIRM and result.pending_tool is not None:
        record = ApprovalRecord.from_tool_call(
            session_id=session_obj.session_id,
            run_id=run_id,
            agent_name=config.meta.name,
            task=decision.delegated_task,
            reason=result.reason,
            paused_turn=result.paused_turn,
            tool_messages=result.tool_messages,
            pending_tool=result.pending_tool,
        )
        approvals.save(record)
        resolved_approval_id = record.approval_id
        pending_approval = {
            "approval_id": record.approval_id,
            "tool": result.pending_tool.tool,
            "operation": result.pending_tool.operation,
            "target": result.pending_tool.target,
            "reason": result.reason,
        }
        reply = (
            f"需要您的确认：{result.pending_tool.tool}.{result.pending_tool.operation} "
            f"→ {result.pending_tool.target}\n原因：{result.reason}"
        )
    elif result.status == RunStatus.COMPLETED:
        reply = result.output
    else:
        reply = result.reason or result.output or "Run failed."

    if result.status == RunStatus.COMPLETED:
        session_obj.append("assistant", reply)
        session.save(session_obj)

    _write_chat_summary(run_dir, message, decision, result, reply)

    learning = None
    if generate_learning and result.status == RunStatus.COMPLETED:
        report_path = _find_report_path(run_dir)
        learning = generate_learning_artifacts(
            config,
            workspace_root=workspace,
            run_id=run_id,
            run_dir=run_dir,
            report_path=report_path,
            agent_name=config.meta.name,
            task=decision.delegated_task,
            source_url=_extract_url(message),
            status=result.status,
        )

    model_used = llm.active_model if isinstance(llm, ConfigDrivenLiteLLMAdapter) else None
    routed_agent = decision.scenario_id or decision.target_agent

    return ChatResult(
        reply=reply,
        status=result.status,
        routed_agent=routed_agent,
        route_reason=decision.reason,
        run_id=run_id,
        run_dir=run_dir,
        routing_run_id=routing_run_id,
        session_id=session_obj.session_id,
        model_used=model_used,
        learning=learning,
        result=result,
        approval_id=resolved_approval_id,
        pending_approval=pending_approval,
        decision_kind=decision.decision_kind,
        scenario_id=decision.scenario_id,
        correlation_id=decision.correlation_id,
    )


def _append_routing_decision(trace: RunTrace, decision: RoutingDecision, session_id: str) -> None:
    trace.append(
        "routing_decision",
        {
            "target_agent": decision.target_agent,
            "delegated_task": decision.delegated_task,
            "reason": decision.reason,
            "decision_kind": decision.decision_kind,
            "scenario_id": decision.scenario_id,
            "correlation_id": decision.correlation_id,
            "subtasks": [
                {"scenario_id": subtask.scenario_id, "task": subtask.task} for subtask in decision.subtasks
            ],
            "session_id": session_id,
        },
    )


def _load_scenario_catalog(workspace: Path, scenarios_dir: str | Path | None) -> ScenarioCatalog:
    root = Path(scenarios_dir) if scenarios_dir is not None else workspace / "configs" / "scenarios"
    return ScenarioCatalog(root)


def _history_from_session(session: ChatSession) -> tuple[ChatTurn, ...]:
    if len(session.turns) <= 1:
        return ()
    prior = session.turns[:-1]
    return tuple(ChatTurn(role=turn["role"], content=turn["content"]) for turn in prior)


def _default_routing_resolver(
    workspace: Path,
    agents_dir: Path,
    scenario_catalog: ScenarioCatalog,
    *,
    use_litellm_proxy: bool,
) -> RoutingResolver:
    if use_litellm_proxy:
        from agent_factory.routing.resolver import load_router_system_prompt

        router_path = agents_dir / "router.yaml"
        agent_resolver: RoutingResolver = LiteLLMRoutingResolver(
            system_prompt=load_router_system_prompt(router_path, scenario_catalog=scenario_catalog),
        )
    else:
        agent_resolver = RuleBasedRoutingResolver()
    return ScenarioAwareRoutingResolver(scenario_catalog=scenario_catalog, agent_resolver=agent_resolver)


def _build_specialist_llm(
    config,
    *,
    use_litellm_proxy: bool,
    history: tuple[ChatTurn, ...] = (),
) -> LLMAdapter:
    if use_litellm_proxy:
        return config_litellm_adapter_from_env(config, extra_system_prompt=_history_prompt(history))
    raise ValueError("specialist_llm is required when use_litellm_proxy is false.")


def _llm_factory_from_specialist(specialist_llm: LLMAdapter | None) -> LLMFactory | None:
    if specialist_llm is None:
        return None

    def factory(_member_id: str, _agent_path: Path) -> LLMAdapter:
        return specialist_llm

    return factory


def _noop_llm() -> LLMAdapter:
    from agent_factory.llm.fake import FakeLLMAdapter
    from agent_factory.llm.messages import FinalResponse

    return FakeLLMAdapter([FinalResponse(content="")])


def _history_prompt(history: tuple[ChatTurn, ...]) -> str:
    if not history:
        return ""
    lines = ["Conversation history:"]
    for turn in history:
        lines.append(f"{turn.role}: {turn.content}")
    return "\n".join(lines)


def _write_chat_summary(
    run_dir: Path,
    message: str,
    decision: RoutingDecision,
    result: RunResult,
    reply: str,
) -> None:
    trace = RunTrace(run_dir)
    routed = decision.scenario_id or decision.target_agent
    trace.write_summary(
        "\n".join(
            [
                "# Chat Run Summary",
                "",
                f"- User message: {message}",
                f"- Decision kind: {decision.decision_kind}",
                f"- Routed target: {routed}",
                f"- Route reason: {decision.reason}",
                f"- Status: {result.status.value}",
                f"- Reply: {reply}",
                "",
            ]
        )
    )


def _find_report_path(run_dir: Path) -> Path | None:
    report = run_dir / "artifact" / "report.md"
    return report if report.is_file() else None


def _extract_url(message: str) -> str | None:
    for token in message.split():
        if token.startswith("http://") or token.startswith("https://"):
            return token.rstrip(".,)")
    return None
