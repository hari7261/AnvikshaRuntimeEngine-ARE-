"""Concurrency and stress tests for the Anviksha Runtime Engine."""
from __future__ import annotations

import asyncio
from typing import Any

import pytest

from anviksha import Runtime, RuntimeConfig
from anviksha.exceptions import CapabilityError, PlanningError


class TestConcurrentExecution:

    def _make_runtime(self) -> Runtime:
        return Runtime(
            config=RuntimeConfig(register_llm=False),
        )

    def test_concurrent_calculations(self) -> None:
        r = self._make_runtime()
        goals = [f"{i} + {i * 2}" for i in range(20)]

        async def run_all() -> list[Any]:
            tasks = [r.aexecute(g) for g in goals]
            return await asyncio.gather(*tasks)

        results = asyncio.run(run_all())
        assert all(res.status.value == "succeeded" for res in results)
        assert all(res.confidence >= 0.99 for res in results)

    def test_high_concurrency_no_deadlock(self) -> None:
        r = self._make_runtime()

        async def worker(n: int) -> None:
            for _ in range(5):
                await r.aexecute(f"{n} + {n}")

        async def run_workers() -> None:
            await asyncio.gather(*[worker(i) for i in range(100)])

        asyncio.run(run_workers())

    def test_burst_then_steady(self) -> None:
        r = self._make_runtime()

        async def burst(n: int) -> None:
            await asyncio.gather(*[r.aexecute(f"{i} * {i}") for i in range(n)])

        async def steady(n: int) -> None:
            for i in range(n):
                await r.aexecute(f"{i} + 1")

        async def run() -> None:
            await burst(50)
            await steady(50)

        asyncio.run(run())

    def test_mixed_intents(self) -> None:
        r = self._make_runtime()
        goals = [
            ("2 + 2", "succeeded"),
            ("search for python", "succeeded"),
            ("evaluate 3 * 3", "succeeded"),
        ]

        async def run_mixed() -> None:
            for goal, expected in goals:
                res = await r.aexecute(goal)
                assert res.status.value == expected, f"goal={goal}: {res}"

        asyncio.run(run_mixed())

    def test_parallel_steps_run_concurrently(self) -> None:
        from anviksha.capabilities.base import CapabilityMetadata, CapabilityResult
        from anviksha.capabilities.registry import CapabilityRegistry
        from anviksha.execution.engine import ExecutionEngine
        from anviksha.observability.events import InMemoryEventSink
        from anviksha.state.manager import StateManager
        from anviksha.types import CapabilityKind, ExecutionPlan, Intent, PlanStep

        delay = 0.2

        class SlowCap:
            metadata = CapabilityMetadata(
                id="test.slow", name="Slow", kind=CapabilityKind.TOOL,
                supported_intents=frozenset({Intent.GENERAL}),
                deterministic=True,
            )
            async def execute(self, arguments: Any) -> CapabilityResult:
                await asyncio.sleep(delay)
                return CapabilityResult(output="done", confidence=1.0)

        registry = CapabilityRegistry()
        registry.register(SlowCap())
        engine = ExecutionEngine(registry, StateManager(), InMemoryEventSink())
        plan = ExecutionPlan(
            "p1", Intent.GENERAL,
            (
                PlanStep("s1", "test.slow", Intent.GENERAL, {}),
                PlanStep("s2", "test.slow", Intent.GENERAL, {}),
                PlanStep("s3", "test.slow", Intent.GENERAL, {}),
            ),
        )

        async def run() -> float:
            start = asyncio.get_event_loop().time()
            await engine.execute(plan)
            return asyncio.get_event_loop().time() - start

        elapsed = asyncio.run(run())
        assert elapsed < delay * 2, f"took {elapsed:.2f}s, expected < {delay*2:.2f}s (parallel)"

    def test_nonexistent_intent_raises_planning_error(self) -> None:
        r = self._make_runtime()

        async def run() -> None:
            with pytest.raises(PlanningError, match="no capability registered"):
                await r.aexecute("summarize this text")

        asyncio.run(run())
