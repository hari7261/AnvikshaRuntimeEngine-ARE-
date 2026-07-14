# Anviksha Runtime Engine — v1.1.0 Release Notes

**Release Date:** July 14, 2026  
**Package:** `anviksha` (PyPI)  
**Install:** `pip install anviksha`  
**Documentation:** https://hari7261.github.io/AnvikshaRuntimeEngine_ARE/

---

## Overview

v1.1.0 is the first full production release of the Anviksha Runtime Engine on PyPI. It delivers 6 new capabilities, true parallel execution, comprehensive CI/CD, performance benchmarks, and a full documentation site.

The runtime grew from 49 to 97 tests (all passing), from 0 to 2 CI workflows (all green), and from a single test file to a structured test suite covering unit, integration, concurrency, and property-based testing.

---

## What's New in 1.1

### True Parallel Execution

The execution engine now dispatches independent plan steps concurrently:

```python
# In _execute_plan (engine.py):
results = await asyncio.gather(
    *tasks.values(), return_exceptions=True
)
```

Previously, even independent steps ran sequentially. Now a plan with 3 independent steps each taking 200ms completes in ~200ms instead of ~600ms.

### PyPI Publishing

First time on PyPI. The package was renamed from `anviksha-runtime-engine` to `anviksha`:

```bash
pip install anviksha
```

### CI/CD Pipeline

Two GitHub Actions workflows ensure code quality:

**CI (`ci.yml`):**
- `ruff check` — linting (E, F, W, I, N, UP, B, SIM)
- `mypy src/anviksha/` — strict type checking (31 files, 0 errors)
- `pytest tests/ --cov` — 97 tests, coverage reporting
- `mkdocs build --strict` — documentation build
- `python -m build` + PyPI publish (on tags)

**Docs Deploy (`docs.yml`):**
- Builds MkDocs site with Material theme
- Deploys to GitHub Pages automatically on push to main

### Documentation Site

Full MkDocs site at GitHub Pages:

- **Quickstart guide** — basic and async usage
- **Configuration reference** — all env vars and RuntimeConfig fields
- **API reference** — auto-generated from docstrings via mkdocstrings
- **Architecture overview** — component diagram and responsibilities
- **RFC index** — links to all 10 architecture RFCs
- **Contributing guide** — setup, testing, linting, releasing

### Performance Benchmarks

A benchmark suite at `benchmarks/benchmark_runtime.py`:

```
Benchmark                     Ops/sec
─────────────────────────────────────
Calculator throughput          4,727/s
Python evaluation             26,068/s
Memory operations            749,597/s
Retrieval (1000 docs)            155/s
Parallel scaling (25)         12,693/s
p50 latency                     0.13ms
p95 latency                     0.23ms
```

---

## Capability Reference

### Built-in Capabilities

All capabilities implement the `Capability` protocol from `capabilities/base.py`:

| Capability | ID | Intent | Deterministic | Offline | Cost |
|---|---|---|---|---|---|
| **Calculator** | `builtin.calculator` | `MATHEMATICAL_COMPUTATION` | ✅ | ✅ | $0 |
| **LLM** | `builtin.llm` | GENERAL, QA, SUMMARIZATION, TRANSLATION, CLASSIFICATION, CREATIVE_GENERATION | ❌ | ❌ | ~$0.002/call |
| **Retrieval** | `builtin.retrieval` | `RETRIEVAL` | ✅ | ✅ | $0 |
| **Memory** | `builtin.memory` | (explicit only) | ✅ | ✅ | $0 |
| **Python** | `builtin.python` | `TOOL_INVOCATION`, `MATHEMATICAL_COMPUTATION` | ✅ | ✅ | $0 |
| **HTTP** | `builtin.http` | `TOOL_INVOCATION`, `RETRIEVAL` | ❌ | ❌ | $0 |
| **Filesystem** | `builtin.filesystem` | `TOOL_INVOCATION` | ✅ | ✅ | $0 |

### Capability Selection

The `CapabilityRegistry.find()` method filters and sorts candidates:

1. **Filter** by allowed_capabilities, offline_only, max_latency_ms, max_cost
2. **Sort** by: deterministic first → lowest cost → lowest latency → highest reliability

The first candidate in the sorted list is selected by the planner.

---

## Configuration

### Environment Variables

