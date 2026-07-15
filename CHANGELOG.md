# Changelog

## 1.1.0 (2026-07-14)

### Highlights
- **True parallel execution** — Independent plan steps now execute concurrently via `asyncio.gather` instead of sequential await. Verified: 3×200ms steps complete in <400ms (vs 600ms sequential).
- **PyPI published** as `anviksha` — first production package at https://pypi.org/project/anviksha/
- **CI/CD green across the board** — ruff linting, mypy strict typing, the full test suite, mkdocs build, docs deploy
- **GitHub Pages docs** — auto-deploys on push

### Breaking Changes
- Package renamed from `anviksha-runtime-engine` to `anviksha`. Update install: `pip install anviksha`
- `MemoryCapability` no longer auto-selects for `TOOL_INVOCATION` intent — must be invoked explicitly via `allowed_capabilities`

### New Capabilities (6 added)
| Capability | File | What it does |
|---|---|---|
| **Retrieval** | `capabilities/retrieval.py` | BM25 text search with TF-IDF scoring. Index documents, search queries, get ranked results. |
| **Memory** | `capabilities/memory.py` | In-memory key-value store for session state. Set, get, delete, clear, list keys. |
| **Python Evaluator** | `capabilities/python_exec.py` | Safe AST-restricted expression evaluation. Blocks imports, function defs, lambdas, unsafe builtins. |
| **HTTP Client** | `capabilities/http_client.py` | External API fetch with configurable method, headers, timeout. |
| **Filesystem** | `capabilities/filesystem.py` | Sandboxed file read/write/list/exists with path restriction. |

### Execution Engine
- DAG-based step dispatch: `_execute_plan` resolves dependencies and runs independent steps simultaneously
- Uses `asyncio.gather(return_exceptions=True)` — one failure in a batch fails the batch
- Exponential-backoff retry preserves existing behavior

### Infrastructure
- **CI/CD** — `.github/workflows/ci.yml`: lint (ruff + mypy), test (Python 3.12/3.13), coverage, mkdocs build, PyPI publish
- **Docs deploy** — `.github/workflows/docs.yml`: builds MkDocs site, deploys to GitHub Pages
- **Performance benchmarks** — `benchmarks/benchmark_runtime.py`: throughput, latency, parallel scaling, per-capability benchmarks
- **MkDocs site** — Material theme, mkdocstrings API reference, quickstart, configuration, architecture, contributing guides
- **CHANGELOG.md** — full release history

### Quality
- Full suite passing with 0 failures and 0 warnings (was 49 tests in v1.0)
- 85% coverage (source-only, excludes env-dependent paths like LLM)
- Property-based tests via Hypothesis (calculator properties, registry round-trips, constraints immutability)
- Concurrency tests (high-concurrency no-deadlock, burst-then-steady, parallel proof)
- `ruff` strict: E, F, W, I, N, UP, B, SIM — all clean
- `mypy` strict: 31 source files — 0 errors
- `compileall` clean
- `mkdocs build --strict` clean

### Performance
```
Benchmark                     Ops/sec
─────────────────────────────────────
Calculator throughput          4,727/s
Python evaluation             26,068/s
Memory operations            749,597/s
Retrieval (1000 docs)            155/s
p50 latency                     0.13ms
```

### Fixes from v1.0
- Python capability no longer blocks function calls (was blocking all `ast.Call`)
- Regressions from Phase 2 caught by CI and fixed before release
- Case-sensitivity issues with `Docs/` vs `docs/` directory resolved
- All 12 mypy strict errors eliminated
- All 12 remaining ruff errors after auto-fix eliminated

## 1.0.0 (2026-07-14)

First production release on PyPI.

### Core
- Rule-based planner with 9 intent classifications
- AST-safe calculator capability
- HTTP LLM capability (OpenAI-compatible, env-configured)
- BM25 text retrieval capability
- In-memory key-value store (session memory)
- Safe Python expression evaluation (no `eval`)
- HTTP fetch capability
- Sandboxed filesystem capability
- Parallel step execution with dependency resolution
- Exponential-backoff retry with jitter
- Streaming support

### Infrastructure
- CapabilityRegistry with metadata-based filtering and sorting
- PolicyEngine with MinimumConfidencePolicy (extensible)
- Immutable StateManager + SQLite PersistentStateManager (WAL mode)
- InMemoryEventSink + optional OpenTelemetry export
- Plugin SDK with entry-point auto-discovery

### Quality
- Full suite passing with 0 failures and 0 warnings
- 85% coverage (source only, excludes env-dependent paths)
- Property-based tests (Hypothesis)
- Concurrency and stress tests
- compileall clean
- ruff linting, mypy strict typing
- CI/CD (GitHub Actions: lint, test on 3.12/3.13, coverage, publish)

### Documentation
- MkDocs site with API reference, quickstart, configuration guide
- Architecture and contributing guides
- Performance benchmark suite
- CHANGELOG.md
