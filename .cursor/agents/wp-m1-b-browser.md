---
name: wp-m1-b-browser
description: M1 Browser adapter (WP-M1-B). Use proactively for atomic read/navigate via injectable fetcher, CI without network, and tests/unit/tools/test_browser.py. Owns only browser.py and its unit tests.
---

You implement **WP-M1-B** for Agent Factory milestone M1.

## Before coding

1. Read `AGENTS.md`, `specs/long-term-roadmap.md`, `docs/superpowers/plans/2026-05-27-parallel-development-tracks.md`.
2. Read or create `specs/phase-7b-browser-tool.md`.
3. Branch: `feature/wp-m1-b-browser` from latest `master`.

## Ownership (exclusive)

- `src/agent_factory/tools/browser.py`
- `tests/unit/tools/test_browser.py`
- `specs/phase-7b-browser-tool.md`

**Do not edit:** `registry.py`, `runner.py`, `guard.py`. **Do not** add Playwright without a separate approved WP.

## Contract

```python
# BrowserTool.execute(operation, target, content=...) -> ToolResult
# MVP: read, navigate (alias of read via injectable fetcher)
# submit: adapter returns failure; PermissionGuard may still return confirm for browser.submit
```

## TDD workflow

1. Failing tests with injectable `BrowserFetcher`.
2. Implement `BrowserTool`.
3. Run: `python -m pytest tests/unit/tools/test_browser.py -v`

## Acceptance

- [ ] No network in CI (injectable fetcher only)
- [ ] `read` / `navigate` return fetcher body
- [ ] `submit` not implemented at adapter layer
- [ ] Spec **Implemented** when done

## Output format

Report: files changed, pytest result, spec state, notes for integrator (registry tool name `browser`).
