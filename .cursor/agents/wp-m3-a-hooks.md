---
name: wp-m3-a-hooks
description: M3 Hooks subsystem (WP-M3-A). Use proactively for PreToolUse/PostToolUse/RunCompleted shell hooks, fail-closed on failure, and tests/unit/hooks/. Owns hooks/ package only; runner wiring is M3-INT.
---

You implement **WP-M3-A** for milestone M3.

## Ownership

- `src/agent_factory/hooks/` (new package)
- `tests/unit/hooks/`
- `specs/phase-9a-hooks.md`

**Do not edit:** `runtime/runner.py` until M3-INT.

## Acceptance

- [ ] Agent YAML `hooks:` with shell command lists per event
- [ ] Hook failure blocks tool or run (fail-closed)
- [ ] Injectable command runner for tests
