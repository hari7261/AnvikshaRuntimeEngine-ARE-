"""Command line interface for the Anviksha Runtime Engine."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from collections.abc import Sequence
from dataclasses import asdict, is_dataclass
from typing import Any

from anviksha import ExecutionConstraints, Runtime, RuntimeConfig
from anviksha.exceptions import AnvikshaError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="anviksha",
        description="Execute goals with the Anviksha Runtime Engine.",
    )
    parser.add_argument("goal", nargs="+", help="Goal or task to execute.")
    parser.add_argument(
        "--with-llm",
        action="store_true",
        help="Register the configured OpenAI-compatible LLM capability.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full runtime response as JSON instead of only the output.",
    )
    parser.add_argument(
        "--offline-only",
        action="store_true",
        help="Only use deterministic/offline capabilities.",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.0,
        help="Minimum acceptable response confidence.",
    )
    parser.add_argument(
        "--allow-capability",
        action="append",
        default=None,
        help="Restrict execution to a capability id. Can be passed multiple times.",
    )
    return parser


def _build_serve_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="anviksha serve",
        description="Serve Anviksha as a self-hosted FastAPI application.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host.")
    parser.add_argument("--port", type=int, default=8000, help="Bind port.")
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable uvicorn reload for local development.",
    )
    parser.add_argument(
        "--with-llm",
        action="store_true",
        help="Register the configured OpenAI-compatible LLM capability.",
    )
    return parser


def _json_default(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    return str(value)


def main(argv: Sequence[str] | None = None) -> int:
    args_list = list(argv) if argv is not None else None
    if args_list and args_list[0] == "serve":
        return _serve(args_list[1:])

    parser = _build_parser()
    args = parser.parse_args(args_list)
    goal = " ".join(args.goal).strip()
    constraints = ExecutionConstraints(
        min_confidence=args.min_confidence,
        offline_only=args.offline_only,
        allowed_capabilities=(
            frozenset(args.allow_capability) if args.allow_capability else None
        ),
    )
    try:
        runtime = Runtime(config=RuntimeConfig(register_llm=args.with_llm))
        response = runtime.execute(goal, constraints=constraints)
    except (AnvikshaError, ValueError) as exc:
        parser.exit(2, f"anviksha: error: {exc}\n")

    if args.json:
        payload = {
            "execution_id": response.execution_id,
            "status": response.status,
            "output": response.output,
            "confidence": response.confidence,
            "diagnostics": response.diagnostics,
            "metadata": response.metadata,
        }
        print(json.dumps(payload, default=_json_default, indent=2, sort_keys=True))
    else:
        print(response.output)
    return 0


def _serve(argv: Sequence[str]) -> int:
    parser = _build_serve_parser()
    args = parser.parse_args(argv)
    if importlib.util.find_spec("uvicorn") is None:
        parser.exit(2, "anviksha serve: install server extras with: pip install anviksha[server]\n")
    if args.with_llm:
        # Instantiate once so LLM configuration errors are reported before uvicorn starts.
        Runtime(config=RuntimeConfig(register_llm=True))
        os.environ["ANVIKSHA_SERVER_REGISTER_LLM"] = "true"
    import uvicorn

    uvicorn.run(
        "anviksha.server.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
