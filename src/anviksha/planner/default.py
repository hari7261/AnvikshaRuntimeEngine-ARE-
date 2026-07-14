"""Deterministic RFC-compliant planner."""
from __future__ import annotations
import re
from anviksha.capabilities.registry import CapabilityRegistry
from anviksha.exceptions import PlanningError
from anviksha.types import ExecutionPlan, ExecutionRequest, Intent, PlanStep

class RuleBasedPlanner:
    def __init__(self, registry: CapabilityRegistry) -> None: self._registry = registry
    def plan(self, request: ExecutionRequest) -> ExecutionPlan:
        intent = self._classify(request.goal)
        candidates = self._registry.find(intent, request.constraints)
        if not candidates and intent is not Intent.GENERAL:
            intent = Intent.GENERAL
            candidates = self._registry.find(intent, request.constraints)
        if not candidates:
            raise PlanningError(f"no capability can satisfy intent {intent}")
        cap = candidates[0]
        step = PlanStep("step-1", cap.metadata.id, intent, {"goal": request.goal, **request.inputs})
        return ExecutionPlan(request.execution_id, intent, (step,), (f"selected {cap.metadata.id} for {intent}",), cap.metadata.average_latency_ms, cap.metadata.cost_per_call)
    def _classify(self, goal: str) -> Intent:
        text = goal.lower().strip()
        if re.fullmatch(r"[\d\s+\-*/().^]+", text): return Intent.MATHEMATICAL_COMPUTATION
        if any(w in text for w in ("calculate", "compute", "sum of", "product of")): return Intent.MATHEMATICAL_COMPUTATION
        if "summarize" in text or "summary" in text: return Intent.SUMMARIZATION
        if "translate" in text: return Intent.TRANSLATION
        if "classify" in text or "categorize" in text: return Intent.CLASSIFICATION
        if "search" in text or "retrieve" in text: return Intent.RETRIEVAL
        if text.endswith("?"): return Intent.QUESTION_ANSWERING
        return Intent.GENERAL
