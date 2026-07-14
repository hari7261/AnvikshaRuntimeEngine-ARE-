"""Shared immutable runtime data models."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any
from uuid import uuid4


class Intent(StrEnum):
    QUESTION_ANSWERING = "question_answering"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    CLASSIFICATION = "classification"
    MATHEMATICAL_COMPUTATION = "mathematical_computation"
    TOOL_INVOCATION = "tool_invocation"
    RETRIEVAL = "retrieval"
    CREATIVE_GENERATION = "creative_generation"
    GENERAL = "general"

class CapabilityKind(StrEnum):
    MODEL = "model"
    TOOL = "tool"
    RETRIEVER = "retriever"
    MEMORY = "memory"
    CACHE = "cache"
    VALIDATOR = "validator"

class ExecutionStatus(StrEnum):
    PENDING = "pending"
    PLANNING = "planning"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"

@dataclass(frozen=True, slots=True)
class ExecutionConstraints:
    max_latency_ms: int | None = None
    max_cost: float | None = None
    min_confidence: float = 0.0
    offline_only: bool = False
    allowed_capabilities: frozenset[str] | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    goal: str
    inputs: Mapping[str, Any] = field(default_factory=dict)
    constraints: ExecutionConstraints = field(default_factory=ExecutionConstraints)
    execution_id: str = field(default_factory=lambda: str(uuid4()))
    session_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.goal or not self.goal.strip():
            raise ValueError("goal must be a non-empty string")
        object.__setattr__(self, "inputs", MappingProxyType(dict(self.inputs)))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

@dataclass(frozen=True, slots=True)
class PlanStep:
    id: str
    capability_id: str
    intent: Intent
    arguments: Mapping[str, Any] = field(default_factory=dict)
    depends_on: tuple[str, ...] = ()

@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    execution_id: str
    intent: Intent
    steps: tuple[PlanStep, ...]
    diagnostics: tuple[str, ...] = ()
    estimated_latency_ms: int = 0
    estimated_cost: float = 0.0

@dataclass(frozen=True, slots=True)
class CapabilityResult:
    output: Any
    confidence: float = 1.0
    metadata: Mapping[str, Any] = field(default_factory=dict)

@dataclass(frozen=True, slots=True)
class RuntimeResponse:
    execution_id: str
    status: ExecutionStatus
    output: Any
    confidence: float
    metadata: Mapping[str, Any]
    diagnostics: tuple[str, ...] = ()
