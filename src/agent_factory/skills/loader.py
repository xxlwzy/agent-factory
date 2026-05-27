from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_factory.config.schema import AgentFactoryConfig
from agent_factory.skills.index import LoadedSkill, format_skill_context, parse_skill_markdown


@dataclass(frozen=True)
class SkillLoadResult:
    skills: tuple[LoadedSkill, ...]
    warnings: tuple[str, ...]
    skill_context: str


def default_skills_root(workspace_root: str | Path) -> Path:
    return Path(workspace_root).resolve() / "configs" / "skills"


def load_enabled_skills(
    enabled_names: tuple[str, ...],
    skills_root: str | Path,
) -> SkillLoadResult:
    root = Path(skills_root).resolve()
    loaded: list[LoadedSkill] = []
    warnings: list[str] = []

    for raw_name in enabled_names:
        name = str(raw_name).strip()
        if not name:
            continue
        skill_path = root / name / "SKILL.md"
        if not skill_path.is_file():
            warnings.append(f"Enabled skill '{name}' has no SKILL.md at {skill_path}.")
            continue
        parsed = parse_skill_markdown(skill_path.read_text(encoding="utf-8"))
        skill_name = parsed.name or name
        loaded.append(
            LoadedSkill(
                name=skill_name,
                description=parsed.description,
                body=parsed.body,
            )
        )

    skills = tuple(loaded)
    return SkillLoadResult(
        skills=skills,
        warnings=tuple(warnings),
        skill_context=format_skill_context(skills),
    )


def load_skills_for_config(
    config: AgentFactoryConfig,
    workspace_root: str | Path,
    *,
    skills_root: str | Path | None = None,
) -> SkillLoadResult:
    root = Path(skills_root) if skills_root is not None else default_skills_root(workspace_root)
    return load_enabled_skills(config.skills.enabled, root)
