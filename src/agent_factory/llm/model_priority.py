from __future__ import annotations

import os

# Default LiteLLM proxy model order: MiMo → ModelScope (ms/) → OneHub.
# Within each tier, earlier entries are preferred.
DEFAULT_LITELLM_MODEL_PRIORITY: tuple[str, ...] = (
    "mimo/mimo-v2.5-pro",
    "mimo/mimo-v2.5",
    "ms/deepseek-v4",
    "ms/glm-5.1",
    "onehub/qwen3.6-plus",
)


def resolve_litellm_model_candidates(explicit_model: str | None = None) -> tuple[str, ...]:
    """Resolve models to try, in order.

    Priority:
    1. Explicit ``explicit_model`` argument (CLI/API).
    2. ``OPENAI_MODEL`` or ``LITELLM_MODEL`` environment variable (single override).
    3. ``LITELLM_MODEL_PRIORITY`` comma-separated list.
    4. Built-in default priority (MiMo → ModelScope → OneHub).
    """
    if explicit_model and explicit_model.strip():
        return (explicit_model.strip(),)

    env_model = (os.environ.get("OPENAI_MODEL") or os.environ.get("LITELLM_MODEL") or "").strip()
    if env_model:
        return (env_model,)

    env_priority = os.environ.get("LITELLM_MODEL_PRIORITY", "").strip()
    if env_priority:
        models = tuple(part.strip() for part in env_priority.split(",") if part.strip())
        if models:
            return models

    return DEFAULT_LITELLM_MODEL_PRIORITY
