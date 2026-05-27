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

Status: Implemented. See `phase-4-memory-skill-drafts.md`.

Entry point: `generate_learning_artifacts()` in `src/agent_factory/runtime/learning.py`.

## 5. Phase 5: Local API And Minimal Web UI

Status: Implemented. See `phase-5-local-api.md`.

Start: `python scripts/run_local_api.py` → http://127.0.0.1:8765/

## 6. Phase 6: Conversational Router

Status: Implemented. See `phase-6-conversational-router.md`.

Entry points: `run_chat()`, `POST /api/chat`, Web UI chat panel on http://127.0.0.1:8765/

## 7. Later Features

Active planning has moved to:

- `specs/long-term-roadmap.md` — milestones M1–M5
- `docs/superpowers/plans/2026-05-27-parallel-development-tracks.md` — parallel work packages for multi-agent development

Topics still open: agent teams, message bus, scheduler, hooks, MCP, terminal/browser execution, skill/memory promotion, worktree isolation.
