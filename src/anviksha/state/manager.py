"""Immutable execution state timeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Any

from anviksha.types import ExecutionStatus


@dataclass(frozen=True, slots=True)
class StateTransition:
    execution_id: str
    status: ExecutionStatus
    timestamp: float = field(default_factory=time)
    step_id: str | None = None
    payload: Any = None

class StateManager:
    def __init__(self) -> None: self._items: dict[str, list[StateTransition]] = {}
    def record(self, transition: StateTransition) -> None:
        self._items.setdefault(transition.execution_id, []).append(transition)
    def timeline(self, execution_id: str) -> tuple[StateTransition, ...]:
        return tuple(self._items.get(execution_id, ()))
