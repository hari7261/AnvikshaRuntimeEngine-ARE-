"""Policy contracts and evaluation engine."""
from __future__ import annotations

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
