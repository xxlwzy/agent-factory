# Phase 8c — Memory Promotion API

> State: Implemented
> WP: WP-M2-C

## Goal

Confirm project/user memory candidates into durable memory files after human review.

## Layout

- Candidates: `.agent-factory/memory/{project|user}/candidates/<id>.md`
- Promoted: `.agent-factory/memory/{project|user}/<id>.md`

## API

- `GET /api/memory/candidates/{layer}` — `layer` is `project` or `user`
- `POST /api/memory/candidates/{layer}/{candidate_id}/promote`

Session archive via `learning.py` unchanged.

## Acceptance

- [x] Promote copies candidate to parent layer directory
- [x] Session auto-archive unchanged (`tests/unit/runtime/test_learning.py`)
