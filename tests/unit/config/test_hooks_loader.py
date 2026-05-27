from pathlib import Path

from agent_factory.config.loader import load_agent_config


def test_loads_hooks_and_automation_sections(tmp_path: Path) -> None:
    config_path = tmp_path / "agent.yaml"
    config_path.write_text(
        """
meta:
  name: hooked
agent:
  role: tester
  model: fake
  system_prompt: test
tools:
  filesystem:
    enabled: true
permissions:
  sandbox:
    paths:
      - .
hooks:
  PreToolUse:
    - command: ["echo", "pre"]
automation:
  schedules:
    - name: tick
      interval_seconds: 30
      task: ping
mcp:
  tools:
    - name: search
      description: Search tool
""",
        encoding="utf-8",
    )

    config = load_agent_config(config_path)

    assert len(config.hooks.pre_tool_use) == 1
    assert config.hooks.pre_tool_use[0].command == ("echo", "pre")
    assert config.automation.schedules[0].name == "tick"
    assert config.mcp.tools[0].name == "search"
    assert config.unsupported_warnings == ()
