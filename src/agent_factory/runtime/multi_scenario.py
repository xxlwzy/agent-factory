from __future__ import annotations

import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from agent_factory.api.store import WorkspaceStore
from agent_factory.config.scenario_catalog import ScenarioCatalog
from agent_factory.config.scenario_schema import ScenarioEntry
from agent_factory.llm.base import LLMAdapter
from agent_factory.llm.messages import FinalResponse, LLMRequest
from agent_factory.routing.decision import RoutingDecision, ScenarioSubtask
from agent_factory.runtime.states import RunStatus
from agent_factory.team.orchestrator_runner import OrchestratorRunResult, run_scenario_orchestrator

LLMFactory = Callable[[str, Path], LLMAdapter]


@dataclass(frozen=True)
class ScenarioRunResult:
    scenario_id: str
    run_id: str
    run_dir: Path
    output: str
    status: RunStatus
    summary: str


@dataclass(frozen=True)
class MultiScenarioRunResult:
    correlation_id: str
    runs: tuple[ScenarioRunResult, ...]
    merged_output: str


def run_multi_scenario(
    decision: RoutingDecision,
    *,
    scenario_catalog: ScenarioCatalog,
    workspace_root: str | Path,
    llm_factory: LLMFactory | None = None,
    merge_llm: LLMAdapter | None = None,
    user_query: str = "",
) -> MultiScenarioRunResult:
    if decision.decision_kind != "multi_scenario":
        raise ValueError("run_multi_scenario requires decision_kind='multi_scenario'.")
    if not decision.subtasks:
        raise ValueError("multi_scenario decision requires subtasks.")

    correlation_id = decision.correlation_id or uuid.uuid4().hex[:12]
    workspace = Path(workspace_root).resolve()

    runs = _run_subtasks_parallel(
        decision.subtasks,
        scenario_catalog=scenario_catalog,
        workspace=workspace,
        llm_factory=llm_factory,
    )
    merged = merge_scenario_summaries(
        [run.run_id for run in runs],
        workspace_root=workspace,
        llm=merge_llm or _default_merge_llm(runs),
        user_query=user_query or decision.delegated_task,
    )
    return MultiScenarioRunResult(correlation_id=correlation_id, runs=tuple(runs), merged_output=merged)


def run_single_scenario(
    decision: RoutingDecision,
    *,
    scenario_catalog: ScenarioCatalog,
    workspace_root: str | Path,
    llm_factory: LLMFactory | None = None,
) -> OrchestratorRunResult:
    if decision.decision_kind != "scenario" or not decision.scenario_id:
        raise ValueError("run_single_scenario requires decision_kind='scenario' with scenario_id.")
    scenario = scenario_catalog.get(decision.scenario_id)
    return run_scenario_orchestrator(
        scenario,
        decision.delegated_task,
        workspace_root=workspace_root,
        llm_factory=llm_factory,
    )


def merge_scenario_summaries(
    run_ids: list[str],
    *,
    workspace_root: str | Path,
    llm: LLMAdapter,
    user_query: str,
) -> str:
    store = WorkspaceStore(workspace_root)
    summaries = [read_run_summary_only(store, run_id) for run_id in run_ids]
    prompt = _build_merge_prompt(user_query, summaries)
    response = llm.next_response(LLMRequest(task=prompt))
    if not isinstance(response, FinalResponse):
        raise RuntimeError("Summary merge LLM must return a final response.")
    return response.content


def read_run_summary_only(store: WorkspaceStore, run_id: str) -> str:
    return store.read_run(run_id)["summary"]


def _run_subtasks_parallel(
    subtasks: tuple[ScenarioSubtask, ...],
    *,
    scenario_catalog: ScenarioCatalog,
    workspace: Path,
    llm_factory: LLMFactory | None,
) -> list[ScenarioRunResult]:
    results: list[ScenarioRunResult] = []
    with ThreadPoolExecutor(max_workers=len(subtasks)) as executor:
        futures = {
            executor.submit(
                _run_one_subtask,
                subtask,
                scenario_catalog=scenario_catalog,
                workspace=workspace,
                llm_factory=llm_factory,
            ): subtask
            for subtask in subtasks
        }
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda item: item.scenario_id)
    return results


def _run_one_subtask(
    subtask: ScenarioSubtask,
    *,
    scenario_catalog: ScenarioCatalog,
    workspace: Path,
    llm_factory: LLMFactory | None,
) -> ScenarioRunResult:
    scenario = scenario_catalog.get(subtask.scenario_id)
    orchestrator_result = run_scenario_orchestrator(
        scenario,
        subtask.task,
        workspace_root=workspace,
        llm_factory=llm_factory,
    )
    store = WorkspaceStore(workspace)
    summary = read_run_summary_only(store, orchestrator_result.run_id)
    return ScenarioRunResult(
        scenario_id=subtask.scenario_id,
        run_id=orchestrator_result.run_id,
        run_dir=orchestrator_result.run_dir,
        output=orchestrator_result.output,
        status=orchestrator_result.status,
        summary=summary,
    )


def _build_merge_prompt(user_query: str, summaries: list[str]) -> str:
    blocks = "\n\n".join(f"### Summary {index + 1}\n{summary}" for index, summary in enumerate(summaries))
    return (
        "Merge the following scenario team summaries into one user-facing reply. "
        "Use only the summary text provided; do not invent details.\n\n"
        f"User query:\n{user_query}\n\n"
        f"{blocks}"
    )


def _default_merge_llm(runs: list[ScenarioRunResult]) -> LLMAdapter:
    from agent_factory.llm.fake import FakeLLMAdapter

    merged = " | ".join(run.summary.strip().splitlines()[0] for run in runs if run.summary.strip())
    return FakeLLMAdapter([FinalResponse(content=f"Merged: {merged}")])
