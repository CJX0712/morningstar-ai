"""工具注册表：声明可用工具及其 OpenAI function-calling Schema。

新增工具只需：实现函数 -> 在此注册（名称、函数、描述、参数 Schema）。
"""
from __future__ import annotations

from typing import Any, Callable

from app.tools.calculator import calculate
from app.tools.code_exec import run_python
from app.tools.search import web_search

# 工具元信息：name / func / description / parameters(OpenAI schema)
_TOOL_DEFS: list[dict[str, Any]] = [
    {
        "name": "web_search",
        "func": web_search,
        "description": "当需要实时信息、新闻、股价、天气或最新事实时，使用联网搜索获取网页结果。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"},
                "num_results": {"type": "integer", "description": "返回结果条数，默认 5"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "calculate",
        "func": calculate,
        "description": "计算数学表达式，支持 + - * / ** % 以及 sqrt、log、sin、cos、factorial、pi、e 等数学函数。",
        "parameters": {
            "type": "object",
            "properties": {"expression": {"type": "string", "description": "数学表达式，例如 'sqrt(144)+2**10'"}},
            "required": ["expression"],
        },
    },
    {
        "name": "run_python",
        "func": run_python,
        "description": "在沙箱中执行 Python 代码并获取输出，适合数据处理、算法验证、绘图数据计算等。",
        "parameters": {
            "type": "object",
            "properties": {"code": {"type": "string", "description": "要执行的 Python 代码"}},
            "required": ["code"],
        },
    },
]


# OpenAI function-calling 格式
TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": t["name"],
            "description": t["description"],
            "parameters": t["parameters"],
        },
    }
    for t in _TOOL_DEFS
]

_REGISTRY: dict[str, Callable] = {t["name"]: t["func"] for t in _TOOL_DEFS}


def execute_tool(name: str, arguments_json: str) -> str:
    """按名称执行工具，arguments 为 JSON 字符串。返回结果文本。"""
    import json

    func = _REGISTRY.get(name)
    if not func:
        return f"[未知工具] {name}"
    try:
        args = json.loads(arguments_json or "{}")
    except json.JSONDecodeError:
        # 退而求其次：若参数本身就是字符串，直接作为首个位置参数
        args = {"expression": arguments_json} if name == "calculate" else {"query": arguments_json}
    try:
        return str(func(**args))
    except Exception as exc:  # noqa: BLE001
        return f"[工具执行错误] {exc}"
