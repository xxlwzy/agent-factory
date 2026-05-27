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


def test_runner_awaits_confirm_for_http_write(tmp_path: Path) -> None:
    runner = AgentRunner(
        config=_config_with_http_confirm(),
        llm=FakeLLMAdapter(
            [ToolCallResponse(tool="http", operation="POST", target="https://api.example.com/items")]
        ),
        trace=RunTrace(tmp_path / "run-1"),
        workspace_root=tmp_path,
    )

    result = runner.run("post data")

    assert result.status == RunStatus.AWAITING_CONFIRM
    assert result.pending_tool is not None
    assert result.pending_tool.operation == "POST"


def test_runner_continue_after_approval_executes_tool(tmp_path: Path) -> None:
    allowed = tmp_path / "out"
    allowed.mkdir()
    target = str(allowed / "data.txt")
    pending = ToolCallResponse(tool="filesystem", operation="write", target=target, content="hi")
    runner = AgentRunner(
        config=_config_filesystem_only(tmp_path),
        llm=FakeLLMAdapter([FinalResponse(content="written")]),
        trace=RunTrace(tmp_path / "run-2"),
        workspace_root=tmp_path,
    )

    result = runner.continue_from_approval("write file", (), pending, approved=True)

    assert result.status == RunStatus.COMPLETED
    assert (allowed / "data.txt").read_text(encoding="utf-8") == "hi"


def _config_with_http_confirm() -> AgentFactoryConfig:
    return AgentFactoryConfig(
        meta=MetaConfig(name="demo"),
        agent=AgentConfig(role="demo", model="fake", system_prompt="test"),
        runtime=RuntimeConfig(max_turns=3),
        tools={"http": ToolConfig(enabled=True)},
        permissions=PermissionsConfig(
            sandbox=SandboxConfig(domains=("api.example.com",)),
            confirm=("http.write",),
        ),
    )


def _config_filesystem_only(tmp_path: Path) -> AgentFactoryConfig:
    return AgentFactoryConfig(
        meta=MetaConfig(name="demo"),
        agent=AgentConfig(role="demo", model="fake", system_prompt="test"),
        runtime=RuntimeConfig(max_turns=3),
        tools={"filesystem": ToolConfig(enabled=True)},
        permissions=PermissionsConfig(sandbox=SandboxConfig(paths=(str(tmp_path),))),
    )
