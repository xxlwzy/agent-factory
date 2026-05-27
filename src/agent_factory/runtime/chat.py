from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from agent_factory.config.catalog import FALLBACK_AGENT, AgentCatalog
from agent_factory.config.loader import load_agent_config
from agent_factory.llm.base import LLMAdapter
from agent_factory.llm.config_litellm import ConfigDrivenLiteLLMAdapter, config_litellm_adapter_from_env
from agent_factory.llm.fake import FakeLLMAdapter
from agent_factory.runtime.learning import LearningArtifactsResult, generate_learning_artifacts
from agent_factory.runtime.runner import AgentRunner
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
    model_used: str | None = None
    learning: LearningArtifactsResult | None = None
    result: RunResult | None = None


def run_chat(
    message: str,
    *,
    workspace_root: str | Path,
    agents_dir: str | Path | None = None,
    routing_resolver: RoutingResolver | None = None,
    specialist_llm: LLMAdapter | None = None,
    use_litellm_proxy: bool = False,
) -> ChatResult:
    workspace = Path(workspace_root).resolve()
    resolved_agents_dir = Path(agents_dir) if agents_dir is not None else workspace / "configs" / "agents"
    catalog = AgentCatalog(resolved_agents_dir)

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
        },
    )

    run_id = uuid.uuid4().hex[:12]
    run_dir = workspace / ".agent-factory" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    trace = RunTrace(run_dir)

    config_path = catalog.path_for(decision.target_agent)
    config = load_agent_config(config_path)
    llm = specialist_llm or _build_specialist_llm(config, use_litellm_proxy=use_litellm_proxy)

    runner = AgentRunner(config=config, llm=llm, trace=trace, workspace_root=workspace)
    result = runner.run(decision.delegated_task)

    reply = result.output if result.status == RunStatus.COMPLETED else (result.reason or result.output or "Run failed.")
    _write_chat_summary(trace, message, decision, result, reply)

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
        model_used=model_used,
        learning=learning,
        result=result,
    )


def _default_routing_resolver(agents_dir: Path, use_litellm_proxy: bool) -> RoutingResolver:
    if use_litellm_proxy:
        from agent_factory.routing.resolver import load_router_system_prompt

        return LiteLLMRoutingResolver(system_prompt=load_router_system_prompt(agents_dir / "router.yaml"))
    return RuleBasedRoutingResolver()


def _build_specialist_llm(config, *, use_litellm_proxy: bool) -> LLMAdapter:
    if use_litellm_proxy:
        return config_litellm_adapter_from_env(config)
    raise ValueError("specialist_llm is required when use_litellm_proxy is false.")


def _write_chat_summary(
    trace: RunTrace,
    message: str,
    decision: RoutingDecision,
    result: RunResult,
    reply: str,
) -> None:
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
