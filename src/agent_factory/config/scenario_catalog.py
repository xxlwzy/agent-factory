from __future__ import annotations

from pathlib import Path

from agent_factory.config.scenario_schema import ScenarioEntry, load_scenario_entry


class ScenarioCatalog:
    def __init__(self, scenarios_root: str | Path) -> None:
        self._root = Path(scenarios_root).resolve()

    @property
    def root(self) -> Path:
        return self._root

    def list_scenarios(self) -> tuple[ScenarioEntry, ...]:
        if not self._root.is_dir():
            return ()
        entries: list[ScenarioEntry] = []
        seen_ids: set[str] = set()
        for child in sorted(self._root.iterdir()):
            if not child.is_dir():
                continue
            if not (child / "scenario.yaml").is_file():
                continue
            entry = load_scenario_entry(child)
            if entry.scenario_id in seen_ids:
                raise ValueError(f"Duplicate scenario_id '{entry.scenario_id}' under {self._root}")
            seen_ids.add(entry.scenario_id)
            entries.append(entry)
        return tuple(entries)

    def get(self, scenario_id: str) -> ScenarioEntry:
        for entry in self.list_scenarios():
            if entry.scenario_id == scenario_id:
                return entry
        raise KeyError(f"Unknown scenario_id: {scenario_id}")

    def format_for_router_prompt(self) -> str:
        lines = ["Available business scenarios (agent teams):"]
        for entry in self.list_scenarios():
            member_ids = ", ".join(member.member_id for member in entry.members)
            lines.append(
                f"- {entry.scenario_id} ({entry.display_name}): {entry.description}; members=[{member_ids}]"
            )
        return "\n".join(lines)
