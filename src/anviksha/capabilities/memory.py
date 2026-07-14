"""In-memory key-value store capability for session state."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from anviksha.capabilities.base import CapabilityMetadata
from anviksha.exceptions import CapabilityError
from anviksha.types import CapabilityKind, CapabilityResult


class MemoryCapability:
    metadata = CapabilityMetadata(
        id="builtin.memory",
        name="Session Memory",
        kind=CapabilityKind.MEMORY,
        supported_intents=frozenset(),
        average_latency_ms=1,
        cost_per_call=0.0,
        reliability=1.0,
        deterministic=True,
        offline=True,
    )

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def execute(self, arguments: Mapping[str, Any]) -> CapabilityResult:
        action = arguments.get("action", "get")
        key = str(arguments.get("key", ""))
        if action == "set":
            value = str(arguments.get("value", ""))
            self._store[key] = value
            return CapabilityResult(
                output=f"stored {key}", confidence=1.0,
                metadata={"action": "set", "key": key},
            )
        if action == "get":
            value = self._store.get(key)
            if value is None:
                raise CapabilityError(f"key '{key}' not found in memory")
            return CapabilityResult(
                output=value, confidence=1.0,
                metadata={"action": "get", "key": key},
            )
        if action == "delete":
            self._store.pop(key, None)
            return CapabilityResult(
                output=f"deleted {key}", confidence=1.0,
                metadata={"action": "delete", "key": key},
            )
        if action == "clear":
            self._store.clear()
            return CapabilityResult(
                output="memory cleared", confidence=1.0,
                metadata={"action": "clear"},
            )
        if action == "keys":
            return CapabilityResult(
                output=list(self._store.keys()), confidence=1.0,
                metadata={"action": "keys", "count": len(self._store)},
            )
        raise CapabilityError(f"unknown memory action: {action}")

    def clear(self) -> None:
        self._store.clear()
