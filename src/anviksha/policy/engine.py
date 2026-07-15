"""Policy contracts and evaluation engine."""
from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Protocol

from anviksha.exceptions import PolicyViolationError
from anviksha.types import ExecutionPlan, ExecutionRequest, RuntimeResponse


class Policy(Protocol):
    name: str

    def validate_plan(self, request: ExecutionRequest, plan: ExecutionPlan) -> None: ...
    def validate_response(self, request: ExecutionRequest, response: RuntimeResponse) -> None: ...


class PolicyEngine:
    def __init__(self, policies: tuple[Policy, ...] = ()) -> None:
        self._policies = policies

    @property
    def policies(self) -> tuple[Policy, ...]:
        return self._policies

    def validate_plan(self, request: ExecutionRequest, plan: ExecutionPlan) -> None:
        for policy in self._policies:
            policy.validate_plan(request, plan)

    def validate_response(self, request: ExecutionRequest, response: RuntimeResponse) -> None:
        for policy in self._policies:
            policy.validate_response(request, response)


class MinimumConfidencePolicy:
    name = "minimum_confidence"

    def validate_plan(self, request: ExecutionRequest, plan: ExecutionPlan) -> None:
        return None

    def validate_response(self, request: ExecutionRequest, response: RuntimeResponse) -> None:
        if response.confidence < request.constraints.min_confidence:
            msg = (
                f"confidence {response.confidence:.2f} below "
                f"required {request.constraints.min_confidence:.2f}"
            )
            raise PolicyViolationError(msg)


class CapabilityAllowlistPolicy:
    """Reject plans that select capabilities outside an explicit allowlist."""

    name = "capability_allowlist"

    def validate_plan(self, request: ExecutionRequest, plan: ExecutionPlan) -> None:
        allowed = request.constraints.allowed_capabilities
        if not allowed:
            return
        denied = sorted(
            {step.capability_id for step in plan.steps if step.capability_id not in allowed}
        )
        if denied:
            raise PolicyViolationError(
                "capability not allowed by request constraints: " + ", ".join(denied)
            )

    def validate_response(self, request: ExecutionRequest, response: RuntimeResponse) -> None:
        return None


class CostBudgetPolicy:
    """Reject plans whose estimated cost exceeds the request budget."""

    name = "cost_budget"

    def validate_plan(self, request: ExecutionRequest, plan: ExecutionPlan) -> None:
        if request.constraints.max_cost is None:
            return
        if plan.estimated_cost > request.constraints.max_cost:
            raise PolicyViolationError(
                f"estimated cost {plan.estimated_cost:.4f} exceeds budget "
                f"{request.constraints.max_cost:.4f}"
            )

    def validate_response(self, request: ExecutionRequest, response: RuntimeResponse) -> None:
        return None


class PiiRedactionPolicy:
    """Block obvious PII from leaving the runtime in string outputs."""

    name = "pii_redaction"
    _patterns = (
        re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b"),
        re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?){2}\d{4}\b"),
    )

    def validate_plan(self, request: ExecutionRequest, plan: ExecutionPlan) -> None:
        return None

    def validate_response(self, request: ExecutionRequest, response: RuntimeResponse) -> None:
        if not isinstance(response.output, str):
            return
        if any(pattern.search(response.output) for pattern in self._patterns):
            raise PolicyViolationError("response contains possible PII and was blocked")


def production_policy_pack(extra: Iterable[Policy] = ()) -> tuple[Policy, ...]:
    """Return the default production-oriented policy pack."""

    return (
        MinimumConfidencePolicy(),
        CapabilityAllowlistPolicy(),
        CostBudgetPolicy(),
        PiiRedactionPolicy(),
        *tuple(extra),
    )
