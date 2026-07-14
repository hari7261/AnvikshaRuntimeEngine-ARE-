"""Safe Python expression evaluation capability."""
from __future__ import annotations

import ast
import math
from typing import Any, Mapping

from anviksha.capabilities.base import CapabilityMetadata
from anviksha.types import CapabilityKind, CapabilityResult, Intent


class PythonCapability:
    metadata = CapabilityMetadata(
        id="builtin.python",
        name="Python Evaluator",
        kind=CapabilityKind.TOOL,
        supported_intents=frozenset({Intent.TOOL_INVOCATION, Intent.MATHEMATICAL_COMPUTATION}),
        average_latency_ms=5,
        cost_per_call=0.0,
        reliability=0.99,
        deterministic=True,
        offline=True,
    )

    _SAFE_GLOBALS: dict[str, Any] = {
        "abs": abs, "all": all, "any": any, "bool": bool,
        "dict": dict, "enumerate": enumerate, "float": float,
        "int": int, "len": len, "list": list, "map": map,
        "max": max, "min": min, "pow": pow, "range": range,
        "round": round, "sorted": sorted, "str": str,
        "sum": sum, "tuple": tuple, "type": type, "zip": zip,
        "True": True, "False": False, "None": None,
        "math": math, "abs": abs, "hex": hex, "bin": bin,
        "oct": oct, "ord": ord, "chr": chr, "reversed": reversed,
    }

    _UNSAFE_NAMES: frozenset[str] = frozenset({
        "__import__", "exec", "eval", "compile", "open",
        "__builtins__", "globals", "locals", "vars",
        "getattr", "setattr", "delattr", "__import__",
        "breakpoint", "input", "print",
    })

    async def execute(self, arguments: Mapping[str, Any]) -> CapabilityResult:
        expr = str(arguments.get("expression") or arguments.get("goal", ""))
        expr = self._clean_expression(expr)
        try:
            tree = ast.parse(expr, mode="eval")
        except SyntaxError as exc:
            raise ValueError(f"'{expr}' is not a valid Python expression") from exc
        self._validate_tree(tree)
        try:
            code = compile(tree, "<string>", "eval")
            result = eval(code, {"__builtins__": {}}, self._SAFE_GLOBALS)
            return CapabilityResult(
                output=result,
                confidence=0.99,
                metadata={"expression": expr, "type": type(result).__name__},
            )
        except Exception as exc:
            raise ValueError(f"evaluation failed: {exc}") from exc

    def _clean_expression(self, expr: str) -> str:
        expr = expr.strip()
        for prefix in ("evaluate", "eval", "compute", "run", "python"):
            if expr.lower().startswith(prefix):
                expr = expr[len(prefix):].strip()
                break
        return expr

    def _validate_tree(self, tree: ast.AST) -> None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in self._UNSAFE_NAMES:
                    raise ValueError(
                        f"call to unsafe function: {node.func.id}"
                    )
                if isinstance(node.func, ast.Attribute):
                    attr = node.func.attr
                    if attr in self._UNSAFE_NAMES:
                        raise ValueError(
                            f"call to unsafe attribute: {attr}"
                        )
            if isinstance(node, (ast.Import, ast.ImportFrom, ast.ClassDef,
                                 ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                raise ValueError(
                    f"unsafe construct not allowed: {type(node).__name__}"
                )
