import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

from agent_factory.api.server import create_handler_class, serve_forever


def test_api_lists_runs_and_serves_ui(tmp_path: Path) -> None:
    run_dir = tmp_path / ".agent-factory" / "runs" / "run-a"
    run_dir.mkdir(parents=True)
    (run_dir / "summary.md").write_text("# Run Summary\n\n- Status: completed\n", encoding="utf-8")

    configs = tmp_path / "configs" / "agents"
    configs.mkdir(parents=True)
    (configs / "demo.yaml").write_text("meta:\n  name: demo\n", encoding="utf-8")

    web_root = Path(__file__).resolve().parents[3] / "apps" / "web"
    handler = create_handler_class(workspace_root=tmp_path, web_root=web_root)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    thread = threading.Thread(target=serve_forever, args=(server,), daemon=True)
    thread.start()

    try:
        import urllib.request

        runs = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/api/runs", timeout=5).read())
        assert runs[0]["run_id"] == "run-a"

        agents = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/api/agents", timeout=5).read())
        assert agents[0]["name"] == "demo"

        ui = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5).read().decode("utf-8")
        assert "Agent Factory" in ui
    finally:
        server.shutdown()
        thread.join(timeout=5)
