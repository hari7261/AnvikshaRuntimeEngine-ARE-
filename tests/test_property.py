"""Property-based tests for runtime invariants."""
from __future__ import annotations

import asyncio
from typing import Any

import pytest

from hypothesis import given, strategies as st

from anviksha import Runtime, RuntimeConfig
from anviksha.capabilities import CalculatorCapability, CapabilityRegistry
from anviksha.capabilities.base import CapabilityMetadata, CapabilityResult
from anviksha.exceptions import PlanningError
from anviksha.types import (
    CapabilityKind,
    ExecutionConstraints,
    ExecutionPlan,
    ExecutionRequest,
    ExecutionStatus,
    Intent,
    PlanStep,
    RuntimeResponse,
)


@given(
    left=st.integers(min_value=-1000, max_value=1000),
    right=st.integers(min_value=-1000, max_value=1000),
    op=st.sampled_from(["+", "-", "*"]),
)
def test_calculator_properties(left: int, right: int, op: str) -> None:
    calc = CalculatorCapability()
    expr = f"{left} {op} {right}"
    result = asyncio.run(calc.execute({"expression": expr}))
    assert isinstance(result.output, float)
    assert result.confidence == 0.99
    expected = {
        "+": left + right,
        "-": left - right,
        "*": left * right,
    }[op]
    assert result.output == float(expected)


@given(
    left=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
    right=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
)
def test_calculator_commutative_addition(left: float, right: float) -> None:
    calc = CalculatorCapability()
    r1 = asyncio.run(calc.execute({"expression": f"{left} + {right}"}))
    r2 = asyncio.run(calc.execute({"expression": f"{right} + {left}"}))
    assert r1.output == r2.output


@given(id_str=st.text(min_size=1, max_size=20))
def test_capability_registry_round_trip(id_str: str) -> None:
    registry = CapabilityRegistry()
    meta = CapabilityMetadata(
        id=id_str,
        name="Test",
        kind=CapabilityKind.TOOL,
        supported_intents=frozenset({Intent.GENERAL}),
    )

    class DynamicCap:
        metadata = meta
        async def execute(self, arguments: Any) -> CapabilityResult:
            return CapabilityResult(output="ok")

    registry.register(DynamicCap())
    retrieved = registry.get(id_str)
    assert retrieved.metadata.id == id_str


@given(goal=st.text(max_size=0))
def test_empty_goal_in_execution_request(goal: str) -> None:
    with pytest.raises(ValueError, match="non-empty"):
        ExecutionRequest(goal=goal)


@given(confidence=st.floats(min_value=0.0, max_value=0.99))
def test_runtime_response_immutability(confidence: float) -> None:
    response = RuntimeResponse(
        execution_id="e1",
        status=ExecutionStatus.SUCCEEDED,
        output="test",
        confidence=confidence,
        metadata={"key": "value"},
    )
    assert response.confidence == confidence
    assert response.metadata["key"] == "value"


@given(
    steps=st.lists(
        st.integers(min_value=1, max_value=10).map(
            lambda i: PlanStep(id=f"s{i}", capability_id=f"cap{i}", intent=Intent.GENERAL)
        ),
        min_size=0,
        max_size=5,
    ),
)
def test_execution_plan_validation(steps: list[PlanStep]) -> None:
    plan = ExecutionPlan(
        execution_id="test",
        intent=Intent.GENERAL,
        steps=tuple(steps),
    )
    assert len(plan.steps) == len(steps)
    if not steps:
        assert plan.steps == ()


@given(
    min_conf=st.floats(min_value=0.0, max_value=1.0),
    offline=st.booleans(),
)
def test_execution_constraints_immutable(min_conf: float, offline: bool) -> None:
    c = ExecutionConstraints(min_confidence=min_conf, offline_only=offline)
    assert c.min_confidence == min_conf
    assert c.offline_only == offline
    assert c.metadata == {}
