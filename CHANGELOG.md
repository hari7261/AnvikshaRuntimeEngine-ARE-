# Changelog

## 1.1.0 (2026-07-14)

### Changed
- **True parallel execution**: Independent plan steps now execute concurrently via `asyncio.gather` instead of sequential await
- **Docs deployed to GitHub Pages** via dedicated workflow
- Added `CHANGELOG.md` with full release history

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
- 96 tests, 0 failures, 0 warnings
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
