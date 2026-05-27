import pytest

from agent_factory.llm.model_priority import (
    DEFAULT_LITELLM_MODEL_PRIORITY,
    resolve_litellm_model_candidates,
)


def test_default_priority_prefers_mimo_then_modelscope_then_onehub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("LITELLM_MODEL", raising=False)
    monkeypatch.delenv("LITELLM_MODEL_PRIORITY", raising=False)
    models = resolve_litellm_model_candidates()

    assert models[0].startswith("mimo/")
    assert any(model.startswith("ms/") for model in models)
    assert any(model.startswith("onehub/") for model in models)
    assert models.index(next(m for m in models if m.startswith("ms/"))) < models.index(
        next(m for m in models if m.startswith("onehub/"))
    )
    assert models == DEFAULT_LITELLM_MODEL_PRIORITY


def test_explicit_model_overrides_defaults() -> None:
    assert resolve_litellm_model_candidates("onehub/gpt-5.4") == ("onehub/gpt-5.4",)


def test_openai_model_env_overrides_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_MODEL", "ms/glm-5.1")
    monkeypatch.delenv("LITELLM_MODEL", raising=False)

    assert resolve_litellm_model_candidates() == ("ms/glm-5.1",)


def test_litellm_model_priority_env_overrides_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("LITELLM_MODEL", raising=False)
    monkeypatch.setenv("LITELLM_MODEL_PRIORITY", "mimo/mimo-v2.5, ms/deepseek-v4")

    assert resolve_litellm_model_candidates() == ("mimo/mimo-v2.5", "ms/deepseek-v4")
