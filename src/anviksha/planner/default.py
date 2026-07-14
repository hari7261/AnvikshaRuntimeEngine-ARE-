"""Deterministic RFC-compliant planner.

The planner classifies request intent and selects the most appropriate
capability. Every decision is recorded in diagnostics. No silent fallbacks:
if no capability satisfies the intent, PlanningError is raised with the
exact reason.
"""
from __future__ import annotations

import re

from anviksha.capabilities.registry import CapabilityRegistry
from anviksha.exceptions import PlanningError
from anviksha.types import ExecutionPlan, ExecutionRequest, Intent, PlanStep


class RuleBasedPlanner:
    def __init__(self, registry: CapabilityRegistry) -> None:
        self._registry = registry

    def plan(self, request: ExecutionRequest) -> ExecutionPlan:
        intent = self._classify(request.goal)
        candidates = self._registry.find(intent, request.constraints)
        if not candidates:
            registered_ids = [c.metadata.id for c in self._registry.all()]
            raise PlanningError(
                f"no capability registered for intent '{intent.value}'. "
                f"Registered capabilities: {registered_ids}. "
                f"Goal: '{request.goal}'"
            )
        cap = candidates[0]
        steps = (
            PlanStep(
                "step-1",
                cap.metadata.id,
                intent,
                {"goal": request.goal, **request.inputs},
            ),
        )
        diagnostics = [f"selected {cap.metadata.id} for {intent.value}"]
        if len(candidates) > 1:
            diagnostics.append(
                f"evaluated {len(candidates)} candidates, chose {cap.metadata.id}"
            )
        return ExecutionPlan(
            execution_id=request.execution_id,
            intent=intent,
            steps=steps,
            diagnostics=tuple(diagnostics),
            estimated_latency_ms=cap.metadata.average_latency_ms,
            estimated_cost=cap.metadata.cost_per_call,
        )

    def _classify(self, goal: str) -> Intent:
        text = goal.lower().strip()
        if not text:
            raise PlanningError("cannot classify empty goal")
        if re.fullmatch(r"[\d\s+\-*/().^]+", text):
            return Intent.MATHEMATICAL_COMPUTATION
        if any(w in text for w in ("calculate", "compute", "sum of", "product of")):
            return Intent.MATHEMATICAL_COMPUTATION
        if "summarize" in text or "summary" in text:
            return Intent.SUMMARIZATION
        if "translate" in text:
            return Intent.TRANSLATION
        if "classify" in text or "categorize" in text:
            return Intent.CLASSIFICATION
        if "search" in text or "retrieve" in text:
            return Intent.RETRIEVAL
        if text.endswith("?"):
            return Intent.QUESTION_ANSWERING
        return Intent.GENERAL
