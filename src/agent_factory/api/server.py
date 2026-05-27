from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from agent_factory.api.store import WorkspaceStore


def create_handler_class(
    *,
    workspace_root: str | Path,
    web_root: str | Path,
    agents_dir: str | Path | None = None,
    use_litellm_proxy: bool = False,
) -> type[BaseHTTPRequestHandler]:
    workspace = Path(workspace_root).resolve()
    web = Path(web_root).resolve()
    store = WorkspaceStore(workspace, agents_dir=agents_dir)
    litellm_enabled = use_litellm_proxy

    class AgentFactoryAPIHandler(BaseHTTPRequestHandler):
        use_litellm_proxy = litellm_enabled

        def log_message(self, format: str, *args: Any) -> None:
            return

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = unquote(parsed.path)

            try:
                if path == "/":
                    self._serve_index()
                    return
                if path == "/api/agents":
                    self._send_json(store.list_agents())
                    return
                if path == "/api/agents/catalog":
                    self._send_json(store.list_agent_catalog())
                    return
                if path == "/api/runs":
                    self._send_json(store.list_runs())
                    return
                if path == "/api/skills/drafts":
                    self._send_json(store.list_skill_drafts())
                    return
                if path.startswith("/api/runs/") and path.endswith("/trace"):
                    run_id = path.removeprefix("/api/runs/").removesuffix("/trace")
                    self._send_json(store.read_trace(run_id))
                    return
                if path.startswith("/api/runs/") and "/artifacts/" in path:
                    suffix = path.removeprefix("/api/runs/")
                    run_id, _, artifact_name = suffix.partition("/artifacts/")
                    content = store.read_artifact(run_id, artifact_name)
                    self._send_text(content, content_type="text/plain; charset=utf-8")
                    return
                if path.startswith("/api/runs/"):
                    run_id = path.removeprefix("/api/runs/").strip("/")
                    if run_id:
                        self._send_json(store.read_run(run_id))
                        return
            except FileNotFoundError:
                self._send_error(HTTPStatus.NOT_FOUND, "Not found")
                return
            except ValueError as error:
                self._send_error(HTTPStatus.BAD_REQUEST, str(error))
                return

            self._send_error(HTTPStatus.NOT_FOUND, "Not found")

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            path = unquote(parsed.path)
            if path != "/api/chat":
                self._send_error(HTTPStatus.NOT_FOUND, "Not found")
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length) if length else b"{}"
                body = json.loads(raw.decode("utf-8"))
                message = str(body.get("message", "")).strip()
                if not message:
                    self._send_error(HTTPStatus.BAD_REQUEST, "message is required")
                    return
                from agent_factory.runtime.chat import run_chat

                result = run_chat(
                    message,
                    workspace_root=workspace,
                    agents_dir=store.agents_dir,
                    use_litellm_proxy=self.use_litellm_proxy,
                )
                self._send_json(
                    {
                        "reply": result.reply,
                        "status": result.status.value,
                        "routed_agent": result.routed_agent,
                        "route_reason": result.route_reason,
                        "run_id": result.run_id,
                        "routing_run_id": result.routing_run_id,
                        "model_used": result.model_used,
                    }
                )
            except (json.JSONDecodeError, ValueError) as error:
                self._send_error(HTTPStatus.BAD_REQUEST, str(error))
            except Exception as error:
                self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(error))

        def _serve_index(self) -> None:
            index_path = web / "index.html"
            if not index_path.is_file():
                self._send_error(HTTPStatus.NOT_FOUND, "Web UI not found")
                return
            content = index_path.read_text(encoding="utf-8")
            self._send_text(content, content_type="text/html; charset=utf-8")

        def _send_json(self, payload: Any) -> None:
            body = json.dumps(payload, ensure_ascii=True, indent=2).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_text(self, content: str, *, content_type: str) -> None:
            body = content.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_error(self, status: HTTPStatus, message: str) -> None:
            body = json.dumps({"error": message}, ensure_ascii=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return AgentFactoryAPIHandler


def serve_forever(server: ThreadingHTTPServer) -> None:
    server.serve_forever()


def run_local_api(
    *,
    workspace_root: str | Path,
    host: str = "127.0.0.1",
    port: int = 8765,
    web_root: str | Path | None = None,
    use_litellm_proxy: bool = True,
) -> ThreadingHTTPServer:
    repo_root = Path(__file__).resolve().parents[3]
    resolved_web = Path(web_root) if web_root is not None else repo_root / "apps" / "web"
    handler = create_handler_class(
        workspace_root=workspace_root,
        web_root=resolved_web,
        use_litellm_proxy=use_litellm_proxy,
    )
    server = ThreadingHTTPServer((host, port), handler)
    return server
