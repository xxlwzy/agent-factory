import json
from pathlib import Path

from agent_factory.config.schema import (
    AgentConfig,
    AgentFactoryConfig,
    HookEntry,
    HooksConfig,
    MetaConfig,
    McpConfig,
    McpToolDescriptor,
    PermissionsConfig,
    RuntimeConfig,
    SandboxConfig,
    SkillsConfig,
    ToolConfig,
)
from agent_factory.hooks.runner import HookRunner
from agent_factory.llm.fake import FakeLLMAdapter
from agent_factory.llm.messages import FinalResponse, ToolCallResponse
from agent_factory.runtime.runner import AgentRunner
from agent_factory.runtime.states import RunStatus
from agent_factory.runtime.trace import RunTrace
from agent_factory.tools.base import ToolResult
from agent_factory.tools.registry import build_default_registry


def test_runner_blocks_tool_when_pre_tool_hook_fails(tmp_path: Path) -> None:
    def failing_runner(command: tuple[str, ...], env: dict[str, str]):
        from agent_factory.hooks.runner import HookResult

        return HookResult(success=False, error="blocked by hook")

    hooks = HooksConfig(pre_tool_use=(HookEntry(command=("false",)),))
    hook_runner = HookRunner(hooks, workspace_root=tmp_path, command_runner=failing_runner)
    runner = AgentRunner(
        config=_config(tmp_path),
        llm=FakeLLMAdapter(
            [ToolCallResponse(tool="filesystem", operation="read", target=str(tmp_path / "x.txt"))]
        ),
        trace=RunTrace(tmp_path / "run-1"),
        workspace_root=tmp_path,
        hook_runner=hook_runner,
    )
    (tmp_path / "x.txt").write_text("hi", encoding="utf-8")

    result = runner.run(task="read file")

    assert result.status == RunStatus.BLOCKED
    assert "hook" in (result.reason or "").lower()
    events = _trace_events(tmp_path / "run-1")
    assert any(event["type"] == "hook_failed" for event in events)


def test_runner_executes_mcp_tool_after_approval(tmp_path: Path) -> None:
    config = _config(tmp_path, mcp_enabled=True)
    registry = build_default_registry(
        config,
        tmp_path,
        mcp_handlers={
            "search": lambda operation, target, content: ToolResult(success=True, output=f"result:{target}"),
        },
    )
    runner = AgentRunner(
        config=config,
        llm=FakeLLMAdapter(
            [
                ToolCallResponse(tool="mcp", operation="search", target="query"),
                FinalResponse(content="done"),
            ]
        ),
        trace=RunTrace(tmp_path / "run-1"),
        workspace_root=tmp_path,
        tool_registry=registry,
    )

    paused = runner.run(task="search")
    assert paused.status == RunStatus.AWAITING_CONFIRM
    result = runner.continue_from_approval(
        task="search",
        messages=(),
        pending_tool=paused.pending_tool,
        approved=True,
    )

    assert result.status == RunStatus.COMPLETED
    events = _trace_events(tmp_path / "run-1")
    executed = next(event for event in events if event["type"] == "tool_executed")
    assert executed["data"]["output"] == "result:query"


def test_runner_loads_skills_into_llm_request(tmp_path: Path) -> None:
    skills_root = tmp_path / "configs" / "skills" / "demo-skill"
    skills_root.mkdir(parents=True)
    (skills_root / "SKILL.md").write_text(
        "---\nname: demo-skill\ndescription: Demo skill body marker\n---\n\nAlways cite sources.\n",
        encoding="utf-8",
    )

    captured: list[str] = []

    class RecordingLLM(FakeLLMAdapter):
        def next_response(self, request):
            captured.append(request.skill_context)
            return super().next_response(request)

    runner = AgentRunner(
        config=_config(tmp_path, enabled_skills=("demo-skill", "missing")),
        llm=RecordingLLM([FinalResponse(content="done")]),
        trace=RunTrace(tmp_path / "run-1"),
        workspace_root=tmp_path,
    )

    result = runner.run(task="use skills")

    assert result.status == RunStatus.COMPLETED
    assert captured
    assert "Demo skill body marker" in captured[0]
    assert "Always cite sources" in captured[0]
    events = _trace_events(tmp_path / "run-1")
    assert any(event["type"] == "skills_loaded" for event in events)
    assert any(event["type"] == "skills_warning" for event in events)


