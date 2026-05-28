from pathlib import Path

from agent_factory.config.role_templates import AgentRole, apply_role_tool_template, merge_scenario_member_tools
from agent_factory.config.schema import ToolConfig
from agent_factory.config.tool_merge import load_tools_yaml, merge_tool_configs


def test_merge_tool_configs_later_layer_wins(tmp_path: Path) -> None:
    common = {"filesystem": ToolConfig(enabled=False), "http": ToolConfig(enabled=False)}
    member = {"filesystem": ToolConfig(enabled=True)}

    merged = merge_tool_configs(common, member)

    assert merged["filesystem"].enabled is True
    assert merged["http"].enabled is False


def test_load_common_tools_yaml() -> None:
    repo = Path(__file__).resolve().parents[3]
    tools = load_tools_yaml(repo / "configs" / "tools" / "common.yaml")

    assert "filesystem" in tools
    assert tools["team"].enabled is False


def test_orchestrator_role_disables_side_effect_tools() -> None:
    member_tools = {
        "filesystem": ToolConfig(enabled=True),
        "terminal": ToolConfig(enabled=True),
        "team": ToolConfig(enabled=True),
    }

    result = apply_role_tool_template(member_tools, AgentRole.ORCHESTRATOR)

    assert result["team"].enabled is True
    assert result["filesystem"].enabled is False
    assert result["terminal"].enabled is False


def test_merge_scenario_member_tools_applies_role() -> None:
    common = {"team": ToolConfig(enabled=False), "filesystem": ToolConfig(enabled=False)}
    scenario = {"research.fetch": ToolConfig(enabled=True)}
    member = {"filesystem": ToolConfig(enabled=True), "team": ToolConfig(enabled=True)}

    orchestrator = merge_scenario_member_tools(
        common=common,
        scenario=scenario,
        member=member,
        role=AgentRole.ORCHESTRATOR,
    )
    teammate = merge_scenario_member_tools(
        common=common,
        scenario=scenario,
        member=member,
        role=AgentRole.TEAMMATE,
    )

    assert orchestrator["filesystem"].enabled is False
    assert orchestrator["team"].enabled is True
    assert teammate["filesystem"].enabled is True
    assert teammate["research.fetch"].enabled is True
