from __future__ import annotations

from pathlib import Path

from agent_factory.config.schema import AgentFactoryConfig
from agent_factory.hooks.runner import HookRunner
from agent_factory.llm.base import LLMAdapter
from agent_factory.llm.messages import ChatTurn, FinalResponse, LLMRequest, ToolCallResponse
from agent_factory.permissions.guard import PermissionGuard, ToolRequest
from agent_factory.runtime.states import RunResult, RunStatus
from agent_factory.runtime.trace import RunTrace
from agent_factory.skills.loader import load_skills_for_config
from agent_factory.tools.base import ToolResult
from agent_factory.tools.registry import ToolRegistry, build_default_registry


class AgentRunner:
    def __init__(
        self,
        config: AgentFactoryConfig,
        llm: LLMAdapter,
        trace: RunTrace,
        workspace_root: str | Path,
        tool_registry: ToolRegistry | None = None,
        hook_runner: HookRunner | None = None,
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
        self._hook_runner = hook_runner or HookRunner(config.hooks, workspace_root=self._workspace_root)

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
                return self._complete_run(task=task, output=response.content, turn=turn)

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

            tool_outcome = self._execute_tool_with_hooks(response, turn=turn)
            if isinstance(tool_outcome, RunResult):
                return tool_outcome
            messages = messages + (
                f"{response.tool}.{response.operation}:{response.target}={tool_outcome.output}",
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

        self._trace.append(
            "approval_granted",
            {
                "tool": pending_tool.tool,
                "operation": pending_tool.operation,
                "target": pending_tool.target,
            },
        )
        tool_outcome = self._execute_tool_with_hooks(pending_tool, turn=0)
        if isinstance(tool_outcome, RunResult):
            return tool_outcome

        messages = messages + (
            f"{pending_tool.tool}.{pending_tool.operation}:{pending_tool.target}={tool_outcome.output}",
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
                return self._complete_run(task=task, output=response.content, turn=turn)

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

            tool_outcome = self._execute_tool_with_hooks(response, turn=turn)
            if isinstance(tool_outcome, RunResult):
                return tool_outcome
            messages = messages + (
                f"{response.tool}.{response.operation}:{response.target}={tool_outcome.output}",
            )

        return self._fail("Max turns reached before final response.")

    def _execute_tool_with_hooks(
        self,
        response: ToolCallResponse,
        *,
        turn: int,
    ) -> ToolResult | RunResult:
        if self._hook_runner.has_hooks():
            pre = self._hook_runner.run_pre_tool_use(
                tool=response.tool,
                operation=response.operation,
                target=response.target,
                run_id=self._run_id(),
            )
            if not pre.success:
                return self._hook_failed("PreToolUse", pre.error or "PreToolUse hook failed.", turn=turn)

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

        if self._hook_runner.has_hooks():
            post = self._hook_runner.run_post_tool_use(
                tool=response.tool,
                operation=response.operation,
                target=response.target,
                run_id=self._run_id(),
            )
            if not post.success:
                return self._hook_failed("PostToolUse", post.error or "PostToolUse hook failed.", turn=turn)

        return tool_result

    def _complete_run(self, *, task: str, output: str, turn: int) -> RunResult:
        if self._hook_runner.has_hooks():
            completed = self._hook_runner.run_run_completed(
                task=task,
                output=output,
                run_id=self._run_id(),
            )
            if not completed.success:
                return self._hook_failed(
                    "RunCompleted",
                    completed.error or "RunCompleted hook failed.",
                    turn=turn,
                )
        self._trace.append("run_completed", {"output": output, "turn": turn})
        return RunResult(status=RunStatus.COMPLETED, output=output)

    def _hook_failed(self, event: str, reason: str, *, turn: int) -> RunResult:
        self._trace.append("hook_failed", {"event": event, "reason": reason, "turn": turn})
        return RunResult(status=RunStatus.BLOCKED, reason=reason)

    def _run_id(self) -> str:
        return self._trace.run_dir.name

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
