from __future__ import annotations

from pathlib import Path

from agent_factory.config.schema import AgentFactoryConfig
from agent_factory.llm.base import LLMAdapter
from agent_factory.llm.messages import ChatTurn, FinalResponse, LLMRequest, ToolCallResponse
from agent_factory.permissions.guard import PermissionGuard, ToolRequest
from agent_factory.runtime.states import RunResult, RunStatus
from agent_factory.runtime.trace import RunTrace
from agent_factory.skills.loader import load_skills_for_config
from agent_factory.tools.registry import ToolRegistry, build_default_registry


class AgentRunner:
    def __init__(
        self,
        config: AgentFactoryConfig,
        llm: LLMAdapter,
        trace: RunTrace,
        workspace_root: str | Path,
        tool_registry: ToolRegistry | None = None,
    ) -> None:
        self._config = config
        self._llm = llm
        self._trace = trace
        self._workspace_root = Path(workspace_root).resolve()
        self._permission_guard = PermissionGuard(
            tools=config.tools,
            permissions=config.permissions,
            workspace_root=self._workspace_root,
        )
        self._tool_registry = tool_registry or build_default_registry(
            config,
            self._workspace_root,
        )

    def run(self, task: str, *, history: tuple[ChatTurn, ...] = ()) -> RunResult:
        self._trace.append("run_started", {"agent": self._config.meta.name, "task": task})
        skill_context = self._resolve_skill_context(trace=True)
        messages: tuple[str, ...] = ()

        for turn in range(1, self._config.runtime.max_turns + 1):
            try:
                response = self._llm.next_response(
                    LLMRequest(
                        task=task,
                        messages=messages,
                        history=history,
                        skill_context=skill_context,
                    )
                )
            except RuntimeError as error:
                return self._fail(str(error))

            self._trace.append("llm_response", _response_trace_data(response, turn))

            if isinstance(response, FinalResponse):
                self._trace.append("run_completed", {"output": response.content, "turn": turn})
                return RunResult(status=RunStatus.COMPLETED, output=response.content)

            decision = self._permission_guard.evaluate(
                ToolRequest(tool=response.tool, operation=response.operation, target=response.target)
            )
            decision_data = {
                "tool": response.tool,
                "operation": response.operation,
                "target": response.target,
                "action": decision.action,
                "reason": decision.reason,
                "turn": turn,
            }
            self._trace.append("permission_decision", decision_data)

            if decision.action == "confirm":
                self._trace.append("approval_requested", decision_data)
                return RunResult(
                    status=RunStatus.AWAITING_CONFIRM,
                    reason=decision.reason,
                    pending_tool=response,
                    tool_messages=messages,
                    paused_turn=turn,
                )

            if decision.action != "allow":
                self._trace.append("run_blocked", decision_data)
                return RunResult(status=RunStatus.BLOCKED, reason=decision.reason)

            tool_result = self._tool_registry.execute(
                response.tool,
                response.operation,
                response.target,
                content=response.content,
            )
            self._trace.append(
                "tool_executed",
                {
                    "tool": response.tool,
                    "operation": response.operation,
                    "target": response.target,
                    "success": tool_result.success,
                    "output": tool_result.output,
                    "error": tool_result.error,
                    "turn": turn,
                },
            )
            if not tool_result.success:
                return self._fail(tool_result.error or "Tool execution failed.")
            messages = messages + (
                f"{response.tool}.{response.operation}:{response.target}={tool_result.output}",
            )

        return self._fail("Max turns reached before final response.")

    def continue_from_approval(
        self,
        task: str,
        messages: tuple[str, ...],
        pending_tool: ToolCallResponse,
        *,
        approved: bool,
    ) -> RunResult:
        if not approved:
            self._trace.append("approval_denied", {"tool": pending_tool.tool, "target": pending_tool.target})
            return RunResult(status=RunStatus.BLOCKED, reason="User denied the tool action.")

        tool_result = self._tool_registry.execute(
            pending_tool.tool,
            pending_tool.operation,
            pending_tool.target,
            content=pending_tool.content,
        )
        self._trace.append(
            "approval_granted",
            {
                "tool": pending_tool.tool,
                "operation": pending_tool.operation,
                "target": pending_tool.target,
            },
        )
        self._trace.append(
            "tool_executed",
            {
                "tool": pending_tool.tool,
                "operation": pending_tool.operation,
                "target": pending_tool.target,
                "success": tool_result.success,
                "output": tool_result.output,
                "error": tool_result.error,
                "turn": 0,
            },
        )
        if not tool_result.success:
            return self._fail(tool_result.error or "Tool execution failed after approval.")

        messages = messages + (
            f"{pending_tool.tool}.{pending_tool.operation}:{pending_tool.target}={tool_result.output}",
        )
        skill_context = self._resolve_skill_context(trace=False)
        start_turn = 1
        for turn in range(start_turn, self._config.runtime.max_turns + 1):
            try:
                response = self._llm.next_response(
                    LLMRequest(task=task, messages=messages, history=(), skill_context=skill_context)
                )
            except RuntimeError as error:
                return self._fail(str(error))

            self._trace.append("llm_response", _response_trace_data(response, turn))

            if isinstance(response, FinalResponse):
                self._trace.append("run_completed", {"output": response.content, "turn": turn})
                return RunResult(status=RunStatus.COMPLETED, output=response.content)

            decision = self._permission_guard.evaluate(
                ToolRequest(tool=response.tool, operation=response.operation, target=response.target)
            )
            decision_data = {
                "tool": response.tool,
                "operation": response.operation,
                "target": response.target,
                "action": decision.action,
                "reason": decision.reason,
                "turn": turn,
            }
            self._trace.append("permission_decision", decision_data)

            if decision.action == "confirm":
                self._trace.append("approval_requested", decision_data)
                return RunResult(
                    status=RunStatus.AWAITING_CONFIRM,
                    reason=decision.reason,
                    pending_tool=response,
                    tool_messages=messages,
                    paused_turn=turn,
                )

            if decision.action != "allow":
                self._trace.append("run_blocked", decision_data)
                return RunResult(status=RunStatus.BLOCKED, reason=decision.reason)

            tool_result = self._tool_registry.execute(
                response.tool,
                response.operation,
                response.target,
                content=response.content,
            )
            self._trace.append(
                "tool_executed",
                {
                    "tool": response.tool,
                    "operation": response.operation,
                    "target": response.target,
                    "success": tool_result.success,
                    "output": tool_result.output,
                    "error": tool_result.error,
                    "turn": turn,
                },
            )
            if not tool_result.success:
                return self._fail(tool_result.error or "Tool execution failed.")
            messages = messages + (
                f"{response.tool}.{response.operation}:{response.target}={tool_result.output}",
            )

        return self._fail("Max turns reached before final response.")

    def _resolve_skill_context(self, *, trace: bool) -> str:
        result = load_skills_for_config(self._config, self._workspace_root)
        if trace:
            if result.warnings:
                self._trace.append("skills_warning", {"warnings": list(result.warnings)})
            if result.skills or self._config.skills.enabled:
                self._trace.append(
                    "skills_loaded",
                    {
                        "skills": [skill.name for skill in result.skills],
                        "enabled": list(self._config.skills.enabled),
                    },
                )
        return result.skill_context

    def _fail(self, reason: str) -> RunResult:
        self._trace.append("run_failed", {"reason": reason})
        return RunResult(status=RunStatus.FAILED, reason=reason)


def _response_trace_data(response: ToolCallResponse | FinalResponse, turn: int) -> dict[str, object]:
    if isinstance(response, FinalResponse):
        return {"kind": "final", "content": response.content, "turn": turn}
    return {
        "kind": "tool_call",
        "tool": response.tool,
        "operation": response.operation,
        "target": response.target,
        "turn": turn,
    }
