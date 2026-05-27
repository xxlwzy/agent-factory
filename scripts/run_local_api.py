#!/usr/bin/env python3
"""Start the Agent Factory read-only local API and Web UI."""

from __future__ import annotations

import argparse
from pathlib import Path

from agent_factory.api.server import run_local_api, serve_forever


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local read-only API + Web UI.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1).")
    parser.add_argument("--port", type=int, default=8765, help="Bind port (default: 8765).")
    parser.add_argument("--workspace", default=".", help="Workspace root.")
    args = parser.parse_args()

    server = run_local_api(workspace_root=Path(args.workspace), host=args.host, port=args.port)
    print(f"Agent Factory local API: http://{args.host}:{args.port}/")
    print("Read-only. Tool execution is not available from this server.")
    try:
        serve_forever(server)
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
