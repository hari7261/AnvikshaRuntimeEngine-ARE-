# Contributing

## Setup

```bash
git clone https://github.com/hari7261/AnvikshaRuntimeEngine_ARE
cd AnvikshaRuntimeEngine_ARE
pip install -e ".[dev,lint,docs]"
```

## Running Tests

```bash
pytest tests/ -v                       # All tests
pytest tests/ --cov                    # With coverage
pytest tests/test_capabilities.py -v   # Capability-specific tests
pytest tests/test_concurrency.py -v    # Concurrency tests
pytest tests/test_property.py -v       # Property-based tests
```

## Linting

```bash
ruff check src/anviksha/ tests/
mypy src/anviksha/
```

## Building Docs

```bash
mkdocs serve
```

## Benchmarks

```bash
python benchmarks/benchmark_runtime.py
```

## Release Process

1. Update version in `pyproject.toml`
2. Commit and tag: `git tag vX.Y.Z && git push --tags`
3. GitHub Actions publishes to PyPI automatically
