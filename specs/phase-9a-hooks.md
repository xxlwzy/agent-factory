# Phase 9a — Hooks

> State: Implemented
> WP: WP-M3-A

## Goal

Execute configured shell hooks on `PreToolUse`, `PostToolUse`, and `RunCompleted`. Fail-closed on non-zero exit.

## YAML

```yaml
hooks:
  PreToolUse:
    - command: ["python", "-c", "print('ok')"]
  PostToolUse: []
  RunCompleted: []
```

## Tests

`tests/unit/hooks/`
