# Anviksha Runtime Engine (ARE)

Anviksha Runtime Engine is an adaptive AI execution runtime. Applications describe intent; the runtime plans, selects capabilities, executes the plan, records state, applies policies, and returns a structured response.

This repository now contains a production-oriented Python package scaffold that follows the Version 1 RFC boundaries:

- **Public SDK**: `Runtime.execute`, `Runtime.aexecute`, and `Runtime.astream` expose developer intent without leaking internals.
- **Planner**: a deterministic rule-based planner classifies intent and creates immutable execution plans.
- **Capability Registry**: capabilities advertise metadata used for cost, latency, reliability, determinism, and offline filtering.
- **Execution Engine**: executes the planner's steps exactly as specified and does not re-plan.
- **Policy Engine**: validates plans and responses, including minimum confidence enforcement.
- **State Manager**: records immutable execution transitions for replay and diagnostics.
- **Observability**: emits structured runtime events for planning and capability execution.
- **Plugin SDK**: defines metadata and capability contracts for local runtime extensions.

## Quick start

```python
from anviksha import Runtime

runtime = Runtime()
response = runtime.execute("2 + 3 * 4")

print(response.output)      # 14.0
print(response.diagnostics) # planner selection details
```

## Development

```bash
python -m pytest -q
python -m compileall -q src tests
```

The package targets Python 3.12+ and keeps provider-specific integrations outside the runtime core.
