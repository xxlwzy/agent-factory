# Phase 9b — Scheduler

> State: Implemented
> WP: WP-M3-B

## Goal

Trigger `AgentRunner.run()` from `automation.schedules` interval definitions.

## YAML

```yaml
automation:
  schedules:
    - name: heartbeat
      interval_seconds: 300
      task: "Summarize workspace status"
```

## Tests

`tests/unit/scheduler/`
