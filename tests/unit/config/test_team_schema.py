from pathlib import Path

import pytest

from agent_factory.config.team_schema import load_team_config, resolve_member_agent_path


def test_load_team_config_parses_members_and_pipeline(tmp_path: Path) -> None:
    team_path = tmp_path / "team.yaml"
    agents = tmp_path / "agents"
    agents.mkdir()
    (agents / "a.yaml").write_text("meta:\n  name: a\n", encoding="utf-8")
    team_path.write_text(
        """
meta:
  name: demo_team
team:
  members:
    - id: researcher
      agent: a.yaml
    - id: writer
      agent: a.yaml
  pipeline:
    - member: researcher
      task: "{team_task}"
    - member: writer
      task: "Report:\\n{last_output}"
""",
        encoding="utf-8",
    )

    team = load_team_config(team_path)

    assert team.name == "demo_team"
    assert len(team.members) == 2
    assert team.pipeline[1].member_id == "writer"
    resolved = resolve_member_agent_path(team_path, "a.yaml", agents)
    assert resolved.is_file()


def test_load_team_config_rejects_unknown_pipeline_member(tmp_path: Path) -> None:
    team_path = tmp_path / "team.yaml"
    team_path.write_text(
        """
team:
  members:
    - id: only
      agent: x.yaml
  pipeline:
    - member: missing
      task: hi
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unknown member"):
        load_team_config(team_path)
