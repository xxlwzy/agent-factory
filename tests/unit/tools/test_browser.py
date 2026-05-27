from agent_factory.tools.browser import BrowserTool


def test_browser_read_returns_fetcher_body() -> None:
    tool = BrowserTool(fetcher=lambda url: f"body:{url}")

    result = tool.execute("read", "https://example.com/page")

    assert result.success is True
    assert result.output == "body:https://example.com/page"


def test_browser_navigate_aliases_read() -> None:
    tool = BrowserTool(fetcher=lambda url: f"nav:{url}")

    result = tool.execute("navigate", "https://example.com")

    assert result.success is True
    assert result.output == "nav:https://example.com"


def test_browser_submit_not_implemented() -> None:
    tool = BrowserTool(fetcher=lambda url: url)

    result = tool.execute("submit", "https://example.com/form")

    assert result.success is False
    assert "submit" in result.error.lower()


def test_browser_rejects_unknown_operation() -> None:
    tool = BrowserTool(fetcher=lambda url: url)

    result = tool.execute("click", "https://example.com")

    assert result.success is False
    assert "Unsupported" in result.error
