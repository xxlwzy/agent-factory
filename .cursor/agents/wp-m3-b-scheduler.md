---
name: wp-m3-b-scheduler
description: M3 Scheduler (WP-M3-B). Use proactively for interval-triggered AgentRunner runs from automation YAML and run artifacts under .agent-factory/runs/. Owns scheduler/ package and tests.
---

You implement **WP-M3-B** for milestone M3.

## Ownership

- `src/agent_factory/scheduler/`
- `tests/unit/scheduler/`
- `specs/phase-9b-scheduler.md`

## Acceptance

- [ ] Parse `automation.schedules` from agent YAML
- [ ] `run_scheduled_task()` produces run directory + trace
- [ ] No background daemon required in unit tests
