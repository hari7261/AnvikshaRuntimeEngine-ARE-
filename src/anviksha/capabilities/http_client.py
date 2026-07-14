"""HTTP fetch capability for requesting external resources."""
from __future__ import annotations

from typing import Any, Mapping

import httpx

from anviksha.capabilities.base import CapabilityMetadata
from anviksha.exceptions import CapabilityError
from anviksha.types import CapabilityKind, CapabilityResult, Intent


class HTTPCapability:
    metadata = CapabilityMetadata(
        id="builtin.http",
        name="HTTP Client",
        kind=CapabilityKind.TOOL,
        supported_intents=frozenset({Intent.TOOL_INVOCATION, Intent.RETRIEVAL}),
        average_latency_ms=500,
        cost_per_call=0.0,
        reliability=0.85,
        deterministic=False,
        offline=False,
    )

    async def execute(self, arguments: Mapping[str, Any]) -> CapabilityResult:
        url = str(arguments.get("url", ""))
        if not url:
            raise CapabilityError("url is required")
        method = str(arguments.get("method", "GET")).upper()
        headers = dict(arguments.get("headers", {}))
        timeout = float(arguments.get("timeout", 10.0))
        body = arguments.get("body")
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.request(method, url, headers=headers, json=body)
                resp.raise_for_status()
                content = resp.text
                return CapabilityResult(
                    output=content,
                    confidence=0.9,
                    metadata={"url": url, "status_code": resp.status_code, "method": method},
                )
        except httpx.HTTPStatusError as exc:
            raise CapabilityError(
                f"HTTP {exc.response.status_code} for {url}: {exc.response.text[:500]}"
            ) from exc
        except httpx.RequestError as exc:
            raise CapabilityError(f"HTTP request to {url} failed: {exc}") from exc
