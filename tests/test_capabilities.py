"""Comprehensive tests for all built-in capabilities."""
from __future__ import annotations

import asyncio
import os
import tempfile
from contextlib import suppress

import pytest

from anviksha.capabilities import (
    CalculatorCapability,
    FilesystemCapability,
    HTTPCapability,
    MemoryCapability,
    PythonCapability,
    RetrievalCapability,
)
from anviksha.exceptions import CapabilityError
from anviksha.types import CapabilityKind, Intent


class TestRetrievalCapability:

    @pytest.fixture
    def cap(self) -> RetrievalCapability:
        r = RetrievalCapability()
        r.index({
            "doc1": "Python is a programming language",
            "doc2": "Anviksha is a runtime engine for AI",
            "doc3": "The capital of France is Paris",
        })
        return r

    @pytest.mark.asyncio
    async def test_basic_retrieval(self, cap: RetrievalCapability) -> None:
        result = await cap.execute({"query": "programming language"})
        assert len(result.output) > 0
        assert any("Python" in r["text"] for r in result.output)

    @pytest.mark.asyncio
    async def test_no_match_returns_empty(self, cap: RetrievalCapability) -> None:
        result = await cap.execute({"query": "xyznonexistent"})
        assert result.output == []
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_empty_index(self) -> None:
        cap = RetrievalCapability()
        result = await cap.execute({"query": "anything"})
        assert result.output == []
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_scored_results_ordered(self, cap: RetrievalCapability) -> None:
        result = await cap.execute({"query": "capital of France"})
        assert len(result.output) >= 1
        scores = [r["score"] for r in result.output]
        assert scores == sorted(scores, reverse=True)

    def test_metadata(self) -> None:
        cap = RetrievalCapability()
        assert cap.metadata.kind == CapabilityKind.RETRIEVER
        assert cap.metadata.deterministic
        assert Intent.RETRIEVAL in cap.metadata.supported_intents


class TestMemoryCapability:

    @pytest.fixture
    def cap(self) -> MemoryCapability:
        return MemoryCapability()

    @pytest.mark.asyncio
    async def test_set_and_get(self, cap: MemoryCapability) -> None:
        await cap.execute({"action": "set", "key": "name", "value": "Alice"})
        result = await cap.execute({"action": "get", "key": "name"})
        assert result.output == "Alice"

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self, cap: MemoryCapability) -> None:
        with pytest.raises(CapabilityError, match="not found"):
            await cap.execute({"action": "get", "key": "nobody"})

    @pytest.mark.asyncio
    async def test_delete(self, cap: MemoryCapability) -> None:
        await cap.execute({"action": "set", "key": "k", "value": "v"})
        await cap.execute({"action": "delete", "key": "k"})
        with pytest.raises(CapabilityError):
            await cap.execute({"action": "get", "key": "k"})

    @pytest.mark.asyncio
    async def test_clear(self, cap: MemoryCapability) -> None:
        await cap.execute({"action": "set", "key": "a", "value": "1"})
        await cap.execute({"action": "clear"})
        result = await cap.execute({"action": "keys"})
        assert result.output == []

    @pytest.mark.asyncio
    async def test_keys(self, cap: MemoryCapability) -> None:
        await cap.execute({"action": "set", "key": "x", "value": "1"})
        await cap.execute({"action": "set", "key": "y", "value": "2"})
        result = await cap.execute({"action": "keys"})
        assert set(result.output) == {"x", "y"}

    @pytest.mark.asyncio
    async def test_unknown_action(self, cap: MemoryCapability) -> None:
        with pytest.raises(CapabilityError, match="unknown memory action"):
            await cap.execute({"action": "invalid"})

    def test_metadata(self) -> None:
        cap = MemoryCapability()
        assert cap.metadata.kind == CapabilityKind.MEMORY
        assert cap.metadata.offline
        assert cap.metadata.cost_per_call == 0.0


