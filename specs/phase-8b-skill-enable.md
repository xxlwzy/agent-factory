# Phase 8b — Skill Enable API

> State: Implemented
> WP: WP-M2-B

## Goal

Promote reviewed draft from `.agent-factory/skills/drafts/<id>/` to `configs/skills/<name>/SKILL.md`.

## API

`POST /api/skills/drafts/{draft_id}/enable`

Optional JSON body: `{ "skill_name": "custom-name" }`

## Acceptance

- [x] Copies SKILL.md; `review.json` status `enabled`
- [x] Enabled skill loadable by skill loader (`tests/unit/api/test_skills_api.py`)
