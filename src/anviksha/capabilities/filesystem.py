"""Filesystem read/write capability with path sandboxing."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from anviksha.capabilities.base import CapabilityMetadata
from anviksha.exceptions import CapabilityError
from anviksha.types import CapabilityKind, CapabilityResult, Intent


class FilesystemCapability:
    metadata = CapabilityMetadata(
        id="builtin.filesystem",
        name="Filesystem",
        kind=CapabilityKind.TOOL,
        supported_intents=frozenset({Intent.TOOL_INVOCATION}),
        average_latency_ms=10,
        cost_per_call=0.0,
        reliability=1.0,
        deterministic=True,
        offline=True,
    )

    def __init__(self, sandbox_path: str | None = None) -> None:
        self._sandbox = Path(sandbox_path).resolve() if sandbox_path else None

    async def execute(self, arguments: Mapping[str, Any]) -> CapabilityResult:
        action = str(arguments.get("action", "read")).lower()
        path_str = str(arguments.get("path", ""))
        if not path_str:
            raise CapabilityError("path is required")
        resolved = Path(path_str).resolve()
        if self._sandbox and not str(resolved).startswith(str(self._sandbox)):
            raise CapabilityError(
                f"path '{path_str}' is outside sandbox '{self._sandbox}'"
            )
        if action == "read":
            if not resolved.exists():
                raise CapabilityError(f"path does not exist: {path_str}")
            if not resolved.is_file():
                raise CapabilityError(f"path is not a file: {path_str}")
            content = resolved.read_text(encoding="utf-8")
            return CapabilityResult(
                output=content,
                confidence=1.0,
                metadata={"path": path_str, "size": len(content)},
            )
        if action == "write":
            content = str(arguments.get("content", ""))
            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(content, encoding="utf-8")
            return CapabilityResult(
                output=f"wrote {len(content)} bytes to {path_str}",
                confidence=1.0,
                metadata={"path": path_str, "bytes": len(content)},
            )
        if action == "list":
            if not resolved.exists():
                raise CapabilityError(f"path does not exist: {path_str}")
            if not resolved.is_dir():
                raise CapabilityError(f"path is not a directory: {path_str}")
            entries = [str(p.relative_to(resolved)) for p in resolved.iterdir()]
            return CapabilityResult(
                output=entries,
                confidence=1.0,
                metadata={"path": path_str, "entries": len(entries)},
            )
        if action == "exists":
            return CapabilityResult(
                output=resolved.exists(),
                confidence=1.0,
                metadata={"path": path_str},
            )
        raise CapabilityError(f"unknown filesystem action: {action}")
