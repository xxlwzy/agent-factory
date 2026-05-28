import json
from pathlib import Path

from agent_factory.config.scenario_schema import load_scenario_entry
from agent_factory.llm.fake import FakeLLMAdapter
from agent_factory.llm.messages import FinalResponse, ToolCallResponse
from agent_factory.runtime.states import RunStatus
from agent_factory.team.orchestrator_runner import run_scenario_orchestrator


def test_orchestrator_two_delegates_complete_with_summary(tmp_path: Path) -> None:
    scenario_root = _write_scenario(tmp_path)

    def llm_factory(member_id: str, agent_path: Path) -> FakeLLMAdapter:
        if member_id == "orchestrator":
            return FakeLLMAdapter(
                [
                    ToolCallResponse(
                        tool="team",
                        operation="delegate",
                        target=json.dumps({"receiver": "researcher", "task": "Find solar facts"}),
                    ),
                    ToolCallResponse(
                        tool="team",
                        operation="delegate",
                        target=json.dumps({"receiver": "writer", "task": "Write report"}),
                    ),
                    FinalResponse(content="Report pipeline complete."),
                ]
            )
        if member_id == "researcher":
            return FakeLLMAdapter([FinalResponse(content="Research: solar is efficient.")])
        return FakeLLMAdapter([FinalResponse(content="# Report\n\nSolar is efficient.")])

    scenario = load_scenario_entry(scenario_root)
    result = run_scenario_orchestrator(
        scenario,
        "Research renewable energy",
        workspace_root=tmp_path,
        llm_factory=llm_factory,
    )

    assert result.status == RunStatus.COMPLETED
    assert result.output == "Report pipeline complete."
    assert len(result.delegations) == 2
    assert (result.run_dir / "summary.md").is_file()
    events = _trace_events(result.run_dir)
    assert any(event["type"] == "run_completed" for event in events)
    delegate_events = [event for event in events if event["type"] == "team_delegate"]
    assert len(delegate_events) == 2
    assert all(event["data"]["scenario_id"] == "demo-scenario" for event in delegate_events)
    assert all(event["data"]["message_id"] for event in delegate_events)
    assert not any(
        event["type"] == "tool_executed"
        and event["data"].get("tool") == "filesystem"
        and event["data"].get("operation", "").lower() == "write"
        for event in events
    )


def test_orchestrator_max_delegations_blocks(tmp_path: Path) -> None:
    scenario_root = _write_scenario(tmp_path)

    def llm_factory(member_id: str, agent_path: Path) -> FakeLLMAdapter:
        if member_id == "orchestrator":
            return FakeLLMAdapter(
                [
                    ToolCallResponse(
                        tool="team",
                        operation="delegate",
                        target=json.dumps({"receiver": "researcher", "task": "task-1"}),
                    ),
                    ToolCallResponse(
                        tool="team",
                        operation="delegate",
                        target=json.dumps({"receiver": "writer", "task": "task-2"}),
                    ),
                ]
            )
        return FakeLLMAdapter([FinalResponse(content="done")])

    scenario = load_scenario_entry(scenario_root)
    result = run_scenario_orchestrator(
        scenario,
        "Too many delegates",
        workspace_root=tmp_path,
        llm_factory=llm_factory,
        max_delegations=1,
    )

    assert result.status in {RunStatus.BLOCKED, RunStatus.FAILED}
    events = _trace_events(result.run_dir)
    assert any(event["type"] == "delegate_guard_triggered" for event in events)


def test_orchestrator_duplicate_delegate_guard(tmp_path: Path) -> None:
    scenario_root = _write_scenario(tmp_path)
    duplicate_target = json.dumps({"receiver": "researcher", "task": "same task"})

    def llm_factory(member_id: str, agent_path: Path) -> FakeLLMAdapter:
        if member_id == "orchestrator":
            return FakeLLMAdapter(
                [
                    ToolCallResponse(tool="team", operation="delegate", target=duplicate_target),
                    ToolCallResponse(tool="team", operation="delegate", target=duplicate_target),
                ]
            )
        return FakeLLMAdapter([FinalResponse(content="done")])

    scenario = load_scenario_entry(scenario_root)
    result = run_scenario_orchestrator(
        scenario,
        "Duplicate delegate",
        workspace_root=tmp_path,
        llm_factory=llm_factory,
    )

    assert result.status in {RunStatus.BLOCKED, RunStatus.FAILED}
    events = _trace_events(result.run_dir)
    assert any(
        event["type"] == "delegate_guard_triggered"
        and "Duplicate delegate" in event["data"]["reason"]
        for event in events
    )


def _write_scenario(tmp_path: Path) -> Path:
    root = tmp_path / "configs" / "scenarios" / "demo-scenario"
    members = root / "members"
    members.mkdir(parents=True)
    (root / "scenario.yaml").write_text(
        """
id: demo-scenario
display_name: Demo
entry: orchestrator.yaml
""",
        encoding="utf-8",
    )
    (root / "orchestrator.yaml").write_text(
        """
meta:
  name: demo_orchestrator
agent:
  role: orchestrator
  model: fake
  system_prompt: coordinate
runtime:
  max_turns: 6
tools:
  team:
    enabled: true
  filesystem:
    enabled: false
permissions:
  sandbox:
    paths:
      - .
""",
        encoding="utf-8",
    )
    for member_id in ("researcher", "writer"):
        (members / f"{member_id}.yaml").write_text(
            f"""
meta:
  name: {member_id}
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


def _trace_events(run_dir: Path) -> list[dict]:
    trace_path = run_dir / "trace.jsonl"
    return [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]
