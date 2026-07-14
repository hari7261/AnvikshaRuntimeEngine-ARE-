"""Provider-free built-in deterministic capabilities."""
from __future__ import annotations
import ast, operator
from typing import Any, Mapping
from anviksha.capabilities.base import CapabilityMetadata
from anviksha.types import CapabilityKind, CapabilityResult, Intent

class EchoModelCapability:
    metadata = CapabilityMetadata("builtin.echo_model", "Echo Model", CapabilityKind.MODEL, frozenset({Intent.GENERAL, Intent.QUESTION_ANSWERING, Intent.SUMMARIZATION, Intent.CREATIVE_GENERATION}), 20, 0.0, 0.7, False, True)
    async def execute(self, arguments: Mapping[str, Any]) -> CapabilityResult:
        goal = str(arguments.get("goal", ""))
        return CapabilityResult(output=goal, confidence=0.7, metadata={"provider": "builtin"})

class CalculatorCapability:
    metadata = CapabilityMetadata("builtin.calculator", "Calculator", CapabilityKind.TOOL, frozenset({Intent.MATHEMATICAL_COMPUTATION}), 5, 0.0, 0.99, True, True)
    _ops = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg}
    async def execute(self, arguments: Mapping[str, Any]) -> CapabilityResult:
        expr = str(arguments.get("expression") or arguments.get("goal", ""))
        value = self._eval(ast.parse(expr, mode="eval").body)
        return CapabilityResult(output=value, confidence=0.99, metadata={"expression": expr})
    def _eval(self, node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, int | float): return float(node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in self._ops: return self._ops[type(node.op)](self._eval(node.left), self._eval(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in self._ops: return self._ops[type(node.op)](self._eval(node.operand))
        raise ValueError("unsupported mathematical expression")
