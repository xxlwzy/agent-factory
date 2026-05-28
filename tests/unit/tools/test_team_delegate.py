import json

from agent_factory.team.bus import MessageBus
from agent_factory.tools.team_delegate import TeamDelegateTool


def test_team_delegate_sends_bus_message_with_scenario_id() -> None:
    bus = MessageBus()
    tool = TeamDelegateTool(bus, scenario_id="research-report", sender="orchestrator")

    result = tool.execute(
        "delegate",
        json.dumps({"receiver": "researcher", "task": "Find sources on solar energy"}),
    )

    assert result.success is True
    data = json.loads(result.output)
    assert data["message_id"]
    assert data["scenario_id"] == "research-report"
    message = bus.get(data["message_id"])
    assert message is not None
    assert message.receiver == "researcher"
    assert message.scenario_id == "research-report"


def test_team_delegate_rejects_invalid_operation() -> None:
    tool = TeamDelegateTool(MessageBus())

    result = tool.execute("broadcast", "{}")

    assert result.success is False
