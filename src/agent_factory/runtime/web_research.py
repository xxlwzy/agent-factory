from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from agent_factory.config.loader import load_agent_config
from agent_factory.llm.base import LLMAdapter
from agent_factory.llm.litellm_proxy import LiteLLMProxyAdapter, litellm_proxy_adapter_from_env
from agent_factory.llm.web_research_demo import WebResearchDemoLLM
from agent_factory.runtime.runner import AgentRunner
from agent_factory.runtime.states import RunResult, RunStatus
from agent_factory.runtime.trace import RunTrace
from agent_factory.tools.http import HttpFetcher
from agent_factory.tools.registry import build_default_registry


@dataclass(frozen=True)
class WebResearchDemoResult:
    run_id: str
    run_dir: Path
    report_path: Path
    result: RunResult
    model_used: str | None = None


def run_web_research_demo(
    *,
    agent_config_path: str | Path,
    url: str,
    workspace_root: str | Path,
    http_fetcher: HttpFetcher | None = None,
    run_id: str | None = None,
    task: str | None = None,
    llm: LLMAdapter | None = None,
    use_litellm_proxy: bool = False,
    litellm_model: str | None = None,
) -> WebResearchDemoResult:
    workspace = Path(workspace_root).resolve()
    config = load_agent_config(agent_config_path)
    resolved_run_id = run_id or uuid.uuid4().hex[:12]
    run_dir = workspace / ".agent-factory" / "runs" / resolved_run_id
    report_rel = Path(".agent-factory") / "runs" / resolved_run_id / "artifact" / "report.md"
    (run_dir / "artifact").mkdir(parents=True, exist_ok=True)

    trace = RunTrace(run_dir)
    resolved_llm = llm
    if resolved_llm is None and use_litellm_proxy:
        resolved_llm = litellm_proxy_adapter_from_env(
            system_prompt=config.agent.system_prompt,
            source_url=url,
            report_path=str(report_rel),
            model=litellm_model,
        )
    if resolved_llm is None:
        resolved_llm = WebResearchDemoLLM(url=url, report_path=str(report_rel))
    registry = build_default_registry(config, workspace, http_fetcher=http_fetcher)
    runner = AgentRunner(
        config=config,
        llm=resolved_llm,
        trace=trace,
        workspace_root=workspace,
        tool_registry=registry,
    )
    run_task = task or f"Research and summarize {url}"
    result = runner.run(run_task)
    _write_run_summary(trace, config.meta.name, url, result, report_rel)
    model_used = resolved_llm.active_model if isinstance(resolved_llm, LiteLLMProxyAdapter) else None
    return WebResearchDemoResult(
        run_id=resolved_run_id,
        run_dir=run_dir,
        report_path=workspace / report_rel,
        result=result,
        model_used=model_used,
    )


def _write_run_summary(
    trace: RunTrace,
    agent_name: str,
    url: str,
    result: RunResult,
    report_rel: Path,
) -> None:
    lines = [
        "# Run Summary",
        "",
        f"- Agent: {agent_name}",
        f"- Source URL: {url}",
        f"- Status: {result.status.value}",
    ]
    if result.status == RunStatus.COMPLETED:
        lines.append(f"- Report: {report_rel.as_posix()}")
        lines.append(f"- Output: {result.output}")
    elif result.reason:
        lines.append(f"- Reason: {result.reason}")
    trace.write_summary("\n".join(lines) + "\n")
