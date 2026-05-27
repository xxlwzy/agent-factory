# Phase 2 Tool Registry Implementation Plan

**Goal:** Add atomic tool registration and minimal safe adapters; wire `AgentRunner` to execute allowed tool calls.

**Architecture:** New `tools` package with `ToolRegistry`, `FilesystemTool`, and `HttpTool`. Runner calls registry after `PermissionGuard` returns allow; trace event type changes from `tool_skipped` to `tool_executed`.

## Tasks

- [x] Tool base types and registry tests
- [x] Filesystem and HTTP adapters
- [x] Runner integration and runtime tests
- [x] Update `specs/phase-2-tool-registry.md` and index

Verification: `python -m pytest tests/unit -v` (31 passed).
