# Future Roadmap Spec

> State: Design Draft
> Updated: 2026-05-27
> This file records future Agent Factory features so later agents can continue work without depending on prior chat context.

## 0. Purpose

Agent Factory should grow in vertical slices. Each future feature should get its own phase spec before implementation starts.

## 1. Phase 1: Single-Agent Runtime

Goal: connect config, permissions, trace, and a fake LLM adapter into a testable agent loop.

Expected scope:

- `LLMAdapter` interface.
- Fake adapter for deterministic tests.
- Tool request/result message shapes.
- Runtime state transitions: running, blocked, failed, completed.
- Permission decisions written into `RunTrace`.

Out of scope:

- Real model provider calls.
- Real browser automation.
- Agent teams.

## 2. Phase 2: Tool Registry And Safe Tool Adapters

Goal: introduce atomic tool registration and minimal safe adapters.

Expected scope:

- Tool registry.
- Filesystem read/write inside sandbox.
- HTTP GET inside allowlist.
- Terminal adapter in confirm-only mode.
- Browser adapter design draft if real browser automation is not ready.

Out of scope:

- Multi-step workflow tools.
- Hidden tool-side retries that obscure traceability.

## 3. Phase 3: Web Research Demo

Goal: deliver the first end-to-end personal automation demo.

Expected flow:

1. Load `configs/agents/web_researcher.yaml`.
2. Read an allowed web page through HTTP or browser capability.
3. Summarize content.
4. Write Markdown report into `.agent-factory/runs/<run_id>/artifact/report.md`.
5. Write trace and summary.

Out of scope:

- Autonomous scheduling.
- Notifications.
- Multi-agent review.

## 4. Phase 4: Memory And Skill Drafts

Goal: generate learning artifacts after successful runs without automatically changing long-term behavior.

Expected scope:

- Session summary archive.
- Project/user memory candidates.
- Skill draft generation.
- Human review status.

Out of scope:

- Automatic skill enabling.
- Executable generated scripts.

## 5. Phase 5: Local API And Minimal Web UI

Goal: provide a local observation and control surface.

Expected scope:

- Local API for agents, runs, trace, artifacts, and skill drafts.
- Simple Web UI for run status and artifact viewing.
- No direct tool execution from Web UI; all actions go through runtime and permissions.

Out of scope:

- Multi-user auth.
- Hosted SaaS deployment.

## 6. Later Features

These remain future design topics:

- Agent team YAML.
- Async message bus and inbox/outbox.
- Scheduler and autonomous runs.
- Hooks lifecycle.
- MCP capability integration.
- Worktree isolation for coding-oriented agents.

Each item should become a dedicated spec before implementation.
