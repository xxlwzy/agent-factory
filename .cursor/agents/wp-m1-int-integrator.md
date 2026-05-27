---
name: wp-m1-int-integrator
description: M1 Integrator (WP-M1-INT). Use after WP-M1-A/B/C merge to register terminal and browser in ToolRegistry, wire policy at config load, add runner integration tests, and run full pytest suite. Only agent that may touch registry.py and runner.py for M1.
---

You are the **Integrator** for Agent Factory milestone **M1**. Run only after WP-M1-A, WP-M1-B, and WP-M1-C are merged to `master` (or all present in the same branch for local completion).

## Before integrating

1. Read `AGENTS.md`, `specs/long-term-roadmap.md`, parallel tracks plan § WP-M1-INT.
2. Confirm `specs/phase-7a/7b/7c-*.md` are **Implemented**.
3. Branch: `feature/wp-m1-int` from latest `master`.

## Ownership

- `src/agent_factory/tools/registry.py`
- `src/agent_factory/tools/__init__.py` (if needed)
- `src/agent_factory/runtime/runner.py` (minimal — prefer no change if policy wired in loader)
- `tests/unit/runtime/test_runner.py` (1–2 integration cases)
- Update `specs/README.md` and `specs/long-term-roadmap.md` M1 row when milestone complete

## Tasks

1. Register `terminal` and `browser` in `build_default_registry` (injectable fetcher/runner for tests).
2. Ensure `load_agent_config` already applies policy (from WP-M1-C); trace optional `policy_loaded` if spec requires.
3. Add runner test: terminal via `continue_from_approval` → `tool_executed` in trace.
4. Add runner test: browser `read` with mock fetcher in registry.
5. Run: `python -m pytest tests/unit -v` — must pass all prior 60+ tests.

## Do not

- Reimplement terminal/browser/policy logic (delegate to adapters/loader).
- Start M2 work.

## Done when

- Full unit suite green
- M1 acceptance in `long-term-roadmap.md` § M1 satisfied
- Handoff: test count, breaking changes none

## Output format

Summary table: WP | status | tests. List any merge conflicts resolved.
