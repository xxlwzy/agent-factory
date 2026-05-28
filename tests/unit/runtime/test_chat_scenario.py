import json
from pathlib import Path

from agent_factory.config.scenario_catalog import ScenarioCatalog
from agent_factory.llm.fake import FakeLLMAdapter
from agent_factory.llm.messages import FinalResponse, ToolCallResponse
from agent_factory.routing.resolver import ScenarioAwareRoutingResolver
from agent_factory.runtime.chat import run_chat
from agent_factory.runtime.states import RunStatus


def test_run_chat_scenario_starts_orchestrator_run(tmp_path: Path) -> None:
    scenarios_root = tmp_path / "configs" / "scenarios"
    _write_scenario(scenarios_root, "demo-scenario")
    _agents_dir(tmp_path)

    def llm_factory(member_id: str, agent_path: Path) -> FakeLLMAdapter:
        if member_id == "orchestrator":
            return FakeLLMAdapter(
                [
                    ToolCallResponse(
                        tool="team",
                        operation="delegate",
                        target=json.dumps({"receiver": "worker", "task": "Gather notes"}),
                    ),
                    FinalResponse(content="Scenario orchestration complete."),
                ]
            )
        return FakeLLMAdapter([FinalResponse(content="Worker output")])

    result = run_chat(
        "Please use scenario:demo-scenario for this task",
        workspace_root=tmp_path,
        routing_resolver=ScenarioAwareRoutingResolver(scenario_catalog=ScenarioCatalog(scenarios_root)),
        llm_factory=llm_factory,
    )

    assert result.status == RunStatus.COMPLETED
    assert result.decision_kind == "scenario"
    assert result.scenario_id == "demo-scenario"
    assert result.routed_agent == "demo-scenario"
    assert result.reply == "Scenario orchestration complete."
    assert (result.run_dir / "summary.md").is_file()

    trace_events = _trace_events(result.run_dir)
    assert any(event["type"] == "team_delegate" for event in trace_events)
    assert any(event["type"] == "run_completed" for event in trace_events)


def test_run_chat_multi_scenario_records_correlation_id(tmp_path: Path) -> None:
    scenarios_root = tmp_path / "configs" / "scenarios"
    _write_scenario(scenarios_root, "alpha")
    _write_scenario(scenarios_root, "beta")
    _agents_dir(tmp_path)

    def llm_factory(member_id: str, agent_path: Path) -> FakeLLMAdapter:
        if member_id == "orchestrator":
            return FakeLLMAdapter(
                [
                    ToolCallResponse(
                        tool="team",
                        operation="delegate",
                        target=json.dumps({"receiver": "worker", "task": "do work"}),
                    ),
                    FinalResponse(content=f"done-{agent_path.parent.name}"),
                ]
            )
        return FakeLLMAdapter([FinalResponse(content="member output")])

    merge_llm = FakeLLMAdapter([FinalResponse(content="Merged parallel scenario summaries.")])
    message = "parallel: alpha | alpha task\nparallel: beta | beta task"

    result = run_chat(
        message,
        workspace_root=tmp_path,
        routing_resolver=ScenarioAwareRoutingResolver(scenario_catalog=ScenarioCatalog(scenarios_root)),
        llm_factory=llm_factory,
        specialist_llm=merge_llm,
    )

    assert result.status == RunStatus.COMPLETED
    assert result.decision_kind == "multi_scenario"
    assert result.correlation_id
    assert result.reply == "Merged parallel scenario summaries."

    routing_trace = _trace_events(tmp_path / ".agent-factory" / "runs" / result.routing_run_id)
    routing_event = next(event for event in routing_trace if event["type"] == "routing_decision")
    assert routing_event["data"]["decision_kind"] == "multi_scenario"
    assert routing_event["data"]["correlation_id"]


def _write_scenario(scenarios_root: Path, scenario_id: str) -> None:
    root = scenarios_root / scenario_id
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


def _agents_dir(tmp_path: Path) -> Path:
    agents_dir = tmp_path / "configs" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / "general_assistant.yaml").write_text(
        "meta:\n  name: general_assistant\n  description: General\n"
        "agent:\n  role: General\n  model: fake\n  system_prompt: test\n"
        "tools:\n  filesystem:\n    enabled: true\npermissions:\n  sandbox:\n    paths: [.]\n",
        encoding="utf-8",
    )
    return agents_dir


def _trace_events(run_dir: Path) -> list[dict]:
    trace_path = run_dir / "trace.jsonl"
    if not trace_path.is_file():
        return []
    return [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]
