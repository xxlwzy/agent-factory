from pathlib import Path

from agent_factory.config.catalog import AgentCatalog, ROUTABLE_EXCLUDE


def test_catalog_lists_specialists_excludes_router(tmp_path: Path) -> None:
    agents_dir = tmp_path / "configs" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "web_researcher.yaml").write_text(
        "meta:\n  name: web_researcher\n  description: Web research\n"
        "agent:\n  role: Web\n  model: fake\n  system_prompt: test\n"
        "tools:\n  http:\n    enabled: true\npermissions:\n  sandbox:\n    paths: [.]\n",
        encoding="utf-8",
    )
    (agents_dir / "router.yaml").write_text(
        "meta:\n  name: router\nagent:\n  role: R\n  model: fake\n  system_prompt: x\n"
        "tools:\n  http:\n    enabled: false\npermissions:\n  sandbox:\n    paths: [.]\n",
        encoding="utf-8",
    )

    catalog = AgentCatalog(agents_dir)
    names = {entry.name for entry in catalog.list_routable()}

    assert "web_researcher" in names
    assert "router" not in names
    assert "router" in ROUTABLE_EXCLUDE


def test_catalog_resolve_path(tmp_path: Path) -> None:
    agents_dir = tmp_path / "configs" / "agents"
    agents_dir.mkdir(parents=True)
    yaml_path = agents_dir / "demo.yaml"
    yaml_path.write_text(
        "meta:\n  name: demo\nagent:\n  role: D\n  model: fake\n  system_prompt: x\n"
        "tools:\n  http:\n    enabled: true\npermissions:\n  sandbox:\n    paths: [.]\n",
        encoding="utf-8",
    )

    catalog = AgentCatalog(agents_dir)
    assert catalog.path_for("demo") == yaml_path.resolve()
