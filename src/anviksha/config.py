"""Centralized runtime configuration from environment variables.

All values must be explicitly set via environment variables.
No hardcoded defaults that silently assume a provider.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class RuntimeSettings:
    llm_api_base: str = field(
        default_factory=lambda: os.getenv("ANVIKSHA_LLM_API_BASE", "")
    )
    llm_api_key: str = field(
        default_factory=lambda: os.getenv("ANVIKSHA_LLM_API_KEY", "")
    )
    llm_model: str = field(
        default_factory=lambda: os.getenv("ANVIKSHA_LLM_MODEL", "")
    )
    llm_max_tokens: int = int(os.getenv("ANVIKSHA_LLM_MAX_TOKENS", "1024"))
    llm_temperature: float = float(os.getenv("ANVIKSHA_LLM_TEMPERATURE", "0.7"))

    max_retries: int = int(os.getenv("ANVIKSHA_MAX_RETRIES", "3"))
    retry_base_delay_s: float = float(os.getenv("ANVIKSHA_RETRY_BASE_DELAY_S", "1.0"))
    retry_max_delay_s: float = float(os.getenv("ANVIKSHA_RETRY_MAX_DELAY_S", "30.0"))

    state_db_path: str = field(
        default_factory=lambda: os.getenv("ANVIKSHA_STATE_DB_PATH", "")
    )
    otel_service_name: str = field(
        default_factory=lambda: os.getenv("OTEL_SERVICE_NAME", "anviksha-runtime")
    )
    otel_endpoint: str = field(
        default_factory=lambda: os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    )

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_base and self.llm_api_key and self.llm_model)

    @property
    def state_persistence_enabled(self) -> bool:
        return bool(self.state_db_path)

    @property
    def otel_enabled(self) -> bool:
        return bool(self.otel_endpoint)


def get_settings() -> RuntimeSettings:
    return RuntimeSettings()
