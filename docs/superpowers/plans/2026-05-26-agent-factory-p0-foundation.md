# Agent Factory P0 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first testable foundation for Agent Factory: Python package skeleton, YAML config parsing, unsupported field warnings, sandbox-first permission decisions, and JSONL run trace writing.

**Architecture:** Keep the runtime small and explicit. `config` turns YAML into typed dataclasses, `permissions` decides allow/confirm/deny before tools run, and `runtime.trace` records every important event to `.agent-factory/runs/<run_id>/trace.jsonl`. This plan intentionally does not implement real LLM calls, browser automation, team coordination, scheduler, hooks, or Web UI.

**Tech Stack:** Python 3.11+, `PyYAML`, `pytest`, stdlib `dataclasses`, `pathlib`, and `json`.

---

## File Structure

Create this initial subset of the design-doc directory structure:

```text
agent-factory/
  pyproject.toml
  README.md
  .gitignore
  configs/
    agents/
      web_researcher.yaml
    policies/
      default.yaml
  src/
    agent_factory/
      __init__.py
      config/
        __init__.py
        loader.py
        schema.py
        unsupported.py
      permissions/
        __init__.py
        guard.py
        policy.py
        sandbox.py
      runtime/
        __init__.py
        trace.py
  tests/
    unit/
      config/
        test_loader.py
      permissions/
        test_guard.py
      runtime/
        test_trace.py
```

Responsibilities:

- `src/agent_factory/config/schema.py`: dataclasses for the executable subset of `agent.yaml`.
- `src/agent_factory/config/unsupported.py`: known top-level schema fields and unsupported-field warning generation.
- `src/agent_factory/config/loader.py`: load YAML from disk, apply defaults, validate minimal required fields.
- `src/agent_factory/permissions/policy.py`: policy dataclasses and YAML loading helper.
- `src/agent_factory/permissions/sandbox.py`: path/domain operation helpers.
- `src/agent_factory/permissions/guard.py`: evaluate a requested tool action as `allow`, `confirm`, or `deny`.
- `src/agent_factory/runtime/trace.py`: append structured JSONL trace events.

## Task 1: Bootstrap Python Package

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `README.md`
- Create: `src/agent_factory/__init__.py`

- [ ] **Step 1: Create project metadata**

Create `pyproject.toml`:

```toml
[project]
name = "agent-factory"
version = "0.1.0"
description = "Local-first personal agent factory harness"
requires-python = ">=3.11"
dependencies = [
  "PyYAML>=6.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0",
]

[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [ ] **Step 2: Create repository ignore rules**

Create `.gitignore`:

```gitignore
.venv/
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
.agent-factory/
.superpowers/
```

- [ ] **Step 3: Create README**

Create `README.md`:

```markdown
# Agent Factory

Local-first personal agent factory harness.

The first milestone focuses on a single-agent vertical slice:

- Load an `agent.yaml`
- Enforce sandbox-first permissions
- Execute only enabled atomic capabilities
- Record run traces
- Generate reviewable learning artifacts in later milestones

See `docs/superpowers/specs/2026-05-26-agent-factory-design.md` for the design.
```

- [ ] **Step 4: Create package marker**

Create `src/agent_factory/__init__.py`:

```python
"""Local-first personal agent factory harness."""

__all__ = ["__version__"]

__version__ = "0.1.0"
```

- [ ] **Step 5: Verify package test command starts**

Run: `python -m pytest --version`

Expected: command exits 0 and prints a pytest version. If pytest is missing, run `python -m pip install -e ".[dev]"` first.

## Task 2: Agent YAML Config Loader

**Files:**
- Create: `src/agent_factory/config/__init__.py`
- Create: `src/agent_factory/config/schema.py`
- Create: `src/agent_factory/config/unsupported.py`
- Create: `src/agent_factory/config/loader.py`
- Create: `tests/unit/config/test_loader.py`
- Create: `configs/agents/web_researcher.yaml`

- [ ] **Step 1: Write failing config loader tests**

Create `tests/unit/config/test_loader.py`:

```python
from pathlib import Path

import pytest

from agent_factory.config.loader import load_agent_config


