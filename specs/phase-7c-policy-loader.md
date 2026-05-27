# Phase 7c — Policy Loader

> State: Implemented
> WP: WP-M1-C
> Plan: `docs/superpowers/plans/2026-05-27-parallel-development-tracks.md`

## Goal

Merge reusable policy files under `configs/policies/` into runtime `PermissionsConfig` when an agent references them.

## Agent YAML

```yaml
policy: default   # optional top-level
permissions:
  sandbox:
    paths: [.]
```

Policy file path: `<agent_dir>/../policies/<name>.yaml` (e.g. `configs/policies/default.yaml`).

## Merge semantics

1. Parse policy file `permissions` section → `PermissionsConfig` (base).
2. Parse agent inline `permissions` → overlay.
3. **Union** (dedupe, preserve order): `sandbox.paths`, `sandbox.domains`, `confirm`, `deny`.
4. Missing policy file → `ValueError` (fail closed).

## Out of scope

- Tool adapter changes

## Tests

`tests/unit/config/test_policy_loader.py`

## Acceptance

- [x] `policy: default` merges deny/confirm (`tests/unit/config/test_policy_loader.py`)
- [x] Missing policy raises clear error
