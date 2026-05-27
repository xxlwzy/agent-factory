from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ChatSession:
    session_id: str
    turns: list[dict[str, str]] = field(default_factory=list)

    def append(self, role: str, content: str) -> None:
        self.turns.append({"role": role, "content": content})

    def to_dict(self) -> dict[str, Any]:
        return {"session_id": self.session_id, "turns": self.turns}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChatSession:
        return cls(session_id=str(data["session_id"]), turns=list(data.get("turns", [])))


class ChatSessionStore:
    def __init__(self, workspace_root: str | Path) -> None:
        self._root = Path(workspace_root).resolve() / ".agent-factory" / "sessions"
        self._root.mkdir(parents=True, exist_ok=True)

    def create(self) -> ChatSession:
        session = ChatSession(session_id=uuid.uuid4().hex[:12])
        self.save(session)
        return session

    def load(self, session_id: str) -> ChatSession:
        path = self._path(session_id)
        if not path.is_file():
            raise FileNotFoundError(f"Session not found: {session_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return ChatSession.from_dict(data)

    def save(self, session: ChatSession) -> Path:
        path = self._path(session.session_id)
        path.write_text(json.dumps(session.to_dict(), ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        return path

    def _path(self, session_id: str) -> Path:
        if Path(session_id).name != session_id:
            raise ValueError("Invalid session id.")
        return self._root / f"{session_id}.json"
