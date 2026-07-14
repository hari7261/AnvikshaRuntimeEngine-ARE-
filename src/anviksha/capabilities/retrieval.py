"""BM25-style text retrieval capability. No external dependencies."""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Mapping

from anviksha.capabilities.base import CapabilityMetadata
from anviksha.types import CapabilityKind, CapabilityResult, Intent


class RetrievalCapability:
    metadata = CapabilityMetadata(
        id="builtin.retrieval",
        name="Text Retrieval",
        kind=CapabilityKind.RETRIEVER,
        supported_intents=frozenset({Intent.RETRIEVAL}),
        average_latency_ms=10,
        cost_per_call=0.0,
        reliability=0.95,
        deterministic=True,
        offline=True,
    )

    def __init__(self) -> None:
        self._documents: dict[str, str] = {}
        self._doc_freq: Counter[str] = Counter()
        self._total_docs: int = 0
        self._avg_doc_len: float = 0.0
        self._k1: float = 1.5
        self._b: float = 0.75

    def index(self, documents: Mapping[str, str]) -> None:
        self._documents = dict(documents)
        self._total_docs = len(documents)
        total_len = 0
        for text in documents.values():
            tokens = self._tokenize(text)
            total_len += len(tokens)
            for token in set(tokens):
                self._doc_freq[token] += 1
        self._avg_doc_len = total_len / self._total_docs if self._total_docs else 0.0

    async def execute(self, arguments: Mapping[str, Any]) -> CapabilityResult:
        query = str(arguments.get("query") or arguments.get("goal", ""))
        if not self._documents:
            return CapabilityResult(
                output=[], confidence=0.0, metadata={"query": query, "results": 0}
            )
        query_tokens = self._tokenize(query)
        scores: list[tuple[str, float]] = []
        for doc_id, text in self._documents.items():
            score = self._bm25(query_tokens, text)
            if score > 0:
                scores.append((doc_id, score))
        scores.sort(key=lambda x: -x[1])
        results = [
            {"id": doc_id, "score": round(score, 4), "text": self._documents[doc_id]}
            for doc_id, score in scores[:10]
        ]
        return CapabilityResult(
            output=results,
            confidence=0.9 if results else 0.0,
            metadata={"query": query, "results": len(results)},
        )

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"[a-z0-9]+", text.lower())

    def _bm25(self, query_tokens: list[str], text: str) -> float:
        doc_tokens = self._tokenize(text)
        doc_len = len(doc_tokens)
        if doc_len == 0:
            return 0.0
        tf = Counter(doc_tokens)
        score = 0.0
        for token in query_tokens:
            if token not in self._doc_freq:
                continue
            idf = math.log(
                (self._total_docs - self._doc_freq[token] + 0.5)
                / (self._doc_freq[token] + 0.5)
                + 1.0
            )
            term_freq = tf.get(token, 0)
            score += idf * (
                (term_freq * (self._k1 + 1))
                / (term_freq + self._k1 * (1 - self._b + self._b * doc_len / self._avg_doc_len))
            )
        return score
