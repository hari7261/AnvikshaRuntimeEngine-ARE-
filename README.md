# Anviksha Runtime Engine (ARE)

Anviksha Runtime Engine is an adaptive AI execution runtime. Applications describe intent; the runtime plans, selects capabilities, executes the plan, records state, applies policies, and returns a structured response — all without developers manually orchestrating models, tools, or workflows.

**Philosophy:** *Define the destination. The runtime decides the journey.*

---

## Quick Start

```python
# 1. Configure LLM (required for non-math intents)
#    export ANVIKSHA_LLM_API_BASE=https://api.openai.com/v1
#    export ANVIKSHA_LLM_API_KEY=sk-...
#    export ANVIKSHA_LLM_MODEL=gpt-4o-mini

# 2. Use the runtime
from anviksha import Runtime

runtime = Runtime()

# Math → calculator (deterministic, no LLM)
response = runtime.execute("2 + 3 * 4")
print(response.output)      # 14.0

# Non-math → LLM (requires env vars above)
response = runtime.execute("What is Python?")

# Inspect execution
print(response.status)       # succeeded
print(response.diagnostics)  # planner decisions
print(response.metadata)     # timeline, events, cost
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
│  executes steps, retries on failure │
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
| HTTP LLM capability (OpenAI-compatible) | ✅ |
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

All configuration is via environment variables. See [Docs/RELEASE-v1.0.md](Docs/RELEASE-v1.0.md) for the full reference.

---

## Development

```bash
pip install -e ".[dev]"
python -m pytest -v
python -m compileall -q src tests
```

Requires Python 3.12+.

---

## Project Structure

```
src/anviksha/
├── __init__.py
├── config.py             # Env-based RuntimeSettings
├── exceptions.py         # Exception hierarchy
├── types.py              # Immutable data models
├── capabilities/         # Capability protocol, registry, calculator, LLM
├── execution/            # ExecutionEngine with retry + streaming
├── observability/        # Event sink, OpenTelemetry export
├── planner/              # RuleBasedPlanner (intent classification)
├── plugins/              # Plugin protocol, entry-point discovery
├── policy/               # PolicyEngine, MinimumConfidencePolicy
├── sdk/                  # Runtime — the primary developer API
└── state/                # In-memory + SQLite state manager
```

---

## Testing

49 tests covering all components — runtime E2E, planner, registry, calculator, LLM config, state, policies, plugins, execution, validation, and public API.

---

## License

MIT
