from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_factory.config.loader import load_agent_config

ROUTABLE_EXCLUDE = frozenset({"router", "general_assistant"})
FALLBACK_AGENT = "general_assistant"


@dataclass(frozen=True)
class AgentCatalogEntry:
    name: str
    role: str
    description: str
    path: Path


class AgentCatalog:
    def __init__(self, agents_dir: str | Path) -> None:
        self._agents_dir = Path(agents_dir).resolve()

    def list_routable(self) -> tuple[AgentCatalogEntry, ...]:
        entries: list[AgentCatalogEntry] = []
        if not self._agents_dir.is_dir():
            return ()
        for path in sorted(self._agents_dir.glob("*.yaml")):
            config = load_agent_config(path)
            if config.meta.name in ROUTABLE_EXCLUDE:
                continue
            entries.append(
                AgentCatalogEntry(
                    name=config.meta.name,
                    role=config.agent.role,
                    description=config.meta.description,
                    path=path.resolve(),
                )
            )
        return tuple(entries)

    def path_for(self, agent_name: str) -> Path:
        path = self._agents_dir / f"{agent_name}.yaml"
        if not path.is_file():
            direct = self._agents_dir / agent_name
            if direct.is_file():
                return direct.resolve()
            raise KeyError(f"Unknown agent: {agent_name}")
        return path.resolve()

    def format_for_router_prompt(self) -> str:
        lines = ["Available specialist agents:"]
        for entry in self.list_routable():
            lines.append(f"- {entry.name}: role={entry.role!r}; {entry.description}")
        lines.append(f"- {FALLBACK_AGENT}: use when no specialist fits (general atomic tools).")
        return "\n".join(lines)
