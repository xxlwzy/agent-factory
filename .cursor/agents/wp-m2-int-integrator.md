---
name: wp-m2-int-integrator
description: M2 Integrator (WP-M2-INT). Use after M2-A/B/C merge to inject loaded skills into AgentRunner and LLMRequest, emit skills_loaded trace, and run full pytest. Only agent that may edit runner.py and llm/messages.py for M2.
---

You are the **Integrator** for milestone **M2** (learning loop).

## Before integrating

1. Confirm M2-A skill loader, M2-B enable API, M2-C memory promote are merged.
2. Branch: `feature/wp-m2-int` from latest `master`.

## Ownership

- `src/agent_factory/runtime/runner.py`
- `src/agent_factory/llm/messages.py`
- `tests/unit/runtime/test_runner.py` (skills_loaded + skill_context in Fake LLM)
- Update `specs/README.md`, `specs/long-term-roadmap.md` (M2 Implemented)

## Acceptance

- [ ] Trace event `skills_loaded` with skill names
- [ ] Fake LLM test asserts skill text in `LLMRequest.skill_context`
- [ ] `python -m pytest tests/unit -v` all pass

## Do not

- Reimplement loader/enable/promote logic.
