# Phase 4 Memory And Skill Drafts Spec

> State: Implemented
> Updated: 2026-05-27
> This spec covers post-run learning artifacts: session archive, memory candidates, and reviewable skill drafts.

## 0. Goal

After a **completed** agent run, generate local learning artifacts under `.agent-factory/` without automatically enabling skills or writing long-term memory.

## 1. Scope

In scope:

- `generate_learning_artifacts()` orchestration after successful runs.
- Session summary archive under `memory.session_path`.
- Project and user memory **candidates** (review queue, not auto-applied).
- Skill draft directory with `SKILL.md` and `review.json` (`status: pending`).
- Integration with `run_web_research_demo()` on `RunStatus.COMPLETED`.

Out of scope:

- Automatic skill enabling.
- Executable generated scripts.
- LLM-based artifact authoring in this phase (templates only).

## 2. Artifact Layout

```text
.agent-factory/
  memory/session/<run_id>.md
  memory/project/candidates/<run_id>.md
  memory/user/candidates/<run_id>.md
  skills/drafts/<agent>-<run_id>/
    SKILL.md
    review.json
```

## 3. File Responsibilities

| File | Responsibility |
|------|----------------|
| `src/agent_factory/memory/session.py` | Archive run `summary.md` |
| `src/agent_factory/memory/candidates.py` | Write project/user candidate markdown |
| `src/agent_factory/skills/review.py` | Review status constants and JSON writer |
| `src/agent_factory/skills/draft.py` | Generate skill draft markdown |
| `src/agent_factory/runtime/learning.py` | Orchestrate artifact generation |
| `tests/unit/runtime/test_learning.py` | Learning artifact tests |

## 4. Key Decisions

- Only `completed` runs produce artifacts; blocked/failed runs skip generation.
- Candidates and drafts are always `pending` until a human review flow exists in a later phase.
- Paths come from `AgentFactoryConfig.memory` and `AgentFactoryConfig.skills`.

## 5. Tests

1. Completed run produces session, candidates, and skill draft files.
2. Failed run produces no learning artifacts.
3. `review.json` records `pending` status.

Verification: `python -m pytest tests/unit -v`

Last known result:

```text
43 passed
```

## 6. Handoff

After Phase 4, Phase 5 should add a local API and minimal Web UI to browse runs, artifacts, and pending drafts.
