import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

from agent_factory.api.server import create_handler_class, serve_forever
from agent_factory.skills.loader import load_enabled_skills
from agent_factory.skills.review import REVIEW_STATUS_ENABLED, read_review_status


def test_post_enable_skill_draft(tmp_path: Path) -> None:
    draft_id = "web-researcher-run-1"
    draft_dir = tmp_path / ".agent-factory" / "skills" / "drafts" / draft_id
    draft_dir.mkdir(parents=True)
    (draft_dir / "SKILL.md").write_text(
        "# Draft\n\n## Steps\n\n1. Fetch page.\n",
        encoding="utf-8",
    )
    (draft_dir / "review.json").write_text('{"status": "pending"}\n', encoding="utf-8")

    web_root = Path(__file__).resolve().parents[3] / "apps" / "web"
    handler = create_handler_class(workspace_root=tmp_path, web_root=web_root)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    thread = threading.Thread(target=serve_forever, args=(server,), daemon=True)
    thread.start()

    try:
        import urllib.request

        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/skills/drafts/{draft_id}/enable",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        response = json.loads(urllib.request.urlopen(request, timeout=5).read())
        assert response["status"] == REVIEW_STATUS_ENABLED
        assert read_review_status(draft_dir) == REVIEW_STATUS_ENABLED

        loaded = load_enabled_skills((response["skill_name"],), tmp_path / "configs" / "skills")
        assert len(loaded.skills) == 1
        assert "Fetch page" in loaded.skills[0].body
    finally:
        server.shutdown()
        thread.join(timeout=5)
