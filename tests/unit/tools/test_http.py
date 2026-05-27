from agent_factory.tools.http import HttpTool


def test_http_get_returns_fetcher_body() -> None:
    tool = HttpTool(fetcher=lambda url: f"body:{url}")

    result = tool.execute("GET", "https://example.com/page")

    assert result.success is True
    assert result.output == "body:https://example.com/page"


def test_http_rejects_non_get_operation() -> None:
    tool = HttpTool(fetcher=lambda url: url)

    result = tool.execute("POST", "https://example.com/page")

    assert result.success is False
    assert "GET" in result.error
