"""OpenTelemetry integration for runtime observability."""
from __future__ import annotations

from typing import Any

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    _OTEL_AVAILABLE = True
except ImportError:
    _OTEL_AVAILABLE = False

from anviksha.observability.events import RuntimeEvent


class OTelEventSink:
    """Event sink that exports spans via OpenTelemetry."""

    def __init__(self, endpoint: str, service_name: str = "anviksha-runtime") -> None:
        if not _OTEL_AVAILABLE:
            raise RuntimeError(
                "OpenTelemetry packages not installed. "
                "Install with: pip install anviksha[otel]"
            )
        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        self._tracer = trace.get_tracer(__name__)

    def emit(self, event: RuntimeEvent) -> None:
        with self._tracer.start_as_current_span(event.name) as span:
            span.set_attribute("execution_id", event.execution_id)
            for key, value in (event.attributes or {}).items():
                span.set_attribute(key, _serialize_attr(value))
            if event.name.endswith("completed"):
                span.set_status(trace.StatusCode.OK)
            elif event.name.endswith("failed"):
                span.set_status(trace.StatusCode.ERROR)


def _serialize_attr(value: Any) -> str:
    if isinstance(value, str | int | float | bool):
        return str(value)
    return str(value)
