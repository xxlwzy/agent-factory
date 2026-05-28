---
name: wp-p11-f-general-fallback
description: Phase 11 WP-P11-F. Use proactively for Router fallback to general_assistant and honest out-of-scope decline replies.
---

Implement **WP-P11-F** (parallel with P11-A/B).

**Own:** `configs/agents/general_assistant.yaml`, `tests/unit/routing/test_general_fallback.py`

**Requirements:**
- Router fallback decision → `general_assistant`
- Impossible task → user-visible「做不到」; no tool_executed

**Do not:** Change team orchestrator.
