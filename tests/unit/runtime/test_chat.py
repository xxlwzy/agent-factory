from pathlib import Path

from agent_factory.config.catalog import FALLBACK_AGENT
from agent_factory.llm.fake import FakeLLMAdapter
from agent_factory.llm.messages import FinalResponse
from agent_factory.routing.resolver import RuleBasedRoutingResolver
from agent_factory.runtime.chat import run_chat
from agent_factory.runtime.states import RunStatus


def test_run_chat_returns_reply_from_specialist(tmp_path: Path) -> None:
    agents_dir = _agents_dir(tmp_path)
    result = run_chat(
        "你好",
        workspace_root=tmp_path,
        agents_dir=agents_dir,
        routing_resolver=RuleBasedRoutingResolver(),
        specialist_llm=FakeLLMAdapter([FinalResponse(content="这是给用户的回复。")]),
    )

    assert result.status == RunStatus.COMPLETED
    assert result.reply == "这是给用户的回复。"
    assert result.routed_agent == FALLBACK_AGENT
    assert (tmp_path / ".agent-factory" / "runs" / result.run_id / "summary.md").is_file()


def test_run_chat_routes_web_research_message(tmp_path: Path) -> None:
    agents_dir = _agents_dir(tmp_path)
    result = run_chat(
        "research https://example.com",
        workspace_root=tmp_path,
        agents_dir=agents_dir,
        routing_resolver=RuleBasedRoutingResolver(),
        specialist_llm=FakeLLMAdapter([FinalResponse(content="report done")]),
    )

    assert result.routed_agent == "web_researcher"
    assert result.reply == "report done"


def _agents_dir(tmp_path: Path) -> Path:
    agents_dir = tmp_path / "configs" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "web_researcher.yaml").write_text(
        "meta:\n  name: web_researcher\n  description: Web research\n"
        "agent:\n  role: Web\n  model: fake\n  system_prompt: test\n"
        "tools:\n  http:\n    enabled: true\npermissions:\n  sandbox:\n    paths: [.]\n    domains: [example.com]\n",
        encoding="utf-8",
    )
    (agents_dir / "general_assistant.yaml").write_text(
        "meta:\n  name: general_assistant\n  description: General\n"
        "agent:\n  role: General\n  model: fake\n  system_prompt: test\n"
        "tools:\n  filesystem:\n    enabled: true\n  http:\n    enabled: true\n"
        "permissions:\n  sandbox:\n    paths: [.]\n    domains: [example.com]\n",
        encoding="utf-8",
    )
    return agents_dir
