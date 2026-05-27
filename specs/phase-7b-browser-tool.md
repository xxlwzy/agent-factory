# Phase 7b — Browser Tool

> State: Implemented
> WP: WP-M1-B
> Plan: `docs/superpowers/plans/2026-05-27-parallel-development-tracks.md`

## Goal

Atomic `read` / `navigate` via injectable fetcher (HTTP GET or mock). No Playwright in M1.

## Contract

| Field | Value |
|-------|-------|
| Tool name | `browser` |
| Operations | `read`, `navigate` (same behavior in MVP) |
| Target | URL string |
| `submit` | Adapter returns failure; guard may still `confirm` on `browser.submit` |

## Out of scope

- Playwright dependency
- Form submit implementation

## Tests

`tests/unit/tools/test_browser.py`

## Acceptance

- [x] Injectable fetcher; no network in CI (`tests/unit/tools/test_browser.py`)
- [x] Registered in `ToolRegistry` via `build_default_registry`
