from pathlib import Path

import pytest

from agent_factory.memory.promote import list_memory_candidates, promote_memory_candidate


def test_promote_memory_candidate_copies_to_layer_root(tmp_path: Path) -> None:
    memory_root = tmp_path / ".agent-factory" / "memory" / "project"
    candidate = memory_root / "candidates" / "run-1.md"
    candidate.parent.mkdir(parents=True)
    candidate.write_text("# Candidate\n", encoding="utf-8")

    destination = promote_memory_candidate(memory_root, "run-1")

    assert destination.is_file()
    assert destination.read_text(encoding="utf-8") == "# Candidate\n"
    assert candidate.is_file()


def test_promote_memory_candidate_missing_raises(tmp_path: Path) -> None:
    memory_root = tmp_path / ".agent-factory" / "memory" / "user"
    memory_root.mkdir(parents=True)

    with pytest.raises(FileNotFoundError):
        promote_memory_candidate(memory_root, "missing")


def test_list_memory_candidates(tmp_path: Path) -> None:
    memory_root = tmp_path / "project"
    candidates_dir = memory_root / "candidates"
    candidates_dir.mkdir(parents=True)
    (candidates_dir / "a.md").write_text("a", encoding="utf-8")
    (candidates_dir / "b.md").write_text("b", encoding="utf-8")

    items = list_memory_candidates(memory_root)

    assert {item["candidate_id"] for item in items} == {"a", "b"}
