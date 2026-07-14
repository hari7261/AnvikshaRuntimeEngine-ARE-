"""Plugin auto-discovery via Python entry points."""
from __future__ import annotations

from importlib.metadata import EntryPoint, entry_points
from typing import TYPE_CHECKING, Any

from anviksha.capabilities.base import Capability
from anviksha.exceptions import PluginError

if TYPE_CHECKING:
    from anviksha.plugins.sdk import Plugin


def discover_plugins() -> tuple[Plugin, ...]:
    discovered: list[Plugin] = []
    for ep in entry_points(group="anviksha.plugins"):
        obj = _load_entry_point(ep)
        if obj is not None and hasattr(obj, "capabilities"):
            discovered.append(obj)
    return tuple(discovered)


def discover_capabilities() -> tuple[Capability, ...]:
    caps: list[Capability] = []
    for ep in entry_points(group="anviksha.plugins"):
        obj = _load_entry_point(ep)
        if obj is not None and hasattr(obj, "execute") and hasattr(obj, "metadata"):
            caps.append(obj)
    return tuple(caps)


def _load_entry_point(ep: EntryPoint) -> Any:
    try:
        cls = ep.load()
    except Exception as exc:
        raise PluginError(
            f"failed to load plugin entry point '{ep.name}': {exc}"
        ) from exc
    if not isinstance(cls, type):
        raise PluginError(
            f"plugin entry point '{ep.name}' must be a class, got {type(cls).__name__}"
        )
    try:
        return cls()
    except Exception as exc:
        raise PluginError(
            f"failed to instantiate plugin '{ep.name}': {exc}"
        ) from exc
