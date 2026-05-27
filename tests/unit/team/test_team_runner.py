import json
from pathlib import Path

from agent_factory.config.team_schema import load_team_config
from agent_factory.llm.fake import FakeLLMAdapter
from agent_factory.llm.messages import FinalResponse
from agent_factory.runtime.states import RunStatus
from agent_factory.team.runner import run_team


def test_team_pipeline_research_then_write(tmp_path: Path) -> None:
    agents = tmp_path / "configs" / "agents"
    agents.mkdir(parents=True)
    _write_minimal_agent(agents / "researcher.yaml", "researcher")
    _write_minimal_agent(agents / "writer.yaml", "writer")

    teams = tmp_path / "configs" / "teams"
    teams.mkdir(parents=True)
    team_path = teams / "demo.yaml"
    team_path.write_text(
        """
meta:
  name: demo
team:
  members:
    - id: researcher
      agent: researcher.yaml
    - id: writer
      agent: writer.yaml
  pipeline:
    - member: researcher
      task: "{team_task}"
    - member: writer
      task: "Write report from: {last_output}"
""",
        encoding="utf-8",
    )

    def llm_factory(member_id: str, agent_path: Path) -> FakeLLMAdapter:
        if member_id == "researcher":
            return FakeLLMAdapter([FinalResponse(content="Research: solar panels are efficient.")])
        return FakeLLMAdapter([FinalResponse(content="# Report\n\nSolar panels are efficient.")])

    team = load_team_config(team_path)
    result = run_team(
        team,
        "Research renewable energy",
        team_config_path=team_path,
        workspace_root=tmp_path,
        agents_dir=agents,
        llm_factory=llm_factory,
    )

    assert result.final_output.startswith("# Report")
    assert len(result.steps) == 2
    assert all(step.status == RunStatus.COMPLETED for step in result.steps)
    writer_step = result.steps[1]
    assert writer_step.inbound_message_id is not None
    events = _trace_events(writer_step.run_dir)
    assert any(event["type"] == "team_message_received" for event in events)
    received = next(event for event in events if event["type"] == "team_message_received")
    assert received["data"]["message_id"] == writer_step.inbound_message_id
    assert any(event["type"] == "team_message_sent" for event in events)


def test_repo_research_report_team_config_loads() -> None:
    repo = Path(__file__).resolve().parents[3]
    team_path = repo / "configs" / "teams" / "research_report.yaml"
    team = load_team_config(team_path)
    assert team.name == "research_report"
    assert [step.member_id for step in team.pipeline] == ["researcher", "writer"]


def _write_minimal_agent(path: Path, name: str) -> None:
    path.write_text(
        f"""
meta:
  name: {name}
agent:
  role: tester
  model: fake
  system_prompt: test
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


def _trace_events(run_dir: Path) -> list[dict]:
    trace_path = run_dir / "trace.jsonl"
    return [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]
