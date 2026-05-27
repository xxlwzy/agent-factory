# Agent Factory Agent Guide

This file is the first document an agent should read before changing this repository. It explains the project shape, development rules, and where durable feature context lives.

## Project Purpose

Agent Factory is a local-first personal agent harness. The first product direction is not a multi-user SaaS or a heavy workflow engine. It should make it easy to define a single agent with YAML, give it atomic capabilities, enforce sandbox-first permissions, record run traces, and later generate reviewable skill drafts.

## Required Reading Order

1. `README.md` for the short project overview.
2. `specs/README.md` for the feature/spec index and document rules.
3. The active feature spec under `specs/`, usually the highest phase number or the file named by the user.
4. Relevant implementation plans under `docs/superpowers/plans/` when executing a planned task.
5. Source files and tests only after understanding the current spec.

## Current Architecture Boundaries

- `src/agent_factory/config/` owns YAML parsing, schema dataclasses, defaults, and unsupported-field warnings.
- `src/agent_factory/permissions/` owns sandbox-first allow/confirm/deny decisions.
- `src/agent_factory/runtime/` owns run-level runtime primitives such as trace writing.
- `configs/agents/` contains reusable agent YAML manifests.
- `configs/policies/` contains reusable permission policy examples.
- `specs/` contains durable feature specs for humans and agents.
- `.agent-factory/` is reserved for local runtime data and must not be committed.

## Git Workflow (Baseline: `master`)

- `master` is the stable baseline branch for verified vertical slices.
- Start each feature from latest `master` on a `feature/<short-name>` branch.
- Merge to `master` only after `python -m pytest tests/unit -v` passes and the relevant spec is updated.
- See `docs/development-workflow.md` for the full branching checklist.

## Development Rules

1. Keep tools atomic. Do not hide multi-step business workflows inside a tool adapter; compose tools through runtime logic or skills.
2. Route every tool action through `PermissionGuard` before execution.
3. Prefer fail-closed behavior for unclear permissions, unsupported actions, unknown target paths, and unknown domains.
4. Do not silently drop user-visible YAML sections. Parse them, warn about them, or mark them as mocked/unsupported in traceable output.
5. Write or update the relevant spec before implementing behavior that changes architecture, permissions, schema, memory, skills, runtime flow, or public configuration.
6. Use TDD for production behavior: write a failing test, confirm the failure, implement the minimum code, then make the test pass.
7. Keep generated/runtime files out of source directories. Run artifacts belong under `.agent-factory/runs/<run_id>/`.
8. Do not introduce Web UI, real LLM calls, scheduler, hooks, team runtime, or autonomous skill enabling unless the active spec and plan call for it.
9. Preserve the separation between durable specs (`specs/`) and process artifacts (`docs/superpowers/`).
10. When handing off across agents, update the active spec with decisions, implemented behavior, tests, and remaining TODOs before ending the task.

## Verification

Before claiming completion, run the narrow tests for the touched area and then the broader suite when practical:

```bash
python -m pytest tests/unit -v
```

If a command cannot be run, state that explicitly in the handoff.
