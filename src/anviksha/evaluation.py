"""Small deterministic evaluation harness for runtime regression checks."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from anviksha.types import ExecutionConstraints


@dataclass(frozen=True, slots=True)
class EvaluationCase:
    name: str
    goal: str
    expected_output: Any | None = None
    constraints: ExecutionConstraints = field(default_factory=ExecutionConstraints)
    inputs: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    name: str
    passed: bool
    output: Any
    expected_output: Any | None
    diagnostics: tuple[str, ...]
    error: str | None = None


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    total: int
    passed: int
    failed: int
    results: tuple[EvaluationResult, ...]


async def run_evaluation(runtime: Any, cases: Iterable[EvaluationCase]) -> EvaluationReport:
    """Execute cases against a runtime and return a compact pass/fail report."""

    results: list[EvaluationResult] = []
    for case in cases:
        try:
            response = await runtime.aexecute(
                case.goal, inputs=case.inputs, constraints=case.constraints
            )
            passed = case.expected_output is None or response.output == case.expected_output
            results.append(
                EvaluationResult(
                    name=case.name,
                    passed=passed,
                    output=response.output,
                    expected_output=case.expected_output,
                    diagnostics=tuple(response.diagnostics),
                )
            )
        except Exception as exc:  # noqa: BLE001 - evaluation reports runtime failures as data.
            results.append(
                EvaluationResult(
                    name=case.name,
                    passed=False,
                    output=None,
                    expected_output=case.expected_output,
                    diagnostics=(),
                    error=str(exc),
                )
            )
    passed = sum(1 for result in results if result.passed)
    return EvaluationReport(len(results), passed, len(results) - passed, tuple(results))
