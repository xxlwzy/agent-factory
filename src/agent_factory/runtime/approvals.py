from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from agent_factory.llm.messages import ToolCallResponse


@dataclass(frozen=True)
class ApprovalRecord:
    approval_id: str
    session_id: str
    run_id: str
    agent_name: str
    task: str
    reason: str
    paused_turn: int
    tool_messages: tuple[str, ...]
    pending_tool: dict[str, Any]
    status: str = "pending"

    @classmethod
    def from_tool_call(
        cls,
        *,
        session_id: str,
        run_id: str,
        agent_name: str,
        task: str,
        reason: str,
        paused_turn: int,
        tool_messages: tuple[str, ...],
        pending_tool: ToolCallResponse,
    ) -> ApprovalRecord:
        return cls(
            approval_id=uuid.uuid4().hex[:12],
            session_id=session_id,
            run_id=run_id,
            agent_name=agent_name,
            task=task,
            reason=reason,
            paused_turn=paused_turn,
            tool_messages=tool_messages,
            pending_tool={
                "tool": pending_tool.tool,
                "operation": pending_tool.operation,
                "target": pending_tool.target,
                "content": pending_tool.content,
            },
        )

    def to_pending_tool(self) -> ToolCallResponse:
        return ToolCallResponse(
            tool=self.pending_tool["tool"],
            operation=self.pending_tool["operation"],
            target=self.pending_tool["target"],
            content=self.pending_tool.get("content", ""),
        )


class ApprovalStore:
    def __init__(self, workspace_root: str | Path) -> None:
        self._root = Path(workspace_root).resolve() / ".agent-factory" / "approvals"
        self._root.mkdir(parents=True, exist_ok=True)

    def save(self, record: ApprovalRecord) -> Path:
        path = self._path(record.approval_id)
        path.write_text(json.dumps(asdict(record), ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        return path

    def load(self, approval_id: str) -> ApprovalRecord:
        path = self._path(approval_id)
        if not path.is_file():
            raise FileNotFoundError(f"Approval not found: {approval_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        data["tool_messages"] = tuple(data.get("tool_messages", ()))
        return ApprovalRecord(**data)

    def list_pending(self) -> list[ApprovalRecord]:
        records: list[ApprovalRecord] = []
        for path in sorted(self._root.glob("*.json")):
            raw = json.loads(path.read_text(encoding="utf-8"))
            raw["tool_messages"] = tuple(raw.get("tool_messages", ()))
            record = ApprovalRecord(**raw)
            if record.status == "pending":
                records.append(record)
        return records

    def update_status(self, approval_id: str, status: str) -> ApprovalRecord:
        record = self.load(approval_id)
        updated = ApprovalRecord(**{**asdict(record), "status": status})
        self.save(updated)
        return updated

    def _path(self, approval_id: str) -> Path:
        if Path(approval_id).name != approval_id:
            raise ValueError("Invalid approval id.")
        return self._root / f"{approval_id}.json"
