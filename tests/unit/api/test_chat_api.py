import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from agent_factory.api.server import create_handler_class, serve_forever
from agent_factory.runtime.chat import ChatResult
from agent_factory.runtime.states import RunStatus


def test_post_api_chat_returns_reply(tmp_path: Path) -> None:
    web_root = Path(__file__).resolve().parents[3] / "apps" / "web"
    handler = create_handler_class(workspace_root=tmp_path, web_root=web_root, use_litellm_proxy=False)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    thread = threading.Thread(target=serve_forever, args=(server,), daemon=True)
    thread.start()

    fake_result = ChatResult(
        reply="你好",
        status=RunStatus.COMPLETED,
        routed_agent="general_assistant",
        route_reason="test",
        run_id="run-1",
        run_dir=tmp_path / ".agent-factory/runs/run-1",
        routing_run_id="route-1",
    )

    try:
        import urllib.request

        with patch("agent_factory.runtime.chat.run_chat", return_value=fake_result):
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/chat",
                data=json.dumps({"message": "你好"}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            response = json.loads(urllib.request.urlopen(request, timeout=5).read())
        assert response["reply"] == "你好"
        assert response["routed_agent"] == "general_assistant"
    finally:
        server.shutdown()
        thread.join(timeout=5)
