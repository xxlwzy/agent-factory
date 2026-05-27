from __future__ import annotations

import json
import os
import urllib.error
from pathlib import Path
import urllib.request
from typing import Any, Protocol

from agent_factory.config.catalog import FALLBACK_AGENT, AgentCatalog
from agent_factory.llm.litellm_env import ensure_litellm_proxy_env, resolve_litellm_api_key
from agent_factory.llm.model_priority import resolve_litellm_model_candidates
from agent_factory.routing.decision import RoutingDecision


class RoutingResolver(Protocol):
    def resolve(self, message: str, catalog: AgentCatalog) -> RoutingDecision: ...


class RuleBasedRoutingResolver:
    """Deterministic router for tests and offline use."""

    def resolve(self, message: str, catalog: AgentCatalog) -> RoutingDecision:
        lowered = message.lower()
        for entry in catalog.list_routable():
            if entry.name == "web_researcher" and any(
                token in lowered for token in ("http://", "https://", "example.com", "网页", "总结", "research")
            ):
                return RoutingDecision(
                    target_agent=entry.name,
                    delegated_task=message,
                    reason="Matched web research keywords.",
                )
        return RoutingDecision(
            target_agent=FALLBACK_AGENT,
            delegated_task=message,
            reason="No specialist keyword match; using general assistant.",
        )


class LiteLLMRoutingResolver:
    def __init__(
        self,
        *,
        system_prompt: str,
        models: str | tuple[str, ...] | list[str] | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 60.0,
    ) -> None:
        ensure_litellm_proxy_env()
        if isinstance(models, str) or models is None:
            resolved = resolve_litellm_model_candidates(models)
        else:
            resolved = tuple(models)
        self._models = list(resolved)
        self._system_prompt = system_prompt
        self._base_url = (base_url or os.environ.get("LITELLM_PROXY_BASE_URL", "http://127.0.0.1:4000/v1")).rstrip(
            "/"
        )
        self._api_key = resolve_litellm_api_key(api_key)
        self._timeout_seconds = timeout_seconds

    def resolve(self, message: str, catalog: AgentCatalog) -> RoutingDecision:
        payload = {
            "model": self._models[0],
            "messages": [
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": f"{catalog.format_for_router_prompt()}\n\nUser message:\n{message}"},
            ],
            "tools": [_DELEGATE_TOOL],
            "tool_choice": {"type": "function", "function": {"name": "delegate_to_agent"}},
            "max_tokens": 1024,
        }
        errors: list[str] = []
        for model in self._models:
            attempt = {**payload, "model": model}
            try:
                data = self._post(attempt)
                return _routing_from_response(data, catalog)
            except RuntimeError as error:
                errors.append(str(error))
        raise RuntimeError(errors[-1] if errors else "Routing failed.")

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self._base_url}/chat/completions",
            data=body,
            headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Routing LLM failed ({error.code}): {detail}") from error


_DELEGATE_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "delegate_to_agent",
        "description": "Delegate the user request to a specialist or general assistant agent.",
        "parameters": {
            "type": "object",
            "properties": {
                "agent_name": {"type": "string", "description": "Target agent name from the catalog"},
                "task": {"type": "string", "description": "Task for the delegated agent"},
                "reason": {"type": "string", "description": "Why this agent was chosen"},
            },
            "required": ["agent_name", "task", "reason"],
        },
    },
}


def _routing_from_response(data: dict[str, Any], catalog: AgentCatalog) -> RoutingDecision:
    message = data["choices"][0]["message"]
    tool_calls = message.get("tool_calls") or []
    if tool_calls:
        arguments = json.loads(tool_calls[0]["function"]["arguments"])
        agent_name = str(arguments.get("agent_name", "")).strip()
        task = str(arguments.get("task", "")).strip()
        reason = str(arguments.get("reason", "")).strip() or "Routed by LLM."
        if not agent_name or not task:
            raise RuntimeError("delegate_to_agent missing agent_name or task.")
        return _normalize_decision(agent_name, task, reason, catalog)

    content = (message.get("content") or "").strip()
    if content:
        return _normalize_decision(FALLBACK_AGENT, content, "Router returned text; using general assistant.", catalog)
    raise RuntimeError("Router returned empty response.")


def _normalize_decision(agent_name: str, task: str, reason: str, catalog: AgentCatalog) -> RoutingDecision:
    routable = {entry.name for entry in catalog.list_routable()}
    target = agent_name if agent_name in routable or agent_name == FALLBACK_AGENT else FALLBACK_AGENT
    if target != agent_name:
        reason = f"{reason} (unknown agent {agent_name!r}, fallback to {target})"
    return RoutingDecision(target_agent=target, delegated_task=task, reason=reason)


def load_router_system_prompt(router_config_path: Path) -> str:
    from agent_factory.config.loader import load_agent_config

    config = load_agent_config(router_config_path)
    return (
        f"{config.agent.system_prompt.strip()}\n\n"
        "Call delegate_to_agent exactly once with the best specialist or general_assistant."
    )
