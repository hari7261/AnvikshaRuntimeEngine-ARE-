# Anviksha Runtime Engine — Production Release v1.0

**Date:** July 14, 2026  
**Author:** Anviksha Core Team  
**Repository:** github.com/hari7261/AnvikshaRuntimeEngine_ARE

---

## Overview

Anviksha Runtime Engine (ARE) is an adaptive AI execution runtime. Applications describe intent; the runtime plans, selects capabilities, executes the plan, records state, applies policies, and returns a structured response — without requiring developers to manually orchestrate models, tools, or workflows.

This release marks the transition from prototype to production-ready infrastructure.

---

## Architecture (10 RFCs Implemented)

| RFC | Component | Status |
|-----|-----------|--------|
| 0001 | Runtime Architecture | ✅ Complete |
| 0002 | Execution Lifecycle | ✅ Complete |
| 0003 | Planner Architecture | ✅ Complete |
| 0004 | Capability Registry | ✅ Complete |
| 0005 | Execution Engine | ✅ Complete |
| 0006 | Policy Engine | ✅ Complete |
| 0007 | State Manager | ✅ Complete |
| 0008 | Observability & Telemetry | ✅ Complete |
| 0009 | Plugin SDK | ✅ Complete |
| 0010 | Public Python SDK | ✅ Complete |

---

## Package Structure

```
src/anviksha/
├── __init__.py              # Public API exports
├── config.py                # Environment-based configuration
├── exceptions.py            # Exception hierarchy
├── types.py                 # Immutable runtime data models
├── capabilities/
│   ├── __init__.py
│   ├── base.py              # Capability protocol + CapabilityMetadata
│   ├── builtins.py          # CalculatorCapability (AST-based, safe)
│   ├── llm.py               # HTTP-based LLM capability (OpenAI-compatible)
│   └── registry.py          # CapabilityRegistry with metadata filtering
├── execution/
│   ├── __init__.py
│   └── engine.py            # ExecutionEngine with retry + streaming
├── observability/
│   ├── __init__.py
│   ├── events.py            # RuntimeEvent + InMemoryEventSink
│   └── otel.py              # OpenTelemetry export (optional)
├── planner/
│   ├── __init__.py
│   └── default.py           # RuleBasedPlanner (intent classification)
├── plugins/
│   ├── __init__.py
│   ├── sdk.py               # Plugin protocol + PluginMetadata
│   └── discovery.py         # Entry-point based auto-discovery
├── policy/
│   ├── __init__.py
│   └── engine.py            # PolicyEngine + MinimumConfidencePolicy
├── sdk/
│   ├── __init__.py
│   └── runtime.py           # Runtime — the primary developer-facing API
└── state/
    ├── __init__.py
    ├── manager.py            # StateManager (in-memory, immutable)
    └── persistence.py        # PersistentStateManager (SQLite-backed)
```

---

## Production Features

### Core Execution
- **Rule-based planner** — classifies intent: math, summarization, translation, classification, retrieval, QA, general
- **Safe calculator** — AST-based arithmetic evaluation (no `eval()`)
- **HTTP LLM capability** — works with any OpenAI-compatible API (OpenAI, Anthropic, Ollama, vLLM)
- **Execution engine** — sequential step execution with plan validation
- **Status tracking** — PENDING → PLANNING → RUNNING → SUCCEEDED/FAILED/BLOCKED

### Resilience
- **Retry with exponential backoff** — configurable via env vars (`ANVIKSHA_MAX_RETRIES`, `ANVIKSHA_RETRY_BASE_DELAY_S`, `ANVIKSHA_RETRY_MAX_DELAY_S`)
- **Plan validation** — verifies all capabilities exist and dependency graph is satisfiable before execution
- **Capability-level retry** — transient failures retry automatically

### Governance
- **Policy engine** — pluggable validation before and after execution
- **Minimum confidence policy** — blocks responses below configurable threshold
- **Capability filtering** — filter by latency, cost, offline-only, allowed list

### Observability
- **Structured events** — every planning, execution, and policy decision emits typed `RuntimeEvent`
- **State timeline** — immutable `StateTransition` log per execution
- **Trace metadata** — attachable to every response
- **OpenTelemetry export** — optional OTLP span export (`pip install anviksha[otel]`)

