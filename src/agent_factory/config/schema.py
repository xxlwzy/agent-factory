from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MetaConfig:
    name: str
    version: str = "0.1"
    description: str = ""
    owner: str = ""


@dataclass(frozen=True)
class AgentConfig:
    role: str
    model: str
    system_prompt: str


@dataclass(frozen=True)
class RuntimeConfig:
    max_turns: int = 20
    working_dir: str = "."
    output_dir: str = ".agent-factory/runs"
    trace_level: str = "standard"


@dataclass(frozen=True)
class ToolConfig:
    enabled: bool = False


@dataclass(frozen=True)
class SandboxConfig:
    paths: tuple[str, ...] = ()
    domains: tuple[str, ...] = ()


@dataclass(frozen=True)
class PermissionsConfig:
    sandbox: SandboxConfig = field(default_factory=SandboxConfig)
    confirm: tuple[str, ...] = ()
    deny: tuple[str, ...] = ()


@dataclass(frozen=True)
class MemoryConfig:
    session_path: str = ".agent-factory/memory/session"
    project_path: str = ".agent-factory/memory/project"
    user_path: str = ".agent-factory/memory/user"


@dataclass(frozen=True)
class SkillsConfig:
    enabled: tuple[str, ...] = ()
    draft_output_dir: str = ".agent-factory/skills/drafts"


@dataclass(frozen=True)
class HookEntry:
    command: tuple[str, ...]


@dataclass(frozen=True)
class HooksConfig:
    pre_tool_use: tuple[HookEntry, ...] = ()
    post_tool_use: tuple[HookEntry, ...] = ()
    run_completed: tuple[HookEntry, ...] = ()


@dataclass(frozen=True)
class ScheduleConfig:
    name: str
    interval_seconds: int
    task: str


@dataclass(frozen=True)
class AutomationConfig:
    schedules: tuple[ScheduleConfig, ...] = ()


@dataclass(frozen=True)
class McpToolDescriptor:
    name: str
    description: str = ""
    operation: str = "invoke"


@dataclass(frozen=True)
class McpConfig:
    tools: tuple[McpToolDescriptor, ...] = ()


@dataclass(frozen=True)
class AgentFactoryConfig:
    meta: MetaConfig
    agent: AgentConfig
    runtime: RuntimeConfig
    tools: dict[str, ToolConfig]
    permissions: PermissionsConfig
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    skills: SkillsConfig = field(default_factory=SkillsConfig)
    hooks: HooksConfig = field(default_factory=HooksConfig)
    automation: AutomationConfig = field(default_factory=AutomationConfig)
    mcp: McpConfig = field(default_factory=McpConfig)
    unsupported_warnings: tuple[str, ...] = ()
