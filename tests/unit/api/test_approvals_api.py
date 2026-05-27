import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from agent_factory.api.server import create_handler_class, serve_forever
from agent_factory.runtime.chat import ChatResult
from agent_factory.runtime.states import RunStatus


def test_post_approval_resolves_pending(tmp_path: Path) -> None:
    web_root = Path(__file__).resolve().parents[3] / "apps" / "web"
    handler = create_handler_class(workspace_root=tmp_path, web_root=web_root, use_litellm_proxy=False)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    thread = threading.Thread(target=serve_forever, args=(server,), daemon=True)
    thread.start()

    fake_result = ChatResult(
        reply="已执行",
        status=RunStatus.COMPLETED,
        routed_agent="general_assistant",
        route_reason="approved",
        run_id="run-1",
        run_dir=tmp_path / ".agent-factory/runs/run-1",
        routing_run_id="",
        session_id="session-1",
        approval_id="appr-1",
    )

    try:
        import urllib.request

        with patch("agent_factory.runtime.chat.resolve_approval", return_value=fake_result):
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/approvals/appr-1",
                data=json.dumps({"approved": True}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            response = json.loads(urllib.request.urlopen(request, timeout=5).read())
        assert response["reply"] == "已执行"
        assert response["session_id"] == "session-1"
    finally:
        server.shutdown()
        thread.join(timeout=5)
