# Phase 9c — MCP Tool Routing

> State: Implemented
> WP: WP-M3-C

## Goal

Register MCP tool descriptors as registry adapters; map to `ToolRequest` for `PermissionGuard`. Transport deferred.

## YAML

```yaml
mcp:
  tools:
    - name: search
      description: Search the web
```

Enables `tools.mcp.enabled: true` with operations from descriptors.

## Tests

`tests/unit/mcp/`
