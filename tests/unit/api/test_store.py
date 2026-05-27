from pathlib import Path

import pytest

from agent_factory.api.store import WorkspaceStore


def test_list_runs_and_read_trace(tmp_path: Path) -> None:
    run_dir = tmp_path / ".agent-factory" / "runs" / "run-1"
    run_dir.mkdir(parents=True)
    (run_dir / "summary.md").write_text("# Run Summary\n\n- Status: completed\n", encoding="utf-8")
    (run_dir / "trace.jsonl").write_text(
        '{"type":"run_started","data":{"task":"demo"}}\n',
        encoding="utf-8",
    )

    store = WorkspaceStore(tmp_path)
    runs = store.list_runs()

    assert len(runs) == 1
    assert runs[0]["run_id"] == "run-1"
    assert runs[0]["status"] == "completed"
    events = store.read_trace("run-1")
    assert events[0]["type"] == "run_started"


def test_read_artifact_and_block_traversal(tmp_path: Path) -> None:
    artifact = tmp_path / ".agent-factory" / "runs" / "run-1" / "artifact" / "report.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("# Report\n", encoding="utf-8")

    store = WorkspaceStore(tmp_path)
    assert store.read_artifact("run-1", "report.md") == "# Report\n"

    with pytest.raises(ValueError):
        store.read_artifact("run-1", "../summary.md")


def test_list_skill_drafts(tmp_path: Path) -> None:
    draft_dir = tmp_path / ".agent-factory" / "skills" / "drafts" / "web-researcher-run-1"
    draft_dir.mkdir(parents=True)
    (draft_dir / "review.json").write_text('{"status":"pending"}\n', encoding="utf-8")

    store = WorkspaceStore(tmp_path)
    drafts = store.list_skill_drafts()

    assert len(drafts) == 1
    assert drafts[0]["draft_id"] == "web-researcher-run-1"
    assert drafts[0]["status"] == "pending"
