# Future Roadmap Spec

> State: Design Draft
> Updated: 2026-05-27
> This file records future Agent Factory features so later agents can continue work without depending on prior chat context.

## 0. Purpose

Agent Factory should grow in vertical slices. Each future feature should get its own phase spec before implementation starts.

## 1. Phase 1: Single-Agent Runtime

Status: Implemented. See `phase-1-single-agent-runtime.md`.

## 2. Phase 2: Tool Registry And Safe Tool Adapters

Status: Implemented. See `phase-2-tool-registry.md`.

Remaining for later phases:

- Terminal adapter execution behind approval UI.
- Browser adapter with real automation.

## 3. Phase 3: Web Research Demo

Status: Implemented. See `phase-3-web-research-demo.md`.

Entry point: `run_web_research_demo()` in `src/agent_factory/runtime/web_research.py`.

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
