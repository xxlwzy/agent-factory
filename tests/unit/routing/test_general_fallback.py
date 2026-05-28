from pathlib import Path

from agent_factory.config.catalog import FALLBACK_AGENT, AgentCatalog
from agent_factory.config.loader import load_agent_config
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
from agent_factory.routing.resolver import RuleBasedRoutingResolver
from agent_factory.runtime.runner import AgentRunner
from agent_factory.runtime.states import RunStatus
from agent_factory.runtime.trace import RunTrace


def test_rule_router_marks_fallback_decision_kind(tmp_path: Path) -> None:
    catalog = AgentCatalog(_agents_dir(tmp_path))
    decision = RuleBasedRoutingResolver().resolve("你好", catalog)

    assert decision.target_agent == FALLBACK_AGENT
    assert decision.decision_kind == "fallback"


def test_general_assistant_declines_out_of_scope_without_tools(tmp_path: Path) -> None:
    config = load_agent_config(
        Path(__file__).resolve().parents[3] / "configs" / "agents" / "general_assistant.yaml"
    )
    runner = AgentRunner(
        config=config,
        llm=FakeLLMAdapter(
            [
                FinalResponse(
                    content="我无法完成这个任务：需要访问未授权域或当前未启用的能力，抱歉做不到。"
                )
            ]
        ),
        trace=RunTrace(tmp_path / "run-1"),
        workspace_root=tmp_path,
    )

    result = runner.run(task="请帮我部署生产集群并修改 DNS")

    assert result.status == RunStatus.COMPLETED
    assert "做不到" in result.output or "无法" in result.output
    events = [line for line in (tmp_path / "run-1" / "trace.jsonl").read_text(encoding="utf-8").splitlines() if line]
    assert "tool_executed" not in "".join(events)


def test_general_assistant_scripted_tool_call_still_works(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    target = allowed / "note.txt"
    config = AgentFactoryConfig(
        meta=MetaConfig(name="general_assistant"),
        agent=AgentConfig(role="assistant", model="fake", system_prompt="test"),
        runtime=RuntimeConfig(),
        tools={"filesystem": ToolConfig(enabled=True), "http": ToolConfig(enabled=True)},
        permissions=PermissionsConfig(sandbox=SandboxConfig(paths=(str(allowed),))),
    )
    runner = AgentRunner(
        config=config,
        llm=FakeLLMAdapter(
            [
                ToolCallResponse(
                    tool="filesystem",
                    operation="write",
                    target=str(target),
                    content="hi",
                ),
                FinalResponse(content="done"),
            ]
        ),
        trace=RunTrace(tmp_path / "run-1"),
        workspace_root=tmp_path,
    )

    result = runner.run(task="write a note")

    assert result.status == RunStatus.COMPLETED


def _agents_dir(tmp_path: Path) -> Path:
    agents_dir = tmp_path / "configs" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "web_researcher.yaml").write_text(
        "meta:\n  name: web_researcher\n  description: Web research\n"
        "agent:\n  role: Web\n  model: fake\n  system_prompt: test\n"
        "tools:\n  http:\n    enabled: true\npermissions:\n  sandbox:\n    paths: [.]\n    domains: [example.com]\n",
        encoding="utf-8",
    )
    return agents_dir
