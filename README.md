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


## Self-hosted FastAPI Server

Anviksha is designed for GitHub/PyPI distribution: you install the runtime, then host it inside your own app, worker, VM, container, or Kubernetes cluster. The project does not require an Anviksha-managed cloud service.

Install the optional FastAPI adapter:

```bash
pip install "anviksha[server]"
```

Run the self-hosted API locally:

```bash
anviksha serve --host 0.0.0.0 --port 8000
```

Or embed it in your own ASGI application:

```python
from anviksha.server import create_app

app = create_app()
```

Full server documentation lives in `Docs/guide/server.md`.

The server is offline-first by default and exposes:

| Endpoint | Purpose |
|---|---|
| `GET /healthz` | process health check |
| `GET /readyz` | runtime readiness and capability count |
| `GET /capabilities` | registered capability metadata |
| `POST /execute` | execute one goal and return a structured response |
| `POST /stream` | stream newline-delimited JSON chunks |
| `POST /jobs` | enqueue an async self-hosted execution job |
| `GET /jobs/{job_id}` | inspect job state/result |
| `DELETE /jobs/{job_id}` | mark queued/running in-memory jobs canceled |
| `GET /sessions/{session_id}` | inspect session execution/job history |
| `GET /metrics` | expose simple Prometheus-style counters |
| `GET /dashboard` | expose lightweight operational dashboard |
| `POST /evaluations/smoke` | run deterministic runtime smoke evaluations |

Example request:

```bash
curl -X POST http://localhost:8000/execute \
  -H 'content-type: application/json' \
  -d '{"goal":"2 + 3 * 4","constraints":{"offline_only":true}}'
```


Self-hosted platform headers are supported without adding a managed Anviksha cloud dependency:

| Header | Purpose |
|---|---|
| `x-request-id` | caller-provided request correlation ID; generated when absent |
| `idempotency-key` | caches successful `/execute` responses per tenant/project/session |
| `x-api-key` or `Authorization: Bearer ...` | optional auth when `ANVIKSHA_SERVER_API_KEY` is set |
| `x-anviksha-tenant` | tenant scope, defaults to `default` |
| `x-anviksha-project` | project scope, defaults to `default` |
| `x-anviksha-session-id` | session scope for `/sessions/{session_id}` history |

Optional server environment variables:

| Variable | Purpose |
|---|---|
| `ANVIKSHA_SERVER_API_KEY` | require API-key/Bearer auth for every endpoint |
| `ANVIKSHA_SERVER_RATE_LIMIT_PER_MINUTE` | enable per-tenant/IP in-memory rate limiting when greater than `0` |
| `ANVIKSHA_SERVER_REGISTER_LLM` | enable LLM registration for embedded ASGI deployments |
| `ANVIKSHA_SERVER_JOB_STORE_PATH` | persist async job/session metadata to a JSON file |

Enable LLM-backed capabilities only when the deployment owner explicitly configures them:

```bash
export ANVIKSHA_LLM_API_BASE=https://api.openai.com/v1
export ANVIKSHA_LLM_API_KEY=...
export ANVIKSHA_LLM_MODEL=...
anviksha serve --with-llm
```

---

## End-to-End Production Readiness

The runtime now covers the full self-hosted path for application teams: SDK execution, deterministic and LLM-backed capabilities, policy enforcement, state timelines, persistence, plugins, observability, HTTP serving, durable job metadata, smoke evaluations, and an operational dashboard.

Implemented production-readiness surfaces:

1. **Self-hostable runtime gateway** — FastAPI/ASGI adapter with auth hooks, request IDs, streaming responses, rate limits, OpenAPI docs, sessions, metrics, idempotency, and tenant/project scoping.
2. **Capability packaging and discovery** — built-in capabilities ship with metadata and plugin entry-point discovery for external capability packages.
3. **Production policy pack** — minimum confidence, tool allowlists, cost budgets, and PII output blocking run by default.
4. **Durable async jobs** — set `ANVIKSHA_SERVER_JOB_STORE_PATH` to persist job/session metadata across server restarts.
5. **Evaluation and regression harness** — `POST /evaluations/smoke` runs deterministic calculator and Python execution checks through the live runtime.
6. **Operational dashboard** — `GET /dashboard` exposes a lightweight text dashboard for requests, executions, jobs, sessions, and capabilities.

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
