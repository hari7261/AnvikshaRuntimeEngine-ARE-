"""Provider-free built-in deterministic capabilities."""
from __future__ import annotations
import ast
import operator
from typing import Any, Mapping
from anviksha.capabilities.base import CapabilityMetadata
from anviksha.types import CapabilityKind, CapabilityResult, Intent


class CalculatorCapability:
    """Evaluates arithmetic expressions using AST (safe, no eval())."""
    metadata = CapabilityMetadata(
        "builtin.calculator",
        "Calculator",
        CapabilityKind.TOOL,
        frozenset({Intent.MATHEMATICAL_COMPUTATION}),
        5,
        0.0,
        0.99,
        True,
        True,
    )
    _ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }

    async def execute(self, arguments: Mapping[str, Any]) -> CapabilityResult:
        expr = str(arguments.get("expression") or arguments.get("goal", ""))
        try:
            tree = ast.parse(expr, mode="eval")
        except SyntaxError as exc:
            raise ValueError(
                f"'{expr}' is not a valid arithmetic expression"
            ) from exc
        try:
            value = self._eval(tree.body)
        except Exception as exc:
            raise ValueError(
                f"'{expr}' is not a valid arithmetic expression: {exc}"
            ) from exc
        return CapabilityResult(
            output=value,
            confidence=0.99,
            metadata={"expression": expr},
        )

    def _eval(self, node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
            return float(node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in self._ops:
            return self._ops[type(node.op)](
                self._eval(node.left), self._eval(node.right)
            )
        if isinstance(node, ast.UnaryOp) and type(node.op) in self._ops:
            return self._ops[type(node.op)](self._eval(node.operand))
        raise ValueError(
            f"unsupported expression: {ast.dump(node)}"
        )
