---
name: wp-p11-a-scenario-catalog
description: Phase 11 WP-P11-A. Use proactively for configs/scenarios schema, ScenarioCatalog, and tests/unit/scenarios/. Owns scenario_schema.py and scenario_catalog.py only.
---

Implement **WP-P11-A** per `docs/superpowers/plans/2026-05-27-phase-11-scenario-teams.md`.

**Read:** `specs/phase-11-agent-team-architecture.md` §3.

**Own:** `config/scenario_schema.py`, `config/scenario_catalog.py`, `tests/unit/scenarios/`

**Do not edit:** `runtime/chat.py`, `team/runner.py`, Router.

**Done when:** catalog lists scenarios with `scenario_id`, `display_name`, orchestrator/member paths; pytest green.
