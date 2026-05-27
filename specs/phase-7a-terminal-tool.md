# Phase 7a — Terminal Tool

> State: Implemented
> WP: WP-M1-A
> Plan: `docs/superpowers/plans/2026-05-27-parallel-development-tracks.md`

## Goal

Atomic terminal execution inside workspace `cwd`; deny dangerous command patterns; default permission path remains confirm via `PermissionGuard`.

## Contract

| Field | Value |
|-------|-------|
| Tool name | `terminal` |
| Operations | `run` (MVP only) |
| Target | Command string (parsed with `shlex.split`, no `shell=True`) |
| cwd | `workspace_root` resolved path |
| Deny | Substring checks before subprocess (e.g. `rm -rf`, `\| bash`, `curl\|bash`) |

Injectable `CommandRunner` for unit tests (no real subprocess in CI).

## Out of scope

- Changing `PermissionGuard` rules (integrator/M1-INT only for tests)
- Web UI, Playwright

## Tests

`tests/unit/tools/test_terminal.py`

## Acceptance

- [x] Mocked subprocess tests pass (`tests/unit/tools/test_terminal.py`)
- [x] Dangerous commands fail at adapter
- [x] Registered in `ToolRegistry` via `build_default_registry`
