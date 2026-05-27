# Phase 0 Foundation Spec

> State: Implemented
> Updated: 2026-05-27
> This spec is the durable handoff for the first Agent Factory foundation slice. The original long-form design lives in `docs/superpowers/specs/2026-05-26-agent-factory-design.md`.

## 0. Goal

Build the smallest reliable foundation for Agent Factory: a Python package that can load agent YAML, preserve schema boundaries, evaluate sandbox-first permissions, and write run traces.

## 1. Implemented Behavior

### 1.1 Python Package Skeleton

Implemented files:

- `pyproject.toml`
- `README.md`
- `.gitignore`
- `src/agent_factory/__init__.py`

The package uses Python 3.11+, `PyYAML`, and `pytest`. Runtime artifacts and generated files are ignored through `.gitignore`.

### 1.2 Agent YAML Config Loader

Implemented files:

- `src/agent_factory/config/schema.py`
- `src/agent_factory/config/loader.py`
- `src/agent_factory/config/unsupported.py`
- `src/agent_factory/config/__init__.py`
- `configs/agents/web_researcher.yaml`

The loader parses:

- `meta`
- `agent`
- `runtime`
- `tools`
- `permissions`
- `memory`
- `skills`

Recognized future sections such as `workflow` and `team` are not executed in Phase 0. They are reported as mocked MVP sections rather than silently ignored. Unknown top-level sections produce schema warnings.

### 1.3 Sandbox-First Permission Guard

Implemented files:

- `src/agent_factory/permissions/guard.py`
- `src/agent_factory/permissions/sandbox.py`
- `src/agent_factory/permissions/policy.py`
- `src/agent_factory/permissions/__init__.py`
- `configs/policies/default.yaml`

Permission rules:

1. Disabled or missing tools are denied.
2. Filesystem targets must be inside configured sandbox paths.
3. HTTP targets must be inside configured domain allowlist.
4. Explicit `deny` rules take precedence over `confirm` and `allow`.
5. Explicit `confirm` rules apply after sandbox checks pass.
6. HTTP non-GET operations require confirmation by default.
7. Other enabled tools require confirmation in Phase 0.

### 1.4 Run Trace Writer

Implemented files:

- `src/agent_factory/runtime/trace.py`
- `src/agent_factory/runtime/__init__.py`

`RunTrace` writes:

- `trace.jsonl` events with timestamp, type, and data.
- `summary.md` for run summaries.

## 2. Tests

Implemented tests:

- `tests/unit/config/test_loader.py`
- `tests/unit/permissions/test_guard.py`
- `tests/unit/runtime/test_trace.py`

Current verification command:

```bash
python -m pytest tests/unit -v
```

Last known result:

```text
14 passed
```

## 3. Key Decisions

- YAML is declarative configuration, not a workflow scripting language.
- Tools remain atomic. Multi-step behavior belongs in runtime orchestration or skills.
- Schema-recognized but unimplemented capabilities must be traceable as mocked/unsupported.
- Permission behavior should fail closed.
- `memory` and `skills` have minimal config contracts now, even though full memory and skill lifecycle are future work.

## 4. Out Of Scope For Phase 0

- Real LLM adapter.
- Agent loop.
- Tool registry.
- Real filesystem, terminal, browser, or HTTP tool adapters.
- Web UI or API server.
- Team runtime and message bus.
- Scheduler, hooks, notifications.
- Automatic skill enabling or long-term memory writes.

## 5. Next Phase

Recommended next spec: `phase-1-single-agent-runtime.md`.

The next phase should connect the existing config, permission, and trace primitives into a fake-LLM-driven single-agent runtime. It should still avoid real external side effects until the loop contract is tested.
