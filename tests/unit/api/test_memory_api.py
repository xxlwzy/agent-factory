import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

from agent_factory.api.server import create_handler_class, serve_forever


def test_post_promote_memory_candidate(tmp_path: Path) -> None:
    configs = tmp_path / "configs" / "agents"
    configs.mkdir(parents=True)
    (configs / "demo.yaml").write_text(
        """
meta:
  name: demo
agent:
  role: tester
  model: fake
  system_prompt: test
tools:
  filesystem:
    enabled: true
permissions:
  sandbox:
    paths:
      - .
memory:
  project_path: .agent-factory/memory/project
  user_path: .agent-factory/memory/user
""",
        encoding="utf-8",
    )
    candidate = tmp_path / ".agent-factory" / "memory" / "project" / "candidates" / "run-1.md"
    candidate.parent.mkdir(parents=True)
    candidate.write_text("# Project memory\n", encoding="utf-8")

    web_root = Path(__file__).resolve().parents[3] / "apps" / "web"
    handler = create_handler_class(workspace_root=tmp_path, web_root=web_root, agents_dir=configs)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    thread = threading.Thread(target=serve_forever, args=(server,), daemon=True)
    thread.start()

    try:
        import urllib.request

        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/memory/candidates/project/run-1/promote",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        response = json.loads(urllib.request.urlopen(request, timeout=5).read())
        assert response["layer"] == "project"
        promoted = tmp_path / ".agent-factory" / "memory" / "project" / "run-1.md"
        assert promoted.is_file()
    finally:
        server.shutdown()
        thread.join(timeout=5)
