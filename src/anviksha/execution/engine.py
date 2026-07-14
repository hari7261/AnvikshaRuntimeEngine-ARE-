"""Execution engine that executes plans without replanning."""
from __future__ import annotations
from time import perf_counter
from anviksha.capabilities.registry import CapabilityRegistry
from anviksha.observability.events import EventSink, RuntimeEvent
from anviksha.state.manager import StateManager, StateTransition
from anviksha.types import CapabilityResult, ExecutionPlan, ExecutionStatus

class ExecutionEngine:
    def __init__(self, registry: CapabilityRegistry, state: StateManager, events: EventSink) -> None:
        self._registry, self._state, self._events = registry, state, events
    async def execute(self, plan: ExecutionPlan) -> CapabilityResult:
        self._state.record(StateTransition(plan.execution_id, ExecutionStatus.RUNNING))
        outputs: dict[str, object] = {}
        confidence = 1.0
        start = perf_counter()
        for step in plan.steps:
            cap = self._registry.get(step.capability_id)
            self._events.emit(RuntimeEvent("capability.started", plan.execution_id, attributes={"step_id": step.id, "capability_id": step.capability_id}))
            result = await cap.execute({**step.arguments, "previous_outputs": outputs})
            outputs[step.id] = result.output
            confidence = min(confidence, result.confidence)
            self._state.record(StateTransition(plan.execution_id, ExecutionStatus.RUNNING, step_id=step.id, payload=result.metadata))
            self._events.emit(RuntimeEvent("capability.completed", plan.execution_id, attributes={"step_id": step.id, "confidence": result.confidence}))
        self._events.emit(RuntimeEvent("execution.completed", plan.execution_id, attributes={"duration_ms": int((perf_counter()-start)*1000)}))
        return CapabilityResult(outputs[plan.steps[-1].id] if plan.steps else None, confidence, {"steps": len(plan.steps)})
