from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


class WorkspaceStore:
    def __init__(self, workspace_root: str | Path, *, agents_dir: str | Path | None = None) -> None:
        self._workspace = Path(workspace_root).resolve()
        self._runs_root = self._workspace / ".agent-factory" / "runs"
        self._drafts_root = self._workspace / ".agent-factory" / "skills" / "drafts"
        agents_path = Path(agents_dir) if agents_dir is not None else self._workspace / "configs" / "agents"
        self._agents_dir = agents_path.resolve()

    def list_agents(self) -> list[dict[str, str]]:
        if not self._agents_dir.is_dir():
            return []
        agents: list[dict[str, str]] = []
        for path in sorted(self._agents_dir.glob("*.yaml")):
            agents.append({"name": path.stem, "path": str(path.relative_to(self._workspace))})
        return agents

    def list_runs(self) -> list[dict[str, Any]]:
        if not self._runs_root.is_dir():
            return []
        runs: list[dict[str, Any]] = []
        for run_dir in sorted(self._runs_root.iterdir()):
            if not run_dir.is_dir():
                continue
            summary_path = run_dir / "summary.md"
            runs.append(
                {
                    "run_id": run_dir.name,
                    "status": _status_from_summary(summary_path),
                    "has_report": (run_dir / "artifact" / "report.md").is_file(),
                }
            )
        runs.sort(key=lambda item: item["run_id"], reverse=True)
        return runs

    def read_run(self, run_id: str) -> dict[str, Any]:
        run_dir = self._run_dir(run_id)
        summary_path = run_dir / "summary.md"
        return {
            "run_id": run_id,
            "status": _status_from_summary(summary_path),
            "summary": summary_path.read_text(encoding="utf-8") if summary_path.is_file() else "",
            "artifacts": _list_artifact_names(run_dir / "artifact"),
        }

    def read_trace(self, run_id: str) -> list[dict[str, Any]]:
        trace_path = self._run_dir(run_id) / "trace.jsonl"
        if not trace_path.is_file():
            return []
        events: list[dict[str, Any]] = []
        for line in trace_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
        return events

    def read_artifact(self, run_id: str, artifact_name: str) -> str:
        if Path(artifact_name).name != artifact_name or artifact_name in (".", ".."):
            raise ValueError("Artifact name must be a single path segment.")
        artifact_path = self._run_dir(run_id) / "artifact" / artifact_name
        if not artifact_path.is_file():
            raise FileNotFoundError(f"Artifact not found: {artifact_name}")
        return artifact_path.read_text(encoding="utf-8")

    def list_skill_drafts(self) -> list[dict[str, Any]]:
        if not self._drafts_root.is_dir():
            return []
        drafts: list[dict[str, Any]] = []
        for draft_dir in sorted(self._drafts_root.iterdir()):
            if not draft_dir.is_dir():
                continue
            review_path = draft_dir / "review.json"
            status = "unknown"
            if review_path.is_file():
                data = json.loads(review_path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and isinstance(data.get("status"), str):
                    status = data["status"]
            drafts.append({"draft_id": draft_dir.name, "status": status})
        drafts.sort(key=lambda item: item["draft_id"], reverse=True)
        return drafts

    def _run_dir(self, run_id: str) -> Path:
        if Path(run_id).name != run_id or run_id in (".", ".."):
            raise ValueError("Invalid run id.")
        run_dir = self._runs_root / run_id
        if not run_dir.is_dir():
            raise FileNotFoundError(f"Run not found: {run_id}")
        return run_dir


def _status_from_summary(summary_path: Path) -> str:
    if not summary_path.is_file():
        return "unknown"
    match = re.search(r"Status:\s*(\w+)", summary_path.read_text(encoding="utf-8"))
    return match.group(1) if match else "unknown"


def _list_artifact_names(artifact_dir: Path) -> list[str]:
    if not artifact_dir.is_dir():
        return []
    return sorted(path.name for path in artifact_dir.iterdir() if path.is_file())
