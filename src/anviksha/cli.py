"""Command line interface for the Anviksha Runtime Engine."""
from __future__ import annotations

import argparse
import json
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


def _json_default(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    return str(value)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
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


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
