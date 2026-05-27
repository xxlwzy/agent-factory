from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse


def resolve_workspace_path(path: str, workspace_root: Path) -> Path:
    return _resolve_against_workspace(path, workspace_root)


def is_path_inside_any_sandbox(target: str, sandbox_paths: tuple[str, ...], workspace_root: Path) -> bool:
    target_path = _resolve_against_workspace(target, workspace_root)
    for sandbox_path in sandbox_paths:
        allowed_path = _resolve_against_workspace(sandbox_path, workspace_root)
        try:
            target_path.relative_to(allowed_path)
            return True
        except ValueError:
            continue
    return False


def is_domain_allowed(target: str, allowed_domains: tuple[str, ...]) -> bool:
    hostname = urlparse(target).hostname
    if not hostname:
        return False
    return hostname in allowed_domains


def _resolve_against_workspace(path: str, workspace_root: Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = workspace_root / candidate
    return candidate.resolve()
