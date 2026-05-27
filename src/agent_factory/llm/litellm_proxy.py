from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from agent_factory.llm.litellm_env import resolve_litellm_api_key
from agent_factory.llm.messages import FinalResponse, LLMRequest, LLMResponse, ToolCallResponse
from agent_factory.llm.tool_calls import tool_call_from_openai_message
from agent_factory.llm.model_priority import resolve_litellm_model_candidates

_PROXY_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "http_get",
            "description": "Fetch a web page with HTTP GET.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "Full HTTP or HTTPS URL"}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "filesystem_write",
            "description": "Write UTF-8 Markdown report content to a sandbox file path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path"},
                    "content": {"type": "string", "description": "Full file contents"},
                },
                "required": ["path", "content"],
            },
        },
    },
]


class LiteLLMProxyAdapter:
    def __init__(
        self,
        *,
        models: str | tuple[str, ...] | list[str],
        system_prompt: str,
        source_url: str,
        report_path: str,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 120.0,
    ) -> None:
        if isinstance(models, str):
            self._models = [models]
        else:
            self._models = [model for model in models if model]
        if not self._models:
            raise ValueError("At least one LiteLLM proxy model is required.")
        self._model_index = 0
        self._models_attempted: list[str] = []
        self._base_url = (base_url or os.environ.get("LITELLM_PROXY_BASE_URL", "http://127.0.0.1:4000/v1")).rstrip(
            "/"
        )
        self._api_key = resolve_litellm_api_key(api_key)
        self._timeout_seconds = timeout_seconds
        self._recorded_tool_messages = 0
        self._messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": _build_system_prompt(system_prompt, source_url, report_path),
            },
        ]

    def next_response(self, request: LLMRequest) -> LLMResponse:
        if len(self._messages) == 1:
            self._messages.append({"role": "user", "content": request.task})
        self._append_tool_messages(request.messages)
        return self._complete_turn(self._chat_payload())

    def _append_tool_messages(self, messages: tuple[str, ...]) -> None:
        while self._recorded_tool_messages < len(messages):
            tool_message = messages[self._recorded_tool_messages]
            self._messages.append({"role": "user", "content": f"Tool output:\n{tool_message}"})
            self._recorded_tool_messages += 1

    @property
    def active_model(self) -> str:
        return self._models[self._model_index]

    def _chat_payload(self) -> dict[str, Any]:
        return {
            "model": self.active_model,
            "messages": self._messages,
            "tools": _PROXY_TOOLS,
            "tool_choice": "auto",
            "max_tokens": 4096,
        }

    def _complete_turn(self, payload: dict[str, Any]) -> LLMResponse:
        errors: list[str] = []
        for index in range(self._model_index, len(self._models)):
            model = self._models[index]
            self._models_attempted.append(model)
            attempt_payload = {**payload, "model": model}
            try:
                data = self._request_chat_completions(attempt_payload)
                response = self._parse_response(data)
            except RuntimeError as error:
                errors.append(str(error))
                continue
            self._model_index = index
            return response
        if errors:
            attempted = ", ".join(self._models_attempted)
            raise RuntimeError(
                "All LiteLLM proxy models failed. "
                f"Attempted: {attempted}. Last error: {errors[-1]}"
            )
        raise RuntimeError("No LiteLLM proxy models configured.")

    def _request_chat_completions(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}/chat/completions"
        body = json.dumps(payload).encode("utf-8")
        http_request = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(http_request, timeout=self._timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            model = payload.get("model", "?")
            raise RuntimeError(
                f"LiteLLM proxy request failed for model '{model}' ({error.code}): {detail}"
            ) from error

    def _parse_response(self, data: dict[str, Any]) -> LLMResponse:
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError(f"Unexpected LiteLLM proxy response: {data!r}") from error

        tool_calls = message.get("tool_calls") or []
        content = (message.get("content") or "").strip()
        if not tool_calls and not content:
            model = data.get("model", self.active_model)
            raise RuntimeError(
                f"LiteLLM proxy model '{model}' returned empty content without tool calls."
            )

        self._messages.append(message)
        if tool_calls:
            return tool_call_from_openai_message(tool_calls[0])
        return FinalResponse(content=content)


def litellm_proxy_adapter_from_env(
    *,
    system_prompt: str,
    source_url: str,
    report_path: str,
    model: str | None = None,
) -> LiteLLMProxyAdapter:
    from agent_factory.llm.litellm_env import ensure_litellm_proxy_env

    ensure_litellm_proxy_env()
    models = resolve_litellm_model_candidates(model)
    return LiteLLMProxyAdapter(
        models=models,
        system_prompt=system_prompt,
        source_url=source_url,
        report_path=report_path,
    )


def _build_system_prompt(system_prompt: str, source_url: str, report_path: str) -> str:
    return (
        f"{system_prompt.strip()}\n\n"
        "You are running inside Agent Factory. Complete the user task using tools:\n"
        "1. Call http_get with the source URL to fetch page content.\n"
        f"2. Call filesystem_write to save a concise Markdown report to exactly: {report_path}\n"
        "3. After the report is written, reply with a short completion message (no further tools).\n\n"
        f"Source URL: {source_url}\n"
        f"Report path: {report_path}\n"
    )


