---
name: wp-m2-c-memory-promote
description: M2 Memory promotion API (WP-M2-C). Use proactively to confirm project/user memory candidates into .agent-factory/memory/ after human review. Owns memory/promote.py and memory API routes/tests.
---

You implement **WP-M2-C** for Agent Factory milestone M2.

## Before coding

1. Read `AGENTS.md`, parallel tracks plan § WP-M2-C, `specs/phase-4-memory-skill-drafts.md`.
2. Read or create `specs/phase-8c-memory-promotion.md`.
3. Branch: `feature/wp-m2-c-memory-promote` from latest `master`.

## Ownership

- `src/agent_factory/memory/promote.py`
- `src/agent_factory/api/memory.py`
- Wire `api/server.py` (GET candidates, POST promote)
- `tests/unit/memory/test_promote.py`
- `specs/phase-8c-memory-promotion.md`

**Do not change:** session auto-archive in `runtime/learning.py`.

## Acceptance

- [ ] Project/user promoted only via API
- [ ] Session archive behavior unchanged
