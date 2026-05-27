from __future__ import annotations

import re


def summarize_web_content(url: str, body: str) -> str:
    text = re.sub(r"<[^>]+>", " ", body)
    text = " ".join(text.split())
    excerpt = text if text else "(empty page)"
    if len(excerpt) > 1500:
        excerpt = excerpt[:1500] + "..."
    return (
        f"# Web Research Report\n\n"
        f"**Source:** {url}\n\n"
        f"## Summary\n\n"
        f"{excerpt}\n"
    )
