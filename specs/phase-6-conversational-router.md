# Phase 6 Conversational Router Spec

> State: Implemented
> Updated: 2026-05-27
> This spec adds a generic chat entrypoint with router agent delegation to YAML-defined specialists and a general fallback agent.

## 0. Goal

User message → router selects a specialist agent (or `general_assistant`) → `AgentRunner` loop with atomic FC → reply returned via API and Web UI.

## 1. Scope

In scope:

- `AgentCatalog` from `configs/agents/*.yaml` (excluding `router`).
- `configs/agents/router.yaml`, `configs/agents/general_assistant.yaml`.
- Config-driven LiteLLM adapter for any agent YAML enabled tools.
- `run_chat()` orchestration with routing trace metadata.
- `POST /api/chat`, `GET /api/agents/catalog`, Web UI chat panel.

Out of scope:

- Agent teams and multi-agent parallelism.
- Human approval UI for `confirm` decisions.
- Multi-turn session memory (single-turn MVP).

## 2. Routing Protocol

Router returns:

- `target_agent`: catalog name or `general_assistant`
- `delegated_task`: task string for specialist `AgentRunner`
- `reason`: short explanation for trace/API

## 3. Tests

1. Catalog lists specialists, excludes router.
2. Rule/fake router picks `web_researcher` vs `general_assistant`.
3. `run_chat` returns reply on completed specialist run.
4. `POST /api/chat` returns JSON reply.

Verification: `python -m pytest tests/unit -v`
