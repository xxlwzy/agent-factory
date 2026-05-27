from agent_factory.config.schema import (
    AgentConfig,
    AgentFactoryConfig,
    MetaConfig,
    PermissionsConfig,
    RuntimeConfig,
    ToolConfig,
)
from agent_factory.llm.tool_schemas import openai_tools_for_config


def test_openai_tools_reflect_enabled_capabilities() -> None:
    config = AgentFactoryConfig(
        meta=MetaConfig(name="demo"),
        agent=AgentConfig(role="r", model="fake", system_prompt="x"),
        runtime=RuntimeConfig(),
        tools={
            "filesystem": ToolConfig(enabled=True),
            "http": ToolConfig(enabled=True),
            "terminal": ToolConfig(enabled=False),
        },
        permissions=PermissionsConfig(),
    )

    names = {tool["function"]["name"] for tool in openai_tools_for_config(config)}

    assert names == {"http_get", "filesystem_read", "filesystem_write"}