| Variable | Default | Required for |
|---|---|---|
| `ANVIKSHA_LLM_API_BASE` | — | LLM capability |
| `ANVIKSHA_LLM_API_KEY` | — | LLM capability |
| `ANVIKSHA_LLM_MODEL` | — | LLM capability |
| `ANVIKSHA_LLM_MAX_TOKENS` | 1024 | LLM capability |
| `ANVIKSHA_LLM_TEMPERATURE` | 0.7 | LLM capability |
| `ANVIKSHA_MAX_RETRIES` | 3 | Execution engine |
| `ANVIKSHA_RETRY_BASE_DELAY_S` | 1.0 | Retry backoff |
| `ANVIKSHA_RETRY_MAX_DELAY_S` | 30.0 | Retry backoff cap |
| `ANVIKSHA_STATE_DB_PATH` | — | Persistent state |
| `OTEL_SERVICE_NAME` | `anviksha-runtime` | OpenTelemetry |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | — | OpenTelemetry export |

### RuntimeConfig

```python
from anviksha import RuntimeConfig

config = RuntimeConfig(
    register_builtins=True,        # Calculator, retrieval, memory, etc.
    register_llm=True,             # Requires env vars
    auto_discover_plugins=True,    # Entry-point plugins
    include_trace_metadata=True,   # Timeline + events in responses
    enable_persistent_state=False, # SQLite persistence
    enable_otel=False,             # OpenTelemetry export
)
```

---

## Test Report

```
tests/test_capabilities.py ................................... (35 tests)
tests/test_concurrency.py ......                       (6 tests)
tests/test_property.py .......                         (7 tests)
tests/test_runtime.py ................................. (49 tests)
────────────────────────────────────────────────────────────────
Total: 97 passed in 8-16s
```

### Coverage

```
TOTAL: 85% (source only, 31 modules)
```

Coverage gaps are in optional/dependent modules:
- `llm.py` (35%) — requires API key and network
- `plugins/discovery.py` (30%) — requires installed entry points
- `observability/otel.py` (0%) — requires opentelemetry-sdk

Core runtime modules (types, registry, planner, engine, state, policy) all exceed 90%.

---

## Developer Quick Start

```bash
# Clone and install
git clone https://github.com/hari7261/AnvikshaRuntimeEngine_ARE
cd AnvikshaRuntimeEngine_ARE
pip install -e ".[dev,lint,docs]"

# Run all checks
ruff check src/anviksha/ tests/
mypy src/anviksha/
pytest tests/ -v --cov
mkdocs build --strict
python benchmarks/benchmark_runtime.py
```

---

## Architecture

```
┌─────────────────────────────────────────┐
│            SDK (Runtime)                 │
│     execute / aexecute / astream        │
├─────────────────────────────────────────┤
│              Planner                     │
│     RuleBasedPlanner → ExecutionPlan     │
├─────────────────────────────────────────┤
│           PolicyEngine                   │
│     MinimumConfidencePolicy + custom     │
├─────────────────────────────────────────┤
│          ExecutionEngine                 │
│   DAG resolve → asyncio.gather → retry   │
├────────┬────────┬────────┬──────────────┤
│Capabili│ Policy │ State  │ Observability │
│ty      │ Engine │Manager │ EventSink     │
│Registry│        │+SQLite │ +OTel         │
├────────┴────────┴────────┴──────────────┤
│         Capabilities Layer               │
│ Calculator │ LLM │ Retrieval │ Memory    │
│ Python │ HTTP │ Filesystem │ Plugin     │
└─────────────────────────────────────────┘
```

---

## Migration from v0.2 / v1.0

1. Update install: `pip install -U anviksha`
2. Replace `from anviksha import ...` — imports are unchanged
3. `MemoryCapability` no longer auto-selects — pass `allowed_capabilities=frozenset({"builtin.memory"})` explicitly

---

## Future Directions

- **Multi-step chain planning** — Planner emits multiple steps with dependency edges for the engine to parallelize
- **Database capability** — SQLite/Postgres query capability
- **FastAPI integration** — Turn the Runtime into a deployable HTTP service
- **Docker image** — Containerized runtime for production deployment
- **gRPC capability** — Bidirectional streaming for real-time use cases

---

*For questions or contributions, open an issue at https://github.com/hari7261/AnvikshaRuntimeEngine_ARE*
