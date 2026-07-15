"""Performance benchmarks for the Anviksha Runtime Engine."""
from __future__ import annotations

import asyncio
import time
from typing import Any

from anviksha import Runtime, RuntimeConfig


def _make_runtime() -> Runtime:
    return Runtime(
        config=RuntimeConfig(register_llm=False),
    )


def benchmark_throughput(count: int = 500) -> dict[str, float]:
    r = _make_runtime()

    async def run_all() -> float:
        start = time.perf_counter()
        tasks = [r.aexecute(f"{i} + {i}") for i in range(count)]
        await asyncio.gather(*tasks)
        return time.perf_counter() - start

    elapsed = asyncio.run(run_all())
    return {
        "type": "throughput",
        "count": count,
        "total_seconds": round(elapsed, 3),
        "ops_per_second": round(count / elapsed, 1),
    }


def benchmark_latency_p50(count: int = 100) -> dict[str, float]:
    r = _make_runtime()
    latencies: list[float] = []

    async def measure() -> None:
        for i in range(count):
            start = time.perf_counter()
            await r.aexecute(f"{i} + 1")
            latencies.append((time.perf_counter() - start) * 1000)

    asyncio.run(measure())
    sorted_lats = sorted(latencies)
    p50 = sorted_lats[len(sorted_lats) // 2]
    p95 = sorted_lats[int(len(sorted_lats) * 0.95)]
    p99 = sorted_lats[int(len(sorted_lats) * 0.99)]
    return {
        "type": "latency",
        "count": count,
        "p50_ms": round(p50, 2),
        "p95_ms": round(p95, 2),
        "p99_ms": round(p99, 2),
        "min_ms": round(sorted_lats[0], 2),
        "max_ms": round(sorted_lats[-1], 2),
    }


def benchmark_parallel_scaling(
    concurrency_levels: tuple[int, ...] = (1, 5, 10, 25, 50),
) -> list[dict[str, float]]:
    results: list[dict[str, float]] = []
    async def run_batch(runtime: Runtime, concurrency: int) -> float:
        start = time.perf_counter()
        sem = asyncio.Semaphore(concurrency)

        async def limited(n: int) -> Any:
            async with sem:
                return await runtime.aexecute(f"{n} * {n}")

        tasks = [limited(i) for i in range(100)]
        await asyncio.gather(*tasks)
        return time.perf_counter() - start

    for concurrency in concurrency_levels:
        r = _make_runtime()

        elapsed = asyncio.run(run_batch(r, concurrency))
        results.append({
            "type": "parallel_scaling",
            "concurrency": concurrency,
            "total_seconds": round(elapsed, 3),
            "ops_per_second": round(100 / elapsed, 1),
        })
    return results


def benchmark_memory_capability_operations(count: int = 1000) -> dict[str, float]:
    from anviksha.capabilities import MemoryCapability

    cap = MemoryCapability()

    async def run_all() -> float:
        start = time.perf_counter()
        for i in range(count):
            await cap.execute({"action": "set", "key": f"k{i}", "value": f"v{i}"})
        for i in range(count):
            await cap.execute({"action": "get", "key": f"k{i}"})
        return time.perf_counter() - start

    elapsed = asyncio.run(run_all())
    return {
        "type": "memory_ops",
        "operations": count * 2,
        "total_seconds": round(elapsed, 3),
        "ops_per_second": round((count * 2) / elapsed, 1),
    }


def benchmark_python_capability(count: int = 500) -> dict[str, float]:
    from anviksha.capabilities import PythonCapability

    cap = PythonCapability()

    async def run_all() -> float:
        start = time.perf_counter()
        tasks = [cap.execute({"expression": f"sum(range({i}))"}) for i in range(1, count + 1)]
        await asyncio.gather(*tasks)
        return time.perf_counter() - start

    elapsed = asyncio.run(run_all())
    return {
        "type": "python_eval",
        "count": count,
        "total_seconds": round(elapsed, 3),
        "ops_per_second": round(count / elapsed, 1),
    }


def benchmark_retrieval_indexing(doc_count: int = 1000) -> dict[str, float]:
    from anviksha.capabilities import RetrievalCapability

    cap = RetrievalCapability()
    docs = {f"doc{i}": f"this is document number {i} with some content" for i in range(doc_count)}

    start = time.perf_counter()
    cap.index(docs)
    index_time = time.perf_counter() - start

    async def search() -> float:
        start = time.perf_counter()
        for _ in range(100):
            await cap.execute({"query": "document content"})
        return time.perf_counter() - start

    search_time = asyncio.run(search())
    return {
        "type": "retrieval",
        "documents": doc_count,
        "index_seconds": round(index_time, 4),
        "search_100_ops_seconds": round(search_time, 3),
        "search_per_second": round(100 / search_time, 1),
    }


if __name__ == "__main__":
    results: list[dict[str, float]] = []
    results.append(benchmark_throughput())
    results.append(benchmark_latency_p50())
    results.extend(benchmark_parallel_scaling())
    results.append(benchmark_memory_capability_operations())
    results.append(benchmark_python_capability())
    results.append(benchmark_retrieval_indexing())

    print("=" * 60)
    print("Anviksha Runtime Engine - Performance Benchmarks")
    print("=" * 60)
    for r in results:
        print(f"\n--- {r.pop('type', '?').replace('_', ' ').title()} ---")
        for k, v in r.items():
            print(f"  {k}: {v}")
