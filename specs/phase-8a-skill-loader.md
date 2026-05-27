# Phase 8a — Skill Loader

> State: Implemented
> WP: WP-M2-A
> Plan: `docs/superpowers/plans/2026-05-27-parallel-development-tracks.md`

## Goal

Load agent `skills.enabled` entries from `configs/skills/<name>/SKILL.md` for runner/LLM context.

## Contract

- Parse YAML frontmatter (`name`, `description`) + markdown body.
- Unknown enabled names → warning strings (trace via M2-INT).
- Do not read or auto-enable `.agent-factory/skills/drafts/`.

## Tests

`tests/unit/skills/test_loader.py`

## Acceptance

- [x] Frontmatter parsing (`tests/unit/skills/test_skill_loader.py`)
- [x] Missing skill directory warns, does not fail load of other skills
