"""Comprehensive tests for the Anviksha Runtime Engine.

No silent fallbacks. Every configuration choice is explicit.
Every error is clear and actionable.
"""
from __future__ import annotations

import asyncio
import os
import tempfile
from typing import Any, Mapping

import pytest

from anviksha import ExecutionConstraints, Runtime, RuntimeConfig
from anviksha.capabilities import (
    CalculatorCapability,
    Capability,
    CapabilityMetadata,
    CapabilityRegistry,
    LLMCapability,
)
from anviksha.capabilities.base import CapabilityResult
from anviksha.exceptions import (
    CapabilityError,
    ConfigurationError,
    PlanningError,
    PolicyViolationError,
)
from anviksha.plugins import Plugin, PluginMetadata
from anviksha.state import PersistentStateManager, StateManager, StateTransition
from anviksha.types import ExecutionStatus, Intent


# ===================================================================
# Runtime end-to-end tests
# ===================================================================

class TestRuntimeEndToEnd:

    def _make_runtime(self) -> Runtime:
        """Create a Runtime that works without LLM env vars."""
        return Runtime(
            config=RuntimeConfig(register_llm=False),
        )

    def test_deterministic_calculation(self) -> None:
        response = self._make_runtime().execute("2 + 3 * 4")

        assert response.status is ExecutionStatus.SUCCEEDED
        assert response.output == 14.0
        assert response.confidence >= 0.99
        assert response.metadata["estimated_cost"] == 0.0
        assert "builtin.calculator" in response.diagnostics[0]

    def test_no_llm_raises_planning_error_for_general_intent(self) -> None:
        r = self._make_runtime()
        with pytest.raises(PlanningError, match="no capability registered for intent 'general'"):
            r.execute("Tell me a story")

    def test_async_execution(self) -> None:
        r = self._make_runtime()

        response = asyncio.run(r.aexecute("2 + 2"))

        assert response.output == 4.0
        assert response.metadata["events"]
        assert response.metadata["timeline"]

    def test_policy_blocks_low_confidence_response(self) -> None:
        class LowConfidenceCap:
            metadata = CapabilityMetadata(
                id="test.low_confidence",
                name="Low Confidence",
                kind="model",
                supported_intents=frozenset({Intent.GENERAL}),
                deterministic=True,
            )
            async def execute(self, arguments: Mapping[str, Any]) -> CapabilityResult:
                return CapabilityResult(output="risky", confidence=0.3)
        registry = CapabilityRegistry()
        registry.register(LowConfidenceCap())
        runtime = Runtime(
            registry=registry,
            config=RuntimeConfig(
                register_builtins=False, register_llm=False, auto_discover_plugins=False,
            ),
        )
        with pytest.raises(PolicyViolationError, match="confidence"):
            runtime.execute("hello", constraints=ExecutionConstraints(min_confidence=0.9))

    def test_policy_passes_high_confidence_response(self) -> None:
        response = self._make_runtime().execute(
            "2 + 2", constraints=ExecutionConstraints(min_confidence=0.9)
        )
        assert response.output == 4.0

    def test_streaming(self) -> None:
        r = self._make_runtime()

        async def collect() -> list[Any]:
            results: list[Any] = []
            async for chunk in r.astream("2 + 3"):
                results.append(chunk)
            return results

        chunks = asyncio.run(collect())
        assert chunks == [5.0]

    def test_offline_only_constraint(self) -> None:
        response = self._make_runtime().execute(
            "2 + 2", constraints=ExecutionConstraints(offline_only=True)
        )
        assert response.output == 4.0

    def test_max_latency_constraint(self) -> None:
        response = self._make_runtime().execute(
            "2 + 2", constraints=ExecutionConstraints(max_latency_ms=100)
        )
        assert response.output == 4.0

    def test_max_cost_constraint(self) -> None:
        response = self._make_runtime().execute(
            "2 + 2", constraints=ExecutionConstraints(max_cost=0.0)
        )
        assert response.output == 4.0

    def test_allowed_capabilities_filters_all(self) -> None:
        with pytest.raises(PlanningError, match="no capability"):
            self._make_runtime().execute(
                "2 + 2",
                constraints=ExecutionConstraints(
                    allowed_capabilities=frozenset({"nonexistent"})
                ),
            )

    def test_empty_goal_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            self._make_runtime().execute("")

    def test_no_capabilities_at_all(self) -> None:
        registry = CapabilityRegistry()
        runtime = Runtime(
            registry=registry,
            config=RuntimeConfig(
                register_builtins=False,
                register_llm=False,
                auto_discover_plugins=False,
            ),
        )
        with pytest.raises(PlanningError, match="no capability registered"):
            runtime.execute("2 + 2")

    def test_retry_on_capability_failure(self) -> None:
        call_count: int = 0

        class FlakyCap:
            metadata = CapabilityMetadata(
                id="test.flaky",
                name="Flaky",
                kind="tool",
                supported_intents=frozenset({Intent.GENERAL}),
                deterministic=True,
            )

            async def execute(self, arguments: Mapping[str, Any]) -> CapabilityResult:
                nonlocal call_count
                call_count += 1
                if call_count < 2:
                    raise CapabilityError("transient failure")
                return CapabilityResult(output="recovered")

        registry = CapabilityRegistry()
        registry.register(FlakyCap())
        runtime = Runtime(
            registry=registry,
            config=RuntimeConfig(
                register_builtins=False,
                register_llm=False,
                auto_discover_plugins=False,
            ),
        )
        response = runtime.execute("retry test")
        assert response.output == "recovered"
        assert call_count == 2

    def test_register_llm_without_env_raises_configuration_error(self) -> None:
        if os.environ.get("ANVIKSHA_LLM_API_KEY"):
            pytest.skip("LLM env vars are set")
        with pytest.raises(ConfigurationError, match="LLM is not configured"):
            Runtime(config=RuntimeConfig(register_llm=True))


