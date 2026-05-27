---
name: wp-m3-c-mcp-routing
description: M3 MCP routing (WP-M3-C). Use proactively to map MCP tool descriptors to ToolRequest and register MCP tools through PermissionGuard. Owns mcp/ package; registry wiring is M3-INT.
---

You implement **WP-M3-C** for milestone M3.

## Ownership

- `src/agent_factory/mcp/`
- `tests/unit/mcp/`
- `specs/phase-9c-mcp-routing.md`

## Acceptance

- [ ] Descriptors map to `ToolRequest`
- [ ] MCP adapter executes via injectable handlers (no network in CI)
- [ ] Do not add Playwright or real MCP transport in M3
