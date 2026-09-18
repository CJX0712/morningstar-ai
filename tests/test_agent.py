"""智能体编排测试：用 FakeLLM 模拟「先调用工具、再给出最终答案」的两轮循环。

验证 Agent 能正确：解析工具调用 -> 执行工具 -> 把结果回灌对话 -> 产出最终回答。
无需联网 / API Key。
"""
import pytest

from app.agent import Agent
from app.schemas import ChatMessage


class FakeLLM:
    def __init__(self, provider, model=None, temperature=0.7):
        self.provider = provider
        self.model = model
        self._called = False

    def is_configured(self):
        return True

    def chat_stream(self, messages, tools=None):
        if not self._called:
            self._called = True
            yield {
                "type": "aggregate",
                "data": {
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "calculate", "arguments": '{"expression":"2**10"}'},
                        }
                    ],
                    "finish_reason": "tool_calls",
                },
            }
        else:
            yield {"type": "token", "data": "结果是 "}
            yield {"type": "token", "data": "1024。"}
            yield {
                "type": "aggregate",
                "data": {"content": "结果是 1024。", "tool_calls": [], "finish_reason": "stop"},
            }


@pytest.mark.asyncio
async def test_agent_tool_loop(monkeypatch):
    monkeypatch.setattr("app.agent.LLM", FakeLLM)
    agent = Agent(provider="openai", model="fake", use_rag=False)
    events = [ev async for ev in agent.run([ChatMessage(role="user", content="2的10次方是多少？")])]

    types = [e["type"] for e in events]
    assert "tool" in types
    assert "done" in types
    tool_ev = next(e for e in events if e["type"] == "tool")
    assert tool_ev["name"] == "calculate"
    assert "1024" in tool_ev["result"]
    # 至少有一个 token 事件
    assert any(e["type"] == "token" for e in events)