class TestLLMNotConfigured:

    def test_llm_capability_raises_configuration_error(self) -> None:
        if os.environ.get("ANVIKSHA_LLM_API_KEY"):
            pytest.skip("LLM env vars are set")
        with pytest.raises(ConfigurationError, match="LLM not configured"):
            LLMCapability()


# ===================================================================
# Planner / intent classification tests
# ===================================================================

class TestIntentClassification:

    def _make_runtime(self) -> Runtime:
        return Runtime(config=RuntimeConfig(register_llm=False))

    @pytest.mark.parametrize(
        ("goal", "expected"),
        [
            ("2 + 3", 5.0),
            ("10 - 4", 6.0),
            ("3 * 7", 21.0),
            ("100 / 5", 20.0),
            ("2 ** 10", 1024.0),
            ("(2 + 3) * 4", 20.0),
        ],
    )
    def test_mathematical_computation(self, goal: str, expected: float) -> None:
        assert self._make_runtime().execute(goal).output == expected

    @pytest.mark.parametrize(
        "goal",
        [
            "summarize this article",
            "give me a summary",
            "What is the capital of France?",
            "translate hello to french",
            "classify this text",
        ],
    )
    def test_non_math_intents_without_llm_raise_planning_error(self, goal: str) -> None:
        with pytest.raises(PlanningError, match="no capability registered"):
            self._make_runtime().execute(goal)


# ===================================================================
# Capability registry tests
# ===================================================================

class TestCapabilityRegistry:

    def test_register_and_get(self) -> None:
        registry = CapabilityRegistry()
        cap = CalculatorCapability()
        registry.register(cap)
        assert registry.get("builtin.calculator") is cap

    def test_duplicate_registration_raises_error(self) -> None:
        registry = CapabilityRegistry()
        registry.register(CalculatorCapability())
        with pytest.raises(ConfigurationError, match="already registered"):
            registry.register(CalculatorCapability())

    def test_get_unknown_capability_raises_error(self) -> None:
        registry = CapabilityRegistry()
        with pytest.raises(PlanningError, match="not registered"):
            registry.get("nonexistent")

    def test_find_by_intent(self) -> None:
        registry = CapabilityRegistry()
        registry.register(CalculatorCapability())

        candidates = registry.find(Intent.MATHEMATICAL_COMPUTATION, ExecutionConstraints())
        assert len(candidates) == 1
        assert candidates[0].metadata.id == "builtin.calculator"

    def test_find_with_allowed_filter(self) -> None:
        registry = CapabilityRegistry()
        registry.register(CalculatorCapability())

        candidates = registry.find(
            Intent.MATHEMATICAL_COMPUTATION,
            ExecutionConstraints(allowed_capabilities=frozenset({"nonexistent"})),
        )
        assert len(candidates) == 0

    def test_find_no_match_returns_empty_list(self) -> None:
        registry = CapabilityRegistry()
        registry.register(CalculatorCapability())
        candidates = registry.find(Intent.GENERAL, ExecutionConstraints())
        assert candidates == []


