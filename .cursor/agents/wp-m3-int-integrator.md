---
name: wp-m3-int-integrator
description: M3 Integrator (WP-M3-INT). Use after M3-A/C merge to wire hooks into AgentRunner and MCP tools into ToolRegistry; run full pytest. Only agent that may edit runner.py and registry.py for M3.
---

Integrate M3 hooks and MCP into the harness.

## Ownership

- `runtime/runner.py` (hook dispatch)
- `tools/registry.py` (MCP adapters)
- `config/loader.py`, `config/schema.py` (hooks + automation + mcp sections)
- `config/unsupported.py`
- Integration tests in `tests/unit/runtime/test_runner.py`

## Acceptance

- [ ] PreToolUse blocks tool on hook failure
- [ ] MCP tool calls go through PermissionGuard
- [ ] Full unit suite passes
