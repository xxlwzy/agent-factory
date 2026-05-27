# Phase 5 Local API And Minimal Web UI Spec

> State: Implemented
> Updated: 2026-05-27
> This spec covers a read-only local HTTP API and a minimal browser UI for observing runs and skill drafts.

## 0. Goal

Provide a local observation surface on top of existing runtime artifacts under `.agent-factory/`, without executing tools from the API or UI.

## 1. Scope

In scope:

- Read-only JSON API (`127.0.0.1`) for agents, runs, trace, artifacts, skill drafts.
- Static minimal Web UI (`apps/web/index.html`) served by the same process.
- CLI script `scripts/run_local_api.py`.
- Path traversal protection for artifact reads.

Out of scope:

- POST endpoints that trigger agent runs or tool execution.
- Multi-user auth or hosted deployment.
- TypeScript build chain or SPA framework.

## 2. API Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Web UI |
| GET | `/api/agents` | Agent config names |
| GET | `/api/runs` | Run index |
| GET | `/api/runs/{run_id}` | Run summary metadata |
| GET | `/api/runs/{run_id}/trace` | Parsed trace events |
| GET | `/api/runs/{run_id}/artifacts/{name}` | Artifact file content |
| GET | `/api/skills/drafts` | Skill draft index with review status |

## 3. File Responsibilities

| File | Responsibility |
|------|----------------|
| `src/agent_factory/api/store.py` | Read-only workspace artifact access |
| `src/agent_factory/api/server.py` | HTTP server and routing |
| `apps/web/index.html` | Minimal observation UI |
| `scripts/run_local_api.py` | Start local server |
| `tests/unit/api/test_store.py` | Store unit tests |
| `tests/unit/api/test_server.py` | HTTP integration tests |

## 4. Key Decisions

- Use stdlib `http.server` only (no new runtime dependencies).
- Bind to `127.0.0.1` by default.
- Artifact paths are single-segment filenames under `artifact/` (e.g. `report.md`).

## 5. Tests

1. Store lists runs and drafts from workspace layout.
2. Store rejects artifact path traversal.
3. HTTP server returns JSON for `/api/runs` and serves UI at `/`.

Verification: `python -m pytest tests/unit -v`

Last known result:

```text
47 passed
```

Start server:

```bash
python scripts/run_local_api.py
# open http://127.0.0.1:8765/
```

## 6. Handoff

Later phases may add POST run triggers through runtime entrypoints, still behind permissions—not from the Web UI directly.
