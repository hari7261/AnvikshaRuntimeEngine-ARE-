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
