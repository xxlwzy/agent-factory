from pathlib import Path

import pytest

from agent_factory.config.loader import load_agent_config


def test_loads_executable_agent_fields(tmp_path: Path) -> None:
    config_path = tmp_path / "agent.yaml"
    config_path.write_text(
        """
meta:
  name: web_researcher
  version: "0.1"
agent:
  role: Web research assistant
  model: fake-model
  system_prompt: Summarize web pages into Markdown.
runtime:
  max_turns: 12
  working_dir: ./workspace
  output_dir: ./outputs
tools:
  filesystem:
    enabled: true
  browser:
    enabled: true
permissions:
  sandbox:
    paths:
      - ./workspace
      - ./outputs
    domains:
      - example.com
""",
        encoding="utf-8",
    )

    config = load_agent_config(config_path)

    assert config.meta.name == "web_researcher"
    assert config.agent.role == "Web research assistant"
    assert config.runtime.max_turns == 12
    assert config.tools["filesystem"].enabled is True
    assert config.permissions.sandbox.paths == ("./workspace", "./outputs")
    assert config.unsupported_warnings == ()


def test_records_unsupported_top_level_sections(tmp_path: Path) -> None:
    config_path = tmp_path / "agent.yaml"
    config_path.write_text(
        """
meta:
  name: web_researcher
agent:
  role: Web research assistant
  model: fake-model
  system_prompt: Summarize web pages into Markdown.
tools:
  filesystem:
    enabled: true
permissions:
  sandbox:
    paths:
      - ./workspace
workflow:
  steps:
    - read_web
team:
  agents:
    - reviewer
""",
        encoding="utf-8",
    )

    config = load_agent_config(config_path)

    assert config.unsupported_warnings == (
        "Top-level section 'workflow' is recognized but mocked in MVP.",
        "Top-level section 'team' is recognized but mocked in MVP.",
    )


def test_missing_required_agent_section_fails(tmp_path: Path) -> None:
    config_path = tmp_path / "agent.yaml"
    config_path.write_text(
        """
meta:
  name: broken
tools:
  filesystem:
    enabled: true
permissions:
  sandbox:
    paths:
      - ./workspace
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Missing required section: agent"):
        load_agent_config(config_path)


def test_loads_memory_and_skill_config_without_warning(tmp_path: Path) -> None:
    config_path = tmp_path / "agent.yaml"
    config_path.write_text(
        """
meta:
  name: web_researcher
agent:
  role: Web research assistant
  model: fake-model
  system_prompt: Summarize web pages into Markdown.
tools:
  filesystem:
    enabled: true
permissions:
  sandbox:
    paths:
      - ./workspace
memory:
  session_path: .agent-factory/memory/session
  project_path: .agent-factory/memory/project
  user_path: .agent-factory/memory/user
skills:
  enabled:
    - web_research_summary
  draft_output_dir: .agent-factory/skills/drafts
""",
        encoding="utf-8",
    )

    config = load_agent_config(config_path)

    assert config.memory.session_path == ".agent-factory/memory/session"
    assert config.memory.project_path == ".agent-factory/memory/project"
    assert config.memory.user_path == ".agent-factory/memory/user"
    assert config.skills.enabled == ("web_research_summary",)
    assert config.skills.draft_output_dir == ".agent-factory/skills/drafts"
    assert config.unsupported_warnings == ()


def test_records_unknown_top_level_section_warning(tmp_path: Path) -> None:
    config_path = tmp_path / "agent.yaml"
    config_path.write_text(
        """
meta:
  name: web_researcher
agent:
  role: Web research assistant
  model: fake-model
  system_prompt: Summarize web pages into Markdown.
tools:
  filesystem:
    enabled: true
permissions:
  sandbox:
    paths:
      - ./workspace
mystery:
  enabled: true
""",
        encoding="utf-8",
    )

    config = load_agent_config(config_path)

    assert config.unsupported_warnings == ("Top-level section 'mystery' is not recognized by schema v1.",)
