"""Capability contracts used by planner and executor."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping, Protocol, runtime_checkable
from anviksha.types import CapabilityKind, CapabilityResult, Intent

@dataclass(frozen=True, slots=True)
class CapabilityMetadata:
    id: str
    name: str
    kind: CapabilityKind
    supported_intents: frozenset[Intent]
    average_latency_ms: int = 100
    cost_per_call: float = 0.0
    reliability: float = 1.0
    deterministic: bool = False
    offline: bool = True

@runtime_checkable
class Capability(Protocol):
    @property
    def metadata(self) -> CapabilityMetadata: ...
    async def execute(self, arguments: Mapping[str, Any]) -> CapabilityResult: ...