def test_loads_executable_agent_fields(tmp_path: Path) -> None:
    config_path = tmp_path / "agent.yaml"
    config_path.write_text(
        """
meta:
  name: web_researcher
  version: "0.1"
agent:
  role: Web research assistant
  model: fake-model
  system_prompt: Summarize web pages into Markdown.
runtime:
  max_turns: 12
  working_dir: ./workspace
  output_dir: ./outputs
tools:
  filesystem:
    enabled: true
  browser:
    enabled: true
permissions:
  sandbox:
    paths:
      - ./workspace
      - ./outputs
    domains:
      - example.com
""",
        encoding="utf-8",
    )

    config = load_agent_config(config_path)

    assert config.meta.name == "web_researcher"
    assert config.agent.role == "Web research assistant"
    assert config.runtime.max_turns == 12
    assert config.tools["filesystem"].enabled is True
    assert config.permissions.sandbox.paths == ("./workspace", "./outputs")
    assert config.unsupported_warnings == ()


def test_records_unsupported_top_level_sections(tmp_path: Path) -> None:
    config_path = tmp_path / "agent.yaml"
    config_path.write_text(
        """
meta:
  name: web_researcher
agent:
  role: Web research assistant
  model: fake-model
  system_prompt: Summarize web pages into Markdown.
tools:
  filesystem:
    enabled: true
permissions:
  sandbox:
    paths:
      - ./workspace
workflow:
  steps:
    - read_web
team:
  agents:
    - reviewer
""",
        encoding="utf-8",
    )

    config = load_agent_config(config_path)

    assert config.unsupported_warnings == (
        "Top-level section 'workflow' is recognized but mocked in MVP.",
        "Top-level section 'team' is recognized but mocked in MVP.",
    )


