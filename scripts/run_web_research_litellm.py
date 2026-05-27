#!/usr/bin/env python3
"""Run the web research demo through a local LiteLLM proxy."""

from __future__ import annotations

import argparse
from pathlib import Path

from agent_factory.llm.litellm_env import ensure_litellm_proxy_env
from agent_factory.llm.model_priority import resolve_litellm_model_candidates
from agent_factory.runtime.states import RunStatus
from agent_factory.runtime.web_research import run_web_research_demo


def main() -> int:
    parser = argparse.ArgumentParser(description="Run web research demo via LiteLLM proxy.")
    parser.add_argument("url", help="HTTP(S) URL to fetch (must match agent domain allowlist).")
    parser.add_argument(
        "--config",
        default="configs/agents/web_researcher.yaml",
        help="Path to agent YAML config.",
    )
    parser.add_argument(
        "--workspace",
        default=".",
        help="Workspace root for sandbox paths and run output.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="LiteLLM proxy model override (default: MiMo → ModelScope → OneHub priority).",
    )
    args = parser.parse_args()
    ensure_litellm_proxy_env()
    models = resolve_litellm_model_candidates(args.model)
    if len(models) == 1:
        print(f"model_plan={models[0]}")
    else:
        print(f"model_plan={models[0]} (+{len(models) - 1} fallbacks)")

    result = run_web_research_demo(
        agent_config_path=args.config,
        url=args.url,
        workspace_root=Path(args.workspace),
        use_litellm_proxy=True,
        litellm_model=args.model,
    )
    print(f"run_id={result.run_id}")
    print(f"status={result.result.status.value}")
    if result.model_used:
        print(f"model={result.model_used}")
    print(f"report={result.report_path}")
    if result.result.status != RunStatus.COMPLETED:
        print(f"reason={result.result.reason or result.result.output}")
        print(
            "hint: ensure litellm-proxy is running and ../litellm-proxy/.env is loaded "
            "(LITELLM_MASTER_KEY / provider API keys)."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
