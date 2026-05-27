# Phase 10c — Team Runner

> State: Implemented
> WP: WP-M4-C

## Goal

Run pipeline steps sequentially; each step uses `AgentRunner`; handoffs via `MessageBus`.

## Demo

`configs/teams/research_report.yaml` — researcher then writer.

## Trace

Emit `team_message_sent` with `message_id` on member run traces.

## Tests

`tests/unit/team/test_runner.py`
