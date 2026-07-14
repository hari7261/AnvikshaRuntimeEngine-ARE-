"""Centralized structured telemetry primitives."""
from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class RuntimeEvent:
    name: str
    execution_id: str
    timestamp: float = field(default_factory=time)
    attributes: dict[str, Any] = field(default_factory=dict)

class EventSink(Protocol):
    def emit(self, event: RuntimeEvent) -> None: ...

class InMemoryEventSink:
    def __init__(self) -> None: self.events: list[RuntimeEvent] = []
    def emit(self, event: RuntimeEvent) -> None: self.events.append(event)
