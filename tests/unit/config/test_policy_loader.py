from pathlib import Path

import pytest

from agent_factory.config.loader import load_agent_config
from agent_factory.config.policy_loader import load_policy_permissions, merge_permissions
from agent_factory.config.schema import PermissionsConfig, SandboxConfig


def test_merge_permissions_unions_lists() -> None:
    base = PermissionsConfig(
        sandbox=SandboxConfig(paths=(".",), domains=("example.com",)),
        confirm=("browser.submit",),
        deny=("terminal.dangerous",),
    )
    overlay = PermissionsConfig(
        sandbox=SandboxConfig(paths=("./workspace",), domains=("api.example.com",)),
        confirm=("http.write",),
        deny=("custom.deny",),
    )

    merged = merge_permissions(base, overlay)

    assert merged.sandbox.paths == (".", "./workspace")
    assert merged.sandbox.domains == ("example.com", "api.example.com")
    assert merged.confirm == ("browser.submit", "http.write")
    assert merged.deny == ("terminal.dangerous", "custom.deny")


def test_load_policy_permissions_from_file(tmp_path: Path) -> None:
    policy_dir = tmp_path / "policies"
    policy_dir.mkdir()
    policy_path = policy_dir / "default.yaml"
    policy_path.write_text(
        """
permissions:
  confirm:
    - browser.submit
  deny:
    - terminal.dangerous
""",
        encoding="utf-8",
    )

    permissions = load_policy_permissions(policy_path)

    assert "browser.submit" in permissions.confirm
    assert "terminal.dangerous" in permissions.deny


def test_load_agent_config_merges_policy(tmp_path: Path) -> None:
    policies = tmp_path / "policies"
    policies.mkdir()
    (policies / "default.yaml").write_text(
        """
permissions:
  confirm:
    - browser.submit
  deny:
    - terminal.dangerous
""",
        encoding="utf-8",
    )
    agent_path = tmp_path / "agents" / "test.yaml"
    agent_path.parent.mkdir()
    agent_path.write_text(
        """
policy: default
meta:
  name: policy_agent
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
      - ./workspace
""",
        encoding="utf-8",
    )

    config = load_agent_config(agent_path)

    assert "browser.submit" in config.permissions.confirm
    assert "terminal.dangerous" in config.permissions.deny
    assert "./workspace" in config.permissions.sandbox.paths


def test_load_agent_config_fails_on_missing_policy(tmp_path: Path) -> None:
    agent_path = tmp_path / "agent.yaml"
    agent_path.write_text(
        """
policy: missing
meta:
  name: broken
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
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Policy file not found"):
        load_agent_config(agent_path)