def test_missing_required_agent_section_fails(tmp_path: Path) -> None:
    config_path = tmp_path / "agent.yaml"
    config_path.write_text(
        """
meta:
  name: broken
tools:
  filesystem:
    enabled: true
permissions:
  sandbox:
    paths:
      - ./workspace
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Missing required section: agent"):
        load_agent_config(config_path)
```

- [ ] **Step 2: Run config tests and verify RED**

Run: `python -m pytest tests/unit/config/test_loader.py -v`

Expected: FAIL because `agent_factory.config.loader` does not exist.

- [ ] **Step 3: Implement config schema and loader**

Create `src/agent_factory/config/schema.py`:

```python
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
class AgentFactoryConfig:
    meta: MetaConfig
    agent: AgentConfig
    runtime: RuntimeConfig
    tools: dict[str, ToolConfig]
    permissions: PermissionsConfig
    unsupported_warnings: tuple[str, ...] = ()
```

Create `src/agent_factory/config/unsupported.py`:

```python
EXECUTABLE_TOP_LEVEL_SECTIONS = {
    "meta",
    "agent",
    "runtime",
    "tools",
    "permissions",
    "memory",
    "skills",
}

MOCKED_TOP_LEVEL_SECTIONS = {
    "workflow",
    "team",
    "automation",
    "hooks",
    "notifications",
}


def collect_unsupported_warnings(raw: dict[str, object]) -> tuple[str, ...]:
    warnings: list[str] = []
    for key in raw:
        if key in MOCKED_TOP_LEVEL_SECTIONS:
            warnings.append(f"Top-level section '{key}' is recognized but mocked in MVP.")
        elif key not in EXECUTABLE_TOP_LEVEL_SECTIONS:
            warnings.append(f"Top-level section '{key}' is not recognized by schema v1.")
    return tuple(warnings)
```

Create `src/agent_factory/config/loader.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from agent_factory.config.schema import (
    AgentConfig,
    AgentFactoryConfig,
    MetaConfig,
    PermissionsConfig,
    RuntimeConfig,
    SandboxConfig,
    ToolConfig,
)
from agent_factory.config.unsupported import collect_unsupported_warnings


def load_agent_config(path: str | Path) -> AgentFactoryConfig:
    config_path = Path(path)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("Agent config must be a YAML mapping.")

    _require_sections(raw, ("meta", "agent", "tools", "permissions"))

    return AgentFactoryConfig(
        meta=_parse_meta(_mapping(raw["meta"], "meta")),
        agent=_parse_agent(_mapping(raw["agent"], "agent")),
        runtime=_parse_runtime(_mapping(raw.get("runtime", {}), "runtime")),
        tools=_parse_tools(_mapping(raw["tools"], "tools")),
        permissions=_parse_permissions(_mapping(raw["permissions"], "permissions")),
        unsupported_warnings=collect_unsupported_warnings(raw),
    )


def _require_sections(raw: dict[str, Any], sections: tuple[str, ...]) -> None:
    for section in sections:
        if section not in raw:
            raise ValueError(f"Missing required section: {section}")


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"Section '{name}' must be a mapping.")
    return value


def _parse_meta(raw: dict[str, Any]) -> MetaConfig:
    name = str(raw.get("name", "")).strip()
    if not name:
        raise ValueError("meta.name is required.")
    return MetaConfig(
        name=name,
        version=str(raw.get("version", "0.1")),
        description=str(raw.get("description", "")),
        owner=str(raw.get("owner", "")),
    )


def _parse_agent(raw: dict[str, Any]) -> AgentConfig:
    role = str(raw.get("role", "")).strip()
    model = str(raw.get("model", "")).strip()
    system_prompt = str(raw.get("system_prompt", "")).strip()
    if not role:
        raise ValueError("agent.role is required.")
    if not model:
        raise ValueError("agent.model is required.")
    if not system_prompt:
        raise ValueError("agent.system_prompt is required.")
    return AgentConfig(role=role, model=model, system_prompt=system_prompt)


def _parse_runtime(raw: dict[str, Any]) -> RuntimeConfig:
    return RuntimeConfig(
        max_turns=int(raw.get("max_turns", 20)),
        working_dir=str(raw.get("working_dir", ".")),
        output_dir=str(raw.get("output_dir", ".agent-factory/runs")),
        trace_level=str(raw.get("trace_level", "standard")),
    )


def _parse_tools(raw: dict[str, Any]) -> dict[str, ToolConfig]:
    tools: dict[str, ToolConfig] = {}
    for name, value in raw.items():
        tool_raw = _mapping(value, f"tools.{name}")
        tools[str(name)] = ToolConfig(enabled=bool(tool_raw.get("enabled", False)))
    return tools


def _parse_permissions(raw: dict[str, Any]) -> PermissionsConfig:
    sandbox_raw = _mapping(raw.get("sandbox", {}), "permissions.sandbox")
    return PermissionsConfig(
        sandbox=SandboxConfig(
            paths=tuple(str(path) for path in sandbox_raw.get("paths", ())),
            domains=tuple(str(domain) for domain in sandbox_raw.get("domains", ())),
        ),
        confirm=tuple(str(rule) for rule in raw.get("confirm", ())),
        deny=tuple(str(rule) for rule in raw.get("deny", ())),
    )
```

Create `src/agent_factory/config/__init__.py`:

```python
from agent_factory.config.loader import load_agent_config
from agent_factory.config.schema import AgentFactoryConfig

__all__ = ["AgentFactoryConfig", "load_agent_config"]
```

- [ ] **Step 4: Add sample agent YAML**

Create `configs/agents/web_researcher.yaml`:

```yaml
meta:
  name: web_researcher
  version: "0.1"
  description: Reads web pages and writes Markdown summaries.
agent:
  role: Web research assistant
  model: fake-model
  system_prompt: |
    You read web content, extract key facts, and write concise Markdown reports.
runtime:
  max_turns: 12
  working_dir: .
  output_dir: .agent-factory/runs
tools:
  filesystem:
    enabled: true
  terminal:
    enabled: false
  browser:
    enabled: true
  http:
    enabled: true
permissions:
  sandbox:
    paths:
      - .
      - .agent-factory/runs
    domains:
      - example.com
workflow:
  mock: true
team:
  mock: true
```

- [ ] **Step 5: Run config tests and verify GREEN**

Run: `python -m pytest tests/unit/config/test_loader.py -v`

Expected: 5 passed.

## Task 3: Sandbox-First Permission Guard

**Files:**
- Create: `src/agent_factory/permissions/__init__.py`
- Create: `src/agent_factory/permissions/policy.py`
- Create: `src/agent_factory/permissions/sandbox.py`
- Create: `src/agent_factory/permissions/guard.py`
- Create: `tests/unit/permissions/test_guard.py`
- Create: `configs/policies/default.yaml`

- [ ] **Step 1: Write failing permission tests**

Create `tests/unit/permissions/test_guard.py`:

```python
from pathlib import Path

from agent_factory.config.schema import PermissionsConfig, SandboxConfig, ToolConfig
from agent_factory.permissions.guard import PermissionDecision, PermissionGuard, ToolRequest


def test_denies_disabled_tool(tmp_path: Path) -> None:
    guard = PermissionGuard(
        tools={"filesystem": ToolConfig(enabled=False)},
        permissions=PermissionsConfig(sandbox=SandboxConfig(paths=(str(tmp_path),))),
        workspace_root=tmp_path,
    )

    decision = guard.evaluate(ToolRequest(tool="filesystem", operation="read", target=str(tmp_path / "a.txt")))

    assert decision == PermissionDecision("deny", "Tool 'filesystem' is not enabled.")


def test_allows_filesystem_target_inside_sandbox(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    guard = PermissionGuard(
        tools={"filesystem": ToolConfig(enabled=True)},
        permissions=PermissionsConfig(sandbox=SandboxConfig(paths=(str(allowed),))),
        workspace_root=tmp_path,
    )

    decision = guard.evaluate(ToolRequest(tool="filesystem", operation="write", target=str(allowed / "report.md")))

    assert decision == PermissionDecision("allow", "Filesystem target is inside sandbox.")


def test_denies_filesystem_target_outside_sandbox(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    guard = PermissionGuard(
        tools={"filesystem": ToolConfig(enabled=True)},
        permissions=PermissionsConfig(sandbox=SandboxConfig(paths=(str(allowed),))),
        workspace_root=tmp_path,
    )

    decision = guard.evaluate(ToolRequest(tool="filesystem", operation="write", target=str(outside / "report.md")))

    assert decision == PermissionDecision("deny", "Filesystem target is outside sandbox.")


def test_confirms_http_write_to_allowed_domain(tmp_path: Path) -> None:
    guard = PermissionGuard(
        tools={"http": ToolConfig(enabled=True)},
        permissions=PermissionsConfig(sandbox=SandboxConfig(domains=("api.example.com",))),
        workspace_root=tmp_path,
    )

    decision = guard.evaluate(ToolRequest(tool="http", operation="POST", target="https://api.example.com/items"))

    assert decision == PermissionDecision("confirm", "HTTP write operation requires confirmation.")


def test_denies_http_domain_outside_allowlist(tmp_path: Path) -> None:
    guard = PermissionGuard(
        tools={"http": ToolConfig(enabled=True)},
        permissions=PermissionsConfig(sandbox=SandboxConfig(domains=("example.com",))),
        workspace_root=tmp_path,
    )

    decision = guard.evaluate(ToolRequest(tool="http", operation="GET", target="https://evil.test/data"))

    assert decision == PermissionDecision("deny", "HTTP target domain is outside allowlist.")
```

- [ ] **Step 2: Run permission tests and verify RED**

Run: `python -m pytest tests/unit/permissions/test_guard.py -v`

Expected: FAIL because `agent_factory.permissions.guard` does not exist.

- [ ] **Step 3: Implement permission guard**

Create `src/agent_factory/permissions/sandbox.py`:

```python
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse


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
```

Create `src/agent_factory/permissions/guard.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_factory.config.schema import PermissionsConfig, ToolConfig
from agent_factory.permissions.sandbox import is_domain_allowed, is_path_inside_any_sandbox


@dataclass(frozen=True)
class ToolRequest:
    tool: str
    operation: str
    target: str


@dataclass(frozen=True)
class PermissionDecision:
    action: str
    reason: str


class PermissionGuard:
    def __init__(
        self,
        tools: dict[str, ToolConfig],
        permissions: PermissionsConfig,
        workspace_root: str | Path,
    ) -> None:
        self._tools = tools
        self._permissions = permissions
        self._workspace_root = Path(workspace_root).resolve()

    def evaluate(self, request: ToolRequest) -> PermissionDecision:
        tool_config = self._tools.get(request.tool)
        if tool_config is None or not tool_config.enabled:
            return PermissionDecision("deny", f"Tool '{request.tool}' is not enabled.")

        if request.tool == "filesystem":
            return self._evaluate_filesystem(request)

        if request.tool == "http":
            return self._evaluate_http(request)

        return PermissionDecision("confirm", f"Tool '{request.tool}' requires confirmation in MVP.")

    def _evaluate_filesystem(self, request: ToolRequest) -> PermissionDecision:
        if is_path_inside_any_sandbox(
            request.target,
            self._permissions.sandbox.paths,
            self._workspace_root,
        ):
            return PermissionDecision("allow", "Filesystem target is inside sandbox.")
        return PermissionDecision("deny", "Filesystem target is outside sandbox.")

    def _evaluate_http(self, request: ToolRequest) -> PermissionDecision:
        if not is_domain_allowed(request.target, self._permissions.sandbox.domains):
            return PermissionDecision("deny", "HTTP target domain is outside allowlist.")
        if request.operation.upper() != "GET":
            return PermissionDecision("confirm", "HTTP write operation requires confirmation.")
        return PermissionDecision("allow", "HTTP GET target domain is allowed.")
```

Create `src/agent_factory/permissions/policy.py`:

```python
from agent_factory.config.schema import PermissionsConfig

__all__ = ["PermissionsConfig"]
```

Create `src/agent_factory/permissions/__init__.py`:

```python
from agent_factory.permissions.guard import PermissionDecision, PermissionGuard, ToolRequest

__all__ = ["PermissionDecision", "PermissionGuard", "ToolRequest"]
```

- [ ] **Step 4: Add default policy YAML**

Create `configs/policies/default.yaml`:

```yaml
permissions:
  sandbox:
    paths:
      - .
      - .agent-factory/runs
    domains:
      - example.com
  confirm:
    - browser.submit
    - http.write
  deny:
    - terminal.dangerous
```

- [ ] **Step 5: Run permission tests and verify GREEN**

Run: `python -m pytest tests/unit/permissions/test_guard.py -v`

Expected: 7 passed.

## Task 4: JSONL Run Trace Writer

**Files:**
- Create: `src/agent_factory/runtime/__init__.py`
- Create: `src/agent_factory/runtime/trace.py`
- Create: `tests/unit/runtime/test_trace.py`

- [ ] **Step 1: Write failing trace tests**

Create `tests/unit/runtime/test_trace.py`:

```python
import json
from pathlib import Path

from agent_factory.runtime.trace import RunTrace


def test_appends_jsonl_trace_events(tmp_path: Path) -> None:
    trace = RunTrace(run_dir=tmp_path / "run-1")

    trace.append("permission_decision", {"action": "allow", "reason": "inside sandbox"})
    trace.append("tool_result", {"tool": "filesystem", "ok": True})

    lines = (tmp_path / "run-1" / "trace.jsonl").read_text(encoding="utf-8").splitlines()

    first = json.loads(lines[0])
    second = json.loads(lines[1])
    assert first["type"] == "permission_decision"
    assert first["data"] == {"action": "allow", "reason": "inside sandbox"}
    assert second["type"] == "tool_result"
    assert second["data"] == {"tool": "filesystem", "ok": True}
    assert "timestamp" in first


def test_writes_summary_markdown(tmp_path: Path) -> None:
    trace = RunTrace(run_dir=tmp_path / "run-1")

    trace.write_summary("# Summary\n\nTask completed.")

    assert (tmp_path / "run-1" / "summary.md").read_text(encoding="utf-8") == "# Summary\n\nTask completed."
```

- [ ] **Step 2: Run trace tests and verify RED**

Run: `python -m pytest tests/unit/runtime/test_trace.py -v`

Expected: FAIL because `agent_factory.runtime.trace` does not exist.

- [ ] **Step 3: Implement trace writer**

Create `src/agent_factory/runtime/trace.py`:

```python
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class RunTrace:
    def __init__(self, run_dir: str | Path) -> None:
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.trace_path = self.run_dir / "trace.jsonl"

    def append(self, event_type: str, data: dict[str, Any]) -> None:
        event = {
            "timestamp": datetime.now(UTC).isoformat(),
            "type": event_type,
            "data": data,
        }
        with self.trace_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=True) + "\n")

    def write_summary(self, content: str) -> None:
        (self.run_dir / "summary.md").write_text(content, encoding="utf-8")
```

Create `src/agent_factory/runtime/__init__.py`:

```python
from agent_factory.runtime.trace import RunTrace

__all__ = ["RunTrace"]
```

- [ ] **Step 4: Run trace tests and verify GREEN**

Run: `python -m pytest tests/unit/runtime/test_trace.py -v`

Expected: 2 passed.

## Task 5: Foundation Verification

**Files:**
- No new source files.

- [ ] **Step 1: Run all unit tests**

Run: `python -m pytest tests/unit -v`

Expected: 14 passed.

- [ ] **Step 2: Verify sample config loads**

Run:

```bash
python - <<'PY'
from agent_factory.config.loader import load_agent_config

config = load_agent_config("configs/agents/web_researcher.yaml")
print(config.meta.name)
print(config.unsupported_warnings)
PY
```

Expected output contains:

```text
web_researcher
("Top-level section 'workflow' is recognized but mocked in MVP.", "Top-level section 'team' is recognized but mocked in MVP.")
```

- [ ] **Step 3: Update design doc if implementation differs**

If any file path, responsibility, or MVP behavior changed during implementation, update `docs/superpowers/specs/2026-05-26-agent-factory-design.md` before continuing.

## Self-Review Notes

- Spec coverage: this plan covers the P0 parts of `agent.yaml` schema, memory/skills config contract, unsupported-field warnings, sandbox-first permission guard, explicit deny/confirm rules, and run trace. It does not cover real LLM loop, real tools, Web UI, agent team, scheduler, hooks, or skill draft generation.
- Scope boundary: the plan intentionally creates a foundation only. The next plan should build fake-LLM runtime integration and then the first web-research demo.
- TDD boundary: source files in `src/agent_factory/` are written only after matching failing tests. Project metadata and sample YAML are configuration files and do not require RED/GREEN.
