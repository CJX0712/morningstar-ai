"""智能体编排：ReAct 风格的工具调用循环。

将多轮记忆、RAG 上下文注入、工具调用（联网搜索 / 计算 / 代码执行）串接起来，
通过流式事件驱动前端实时渲染。
"""
from __future__ import annotations

import asyncio
from typing import AsyncGenerator

from app.async_utils import run_generator_in_thread
from app.config import settings
from app.llm import LLM
from app.rag import rag
from app.schemas import ChatMessage
from app.tools import TOOL_SCHEMAS, execute_tool

SYSTEM_PROMPT = (
    "你是一个名为「晨星 (MorningStar)」的世界级 AI 智能体，由用户 晨星 打造。"
    "你严谨、可靠、乐于助人。当问题需要实时信息、精确计算或代码执行时，"
    "请主动调用相应工具；工具结果可用时，应基于事实作答并注明来源。"
)


class Agent:
    def __init__(
        self,
        provider: str,
        model: str | None = None,
        use_rag: bool = False,
        temperature: float = 0.7,
    ) -> None:
        self.llm = LLM(provider, model, temperature)
        self.use_rag = use_rag
        self.temperature = temperature

    async def run(self, messages: list[ChatMessage]) -> AsyncGenerator[dict, None]:
        conv = [m.model_dump(exclude_none=True) for m in messages]

        # RAG：基于最后一条用户消息检索并注入上下文
        if self.use_rag and rag.ready:
            last_user = next(
                (m.content for m in reversed(messages) if m.role == "user"), ""
            )
            if last_user:
                ctx = rag.query(last_user)
                if ctx:
                    ctx_text = "\n\n".join(
                        f"【来源 {c['source']}】\n{c['content']}" for c in ctx
                    )
                    conv.insert(
                        0,
                        {
                            "role": "system",
                            "content": f"{SYSTEM_PROMPT}\n\n以下是知识库检索到的相关资料，请优先参考：\n{ctx_text}",
                        },
                    )
                else:
                    conv.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
            else:
                conv.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
        else:
            conv.insert(0, {"role": "system", "content": SYSTEM_PROMPT})

        for _ in range(settings.max_tool_rounds):
            aggregate: dict | None = None
            stream = run_generator_in_thread(self.llm.chat_stream, conv, TOOL_SCHEMAS)
            async for ev in stream:
                if ev["type"] == "token":
                    yield {"type": "token", "text": ev["data"]}
                else:
                    aggregate = ev["data"]

            if aggregate is None:
                yield {"type": "error", "message": "模型未返回任何内容。"}
                return

            tool_calls = aggregate.get("tool_calls") or []
            if not tool_calls:
                break

            # 把带有 tool_calls 的助手消息加入对话
            conv.append(
                {
                    "role": "assistant",
                    "content": aggregate.get("content") or None,
                    "tool_calls": tool_calls,
                }
            )
            for tc in tool_calls:
                name = tc["function"]["name"]
                args = tc["function"]["arguments"]
                result = await asyncio.to_thread(execute_tool, name, args)
                yield {
                    "type": "tool",
                    "name": name,
                    "args": args,
                    "result": result,
                }
                conv.append(
                    {"role": "tool", "tool_call_id": tc["id"], "content": result}
                )

        yield {"type": "done"}
