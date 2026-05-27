import pytest

from agent_factory.llm.fake import FakeLLMAdapter
from agent_factory.llm.messages import FinalResponse, LLMRequest, ToolCallResponse


def test_fake_adapter_returns_scripted_responses_in_order() -> None:
    adapter = FakeLLMAdapter(
        responses=[
            ToolCallResponse(tool="filesystem", operation="write", target="report.md"),
            FinalResponse(content="done"),
        ]
    )

    first = adapter.next_response(LLMRequest(task="write a report", messages=()))
    second = adapter.next_response(LLMRequest(task="write a report", messages=()))

    assert first == ToolCallResponse(tool="filesystem", operation="write", target="report.md")
    assert second == FinalResponse(content="done")


def test_fake_adapter_raises_when_script_is_exhausted() -> None:
    adapter = FakeLLMAdapter(responses=[])

    with pytest.raises(RuntimeError, match="FakeLLMAdapter has no scripted responses left."):
        adapter.next_response(LLMRequest(task="write a report", messages=()))
