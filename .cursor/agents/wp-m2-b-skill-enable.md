---
name: wp-m2-b-skill-enable
description: M2 Skill enable API/UI (WP-M2-B). Use proactively for POST /api/skills/drafts/{id}/enable, draft promotion to configs/skills/, and Web UI enable buttons. Owns skills/review enable logic and api skills routes/tests.
---

You implement **WP-M2-B** for Agent Factory milestone M2.

## Before coding

1. Read `AGENTS.md`, parallel tracks plan § WP-M2-B.
2. Read or create `specs/phase-8b-skill-enable.md`.
3. Branch: `feature/wp-m2-b-skill-enable` from latest `master`.

## Ownership

- Extend `src/agent_factory/skills/review.py` (enable draft helper)
- `src/agent_factory/api/skills.py` (handlers)
- Wire `src/agent_factory/api/server.py` (minimal POST route)
- `tests/unit/api/test_skills_api.py`
- `apps/web/index.html` (enable button on drafts table)
- `specs/phase-8b-skill-enable.md`

**Do not edit:** `AgentRunner` loop (M2-INT).

## Acceptance

- [ ] `POST /api/skills/drafts/{id}/enable` copies SKILL.md and sets review status `enabled`
- [ ] Enabled skill visible via skill loader (coordinate with M2-A interface)
