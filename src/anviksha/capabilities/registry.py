"""Capability registry with deterministic selection metadata.

Every capability must be explicitly registered. The registry never silently
ignores registration requests — duplicate IDs raise ConfigurationError.
"""
from __future__ import annotations
from anviksha.capabilities.base import Capability
from anviksha.exceptions import ConfigurationError, PlanningError
from anviksha.types import ExecutionConstraints, Intent


class CapabilityRegistry:
    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}

    def register(self, capability: Capability) -> None:
        meta = capability.metadata
        if meta.id in self._capabilities:
            raise ConfigurationError(
                f"capability '{meta.id}' is already registered. "
                f"Each capability must have a unique id."
            )
        self._capabilities[meta.id] = capability

    def get(self, capability_id: str) -> Capability:
        try:
            return self._capabilities[capability_id]
        except KeyError:
            registered = list(self._capabilities.keys())
            raise PlanningError(
                f"capability '{capability_id}' is not registered. "
                f"Registered capabilities: {registered}"
            )

    def find(
        self, intent: Intent, constraints: ExecutionConstraints
    ) -> list[Capability]:
        candidates = [
            c for c in self._capabilities.values()
            if intent in c.metadata.supported_intents
        ]
        if constraints.allowed_capabilities is not None:
            candidates = [
                c for c in candidates
                if c.metadata.id in constraints.allowed_capabilities
            ]
            if not candidates:
                return []
        if constraints.offline_only:
            candidates = [c for c in candidates if c.metadata.offline]
        if constraints.max_latency_ms is not None:
            candidates = [
                c for c in candidates
                if c.metadata.average_latency_ms <= constraints.max_latency_ms
            ]
        if constraints.max_cost is not None:
            candidates = [
                c for c in candidates
                if c.metadata.cost_per_call <= constraints.max_cost
            ]
        return sorted(
            candidates,
            key=lambda c: (
                not c.metadata.deterministic,
                c.metadata.cost_per_call,
                c.metadata.average_latency_ms,
                -c.metadata.reliability,
            ),
        )

    def all(self) -> tuple[Capability, ...]:
        return tuple(self._capabilities.values())
