from pathlib import Path

from agent_factory.config.schema import PermissionsConfig, SandboxConfig, ToolConfig
from agent_factory.permissions.guard import PermissionDecision, PermissionGuard, ToolRequest


def test_denies_disabled_tool(tmp_path: Path) -> None:
    guard = PermissionGuard(
        tools={"filesystem": ToolConfig(enabled=False)},
        permissions=PermissionsConfig(sandbox=SandboxConfig(paths=(str(tmp_path),))),
        workspace_root=tmp_path,
    )

    decision = guard.evaluate(ToolRequest(tool="filesystem", operation="read", target=str(tmp_path / "a.txt")))

    assert decision == PermissionDecision("deny", "Tool 'filesystem' is not enabled.")


def test_allows_filesystem_target_inside_sandbox(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    guard = PermissionGuard(
        tools={"filesystem": ToolConfig(enabled=True)},
        permissions=PermissionsConfig(sandbox=SandboxConfig(paths=(str(allowed),))),
        workspace_root=tmp_path,
    )

    decision = guard.evaluate(ToolRequest(tool="filesystem", operation="write", target=str(allowed / "report.md")))

    assert decision == PermissionDecision("allow", "Filesystem target is inside sandbox.")


def test_denies_filesystem_target_outside_sandbox(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    guard = PermissionGuard(
        tools={"filesystem": ToolConfig(enabled=True)},
        permissions=PermissionsConfig(sandbox=SandboxConfig(paths=(str(allowed),))),
        workspace_root=tmp_path,
    )

    decision = guard.evaluate(ToolRequest(tool="filesystem", operation="write", target=str(outside / "report.md")))

    assert decision == PermissionDecision("deny", "Filesystem target is outside sandbox.")


def test_confirms_http_write_to_allowed_domain(tmp_path: Path) -> None:
    guard = PermissionGuard(
        tools={"http": ToolConfig(enabled=True)},
        permissions=PermissionsConfig(sandbox=SandboxConfig(domains=("api.example.com",))),
        workspace_root=tmp_path,
    )

    decision = guard.evaluate(ToolRequest(tool="http", operation="POST", target="https://api.example.com/items"))

    assert decision == PermissionDecision("confirm", "HTTP write operation requires confirmation.")


def test_denies_http_domain_outside_allowlist(tmp_path: Path) -> None:
    guard = PermissionGuard(
        tools={"http": ToolConfig(enabled=True)},
        permissions=PermissionsConfig(sandbox=SandboxConfig(domains=("example.com",))),
        workspace_root=tmp_path,
    )

    decision = guard.evaluate(ToolRequest(tool="http", operation="GET", target="https://evil.test/data"))

    assert decision == PermissionDecision("deny", "HTTP target domain is outside allowlist.")


def test_explicit_deny_rule_takes_precedence(tmp_path: Path) -> None:
    guard = PermissionGuard(
        tools={"http": ToolConfig(enabled=True)},
        permissions=PermissionsConfig(
            sandbox=SandboxConfig(domains=("api.example.com",)),
            deny=("http.write",),
        ),
        workspace_root=tmp_path,
    )

    decision = guard.evaluate(ToolRequest(tool="http", operation="POST", target="https://api.example.com/items"))

    assert decision == PermissionDecision("deny", "Rule 'http.write' is explicitly denied.")


def test_explicit_confirm_rule_applies_after_sandbox_allows(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    guard = PermissionGuard(
        tools={"filesystem": ToolConfig(enabled=True)},
        permissions=PermissionsConfig(
            sandbox=SandboxConfig(paths=(str(allowed),)),
            confirm=("filesystem.write",),
        ),
        workspace_root=tmp_path,
    )

    decision = guard.evaluate(ToolRequest(tool="filesystem", operation="write", target=str(allowed / "report.md")))

    assert decision == PermissionDecision("confirm", "Rule 'filesystem.write' requires confirmation.")
