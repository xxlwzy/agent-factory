from pathlib import Path

from agent_factory.tools.filesystem import FilesystemTool


def test_filesystem_write_and_read(tmp_path: Path) -> None:
    target = tmp_path / "notes" / "report.md"
    tool = FilesystemTool(workspace_root=tmp_path)

    write_result = tool.execute("write", str(target), content="hello")
    read_result = tool.execute("read", str(target))

    assert write_result.success is True
    assert target.read_text(encoding="utf-8") == "hello"
    assert read_result.success is True
    assert read_result.output == "hello"


def test_filesystem_read_missing_file_returns_error(tmp_path: Path) -> None:
    tool = FilesystemTool(workspace_root=tmp_path)

    result = tool.execute("read", str(tmp_path / "missing.txt"))

    assert result.success is False
    assert "missing" in result.error.lower() or "not found" in result.error.lower()


def test_filesystem_rejects_unknown_operation(tmp_path: Path) -> None:
    tool = FilesystemTool(workspace_root=tmp_path)

    result = tool.execute("delete", str(tmp_path / "x.txt"))

    assert result.success is False
    assert "unsupported" in result.error.lower()
