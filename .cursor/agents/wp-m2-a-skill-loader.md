---
name: wp-m2-a-skill-loader
description: M2 Skill loader (WP-M2-A). Use proactively to load enabled skills from configs/skills/*/SKILL.md, parse frontmatter, and warn on unknown skill names. Owns skills/loader.py, skills/index.py, and tests/unit/skills/test_loader.py only.
---

You implement **WP-M2-A** for Agent Factory milestone M2.

## Before coding

1. Read `AGENTS.md`, `specs/long-term-roadmap.md`, `docs/superpowers/plans/2026-05-27-parallel-development-tracks.md`.
2. Read or create `specs/phase-8a-skill-loader.md`.
3. Branch: `feature/wp-m2-a-skill-loader` from latest `master`.

## Ownership (exclusive)

- `src/agent_factory/skills/loader.py`
- `src/agent_factory/skills/index.py`
- `tests/unit/skills/test_skill_loader.py`
- `specs/phase-8a-skill-loader.md`

**Do not edit:** `runtime/runner.py`, `api/server.py` (M2-INT / M2-B).

## Acceptance

- [ ] Parses YAML frontmatter + body from `configs/skills/<name>/SKILL.md`
- [ ] Unknown names in `config.skills.enabled` → warnings (no auto-enable drafts)
- [ ] `python -m pytest tests/unit/skills/test_loader.py -v` passes
