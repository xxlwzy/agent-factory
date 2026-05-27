---
name: wp-m4-team
description: M4 Team collaboration (WP-M4-A/B/C sequential). Use for team YAML schema, MessageBus, and research+report team runner demo. Work in order A→B→C; do not parallelize M4 file edits across agents.
---

You implement **M4** (multi-agent team) for Agent Factory.

## Sequential work packages

1. **WP-M4-A** — `config/team_schema.py`, `specs/phase-10a-team-schema.md`, `tests/unit/config/test_team_schema.py`
2. **WP-M4-B** — `team/bus.py`, `specs/phase-10b-message-bus.md`, `tests/unit/team/test_bus.py`
3. **WP-M4-C** — `team/runner.py`, `configs/teams/research_report.yaml`, demo tests, `specs/phase-10c-team-runner.md`

## Acceptance (milestone)

- [ ] Two agents complete research → write report pipeline
- [ ] Trace events reference `message_id`
- [ ] `python -m pytest tests/unit -v` passes

## Do not

- Implement M5 CLI or distributed bus yet.
