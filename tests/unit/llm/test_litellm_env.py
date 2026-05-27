import os
from pathlib import Path

import pytest

from agent_factory.llm.litellm_env import ensure_litellm_proxy_env, resolve_litellm_api_key


def test_resolve_litellm_api_key_defaults_to_sk_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LITELLM_PROXY_API_KEY", raising=False)
    monkeypatch.delenv("LITELLM_MASTER_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert resolve_litellm_api_key() == "sk-local"


def test_ensure_litellm_proxy_env_loads_sibling_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from agent_factory.llm import litellm_env

    env_file = tmp_path / "litellm-proxy" / ".env"
    env_file.parent.mkdir(parents=True)
    env_file.write_text("LITELLM_MASTER_KEY=sk-from-file\n", encoding="utf-8")

    monkeypatch.delenv("LITELLM_MASTER_KEY", raising=False)
    monkeypatch.delenv("LITELLM_PROXY_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(litellm_env, "_litellm_env_candidates", lambda: (env_file,))

    ensure_litellm_proxy_env()

    assert os.environ.get("LITELLM_MASTER_KEY") == "sk-from-file"