# ===================================================================
# Calculator capability tests
# ===================================================================

class TestCalculator:

    @pytest.mark.parametrize(
        ("expr", "expected"),
        [("2+2", 4.0), ("10/3", 3.3333333333333335), ("-5", -5.0)],
    )
    def test_valid_expressions(self, expr: str, expected: float) -> None:
        calc = CalculatorCapability()
        result = asyncio.run(calc.execute({"expression": expr}))
        assert result.output == expected

    def test_invalid_expression_raises_value_error(self) -> None:
        calc = CalculatorCapability()
        with pytest.raises(ValueError, match="not a valid"):
            asyncio.run(calc.execute({"expression": "hello + world"}))


# ===================================================================
# State manager tests
# ===================================================================

class TestStateManager:

    def test_record_and_timeline(self) -> None:
        mgr = StateManager()
        mgr.record(StateTransition("exec-1", ExecutionStatus.PLANNING))
        mgr.record(StateTransition("exec-1", ExecutionStatus.RUNNING))
        mgr.record(StateTransition("exec-1", ExecutionStatus.SUCCEEDED))
        assert len(mgr.timeline("exec-1")) == 3

    def test_timeline_unknown_execution(self) -> None:
        mgr = StateManager()
        assert mgr.timeline("nonexistent") == ()

    def test_state_isolation(self) -> None:
        mgr = StateManager()
        mgr.record(StateTransition("a", ExecutionStatus.PLANNING))
        mgr.record(StateTransition("b", ExecutionStatus.RUNNING))
        assert len(mgr.timeline("a")) == 1
        assert len(mgr.timeline("b")) == 1


class TestPersistentStateManager:

    def test_persist_and_reload(self, tmp_path: Any) -> None:
        db = str(tmp_path / "state.db")
        mgr = PersistentStateManager(db)
        mgr.record(StateTransition("e1", ExecutionStatus.PLANNING))
        mgr.record(StateTransition("e1", ExecutionStatus.SUCCEEDED))
        assert len(mgr.timeline("e1")) == 2
        mgr.close()

        mgr2 = PersistentStateManager(db)
        assert len(mgr2.timeline("e1")) == 2
        mgr2.close()


# ===================================================================
# Policy engine tests
# ===================================================================

class TestPolicyEngine:

    def test_minimum_confidence_passes(self) -> None:
        from anviksha.policy.engine import MinimumConfidencePolicy
        from anviksha.types import ExecutionPlan, ExecutionRequest, RuntimeResponse

        policy = MinimumConfidencePolicy()
        request = ExecutionRequest(
            goal="test", constraints=ExecutionConstraints(min_confidence=0.5)
        )
        policy.validate_plan(request, ExecutionPlan("e1", Intent.GENERAL, ()))

        response = RuntimeResponse("e1", ExecutionStatus.SUCCEEDED, "ok", 0.8, {})
        policy.validate_response(request, response)

    def test_minimum_confidence_fails(self) -> None:
        from anviksha.policy.engine import MinimumConfidencePolicy
        from anviksha.types import ExecutionRequest, RuntimeResponse

        policy = MinimumConfidencePolicy()
        request = ExecutionRequest(
            goal="test", constraints=ExecutionConstraints(min_confidence=0.9)
        )
        response = RuntimeResponse("e1", ExecutionStatus.SUCCEEDED, "ok", 0.5, {})
        with pytest.raises(PolicyViolationError, match="confidence"):
            policy.validate_response(request, response)


# ===================================================================
# Plugin SDK tests
# ===================================================================

