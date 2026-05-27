from __future__ import annotations

import os
from pathlib import Path


def ensure_litellm_proxy_env() -> None:
    """Load sibling ``litellm-proxy/.env`` when proxy credentials are not set."""
    if _proxy_credentials_configured():
        return

    for env_path in _litellm_env_candidates():
        if env_path.is_file():
            _load_dotenv(env_path)
            return


def resolve_litellm_api_key(explicit_api_key: str | None = None) -> str:
    ensure_litellm_proxy_env()
    api_key = (
        explicit_api_key
        or os.environ.get("LITELLM_PROXY_API_KEY")
        or os.environ.get("LITELLM_MASTER_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or "sk-local"
    ).strip()
    return api_key or "sk-local"


def _proxy_credentials_configured() -> bool:
    for name in ("LITELLM_PROXY_API_KEY", "LITELLM_MASTER_KEY", "OPENAI_API_KEY"):
        if os.environ.get(name, "").strip():
            return True
    return False


def _litellm_env_candidates() -> tuple[Path, ...]:
    repo_root = Path(__file__).resolve().parents[3]
    return (
        repo_root.parent / "litellm-proxy" / ".env",
        Path.cwd() / ".." / "litellm-proxy" / ".env",
    )


def _load_dotenv(path: Path) -> None:
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)
