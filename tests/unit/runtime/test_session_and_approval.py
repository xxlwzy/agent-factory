from pathlib import Path

from agent_factory.config.schema import (
    AgentConfig,
    AgentFactoryConfig,
    MetaConfig,
    PermissionsConfig,
    RuntimeConfig,
    SandboxConfig,
    ToolConfig,
)
from agent_factory.llm.fake import FakeLLMAdapter
from agent_factory.llm.messages import FinalResponse, ToolCallResponse
from agent_factory.runtime.approvals import ApprovalStore
from agent_factory.runtime.chat import resolve_approval, run_chat
from agent_factory.runtime.session_store import ChatSessionStore
from agent_factory.runtime.states import RunStatus
from agent_factory.routing.resolver import RuleBasedRoutingResolver


def test_run_chat_persists_session_across_turns(tmp_path: Path) -> None:
    agents_dir = _agents_dir(tmp_path)
    first = run_chat(
        "hello",
        workspace_root=tmp_path,
        agents_dir=agents_dir,
        routing_resolver=RuleBasedRoutingResolver(),
        specialist_llm=FakeLLMAdapter([FinalResponse(content="first reply")]),
    )
    second = run_chat(
        "follow up",
        workspace_root=tmp_path,
        agents_dir=agents_dir,
        session_id=first.session_id,
        routing_resolver=RuleBasedRoutingResolver(),
        specialist_llm=FakeLLMAdapter([FinalResponse(content="second reply")]),
    )

    session = ChatSessionStore(tmp_path).load(first.session_id)
    assert len(session.turns) == 4
    assert session.turns[-1]["content"] == "second reply"


def test_resolve_approval_after_confirm(tmp_path: Path) -> None:
    agents_dir = _agents_dir(tmp_path)
    confirm_config_path = agents_dir / "confirm_agent.yaml"
    allowed = tmp_path / "data"
    allowed.mkdir()
    target = str(allowed / "out.txt")
    confirm_config_path.write_text(
        "meta:\n  name: confirm_agent\n  description: confirm\n"
        "agent:\n  role: C\n  model: fake\n  system_prompt: test\n"
        "tools:\n  filesystem:\n    enabled: true\npermissions:\n  sandbox:\n    paths: [.]\n  confirm:\n    - filesystem.write\n",
        encoding="utf-8",
    )

    class _ConfirmRouter(RuleBasedRoutingResolver):
        def resolve(self, message, catalog):
            from agent_factory.routing.decision import RoutingDecision

            return RoutingDecision(
                target_agent="confirm_agent",
                delegated_task=message,
                reason="test",
            )

    blocked = run_chat(
        "post it",
        workspace_root=tmp_path,
        agents_dir=agents_dir,
        routing_resolver=_ConfirmRouter(),
        specialist_llm=FakeLLMAdapter(
            [ToolCallResponse(tool="filesystem", operation="write", target=target, content="secret")]
        ),
    )
    assert blocked.status == RunStatus.AWAITING_CONFIRM
    assert blocked.approval_id

    approved = resolve_approval(
        blocked.approval_id,
        approved=True,
        workspace_root=tmp_path,
        agents_dir=agents_dir,
        specialist_llm=FakeLLMAdapter([FinalResponse(content="approved reply")]),
    )
    assert approved.status == RunStatus.COMPLETED
    assert ApprovalStore(tmp_path).load(blocked.approval_id).status == "approved"


def _agents_dir(tmp_path: Path) -> Path:
    agents_dir = tmp_path / "configs" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "general_assistant.yaml").write_text(
        "meta:\n  name: general_assistant\n  description: General\n"
        "agent:\n  role: General\n  model: fake\n  system_prompt: test\n"
        "tools:\n  filesystem:\n    enabled: true\n  http:\n    enabled: true\n"
        "permissions:\n  sandbox:\n    paths: [.]\n    domains: [example.com]\n",
        encoding="utf-8",
    )
    return agents_dir
