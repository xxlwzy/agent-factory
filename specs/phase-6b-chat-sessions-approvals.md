# Phase 6b Chat Sessions And Approvals Spec

> State: Implemented
> Updated: 2026-05-27
> Multi-turn chat sessions and human approval for confirm-gated tool calls.

## 0. Goal

- Persist chat sessions under `.agent-factory/sessions/` for multi-turn UI.
- Pause runs on `confirm` permission decisions; user approves/denies in Web UI.
- Resume agent loop after approval without re-routing.

## 1. Scope

In scope:

- `ChatSessionStore` read/write session transcripts.
- `RunStatus.AWAITING_CONFIRM` and `ApprovalStore`.
- `AgentRunner.continue_from_approval()`.
- API: `GET /api/chat/sessions/{id}`, `POST /api/chat` with `session_id`, approvals endpoints.
- Web UI: message thread, pending approval banner with approve/deny.

Out of scope:

- Streaming tokens.
- Multi-user auth.

## 2. Tests

- `tests/unit/runtime/test_session_and_approval.py`
- `tests/unit/runtime/test_runner_approval.py`
- `tests/unit/api/test_approvals_api.py`

Verification: `python -m pytest tests/unit -v` (60 passed as of 2026-05-27).

## 3. Handoff

- Sessions: `.agent-factory/sessions/<id>.json`
- Approvals: `.agent-factory/approvals/<id>.json`
- Local UI: `python scripts/run_local_api.py` → http://127.0.0.1:8765/