### Plugin System
- **Plugin protocol** — standard interface for adding capabilities
- **Entry-point discovery** — `anviksha.plugins` group auto-loads installed packages
- **Explicit registration** — `Runtime(plugins=(...))` for programmatic use

### Persistence
- **In-memory state** — default, zero-config
- **SQLite state** — `PersistentStateManager` with WAL mode, thread-safe, auto-replay on reopen

### Error Handling
- **No silent fallbacks** — every configuration gap raises actionable `ConfigurationError`
- **Clear error messages** — each error states the problem, the cause, and the fix
- **Explicit hierarchy** — `AnvikshaError` → `ConfigurationError`, `PlanningError`, `CapabilityError`, `PolicyViolationError`, `PluginError`

---

## Configuration Reference

| Env Variable | Default | Description |
|---|---|---|
| `ANVIKSHA_LLM_API_BASE` | — | OpenAI-compatible API base URL |
| `ANVIKSHA_LLM_API_KEY` | — | API key |
| `ANVIKSHA_LLM_MODEL` | — | Model name (e.g. gpt-4o-mini) |
| `ANVIKSHA_LLM_MAX_TOKENS` | 1024 | Max tokens per response |
| `ANVIKSHA_LLM_TEMPERATURE` | 0.7 | LLM temperature |
| `ANVIKSHA_MAX_RETRIES` | 3 | Max capability retry attempts |
| `ANVIKSHA_RETRY_BASE_DELAY_S` | 1.0 | Initial retry delay (exponential) |
| `ANVIKSHA_RETRY_MAX_DELAY_S` | 30.0 | Maximum retry delay |
| `ANVIKSHA_STATE_DB_PATH` | — | Path to SQLite state database |
| `OTEL_SERVICE_NAME` | anviksha-runtime | OpenTelemetry service name |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | — | OTLP HTTP endpoint |

---

## Quick Start

```python
# Configure LLM (required for non-math intents)
# export ANVIKSHA_LLM_API_BASE=https://api.openai.com/v1
# export ANVIKSHA_LLM_API_KEY=sk-...
# export ANVIKSHA_LLM_MODEL=gpt-4o-mini

from anviksha import Runtime

runtime = Runtime()

# Math → calculator (deterministic, no LLM)
response = runtime.execute("2 + 3 * 4")
print(response.output)  # 14.0

# Non-math → LLM
response = runtime.execute("What is Python?")
print(response.output)
```

---

## Test Report

**Total:** 49 tests, 0 failures, 0 warnings  
**Coverage areas:**
- Runtime E2E: calculation, intent routing, streaming, constraints, policies
- Planner: all 9 intent classifications, error cases
- Capability registry: register/get/find/filter/duplicate/unknown
- Calculator: valid expressions, invalid expressions
- LLM capability: configuration validation
- State manager: in-memory timeline, SQLite persistence/replay, isolation
- Policy engine: pass/fail for minimum confidence
- Plugin SDK: capability registration via plugins
- Execution engine: empty plan, missing capability, unresolved dependency
- Plan validation: dependency resolution, capability existence
- Configuration: default settings
- Public API: top-level and subpackage exports

---

## Quick Reference — Error Messages

| Scenario | Error |
|---|---|
| LLM env vars missing | `ConfigurationError: LLM not configured. Set ANVIKSHA_LLM_API_BASE...` |
| `register_llm=True` but not configured | `ConfigurationError: RuntimeConfig.register_llm=True but LLM is not configured...` |
| No capability for intent | `PlanningError: no capability registered for intent 'general'. Registered capabilities: ['builtin.calculator']` |
| Unknown capability in plan | `PlanningError: capability 'builtin.nonexistent' is not registered. Registered capabilities: [...]` |
| Empty goal | `ValueError: goal must be a non-empty string` |
| Policy violation | `PolicyViolationError: confidence 0.50 below required 0.95` |
| Calculator invalid expression | `ValueError: 'hello + world' is not a valid arithmetic expression` |
| Duplicate capability | `ConfigurationError: capability 'builtin.calculator' is already registered` |
| Empty plan | `PlanningError: execution plan has no steps` |
| Unresolved dependency | `PlanningError: step s2 depends on unresolved step s1` |
| Plugin load failure | `PluginError: failed to load plugin entry point 'xxx': ...` |
| Persistent state without path | `ConfigurationError: enable_persistent_state=True but ANVIKSHA_STATE_DB_PATH is not set` |
