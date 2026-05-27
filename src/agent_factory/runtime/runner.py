from __future__ import annotations

from pathlib import Path

from agent_factory.config.schema import AgentFactoryConfig
from agent_factory.llm.base import LLMAdapter
from agent_factory.llm.messages import FinalResponse, LLMRequest, ToolCallResponse
from agent_factory.permissions.guard import PermissionGuard, ToolRequest
from agent_factory.runtime.states import RunResult, RunStatus
from agent_factory.runtime.trace import RunTrace


class AgentRunner:
    def __init__(
        self,
        config: AgentFactoryConfig,
        llm: LLMAdapter,
        trace: RunTrace,
        workspace_root: str | Path,
    ) -> None:
        self._config = config
        self._llm = llm
        self._trace = trace
        self._permission_guard = PermissionGuard(
            tools=config.tools,
            permissions=config.permissions,
            workspace_root=workspace_root,
        )

    def run(self, task: str) -> RunResult:
        self._trace.append("run_started", {"agent": self._config.meta.name, "task": task})
        messages: tuple[str, ...] = ()

        for turn in range(1, self._config.runtime.max_turns + 1):
            try:
                response = self._llm.next_response(LLMRequest(task=task, messages=messages))
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

            if decision.action != "allow":
                self._trace.append("run_blocked", decision_data)
                return RunResult(status=RunStatus.BLOCKED, reason=decision.reason)

            self._trace.append(
                "tool_skipped",
                {
                    "tool": response.tool,
                    "operation": response.operation,
                    "target": response.target,
                    "reason": "Tool execution is out of scope for Phase 1.",
                    "turn": turn,
                },
            )
            messages = messages + (f"{response.tool}.{response.operation}:{response.target}=skipped",)

        return self._fail("Max turns reached before final response.")

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