def test_runner_completes_on_final_response(tmp_path: Path) -> None:
    runner = AgentRunner(
        config=_config(tmp_path),
        llm=FakeLLMAdapter([FinalResponse(content="done")]),
        trace=RunTrace(tmp_path / "run-1"),
        workspace_root=tmp_path,
    )

    result = runner.run(task="write a report")

    assert result.status == RunStatus.COMPLETED
    assert result.output == "done"
    events = _trace_events(tmp_path / "run-1")
    assert [event["type"] for event in events] == ["run_started", "llm_response", "run_completed"]


def test_runner_executes_allowed_filesystem_write_and_continues(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    report_path = allowed / "report.md"
    runner = AgentRunner(
        config=_config(tmp_path, sandbox_paths=(str(allowed),)),
        llm=FakeLLMAdapter(
            [
                ToolCallResponse(
                    tool="filesystem",
                    operation="write",
                    target=str(report_path),
                    content="# report",
                ),
                FinalResponse(content="done"),
            ]
        ),
        trace=RunTrace(tmp_path / "run-1"),
        workspace_root=tmp_path,
    )

    result = runner.run(task="write a report")

    assert result.status == RunStatus.COMPLETED
    events = _trace_events(tmp_path / "run-1")
    assert [event["type"] for event in events] == [
        "run_started",
        "llm_response",
        "permission_decision",
        "tool_executed",
        "llm_response",
        "run_completed",
    ]
    assert events[2]["data"]["action"] == "allow"
    assert events[3]["data"]["success"] is True
    assert report_path.read_text(encoding="utf-8") == "# report"


def test_runner_fails_when_tool_execution_fails(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    runner = AgentRunner(
        config=_config(tmp_path, sandbox_paths=(str(allowed),)),
        llm=FakeLLMAdapter(
            [ToolCallResponse(tool="filesystem", operation="read", target=str(allowed / "missing.md"))]
        ),
        trace=RunTrace(tmp_path / "run-1"),
        workspace_root=tmp_path,
    )

    result = runner.run(task="read report")

    assert result.status == RunStatus.FAILED
    assert "not found" in (result.reason or "").lower()
    events = _trace_events(tmp_path / "run-1")
    assert events[-2]["type"] == "tool_executed"
    assert events[-2]["data"]["success"] is False
    assert events[-1]["type"] == "run_failed"


def test_runner_awaits_confirm_on_confirm_decision(tmp_path: Path) -> None:
    runner = AgentRunner(
        config=_config(tmp_path, http_domains=("api.example.com",)),
        llm=FakeLLMAdapter([ToolCallResponse(tool="http", operation="POST", target="https://api.example.com/items")]),
        trace=RunTrace(tmp_path / "run-1"),
        workspace_root=tmp_path,
    )

    result = runner.run(task="write via api")

    assert result.status == RunStatus.AWAITING_CONFIRM
    assert result.reason == "HTTP write operation requires confirmation."
    assert result.pending_tool is not None
    events = _trace_events(tmp_path / "run-1")
    assert [event["type"] for event in events[-2:]] == ["permission_decision", "approval_requested"]
    assert events[-2]["data"]["action"] == "confirm"


def test_runner_awaits_confirm_for_domain_outside_allowlist(tmp_path: Path) -> None:
    runner = AgentRunner(
        config=_config(tmp_path, http_domains=("example.com",)),
        llm=FakeLLMAdapter([ToolCallResponse(tool="http", operation="GET", target="https://evil.test/items")]),
        trace=RunTrace(tmp_path / "run-1"),
        workspace_root=tmp_path,
    )

    result = runner.run(task="read api")

    assert result.status == RunStatus.AWAITING_CONFIRM
    assert "outside allowlist" in (result.reason or "")
    events = _trace_events(tmp_path / "run-1")
    assert [event["type"] for event in events[-2:]] == ["permission_decision", "approval_requested"]
    assert events[-2]["data"]["action"] == "confirm"


def test_runner_fails_when_adapter_is_exhausted(tmp_path: Path) -> None:
    runner = AgentRunner(
        config=_config(tmp_path),
        llm=FakeLLMAdapter([]),
        trace=RunTrace(tmp_path / "run-1"),
        workspace_root=tmp_path,
    )

    result = runner.run(task="write a report")

    assert result.status == RunStatus.FAILED
    assert result.reason == "FakeLLMAdapter has no scripted responses left."
    assert _trace_events(tmp_path / "run-1")[-1]["type"] == "run_failed"


def test_runner_executes_terminal_after_approval(tmp_path: Path) -> None:
    captured: list[str] = []

    def fake_runner(args: list[str], cwd: Path) -> ToolResult:
        captured.append(" ".join(args))
        return ToolResult(success=True, output="hello")

    registry = build_default_registry(
        _config(tmp_path, terminal_enabled=True),
        tmp_path,
        terminal_runner=fake_runner,
    )
    runner = AgentRunner(
        config=_config(tmp_path, terminal_enabled=True),
        llm=FakeLLMAdapter(
            [
                ToolCallResponse(tool="terminal", operation="run", target="echo hello"),
                FinalResponse(content="done"),
            ]
        ),
        trace=RunTrace(tmp_path / "run-1"),
        workspace_root=tmp_path,
        tool_registry=registry,
    )

    paused = runner.run(task="run echo")
    assert paused.status == RunStatus.AWAITING_CONFIRM
    assert paused.pending_tool is not None

    result = runner.continue_from_approval(
        task="run echo",
        messages=(),
        pending_tool=paused.pending_tool,
        approved=True,
    )

    assert result.status == RunStatus.COMPLETED
    assert captured == ["echo hello"]
    events = _trace_events(tmp_path / "run-1")
    assert "tool_executed" in [event["type"] for event in events]
    executed = next(event for event in events if event["type"] == "tool_executed")
    assert executed["data"]["tool"] == "terminal"
    assert executed["data"]["success"] is True


def test_runner_executes_browser_read(tmp_path: Path) -> None:
    registry = build_default_registry(
        _config(tmp_path, browser_enabled=True),
        tmp_path,
        browser_fetcher=lambda url: f"page:{url}",
    )
    runner = AgentRunner(
        config=_config(tmp_path, browser_enabled=True),
        llm=FakeLLMAdapter(
            [
                ToolCallResponse(tool="browser", operation="read", target="https://example.com"),
                FinalResponse(content="done"),
            ]
        ),
        trace=RunTrace(tmp_path / "run-1"),
        workspace_root=tmp_path,
        tool_registry=registry,
    )

    paused = runner.run(task="read page")

    assert paused.status == RunStatus.AWAITING_CONFIRM
    result = runner.continue_from_approval(
        task="read page",
        messages=(),
        pending_tool=paused.pending_tool,
        approved=True,
    )

    assert result.status == RunStatus.COMPLETED
    events = _trace_events(tmp_path / "run-1")
    executed = next(event for event in events if event["type"] == "tool_executed")
    assert executed["data"]["output"] == "page:https://example.com"


def test_runner_fails_when_max_turns_is_reached(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    runner = AgentRunner(
        config=_config(tmp_path, max_turns=1, sandbox_paths=(str(allowed),)),
        llm=FakeLLMAdapter(
            [
                ToolCallResponse(tool="filesystem", operation="write", target=str(allowed / "report.md")),
                FinalResponse(content="done"),
            ]
        ),
        trace=RunTrace(tmp_path / "run-1"),
        workspace_root=tmp_path,
    )

    result = runner.run(task="write a report")

    assert result.status == RunStatus.FAILED
    assert result.reason == "Max turns reached before final response."
    assert _trace_events(tmp_path / "run-1")[-1]["type"] == "run_failed"


def _config(
    tmp_path: Path,
    max_turns: int = 5,
    sandbox_paths: tuple[str, ...] | None = None,
    http_domains: tuple[str, ...] = (),
    *,
    terminal_enabled: bool = False,
    browser_enabled: bool = False,
    enabled_skills: tuple[str, ...] = (),
    mcp_enabled: bool = False,
) -> AgentFactoryConfig:
    tools: dict[str, ToolConfig] = {
        "filesystem": ToolConfig(enabled=True),
        "http": ToolConfig(enabled=True),
    }
    if terminal_enabled:
        tools["terminal"] = ToolConfig(enabled=True)
    if browser_enabled:
        tools["browser"] = ToolConfig(enabled=True)
    if mcp_enabled:
        tools["mcp"] = ToolConfig(enabled=True)
    return AgentFactoryConfig(
        meta=MetaConfig(name="test_agent"),
        agent=AgentConfig(role="tester", model="fake", system_prompt="test"),
        runtime=RuntimeConfig(max_turns=max_turns),
        tools=tools,
        permissions=PermissionsConfig(
            sandbox=SandboxConfig(
                paths=sandbox_paths if sandbox_paths is not None else (str(tmp_path),),
                domains=http_domains,
            )
        ),
        skills=SkillsConfig(enabled=enabled_skills),
        mcp=McpConfig(tools=(McpToolDescriptor(name="search", description="search"),)) if mcp_enabled else McpConfig(),
    )


def _trace_events(run_dir: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in (run_dir / "trace.jsonl").read_text(encoding="utf-8").splitlines()]
