# Self-hosted FastAPI Server

Anviksha is distributed as a GitHub/PyPI framework, not as an Anviksha-managed cloud service. The FastAPI adapter lets application teams run the runtime in their own process, container, VM, Kubernetes cluster, or existing ASGI application.

Use this mode when you want the runtime to be callable by multiple apps or services over HTTP while still keeping deployment, credentials, storage, policies, and scaling under your control.

## Install

```bash
pip install "anviksha[server]"
```

The base `anviksha` package stays lightweight. The `server` extra adds FastAPI and Uvicorn.

## Run from the CLI

```bash
anviksha serve --host 0.0.0.0 --port 8000
```

For local development with reload:

```bash
anviksha serve --reload
```

LLM support is explicit and opt-in. Set the LLM environment variables, then start the server with `--with-llm`:

```bash
export ANVIKSHA_LLM_API_BASE=https://api.openai.com/v1
export ANVIKSHA_LLM_API_KEY=...
export ANVIKSHA_LLM_MODEL=...
anviksha serve --with-llm
```

## Embed in an ASGI app

```python
from anviksha.server import create_app

app = create_app()
```

You can also pass a preconfigured `Runtime` instance or `RuntimeConfig` to `create_app()` if your service owns runtime construction.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/healthz` | Process health check. |
| `GET` | `/readyz` | Runtime readiness, capability count, and uptime. |
| `GET` | `/metrics` | Prometheus-style text counters. |
| `GET` | `/capabilities` | Registered capability metadata. |
| `POST` | `/execute` | Execute one goal and return a structured response. |
| `POST` | `/stream` | Stream newline-delimited JSON events. |
| `POST` | `/jobs` | Enqueue an async in-memory job. |
| `GET` | `/jobs/{job_id}` | Inspect job state and result. |
| `DELETE` | `/jobs/{job_id}` | Mark queued/running in-memory jobs canceled. |
| `GET` | `/sessions/{session_id}` | Inspect session execution and job history. |

## Execute a goal

```bash
curl -X POST http://localhost:8000/execute \
  -H 'content-type: application/json' \
  -H 'x-request-id: demo-request-1' \
  -H 'x-anviksha-tenant: demo-tenant' \
  -H 'x-anviksha-project: demo-project' \
  -H 'x-anviksha-session-id: demo-session' \
  -H 'idempotency-key: demo-2-plus-2' \
  -d '{"goal":"2 + 2","constraints":{"offline_only":true}}'
```

Example response shape:

```json
{
  "execution_id": "...",
  "status": "succeeded",
  "output": 4.0,
  "confidence": 1.0,
  "metadata": {
    "estimated_cost": 0.0
  },
  "diagnostics": ["selected builtin.calculator for mathematical_computation"],
  "request_id": "demo-request-1",
  "tenant_id": "demo-tenant",
  "project_id": "demo-project",
  "session_id": "demo-session",
  "cached": false
}
```

## Stream a response

```bash
curl -N -X POST http://localhost:8000/stream \
  -H 'content-type: application/json' \
  -d '{"goal":"2 + 2"}'
```

The stream uses newline-delimited JSON:

```json
{"type":"chunk","request_id":"...","output":4.0}
{"type":"completed","request_id":"..."}
```

## Run an async job

```bash
JOB_ID=$(curl -s -X POST http://localhost:8000/jobs \
  -H 'content-type: application/json' \
  -H 'x-anviksha-session-id: demo-session' \
  -d '{"goal":"2 + 5"}' | python -c 'import json,sys; print(json.load(sys.stdin)["job_id"])')

curl http://localhost:8000/jobs/$JOB_ID
```

Jobs are intentionally in-memory in the current adapter. They are useful for local/self-hosted execution and for defining the HTTP contract. For multi-worker production deployments, replace this layer with a durable queue adapter such as Redis, Celery, Dramatiq, Arq, Temporal, or another user-owned backend.

## Inspect session history

```bash
curl http://localhost:8000/sessions/demo-session
```

Sessions are scoped by `x-anviksha-tenant` and `x-anviksha-project`. A request using a different tenant/project receives a generic `404` so scoped data is not leaked.

## Platform headers

| Header | Purpose |
|---|---|
| `x-request-id` | Caller-provided correlation ID. Generated when absent. |
| `idempotency-key` | Caches successful `/execute` responses per tenant/project/session. |
| `x-api-key` | Optional API key when `ANVIKSHA_SERVER_API_KEY` is set. |
| `Authorization: Bearer ...` | Alternative bearer form for the same API key. |
| `x-anviksha-tenant` | Tenant scope. Defaults to `default`. |
| `x-anviksha-project` | Project scope. Defaults to `default`. |
| `x-anviksha-session-id` | Session scope for execution/job history. |

## Server environment variables

| Variable | Default | Purpose |
|---|---|---|
| `ANVIKSHA_SERVER_API_KEY` | empty | Require API-key/Bearer auth when set. |
| `ANVIKSHA_SERVER_RATE_LIMIT_PER_MINUTE` | `0` | Enable in-memory per-tenant/IP rate limiting when greater than `0`. |
| `ANVIKSHA_SERVER_REGISTER_LLM` | false | Enable LLM registration for embedded ASGI deployments. |
| `ANVIKSHA_LLM_API_BASE` | empty | OpenAI-compatible LLM base URL when LLM is enabled. |
| `ANVIKSHA_LLM_API_KEY` | empty | LLM API key when LLM is enabled. |
| `ANVIKSHA_LLM_MODEL` | empty | LLM model name when LLM is enabled. |

## Production readiness notes

The adapter is a self-hosted platform foundation, not a managed cloud. It intentionally uses in-memory idempotency, jobs, sessions, metrics, and rate limits so the core package remains simple and easy to install.

For serious multi-worker production, add user-owned adapters for:

- durable jobs and cancellation,
- Postgres or another queryable state store,
- Redis or another distributed cache/rate limiter,
- object storage for artifacts,
- external metrics and traces,
- richer policy packs,
- model/provider routing,
- capability marketplace/versioning.

That path keeps Anviksha aligned with the PyPI/GitHub model: Anviksha ships the runtime and adapters; users own deployment and infrastructure.
