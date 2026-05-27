from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_factory.config.schema import PermissionsConfig, ToolConfig
from agent_factory.permissions.sandbox import is_domain_allowed, is_path_inside_any_sandbox


@dataclass(frozen=True)
class ToolRequest:
    tool: str
    operation: str
    target: str


@dataclass(frozen=True)
class PermissionDecision:
    action: str
    reason: str


class PermissionGuard:
    def __init__(
        self,
        tools: dict[str, ToolConfig],
        permissions: PermissionsConfig,
        workspace_root: str | Path,
    ) -> None:
        self._tools = tools
        self._permissions = permissions
        self._workspace_root = Path(workspace_root).resolve()

    def evaluate(self, request: ToolRequest) -> PermissionDecision:
        tool_config = self._tools.get(request.tool)
        if tool_config is None or not tool_config.enabled:
            return PermissionDecision("deny", f"Tool '{request.tool}' is not enabled.")

        if request.tool == "filesystem":
            sandbox_decision = self._evaluate_filesystem(request)
            if sandbox_decision.action != "allow":
                return sandbox_decision
            rule_decision = self._evaluate_explicit_rules(request)
            if rule_decision is not None:
                return rule_decision
            return sandbox_decision

        if request.tool == "http":
            sandbox_decision = self._evaluate_http_sandbox(request)
            if sandbox_decision.action != "allow":
                return sandbox_decision
            rule_decision = self._evaluate_explicit_rules(request)
            if rule_decision is not None:
                return rule_decision
            if request.operation.upper() != "GET":
                return PermissionDecision("confirm", "HTTP write operation requires confirmation.")
            return sandbox_decision

        rule_decision = self._evaluate_explicit_rules(request)
        if rule_decision is not None:
            return rule_decision
        return PermissionDecision("confirm", f"Tool '{request.tool}' requires confirmation in MVP.")

    def _evaluate_filesystem(self, request: ToolRequest) -> PermissionDecision:
        if is_path_inside_any_sandbox(
            request.target,
            self._permissions.sandbox.paths,
            self._workspace_root,
        ):
            return PermissionDecision("allow", "Filesystem target is inside sandbox.")
        return PermissionDecision("deny", "Filesystem target is outside sandbox.")

    def _evaluate_http_sandbox(self, request: ToolRequest) -> PermissionDecision:
        if not is_domain_allowed(request.target, self._permissions.sandbox.domains):
            return PermissionDecision(
                "confirm",
                "HTTP target domain is outside allowlist; confirm to allow this request.",
            )
        return PermissionDecision("allow", "HTTP GET target domain is allowed.")

    def _evaluate_explicit_rules(self, request: ToolRequest) -> PermissionDecision | None:
        rule = _rule_name(request)
        if rule in self._permissions.deny:
            return PermissionDecision("deny", f"Rule '{rule}' is explicitly denied.")
        if rule in self._permissions.confirm:
            return PermissionDecision("confirm", f"Rule '{rule}' requires confirmation.")
        return None


def _rule_name(request: ToolRequest) -> str:
    operation = request.operation.lower()
    if request.tool == "http":
        operation = "read" if operation == "get" else "write"
    return f"{request.tool}.{operation}"
