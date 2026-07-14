"""HTTP-based LLM capability for OpenAI-compatible APIs.

Requires ANVIKSHA_LLM_API_BASE, ANVIKSHA_LLM_API_KEY, and ANVIKSHA_LLM_MODEL
to be set in the environment. Raises ConfigurationError if LLM is not configured.
"""
from __future__ import annotations

from typing import Any, Mapping

import httpx

from anviksha.capabilities.base import CapabilityMetadata
from anviksha.config import get_settings
from anviksha.exceptions import CapabilityError, ConfigurationError
from anviksha.types import CapabilityKind, CapabilityResult, Intent


class LLMCapability:
    metadata = CapabilityMetadata(
        id="builtin.llm",
        name="Language Model",
        kind=CapabilityKind.MODEL,
        supported_intents=frozenset({
            Intent.GENERAL,
            Intent.QUESTION_ANSWERING,
            Intent.SUMMARIZATION,
            Intent.TRANSLATION,
            Intent.CLASSIFICATION,
            Intent.CREATIVE_GENERATION,
            Intent.TOOL_INVOCATION,
        }),
        average_latency_ms=2000,
        cost_per_call=0.002,
        reliability=0.85,
        deterministic=False,
        offline=False,
    )

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.llm_configured:
            raise ConfigurationError(
                "LLM not configured. Set the following environment variables:\n"
                "  ANVIKSHA_LLM_API_BASE  (e.g. https://api.openai.com/v1)\n"
                "  ANVIKSHA_LLM_API_KEY   (your API key)\n"
                "  ANVIKSHA_LLM_MODEL     (e.g. gpt-4o-mini)"
            )
        self._api_base = settings.llm_api_base.rstrip("/")
        self._api_key = settings.llm_api_key
        self._model = settings.llm_model
        self._max_tokens = settings.llm_max_tokens
        self._temperature = settings.llm_temperature

    async def execute(self, arguments: Mapping[str, Any]) -> CapabilityResult:
        prompt = self._build_prompt(arguments)
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self._api_base}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self._model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": self._max_tokens,
                        "temperature": self._temperature,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return CapabilityResult(
                    output=content,
                    confidence=0.9,
                    metadata={
                        "provider": self._api_base,
                        "model": self._model,
                        "tokens": data.get("usage", {}),
                    },
                )
        except httpx.HTTPStatusError as exc:
            raise CapabilityError(
                f"LLM API returned {exc.response.status_code}: {exc.response.text}"
            ) from exc
        except httpx.RequestError as exc:
            raise CapabilityError(
                f"LLM request failed — check ANVIKSHA_LLM_API_BASE is reachable: {exc}"
            ) from exc

    def _build_prompt(self, arguments: Mapping[str, Any]) -> str:
        goal = str(arguments.get("goal", ""))
        context = arguments.get("previous_outputs", {})
        parts = [goal]
        if context:
            ctx_str = "\n".join(f"{k}: {v}" for k, v in context.items() if v)
            if ctx_str:
                parts.append(f"\nContext:\n{ctx_str}")
        return "\n".join(parts)
