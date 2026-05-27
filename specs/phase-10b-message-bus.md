# Phase 10b — Message Bus

> State: Implemented
> WP: WP-M4-B

## Goal

In-memory async mailbox for team handoffs.

## Message fields

`message_id`, `sender`, `receiver`, `task_ref`, `payload`, `status` (`pending` | `delivered` | `processed`).

## Tests

`tests/unit/team/test_bus.py`
