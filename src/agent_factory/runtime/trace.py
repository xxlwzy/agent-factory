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
