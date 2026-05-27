# Specs Index

`specs/` is the durable product and architecture memory for Agent Factory. It exists so humans and agents can understand the project across sessions without relying on a single conversation context window.

## How To Use This Folder

- Read `AGENTS.md` first, then this index, then the active feature spec.
- Create one spec file per phase or major feature.
- Keep current behavior, decisions, TODOs, tests, and handoff notes in the relevant spec.
- Record future features here before implementation, but mark them as design drafts.
- Do not use specs as implementation logs; implementation plans belong under `docs/superpowers/plans/`.

## Naming

Use stable, stage-oriented names:

```text
phase-0-foundation.md
phase-1-single-agent-runtime.md
phase-2-web-research-demo.md
future-roadmap.md
```

## Spec States

Each spec should declare one state near the top:

- `Design Draft`: discussed direction, not ready to implement.
- `Ready`: approved enough to write an implementation plan.
- `In Progress`: implementation is underway.
- `Implemented`: behavior exists and tests/verification are recorded.
- `Archived`: kept for history, not current behavior.

## Current Specs

| Spec | State | Purpose |
|------|-------|---------|
| `phase-0-foundation.md` | Implemented | Python package skeleton, YAML config loader, permission guard, and run trace foundation. |
| `phase-1-single-agent-runtime.md` | Implemented | Fake-LLM-driven single-agent runtime loop with state transitions and trace events. |
| `phase-2-tool-registry.md` | Implemented | Tool registry with filesystem read/write and HTTP GET adapters; runner executes allowed tools. |
| `phase-3-web-research-demo.md` | Implemented | End-to-end web research demo with report artifact under `.agent-factory/runs/<run_id>/`. |
| `phase-4-memory-skill-drafts.md` | Implemented | Post-run session archive, memory candidates, and pending skill drafts. |
| `phase-5-local-api.md` | Implemented | Read-only local API and minimal Web UI for runs, traces, artifacts, drafts. |
| `phase-6-conversational-router.md` | Implemented | Chat entry with router delegation to YAML specialists and general fallback. |
| `future-roadmap.md` | Design Draft | Future features such as teams, scheduler, hooks, MCP integration. |

## Relationship To Existing Docs

- `docs/superpowers/specs/2026-05-26-agent-factory-design.md` contains the original long-form design discussion.
- `docs/superpowers/plans/2026-05-26-agent-factory-p0-foundation.md` contains the first implementation plan.
- New feature maintenance should start from this `specs/` folder, then link out to detailed plans when needed.
