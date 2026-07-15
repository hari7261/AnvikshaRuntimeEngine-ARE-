"""Public Python SDK runtime entry point with full production wiring."""
from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Mapping
from dataclasses import dataclass
from typing import Any

from anviksha.capabilities import Capability
from anviksha.capabilities.builtins import CalculatorCapability
from anviksha.capabilities.filesystem import FilesystemCapability
from anviksha.capabilities.http_client import HTTPCapability
from anviksha.capabilities.llm import LLMCapability
from anviksha.capabilities.memory import MemoryCapability
from anviksha.capabilities.python_exec import PythonCapability
from anviksha.capabilities.registry import CapabilityRegistry
from anviksha.capabilities.retrieval import RetrievalCapability
from anviksha.config import get_settings
from anviksha.exceptions import ConfigurationError
from anviksha.execution.engine import ExecutionEngine
from anviksha.observability.events import InMemoryEventSink, RuntimeEvent
from anviksha.planner.default import RuleBasedPlanner
from anviksha.plugins.discovery import discover_capabilities
from anviksha.plugins.sdk import Plugin
from anviksha.policy.engine import PolicyEngine, production_policy_pack
from anviksha.state.manager import StateManager, StateTransition
from anviksha.state.persistence import PersistentStateManager
from anviksha.types import (
    ExecutionConstraints,
    ExecutionRequest,
    ExecutionStatus,
    RuntimeResponse,
)


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    register_builtins: bool = True
    register_llm: bool = True
    auto_discover_plugins: bool = True
    include_trace_metadata: bool = True
    enable_persistent_state: bool = False
    enable_otel: bool = False


class Runtime:
    def __init__(
        self,
        config: RuntimeConfig | None = None,
        registry: CapabilityRegistry | None = None,
        plugins: tuple[Plugin, ...] | None = None,
    ) -> None:
        self.config = config or RuntimeConfig()
        self.registry = registry or CapabilityRegistry()
        settings = get_settings()

        registered_ids = {c.metadata.id for c in self.registry.all()}

        if self.config.register_builtins:
            builtins: tuple[Capability, ...] = (
                CalculatorCapability(),
                RetrievalCapability(),
                MemoryCapability(),
                PythonCapability(),
                HTTPCapability(),
                FilesystemCapability(),
            )
            for cap in builtins:
                if cap.metadata.id not in registered_ids:
                    self.registry.register(cap)
                    registered_ids.add(cap.metadata.id)

        if self.config.register_llm:
            if not settings.llm_configured:
                raise ConfigurationError(
                    "RuntimeConfig.register_llm=True but LLM is not configured.\n"
                    "Set these environment variables and try again:\n"
                    "  ANVIKSHA_LLM_API_BASE  (e.g. https://api.openai.com/v1)\n"
                    "  ANVIKSHA_LLM_API_KEY   (your API key)\n"
                    "  ANVIKSHA_LLM_MODEL     (e.g. gpt-4o-mini)\n\n"
                    "Or set RuntimeConfig(register_llm=False) to run without an LLM."
                )
            llm = LLMCapability()
            if llm.metadata.id not in registered_ids:
                self.registry.register(llm)

        if self.config.auto_discover_plugins:
            for cap in discover_capabilities():
                if cap.metadata.id not in registered_ids:
                    self.registry.register(cap)
                    registered_ids.add(cap.metadata.id)

        if plugins:
            for plugin in plugins:
                for cap in plugin.capabilities():
                    if cap.metadata.id not in registered_ids:
                        self.registry.register(cap)
                        registered_ids.add(cap.metadata.id)

        if self.config.enable_persistent_state:
            if not settings.state_persistence_enabled:
                raise ConfigurationError(
                    "RuntimeConfig.enable_persistent_state=True but "
                    "ANVIKSHA_STATE_DB_PATH is not set."
                )
            self.state: StateManager = PersistentStateManager(settings.state_db_path)
        else:
            self.state = StateManager()

        self.events = InMemoryEventSink()
        self.planner = RuleBasedPlanner(self.registry)
        self.policies = PolicyEngine(production_policy_pack())
        self.executor = ExecutionEngine(self.registry, self.state, self.events)

    def execute(
        self,
        goal: str,
        inputs: Mapping[str, Any] | None = None,
        constraints: ExecutionConstraints | None = None,
    ) -> RuntimeResponse:
        return asyncio.run(self.aexecute(goal, inputs, constraints))

    async def aexecute(
        self,
        goal: str,
        inputs: Mapping[str, Any] | None = None,
        constraints: ExecutionConstraints | None = None,
    ) -> RuntimeResponse:
        request = ExecutionRequest(
            goal=goal,
            inputs=inputs or {},
            constraints=constraints or ExecutionConstraints(),
        )
        self.state.record(StateTransition(request.execution_id, ExecutionStatus.PLANNING))
        self.events.emit(RuntimeEvent("planning.started", request.execution_id))
        plan = self.planner.plan(request)
        self.policies.validate_plan(request, plan)
        self.events.emit(
            RuntimeEvent(
                "planning.completed",
                request.execution_id,
                attributes={"intent": plan.intent, "steps": len(plan.steps)},
            )
        )
        result = await self.executor.execute(plan)
        response = RuntimeResponse(
            request.execution_id,
            ExecutionStatus.SUCCEEDED,
            result.output,
            result.confidence,
            self._metadata(request.execution_id, plan.estimated_cost),
            plan.diagnostics,
        )
        self.policies.validate_response(request, response)
        self.state.record(
            StateTransition(
                request.execution_id, ExecutionStatus.SUCCEEDED, payload=response.metadata
            )
        )
        return response

    async def astream(
        self,
        goal: str,
        inputs: Mapping[str, Any] | None = None,
        constraints: ExecutionConstraints | None = None,
    ) -> AsyncGenerator[Any, None]:
        request = ExecutionRequest(
            goal=goal,
            inputs=inputs or {},
            constraints=constraints or ExecutionConstraints(),
        )
        self.state.record(StateTransition(request.execution_id, ExecutionStatus.PLANNING))
        self.events.emit(RuntimeEvent("planning.started", request.execution_id))
        plan = self.planner.plan(request)
        self.policies.validate_plan(request, plan)
        self.events.emit(
            RuntimeEvent(
                "planning.completed",
                request.execution_id,
                attributes={"intent": plan.intent, "steps": len(plan.steps)},
            )
        )
        final_output: Any = None
        async for _step_id, output in self.executor.execute_stream(plan):
            final_output = output
            yield output
        response = RuntimeResponse(
            request.execution_id,
            ExecutionStatus.SUCCEEDED,
            final_output,
            1.0,
            self._metadata(request.execution_id, plan.estimated_cost),
            plan.diagnostics,
        )
        self.policies.validate_response(request, response)
        self.state.record(
            StateTransition(
                request.execution_id, ExecutionStatus.SUCCEEDED, payload=response.metadata
            )
        )

    def _metadata(self, execution_id: str, estimated_cost: float) -> dict[str, Any]:
        data: dict[str, Any] = {"estimated_cost": estimated_cost}
        if self.config.include_trace_metadata:
            data["timeline"] = self.state.timeline(execution_id)
            data["events"] = tuple(
                e for e in self.events.events if e.execution_id == execution_id
            )
        return data
