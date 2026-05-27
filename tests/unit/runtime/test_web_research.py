from pathlib import Path

from agent_factory.llm.messages import FinalResponse, LLMRequest, ToolCallResponse
from agent_factory.llm.web_research_demo import WebResearchDemoLLM
from agent_factory.runtime.states import RunStatus
from agent_factory.runtime.summarize import summarize_web_content
from agent_factory.runtime.web_research import run_web_research_demo


def test_summarize_web_content_includes_source_url() -> None:
    report = summarize_web_content("https://example.com/page", "<p>Hello world</p>")

    assert "example.com" in report
    assert "Hello world" in report
    assert report.startswith("# ")


def test_web_research_demo_llm_scripts_get_then_write() -> None:
    llm = WebResearchDemoLLM(
        url="https://example.com/page",
        report_path=".agent-factory/runs/demo/artifact/report.md",
    )

    first = llm.next_response(LLMRequest(task="research", messages=()))
    assert first == ToolCallResponse(tool="http", operation="GET", target="https://example.com/page")

    second = llm.next_response(
        LLMRequest(
            task="research",
            messages=("http.GET:https://example.com/page=<p>Body</p>",),
        )
    )
    assert second.tool == "filesystem"
    assert second.operation == "write"
    assert "Body" in second.content

    third = llm.next_response(LLMRequest(task="research", messages=("ignored",)))
    assert isinstance(third, FinalResponse)


def test_run_web_research_demo_writes_report_and_summary(tmp_path: Path) -> None:
    config_path = _repo_root() / "configs/agents/web_researcher.yaml"
    result = run_web_research_demo(
        agent_config_path=config_path,
        url="https://example.com/article",
        workspace_root=tmp_path,
        http_fetcher=lambda _url: "<title>Demo</title><p>Key fact here.</p>",
        run_id="test-run-1",
    )

    assert result.result.status == RunStatus.COMPLETED
    report_path = tmp_path / ".agent-factory/runs/test-run-1/artifact/report.md"
    summary_path = tmp_path / ".agent-factory/runs/test-run-1/summary.md"
    trace_path = tmp_path / ".agent-factory/runs/test-run-1/trace.jsonl"

    assert report_path.is_file()
    assert "example.com" in report_path.read_text(encoding="utf-8")
    assert "Key fact here" in report_path.read_text(encoding="utf-8")
    assert summary_path.is_file()
    assert trace_path.is_file()
    assert result.learning is not None
    assert result.learning.session_archive is not None
    assert result.learning.skill_draft_dir is not None


def test_run_web_research_demo_blocks_disallowed_domain(tmp_path: Path) -> None:
    config_path = _repo_root() / "configs/agents/web_researcher.yaml"

    result = run_web_research_demo(
        agent_config_path=config_path,
        url="https://evil.test/page",
        workspace_root=tmp_path,
        http_fetcher=lambda _url: "should not run",
        run_id="test-run-blocked",
    )

    assert result.result.status == RunStatus.BLOCKED
    assert (tmp_path / ".agent-factory/runs/test-run-blocked/artifact/report.md").exists() is False


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]
