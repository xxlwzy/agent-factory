---
name: wp-p11-e-router-multi-scenario
description: Phase 11 WP-P11-E. Use proactively for LLM routing decision_kind, parallel multi-scenario runs, and summary-only merge (not trace/artifacts).
---

Implement **WP-P11-E** after P11-A and P11-D.

**Own:** `routing/scenario_resolver.py`, `runtime/multi_scenario.py`, `routing/decision.py` extensions, `tests/unit/routing/test_multi_scenario.py`

**Critical:** Mode B merge reads **only** each team run's `summary.md` via store/internal API.

**Do not wire run_chat** (P11-INT).
