# Anviksha Runtime Engine

A production-grade, adaptive AI execution runtime for building reliable AI applications.

## Features

- **Intent Classification** — Rule-based planner with 9 intent types
- **Multi-Capability Execution** — Calculator, LLM, Retrieval, Memory, Python, HTTP, Filesystem
- **Parallel Execution** — Automatic dependency resolution with concurrent step execution
- **Policy Engine** — Pluggable pre/post execution validation
- **State Management** — Immutable state transitions with SQLite persistence
- **Observability** — Structured events with optional OpenTelemetry export
- **Plugin SDK** — Entry-point auto-discovery for third-party capabilities
- **Safety** — No `eval()`, sandboxed filesystem, restricted Python execution

## Quickstart

```python
from anviksha import Runtime, RuntimeConfig

runtime = Runtime(config=RuntimeConfig(register_llm=False))

# Arithmetic
response = runtime.execute("2 + 3 * 4")
print(response.output)  # 14.0

# Search
response = runtime.execute("search for python runtime")
print(response.output)  # ranked results

# Python evaluation
response = runtime.execute("evaluate sum(range(100))")
print(response.output)  # 4950
```

## Installation

```bash
pip install anviksha
```
