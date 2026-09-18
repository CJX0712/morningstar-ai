"""安全计算器：仅允许算术运算与常用数学函数，杜绝任意代码执行。"""
from __future__ import annotations

import ast
import math
import operator

_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}
_ALLOWED_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_ALLOWED_FUNCS = {
    name: getattr(math, name)
    for name in (
        "sqrt", "pow", "log", "log10", "log2", "exp", "sin", "cos", "tan",
        "asin", "acos", "atan", "degrees", "radians", "factorial", "gcd", "hypot",
    )
}
_ALLOWED_NAMES = {name: getattr(math, name) for name in ("pi", "e", "tau")}


def _eval_node(node: ast.AST):
    if isinstance(node, ast.Constant):  # 数字字面量
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("仅支持数值")
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
        return _ALLOWED_BINOPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARY:
        return _ALLOWED_UNARY[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        fn = _ALLOWED_FUNCS.get(node.func.id)
        if fn is None:
            raise ValueError(f"不支持的函数: {node.func.id}")
        args = [_eval_node(a) for a in node.args]
        return fn(*args)
    if isinstance(node, ast.Name):
        if node.id in _ALLOWED_NAMES:
            return _ALLOWED_NAMES[node.id]
        raise ValueError(f"未知名称: {node.id}")
    raise ValueError(f"不支持的表达式: {ast.dump(node)}")


def calculate(expression: str) -> str:
    """安全计算数学表达式，例如 'sqrt(144) + 2**10'。"""
    try:
        tree = ast.parse(str(expression).strip(), mode="eval")
        result = _eval_node(tree.body)
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        return str(result)
    except Exception as exc:  # noqa: BLE001
        return f"[计算错误] {exc}"
