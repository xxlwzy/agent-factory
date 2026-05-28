from pathlib import Path

import pytest

from agent_factory.config.scenario_catalog import ScenarioCatalog
from agent_factory.config.scenario_schema import load_scenario_entry


def test_load_scenario_entry_from_directory(tmp_path: Path) -> None:
    root = tmp_path / "research-report"
    members = root / "members"
    members.mkdir(parents=True)
    (root / "scenario.yaml").write_text(
        """
id: research-report
display_name: 研究报告
description: Research and write reports
entry: orchestrator.yaml
single_agent_fallback: web_researcher.yaml
""",
        encoding="utf-8",
    )
    (root / "orchestrator.yaml").write_text("meta:\n  name: orch\n", encoding="utf-8")
    (members / "researcher.yaml").write_text("meta:\n  name: researcher\n", encoding="utf-8")

    entry = load_scenario_entry(root)

    assert entry.scenario_id == "research-report"
    assert entry.display_name == "研究报告"
    assert entry.single_agent_fallback == "web_researcher.yaml"
    assert len(entry.members) == 1
    assert entry.members[0].member_id == "researcher"


def test_scenario_catalog_lists_and_rejects_duplicate_ids(tmp_path: Path) -> None:
    scenarios_root = tmp_path / "scenarios"

    for name in ("a", "b"):
        root = scenarios_root / name
        (root / "members").mkdir(parents=True)
        (root / "scenario.yaml").write_text(
            f"id: dup\ndisplay_name: {name}\nentry: orchestrator.yaml\n",
            encoding="utf-8",
        )
        (root / "orchestrator.yaml").write_text("meta:\n  name: o\n", encoding="utf-8")

    catalog = ScenarioCatalog(scenarios_root)
    with pytest.raises(ValueError, match="Duplicate scenario_id"):
        catalog.list_scenarios()


def test_scenario_catalog_get_by_id(tmp_path: Path) -> None:
    root = tmp_path / "scenarios" / "demo"
    (root / "members").mkdir(parents=True)
    (root / "scenario.yaml").write_text(
        "id: demo\ndisplay_name: Demo\nentry: orchestrator.yaml\n",
        encoding="utf-8",
    )
    (root / "orchestrator.yaml").write_text("meta:\n  name: o\n", encoding="utf-8")

    catalog = ScenarioCatalog(tmp_path / "scenarios")
    entry = catalog.get("demo")

    assert entry.display_name == "Demo"


def test_repo_research_report_scenario_loads() -> None:
    repo = Path(__file__).resolve().parents[3]
    catalog = ScenarioCatalog(repo / "configs" / "scenarios")
    entry = catalog.get("research-report")

    assert entry.display_name == "研究报告"
    assert entry.orchestrator_path.is_file()
    assert {member.member_id for member in entry.members} == {"researcher", "writer"}
