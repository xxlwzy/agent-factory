import json
from pathlib import Path

from agent_factory.config.schema import (
    AgentConfig,
    AgentFactoryConfig,
    MetaConfig,
    PermissionsConfig,
    RuntimeConfig,
    SandboxConfig,
    ToolConfig,
)
from agent_factory.llm.fake import FakeLLMAdapter
from agent_factory.llm.messages import FinalResponse, ToolCallResponse
from agent_factory.runtime.runner import AgentRunner
from agent_factory.runtime.states import RunStatus
from agent_factory.runtime.trace import RunTrace


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


def test_runner_records_allowed_tool_call_and_continues(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    runner = AgentRunner(
        config=_config(tmp_path, sandbox_paths=(str(allowed),)),
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

    assert result.status == RunStatus.COMPLETED
    events = _trace_events(tmp_path / "run-1")
    assert [event["type"] for event in events] == [
        "run_started",
        "llm_response",
        "permission_decision",
        "tool_skipped",
        "llm_response",
        "run_completed",
    ]
    assert events[2]["data"]["action"] == "allow"
    assert not (allowed / "report.md").exists()


def test_runner_blocks_on_confirm_decision(tmp_path: Path) -> None:
    runner = AgentRunner(
        config=_config(tmp_path, http_domains=("api.example.com",)),
        llm=FakeLLMAdapter([ToolCallResponse(tool="http", operation="POST", target="https://api.example.com/items")]),
        trace=RunTrace(tmp_path / "run-1"),
        workspace_root=tmp_path,
    )

    result = runner.run(task="write via api")

    assert result.status == RunStatus.BLOCKED
    assert result.reason == "HTTP write operation requires confirmation."
    events = _trace_events(tmp_path / "run-1")
    assert [event["type"] for event in events[-2:]] == ["permission_decision", "run_blocked"]
    assert events[-1]["data"]["action"] == "confirm"


def test_runner_blocks_on_deny_decision(tmp_path: Path) -> None:
    runner = AgentRunner(
        config=_config(tmp_path, http_domains=("example.com",)),
        llm=FakeLLMAdapter([ToolCallResponse(tool="http", operation="GET", target="https://evil.test/items")]),
        trace=RunTrace(tmp_path / "run-1"),
        workspace_root=tmp_path,
    )

    result = runner.run(task="read api")

    assert result.status == RunStatus.BLOCKED
    assert result.reason == "HTTP target domain is outside allowlist."
    events = _trace_events(tmp_path / "run-1")
    assert [event["type"] for event in events[-2:]] == ["permission_decision", "run_blocked"]
    assert events[-1]["data"]["action"] == "deny"


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
) -> AgentFactoryConfig:
    return AgentFactoryConfig(
        meta=MetaConfig(name="test_agent"),
        agent=AgentConfig(role="tester", model="fake", system_prompt="test"),
        runtime=RuntimeConfig(max_turns=max_turns),
        tools={
            "filesystem": ToolConfig(enabled=True),
            "http": ToolConfig(enabled=True),
        },
        permissions=PermissionsConfig(
            sandbox=SandboxConfig(
                paths=sandbox_paths if sandbox_paths is not None else (str(tmp_path),),
                domains=http_domains,
            )
        ),
    )


def _trace_events(run_dir: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in (run_dir / "trace.jsonl").read_text(encoding="utf-8").splitlines()]
