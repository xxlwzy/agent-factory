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
