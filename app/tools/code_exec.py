"""Python 代码执行沙箱。

在独立子进程中运行用户/模型生成的 Python 代码，带超时与输出长度限制。
注意：这是开发沙箱内的受限执行，仅建议在可信环境中启用。
"""
from __future__ import annotations

import subprocess
import textwrap

PYTHON_BIN = "/root/.pyenv/versions/3.11.1/bin/python3.11"
TIMEOUT = 15
MAX_OUTPUT = 4000


def _strip_fences(code: str) -> str:
    code = code.strip()
    if code.startswith("```"):
        code = code.split("```", 2)[1]
        if code.startswith("python") or code.startswith("py"):
            code = code.split("\n", 1)[1] if "\n" in code else ""
    return code


def run_python(code: str) -> str:
    """执行 Python 代码片段，返回 stdout/stderr。"""
    source = _strip_fences(code)
    if not source:
        return "[空代码]"
    try:
        proc = subprocess.run(
            [PYTHON_BIN, "-c", source],
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return f"[执行超时] 超过 {TIMEOUT} 秒被终止"
    except Exception as exc:  # noqa: BLE001
        return f"[执行异常] {exc}"

    out = (proc.stdout or "") + (proc.stderr or "")
    if not out.strip():
        out = "[无输出]"
    if len(out) > MAX_OUTPUT:
        out = out[:MAX_OUTPUT] + "\n... (输出过长已截断)"
    return out
