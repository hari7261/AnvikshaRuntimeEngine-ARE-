# Quickstart Guide

## Basic Usage

```python
from anviksha import Runtime, RuntimeConfig

# Create runtime without LLM (offline mode)
runtime = Runtime(config=RuntimeConfig(register_llm=False))

# Execute synchronously
response = runtime.execute("2 + 2")
print(response.output)  # 4.0

# Execute asynchronously
import asyncio
response = asyncio.run(runtime.aexecute("3 * 7"))
print(response.output)  # 21.0

# Stream results
async for chunk in runtime.astream("100 / 5"):
    print(chunk)  # 20.0
```

## Using Constraints

```python
from anviksha import ExecutionConstraints

# Require minimum confidence
response = runtime.execute(
    "2 + 2",
    constraints=ExecutionConstraints(min_confidence=0.9)
)

# Offline-only (no network calls)
response = runtime.execute(
    "search for python",
    constraints=ExecutionConstraints(offline_only=True)
)
```

## Using Memory

```python
asyncio.run(runtime.aexecute(
    "store my name as Alice",
    constraints=ExecutionConstraints(allowed_capabilities=frozenset({"builtin.memory"}))
))
```


## Self-hosted FastAPI Server

Anviksha can run as an embedded Python SDK or as a self-hosted FastAPI app that you deploy yourself. Install the optional server extra:

```bash
pip install "anviksha[server]"
```

Start the offline-first API:

```bash
anviksha serve --host 0.0.0.0 --port 8000
```

Execute a goal over HTTP:

```bash
curl -X POST http://localhost:8000/execute \
  -H 'content-type: application/json' \
  -d '{"goal":"2 + 2","constraints":{"offline_only":true}}'
```

Embed the ASGI app when you already own the deployment shell:

```python
from anviksha.server import create_app

app = create_app()
```

The server exposes `/healthz`, `/readyz`, `/metrics`, `/capabilities`, `/execute`, `/stream`, `/jobs`, `/jobs/{job_id}`, and `/sessions/{session_id}`. LLM support remains opt-in with `anviksha serve --with-llm` after setting `ANVIKSHA_LLM_API_BASE`, `ANVIKSHA_LLM_API_KEY`, and `ANVIKSHA_LLM_MODEL`.


### Server platform controls

The FastAPI adapter is still self-hosted and in-process, but it includes the first platform-layer controls applications need before adding external databases or queues:

- request correlation via `x-request-id`
- idempotent `/execute` calls via `idempotency-key`
- optional API-key/Bearer auth with `ANVIKSHA_SERVER_API_KEY`
- optional per-tenant/IP rate limiting with `ANVIKSHA_SERVER_RATE_LIMIT_PER_MINUTE`
- tenant/project scoping with `x-anviksha-tenant` and `x-anviksha-project`
- session history with `x-anviksha-session-id` and `/sessions/{session_id}`
- async job submission and polling with `/jobs` and `/jobs/{job_id}`
- Prometheus-style text counters at `/metrics`


For complete HTTP deployment details, see the [Self-hosted FastAPI Server](server.md) guide.
