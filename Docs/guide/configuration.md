# Configuration

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ANVIKSHA_LLM_API_BASE` | — | OpenAI-compatible API base URL |
| `ANVIKSHA_LLM_API_KEY` | — | API key |
| `ANVIKSHA_LLM_MODEL` | — | Model name (e.g., `gpt-4o-mini`) |
| `ANVIKSHA_LLM_MAX_TOKENS` | `1024` | Max tokens per response |
| `ANVIKSHA_LLM_TEMPERATURE` | `0.7` | Sampling temperature |
| `ANVIKSHA_MAX_RETRIES` | `3` | Max capability retry attempts |
| `ANVIKSHA_RETRY_BASE_DELAY_S` | `1.0` | Initial retry backoff (seconds) |
| `ANVIKSHA_RETRY_MAX_DELAY_S` | `30.0` | Maximum retry delay |
| `ANVIKSHA_STATE_DB_PATH` | — | SQLite path for persistent state |
| `OTEL_SERVICE_NAME` | `anviksha-runtime` | OpenTelemetry service name |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | — | OpenTelemetry collector endpoint |

## RuntimeConfig

```python
from anviksha import RuntimeConfig

config = RuntimeConfig(
    register_builtins=True,        # Enable calculator, memory, retrieval, etc.
    register_llm=True,             # Enable LLM (requires env vars)
    auto_discover_plugins=True,    # Auto-discover installed plugins
    include_trace_metadata=True,   # Include timeline/events in responses
    enable_persistent_state=False, # Enable SQLite state persistence
    enable_otel=False,             # Enable OpenTelemetry export
)
```
