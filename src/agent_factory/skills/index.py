from __future__ import annotations

from dataclasses import dataclass

import yaml


@dataclass(frozen=True)
class ParsedSkill:
    name: str
    description: str
    body: str


@dataclass(frozen=True)
class LoadedSkill:
    name: str
    description: str
    body: str

    def to_context_block(self) -> str:
        header = f"### Skill: {self.name}"
        if self.description:
            header = f"{header}\n{self.description}"
        if self.body.strip():
            return f"{header}\n\n{self.body.strip()}"
        return header


def parse_skill_markdown(text: str) -> ParsedSkill:
    stripped = text.lstrip("\ufeff")
    if not stripped.startswith("---"):
        return ParsedSkill(name="", description="", body=stripped)

    parts = stripped.split("---", 2)
    if len(parts) < 3:
        return ParsedSkill(name="", description="", body=stripped)

    meta_raw = yaml.safe_load(parts[1]) or {}
    if not isinstance(meta_raw, dict):
        raise ValueError("Skill frontmatter must be a YAML mapping.")

    name = str(meta_raw.get("name", "")).strip()
    description = str(meta_raw.get("description", "")).strip()
    body = parts[2].lstrip("\n")
    return ParsedSkill(name=name, description=description, body=body)


def format_skill_context(skills: tuple[LoadedSkill, ...]) -> str:
    if not skills:
        return ""
    blocks = [skill.to_context_block() for skill in skills]
    return "\n\n".join(blocks)
