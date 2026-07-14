# Anviksha Runtime Engine (ARE)

Anviksha Runtime Engine is an adaptive AI execution runtime. Applications describe intent; the runtime plans, selects capabilities, executes the plan, records state, applies policies, and returns a structured response — all without developers manually orchestrating models, tools, or workflows.

**Philosophy:** *Define the destination. The runtime decides the journey.*

---

## Quick Start

```python
from anviksha import Runtime, RuntimeConfig

# Offline mode — no LLM required
runtime = Runtime(config=RuntimeConfig(register_llm=False))

# Math → calculator (deterministic)
response = runtime.execute("2 + 3 * 4")
print(response.output)        # 14.0

# Search → retrieval (BM25)
response = runtime.execute("search for python runtime")
print(response.output)        # ranked results

# Python evaluation (safe AST)
response = runtime.execute("evaluate sum(range(100))")
print(response.output)        # 4950

# Async
import asyncio
response = asyncio.run(runtime.aexecute("2 ** 10"))
print(response.output)        # 1024

# Inspect execution
print(response.status)        # succeeded
print(response.diagnostics)   # planner decisions
print(response.metadata)      # timeline, events, cost
```

---

## Architecture

```
Application
    │
    ▼
┌─────────────────────────────────────┐
│         Runtime (SDK)               │
│  execute / aexecute / astream       │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│         Planner                     │
│  classifies intent, selects caps    │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│      Policy Engine                  │
│  validates plan & response          │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│      Execution Engine               │
│  parallel step execution + retry    │
└─────────────────────────────────────┘
    │                           │
    ▼                           ▼
┌──────────┐           ┌──────────────┐
│ Capability│◄─────────│ State Manager│
│ Registry  │  events  │ + SQLite     │
└──────────┘           └──────────────┘
```

10 RFCs implemented: Runtime Architecture, Execution Lifecycle, Planner, Capability Registry, Execution Engine, Policy Engine, State Manager, Observability, Plugin SDK, Public Python SDK.

---

## Features

| Feature | Status |
|---|---|
| Intent classification (9 types) | ✅ |
| Safe AST-based calculator | ✅ |
| Text retrieval (BM25) | ✅ |
| Session memory (key-value) | ✅ |
| Safe Python evaluation | ✅ |
| HTTP fetch capability | ✅ |
| Sandboxed filesystem | ✅ |
| HTTP LLM capability (OpenAI-compatible) | ✅ |
| Parallel step execution | ✅ |
| Retry with exponential backoff | ✅ |
| Plan validation (dependencies, capability existence) | ✅ |
| Minimum confidence policy | ✅ |
| Immutable state timeline | ✅ |
| SQLite persistent state | ✅ |
| Structured observability events | ✅ |
| OpenTelemetry export (optional) | ✅ |
| Plugin auto-discovery (entry points) | ✅ |
| No silent fallbacks — every error is actionable | ✅ |

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `ANVIKSHA_LLM_API_BASE` | — | OpenAI-compatible API base URL |
| `ANVIKSHA_LLM_API_KEY` | — | API key |
| `ANVIKSHA_LLM_MODEL` | — | Model name |
| `ANVIKSHA_MAX_RETRIES` | `3` | Max capability retry attempts |
| `ANVIKSHA_RETRY_BASE_DELAY_S` | `1.0` | Initial retry backoff |
| `ANVIKSHA_RETRY_MAX_DELAY_S` | `30.0` | Maximum retry delay |
| `ANVIKSHA_STATE_DB_PATH` | — | SQLite path for persistence |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | — | OpenTelemetry endpoint |

---

## Performance

```
Benchmark                     Ops/sec
─────────────────────────────────────
Calculator throughput          4,727/s
Python evaluation             26,068/s
Memory operations            749,597/s
Retrieval (1000 docs)            155/s
p50 latency                     0.13ms
```

---

## Testing

96 tests (49 original + 47 new Phase 2) — unit, integration, concurrency, property-based.

```bash
pip install -e ".[dev]"
pytest tests/ -v --cov
```

---

## Project Structure

```
src/anviksha/
├── __init__.py
├── config.py                  # Env-based RuntimeSettings
├── exceptions.py              # Exception hierarchy
├── types.py                   # Immutable data models
├── capabilities/
│   ├── base.py                # Capability protocol & metadata
│   ├── registry.py            # Filtering/sorting registry
│   ├── builtins.py            # AST calculator
│   ├── llm.py                 # HTTP LLM capability
│   ├── retrieval.py           # BM25 text retrieval
│   ├── memory.py              # In-memory key-value store
│   ├── python_exec.py         # Safe Python evaluation
│   ├── http_client.py         # HTTP fetch capability
│   └── filesystem.py          # Sandboxed file I/O
├── execution/engine.py        # Parallel execution + retry
├── observability/events.py    # Structured event sink
├── planner/default.py         # Rule-based intent classifier
├── plugins/sdk.py             # Plugin protocol & metadata
├── plugins/discovery.py       # Entry-point auto-discovery
├── policy/engine.py           # Policy engine + min confidence
├── sdk/runtime.py             # Public Runtime API
└── state/manager.py           # Immutable state timeline
    state/persistence.py       # SQLite persistent state
```

---

## License

MIT
