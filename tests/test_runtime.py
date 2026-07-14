from __future__ import annotations

import asyncio

import pytest

from anviksha import ExecutionConstraints, Runtime
from anviksha.exceptions import PolicyViolationError
from anviksha.types import ExecutionStatus


def test_runtime_executes_deterministic_calculation() -> None:
    response = Runtime().execute("2 + 3 * 4")

    assert response.status is ExecutionStatus.SUCCEEDED
    assert response.output == 14.0
    assert response.confidence >= 0.99
    assert response.metadata["estimated_cost"] == 0.0
    assert response.diagnostics == ("selected builtin.calculator for mathematical_computation",)


def test_runtime_supports_async_execution_and_observability() -> None:
    runtime = Runtime()

    response = asyncio.run(runtime.aexecute("What is Anviksha?"))

    assert response.output == "What is Anviksha?"
    assert response.metadata["events"]
    assert response.metadata["timeline"]


def test_minimum_confidence_policy_blocks_low_confidence_response() -> None:
    runtime = Runtime()

    with pytest.raises(PolicyViolationError):
        runtime.execute("What is Anviksha?", constraints=ExecutionConstraints(min_confidence=0.95))
