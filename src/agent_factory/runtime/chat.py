from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from agent_factory.config.catalog import FALLBACK_AGENT, AgentCatalog
from agent_factory.config.loader import load_agent_config
from agent_factory.llm.base import LLMAdapter
from agent_factory.llm.config_litellm import ConfigDrivenLiteLLMAdapter, config_litellm_adapter_from_env
from agent_factory.llm.messages import ChatTurn
from agent_factory.runtime.approvals import ApprovalRecord, ApprovalStore
from agent_factory.runtime.learning import LearningArtifactsResult, generate_learning_artifacts
from agent_factory.runtime.runner import AgentRunner
from agent_factory.runtime.session_store import ChatSession, ChatSessionStore
from agent_factory.runtime.states import RunResult, RunStatus
from agent_factory.runtime.trace import RunTrace
from agent_factory.routing.decision import RoutingDecision
from agent_factory.routing.resolver import LiteLLMRoutingResolver, RoutingResolver, RuleBasedRoutingResolver


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


def run_chat(
    message: str,
    *,
    workspace_root: str | Path,
    agents_dir: str | Path | None = None,
    session_id: str | None = None,
    routing_resolver: RoutingResolver | None = None,
    specialist_llm: LLMAdapter | None = None,
    use_litellm_proxy: bool = False,
) -> ChatResult:
    workspace = Path(workspace_root).resolve()
    resolved_agents_dir = Path(agents_dir) if agents_dir is not None else workspace / "configs" / "agents"
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

    resolver = routing_resolver or _default_routing_resolver(resolved_agents_dir, use_litellm_proxy)
    decision = resolver.resolve(message, catalog)
    routing_trace.append(
        "routing_decision",
        {
            "target_agent": decision.target_agent,
            "delegated_task": decision.delegated_task,
            "reason": decision.reason,
            "session_id": session.session_id,
        },
    )

    run_id = uuid.uuid4().hex[:12]
    run_dir = workspace / ".agent-factory" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    trace = RunTrace(run_dir)

    config = load_agent_config(catalog.path_for(decision.target_agent))
    llm = specialist_llm or _build_specialist_llm(config, use_litellm_proxy=use_litellm_proxy, history=history)

    runner = AgentRunner(config=config, llm=llm, trace=trace, workspace_root=workspace)
    result = runner.run(decision.delegated_task, history=history)

    return _finalize_chat_result(
        workspace=workspace,
        session=sessions,
        session_obj=session,
        message=message,
        decision=decision,
        config=config,
        result=result,
        run_id=run_id,
        run_dir=run_dir,
        routing_run_id=routing_run_id,
        llm=llm,
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
    if result.status == RunStatus.COMPLETED:
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

    return ChatResult(
        reply=reply,
        status=result.status,
        routed_agent=decision.target_agent,
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
    )


def _history_from_session(session: ChatSession) -> tuple[ChatTurn, ...]:
    if len(session.turns) <= 1:
        return ()
    prior = session.turns[:-1]
    return tuple(ChatTurn(role=turn["role"], content=turn["content"]) for turn in prior)


def _default_routing_resolver(agents_dir: Path, use_litellm_proxy: bool) -> RoutingResolver:
    if use_litellm_proxy:
        from agent_factory.routing.resolver import load_router_system_prompt

        return LiteLLMRoutingResolver(system_prompt=load_router_system_prompt(agents_dir / "router.yaml"))
    return RuleBasedRoutingResolver()


def _build_specialist_llm(
    config,
    *,
    use_litellm_proxy: bool,
    history: tuple[ChatTurn, ...] = (),
) -> LLMAdapter:
    if use_litellm_proxy:
        return config_litellm_adapter_from_env(config, extra_system_prompt=_history_prompt(history))
    raise ValueError("specialist_llm is required when use_litellm_proxy is false.")


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
    trace.write_summary(
        "\n".join(
            [
                "# Chat Run Summary",
                "",
                f"- User message: {message}",
                f"- Routed agent: {decision.target_agent}",
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
