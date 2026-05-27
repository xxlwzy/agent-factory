from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from agent_factory.config.schema import AgentFactoryConfig
from agent_factory.llm.litellm_env import ensure_litellm_proxy_env, resolve_litellm_api_key
from agent_factory.llm.messages import FinalResponse, LLMRequest, LLMResponse
from agent_factory.llm.model_priority import resolve_litellm_model_candidates
from agent_factory.llm.tool_calls import tool_call_from_openai_message
from agent_factory.llm.tool_schemas import openai_tools_for_config


class ConfigDrivenLiteLLMAdapter:
    def __init__(
        self,
        config: AgentFactoryConfig,
        *,
        models: str | tuple[str, ...] | list[str] | None = None,
        extra_system_prompt: str = "",
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 120.0,
    ) -> None:
        if isinstance(models, str) or models is None:
            self._models = list(resolve_litellm_model_candidates(models))
        else:
            self._models = [model for model in models if model]
        self._tools = openai_tools_for_config(config)
        self._base_url = (base_url or os.environ.get("LITELLM_PROXY_BASE_URL", "http://127.0.0.1:4000/v1")).rstrip(
            "/"
        )
        self._api_key = resolve_litellm_api_key(api_key)
        self._timeout_seconds = timeout_seconds
        self._recorded_tool_messages = 0
        system = config.agent.system_prompt.strip()
        if extra_system_prompt:
            system = f"{system}\n\n{extra_system_prompt.strip()}"
        if self._tools:
            system = (
                f"{system}\n\nUse the provided tools when needed. "
                "When the task is complete, reply with a concise final answer to the user."
            )
        self._messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
        self._model_index = 0
        self._models_attempted: list[str] = []

    @property
    def active_model(self) -> str:
        return self._models[self._model_index]

    def next_response(self, request: LLMRequest) -> LLMResponse:
        if len(self._messages) == 1:
            for turn in request.history:
                if turn.role in ("user", "assistant"):
                    self._messages.append({"role": turn.role, "content": turn.content})
            self._messages.append({"role": "user", "content": request.task})
        self._append_tool_messages(request.messages)
        return self._complete_turn()

    def _append_tool_messages(self, messages: tuple[str, ...]) -> None:
        while self._recorded_tool_messages < len(messages):
            tool_message = messages[self._recorded_tool_messages]
            self._messages.append({"role": "user", "content": f"Tool output:\n{tool_message}"})
            self._recorded_tool_messages += 1

    def _complete_turn(self) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self.active_model,
            "messages": self._messages,
            "max_tokens": 4096,
        }
        if self._tools:
            payload["tools"] = self._tools
            payload["tool_choice"] = "auto"

        errors: list[str] = []
        for index in range(self._model_index, len(self._models)):
            model = self._models[index]
            self._models_attempted.append(model)
            attempt = {**payload, "model": model}
            try:
                data = self._post(attempt)
                response = self._parse_response(data)
            except RuntimeError as error:
                errors.append(str(error))
                continue
            self._model_index = index
            return response
        raise RuntimeError(errors[-1] if errors else "LLM request failed.")

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
            raise RuntimeError(
                f"LiteLLM proxy request failed for model '{payload.get('model')}' ({error.code}): {detail}"
            ) from error

    def _parse_response(self, data: dict[str, Any]) -> LLMResponse:
        message = data["choices"][0]["message"]
        tool_calls = message.get("tool_calls") or []
        content = (message.get("content") or "").strip()
        if not tool_calls and not content:
            raise RuntimeError("LLM returned empty content without tool calls.")
        self._messages.append(message)
        if tool_calls:
            return tool_call_from_openai_message(tool_calls[0])
        return FinalResponse(content=content)


def config_litellm_adapter_from_env(
    config: AgentFactoryConfig,
    *,
    model: str | None = None,
    extra_system_prompt: str = "",
) -> ConfigDrivenLiteLLMAdapter:
    ensure_litellm_proxy_env()
    return ConfigDrivenLiteLLMAdapter(
        config,
        models=model,
        extra_system_prompt=extra_system_prompt,
    )
