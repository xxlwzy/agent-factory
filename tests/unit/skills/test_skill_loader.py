from pathlib import Path

from agent_factory.skills.index import parse_skill_markdown
from agent_factory.skills.loader import load_enabled_skills


def test_parse_skill_markdown_reads_frontmatter() -> None:
    parsed = parse_skill_markdown(
        "---\nname: demo\ndescription: Do demo things\n---\n\nStep one.\n"
    )

    assert parsed.name == "demo"
    assert parsed.description == "Do demo things"
    assert "Step one" in parsed.body


def test_load_enabled_skills_reads_configs_directory(tmp_path: Path) -> None:
    skills_root = tmp_path / "configs" / "skills"
    skill_dir = skills_root / "web-summary"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: web-summary\ndescription: Summarize pages\n---\n\nUse HTTP GET.\n",
        encoding="utf-8",
    )

    result = load_enabled_skills(("web-summary", "missing-skill"), skills_root)

    assert len(result.skills) == 1
    assert result.skills[0].name == "web-summary"
    assert "HTTP GET" in result.skill_context
    assert any("missing-skill" in warning for warning in result.warnings)
