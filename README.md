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

## Command Line

Install the package and run deterministic/offline tasks directly from a terminal:

```bash
anviksha "2 + 3 * 4"
anviksha --json "2 + 2"
anviksha --offline-only --min-confidence 0.9 "2 ** 10"
```

LLM-backed general, QA, summarization, translation, classification, and creative tasks are explicit:

```bash
export ANVIKSHA_LLM_API_BASE=https://api.openai.com/v1
export ANVIKSHA_LLM_API_KEY=...
export ANVIKSHA_LLM_MODEL=...
anviksha --with-llm "summarize this release note"
```

---

## Production Readiness: What To Build Next

The current runtime has a solid deterministic execution core, capability registry, policy checks, state timeline, persistence, plugins, and observability events. To make production AI backends smoother for application teams, the next implementation priorities are:

1. **Hosted runtime gateway** — expose the SDK through a FastAPI/ASGI service with auth, request IDs, streaming responses, rate limits, and OpenAPI docs.
2. **Capability marketplace and version pinning** — package reusable capabilities with semantic versions, health checks, signed metadata, and compatibility checks.
3. **Production policy packs** — add configurable policies for PII redaction, prompt-injection checks, cost budgets, tenant isolation, tool allowlists, and human approval gates.
4. **Durable async jobs** — add queue-backed execution for long-running plans, resumable state, cancellation, and result retrieval by execution ID.
5. **Evaluation and regression harness** — ship fixtures for quality, latency, cost, and safety evaluations before deployment.
6. **Operational dashboard** — turn runtime events and state into traces, metrics, alerts, replay, and per-capability performance reports.

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

The test suite covers unit, integration, concurrency, property-based, and CLI behavior.

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