class TestPythonCapability:

    @pytest.mark.asyncio
    async def test_arithmetic(self) -> None:
        cap = PythonCapability()
        result = await cap.execute({"expression": "2 + 3 * 4"})
        assert result.output == 14

    @pytest.mark.asyncio
    async def test_string_operations(self) -> None:
        cap = PythonCapability()
        result = await cap.execute({"expression": "'hello ' + 'world'"})
        assert result.output == "hello world"

    @pytest.mark.asyncio
    async def test_list_comprehension(self) -> None:
        cap = PythonCapability()
        result = await cap.execute({"expression": "[x*2 for x in range(5)]"})
        assert result.output == [0, 2, 4, 6, 8]

    @pytest.mark.asyncio
    async def test_math_module(self) -> None:
        cap = PythonCapability()
        result = await cap.execute({"expression": "math.sqrt(16)"})
        assert result.output == 4.0

    @pytest.mark.asyncio
    async def test_blocks_import(self) -> None:
        cap = PythonCapability()
        with pytest.raises(ValueError, match="unsafe"):
            await cap.execute({"expression": "__import__('os')"})

    @pytest.mark.asyncio
    async def test_blocks_function_def(self) -> None:
        cap = PythonCapability()
        with pytest.raises(ValueError, match="unsafe"):
            await cap.execute({"expression": "lambda x: x"})

    @pytest.mark.asyncio
    async def test_invalid_syntax(self) -> None:
        cap = PythonCapability()
        with pytest.raises(ValueError, match="not a valid Python expression"):
            await cap.execute({"expression": "def foo():"})

    @pytest.mark.asyncio
    async def test_safe_globals_isolated(self) -> None:
        cap = PythonCapability()
        result = await cap.execute({"expression": "type(42).__name__"})
        assert result.output == "int"

    def test_metadata(self) -> None:
        cap = PythonCapability()
        assert cap.metadata.deterministic
        assert cap.metadata.offline


class TestFilesystemCapability:

    @pytest.mark.asyncio
    async def test_read_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cap = FilesystemCapability(sandbox_path=tmpdir)
            test_file = os.path.join(tmpdir, "test.txt")
            await cap.execute({"action": "write", "path": test_file, "content": "hello"})
            result = await cap.execute({"action": "read", "path": test_file})
            assert result.output == "hello"

    @pytest.mark.asyncio
    async def test_list_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cap = FilesystemCapability(sandbox_path=tmpdir)
            open(os.path.join(tmpdir, "a.txt"), "w").close()
            open(os.path.join(tmpdir, "b.txt"), "w").close()
            result = await cap.execute({"action": "list", "path": tmpdir})
            assert set(result.output) == {"a.txt", "b.txt"}

    @pytest.mark.asyncio
    async def test_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cap = FilesystemCapability(sandbox_path=tmpdir)
            result = await cap.execute({"action": "exists", "path": tmpdir})
            assert result.output is True

    @pytest.mark.asyncio
    async def test_sandbox_blocks_escape(self) -> None:
        cap = FilesystemCapability(sandbox_path="/tmp/safe")
        with pytest.raises(CapabilityError, match="outside sandbox"):
            await cap.execute({"action": "read", "path": "/etc/passwd"})

    @pytest.mark.asyncio
    async def test_missing_path_raises_error(self) -> None:
        cap = FilesystemCapability()
        with pytest.raises(CapabilityError, match="path is required"):
            await cap.execute({"action": "read", "path": ""})

    def test_metadata(self) -> None:
        cap = FilesystemCapability()
        assert cap.metadata.offline
        assert cap.metadata.deterministic


class TestHTTPCapability:

    @pytest.mark.asyncio
    async def test_missing_url(self) -> None:
        cap = HTTPCapability()
        with pytest.raises(CapabilityError, match="url is required"):
            await cap.execute({})

    @pytest.mark.asyncio
    async def test_invalid_url_fails_gracefully(self) -> None:
        cap = HTTPCapability()
        with pytest.raises(CapabilityError, match="failed"):
            await cap.execute({"url": "http://nonexistent.invalid"})

    def test_metadata(self) -> None:
        cap = HTTPCapability()
        assert not cap.metadata.offline
        assert not cap.metadata.deterministic


class TestCalculatorEdgeCases:

    @pytest.mark.asyncio
    async def test_division_by_zero(self) -> None:
        calc = CalculatorCapability()
        with pytest.raises(ValueError):
            await calc.execute({"expression": "1/0"})

    @pytest.mark.asyncio
    async def test_large_numbers(self) -> None:
        calc = CalculatorCapability()
        result = await calc.execute({"expression": "1e10 + 2e10"})
        assert result.output == 3e10

    @pytest.mark.asyncio
    async def test_negative_result(self) -> None:
        calc = CalculatorCapability()
        result = await calc.execute({"expression": "3 - 10"})
        assert result.output == -7.0

    @pytest.mark.asyncio
    async def test_nested_parentheses(self) -> None:
        calc = CalculatorCapability()
        result = await calc.execute({"expression": "((2 + 3) * (4 + 1))"})
        assert result.output == 25.0


class TestMemoryConcurrency:

    @pytest.mark.asyncio
    async def test_concurrent_access(self) -> None:
        cap = MemoryCapability()

        async def writer(key: str, value: str) -> None:
            for _ in range(10):
                await cap.execute({"action": "set", "key": key, "value": value})

        async def reader(key: str) -> None:
            for _ in range(10):
                with suppress(CapabilityError):
                    await cap.execute({"action": "get", "key": key})

        await asyncio.gather(
            writer("k1", "v1"),
            writer("k2", "v2"),
            reader("k1"),
            reader("k2"),
        )
        result = await cap.execute({"action": "get", "key": "k1"})
        assert result.output == "v1"
