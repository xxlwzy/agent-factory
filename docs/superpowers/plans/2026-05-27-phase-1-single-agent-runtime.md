# Phase 1 Single-Agent Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect Phase 0 config, permissions, and trace primitives into a deterministic single-agent runtime loop.

**Architecture:** Add a small `llm` package for response/message shapes and fake adapter. Add runtime state/result types and `AgentRunner` that calls the adapter, evaluates tool calls with `PermissionGuard`, records `RunTrace` events, and stops on completed, blocked, failed, or max-turn states. No real model calls or real tool execution are implemented in this phase.

**Tech Stack:** Python 3.11+, stdlib dataclasses/protocols, pytest.

---

## Task 1: LLM Message Types And Fake Adapter

**Files:**
- Create: `src/agent_factory/llm/__init__.py`
- Create: `src/agent_factory/llm/messages.py`
- Create: `src/agent_factory/llm/base.py`
- Create: `src/agent_factory/llm/fake.py`
- Test: `tests/unit/llm/test_fake.py`

Steps:

- [ ] Write tests for scripted response order and exhaustion.
- [ ] Run tests and confirm they fail because `agent_factory.llm` does not exist.
- [ ] Implement dataclasses: `ToolCallResponse`, `FinalResponse`, `LLMRequest`.
- [ ] Implement `LLMAdapter` protocol.
- [ ] Implement `FakeLLMAdapter`.
- [ ] Run `python -m pytest tests/unit/llm/test_fake.py -v`.

## Task 2: Agent Runner State And Loop

**Files:**
- Create: `src/agent_factory/runtime/states.py`
- Create: `src/agent_factory/runtime/runner.py`
- Modify: `src/agent_factory/runtime/__init__.py`
- Test: `tests/unit/runtime/test_runner.py`

Steps:

- [ ] Write runner tests for completed, allowed-tool-then-completed, confirm-blocked, deny-blocked, adapter-exhausted, and max-turns failed cases.
- [ ] Run tests and confirm they fail because runner types do not exist.
- [ ] Implement `RunStatus` and `RunResult`.
- [ ] Implement `AgentRunner`.
- [ ] Run `python -m pytest tests/unit/runtime/test_runner.py -v`.

## Task 3: Specs And Verification

**Files:**
- Modify: `specs/phase-1-single-agent-runtime.md`
- Modify if needed: `specs/README.md`

Steps:

- [ ] Update Phase 1 spec state/details if implementation differs from planned behavior.
- [ ] Run `python -m pytest tests/unit -v`.
- [ ] Run lints through IDE diagnostics for changed files.
- [ ] Request code review for Phase 1.

## Self-Review Notes

- This plan intentionally skips real tool execution and approval UI.
- Allowed tool calls are recorded as `tool_skipped` so the loop contract is testable without side effects.
- Confirm/deny decisions block the run because no human approval channel exists in Phase 1.
