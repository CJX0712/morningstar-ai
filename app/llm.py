"""多后端大模型适配层。

基于 OpenAI 官方 SDK（兼容协议），一套代码切换：
  - OpenAI / DeepSeek / 智谱 GLM / 通义千问（云端 API）
  - 本地 Ollama（OpenAI 兼容端点）
支持流式输出与工具调用（function calling）。
"""
from __future__ import annotations

import json
from typing import Any, Optional

from openai import OpenAI

from app.config import settings


class LLM:
    def __init__(
        self,
        provider: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
    ) -> None:
        self.provider = provider
        if provider not in settings.providers:
            raise ValueError(f"不支持的提供方: {provider}")
        cfg = settings.providers[provider]
        self.model = model or cfg["default_model"]
        self.temperature = temperature
        # Ollama 等本地端点不需要真实 Key，传占位即可
        api_key = cfg["api_key"] if cfg["api_key"] else "not-needed"
        self.client = OpenAI(base_url=cfg["base_url"], api_key=api_key)

    def chat_stream(self, messages: list[dict], tools: Optional[list[dict]] = None):
        """同步流式对话。

        产出两类事件字典：
          - {"type": "token", "data": "<增量文本>"}
          - {"type": "aggregate", "data": {"content", "tool_calls", "finish_reason"}}
        """
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        content_parts: list[str] = []
        tool_calls: dict[int, dict] = {}
        finish_reason: Optional[str] = None

        stream = self.client.chat.completions.create(**kwargs)
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                content_parts.append(delta.content)
                yield {"type": "token", "data": delta.content}
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index if tc.index is not None else 0
                    slot = tool_calls.setdefault(
                        idx, {"id": "", "type": "function", "function": {"name": "", "arguments": ""}}
                    )
                    if tc.id:
                        slot["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            slot["function"]["name"] += tc.function.name
                        if tc.function.arguments:
                            slot["function"]["arguments"] += tc.function.arguments
            fr = chunk.choices[0].finish_reason
            if fr:
                finish_reason = fr

        # 规范化 tool_calls 为 OpenAI 消息格式
        normalized: list[dict] = []
        for slot in tool_calls.values():
            # 解析参数，失败则保留原始字符串（交给执行器处理）
            try:
                json.loads(slot["function"]["arguments"] or "{}")
            except json.JSONDecodeError:
                pass
            normalized.append(
                {
                    "id": slot["id"],
                    "type": "function",
                    "function": {
                        "name": slot["function"]["name"],
                        "arguments": slot["function"]["arguments"],
                    },
                }
            )

        yield {
            "type": "aggregate",
            "data": {
                "content": "".join(content_parts),
                "tool_calls": normalized,
                "finish_reason": finish_reason,
            },
        }

    def is_configured(self) -> bool:
        """该提供方是否已配置可用（有 Key 或是本地 Ollama）。"""
        if self.provider == "ollama":
            return True
        return bool(settings.providers[self.provider]["api_key"])
