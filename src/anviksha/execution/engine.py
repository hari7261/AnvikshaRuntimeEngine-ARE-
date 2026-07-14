"""Execution engine with parallel step execution, retry, and streaming."""
from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Callable, Coroutine
from time import perf_counter
from typing import Any

from anviksha.capabilities.registry import CapabilityRegistry
from anviksha.config import get_settings
from anviksha.exceptions import CapabilityError, PlanningError
from anviksha.observability.events import EventSink, RuntimeEvent
from anviksha.state.manager import StateManager, StateTransition
from anviksha.types import CapabilityResult, ExecutionPlan, ExecutionStatus


class ExecutionEngine:
    def __init__(
        self,
        registry: CapabilityRegistry,
        state: StateManager,
        events: EventSink,
    ) -> None:
        self._registry = registry
        self._state = state
        self._events = events

    async def execute(self, plan: ExecutionPlan) -> CapabilityResult:
        self._validate_plan(plan)
        self._state.record(StateTransition(plan.execution_id, ExecutionStatus.RUNNING))
        outputs: dict[str, object] = {}
        confidence = 1.0
        start = perf_counter()
        async for step_id, result in self._execute_plan(plan.execution_id, plan.steps, outputs):
            outputs[step_id] = result.output
            confidence = min(confidence, result.confidence)
        self._events.emit(
            RuntimeEvent(
                "execution.completed",
                plan.execution_id,
                attributes={"duration_ms": int((perf_counter() - start) * 1000)},
            )
        )
        return CapabilityResult(
            outputs[plan.steps[-1].id], confidence, {"steps": len(plan.steps)}
        )

    async def execute_stream(
        self, plan: ExecutionPlan
    ) -> AsyncGenerator[tuple[str, Any], None]:
        self._validate_plan(plan)
        self._state.record(StateTransition(plan.execution_id, ExecutionStatus.RUNNING))
        outputs: dict[str, object] = {}
        start = perf_counter()
        async for step_id, result in self._execute_plan(plan.execution_id, plan.steps, outputs):
            outputs[step_id] = result.output
            yield (step_id, result.output)
        self._events.emit(
            RuntimeEvent(
                "execution.completed",
                plan.execution_id,
                attributes={"duration_ms": int((perf_counter() - start) * 1000)},
            )
        )

    async def _execute_plan(
        self,
        execution_id: str,
        steps: Any,
        outputs: dict[str, object],
    ) -> AsyncGenerator[tuple[str, CapabilityResult], None]:
        step_map = {s.id: s for s in steps}
        resolved: set[str] = set()
        pending: set[str] = set(step_map.keys())

        while pending:
            ready = [
                s for s in pending
                if all(dep in resolved for dep in step_map[s].depends_on)
            ]
            if not ready:
                raise PlanningError(
                    f"circular or unresolvable dependency in steps: {pending}"
                )
            tasks = {
                step_id: self._execute_step(
                    execution_id, step_map[step_id], outputs
                )
                for step_id in ready
            }
            results = await asyncio.gather(
                *tasks.values(), return_exceptions=True
            )
            for step_id, result in zip(tasks.keys(), results, strict=True):
                if isinstance(result, BaseException):
                    raise result
                cap_result: CapabilityResult = result
                resolved.add(step_id)
                pending.discard(step_id)
                outputs[step_id] = cap_result.output
                yield step_id, cap_result

    def _validate_plan(self, plan: ExecutionPlan) -> None:
        if not plan.steps:
            raise PlanningError("execution plan has no steps")
        resolved: set[str] = set()
        for step in plan.steps:
            self._registry.get(step.capability_id)
            for dep in step.depends_on:
                if dep not in resolved:
                    raise PlanningError(
                        f"step {step.id} depends on unresolved step {dep}"
                    )
            resolved.add(step.id)

    async def _execute_step(
        self,
        execution_id: str,
        step: Any,
        outputs: dict[str, object],
    ) -> CapabilityResult:
        cap = self._registry.get(step.capability_id)
        self._events.emit(
            RuntimeEvent(
                "capability.started",
                execution_id,
                attributes={"step_id": step.id, "capability_id": step.capability_id},
            )
        )
        result = await self._run_with_retry(
            lambda: cap.execute({**step.arguments, "previous_outputs": outputs}),
            execution_id,
            step,
        )
        self._state.record(
            StateTransition(
                execution_id,
                ExecutionStatus.RUNNING,
                step_id=step.id,
                payload=result.metadata,
            )
        )
        self._events.emit(
            RuntimeEvent(
                "capability.completed",
                execution_id,
                attributes={"step_id": step.id, "confidence": result.confidence},
            )
        )
        return result

    async def _run_with_retry(
        self,
        factory: Callable[[], Coroutine[Any, Any, CapabilityResult]],
        execution_id: str,
        step: Any,
    ) -> CapabilityResult:
        settings = get_settings()
        last_exc: Exception | None = None
        for attempt in range(1, settings.max_retries + 1):
            try:
                return await factory()
            except CapabilityError as exc:
                last_exc = exc
                self._events.emit(
                    RuntimeEvent(
                        "capability.retry",
                        execution_id,
                        attributes={
                            "step_id": step.id,
                            "attempt": attempt,
                            "error": str(exc),
                        },
                    )
                )
                if attempt < settings.max_retries:
                    delay = min(
                        settings.retry_base_delay_s * (2 ** (attempt - 1)),
                        settings.retry_max_delay_s,
                    )
                    await asyncio.sleep(delay)
        raise CapabilityError(
            f"step {step.id} failed after {settings.max_retries} retries: {last_exc}"
        ) from last_exc
