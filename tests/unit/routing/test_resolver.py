from pathlib import Path

from agent_factory.config.catalog import AgentCatalog, FALLBACK_AGENT
from agent_factory.routing.resolver import RuleBasedRoutingResolver


def test_rule_router_selects_web_researcher(tmp_path: Path) -> None:
    agents_dir = _agents_dir(tmp_path)
    catalog = AgentCatalog(agents_dir)
    resolver = RuleBasedRoutingResolver()

    decision = resolver.resolve("请总结 https://example.com 的内容", catalog)

    assert decision.target_agent == "web_researcher"
    assert "research" in decision.reason.lower() or "keyword" in decision.reason.lower()


def test_rule_router_falls_back_to_general(tmp_path: Path) -> None:
    agents_dir = _agents_dir(tmp_path)
    catalog = AgentCatalog(agents_dir)
    resolver = RuleBasedRoutingResolver()

    decision = resolver.resolve("你好，今天天气怎么样？", catalog)

    assert decision.target_agent == FALLBACK_AGENT


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
