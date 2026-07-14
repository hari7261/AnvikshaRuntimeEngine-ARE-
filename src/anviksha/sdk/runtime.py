"""Public Python SDK runtime entry point."""
from __future__ import annotations
import asyncio
from dataclasses import dataclass
from typing import Any, Mapping
from anviksha.capabilities.builtins import CalculatorCapability, EchoModelCapability
from anviksha.capabilities.registry import CapabilityRegistry
from anviksha.execution.engine import ExecutionEngine
from anviksha.observability.events import InMemoryEventSink, RuntimeEvent
from anviksha.planner.default import RuleBasedPlanner
from anviksha.policy.engine import MinimumConfidencePolicy, PolicyEngine
from anviksha.state.manager import StateManager, StateTransition
from anviksha.types import ExecutionConstraints, ExecutionRequest, ExecutionStatus, RuntimeResponse

@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    register_builtins: bool = True
    include_trace_metadata: bool = True

class Runtime:
    def __init__(self, config: RuntimeConfig | None = None, registry: CapabilityRegistry | None = None) -> None:
        self.config = config or RuntimeConfig()
        self.registry = registry or CapabilityRegistry()
        if self.config.register_builtins:
            for cap in (CalculatorCapability(), EchoModelCapability()):
                if cap.metadata.id not in {c.metadata.id for c in self.registry.all()}: self.registry.register(cap)
        self.state = StateManager(); self.events = InMemoryEventSink()
        self.planner = RuleBasedPlanner(self.registry)
        self.policies = PolicyEngine((MinimumConfidencePolicy(),))
        self.executor = ExecutionEngine(self.registry, self.state, self.events)

    def execute(self, goal: str, inputs: Mapping[str, Any] | None = None, constraints: ExecutionConstraints | None = None) -> RuntimeResponse:
        return asyncio.run(self.aexecute(goal, inputs, constraints))

    async def aexecute(self, goal: str, inputs: Mapping[str, Any] | None = None, constraints: ExecutionConstraints | None = None) -> RuntimeResponse:
        request = ExecutionRequest(goal=goal, inputs=inputs or {}, constraints=constraints or ExecutionConstraints())
        self.state.record(StateTransition(request.execution_id, ExecutionStatus.PLANNING))
        self.events.emit(RuntimeEvent("planning.started", request.execution_id))
        plan = self.planner.plan(request)
        self.policies.validate_plan(request, plan)
        self.events.emit(RuntimeEvent("planning.completed", request.execution_id, attributes={"intent": plan.intent, "steps": len(plan.steps)}))
        result = await self.executor.execute(plan)
        response = RuntimeResponse(request.execution_id, ExecutionStatus.SUCCEEDED, result.output, result.confidence, self._metadata(request.execution_id, plan.estimated_cost), plan.diagnostics)
        self.policies.validate_response(request, response)
        self.state.record(StateTransition(request.execution_id, ExecutionStatus.SUCCEEDED, payload=response.metadata))
        return response

    async def astream(self, goal: str, inputs: Mapping[str, Any] | None = None, constraints: ExecutionConstraints | None = None):
        response = await self.aexecute(goal, inputs, constraints)
        yield response.output

    def _metadata(self, execution_id: str, estimated_cost: float) -> dict[str, Any]:
        data: dict[str, Any] = {"estimated_cost": estimated_cost}
        if self.config.include_trace_metadata:
            data["timeline"] = self.state.timeline(execution_id)
            data["events"] = tuple(e for e in self.events.events if e.execution_id == execution_id)
        return data
