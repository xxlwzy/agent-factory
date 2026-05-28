import json
from pathlib import Path

from agent_factory.config.catalog import AgentCatalog, FALLBACK_AGENT
from agent_factory.config.scenario_catalog import ScenarioCatalog
from agent_factory.llm.fake import FakeLLMAdapter
from agent_factory.llm.messages import FinalResponse, ToolCallResponse
from agent_factory.routing.decision import ScenarioSubtask
from agent_factory.routing.scenario_resolver import RuleBasedScenarioRoutingResolver
from agent_factory.runtime.multi_scenario import merge_scenario_summaries, run_multi_scenario
from agent_factory.runtime.states import RunStatus


def test_rule_scenario_resolver_single_scenario(tmp_path: Path) -> None:
    scenario_root = _write_scenario(tmp_path, "alpha")
    agents_dir = _agents_dir(tmp_path)
    resolver = RuleBasedScenarioRoutingResolver()

    decision = resolver.resolve(
        "请用 scenario:alpha 做调研",
        agent_catalog=AgentCatalog(agents_dir),
        scenario_catalog=ScenarioCatalog(scenario_root.parent),
    )

    assert decision.decision_kind == "scenario"
    assert decision.scenario_id == "alpha"


def test_rule_scenario_resolver_multi_scenario(tmp_path: Path) -> None:
    scenarios_root = tmp_path / "configs" / "scenarios"
    _write_scenario(tmp_path, "alpha", scenarios_root=scenarios_root)
    _write_scenario(tmp_path, "beta", scenarios_root=scenarios_root)
    agents_dir = _agents_dir(tmp_path)
    resolver = RuleBasedScenarioRoutingResolver()

    decision = resolver.resolve(
        "parallel: alpha | task A\nparallel: beta | task B",
        agent_catalog=AgentCatalog(agents_dir),
        scenario_catalog=ScenarioCatalog(scenarios_root),
    )

    assert decision.decision_kind == "multi_scenario"
    assert decision.subtasks == (
        ScenarioSubtask(scenario_id="alpha", task="task A"),
        ScenarioSubtask(scenario_id="beta", task="task B"),
    )


def test_rule_scenario_resolver_fallback(tmp_path: Path) -> None:
    scenario_root = _write_scenario(tmp_path, "alpha")
    agents_dir = _agents_dir(tmp_path)
    resolver = RuleBasedScenarioRoutingResolver()

    decision = resolver.resolve(
        "你好",
        agent_catalog=AgentCatalog(agents_dir),
        scenario_catalog=ScenarioCatalog(scenario_root.parent),
    )

    assert decision.decision_kind == "fallback"
    assert decision.target_agent == FALLBACK_AGENT


def test_parallel_two_scenarios_produce_summaries_and_merge(tmp_path: Path) -> None:
    scenarios_root = tmp_path / "configs" / "scenarios"
    _write_scenario(tmp_path, "alpha", scenarios_root=scenarios_root)
    _write_scenario(tmp_path, "beta", scenarios_root=scenarios_root)
    catalog = ScenarioCatalog(scenarios_root)

    def llm_factory(member_id: str, agent_path: Path) -> FakeLLMAdapter:
        if member_id == "orchestrator":
            return FakeLLMAdapter(
                [
                    ToolCallResponse(
                        tool="team",
                        operation="delegate",
                        target=json.dumps({"receiver": "worker", "task": "do work"}),
                    ),
                    FinalResponse(content=f"done from {agent_path.parent.name}"),
                ]
            )
        return FakeLLMAdapter([FinalResponse(content="member output")])

    from agent_factory.routing.decision import RoutingDecision

    decision = RoutingDecision(
        target_agent="",
        delegated_task="parallel jobs",
        reason="test",
        decision_kind="multi_scenario",
        subtasks=(
            ScenarioSubtask(scenario_id="alpha", task="alpha task"),
            ScenarioSubtask(scenario_id="beta", task="beta task"),
        ),
        correlation_id="corr-1",
    )
    merge_llm = FakeLLMAdapter([FinalResponse(content="Combined alpha and beta summaries.")])

    result = run_multi_scenario(
        decision,
        scenario_catalog=catalog,
        workspace_root=tmp_path,
        llm_factory=llm_factory,
        merge_llm=merge_llm,
        user_query="parallel jobs",
    )

    assert len(result.runs) == 2
    assert all(run.status == RunStatus.COMPLETED for run in result.runs)
    assert all((run.run_dir / "summary.md").is_file() for run in result.runs)
    assert result.merged_output == "Combined alpha and beta summaries."


def test_merge_reads_summary_only_not_trace(tmp_path: Path) -> None:
    run_dir = tmp_path / ".agent-factory" / "runs" / "run-1"
    run_dir.mkdir(parents=True)
    (run_dir / "summary.md").write_text("# Scenario Orchestrator\n\n- Status: completed\n", encoding="utf-8")
    (run_dir / "trace.jsonl").write_text('{"type":"secret"}\n', encoding="utf-8")

    merge_llm = FakeLLMAdapter([FinalResponse(content="ok")])

    merged = merge_scenario_summaries(
        ["run-1"],
        workspace_root=tmp_path,
        llm=merge_llm,
        user_query="test",
    )

    assert merged == "ok"
    request = merge_llm._responses  # type: ignore[attr-defined]
    assert len(request) == 0


def _write_scenario(
    tmp_path: Path,
    scenario_id: str,
    *,
    scenarios_root: Path | None = None,
) -> Path:
    root = (scenarios_root or tmp_path / "configs" / "scenarios") / scenario_id
    members = root / "members"
    members.mkdir(parents=True)
    (root / "scenario.yaml").write_text(
        f"id: {scenario_id}\ndisplay_name: {scenario_id}\nentry: orchestrator.yaml\n",
        encoding="utf-8",
    )
    (root / "orchestrator.yaml").write_text(
        """
meta:
  name: orch
agent:
  role: orchestrator
  model: fake
  system_prompt: coordinate
runtime:
  max_turns: 4
tools:
  team:
    enabled: true
permissions:
  sandbox:
    paths:
      - .
""",
        encoding="utf-8",
    )
    (members / "worker.yaml").write_text(
        """
meta:
  name: worker
agent:
  role: teammate
  model: fake
  system_prompt: work
tools:
  filesystem:
    enabled: true
permissions:
  sandbox:
    paths:
      - .
""",
        encoding="utf-8",
    )
    return root


def _agents_dir(tmp_path: Path) -> Path:
    agents_dir = tmp_path / "configs" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    return agents_dir
