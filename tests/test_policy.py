"""Production policy pack tests."""
from __future__ import annotations

import pytest

from anviksha.exceptions import PolicyViolationError
from anviksha.policy.engine import CapabilityAllowlistPolicy, CostBudgetPolicy
from anviksha.types import ExecutionConstraints, ExecutionPlan, ExecutionRequest, Intent, PlanStep


def test_capability_allowlist_policy_blocks_disallowed_capability() -> None:
    request = ExecutionRequest(
        "2 + 2",
        constraints=ExecutionConstraints(allowed_capabilities=frozenset({"builtin.memory"})),
    )
    plan = ExecutionPlan(
        request.execution_id,
        Intent.MATHEMATICAL_COMPUTATION,
        (PlanStep("step-1", "builtin.calculator", Intent.MATHEMATICAL_COMPUTATION),),
    )

    with pytest.raises(PolicyViolationError, match="capability not allowed"):
        CapabilityAllowlistPolicy().validate_plan(request, plan)


def test_cost_budget_policy_blocks_estimated_cost() -> None:
    request = ExecutionRequest("2 + 2", constraints=ExecutionConstraints(max_cost=0.01))
    plan = ExecutionPlan(
        request.execution_id,
        Intent.MATHEMATICAL_COMPUTATION,
        (PlanStep("step-1", "expensive", Intent.MATHEMATICAL_COMPUTATION),),
        estimated_cost=0.02,
    )

    with pytest.raises(PolicyViolationError, match="exceeds budget"):
        CostBudgetPolicy().validate_plan(request, plan)
