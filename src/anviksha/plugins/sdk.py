"""Minimal local plugin SDK."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
from anviksha.capabilities.base import Capability

@dataclass(frozen=True, slots=True)
class PluginMetadata:
    name: str
    version: str
    category: str
    runtime_version: str = "0.1"

class Plugin(Protocol):
    @property
    def metadata(self) -> PluginMetadata: ...
    def capabilities(self) -> tuple[Capability, ...]: ...