class TestPluginSDK:

    def test_plugin_registers_capabilities(self) -> None:
        meta = CapabilityMetadata(
            id="test.plugin_cap",
            name="Plugin Cap",
            kind="tool",
            supported_intents=frozenset({Intent.GENERAL}),
            deterministic=True,
        )

        class PluginCap:
            metadata = meta

            async def execute(self, arguments: Mapping[str, Any]) -> CapabilityResult:
                return CapabilityResult(output="plugin_ok")

        class TestPlugin:
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(name="test_plugin", version="1.0", category="capability")

            def capabilities(self) -> tuple[Capability, ...]:
                return (PluginCap(),)

        runtime = Runtime(
            plugins=(TestPlugin(),),
            config=RuntimeConfig(
                register_builtins=False,
                register_llm=False,
                auto_discover_plugins=False,
            ),
        )
        response = runtime.execute("test plugin")
        assert response.output == "plugin_ok"


# ===================================================================
# Execution engine & plan validation tests
# ===================================================================

class TestExecutionEngine:

    async def test_empty_plan_raises_error(self) -> None:
        from anviksha.execution.engine import ExecutionEngine
        from anviksha.observability.events import InMemoryEventSink
        from anviksha.types import ExecutionPlan, Intent

        engine = ExecutionEngine(CapabilityRegistry(), StateManager(), InMemoryEventSink())
        with pytest.raises(PlanningError, match="no steps"):
            await engine.execute(ExecutionPlan("e1", Intent.GENERAL, ()))

    async def test_missing_capability_in_plan(self) -> None:
        from anviksha.execution.engine import ExecutionEngine
        from anviksha.observability.events import InMemoryEventSink
        from anviksha.types import ExecutionPlan, Intent, PlanStep

        engine = ExecutionEngine(CapabilityRegistry(), StateManager(), InMemoryEventSink())
        plan = ExecutionPlan(
            "e1", Intent.GENERAL, (PlanStep("s1", "nonexistent", Intent.GENERAL, {}),)
        )
        with pytest.raises(PlanningError, match="not registered"):
            await engine.execute(plan)

    async def test_unresolved_dependency(self) -> None:
        from anviksha.execution.engine import ExecutionEngine
        from anviksha.observability.events import InMemoryEventSink
        from anviksha.types import ExecutionPlan, Intent, PlanStep

        registry = CapabilityRegistry()
        registry.register(CalculatorCapability())
        engine = ExecutionEngine(registry, StateManager(), InMemoryEventSink())
        plan = ExecutionPlan(
            "e1",
            Intent.GENERAL,
            (
                PlanStep(
                    "s2",
                    "builtin.calculator",
                    Intent.MATHEMATICAL_COMPUTATION,
                    {},
                    depends_on=("s1",),
                ),
            ),
        )
        with pytest.raises(PlanningError, match="depends on unresolved"):
            await engine.execute(plan)


# ===================================================================
# Configuration tests
# ===================================================================

class TestConfiguration:

    def test_settings_defaults(self) -> None:
        from anviksha.config import RuntimeSettings

        settings = RuntimeSettings()
        assert settings.max_retries == 3
        assert settings.llm_model == ""
        assert not settings.llm_configured
        assert not settings.state_persistence_enabled


# ===================================================================
# Public API surface tests
# ===================================================================

class TestPublicAPI:

    def test_top_level_exports(self) -> None:
        import anviksha

        assert hasattr(anviksha, "Runtime")
        assert hasattr(anviksha, "RuntimeConfig")
        assert hasattr(anviksha, "ExecutionConstraints")
        assert hasattr(anviksha, "RuntimeResponse")
        assert hasattr(anviksha, "RuntimeSettings")
        assert hasattr(anviksha, "get_settings")

    def test_subpackage_exports(self) -> None:
        from anviksha.capabilities import (
            CalculatorCapability,
            Capability,
            CapabilityMetadata,
            CapabilityRegistry,
            LLMCapability,
        )
        from anviksha.planner import RuleBasedPlanner
        from anviksha.execution import ExecutionEngine
        from anviksha.policy import MinimumConfidencePolicy, Policy, PolicyEngine
        from anviksha.state import PersistentStateManager, StateManager, StateTransition
        from anviksha.observability import EventSink, InMemoryEventSink, RuntimeEvent
        from anviksha.plugins import Plugin, PluginMetadata, discover_capabilities, discover_plugins
        from anviksha.sdk import Runtime, RuntimeConfig
        from anviksha.types import (
            CapabilityKind,
            CapabilityResult,
            ExecutionConstraints,
            ExecutionPlan,
            ExecutionRequest,
            ExecutionStatus,
            Intent,
            PlanStep,
            RuntimeResponse,
        )
