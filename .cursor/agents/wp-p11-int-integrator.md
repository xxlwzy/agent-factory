---
name: wp-p11-int-integrator
description: Phase 11 integrator WP-P11-INT. Use after P11-D/E/F/G merge to wire run_chat, routing resolver, and full pytest suite.
---

**Integrator only** for Phase 11.

**Own:** `runtime/chat.py`, `routing/resolver.py`, `tests/unit/runtime/test_chat_scenario.py`

**Depends:** P11-D, E, F, G merged to master.

**Done when:** existing chat tests + new scenario/multi-scenario tests pass; `python -m pytest tests/unit -v`.
