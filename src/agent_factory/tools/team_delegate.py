from __future__ import annotations

import json

from agent_factory.team.bus import MessageBus
from agent_factory.tools.base import ToolResult


class TeamDelegateTool:
    name = "team"

    def __init__(
        self,
        bus: MessageBus,
        *,
        scenario_id: str = "",
        sender: str = "orchestrator",
    ) -> None:
        self._bus = bus
        self._scenario_id = scenario_id
        self._sender = sender

    def execute(self, operation: str, target: str, *, content: str = "") -> ToolResult:
        if operation.lower() != "delegate":
            return ToolResult(success=False, error=f"Unsupported team operation '{operation}'.")

        try:
            payload = json.loads(target)
        except json.JSONDecodeError as error:
            return ToolResult(success=False, error=f"Invalid delegate JSON: {error}")

        if not isinstance(payload, dict):
            return ToolResult(success=False, error="Delegate target must be a JSON object.")

        receiver = str(payload.get("receiver", "")).strip()
        task = str(payload.get("task", "")).strip()
        if not receiver:
            return ToolResult(success=False, error="Delegate requires 'receiver'.")
        if not task:
            return ToolResult(success=False, error="Delegate requires 'task'.")

        scenario_id = str(payload.get("scenario_id", self._scenario_id)).strip()
        message = self._bus.send(
            sender=self._sender,
            receiver=receiver,
            task_ref=task,
            payload=task,
            scenario_id=scenario_id,
        )
        return ToolResult(
            success=True,
            output=json.dumps(
                {
                    "message_id": message.message_id,
                    "receiver": receiver,
                    "scenario_id": scenario_id,
                },
                ensure_ascii=True,
            ),
        )
